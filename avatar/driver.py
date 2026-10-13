import base64
import asyncio
from typing import AsyncGenerator
import config

class BaseAvatarDriver:
    async def drive_stream(self, audio_bytes: bytes) -> AsyncGenerator[bytes, None]:
        raise NotImplementedError

class MockAvatarDriver(BaseAvatarDriver):
    """
    轻量调试模式驱动：
    在笔记本上无需调用 GPU，直接配合音频返回状态与指示，方便测试全流程前后端连通性。
    """
    def __init__(self):
        print(">>> [AvatarDriver] 初始化 Mock 驱动（轻量调试模式，0 显存消耗）")

    async def drive_stream(self, audio_bytes: bytes) -> AsyncGenerator[dict, None]:
        # 模拟产生驱动事件
        yield {"type": "status", "data": "speaking"}

class LivePortraitDriver(BaseAvatarDriver):
    """
    5060 Ti GPU 硬件渲染驱动：
    在配备 NVIDIA 显卡的环境下，加载 LivePortrait 模型并对音频生成 30fps 视频帧。
    """
    def __init__(self, source_image_path: str = "assets/default_avatar.jpg"):
        self.source_image_path = source_image_path
        print(f">>> [AvatarDriver] 正在初始化 LivePortrait 5060 Ti 驱动引擎: {source_image_path}")
        # 这里在回家部署 5060 Ti 时加载 PyTorch / LivePortrait 管道
        self.pipeline = None

    async def drive_stream(self, audio_bytes: bytes) -> AsyncGenerator[dict, None]:
        # 实际通过 LivePortrait 逐帧产出 JPEG/WebM 视频帧
        yield {"type": "frame", "data": "video_frame_placeholder"}

def get_avatar_driver():
    if config.AVATAR_MODE == "liveportrait":
        return LivePortraitDriver()
    return MockAvatarDriver()
