import asyncio
import json
import os
import time
from playwright.async_api import async_playwright, Page

# --- Configuration ---
VERTEX_URL = "https://console.cloud.google.com/vertex-ai/studio/multimodal?mode=prompt&model=gemini-2.5-flash-lite-preview-09-2025"
COOKIES_ENV_VAR = "GOOGLE_COOKIES"

class CloudHarvester:
    def __init__(self, cred_manager):
        self.cred_manager = cred_manager
        self.browser = None
        self.page = None
        self.is_running = False
        self.last_harvest_time = 0
        self.current_cookies = os.environ.get(COOKIES_ENV_VAR)
        self.restart_requested = False

    async def update_cookies(self, new_cookies_json):
        """Updates cookies and triggers a browser restart."""
        print("🍪 Cloud Harvester: Received new cookies. Scheduling restart...")
        self.current_cookies = new_cookies_json
        self.restart_requested = True

    async def start(self):
        """Starts the browser and the harvesting loop."""
        if self.is_running:
            return
        
        if not self.current_cookies:
            print("⚠️ Cloud Harvester: No cookies available. Waiting for update via /admin...")
            # Wait loop for cookies
            # while not self.current_cookies:
            #     await asyncio.sleep(5)
            # Allow proceeding without cookies based on user feedback (experimental)
            print("⚠️ Cloud Harvester: Proceeding without cookies (Experimental).")
        
        print("☁️ Cloud Harvester: Starting...")
        self.is_running = True
        
        while self.is_running:
            try:
                async with async_playwright() as p:
                    # Launch browser (headless=True for cloud)
                    self.browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
                    context = await self.browser.new_context(
                        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    )
                    
                    # Load Cookies
                    if self.current_cookies:
                        try:
                            cookies = json.loads(self.current_cookies)
                            await context.add_cookies(cookies)
                            print(f"🍪 Cloud Harvester: Loaded {len(cookies)} cookies.")
                        except json.JSONDecodeError:
                            print("❌ Cloud Harvester: Invalid JSON in cookies.")
                            self.current_cookies = None # Reset invalid cookies
                            await asyncio.sleep(10)
                            continue

                    self.page = await context.new_page()
                    
                    # Setup Request Interception
                    await self.page.route("**/*", self.handle_route)
                    
                    # Navigate to Vertex AI
                    print(f"☁️ Cloud Harvester: Navigating to {VERTEX_URL}...")
                    try:
                        await self.page.goto(VERTEX_URL, timeout=60000, wait_until="domcontentloaded")
                    except Exception as e:
                        print(f"❌ Cloud Harvester: Navigation failed: {e}")
                    
                    # Inner Loop (Session)
                    self.restart_requested = False
                    while self.is_running and not self.restart_requested:
                        # Check for Login Redirection (Cookie Expiry)
                        if "accounts.google.com" in self.page.url or "Sign in" in await self.page.title():
                            print("❌ Cloud Harvester: Cookies Expired or Invalidated by Google (Login Page Detected).")
                            print("   👉 Please export fresh cookies from your browser and update the GOOGLE_COOKIES variable.")
                            # Stop trying to harvest to avoid account lock
                            break

                        # Check if we need to harvest (e.g., every 45 minutes or if credentials are missing)
                        if time.time() - self.last_harvest_time > 2700 or not self.cred_manager.latest_harvest:
                            await self.perform_harvest()
                        
                        await asyncio.sleep(10) # Check every 10 seconds
                    
                    # If we broke out of inner loop, close browser to restart or stop
                    await self.browser.close()
                    if self.restart_requested:
                        print("♻️ Cloud Harvester: Restarting with new cookies...")

            except Exception as e:
                print(f"❌ Cloud Harvester Error: {e}")
                print("♻️ Cloud Harvester: Crashed. Restarting in 10s...")
                await asyncio.sleep(10)
        
        print("☁️ Cloud Harvester: Stopped.")

    async def handle_route(self, route):
        request = route.request
        
        # Check if this is the target request
        if "batchGraphql" in request.url and request.method == "POST":
            try:
                post_data = request.post_data
                if post_data and ("StreamGenerateContent" in post_data or "generateContent" in post_data):
                    print("🎯 Cloud Harvester: Captured Target Request!")
                    
                    # Extract Headers
                    headers = request.headers
                    
                    # Construct Harvest Data
                    harvest_data = {
                        "url": request.url,
                        "method": request.method,
                        "headers": headers,
                        "body": post_data
                    }
                    
                    # Update Credential Manager
                    self.cred_manager.update(harvest_data)
                    self.last_harvest_time = time.time()
                    
            except Exception as e:
                print(f"⚠️ Cloud Harvester: Error analyzing request: {e}")

        await route.continue_()

    async def perform_harvest(self):
        print("🤖 Cloud Harvester: Attempting to trigger request...")
        if not self.page:
            return

        try:
            # --- Popup Handling ---
            # Try to close common popups/dialogs that might block interaction
            print("🧹 Cloud Harvester: Checking for popups...")
            popup_selectors = [
                'button[aria-label="Close"]',
                'button[aria-label="Dismiss"]',
                'button:has-text("Got it")',
                'button:has-text("Not now")',
                'button:has-text("No thanks")',
                'button:has-text("Agree")', # Consent screens
                'div[role="dialog"] button:has-text("Close")',
                'div[role="dialog"] button:has-text("OK")',
                'button:has-text("Accept terms of use")' # Specific Terms button
            ]
            
            # Special handling for "Demo Terms of Use" checkbox (English & Chinese support)
            try:
                # 1. Try to scroll the dialog content to bottom
                dialog_content = 'div.mat-mdc-dialog-content'
                if await self.page.is_visible(dialog_content):
                    print("   - Scrolling terms dialog...")
                    await self.page.evaluate(f"document.querySelector('{dialog_content}').scrollTop = document.querySelector('{dialog_content}').scrollHeight")
                    await asyncio.sleep(0.5)

                # 2. Click Checkbox (Support EN: "Accept terms of use" and CN: "接受使用条款")
                # 使用逗号分隔选择器，表示“或”的关系
                terms_checkbox_selector = 'mat-checkbox:has-text("Accept terms of use"), mat-checkbox:has-text("接受使用条款")'
                
                if await self.page.is_visible(terms_checkbox_selector, timeout=2000):
                    print("   - Found Terms of Use checkbox (EN/CN). Clicking...")
                    # Try standard click first
                    try:
                        await self.page.click(terms_checkbox_selector, force=True, timeout=1000)
                    except:
                        # Fallback to JS click (Find the specific visible input)
                        print("   - Standard click failed, trying JS click...")
                        # 注意：这里需要定位到具体的 input 元素
                        await self.page.evaluate(f"""
                            const cb = document.querySelector('mat-checkbox:has-text("Accept terms of use") input') || document.querySelector('mat-checkbox:has-text("接受使用条款") input');
                            if(cb) cb.click();
                        """)
                     async def perform_harvest(self):
        print("🤖 Cloud Harvester: Attempting to trigger request...")
        if not self.page:
            return

        try:
            # ==========================================
            # 1. 处理“使用条款”弹窗 (Priority Handling)
            # ==========================================
            
            # 定义选择器 (支持中英文)
            terms_checkbox = 'mat-checkbox:has-text("Accept terms of use"), mat-checkbox:has-text("接受使用条款")'
            agree_btn = 'button:has-text("Agree"), button:has-text("同意")'
            dialog_content = 'div.mat-mdc-dialog-content' # 遮挡屏幕的元凶

            # 检测是否有弹窗内容
            if await self.page.is_visible(dialog_content):
                print("🧹 Cloud Harvester: Terms Dialog detected.")
                
                # 1.1 滚动到底部 (防止无法勾选)
                try:
                    await self.page.evaluate(f"document.querySelector('{dialog_content}').scrollTop = document.querySelector('{dialog_content}').scrollHeight")
                    await asyncio.sleep(0.5)
                except: 
                    pass

                # 1.2 勾选复选框
                if await self.page.is_visible(terms_checkbox):
                    print("   - Ticking checkbox...")
                    # 尝试 JS 点击 (更稳定)
                    await self.page.evaluate(f"""
                        const cb = document.querySelector('mat-checkbox:has-text("Accept terms of use") input') || document.querySelector('mat-checkbox:has-text("接受使用条款") input');
                        if(cb) cb.click();
                    """)
                    # 等待按钮变亮，这里很重要！
                    print("   - Waiting for Agree button to enable...")
                    await asyncio.sleep(2) 

                # 1.3 点击同意按钮
                if await self.page.is_visible(agree_btn):
                    print("   - Clicking Agree...")
                    # 使用 JS 强制点击，无视遮挡或禁用状态尝试触发
                    await self.page.evaluate(f"""
                        document.querySelectorAll('button:has-text("Agree"), button:has-text("同意")').forEach(b => {{
                            b.disabled = false; # 强制移除禁用属性(如果还在)
                            b.click();
                        }})
                    """)
                    
                    # 1.4 【关键】等待弹窗消失
                    print("   - Waiting for dialog to vanish...")
                    try:
                        await self.page.wait_for_selector(dialog_content, state='hidden', timeout=5000)
                        print("   - Dialog closed.")
                    except:
                        print("   ⚠️ Warning: Dialog might still be open, attempting to proceed...")

            # 处理其他杂项弹窗 (Close/OK/Got it)
            popup_selectors = [
                'button[aria-label="Close"]', 'button[aria-label="Dismiss"]',
                'button:has-text("Got it")', 'button:has-text("No thanks")',
                'div[role="dialog"] button:has-text("Close")', 'div[role="dialog"] button:has-text("OK")'
            ]
            for selector in popup_selectors:
                if await self.page.is_visible(selector):
                    await self.page.click(selector)
                    await asyncio.sleep(0.5)

            # ==========================================
            # 2. 发送文本 "Hello"
            # ==========================================
            
            # 定位输入框
            editor_selector = 'div[contenteditable="true"]'
            
            print("⏳ Cloud Harvester: Waiting for editor...")
            # 等待输入框变为可见且可操作
            await self.page.wait_for_selector(editor_selector, state="visible", timeout=10000)

            # 点击输入框 (使用 force=True 强行点击，即使上方还有透明遮挡)
            await self.page.click(editor_selector, force=True)
            
            # 清空并输入
            await self.page.evaluate(f"document.querySelector('{editor_selector}').innerText = ''")
            await self.page.fill(editor_selector, "Hello")
            await asyncio.sleep(0.5)
            
            print("🚀 Cloud Harvester: Sending 'Hello'...")
            await self.page.press(editor_selector, "Enter")
            
            # 等待捕获
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"❌ Cloud Harvester: Interaction failed: {e}")
            # 如果失败，截图保存以便调试 (可选，如果运行在本地)
            # await self.page.screenshot(path="error_screenshot.png")

            for selector in popup_selectors:
                try:
                    if await self.page.is_visible(selector, timeout=500):
                        print(f"   - Closing popup: {selector}")
                        await self.page.click(selector)
                        await asyncio.sleep(1)
                except:
                    pass
            # ----------------------

            # Wait for editor
            editor_selector = 'div[contenteditable="true"]'
            try:
                await self.page.wait_for_selector(editor_selector, timeout=10000)
            except:
                print("⚠️ Cloud Harvester: Editor not found. Reloading page...")
                await self.page.reload(wait_until="domcontentloaded")
                await asyncio.sleep(5)
                return

            # Type "Hello"
            await self.page.click(editor_selector)
            await self.page.fill(editor_selector, "Hello")
            await asyncio.sleep(1)
            
            # Press Enter
            await self.page.press(editor_selector, "Enter")
            print("🚀 Cloud Harvester: Sent 'Hello' message.")
            
            # Wait a bit to ensure request is captured
            await asyncio.sleep(5)
            
        except Exception as e:
            print(f"❌ Cloud Harvester: Interaction failed: {e}")
