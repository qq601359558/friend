"""
RTX 5060 Ti (8GB) 视觉驱动与语音感知模型权重一键下载脚本
支持自动切换 HuggingFace 国内镜像 (hf-mirror.com)，严格选用 MIT / Apache-2.0 开源合规模型。
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")

BASE_DIR = Path(__file__).resolve().parent.parent
WEIGHTS_DIR = BASE_DIR / "weights"

MODELS = [
    {
        "name": "FasterLivePortrait (人像特征提取与微表情基底驱动 - MIT 协议)",
        "repo_id": "warmshao/FasterLivePortrait",
        "local_dir": WEIGHTS_DIR / "liveportrait",
    },
    {
        "name": "MuseTalk (实时潜空间音频驱动嘴型同步 - MIT 协议)",
        "repo_id": "TMElyralab/MuseTalk",
        "local_dir": WEIGHTS_DIR / "musetalk",
    },
    {
        "name": "SenseVoiceSmall (本地超低延迟语音与情绪识别 - Apache-2.0 协议)",
        "repo_id": "FunAudioLLM/SenseVoiceSmall",
        "local_dir": WEIGHTS_DIR / "sensevoice",
    },
]


def main():
    print("=" * 68)
    print("🚀 RTX 5060 Ti (8GB) 写实 AI 伴侣模型权重下载器")
    print(f"📂 目标存放路径: {WEIGHTS_DIR}")
    print(f"🌐 当前镜像节点: {os.environ.get('HF_ENDPOINT')}")
    print("=" * 68)

    try:
        from huggingface_hub import snapshot_download
    except ImportError:
        print("❌ 未检测到 huggingface_hub，请先运行: pip install huggingface-hub")
        sys.exit(1)

    WEIGHTS_DIR.mkdir(parents=True, exist_ok=True)

    for item in MODELS:
        print(f"\n⏳ 正在拉取: {item['name']} ({item['repo_id']})...")
        item["local_dir"].mkdir(parents=True, exist_ok=True)
        try:
            snapshot_download(
                repo_id=item["repo_id"],
                local_dir=str(item["local_dir"]),
                local_dir_use_symlinks=False,
                resume_download=True,
            )
            print(f"✅ 下载完成: {item['local_dir']}")
        except Exception as e:
            print(f"⚠️ 下载 {item['repo_id']} 时遇到网络波动: {e}")
            print("   你可以稍后重新运行本脚本，支持断点续传。")

    print("\n🎉 所有核心模型检查完毕！现在可以在 .env 中设置 AVATAR_MODE=liveportrait 并运行 python main.py")


if __name__ == "__main__":
    main()
