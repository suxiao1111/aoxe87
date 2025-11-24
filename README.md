---
title: Vertex AI Proxy
emoji: 🚀
colorFrom: blue
colorTo: purple
sdk: docker
pinned: false
app_port: 7860
---

# Vertex AI Headful Proxy

这是一个基于 Python 和 浏览器脚本（Userscript）的 Vertex AI 代理工具。它允许你通过 OpenAI 兼容接口（API）调用 Google Vertex AI 的强大模型（如 Gemini 1.5 Pro, Gemini 2.0 Flash 等），利用浏览器已登录的会话进行认证。

**支持本地运行和云端部署（如 Hugging Face Spaces）。**

> **⚠️ 部署模式说明**：
> 本项目支持两种凭证获取模式：
> 1.  **本地浏览器模式 (推荐)**: 在本地浏览器安装油猴脚本，通过 WebSocket 将凭证推送到云端。最稳定，不易被 Google 风控。
> 2.  **云端自动模式 (实验性)**: 在云端直接运行无头浏览器，通过注入 Cookies 自动获取凭证。无需本地浏览器参与，但可能面临 IP 风控或验证码挑战。

## ✨ 功能特点

*   **OpenAI 格式兼容**: 提供标准的 `/v1/chat/completions` 接口，可直接接入 NextChat, Chatbox, LobeChat 等常见 AI 客户端。
*   **自动凭证获取**: 通过 Tampermonkey 脚本自动从浏览器抓取 Vertex AI Studio 的请求头和 Token。
*   **自动保活与刷新**: 支持自动检测 Token 过期并触发浏览器刷新 Token，实现长时间稳定运行。
*   **图片生成**: 支持调用 Imagen 或 Gemini 的画图能力（通过 `-1k`, `-**高级特性支持**:
    *   **思考模式 (Thinking Mode)**: 支持 Gemini 的思考过程（通过 `-low` 或 `-high` 后缀触发）。

## 🛠️ 安装指南

### 1. 后端环境准备

#### 方式 A: 本地运行

1.  确保安装2k`, `-4k` 后缀触发）。
*   **可视化界面**: 提供简洁的 GUI 界面查看实时请求统计、Token 消耗（仅限本地模式）。
*   **多模型支持**: 支持 `models.json` 中配置的多种 Gemini 模型，包括最新的预览版。
*    Python 3.9+。
2.  克隆本项目。
3.  安装依赖：
    ```bash
    pip install -r requirements.txt
    ```
4.  运行：
    ```bash
    python main.py
    ```

#### 方式 B: 云端部署 (Hugging Face Spaces / GitHub)

**推荐使用 GitHub 同步部署，方便后续更新。**

1.  **推送到 GitHub**:
    *   在 GitHub 创建一个新的仓库（例如 `vertex-proxy`）。
    *   将本项目代码推送到该仓库。
    *   确保仓库包含 `Dockerfile`。

2.  **连接 Hugging Face Space**:
    *   在 Hugging Face 创建一个新的 Space。
    *   **Space Name**: 起个名字。
    *   **License**: MIT。
    *   **SDK**: 选择 **Docker**。
    *   **Create Space** 后，在页面上方找到 "Files" 旁边的 **Settings**。
    *   向下滚动找到 **Git / Docker** 部分，或者直接在创建时选择 "Sync from GitHub"（如果有该选项）。
    *   如果没有直接同步选项，你可以使用 GitHub Actions，或者最简单的方式：**直接在 Space 页面选择 "Docker" SDK，然后它会提供一个 Git 地址，你直接把代码 push 到 Hugging Face 的 Git 地址即可（如上方 README 之前所述）。**
    
    *(更正：Hugging Face Space 原生支持直接作为 Git 仓库。如果你想从 GitHub 同步，通常使用 GitHub Actions 或手动 Push。最简单的方法是直接把 HF Space 当作你的远程仓库)*

    **最佳实践 (GitHub -> HF Space)**:
    1.  本项目已包含 `.github/workflows/sync_to_hub.yml` 文件。
    2.  你需要修改该文件最后一行，将 `YOUR_USERNAME/YOUR_SPACE_NAME` 替换为你实际的 Hugging Face Space 地址（例如 `my-user/vertex-proxy`）。
    3.  在 GitHub 仓库的 **Settings -> Secrets and variables -> Actions** 中，添加一个 Secret：
        *   Name: `HF_TOKEN`
        *   Value: 你的 Hugging Face Access Token (需有 Write 权限，在 HF 个人设置中获取)。
    4.  之后每次你 push 代码到 GitHub，它会自动同步部署到 Hugging Face Space。

    > **注意**: 不需要创建 GHCR 或 Docker Hub 镜像。Hugging Face 会根据仓库中的 `Dockerfile` 自动构建。

3.  **环境变量配置 (Settings -> Variables)**:
    *   `API_KEY`: (可选) 接口密钥。
    *   `GOOGLE_COOKIES`: (可选) 仅用于云端自动模式。

### 2. 前端脚本安装 (仅本地浏览器模式需要)

你需要一个支持用户脚本的浏览器扩展，推荐 **Tampermonkey** (油猴)。

1.  在浏览器中安装 Tampermonkey 扩展。
2.  点击 Tampermonkey 图标 -> "添加新脚本"。
3.  将 `vertex-ai-harvester.user.js` 文件的内容全部复制并粘贴到编辑器中。
4.  保存脚本 (Ctrl+S)。

## 🚀 使用教程

### 模式一：本地浏览器模式 (推荐)

此模式下，你需要保持本地浏览器打开，并通过油猴脚本将凭证推送到云端。

1.  **配置脚本**:
    *   打开 Google Vertex AI Studio 页面。
    *   点击左下角 "Vertex AI Harvester" 面板的 ⚙️ 图标。
    *   输入云端 WebSocket 地址: `wss://你的应用域名.hf.space/ws`。
2.  **获取凭证**:
    *   在 Vertex AI Studio 对话框中发送任意消息（如 "Hello"）。
    *   脚本会自动拦截并推送到云端。
3.  **连接使用**:
    *   API 地址: `https://你的应用域名.hf.space/v1`

### 模式二：云端自动模式 (实验性)

此模式下，云端会自动运行浏览器获取凭证，无需本地干预。

**⚠️ 局限性警告 (必读)**:
*   **无法自动登录**: 云端脚本**无法**自动输入账号密码登录。
*   **免登录模式 (实验性)**: 最新版本尝试在无 Cookies 情况下直接访问。如果 Google 允许匿名访问 Vertex AI Studio (极少见情况) 或仅需关闭弹窗，此模式可能奏效。
*   **Cookie 易失效**: 如果必须登录，Google 的 Cookies 对 IP 敏感。从本地 IP 切换到云端 IP，极易导致 Cookies 立即失效。

**结论**: 除非你非常熟悉如何维持 Google Cookies 的活性，否则**强烈推荐使用模式一（本地浏览器模式）**。

1.  **获取 Cookies (可选)**:
    *   在本地浏览器安装 "EditThisCookie" 或类似插件。
    *   登录 Google Cloud Console。
    *   导出 Cookies 为 JSON 格式。
2.  **配置环境变量**:
    *   在 Hugging Face Space 设置中，添加变量 `GOOGLE_COOKIES`。
    *   将导出的 JSON 字符串粘贴进去。
3.  **重启 Space**:
    *   Space 重启后，后台会自动启动浏览器并尝试获取凭证。
    *   查看 Space 的 Logs，如果看到 `☁️ Cloud Harvester: Captured Target Request!` 即表示成功。

#### 🍪 如何更新失效的 Cookies (热更新)

当日志提示 Cookies 失效时，你无需重启 Space：
1.  访问 `https://你的应用域名.hf.space/admin`。
2.  在文本框中粘贴新的 Cookies JSON。
3.  输入 API Key (如果设置了的话)。
4.  点击 **Update Cookies**，后台浏览器会自动重启并应用新 Cookies。

### 第三步：连接客户端

现在你可以使用任何支持 OpenAI 接口的客户端连接了。

*   **Base URL (接口地址)**: 
    *   本地: `http://127.0.0.1:28880/v1`
    *   云端: `https://你的应用域名.hf.space/v1`
*   **API Key**: 
    *   本地: 任意填写
    *   云端: 填写你在环境变量 `API_KEY` 中设置的值。
*   **Model (模型)**: 输入你想使用的模型名称，例如 `gemini-1.5-pro` 或 `gemini-2.0-flash-exp`。

## ⚙️ 高级用法

### 思考模式 (Thinking Mode)
对于支持思考的模型（如 Gemini 2.0 Flash Thinking），你可以通过以下方式触发：
*   **后缀法**: 在模型名后添加 `-low` (8k budget) 或 `-high` (32k budget)。
    *   例如: `gemini-2.0-flash-thinking-exp-low`
*   **参数法**: 设置 `max_tokens` 参数。代理会自动将其识别为思考预算。

### 图片生成
使用支持图片生成的模型时，可以通过后缀指定分辨率：
*   `-1k`: 1024x1024
*   `-2k`: 2048x2048 (如果模型支持)
*   例如: `gemini-2.5-flash-image-1k`

### 模型列表配置
你可以在 `models.json` 中修改或添加支持的模型列表和别名映射。

## ❓ 常见问题

**Q: 为什么提示 "Credentials might be stale"?**
A: Google 的 Token 有效期较短（通常 1 小时）。代理会自动尝试通过 WebSocket 通知浏览器刷新页面来获取新 Token。请保持浏览器中 Vertex AI Studio 页面处于打开状态。

**Q: 部署在 Hugging Face 上连接不上 WebSocket？**
A: 请确保脚本设置中的地址是 `wss://` 开头，并且包含 `/ws` 路径。例如 `wss://my-app.hf.space/ws`。

**Q: 如何在局域网其他设备使用？**
A: 代理默认监听 `0.0.0.0`，你可以使用运行代理电脑的局域网 IP 地址来访问。

## ⚠️ 免责声明

本项目仅供学习和研究使用。请遵守 Google Cloud Platform 的服务条款。不要将此工具用于非法用途。
