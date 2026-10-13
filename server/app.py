import os
import json
import base64
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

import config
from brain import BrainAgent
from voice import TTSEngine
from avatar import get_avatar_driver

app = FastAPI(title="AI Companion System")

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

# 挂载静态资源与头像素材
app.mount("/static", StaticFiles(directory=str(WEB_DIR)), name="static")
app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

agent = BrainAgent()
tts = TTSEngine()
avatar_driver = get_avatar_driver()

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
        "ai_name": config.AI_NAME,
        "avatar_mode": config.AVATAR_MODE,
        "llm_model": config.LLM_MODEL
    }

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await websocket.accept()
    print(">>> 客户端已建立 WebSocket 视频/语音连接")

    try:
        while True:
            raw_data = await websocket.receive_text()
            msg = json.loads(raw_data)
            msg_type = msg.get("type", "text")

            if msg_type == "user_message":
                user_text = msg.get("text", "").strip()
                if not user_text:
                    continue

                # 1. 广播：AI 正在思考
                await websocket.send_json({"type": "state", "data": "thinking"})

                # 2. 逐字接收大模型回复
                full_reply = ""
                async for chunk in agent.chat_stream(user_text):
                    full_reply += chunk
                    await websocket.send_json({
                        "type": "text_delta",
                        "delta": chunk
                    })

                # 3. 生成写法语音
                await websocket.send_json({"type": "state", "data": "speaking"})
                try:
                    audio_bytes = await tts.synthesize_to_bytes(full_reply)
                    audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                    
                    # 4. 发送音频及完整文本回客户端播放
                    await websocket.send_json({
                        "type": "audio",
                        "audio_base64": audio_b64,
                        "text": full_reply
                    })
                except Exception as e:
                    print(f"TTS 合成错误: {e}")

                await websocket.send_json({"type": "state", "data": "idle"})

            elif msg_type == "camera_frame":
                # 预留接收客户端前置摄像头抽帧（用于视觉理解）
                pass

    except WebSocketDisconnect:
        print(">>> 客户端断开连接")
    except Exception as e:
        print(f">>> 异常断开: {e}")
