#!/bin/bash

# AOA 定位系统 Web UI 启动脚本

echo "======================================"
echo "AOA 定位系统 - Web 可视化界面"
echo "======================================"
echo ""

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# 检查 Python 环境
echo "🔍 检查 Python 环境..."
if ! command -v python3 &> /dev/null; then
    echo "❌ 错误：未找到 Python 3"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo "✓ 找到 $PYTHON_VERSION"
echo ""

# 检查依赖包
echo "🔍 检查依赖包..."
REQUIRED_PACKAGES=("flask" "flask_cors" "pyserial" "requests" "numpy")

for package in "${REQUIRED_PACKAGES[@]}"; do
    if python3 -c "import ${package//_/-}" 2>/dev/null; then
        echo "✓ $package 已安装"
    else
        echo "⚠️  $package 未安装，即将安装..."
        pip3 install "$package" || {
            echo "❌ 安装 $package 失败"
            exit 1
        }
    fi
done
echo ""

# 检查必要的项目文件
echo "🔍 检查项目文件..."
required_files=(
    "web_app.py"
    "templates/index.html"
    "static/css/style.css"
    "static/js/map.js"
    "core/api_client.py"
    "workers/aoa_kalman_filter.py"
    "workers/aoa_serial_reader.py"
    "coordinate_transform.py"
    "load_baseline_map.py"
)

for file in "${required_files[@]}"; do
    if [ -f "$file" ]; then
        echo "✓ $file"
    else
        echo "❌ 缺少文件：$file"
        exit 1
    fi
done
echo ""

# 启动 Flask 应用
echo "🚀 启动 Flask 服务器..."
echo "📌 访问地址："
echo "   本地:      http://127.0.0.1:5000"
echo "   远程访问:  http://$(hostname -I | awk '{print $1}'):5000"
echo ""
echo "💡 按 Ctrl+C 停止服务器"
echo "======================================"
echo ""

# 启动应用
python3 web_app.py
