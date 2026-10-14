@echo off
chcp 65001 >nul
echo ====================================================================
echo 🚀 正在将 AI 伴侣系统 (Industrial v3.1) 代码与文档推送到 GitHub...
echo 📂 目标仓库: https://github.com/qq601359558/friend.git
echo ====================================================================

if not exist ".git" (
    git init
    git branch -M main
    git remote add origin https://github.com/qq601359558/friend.git
)

git add .
git commit -m "feat: upgrade to v3.1 industrial full-duplex companion (streaming TTS, memory, vision, CosyVoice2)"
git push -u origin main

echo ====================================================================
echo ✅ 推送流程执行完毕！
echo ====================================================================
pause
