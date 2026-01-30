#!/bin/bash

# 启动脚本 - 同时启动 Beacon Filter Service (5001) 和 Web App (5000)

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

echo "======================================================"
echo "AOA 定位系统 - 一键启动脚本"
echo "======================================================"
echo ""

# 获取占用端口的 PID（尽量兼容不同系统工具）
get_listening_pids() {
    local port="$1"

    if command -v lsof >/dev/null 2>&1; then
        # macOS / 常见 Linux
        lsof -nP -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | sort -u
        return 0
    fi

    if command -v ss >/dev/null 2>&1; then
        # Linux: 从 ss 输出中提取 pid=
        ss -lptn "sport = :$port" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u
        return 0
    fi

    if command -v netstat >/dev/null 2>&1; then
        # 兜底：部分环境可能有 netstat
        netstat -lntp 2>/dev/null | awk -v p=":$port" '$4 ~ p {print $7}' | sed 's%/.*%%' | grep -E '^[0-9]+$' | sort -u
        return 0
    fi

    return 0
}

# 关闭占用端口的旧服务（优雅停止，必要时强杀）
stop_service_on_port() {
    local port="$1"
    local name="$2"

    local pids
    pids="$(get_listening_pids "$port" || true)"

    if [ -z "$pids" ]; then
        return 0
    fi

    echo "⚠️  发现端口 $port 已被占用（$name），尝试停止旧服务..."

    # 先 SIGTERM
    for pid in $pids; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "  - 发送 SIGTERM 到 PID $pid"
            kill "$pid" 2>/dev/null || true
        fi
    done

    # 等待最多 5 秒
    local end=$((SECONDS + 5))
    while [ $SECONDS -lt $end ]; do
        local still_running=""
        for pid in $pids; do
            if kill -0 "$pid" 2>/dev/null; then
                still_running="1"
                break
            fi
        done
        if [ -z "$still_running" ]; then
            echo "✅ 旧服务已停止（端口 $port）"
            return 0
        fi
        sleep 0.2
    done

    # 还活着就强杀
    for pid in $pids; do
        if kill -0 "$pid" 2>/dev/null; then
            echo "  - 发送 SIGKILL 到 PID $pid"
            kill -9 "$pid" 2>/dev/null || true
        fi
    done

    echo "✅ 旧服务已强制停止（端口 $port）"
}

# 检查端口是否仍被占用（用于停止后最终确认）
check_port_free() {
    local port="$1"
    if nc -z 127.0.0.1 "$port" 2>/dev/null; then
        echo "❌ 端口 $port 仍被占用，无法启动新服务"
        exit 1
    fi
}

# 启动前先关闭旧服务
stop_service_on_port 5001 "Beacon Filter Service"
stop_service_on_port 5000 "Web App"

check_port_free 5001
check_port_free 5000
echo "✓ 端口已释放，可启动服务"
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
