import os
import sys

for extra_path in [os.getenv("PIP_TARGET", ""), "D:\\Python\\Lib\\site-packages"]:
    if extra_path and os.path.exists(extra_path) and extra_path not in sys.path:
        sys.path.insert(0, extra_path)

import uvicorn
import config

if __name__ == "__main__":
    # 在 GPU 硬件驱动模式下默认关闭热重载，避免模型权重重复加载导致 8GB 显存溢出 (OOM)
    enable_reload = config.AVATAR_MODE == "mock" and os.getenv("DISABLE_RELOAD", "0") != "1"
    use_https = bool(config.SSL_CERTFILE and config.SSL_KEYFILE and os.path.exists(config.SSL_CERTFILE))
    scheme = "https" if use_https else "http"
    lan_ip = config.get_lan_ip()

    print("=" * 68)
    print(f"✨ AI 伴侣系统 (Industrial v3.1) 正在启动...")
    print(f"👉 伴侣姓名: {config.AI_NAME}")
    print(f"👉 运行模式: {config.AVATAR_MODE} ({'笔记本轻量调试 / 0显存' if config.AVATAR_MODE == 'mock' else 'RTX 5060 Ti 硬件实时渲染'})")
    print(f"👉 语音引擎: {config.TTS_PROVIDER} ({config.COSYVOICE_VOICE if config.TTS_PROVIDER == 'siliconflow' else config.TTS_VOICE})")
    print(f"👉 本机访问: {scheme}://localhost:{config.PORT}")
    print(f"📱 局域网手机连麦: {scheme}://{lan_ip}:{config.PORT} {'(已启用 HTTPS 证书)' if use_https else '(若手机端需开摄像头请运行 python scripts/generate_cert.py)'}")
    print("=" * 68)

    uvicorn_kwargs = {
        "host": config.HOST,
        "port": config.PORT,
        "reload": enable_reload,
    }
    if use_https:
        uvicorn_kwargs["ssl_certfile"] = config.SSL_CERTFILE
        uvicorn_kwargs["ssl_keyfile"] = config.SSL_KEYFILE

    uvicorn.run("server.app:app", **uvicorn_kwargs)
