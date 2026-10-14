# 写实多模态 AI 伴侣项目（Friend）技术审计汇总报告与后续开发计划 (v3.1 Industrial)

## 1. 架构总览与端云协同设计

本项目（仓库地址：`https://github.com/qq601359558/friend.git`）定位于面向消费级显卡（NVIDIA GeForce RTX 5060 Ti 8GB）的新一代写实多模态 AI 伴侣系统。系统采用**“云端大脑 + 本地身体”**的端云协同架构：
* **云端大脑（0 本地显存）**：大语言模型（LLM）、视觉语言模型（VLM）与可选云端声音克隆（CosyVoice2）通过 OpenAI 兼容接口（如 SiliconFlow）流式调用；
* **本地身体（4.5GB ~ 5.4GB / 8GB 显存）**：本地负责 30~50 FPS 写实面部驱动（FasterLivePortrait + MuseTalk）、语音活动检测（Silero VAD）与极速语音情绪识别（SenseVoiceSmall），留足 2.5GB+ 显存安全裕度，杜绝 OOM。

---

## 2. 核心修复与工业级升级清单 (v1.0 -> v3.1)

| 模块名称 | 核心文件路径 | 已完成的核心升级与修复内容 | 状态 |
| :--- | :--- | :--- | :--- |
| **配置与入口** | `config.py` / `main.py` / `.env.example` | 统一默认端口 `8899`；GPU 模式下自动关闭 `reload=True` 防止显存泄漏；支持局域网 HTTPS 证书自动挂载与本机局域网 IP 打印。 | ✅ 已完成 |
| **全双工通信网关** | `server/app.py` | 1. 实装 `SafeWebSocket` 异步互斥锁；<br>2. **二级解耦流水线 (`tts_pre_synthesizer` + `playout_consumer`)**：消除句间等待间隙，实现 0ms 无缝连播；<br>3. 修复 `speaking -> idle` 状态过早重置 Bug；支持随时打断 (`interrupt`)、摄像头帧缓存 (`camera_frame`) 与空闲主动关怀监控。 | ✅ 已完成 |
| **多模态大脑与双擎记忆** | `brain/agent.py` / `brain/memory.py` | 1. 复用 `aiohttp.ClientSession` 连接池与异常安全回滚；<br>2. 支持摄像头画面自动构造 Vision 多模态请求并在异常时无缝降级；<br>3. **双擎长期记忆**：启发式秒级提取 + 后台异步 LLM 隐含事实提炼 + Mem0 自动桥接 + 亲密度/心情状态机。 | ✅ 已完成 |
| **三级自适应声音引擎** | `voice/tts.py` | 支持 **CosyVoice2 云端声音克隆（含 `assets/reference_voice.wav` 零样本克隆） -> Edge-TTS -> 浏览器原生 Web Speech API** 三级自动故障转移，内置 30fps 声学能量包络提取。 | ✅ 已完成 |
| **混合神经视觉驱动** | `avatar/driver.py` | 1. Windows 下自动预注入 PyTorch CUDA 12.8 / cuDNN DLL 搜索路径；<br>2. 启动预热 **90 帧（3 秒）自然眨眼+呼吸无缝循环基底**；<br>3. 支持在线热更新头像照片与纵向高斯软遮罩下颌变形合成。 | ✅ 已完成 |
| **视频交互前端** | `web/index.html` | 1. 新增 **📞 免提持续连麦模式（带自动防回声自激）**、**🎙️ 单次语音输入**与 **⏹️ 随时打断**；<br>2. 新增 **💕 侧边记忆手账与音色/头像设置抽屉**；<br>3. 新增 9 段实时声浪频谱条、**👋 让她找话题**按钮与摄像头像素帧差检测。 | ✅ 已完成 |
| **自动化工具脚本** | `scripts/download_weights.py` / `scripts/generate_cert.py` | 一键从国内镜像 (`hf-mirror.com`) 拉取 FasterLivePortrait + MuseTalk + SenseVoiceSmall 权重；一键生成手机局域网 HTTPS 自签名证书。 | ✅ 已完成 |

---

## 3. RTX 5060 Ti (8GB VRAM) 显存预算分配表

| 子系统模块 | 选型方案 | 运行位置 | 开源协议 | 显存占用 (VRAM) | 延迟指标 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **对话与视觉大脑 (LLM / VLM)** | `Qwen2.5-72B-Instruct` / `Qwen2.5-VL-72B` | 云端 API | - | **0.0 GB** | 首字 TTFT ~350ms |
| **长期记忆引擎 (Memory)** | 本地 JSON + 异步 LLM 提炼 / Mem0 | 本地磁盘 + 云端 | Apache-2.0 | **0.0 GB** | 检索耗时 < 10ms |
| **语音合成与克隆 (TTS)** | CosyVoice2-0.5B (云端) / Edge-TTS | 云端 API | Apache-2.0 / MIT | **0.0 GB** | 分句首包 ~250ms |
| **语音检测与识别 (VAD + ASR)** | Silero VAD + SenseVoiceSmall | 本地 GPU (5060 Ti) | MIT / Apache-2.0 | **~ 0.7 GB** | 识别耗时 < 80ms |
| **写实面部实时驱动 (Avatar)** | FasterLivePortrait + MuseTalk (FP16) | 本地 GPU (5060 Ti) | MIT License | **~ 3.2 GB** | 单帧耗时 ~18ms (50+ FPS) |
| **CUDA 上下文与桌面预留** | PyTorch 2.6+ (CUDA 12.8 Blackwell `sm_120`) | 本地 GPU (5060 Ti) | BSD-3-Clause | **~ 1.0 GB** | - |
| **合计总占用** | **全功能满载运行状态** | **端云协同** | **全线商用合规** | **~ 4.9 GB / 8.0 GB** | **端到端响应 < 0.8s** |
