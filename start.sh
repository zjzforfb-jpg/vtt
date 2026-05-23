#!/bin/bash

cd "$(dirname "$0")/api"

echo ""
echo "=============================================="
echo "     字幕校对工作台 启动中..."
echo "=============================================="
echo ""

LOCAL_IP=$(ifconfig | grep "inet " | grep -v 127.0.0.1 | head -n 1 | awk '{print $2}')

echo "  🌐 本地访问地址: http://localhost:8000"
if [ -n "$LOCAL_IP" ]; then
    echo "  🌐 局域网访问地址: http://$LOCAL_IP:8000"
else
    echo "  ⚠️  未检测到局域网IP"
fi
echo ""
echo "  按 Ctrl+C 停止服务"
echo "=============================================="
echo ""

pip install -q -r requirements.txt 2>/dev/null

python main.py
