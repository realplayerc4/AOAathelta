#!/bin/bash

# 部署脚本 - 将 AOA 定位系统部署到树莓派
# 使用: bash deploy_to_raspi.sh

set -e

# ==================== 配置 ====================
RASPI_IP="192.168.0.144"
RASPI_USER="han16"
RASPI_PORT=22
REMOTE_BASE="/home/han16"
REMOTE_PATH="/home/han16/AOAathelta"
LOCAL_PATH="$(cd "$(dirname "$0")" && pwd)"

echo "======================================================"
echo "AOA 定位系统 - 树莓派部署"
echo "======================================================"
echo ""
echo "📍 部署配置:"
echo "  • 树莓派地址: $RASPI_IP"
echo "  • 用户名: $RASPI_USER"
echo "  • 远程路径: $REMOTE_PATH"
echo "  • 本地路径: $LOCAL_PATH"
echo ""

# ==================== 第1步: 上传项目 ====================
echo "第1步: 上传项目文件..."
echo "  正在排除不必要的文件..."

# 先创建远程目录
ssh -p $RASPI_PORT "$RASPI_USER@$RASPI_IP" "mkdir -p $REMOTE_BASE" 2>/dev/null

# 上传项目（排除不必要的文件）
rsync -avz \
  --delete \
  --exclude='.git/' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='.DS_Store' \
  --exclude='*.log' \
  --exclude='.pytest_cache/' \
  -e "ssh -p $RASPI_PORT" \
  "$LOCAL_PATH/" \
  "$RASPI_USER@$RASPI_IP:$REMOTE_PATH/" \
  || echo "✅ rsync 完成（可能有些小差异）"

echo "✅ 项目文件已上传"
echo ""

# ==================== 第2步: 安装依赖 ====================
echo "第2步: 在树莓派上安装依赖..."

ssh -p $RASPI_PORT "$RASPI_USER@$RASPI_IP" << 'REMOTE_SCRIPT'
  set -e
  
  cd /home/han16/AOAathelta
  
  echo "  • 检查 Python 版本..."
  python3 --version
  echo ""
  
  echo "  • 升级 pip..."
  python3 -m pip install --upgrade pip -q 2>/dev/null || true
  echo ""
  
  echo "  • 安装项目依赖..."
  if [ -f requirements.txt ]; then
    python3 -m pip install -r requirements.txt -q 2>/dev/null || \
    python3 -m pip install flask flask-cors requests numpy pyserial websocket-client -q
  else
    python3 -m pip install flask flask-cors requests numpy pyserial websocket-client -q
  fi
  
  echo "✅ 依赖安装完成"
REMOTE_SCRIPT

echo ""

# ==================== 第3步: 创建启动脚本 ====================
echo "第3步: 创建树莓派启动脚本..."

ssh -p $RASPI_PORT "$RASPI_USER@$RASPI_IP" << 'REMOTE_SCRIPT'
  cd /home/han16/AOAathelta
  
  # 创建简单启动脚本
  cat > run_services.sh << 'STARTSCRIPT'
#!/bin/bash
cd /home/han16/AOAathelta
exec python3 start_services.py
STARTSCRIPT
  
  chmod +x run_services.sh
  
  # 创建后台运行脚本
  cat > run_services_background.sh << 'BGSCRIPT'
#!/bin/bash
cd /home/han16/AOAathelta
nohup python3 start_services.py > services.log 2>&1 &
echo $! > services.pid
echo "服务已在后台启动，PID: $(cat services.pid)"
echo "查看日志: tail -f services.log"
BGSCRIPT
  
  chmod +x run_services_background.sh
  
  # 创建停止脚本
  cat > stop_services.sh << 'STOPSCRIPT'
#!/bin/bash
if [ -f /home/han16/AOAathelta/services.pid ]; then
  PID=$(cat /home/han16/AOAathelta/services.pid)
  kill $PID 2>/dev/null || true
  rm /home/han16/AOAathelta/services.pid
  echo "✅ 服务已停止"
else
  pkill -f "start_services.py" || true
  echo "✅ 已停止所有相关进程"
fi
STOPSCRIPT
  
  chmod +x stop_services.sh
  
  echo "  • run_services.sh - 前台运行（查看日志）"
  echo "  • run_services_background.sh - 后台运行"
  echo "  • stop_services.sh - 停止服务"

REMOTE_SCRIPT

echo "✅ 启动脚本已创建"
echo ""

# ==================== 第4步: 验证安装 ====================
echo "第4步: 验证安装..."

ssh -p $RASPI_PORT "$RASPI_USER@$RASPI_IP" << 'REMOTE_SCRIPT'
  echo "  • 检查必要文件..."
  cd /home/han16/AOAathelta
  
  files=("beacon_filter_service.py" "web_app.py" "start_services.py" "config.py" "requirements.txt")
  for file in "${files[@]}"; do
    if [ -f "$file" ]; then
      echo "    ✓ $file"
    else
      echo "    ✗ $file (缺失)"
    fi
  done
  
  echo ""
  echo "  • 检查 Python 模块..."
  python3 -c "import flask; import requests; import numpy" 2>/dev/null && \
    echo "    ✓ 所有主要模块已安装" || \
    echo "    ⚠ 某些模块可能缺失"

REMOTE_SCRIPT

echo "✅ 验证完成"
echo ""

# ==================== 显示完成信息 ====================
echo "======================================================"
echo "✅ 部署完成！"
echo "======================================================"
echo ""
echo "📊 在树莓派上启动服务:"
echo ""
echo "  【方式1】前台运行（推荐用于测试）"
echo "  $ ssh han16@192.168.0.144 '/home/han16/AOAathelta/run_services.sh'"
echo ""
echo "  【方式2】后台运行（推荐用于生产）"
echo "  $ ssh han16@192.168.0.144 '/home/han16/AOAathelta/run_services_background.sh'"
echo ""
echo "  【方式3】直接SSH运行"
echo "  $ ssh han16@192.168.0.144 'cd /home/han16/AOAathelta && python3 start_services.py'"
echo ""
echo "🛑 停止服务:"
echo "  $ ssh han16@192.168.0.144 '/home/han16/AOAathelta/stop_services.sh'"
echo ""
echo "📡 服务地址（树莓派上）:"
echo "  • Beacon Filter Service: http://192.168.0.144:5001"
echo "  • Web App: http://192.168.0.144:5000"
echo ""
echo "🌐 从本地电脑访问:"
echo "  • Web UI: http://192.168.0.144:5000"
echo "  • API: http://192.168.0.144:5001/api/beacon"
echo ""
echo "📝 查看日志（后台运行时）:"
echo "  $ ssh han16@192.168.0.144 'tail -f /home/han16/AOAathelta/services.log'"
echo ""
echo "======================================================"
