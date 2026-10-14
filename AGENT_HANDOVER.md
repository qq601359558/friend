# 🤖 Antigravity 智能体接力开发手册 (Agent Handover Brief v3.0 Industrial Edition)

> **致接棒的 Antigravity 智能体**：  
> 请仔细阅读本文件。本项目为**新一代写实多模态 AI 伴侣系统（Industrial v3.0 工业级全双工版）**，当前已完成全套二级解耦流式音视频管线、免提连麦防回声交互、双向摄像头运动感知、空闲主动关怀引擎以及“规则+异步LLM”双擎长期记忆系统的实装验证。你的任务是在**宿主机的 RTX 5060 Ti (8GB) 显卡环境**下，运行权重拉取脚本并完成 **FasterLivePortrait + MuseTalk 实时神经面部渲染算子**的最终硬件联调。

## 1. 项目愿景与设计哲学

* **写实、真实、有生命感**：拒绝千篇一律的二次元萌妹或僵硬的 3D 塑料建模，面向写实真人风格；
* **非顺从的真实伴侣**：人设有自己的情绪与边界，具备共同记忆感（亲密度、心情状态机与可视化记忆手账）与主动关怀意识，不使用“有什么可以帮您”等客服腔；
* **工业级全双工高频交互**：二级解耦预合成流式语音（句间 0ms 卡顿）+ 📞 免提持续连麦（带自动防回声自激）+ 随时语音打断 (Barge-in) + 👀 双向注视与超时主动找话题；
* **开源版权合规**：所有引用的第三方开源技术**严格采用 MIT / Apache 2.0 / BSD 宽松协议**，杜绝 CC-BY-NC（禁止商用）版权雷区。

## 2. 目标硬件与架构决策（关键约束）

* **宿主机硬件**：**NVIDIA GeForce RTX 5060 Ti (8GB VRAM)**，Blackwell 架构（`sm_120`），算力强劲但显存受限于 8GB。
* **核心架构策略：端云协同（云端大脑 + 本地身体）**：
  * **大脑 (LLM / VLM)**：走云端 OpenAI 兼容 API（如 SiliconFlow 的 `Qwen2.5-7B-Instruct` 与 `Qwen2.5-VL-72B-Instruct`），**0 本地显存**；
  * **双擎长期记忆 (Memory)**：本地原子化 JSON 持久化 + 后台异步非阻塞 LLM 隐含事实提炼 + 自动探测桥接 [Mem0](https://github.com/mem0ai/mem0)，**0 本地显存**；
  * **面部驱动 (Avatar)**：原版 [LivePortrait](https://github.com/KlingAIResearch/LivePortrait) 仅支持视频驱动而无音频输入分支，因此在 5060 Ti 上采用 **[FasterLivePortrait](https://github.com/warmshao/FasterLivePortrait)（90 帧预计算眨眼/呼吸循环基底）+ [MuseTalk](https://github.com/TMElyralab/MuseTalk)（实时潜空间音频嘴型重绘）** 组合（FP16 占用约 2.8~3.2GB 显存，跑满 40~60 FPS）；
  * **声音引擎 (TTS & ASR)**：支持 `edge-tts` 二级预合成队列（0 显存）及前端免提连麦；5060 Ti 本地可选装 [Silero VAD](https://github.com/snakers4/silero-vad) + [SenseVoiceSmall](https://github.com/QwenAudio/SenseVoice)（占用约 0.6GB 显存）；
  * **显存总预算**：控制在 **4.5GB ~ 5.4GB / 8GB**，留足 2.5GB+ 安全冗余，**严禁爆显存 (OOM)**。

## 3. 当前已完成的进展 (Current State v3.0 Industrial)

代码仓库：`https://github.com/qq601359558/friend.git`

| 模块 | 文件路径 | v3.0 工业级状态与实现细节 |
| :--- | :--- | :--- |
| **配置中心** | `config.py` / `.env.example` | 统一默认端口 `8899`，支持 `LLM_MODEL`、`VLM_MODEL`、`EMBEDDING_MODEL`、`PROACTIVE_IDLE_SECONDS`（空闲主动关怀阈值）与显存预算红线配置。 |
| **大脑与双擎记忆** | `brain/agent.py` / `brain/memory.py` | 1. 复用 `aiohttp.ClientSession` 连接池与异常安全回滚；<br>2. **双擎长期记忆**：启发式秒级提取 + **后台异步 LLM 隐含事实提炼**（自动捕捉口语中的身体状况、禁忌与约定）+ Mem0 自动桥接；<br>3. **主动关怀流 (`proactive_stream`)**：支持结合静默时长与摄像头画面主动开口关心用户。 |
| **二级解耦通信网关** | `server/app.py` | 1. **`SafeWebSocket` 并发互斥锁**：杜绝高频推送文本、音频与视频帧时的底层 Socket 竞争；<br>2. **二级解耦流水线 (`tts_pre_synthesizer` + `playout_consumer`)**：播放第一句视频帧的同时后台全速预合成后续句子，实现句间 **0ms 无缝连播**；<br>3. **空闲主动关怀监控协程** + 记忆增删改查 REST API（`/api/memory/add`, `DELETE /api/memory/{idx}`）。 |
| **混合神经视觉驱动** | `avatar/driver.py` / `scripts/download_weights.py` | 1. **启动预计算 90 帧（3 秒）自然眨眼+呼吸无缝循环基底**，大幅降低实时计算开销；<br>2. 自动探测 `ONNXRuntime-GPU` (`TensorrtExecutionProvider` / `CUDAExecutionProvider`) 与 PyTorch CUDA 显存余量；<br>3. 未下载深度学习权重时内置**高斯软遮罩下颌变形合成器**，开箱输出平滑 30fps 视频流。 |
| **工业级视频前端** | `web/index.html` | 1. **📞 免提持续连麦模式**（伴侣说话时自动静音防回声自激，说完 250ms 自动恢复倾听）；<br>2. **💕 侧边记忆手账抽屉**（可视化查看、手动新增、单条删除共同记忆及查看渲染引擎遥测状态）；<br>3. **实时声浪频谱条**、**👋 一键主动找话题按钮**与**摄像头像素帧差（Motion Diff）智能检测**。 |

## 4. 接棒智能体的 RTX 5060 Ti 硬件联调清单 (Next Tasks)

当你（新 Antigravity）在配备 **RTX 5060 Ti (8GB)** 的宿主机接手后，请按以下步骤完成最终 GPU 算子联调：

### 🎯 任务一：配置 Blackwell (CUDA 12.8) 环境并拉取预训练权重
1. 安装支持 RTX 5060 Ti (`sm_120`) 的 PyTorch 2.6+ (CUDA 12.8)：
   ```powershell
   pip install --pre torch torchvision torchaudio --index-url https://download.pytorch.org/whl/nightly/cu128
   pip install -r requirements-gpu.txt
   ```
2. 运行内置的国内镜像权重下载器，自动将 FasterLivePortrait、MuseTalk 与 SenseVoiceSmall 权重下载至 `weights/` 目录：
   ```powershell
   python scripts/download_weights.py
   ```

### 🎯 任务二：在 `avatar/driver.py` 中启用 MuseTalk 潜空间嘴部重绘张量推理
1. 当前 `avatar/driver.py` 已在启动时预计算好 90 帧含自然眨眼与呼吸的无缝循环基底（`self.idle_base_frames`），并自动探测 `ONNXRuntime-GPU` 与 `torch.cuda` 显存状态；
2. 权重下载完成后，在 `_synthesize_talking_frame()` 中将 `self.onnx_session` 或 `MuseTalk` 的 UNet 半精度推理结果替换当前的软遮罩形变区域，即可跑满 50+ FPS 写实口型。

## 5. 新环境启动与检验命令

```powershell
# 1. 复制配置并填入 API Key (如 SiliconFlow / DeepSeek API Key)
copy .env.example .env

# 2. 启动服务（默认端口 8899，GPU 模式下自动关闭热重载以保护 8GB 显存）
python main.py
```

## 6. 用户给新 Agent 的唤醒 Prompt（请复制使用）

> **“你好 Antigravity，我已经阅读了仓库中的 `AGENT_HANDOVER.md` (v3.0 Industrial)。当前机器已配备 RTX 5060 Ti 显卡环境，请先帮我运行 `python scripts/download_weights.py` 拉取预训练权重，并将 FasterLivePortrait + MuseTalk 的 FP16 张量推理挂载到 `avatar/driver.py` 的 `_synthesize_talking_frame` 中！”**
