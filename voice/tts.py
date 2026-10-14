import math
import json
import base64
import asyncio
import urllib.request
from pathlib import Path
from typing import AsyncGenerator, List, Dict, Any, Optional
import config

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    aiohttp = None
    HAS_AIOHTTP = False

try:
    import edge_tts
    HAS_EDGE_TTS = True
except ImportError:
    edge_tts = None
    HAS_EDGE_TTS = False


class TTSEngine:
    """
    工业级三级自适应语音合成与声音克隆引擎：
    1. Tier 1 (SiliconFlow / CosyVoice2-0.5B 云端克隆与拟真女声)：
       - 支持预置高自然度情感女声（如 FunAudioLLM/CosyVoice2-0.5B:claire / bella / anna）；
       - 支持放入 assets/reference_voice.wav (5~10秒) 实现零样本专属女友音色克隆；
    2. Tier 2 (Edge-TTS 微软神经网络女声)：
       - 免费、0显存、极高可用性（zh-CN-XiaoxiaoNeural / zh-CN-XiaoyiNeural）；
    3. Tier 3 (浏览器原生 Web Speech API 兜底)：
       - 当处于离线断网环境时安全返回空字节，由前端自动零延迟朗读。
    """

    VOICE_PRESETS = [
        {"id": "edge:zh-CN-XiaoxiaoNeural", "provider": "edge", "voice": "zh-CN-XiaoxiaoNeural", "label": "微软晓晓 (温柔柔美 · 免费0显存)"},
        {"id": "edge:zh-CN-XiaoyiNeural", "provider": "edge", "voice": "zh-CN-XiaoyiNeural", "label": "微软晓伊 (灵动俏皮 · 免费0显存)"},
        {"id": "siliconflow:FunAudioLLM/CosyVoice2-0.5B:claire", "provider": "siliconflow", "voice": "FunAudioLLM/CosyVoice2-0.5B:claire", "label": "CosyVoice2 Claire (知性甜美 · 云端拟真)"},
        {"id": "siliconflow:FunAudioLLM/CosyVoice2-0.5B:bella", "provider": "siliconflow", "voice": "FunAudioLLM/CosyVoice2-0.5B:bella", "label": "CosyVoice2 Bella (元气少女 · 云端拟真)"},
        {"id": "siliconflow:FunAudioLLM/CosyVoice2-0.5B:anna", "provider": "siliconflow", "voice": "FunAudioLLM/CosyVoice2-0.5B:anna", "label": "CosyVoice2 Anna (温柔御姐 · 云端拟真)"},
        {"id": "siliconflow:custom_clone", "provider": "siliconflow", "voice": "custom_clone", "label": "CosyVoice2 专属克隆 (读取 assets/reference_voice.wav)"},
    ]

    def __init__(
        self,
        provider: str = config.TTS_PROVIDER,
        voice: str = config.TTS_VOICE,
        rate: str = config.TTS_RATE,
        pitch: str = config.TTS_PITCH,
    ):
        self.provider = provider.lower()
        self.voice = config.COSYVOICE_VOICE if self.provider == "siliconflow" else voice
        self.rate = rate
        self.pitch = pitch
        self.cosyvoice_model = config.COSYVOICE_MODEL
        self.ref_audio_path = Path(config.REFERENCE_AUDIO_PATH)
        self.ref_audio_text = config.REFERENCE_AUDIO_TEXT

    def set_voice_profile(self, provider: str, voice: str):
        self.provider = provider.lower()
        self.voice = voice
        print(f">>> [TTSEngine] 已切换音色配置: provider={self.provider}, voice={self.voice}")

    def get_info(self) -> Dict[str, Any]:
        return {
            "provider": self.provider,
            "voice": self.voice,
            "ref_audio_ready": self.ref_audio_path.exists(),
            "presets": self.VOICE_PRESETS,
        }

    async def synthesize_to_bytes(self, text: str) -> bytes:
        """合成单句语音，支持 CosyVoice2 克隆 -> Edge-TTS -> 浏览器原生语音三级自动故障转移"""
        clean_text = text.strip()
        if not clean_text:
            return b""

        # Tier 1: 若选用 siliconflow (CosyVoice2) 且配置了有效 API Key
        if (
            self.provider == "siliconflow"
            and config.LLM_API_KEY
            and config.LLM_API_KEY != "your_api_key_here"
        ):
            audio_bytes = await self._synthesize_siliconflow_cosyvoice(clean_text)
            if audio_bytes:
                return audio_bytes
            print("[TTSEngine] CosyVoice 云端合成未返回音频，自动降级至 Edge-TTS")

        # Tier 2: 使用 Edge-TTS 合成
        edge_voice = self.voice if self.voice.startswith("zh-") else config.TTS_VOICE
        if HAS_EDGE_TTS:
            try:
                communicate = edge_tts.Communicate(
                    clean_text, edge_voice, rate=self.rate, pitch=self.pitch
                )
                audio_data = bytearray()
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data.extend(chunk["data"])
                if audio_data:
                    return bytes(audio_data)
            except Exception as e:
                print(f"[TTSEngine] edge-tts 云端合成降级（将由前端浏览器原生合成）: {e}")

        # Tier 3: 返回空字节，前端自动启用 Web Speech API
        return b""

    async def _synthesize_siliconflow_cosyvoice(self, text: str) -> bytes:
        """调用 SiliconFlow OpenAI 兼容 /v1/audio/speech 接口（支持预置音色与零样本参考音频克隆）"""
        url = f"{config.LLM_API_BASE.rstrip('/')}/audio/speech"
        headers = {
            "Authorization": f"Bearer {config.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload: Dict[str, Any] = {
            "model": self.cosyvoice_model,
            "input": text,
            "response_format": "mp3",
            "speed": 1.05,
        }

        # 检查是否启用本地参考音频零样本克隆
        if self.voice == "custom_clone" and self.ref_audio_path.exists():
            raw_ref = self.ref_audio_path.read_bytes()
            b64_ref = base64.b64encode(raw_ref).decode("utf-8")
            mime = "audio/mpeg" if self.ref_audio_path.suffix.lower() == ".mp3" else "audio/wav"
            payload["references"] = [
                {
                    "audio": f"data:{mime};base64,{b64_ref}",
                    "text": self.ref_audio_text or "这是一段用于克隆专属伴侣音色的参考语音。",
                }
            ]
        else:
            payload["voice"] = (
                self.voice
                if ":" in self.voice
                else f"{self.cosyvoice_model}:claire"
            )

        try:
            if HAS_AIOHTTP:
                timeout = aiohttp.ClientTimeout(total=15)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    async with session.post(url, headers=headers, json=payload) as resp:
                        if resp.status == 200:
                            return await resp.read()
                        err_txt = await resp.text()
                        print(f"[TTSEngine] CosyVoice HTTP {resp.status}: {err_txt[:120]}")
                        return b""
            else:
                req_data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
                return await asyncio.to_thread(
                    lambda: urllib.request.urlopen(req, timeout=15).read()
                )
        except Exception as e:
            print(f"[TTSEngine] CosyVoice 请求异常: {e}")
            return b""

    @staticmethod
    def estimate_envelope(audio_bytes: bytes, text: str, fps: int = 30) -> List[float]:
        """提取或估算 30fps 的音频能量包络序列 (0.0 ~ 1.0)"""
        if audio_bytes and len(audio_bytes) > 512:
            duration_sec = max(0.5, min(15.0, len(audio_bytes) / 6000.0))
        else:
            duration_sec = max(0.6, len(text.strip()) / 4.2)

        total_frames = max(6, int(duration_sec * fps))
        envelope: List[float] = []

        if audio_bytes and len(audio_bytes) > total_frames * 4:
            step = len(audio_bytes) // total_frames
            for i in range(total_frames):
                segment = audio_bytes[i * step : (i + 1) * step]
                energy = sum(abs(b - 128) for b in segment) / (len(segment) * 128.0)
                syllable_mod = 0.65 + 0.35 * math.sin(i * 0.55)
                val = min(1.0, max(0.08, energy * 1.4 * syllable_mod))
                envelope.append(round(val, 3))
        else:
            for i in range(total_frames):
                t = i / fps
                val = 0.45 + 0.35 * math.sin(t * 14.0) + 0.15 * math.cos(t * 7.3)
                envelope.append(round(min(1.0, max(0.05, val)), 3))

        if len(envelope) >= 4:
            envelope[0] *= 0.3
            envelope[1] *= 0.6
            envelope[-2] *= 0.6
            envelope[-1] = 0.0
        return envelope
