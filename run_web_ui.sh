#!/bin/bash

# 🤖 AOA 定位系统 Web UI - 完整启动脚本

set -e

echo "======================================"
echo "🤖 AOA 定位系统 - Web 可视化界面"
echo "======================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 工作目录: $SCRIPT_DIR"
echo ""

# 检查 Python 环境
echo "🔍 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误: 未找到 Python 3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
echo "✓ Python $PYTHON_VERSION"
echo ""

# 检查必需的包
echo "📦 检查必需的包..."
PACKAGES=("flask" "requests" "numpy" "pyserial")
for pkg in "${PACKAGES[@]}"; do
    python3 -c "import ${pkg}" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "  ✓ $pkg"
    else
        echo "  ⚠ 安装 $pkg..."
        pip3 install $pkg -q
        echo "  ✓ $pkg 已安装"
    fi
done
echo ""

# 显示使用说明
echo "📖 使用说明"
echo "======================================"
echo ""
echo "1. 打开浏览器访问："
echo "   👉 http://127.0.0.1:5000"
echo ""
echo "2. Web UI 功能："
echo "   • 实时显示小车位置（蓝色箭头）"
echo "   • 箭头指向表示小车朝向"
echo "   • 右下角显示具体坐标"
echo "   • 黄色矩形为用户绘制的检测区域"
echo "   • 红色圆点表示 Beacon 位置"
echo ""
echo "3. 启动步骤："
echo "   ① 点击'加载地图'按钮加载基准地图"
echo "   ② 点击'启动'按钮启动系统处理"
echo "   ③ 观察蓝色箭头实时显示小车位置"
echo ""
echo "4. 可选操作："
echo "   • 在地图上拖拽绘制矩形检测区域"
echo "   • 鼠标滚轮缩放地图"
echo "   • 拖拽地图移动视图"
echo ""
echo "5. API 测试（在另一个终端）："
echo "   # 获取小车位置"
echo "   curl http://127.0.0.1:5000/api/robot-pose | python3 -m json.tool"
echo ""
echo "   # 获取系统状态"
echo "   curl http://127.0.0.1:5000/api/status | python3 -m json.tool"
echo ""
echo "======================================"
echo ""
echo "🚀 启动 Web 服务器..."
echo "   (按 Ctrl+C 停止服务器)"
echo ""
echo "======================================"
echo ""

# 启动应用
python3 web_app.py

