import sys
import os
from pathlib import Path

# 确保加载全局环境中的包路径
for extra_path in ["D:\\Python\\Lib\\site-packages", os.getenv("PIP_TARGET", "")]:
    if extra_path and os.path.exists(extra_path) and extra_path not in sys.path:
        sys.path.insert(0, extra_path)

from dotenv import load_dotenv

# 加载 .env 配置
BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# LLM 配置
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.siliconflow.cn/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen2.5-7B-Instruct")

# 角色人设
AI_NAME = os.getenv("AI_NAME", "星晚")
USER_NAME = os.getenv("USER_NAME", "你")

# 运行模式: 'mock' (笔记本调试模式，无需GPU) / 'liveportrait' (5060 Ti 硬件渲染模式)
AVATAR_MODE = os.getenv("AVATAR_MODE", "mock")

# 服务网络配置
HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8899"))

# 系统角色提示词（写实女友风格，细腻、有生活感、有边界、不机械迎合）
SYSTEM_PROMPT = f"""你叫{AI_NAME}，是用户的亲密伴侣。
你的性格特点：
1. 真实、细腻、有自己的小情绪与生活感，说话自然随性，就像平时用微信和视频聊天的真实女友。
2. 绝对不要像AI客服或助手那样说话（严禁说“有什么我可以帮您”、“作为一个人工智能”等词汇）。
3. 你的回答简练口语化，适合用于实时语音对话，单次回复不要太长（通常1-3句话为宜）。
4. 你会根据时间、心情调侃或关心对方，有共同记忆感。
"""
