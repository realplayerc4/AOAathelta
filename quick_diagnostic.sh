#!/bin/bash

# 快速诊断脚本 - 直接在树莓派上运行
# 使用方法: bash quick_diagnostic.sh

echo "======================================"
echo "🔍 AOA Beacon 快速诊断"
echo "======================================"
echo ""

echo "1️⃣ 检查串口设备"
echo "=================================="
echo ""

if [ -e /dev/ttyUSB0 ]; then
    echo "✓ /dev/ttyUSB0 存在"
    ls -la /dev/ttyUSB0
else
    echo "✗ /dev/ttyUSB0 不存在"
fi

echo ""
if [ -e /dev/ttyUSB1 ]; then
    echo "✓ /dev/ttyUSB1 存在"
    ls -la /dev/ttyUSB1
else
    echo "✗ /dev/ttyUSB1 不存在"
fi

echo ""
if [ -e /dev/ttyACM0 ]; then
    echo "✓ /dev/ttyACM0 存在"
    ls -la /dev/ttyACM0
else
    echo "✗ /dev/ttyACM0 不存在"
fi

echo ""
echo "列出所有 /dev/tty* 设备:"
ls -la /dev/tty* 2>/dev/null | grep -E 'USB|ACM|AMA|S0' || echo "  (没有找到标准串口设备)"

echo ""
echo ""
echo "2️⃣ 检查 USB 设备"
echo "=================================="
lsusb || echo "⚠️  lsusb 未安装"

echo ""
echo ""
echo "3️⃣ 检查用户权限"
echo "=================================="
echo "当前用户: $(whoami)"
echo "用户组: $(groups)"

echo ""
echo "检查 dialout 组:"
getent group dialout || echo "⚠️ dialout 组不存在"

echo ""
echo ""
echo "4️⃣ 检查 Python 环境"
echo "=================================="
python3 --version
pip3 --version || echo "⚠️ pip3 未安装"

echo ""
echo "检查必要的 Python 模块:"
python3 -c "import flask" 2>&1 && echo "  ✓ flask" || echo "  ✗ flask"
python3 -c "import serial" 2>&1 && echo "  ✓ pyserial" || echo "  ✗ pyserial"
python3 -c "import numpy" 2>&1 && echo "  ✓ numpy" || echo "  ✗ numpy"
python3 -c "import requests" 2>&1 && echo "  ✓ requests" || echo "  ✗ requests"

echo ""
echo ""
echo "5️⃣ 检查项目文件"
echo "=================================="
cd /home/han16/AOAathelta 2>/dev/null || { echo "❌ 无法进入项目目录"; exit 1; }

files=("beacon_filter_service.py" "web_app.py" "start_services.py" "config.py" "requirements.txt")
for file in "${files[@]}"; do
    if [ -f "$file" ]; then
        echo "  ✓ $file"
    else
        echo "  ✗ $file (缺失)"
    fi
done

echo ""
echo ""
echo "6️⃣ 检查系统信息"
echo "=================================="
echo "系统: $(uname -s)"
echo "发行版: $(cat /etc/os-release 2>/dev/null | grep PRETTY_NAME | cut -d'=' -f2 | tr -d '\"')"
echo "内核: $(uname -r)"
echo "架构: $(uname -m)"

echo ""
echo ""
echo "✅ 诊断完成"
echo ""
echo "📝 建议:"
echo "  1. 如果找到了串口设备，可以尝试运行:"
echo "     python3 beacon_filter_service.py"
echo ""
echo "  2. 如果没有找到串口设备，检查:"
echo "     • Beacon 设备硬件连接"
echo "     • USB 驱动是否正确安装"
echo "     • 系统日志: dmesg | tail -30"
echo ""
echo "  3. 如果权限不足，运行:"
echo "     sudo usermod -a -G dialout $USER"
echo "     然后重新登录 SSH"
echo ""
