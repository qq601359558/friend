# 🤖 Antigravity 智能体接力开发手册 (Agent Handover Brief)

> **致接棒的 Antigravity 智能体**：  
> 请仔细阅读本文件。本项目为**新一代写实多模态 AI 伴侣系统**，当前已完成全套前后端基础设施搭建，已通过轻量模式验证。你的任务是在**宿主机的 RTX 5060 Ti (8GB) 显卡环境**下，接棒完成真正的 **LivePortrait 神经面部驱动实装**及后续多模态闭环。

---

## 1. 项目愿景与设计哲学

* **写实、真实、有生命感**：拒绝千篇一律的二次元萌妹或僵硬的 3D 塑料建模，面向写实真人风格；
* **非顺从的真实伴侣**：人设有自己的情绪与边界，具备共同记忆感与日常感，不使用“有什么可以帮您”等客服腔；
* **全双工高频交互**：低延迟语音对话 + 双向注视（她能通过前置摄像头看见你）+ 实时对口型微表情（LivePortrait）。
* **开源版权合规**：所有引用的第三方开源技术**严格采用 MIT / Apache 2.0 / BSD 宽松协议**，杜绝 CC-BY-NC（禁止商用）版权雷区。

---

## 2. 目标硬件与架构决策（关键约束）

* **宿主机硬件**：**NVIDIA GeForce RTX 5060 Ti (8GB VRAM)**，Blackwell 架构，算力强劲但显存受限于 8GB。
* **核心架构策略：端云协同（云端大脑 + 本地身体）**：
  * **大脑 (LLM / VLM)**：走云端 API（如 DeepSeek-Flash / 通义千问），**0 本地显存**；
  * **面部驱动 (Avatar)**：由 5060 Ti 本地运行 **LivePortrait**（占用约 2.5GB 显存，跑满 40~60 FPS）；
  * **声音引擎 (TTS)**：由 5060 Ti 本地运行轻量模型或 Edge-TTS（占用 0~1.5GB 显存）；
  * **显存总预算**：控制在 **4.5GB ~ 5.5GB / 8GB**，留足 2.5GB+ 安全冗余，**严禁爆显存 (OOM)**。

---

## 3. 当前已完成的进展 (Current State)

代码仓库：`https://github.com/qq601359558/friend.git`

| 模块 | 文件路径 | 当前状态与实现细节 |
| :--- | :--- | :--- |
| **配置中心** | `config.py` / `.env` | 支持动态端口、环境自动嗅探、路径修复（已自动适配全局 Python 路径）。 |
| **大脑智能体** | `brain/agent.py` | 基于 `aiohttp` 的流式 OpenAI 兼容对话客户端，已成功联调 DeepSeek-Flash。 |
| **声音引擎** | `voice/tts.py` | 支持 `edge-tts` 高保真音色，具备**浏览器原生 Web Speech API 优雅降级兜底**。 |
| **通信服务** | `server/app.py` | 基于 FastAPI + WebSocket，挂载了 `/static` 与 `/assets`，具备字幕/状态/音频全双工传输。 |
| **视频交互前端** | `web/index.html` | FaceTime / 视频通话风格 UI；已实现**微呼吸起伏、鼠标视线 2.5D 跟随、说话微动态、双向画中画摄像头**。 |
| **形象资产** | `assets/default_avatar.jpg` | 用户已放置初始写实头像素材。 |
| **硬件驱动接口** | `avatar/driver.py` | **【待接棒实装】** 当前为骨架接口，预留了 `MockAvatarDriver` 与 `LivePortraitDriver`。 |

---

## 4. 接棒智能体的即刻开发任务清单 (Next Tasks)

当你（新 Antigravity）接手后，请按以下优先级继续推进：

### 🎯 任务一：在 5060 Ti 上实装 `LivePortraitDriver`（最高优先级）
1. 在 `avatar/driver.py` 中引入真正的 LivePortrait 管道；
2. 引导用户或自动运行脚本下载 LivePortrait 预训练权重（推荐通过 HuggingFace / ModelScope 镜像）；
3. 实现根据输入的语音音频流（或音素特征），实时以 30fps 生成面部对口型与眨眼视频帧（通过 WebRTC 或 WebSocket 发送到前端），将前端静态展示彻底替换为**实时渲染视频流**。

### 🎯 任务二：实现“双向看见你”多模态感知闭环
1. 前端 `web/index.html` 的画中画摄像头目前已能采集视频流；
2. 增加定时抽帧（每 2~3 秒抽取 1 帧压缩 JPEG）通过 WebSocket 上传至后端；
3. 将画面送入多模态模型（如 Qwen2-VL 或 Gemini Live API），使伴侣能够在对话中主动感知用户的表情、动作与穿着。

### 🎯 任务三：集成长期记忆图谱 (Mem0)
1. 引入开源宽松协议的长期记忆库（如 `mem0ai`，基于 SQLite 存储）；
2. 自动在后台提取每次对话中用户提到的重要事实、偏好与情感纪念日，使关系具备不可替代的成长性。

---

## 5. 新环境启动与检验命令

```powershell
# 1. 克隆代码
git clone https://github.com/qq601359558/friend.git
cd friend

# 2. 复制配置并填入 API Key
copy .env.example .env

# 3. 安装依赖（5060 Ti 环境请安装 GPU 依赖）
pip install -r requirements-gpu.txt

# 4. 启动服务（默认端口 8899）
python main.py
```

---

## 6. 用户给新 Agent 的唤醒 Prompt（请复制使用）

用户只需要对新环境的 Antigravity 发送以下这句话：

> **“你好 Antigravity，我已经阅读了仓库中的 `AGENT_HANDOVER.md`。当前机器已配备 RTX 5060 Ti 显卡环境，请阅读该文件，接着之前的架构思路，帮我实装 `avatar/driver.py` 中的 LivePortrait 实时视频驱动引擎！”**
