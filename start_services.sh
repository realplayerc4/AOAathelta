#!/bin/bash

# 启动脚本 - 同时启动 Beacon Filter Service (5001) 和 Web App (5000)

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "======================================================"
echo "AOA 定位系统 - 一键启动脚本"
echo "======================================================"
echo ""

# 检查端口是否被占用
check_port() {
    if nc -z 127.0.0.1 "$1" 2>/dev/null; then
        echo "❌ 端口 $1 已被占用，请先停止其他服务"
        exit 1
    fi
}

check_port 5001
check_port 5000
echo "✓ 端口检查完成"
echo ""

# 启动 Beacon Filter Service
echo "🚀 启动 Beacon Filter Service (5001)..."
python3 beacon_filter_service.py &
BEACON_PID=$!
echo "✅ Beacon Filter Service 已启动 (PID $BEACON_PID)"
echo ""

# 等待 beacon 服务启动
sleep 2

# 启动 Web App
echo "🚀 启动 Web App (5000)..."
python3 web_app.py &
WEB_PID=$!
echo "✅ Web App 已启动 (PID $WEB_PID)"
echo ""

echo "======================================================"
echo "✅ 所有服务已启动"
echo "======================================================"
echo ""
echo "📊 服务信息:"
echo "  • Beacon Filter Service: http://127.0.0.1:5001"
echo "    - API: /api/beacon (获取滤波数据)"
echo "    - API: /api/stats (获取统计信息)"
echo ""
echo "  • Web UI: http://127.0.0.1:5000"
echo "    - 实时定位可视化界面"
echo ""
echo "📝 按 Ctrl+C 停止所有服务"
echo "======================================================"
echo ""

# 捕获 Ctrl+C 信号
trap "kill $BEACON_PID $WEB_PID; echo ''; echo '✅ 所有服务已停止'; exit 0" SIGINT SIGTERM

# 等待进程
wait
