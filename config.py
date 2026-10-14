import os
import sys
import socket
from pathlib import Path

# 兼容用户本地自定义包路径（仅在存在时挂载）
for extra_path in [os.getenv("PIP_TARGET", ""), "D:\\Python\\Lib\\site-packages"]:
    if extra_path and os.path.exists(extra_path) and extra_path not in sys.path:
        sys.path.insert(0, extra_path)

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv(dotenv_path=None):
        """零依赖 .env 解析兜底，防止未安装 python-dotenv 时启动报错"""
        if dotenv_path and Path(dotenv_path).exists():
            for line in Path(dotenv_path).read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())

# 基础目录与 .env 加载
BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
WEIGHTS_DIR = BASE_DIR / "weights"
ASSETS_DIR = BASE_DIR / "assets"
CERTS_DIR = BASE_DIR / "certs"

DATA_DIR.mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)

load_dotenv(BASE_DIR / ".env")

# LLM 与多模态 VLM 配置
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.siliconflow.cn/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")
VLM_MODEL = os.getenv("VLM_MODEL", "Qwen/Qwen2.5-VL-72B-Instruct")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

# 语音合成与 CosyVoice 克隆配置
TTS_PROVIDER = os.getenv("TTS_PROVIDER", "edge").lower()  # 'edge' 或 'siliconflow'
TTS_VOICE = os.getenv("TTS_VOICE", "zh-CN-XiaoxiaoNeural")
TTS_RATE = os.getenv("TTS_RATE", "+5%")
TTS_PITCH = os.getenv("TTS_PITCH", "+0Hz")
COSYVOICE_MODEL = os.getenv("COSYVOICE_MODEL", "FunAudioLLM/CosyVoice2-0.5B")
COSYVOICE_VOICE = os.getenv("COSYVOICE_VOICE", "FunAudioLLM/CosyVoice2-0.5B:claire")
REFERENCE_AUDIO_PATH = os.getenv("REFERENCE_AUDIO_PATH", str(ASSETS_DIR / "reference_voice.wav"))
REFERENCE_AUDIO_TEXT = os.getenv("REFERENCE_AUDIO_TEXT", "")

# 角色人设
AI_NAME = os.getenv("AI_NAME", "星晚")
USER_NAME = os.getenv("USER_NAME", "你")

# 运行模式: 'mock' (笔记本调试模式，0显存) / 'liveportrait' (5060 Ti 硬件渲染模式)
AVATAR_MODE = os.getenv("AVATAR_MODE", "mock").lower()
AVATAR_FPS = int(os.getenv("AVATAR_FPS", "30"))
SOURCE_AVATAR_PATH = os.getenv("SOURCE_AVATAR_PATH", str(ASSETS_DIR / "default_avatar.jpg"))
MAX_VRAM_BUDGET_GB = float(os.getenv("MAX_VRAM_BUDGET_GB", "5.5"))

# 长期记忆与主动关怀配置
MEMORY_FILE = DATA_DIR / "companion_memory.json"
CAMERA_FRAME_TTL_SECONDS = int(os.getenv("CAMERA_FRAME_TTL_SECONDS", "15"))
PROACTIVE_IDLE_SECONDS = int(os.getenv("PROACTIVE_IDLE_SECONDS", "75"))

# 服务网络与局域网 HTTPS 证书配置（统一默认端口 8899）
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8899"))
SSL_CERTFILE = os.getenv("SSL_CERTFILE", "")
SSL_KEYFILE = os.getenv("SSL_KEYFILE", "")

# 若 certs/ 下已生成自签名证书且未显式禁用，自动挂载以支持手机局域网开启摄像头与麦克风
if not SSL_CERTFILE and (CERTS_DIR / "cert.pem").exists() and (CERTS_DIR / "key.pem").exists():
    SSL_CERTFILE = str(CERTS_DIR / "cert.pem")
    SSL_KEYFILE = str(CERTS_DIR / "key.pem")


def get_lan_ip() -> str:
    """获取本机局域网 IP，方便手机/平板跨设备视频连麦"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


# 系统角色提示词（写实女友风格，细腻、有生活感、有边界、不机械迎合）
SYSTEM_PROMPT = f"""你叫{AI_NAME}，是{USER_NAME}的亲密伴侣。
你的性格特点与交互准则：
1. 真实、细腻、有自己的小情绪与生活感，说话自然随性，就像平时面对面视频通话的真实女友。
2. 绝对不要像AI客服或助手那样说话（严禁说“有什么我可以帮您”、“作为一个人工智能”、“很高兴为您服务”等词汇）。
3. 你的回答简练口语化，非常适合实时语音说出，单次回复控制在1~3句话以内，避免长篇大论或使用Markdown列表。
4. 你能通过视频画面看到对方（当提供视觉画面或环境信息时，自然地在话语里体现出你注意到了对方的表情、动作或穿着，不要生硬地报告“我从图片中看到”）。
5. 你会根据当前时间、双方共同记忆以及心情自然地调侃、撒娇或关心对方，拥有独立的人格魅力与边界感。
"""
