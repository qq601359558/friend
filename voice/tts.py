import edge_tts
from typing import AsyncGenerator

# 推荐的自然写实女声音色:
# zh-CN-XiaoxiaoNeural (温和柔美)
# zh-CN-XiaoyiNeural (灵动活泼)
DEFAULT_VOICE = "zh-CN-XiaoxiaoNeural"

class TTSEngine:
    def __init__(self, voice: str = DEFAULT_VOICE):
        self.voice = voice

    async def synthesize_to_bytes(self, text: str) -> bytes:
        """将文字转为 mp3 音频二进制数据，失败时安全返回空字节以便前端使用原生语音降级"""
        try:
            communicate = edge_tts.Communicate(text, self.voice, rate="+5%", pitch="+0Hz")
            audio_data = b""
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_data += chunk["data"]
            return audio_data
        except Exception as e:
            print(f"[TTSEngine] edge-tts 云端合成降级（将由前端浏览器原生合成）: {e}")
            return b""

    async def stream_audio_chunks(self, text: str) -> AsyncGenerator[bytes, None]:
        """流式输出音频二进制块"""
        communicate = edge_tts.Communicate(text, self.voice, rate="+5%", pitch="+0Hz")
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
