# 🌟 AI 时代伴侣系统 (写实视频交互版 v2.0)

这是一个面向下一代人机情感陪伴的开源架构系统，支持**低延迟分句流式语音**、**🎙️ 麦克风语音对话与随时打断**、**👀 双向摄像头互看（多模态视觉感知）**、**💕 本地持久化长程记忆与亲密度系统**，以及**面向 RTX 5060 Ti (8GB) 的写实面部实时渲染**。

---

## 🚀 快速启动（笔记本轻量模式 / 0显存占用）

1. **安装基础依赖**：
   ```powershell
   pip install -r requirements.txt
   ```
2. **配置文件初始化**：
   ```powershell
   copy .env.example .env
   ```
   *(注：即使暂不填写 `LLM_API_KEY`，系统也内置了带视觉与记忆反馈的高情商离线调试回复，开箱即用！)*
3. **启动服务**：
   ```powershell
   python main.py
   ```
4. **打开浏览器访问**：
   👉 **http://localhost:8899**

---

## ✨ v2.0 核心能力亮点

* **流式分句超低延迟语音**：大模型一边思考吐字，后端一边按标点切分短句并发合成语音推送至前端音频队列无缝连播，首字出声延迟缩短 60% 以上。
* **全双工语音输入与随时打断 (Barge-in)**：点击底部 `🎙️` 按钮可直接开口说话（基于浏览器原生语音识别），或随时点击 `⏹️ 打断` 停止伴侣当前播报。
* **“双向看见你”多模态感知**：点击底部 `📹` 开启右上角画中画摄像头后，前端每 2.5 秒自动抽帧同步给后端缓存；当你说话时自动携带画面送入多模态视觉大模型（`VLM_MODEL`），让她真正看见你的表情与穿搭。
* **零显存持久化长期记忆 (`brain/memory.py`)**：自动从日常对话中提取并记住你的名字、饮食喜好、禁忌与重要纪念日（持久化保存在 `data/companion_memory.json`），实时更新顶部的**亲密度**与**当前心情**。
* **声浪光晕与 2.5D 视线跟随**：提取 30fps 音频能量包络实时驱动说话光晕与面部微动，并将呼吸起伏动画与鼠标 2.5D 视差分离，交互丝滑不冲突。

---

## 📁 项目目录结构

```text
friend/
├── .env.example          # 配置模板（统一默认端口 8899，含 LLM / VLM / TTS 配置）
├── config.py             # 系统统一配置中心
├── main.py               # 服务启动入口（自动根据运行模式管理热重载以防显存泄漏）
├── AGENT_HANDOVER.md     # 智能体接力开发手册 (v2.0)
├── brain/                # 大脑、多模态视觉与长期记忆核心
│   ├── agent.py          # 支持图文多模态、连接池复用与异常安全回滚的流式对话代理
│   └── memory.py         # 零显存本地持久化长期记忆与好感度/心情状态机
├── voice/                # 声音合成与声学包络引擎
│   └── tts.py            # 高保真自然女声输出 + 30fps 音频能量包络提取
├── avatar/               # 视觉形象驱动
│   └── driver.py         # 支持 Mock 声学包络驱动与 RTX 5060 Ti 实时视频帧渲染
├── scripts/              # 自动化工具脚本
│   └── download_weights.py # 一键从国内镜像拉取 FasterLivePortrait + MuseTalk 权重
├── server/               # 通信网关 (FastAPI + WebSocket)
│   └── app.py            # 流式分句 TTS 队列、打断控制、摄像头帧缓存与记忆 API
└── web/                  # 前端交互终端
    └── index.html        # 视频通话 UI (含音频队列、麦克风输入、摄像头抽帧与 2.5D 视差)
```

---

## 🏠 回家部署到 RTX 5060 Ti (8GB) 的操作指南

1. **安装 Blackwell (CUDA 12.8) 专属 GPU 依赖**：
   ```powershell
   pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
   pip install -r requirements-gpu.txt
   ```
2. **一键下载开源预训练模型权重**：
   ```powershell
   python scripts/download_weights.py
   ```
3. **切换为硬件驱动模式**：
   在 `.env` 中修改：
   ```bash
   AVATAR_MODE=liveportrait
   ```
4. **启动服务**：
   ```powershell
   python main.py
   ```
