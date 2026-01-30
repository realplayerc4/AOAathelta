#!/bin/bash

# 停止脚本 - 只停止占用端口的旧服务，不启动新服务

set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$PROJECT_DIR"

# 获取占用端口的 PID（尽量兼容不同系统工具）
get_listening_pids() {
    local port="$1"

    if command -v lsof >/dev/null 2>&1; then
        lsof -nP -t -iTCP:"$port" -sTCP:LISTEN 2>/dev/null | sort -u
        return 0
    fi

    if command -v ss >/dev/null 2>&1; then
        ss -lptn "sport = :$port" 2>/dev/null | sed -n 's/.*pid=\([0-9]\+\).*/\1/p' | sort -u
        return 0
    fi

    if command -v netstat >/dev/null 2>&1; then
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
        echo "✓ 端口 $port 未被占用（$name）"
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

echo "======================================================"
echo "AOA 定位系统 - 停止旧服务（stop-only）"
echo "======================================================"

stop_service_on_port 5001 "Beacon Filter Service"
stop_service_on_port 5000 "Web App"

echo "======================================================"
echo "✅ 停止操作完成"
echo "======================================================"
