# 🌟 AI 时代伴侣系统 (写实视频交互版)

这是一个面向下一代人机情感陪伴的开源架构系统，支持**全双工语音**、**双向摄像头互看**、**长程记忆人设**与**写实面部实时渲染**。

---

## 🚀 当前状态：服务已在本地启动！

你可以直接在浏览器中打开：
👉 **http://localhost:8899**

### 💻 当前模式（轻量调试模式 / 0显存占用）
* **大模型思考**：默认已内置离线女友模拟回复（配置 `.env` 填入 API Key 即可切换为通义千问 / DeepSeek 真实智能体）。
* **声音引擎**：集成流式 TTS 与浏览器原生语音双重冗余，输入文字即可出声。
* **双向感知**：网页右上角支持一键开启前置摄像头画中画。

---

## 📁 项目目录结构

```text
d:\codex\friend\
├── .env                  # 核心配置（API Key、伴侣姓名、运行模式、端口）
├── config.py             # 系统统一配置中心
├── main.py               # 服务启动入口
├── brain/                # 大脑与情感对话核心
│   └── agent.py          # OpenAI 兼容协议流式对话代理
├── voice/                # 声音合成引擎
│   └── tts.py            # 高保真自然女声输出
├── avatar/               # 视觉形象驱动
│   └── driver.py         # 支持 Mock 调试与 LivePortrait 5060 Ti 硬件驱动
├── server/               # 通信网关 (FastAPI + WebSocket)
│   └── app.py            # 全双工音视频与字幕流中枢
└── web/                  # 前端交互终端
    └── index.html        # 视频通话风格 UI (支持画中画摄像头)
```

---

## 🔑 开启真强大脑（配置 API Key）

用记事本或编辑器打开 `d:\codex\friend\.env`：

```bash
# 示例：使用 SiliconFlow（免费赠送大量额度）
LLM_API_BASE=https://api.siliconflow.cn/v1
LLM_API_KEY=sk-xxxx你的API密钥
LLM_MODEL=Qwen/Qwen2.5-7B-Instruct

# 伴侣名字与用户称谓
AI_NAME=星晚
USER_NAME=你
```

保存后，服务会自动热重载（无需手动重启），之后她就会以极高情商与你深度聊天。

---

## 🏠 回家部署到 RTX 5060 Ti (8GB) 的操作指南

当你回到家，坐在 5060 Ti 台式机前时：

1. **复制代码库**：直接将 `d:\codex\friend` 文件夹拷贝（或 Git push/pull）到家里的 5060 Ti 主机上。
2. **安装 GPU 渲染依赖**：
   ```powershell
   cd friend
   pip install -r requirements-gpu.txt
   ```
3. **切换为硬件驱动模式**：
   在 `.env` 中修改：
   ```bash
   AVATAR_MODE=liveportrait
   ```
4. **准备形象照片**：
   在 `assets/default_avatar.jpg` 放入一张你中意的写实真人正面照片。
5. **启动服务**：
   ```powershell
   python main.py
   ```
   5060 Ti 的 Blackwell 核心将全力以 30~50 FPS 实时渲染逼真的人脸微表情视频流推送到你的浏览器窗口！
