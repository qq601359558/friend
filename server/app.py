import re
import time
import json
import base64
import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Body
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import config
from brain import BrainAgent
from voice import TTSEngine
from avatar import get_avatar_driver

agent = BrainAgent()
tts = TTSEngine()
avatar_driver = get_avatar_driver()

SENTENCE_BOUNDARY_RE = re.compile(r"([。！？；!?;~\n]+)")


class SafeWebSocket:
    """带异步互斥锁的 WebSocket 包装器，防止多协程高频推送文本、音频与视频帧时发生并发写冲突"""

    def __init__(self, ws: WebSocket):
        self.ws = ws
        self._lock = asyncio.Lock()

    async def send_json(self, data: Dict[str, Any]):
        async with self._lock:
            await self.ws.send_json(data)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await agent.close()


app = FastAPI(title="AI Companion System (Industrial v3.1)", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DIR = BASE_DIR / "web"
ASSETS_DIR = BASE_DIR / "assets"

ASSETS_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")


@app.get("/")
async def get_index():
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return HTMLResponse("<h1>AI 伴侣服务运行中，请检查 web/index.html</h1>")


@app.get("/api/status")
async def get_status():
    return {
        "status": "online",
        "version": "3.1-industrial",
        "ai_name": config.AI_NAME,
        "user_name": config.USER_NAME,
        "avatar_mode": config.AVATAR_MODE,
        "llm_model": config.LLM_MODEL,
        "vlm_model": config.VLM_MODEL,
        "lan_ip": config.get_lan_ip(),
        "https_enabled": bool(config.SSL_CERTFILE),
        "proactive_idle_seconds": config.PROACTIVE_IDLE_SECONDS,
        "tts": tts.get_info(),
        "driver": avatar_driver.get_driver_info(),
        "memory": agent.memory.get_summary(),
    }


@app.post("/api/tts/config")
async def update_tts_config(payload: Dict[str, str] = Body(...)):
    """动态切换语音合成引擎与音色（支持 Edge-TTS 与 SiliconFlow CosyVoice2 拟真/克隆音色）"""
    preset_id = payload.get("preset_id", "").strip()
    if preset_id and ":" in preset_id:
        provider, voice = preset_id.split(":", 1)
        tts.set_voice_profile(provider, voice)
    else:
        provider = payload.get("provider", tts.provider)
        voice = payload.get("voice", tts.voice)
        tts.set_voice_profile(provider, voice)
    return {"status": "ok", "tts": tts.get_info()}


@app.post("/api/avatar/upload")
async def upload_avatar_image(payload: Dict[str, str] = Body(...)):
    """前端在线更换写实头像照片，并立即触发 90 帧呼吸/眨眼基底热重载"""
    b64_str = payload.get("image_base64", "")
    if not b64_str:
        return {"status": "error", "message": "未提供图片数据"}
    if "," in b64_str:
        b64_str = b64_str.split(",", 1)[1]
    try:
        raw_bytes = base64.b64decode(b64_str)
        target_path = ASSETS_DIR / "default_avatar.jpg"
        target_path.write_bytes(raw_bytes)
        reloaded = avatar_driver.reload_avatar_image(str(target_path))
        return {
            "status": "ok",
            "reloaded": reloaded,
            "driver": avatar_driver.get_driver_info(),
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@app.get("/api/memory")
async def get_memory():
    return agent.memory.get_summary()


@app.post("/api/memory/add")
async def add_memory_fact(payload: Dict[str, str] = Body(...)):
    content = payload.get("content", "").strip()
    category = payload.get("category", "手动备忘").strip() or "手动备忘"
    summary = agent.memory.add_manual_fact(content, category)
    return {"status": "ok", "memory": summary}


@app.delete("/api/memory/{fact_index}")
async def delete_memory_fact(fact_index: int):
    summary = agent.memory.delete_fact(fact_index)
    return {"status": "ok", "memory": summary}


@app.post("/api/memory/reset")
async def reset_memory():
    agent.reset()
    agent.memory.reset()
    return {"status": "ok", "memory": agent.memory.get_summary()}


async def _handle_dialogue_stream(
    safe_ws: SafeWebSocket,
    user_text: str = "",
    camera_frame_b64: Optional[str] = None,
    is_proactive: bool = False,
    idle_seconds: int = 60,
):
    """
    工业级二级解耦全双工流水线 (Two-Stage Producer-Consumer Pipeline)
    """
    await safe_ws.send_json({
        "type": "state",
        "data": "thinking",
        "vision_active": bool(camera_frame_b64),
        "proactive": is_proactive,
    })

    sentence_queue: asyncio.Queue[Optional[Tuple[int, str]]] = asyncio.Queue()
    playout_queue: asyncio.Queue[Optional[Dict[str, Any]]] = asyncio.Queue()
    produced_segments = 0
    played_segments = 0

    async def tts_pre_synthesizer():
        while True:
            item = await sentence_queue.get()
            if item is None:
                await playout_queue.put(None)
                break
            seg_idx, raw_sentence = item
            clean_seg = raw_sentence.strip()
            if not clean_seg:
                continue
            audio_bytes = await tts.synthesize_to_bytes(clean_seg)
            audio_b64 = base64.b64encode(audio_bytes).decode("utf-8") if audio_bytes else ""
            envelope = tts.estimate_envelope(audio_bytes, clean_seg, fps=config.AVATAR_FPS)
            await playout_queue.put({
                "segment_index": seg_idx,
                "text": clean_seg,
                "audio_bytes": audio_bytes,
                "audio_base64": audio_b64,
                "envelope": envelope,
            })

    async def playout_and_avatar_consumer():
        nonlocal played_segments
        while True:
            pkg = await playout_queue.get()
            if pkg is None:
                break
            if played_segments == 0:
                await safe_ws.send_json({"type": "state", "data": "speaking"})
            played_segments += 1

            await safe_ws.send_json({
                "type": "audio",
                "segment_index": pkg["segment_index"],
                "audio_base64": pkg["audio_base64"],
                "text": pkg["text"],
                "fps": config.AVATAR_FPS,
                "envelope": pkg["envelope"],
            })

            if config.AVATAR_MODE == "liveportrait":
                async for event in avatar_driver.drive_stream(
                    pkg["audio_bytes"], pkg["text"], envelope=pkg["envelope"]
                ):
                    if event.get("type") == "video_frame":
                        await safe_ws.send_json(event)

    tts_task = asyncio.create_task(tts_pre_synthesizer())
    playout_task = asyncio.create_task(playout_and_avatar_consumer())

    full_reply = ""
    buffer = ""
    try:
        token_stream = (
            agent.proactive_stream(image_base64=camera_frame_b64, idle_seconds=idle_seconds)
            if is_proactive
            else agent.chat_stream(user_text, image_base64=camera_frame_b64)
        )
        async for chunk in token_stream:
            full_reply += chunk
            buffer += chunk
            await safe_ws.send_json({
                "type": "text_delta",
                "delta": chunk,
                "proactive": is_proactive,
            })

            if SENTENCE_BOUNDARY_RE.search(buffer) or ("，" in buffer and len(buffer) >= 12):
                await sentence_queue.put((produced_segments, buffer))
                produced_segments += 1
                buffer = ""

        if buffer.strip():
            await sentence_queue.put((produced_segments, buffer))
            produced_segments += 1

        await sentence_queue.put(None)
        await tts_task
        await playout_task

        await safe_ws.send_json({
            "type": "tts_stream_end",
            "text": full_reply,
            "segments": played_segments,
            "memory": agent.memory.get_summary(),
        })
        if played_segments == 0:
            await safe_ws.send_json({"type": "state", "data": "idle"})

    except asyncio.CancelledError:
        tts_task.cancel()
        playout_task.cancel()
        await safe_ws.send_json({"type": "state", "data": "idle"})
        raise
    except Exception as e:
        tts_task.cancel()
        playout_task.cancel()
        print(f"[WebSocket] 全双工对话流水线异常: {e}")
        await safe_ws.send_json({"type": "state", "data": "idle"})


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    safe_ws = SafeWebSocket(websocket)
    print(">>> 客户端已建立 WebSocket 视频/语音全双工连接 (Industrial v3.1)")

    latest_camera_frame: Optional[str] = None
    latest_camera_ts: float = 0.0
    last_activity_ts: float = time.time()
    is_client_playing: bool = False
    active_turn_task: Optional[asyncio.Task] = None

    def get_valid_camera_frame() -> Optional[str]:
        if (
            latest_camera_frame
            and (time.time() - latest_camera_ts) <= config.CAMERA_FRAME_TTL_SECONDS
        ):
            return latest_camera_frame
        return None

    async def proactive_care_monitor():
        nonlocal last_activity_ts, active_turn_task
        while True:
            await asyncio.sleep(5.0)
            if config.PROACTIVE_IDLE_SECONDS <= 0:
                continue
            if is_client_playing or (active_turn_task and not active_turn_task.done()):
                last_activity_ts = time.time()
                continue
            idle_sec = int(time.time() - last_activity_ts)
            if idle_sec >= config.PROACTIVE_IDLE_SECONDS:
                last_activity_ts = time.time()
                active_turn_task = asyncio.create_task(
                    _handle_dialogue_stream(
                        safe_ws,
                        camera_frame_b64=get_valid_camera_frame(),
                        is_proactive=True,
                        idle_seconds=idle_sec,
                    )
                )

    monitor_task = asyncio.create_task(proactive_care_monitor())

    try:
        while True:
            raw_data = await websocket.receive_text()
            msg = json.loads(raw_data)
            msg_type = msg.get("type", "text")

            if msg_type == "user_message":
                user_text = msg.get("text", "").strip()
                if not user_text:
                    continue

                last_activity_ts = time.time()
                is_client_playing = True
                if active_turn_task and not active_turn_task.done():
                    active_turn_task.cancel()

                active_turn_task = asyncio.create_task(
                    _handle_dialogue_stream(
                        safe_ws,
                        user_text=user_text,
                        camera_frame_b64=get_valid_camera_frame(),
                        is_proactive=False,
                    )
                )

            elif msg_type == "proactive_trigger":
                last_activity_ts = time.time()
                is_client_playing = True
                if active_turn_task and not active_turn_task.done():
                    active_turn_task.cancel()

                active_turn_task = asyncio.create_task(
                    _handle_dialogue_stream(
                        safe_ws,
                        camera_frame_b64=get_valid_camera_frame(),
                        is_proactive=True,
                        idle_seconds=int(msg.get("idle_seconds", 30)),
                    )
                )

            elif msg_type == "camera_frame":
                frame_data = msg.get("image_base64", "")
                if frame_data:
                    if "," in frame_data:
                        frame_data = frame_data.split(",", 1)[1]
                    latest_camera_frame = frame_data
                    latest_camera_ts = time.time()

            elif msg_type == "interrupt":
                last_activity_ts = time.time()
                is_client_playing = False
                if active_turn_task and not active_turn_task.done():
                    active_turn_task.cancel()
                await safe_ws.send_json({"type": "state", "data": "idle"})

            elif msg_type == "playback_finished":
                last_activity_ts = time.time()
                is_client_playing = False
                await safe_ws.send_json({"type": "state", "data": "idle"})

    except WebSocketDisconnect:
        monitor_task.cancel()
        if active_turn_task and not active_turn_task.done():
            active_turn_task.cancel()
        print(">>> 客户端断开连接")
    except Exception as e:
        monitor_task.cancel()
        if active_turn_task and not active_turn_task.done():
            active_turn_task.cancel()
        print(f">>> 异常断开: {e}")
