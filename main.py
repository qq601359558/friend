import sys
import os

for extra_path in ["D:\\Python\\Lib\\site-packages", os.getenv("PIP_TARGET", "")]:
    if extra_path and os.path.exists(extra_path) and extra_path not in sys.path:
        sys.path.insert(0, extra_path)

import uvicorn
import config

if __name__ == "__main__":
    print("=" * 60)
    print(f"✨ AI 伴侣系统正在启动...")
    print(f"👉 伴侣姓名: {config.AI_NAME}")
    print(f"👉 运行模式: {config.AVATAR_MODE} (笔记本轻量调试 / 5060Ti GPU硬件驱动)")
    print(f"👉 访问地址: http://localhost:{config.PORT}")
    print("=" * 60)
    uvicorn.run("server.app:app", host=config.HOST, port=config.PORT, reload=True)
