import json
import aiohttp
from typing import List, Dict, AsyncGenerator
import config

class BrainAgent:
    def __init__(self):
        self.history: List[Dict[str, str]] = []
        self.system_prompt = config.SYSTEM_PROMPT

    def reset(self):
        self.history = []

    async def chat_stream(self, user_message: str) -> AsyncGenerator[str, None]:
        """流式与大模型对话"""
        self.history.append({"role": "user", "content": user_message})

        # 如果没有配置 API_KEY，提供可调试的默认女友模拟回复
        if not config.LLM_API_KEY:
            mock_replies = [
                f"在听呢~ 你刚刚说：'{user_message}'。今天忙不忙呀？",
                "哼，你终于想起来找我啦，刚才还在想你今天在干嘛呢。",
                "知道啦，看你挺辛苦的，晚上想吃点什么好吃的？"
            ]
            import random
            reply = random.choice(mock_replies)
            self.history.append({"role": "assistant", "content": reply})
            for char in reply:
                yield char
            return

        # 准备带有系统人设的消息体
        messages = [{"role": "system", "content": self.system_prompt}]
        # 截取最近 10 轮对话以保护上下文
        messages.extend(self.history[-10:])

        headers = {
            "Authorization": f"Bearer {config.LLM_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": config.LLM_MODEL,
            "messages": messages,
            "stream": True,
            "temperature": 0.8
        }

        full_reply = ""
        url = f"{config.LLM_API_BASE.rstrip('/')}/chat/completions"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status != 200:
                    err_msg = f"（呜呜，连接有点卡顿，状态码: {response.status}）"
                    yield err_msg
                    return

                async for line in response.content:
                    line_str = line.decode("utf-8").strip()
                    if line_str.startswith("data: "):
                        data_part = line_str[6:].strip()
                        if data_part == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data_part)
                            delta = chunk["choices"][0]["delta"].get("content", "")
                            if delta:
                                full_reply += delta
                                yield delta
                        except Exception:
                            continue

        if full_reply:
            self.history.append({"role": "assistant", "content": full_reply})
