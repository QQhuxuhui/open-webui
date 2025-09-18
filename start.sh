#!/bin/bash

# Open WebUI 启动脚本
# 确保使用中国HuggingFace镜像源，避免SSL连接问题

echo "🚀 正在启动 Open WebUI..."

# 激活conda环境
source /opt/anaconda3/bin/activate open-webui

# 设置HuggingFace镜像源
export HF_ENDPOINT=https://hf-mirror.com

# 设置工作目录
cd /usr/src/workspace/github/QQhuxuhui/open-webui/backend

# 运行数据库迁移
echo "📊 正在执行数据库迁移..."
python -c "
from open_webui.config import run_migrations
try:
    run_migrations()
    print('✅ 数据库迁移成功完成')
except Exception as e:
    print(f'❌ 数据库迁移失败: {e}')
    exit(1)
"

# 检查嵌入模型状态
echo "🔍 检查嵌入模型状态..."
python -c "
import os
cache_dir = os.path.expanduser('~/.cache/huggingface/hub/models--sentence-transformers--all-MiniLM-L6-v2')
if os.path.exists(cache_dir):
    print('✅ 嵌入模型已就绪')
else:
    print('⚠️ 首次启动将下载嵌入模型（约80MB）')
"

echo "🌐 启动 Open WebUI 服务器..."
echo "访问地址: http://localhost:8080"
echo "按 Ctrl+C 停止服务"

# 启动服务
python -m uvicorn open_webui.main:app --host 0.0.0.0 --port 8080 --reload