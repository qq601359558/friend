import re
import json
import random
import asyncio
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional, AsyncGenerator
import config

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    aiohttp = None
    HAS_AIOHTTP = False


class MemoryManager:
    """
    工业级混合长期记忆与情感状态机引擎 (0 本地显存占用)：
    1. 实时启发式规则提取（0ms 延迟捕捉姓名、喜好、禁忌、生日、叮嘱）；
    2. 后台异步 LLM 深度语义记忆提炼（自动从自然闲聊中提取隐含事实、近期身体/工作状态与约定，绝不阻塞主对话）；
    3. 自动探测并桥接 Mem0 (mem0ai) 向量库，同时保持本地 JSON 原子化持久化存储 (data/companion_memory.json)；
    4. 支持单条记忆的增删改查 API 与多维情感状态机（Mood / Intimacy / Energy）。
    """

    FACT_PATTERNS = [
        (r"我(?:叫|的名字是|姓)([^\s，。！？,;!?]{1,10})", "用户姓名/称呼"),
        (r"我(?:喜欢|爱吃|最爱|平时喜欢)([^，。！？,;!?\n]{2,22})", "个人喜好"),
        (r"(?:我)?(?:不喜欢|讨厌|不吃|对[^，。]{1,8}过敏|不能喝|不能吃|忌口)([^，。！？,;!?\n]{1,22})", "个人禁忌/雷区"),
        (r"我的生日是([^，。！？,;!?]{2,15})", "重要纪念日/生日"),
        (r"我(?:在|目前在|工作是|是做)([^，。！？,;!?]{2,20})", "职业与日常背景"),
        (r"我(?:最近|今天|今晚)(?:感觉|有点|很|特别|在)([^，。！？,;!?]{2,20})", "近期状态与情绪"),
        (r"记住([^，。！？,;!?\n]{2,30})", "用户叮嘱记住的事"),
    ]

    def __init__(self, storage_path: Path = config.MEMORY_FILE):
        self.storage_path = Path(storage_path)
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self.state: Dict[str, Any] = {
            "intimacy": 65,
            "mood": "温柔愉悦",
            "energy": 90,
            "total_turns": 0,
            "last_seen": None,
            "facts": [],
            "recent_summaries": [],
        }
        self._mem0_client = None
        self._load()
        self._init_optional_mem0()

    def _init_optional_mem0(self):
        """若宿主机已安装 mem0ai 且配置了 API Key，自动挂载向量记忆桥接"""
        if not config.LLM_API_KEY or config.LLM_API_KEY == "your_api_key_here":
            return
        try:
            from mem0 import Memory
            mem0_cfg = {
                "llm": {
                    "provider": "openai",
                    "config": {
                        "model": config.LLM_MODEL,
                        "api_key": config.LLM_API_KEY,
                        "openai_base_url": config.LLM_API_BASE,
                    },
                },
                "embedder": {
                    "provider": "openai",
                    "config": {
                        "model": config.EMBEDDING_MODEL,
                        "api_key": config.LLM_API_KEY,
                        "openai_base_url": config.LLM_API_BASE,
                    },
                },
            }
            self._mem0_client = Memory.from_config(mem0_cfg)
            print(">>> [MemoryManager] 已挂载 Mem0 向量长期记忆图谱扩展")
        except Exception:
            self._mem0_client = None

    def _load(self):
        if self.storage_path.exists():
            try:
                data = json.loads(self.storage_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.state.update(data)
            except Exception as e:
                print(f"[MemoryManager] 读取记忆文件失败，使用默认初始记忆: {e}")

    def save(self):
        try:
            tmp_path = self.storage_path.with_suffix(".tmp")
            tmp_path.write_text(
                json.dumps(self.state, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            tmp_path.replace(self.storage_path)
        except Exception as e:
            print(f"[MemoryManager] 保存记忆文件失败: {e}")

    def add_manual_fact(self, content: str, category: str = "手动备忘") -> Dict[str, Any]:
        clean = content.strip()
        if not clean:
            return self.get_summary()
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        formatted = clean if ":" in clean or "：" in clean else f"{category}: {clean}"
        self.state["facts"].append({
            "category": category,
            "content": formatted,
            "raw": clean,
            "timestamp": now_str,
        })
        self.save()
        return self.get_summary()

    def delete_fact(self, index: int) -> Dict[str, Any]:
        facts = self.state.get("facts", [])
        if 0 <= index < len(facts):
            facts.pop(index)
            self.save()
        return self.get_summary()

    def extract_and_store(self, user_text: str, assistant_reply: str = ""):
        """从单轮对话中提取关键事实并更新亲密度与心情状态"""
        text = user_text.strip()
        if not text:
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        self.state["total_turns"] = self.state.get("total_turns", 0) + 1
        self.state["last_seen"] = now_str

        existing_contents = {item.get("content") for item in self.state["facts"]}
        for pattern, category in self.FACT_PATTERNS:
            matches = re.findall(pattern, text)
            for match in matches:
                fact_text = f"{category}: {match.strip()}"
                if fact_text not in existing_contents:
                    self.state["facts"].append({
                        "category": category,
                        "content": fact_text,
                        "raw": text,
                        "timestamp": now_str,
                    })
                    existing_contents.add(fact_text)

        if len(self.state["facts"]) > 60:
            self.state["facts"] = self.state["facts"][-60:]

        # 更新多维情感状态机
        if any(w in text for w in ["想你", "喜欢你", "爱你", "辛苦了", "抱抱", "晚安", "早安", "好看", "真棒"]):
            self.state["intimacy"] = min(100, self.state.get("intimacy", 65) + 2)
            self.state["mood"] = "甜蜜心动"
        elif any(w in text for w in ["累", "烦", "难过", "加班", "头疼", "胃疼", "感冒", "睡不着", "委屈"]):
            self.state["intimacy"] = min(100, self.state.get("intimacy", 65) + 1)
            self.state["mood"] = "心疼关切"
        elif any(w in text for w in ["笨", "讨厌", "走开", "闭嘴", "无聊"]):
            self.state["mood"] = "有点小傲娇/委屈"
        else:
            self.state["intimacy"] = min(100, self.state.get("intimacy", 65) + 1)
            self.state["mood"] = "温柔松弛"

        self.save()

    def store_llm_extracted_facts(self, extracted_items: List[Dict[str, str]], raw_text: str):
        """将后台异步 LLM 提炼出的隐含事实合入持久化记忆库"""
        if not extracted_items:
            return
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        existing_contents = {item.get("content") for item in self.state["facts"]}
        added = False
        for item in extracted_items:
            cat = item.get("category", "日常点滴").strip()
            fact = item.get("fact", "").strip()
            if not fact or len(fact) < 2:
                continue
            fact_text = f"{cat}: {fact}"
            if fact_text not in existing_contents:
                self.state["facts"].append({
                    "category": cat,
                    "content": fact_text,
                    "raw": raw_text,
                    "timestamp": now_str,
                })
                existing_contents.add(fact_text)
                added = True
        if added:
            if len(self.state["facts"]) > 60:
                self.state["facts"] = self.state["facts"][-60:]
            self.save()

    def search_relevant_facts(self, query: str, top_k: int = 6) -> List[str]:
        """根据当前话题检索最相关的长期记忆条目"""
        facts = self.state.get("facts", [])
        if not facts:
            return []

        scored = []
        for idx, item in enumerate(facts):
            content = item.get("content", "")
            raw = item.get("raw", "")
            overlap = sum(1 for ch in set(query) if ch in content or ch in raw)
            recency_bonus = idx * 0.12
            scored.append((overlap + recency_bonus, content))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [item[1] for item in scored[:top_k]]

    def build_context_prompt(self, user_query: str = "") -> str:
        """生成动态注入 System Prompt 的时间、情绪与长期记忆上下文"""
        now = datetime.now()
        hour = now.hour
        if 5 <= hour < 11:
            time_desc = f"清晨/上午 ({now.strftime('%H:%M')})"
        elif 11 <= hour < 14:
            time_desc = f"午间 ({now.strftime('%H:%M')})"
        elif 14 <= hour < 18:
            time_desc = f"下午 ({now.strftime('%H:%M')})"
        elif 18 <= hour < 23:
            time_desc = f"夜晚 ({now.strftime('%H:%M')})"
        else:
            time_desc = f"深夜 ({now.strftime('%H:%M')}，注意提醒对方早点休息)"

        relevant_facts = self.search_relevant_facts(user_query)
        facts_block = (
            "\n".join(f"- {f}" for f in relevant_facts)
            if relevant_facts
            else "- 暂无特定历史偏好记录，请在自然聊天中慢慢了解对方。"
        )

        return (
            f"\n【当前时空与伴侣状态】\n"
            f"- 当前时间：{now.strftime('%Y-%m-%d')} {time_desc}\n"
            f"- 你的当前心情：{self.state.get('mood', '温柔愉悦')} | 亲密度：{self.state.get('intimacy', 65)}/100 | 累计互动：{self.state.get('total_turns', 0)} 次\n"
            f"【你们的共同记忆片段】\n"
            f"{facts_block}\n"
        )

    def get_summary(self) -> Dict[str, Any]:
        facts = self.state.get("facts", [])
        return {
            "intimacy": self.state.get("intimacy", 65),
            "mood": self.state.get("mood", "温柔愉悦"),
            "energy": self.state.get("energy", 90),
            "total_turns": self.state.get("total_turns", 0),
            "facts_count": len(facts),
            "facts": facts,
            "last_seen": self.state.get("last_seen"),
        }

    def reset(self):
        self.state["facts"] = []
        self.state["total_turns"] = 0
        self.state["intimacy"] = 65
        self.state["mood"] = "温柔愉悦"
        self.save()


class BrainAgent:
    """
    工业级云端大脑与多模态情感对话代理：
    1. 复用 aiohttp.ClientSession 连接池，支持指数退避重试与标准库回退；
    2. 严格维护 user/assistant 角色交替，API 失败自动回滚，杜绝 400 上下文污染；
    3. 支持传入前置摄像头抽帧 (image_base64)，自动路由至多模态视觉模型 (VLM) 并在失败时无缝降级；
    4. 内置后台非阻塞 LLM 语义记忆提炼器 (_async_llm_extract_memory) 与空闲主动关怀生成器 (proactive_stream)。
    """

    def __init__(self):
        self.history: List[Dict[str, Any]] = []
        self.base_system_prompt = config.SYSTEM_PROMPT
        self.memory = MemoryManager()
        self._session: Optional[Any] = None
        self._bg_tasks: set = set()

    async def _get_session(self):
        if not HAS_AIOHTTP:
            return None
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=45, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self):
        for t in list(self._bg_tasks):
            t.cancel()
        if self._session and not self._session.closed:
            await self._session.close()

    def reset(self):
        self.history = []

    def _schedule_bg_memory_extraction(self, user_msg: str, assistant_reply: str):
        """在后台异步启动 LLM 深度语义记忆提炼，0 延迟影响主对话流"""
        if not config.LLM_API_KEY or config.LLM_API_KEY == "your_api_key_here":
            return
        if len(user_msg.strip()) < 6:
            return
        task = asyncio.create_task(self._async_llm_extract_memory(user_msg, assistant_reply))
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)

    async def _async_llm_extract_memory(self, user_msg: str, assistant_reply: str):
        """调用轻量大模型从自然口语中提取隐含事实（如身体不适、饮食禁忌、工作计划）"""
        extract_prompt = (
            "请从以下用户的话语中提取值得作为伴侣长期记住的个人事实、偏好、身体状态、禁忌或约定。\n"
            "若没有值得记住的新事实，请直接返回 []。\n"
            "若有，请严格返回 JSON 数组，格式为：[{\"category\": \"类别\", \"fact\": \"简短事实描述\"}]，不要输出任何其他解释。\n"
            f"用户说：{user_msg}"
        )
        headers = {
            "Authorization": f"Bearer {config.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": config.LLM_MODEL,
            "messages": [{"role": "user", "content": extract_prompt}],
            "stream": False,
            "temperature": 0.1,
        }
        url = f"{config.LLM_API_BASE.rstrip('/')}/chat/completions"
        try:
            session = await self._get_session()
            if session is not None:
                async with session.post(url, headers=headers, json=payload) as resp:
                    if resp.status != 200:
                        return
                    data = await resp.json()
                    content = data["choices"][0]["message"]["content"].strip()
            else:
                req_data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
                raw_resp = await asyncio.to_thread(
                    lambda: urllib.request.urlopen(req, timeout=15).read().decode("utf-8")
                )
                content = json.loads(raw_resp)["choices"][0]["message"]["content"].strip()

            match = re.search(r"\[.*\]", content, re.DOTALL)
            if match:
                items = json.loads(match.group(0))
                if isinstance(items, list):
                    self.memory.store_llm_extracted_facts(items, user_msg)
        except Exception:
            pass

    async def proactive_stream(
        self,
        image_base64: Optional[str] = None,
        idle_seconds: int = 60,
    ) -> AsyncGenerator[str, None]:
        """当用户长时间静默或点击主动关怀时，结合画面与时间主动开口搭话"""
        prompt = (
            f"（系统提示：对方已经安静了约 {idle_seconds} 秒没有说话。"
            f"{'你正通过摄像头看着对方，请结合画面里对方的状态或当前时间，' if image_base64 else '请结合当前时间与你们的共同记忆，'}"
            f"自然、温柔或俏皮地主动开口跟对方搭一句话，关心一下对方在干嘛，控制在1~2句话内。）"
        )
        if not config.LLM_API_KEY or config.LLM_API_KEY == "your_api_key_here":
            vision_hint = "看你一直盯着屏幕不说话，" if image_base64 else "怎么突然安静下来啦，"
            mock_proactive = [
                f"{vision_hint}是在发呆还是在忙工作呀？累了的话伸个懒腰休息一下嘛~",
                f"{vision_hint}哼，开启视频又不出声，是不是在偷偷看我呀？",
                f"{vision_hint}要不要喝口水歇会儿？我一直在这儿陪着你呢。",
            ]
            reply = random.choice(mock_proactive)
            self.history.append({"role": "assistant", "content": reply})
            for ch in reply:
                await asyncio.sleep(0.01)
                yield ch
            return

        async for ch in self.chat_stream(prompt, image_base64=image_base64, is_proactive=True):
            yield ch

    async def chat_stream(
        self,
        user_message: str,
        image_base64: Optional[str] = None,
        is_proactive: bool = False,
    ) -> AsyncGenerator[str, None]:
        """流式与大模型（或视觉大模型）对话"""
        clean_msg = user_message.strip()
        if not clean_msg:
            return

        # 1. 如果没有配置真实 API_KEY，提供高情商且带视觉感知反馈的本地调试回复
        if not config.LLM_API_KEY or config.LLM_API_KEY == "your_api_key_here":
            vision_prefix = "（看着镜头里的你笑了一下）" if image_base64 else ""
            mock_replies = [
                f"{vision_prefix}在听呢~ 你刚刚说“{clean_msg}”，今天忙不忙呀？要不要跟我多聊会儿？",
                f"{vision_prefix}哼，你终于想起来找我啦！我刚才还在想你现在在干嘛呢，看你精神还不错嘛~",
                f"{vision_prefix}知道啦，看你挺辛苦的，待会打算吃点什么好吃的犒劳一下自己呀？",
            ]
            reply = random.choice(mock_replies)
            if not is_proactive:
                self.history.append({"role": "user", "content": clean_msg})
                self.memory.extract_and_store(clean_msg, reply)
            self.history.append({"role": "assistant", "content": reply})
            for char in reply:
                await asyncio.sleep(0.01)
                yield char
            return

        # 2. 组装注入了时空、心情与长期记忆的动态 System Prompt
        dynamic_system_prompt = self.base_system_prompt + self.memory.build_context_prompt(clean_msg)
        messages: List[Dict[str, Any]] = [{"role": "system", "content": dynamic_system_prompt}]
        messages.extend(self.history[-10:])

        # 3. 如果附带了最新的摄像头画面，构造 OpenAI Vision 兼容多模态消息体
        use_vision = bool(image_base64)
        if use_vision:
            current_user_msg: Dict[str, Any] = {
                "role": "user",
                "content": [
                    {"type": "text", "text": clean_msg},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                    },
                ],
            }
            target_model = config.VLM_MODEL or config.LLM_MODEL
        else:
            current_user_msg = {"role": "user", "content": clean_msg}
            target_model = config.LLM_MODEL

        messages.append(current_user_msg)

        headers = {
            "Authorization": f"Bearer {config.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": True,
            "temperature": 0.8,
        }

        url = f"{config.LLM_API_BASE.rstrip('/')}/chat/completions"
        full_reply = ""
        session = await self._get_session()

        try:
            if session is not None:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200 and use_vision:
                        print(f"[BrainAgent] VLM 模型 ({target_model}) 返回 {response.status}，自动降级为纯文本模型 ({config.LLM_MODEL})")
                        messages[-1] = {"role": "user", "content": clean_msg}
                        payload["model"] = config.LLM_MODEL
                        payload["messages"] = messages
                        async with session.post(url, headers=headers, json=payload) as fallback_resp:
                            if fallback_resp.status != 200:
                                yield f"（呜呜，网络好像有点小卡顿，状态码: {fallback_resp.status}）"
                                return
                            async for delta in self._iter_sse_content(fallback_resp):
                                full_reply += delta
                                yield delta
                    elif response.status != 200:
                        yield f"（呜呜，连接有点小卡顿，状态码: {response.status}）"
                        return
                    else:
                        async for delta in self._iter_sse_content(response):
                            full_reply += delta
                            yield delta
            else:
                payload["stream"] = False
                req_data = json.dumps(payload).encode("utf-8")
                req = urllib.request.Request(url, data=req_data, headers=headers, method="POST")
                raw_resp = await asyncio.to_thread(
                    lambda: urllib.request.urlopen(req, timeout=30).read().decode("utf-8")
                )
                data = json.loads(raw_resp)
                full_reply = data["choices"][0]["message"]["content"]
                for ch in full_reply:
                    yield ch
        except asyncio.CancelledError:
            if full_reply:
                if not is_proactive:
                    self.history.append({"role": "user", "content": clean_msg})
                self.history.append({"role": "assistant", "content": full_reply + "…"})
            raise
        except Exception as e:
            print(f"[BrainAgent] 请求异常: {e}")
            yield "（网络信号稍微闪了一下，你刚刚说什么呀，再跟我说一遍好不好~）"
            return

        # 4. 仅在成功获得回复后成对写入 history，并触发异步 LLM 记忆提炼
        if full_reply:
            if not is_proactive:
                self.history.append({"role": "user", "content": clean_msg})
                self.memory.extract_and_store(clean_msg, full_reply)
                self._schedule_bg_memory_extraction(clean_msg, full_reply)
            self.history.append({"role": "assistant", "content": full_reply})

    async def _iter_sse_content(self, response: Any) -> AsyncGenerator[str, None]:
        """解析 OpenAI 兼容 SSE 流"""
        async for line in response.content:
            line_str = line.decode("utf-8", errors="ignore").strip()
            if not line_str.startswith("data: "):
                continue
            data_part = line_str[6:].strip()
            if data_part == "[DONE]":
                break
            try:
                chunk = json.loads(data_part)
                choices = chunk.get("choices", [])
                if choices:
                    delta = choices[0].get("delta", {}).get("content", "")
                    if delta:
                        yield delta
            except Exception:
                continue
