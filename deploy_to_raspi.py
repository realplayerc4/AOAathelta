#!/usr/bin/env python3
"""
部署脚本 - 将 AOA 定位系统部署到树莓派

使用方法:
    python3 deploy_to_raspi.py
"""

import subprocess
import sys
import os
from pathlib import Path
import logging

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 配置
RASPI_IP = "192.168.0.144"
RASPI_USER = "han16"
RASPI_PORT = 22
REMOTE_BASE = "/home/han16"
REMOTE_PATH = "/home/han16/AOAathelta"
LOCAL_PATH = Path(__file__).parent.absolute()

class RaspiDeployer:
    """树莓派部署工具"""
    
    def __init__(self):
        self.ssh_cmd = f"ssh -p {RASPI_PORT} {RASPI_USER}@{RASPI_IP}"
        self.rsync_cmd = f"rsync -avz -e 'ssh -p {RASPI_PORT}' --delete"
    
    def run_ssh(self, command):
        """执行 SSH 命令"""
        full_cmd = f'{self.ssh_cmd} "{command}"'
        try:
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            if result.returncode != 0:
                logger.error(f"SSH 命令失败: {result.stderr}")
                return False
            if result.stdout:
                print(result.stdout.strip())
            return True
        except Exception as e:
            logger.error(f"执行 SSH 命令出错: {e}")
            return False
    
    def upload_project(self):
        """第1步: 上传项目文件"""
        logger.info("第1步: 上传项目文件...")
        
        # 创建远程目录
        self.run_ssh(f"mkdir -p {REMOTE_BASE}")
        
        # 上传项目
        exclude_patterns = [
            "--exclude='.git/'",
            "--exclude='__pycache__/'",
            "--exclude='*.pyc'",
            "--exclude='.DS_Store'",
            "--exclude='*.log'",
            "--exclude='.pytest_cache/'",
        ]
        
        cmd = f"{self.rsync_cmd} {' '.join(exclude_patterns)} {LOCAL_PATH}/ {RASPI_USER}@{RASPI_IP}:{REMOTE_PATH}/"
        
        try:
            subprocess.run(cmd, shell=True, check=False)
            logger.info("✅ 项目文件已上传")
            return True
        except Exception as e:
            logger.error(f"上传失败: {e}")
            return False
    
    def install_dependencies(self):
        """第2步: 安装依赖"""
        logger.info("第2步: 在树莓派上安装依赖...")
        
        install_script = """
cd /home/han16/AOAathelta

echo "  • 检查 Python 版本..."
python3 --version

echo "  • 升级 pip..."
python3 -m pip install --upgrade pip -q 2>/dev/null || true

echo "  • 安装项目依赖..."
if [ -f requirements.txt ]; then
  python3 -m pip install -r requirements.txt -q 2>/dev/null || \\
  python3 -m pip install flask flask-cors requests numpy pyserial websocket-client -q
else
  python3 -m pip install flask flask-cors requests numpy pyserial websocket-client -q
fi

echo "✅ 依赖安装完成"
"""
        
        return self.run_ssh(install_script.replace('\n', ' && '))
    
    def create_startup_scripts(self):
        """第3步: 创建启动脚本"""
        logger.info("第3步: 创建树莓派启动脚本...")
        
        # 前台启动脚本
        run_script = """#!/bin/bash
cd /home/han16/AOAathelta
exec python3 start_services.py"""
        
        # 后台启动脚本
        bg_script = """#!/bin/bash
cd /home/han16/AOAathelta
nohup python3 start_services.py > services.log 2>&1 &
echo $! > services.pid
echo "服务已在后台启动，PID: $(cat services.pid)"
echo "查看日志: tail -f services.log\"""" 
        
        # 停止脚本
        stop_script = """#!/bin/bash
if [ -f /home/han16/AOAathelta/services.pid ]; then
  PID=$(cat /home/han16/AOAathelta/services.pid)
  kill $PID 2>/dev/null || true
  rm /home/han16/AOAathelta/services.pid
  echo "✅ 服务已停止"
else
  pkill -f "start_services.py" || true
  echo "✅ 已停止所有相关进程"
fi"""
        
        # 上传脚本
        create_script = f"""
cat > /home/han16/AOAathelta/run_services.sh << 'EOF'
{run_script}
EOF

cat > /home/han16/AOAathelta/run_services_background.sh << 'EOF'
{bg_script}
EOF

cat > /home/han16/AOAathelta/stop_services.sh << 'EOF'
{stop_script}
EOF

chmod +x /home/han16/AOAathelta/run_services.sh
chmod +x /home/han16/AOAathelta/run_services_background.sh
chmod +x /home/han16/AOAathelta/stop_services.sh

echo "  • run_services.sh - 前台运行（查看日志）"
echo "  • run_services_background.sh - 后台运行"
echo "  • stop_services.sh - 停止服务"
"""
        
        return self.run_ssh(create_script)
    
    def verify_installation(self):
        """第4步: 验证安装"""
        logger.info("第4步: 验证安装...")
        
        verify_script = """
echo "  • 检查必要文件..."
cd /home/han16/AOAathelta

for file in beacon_filter_service.py web_app.py start_services.py config.py requirements.txt; do
  if [ -f "$file" ]; then
    echo "    ✓ $file"
  else
    echo "    ✗ $file (缺失)"
  fi
done

echo ""
echo "  • 检查 Python 模块..."
python3 -c "import flask; import requests; import numpy" 2>/dev/null && \\
  echo "    ✓ 所有主要模块已安装" || \\
  echo "    ⚠ 某些模块可能缺失"
"""
        
        return self.run_ssh(verify_script)
    
    def show_summary(self):
        """显示部署总结"""
        logger.info("")
        logger.info("=" * 60)
        logger.info("✅ 部署完成！")
        logger.info("=" * 60)
        logger.info("")
        logger.info("📊 在树莓派上启动服务:")
        logger.info("")
        logger.info("  【方式1】前台运行（推荐用于测试）")
        logger.info("  $ ssh han16@192.168.0.144 '/home/han16/AOAathelta/run_services.sh'")
        logger.info("")
        logger.info("  【方式2】后台运行（推荐用于生产）")
        logger.info("  $ ssh han16@192.168.0.144 '/home/han16/AOAathelta/run_services_background.sh'")
        logger.info("")
        logger.info("  【方式3】直接SSH运行")
        logger.info("  $ ssh han16@192.168.0.144 'cd /home/han16/AOAathelta && python3 start_services.py'")
        logger.info("")
        logger.info("🛑 停止服务:")
        logger.info("  $ ssh han16@192.168.0.144 '/home/han16/AOAathelta/stop_services.sh'")
        logger.info("")
        logger.info("📡 服务地址（树莓派上）:")
        logger.info("  • Beacon Filter Service: http://192.168.0.144:5001")
        logger.info("  • Web App: http://192.168.0.144:5000")
        logger.info("")
        logger.info("🌐 从本地电脑访问:")
        logger.info("  • Web UI: http://192.168.0.144:5000")
        logger.info("  • API: http://192.168.0.144:5001/api/beacon")
        logger.info("")
        logger.info("📝 查看日志（后台运行时）:")
        logger.info("  $ ssh han16@192.168.0.144 'tail -f /home/han16/AOAathelta/services.log'")
        logger.info("")
        logger.info("=" * 60)
    
    def deploy(self):
        """执行完整部署"""
        logger.info("=" * 60)
        logger.info("AOA 定位系统 - 树莓派部署")
        logger.info("=" * 60)
        logger.info("")
        logger.info("📍 部署配置:")
        logger.info(f"  • 树莓派地址: {RASPI_IP}")
        logger.info(f"  • 用户名: {RASPI_USER}")
        logger.info(f"  • 远程路径: {REMOTE_PATH}")
        logger.info(f"  • 本地路径: {LOCAL_PATH}")
        logger.info("")
        
        steps = [
            ("上传项目文件", self.upload_project),
            ("安装依赖", self.install_dependencies),
            ("创建启动脚本", self.create_startup_scripts),
            ("验证安装", self.verify_installation),
        ]
        
        for step_name, step_func in steps:
            if not step_func():
                logger.error(f"❌ {step_name} 失败")
                return False
            logger.info("")
        
        self.show_summary()
        return True


def main():
    """主函数"""
    try:
        deployer = RaspiDeployer()
        
        # 检查是否能连接树莓派
        logger.info("检查树莓派连接...")
        if not deployer.run_ssh("echo 'OK'"):
            logger.error(f"❌ 无法连接到树莓派 {RASPI_IP}")
            logger.error("请检查:")
            logger.error(f"  1. 树莓派 IP 地址是否正确: {RASPI_IP}")
            logger.error(f"  2. SSH 是否可访问")
            logger.error(f"  3. 用户名和密码是否正确: {RASPI_USER}")
            sys.exit(1)
        
        logger.info("✅ 树莓派连接成功")
        logger.info("")
        
        # 执行部署
        if deployer.deploy():
            logger.info("✅ 部署成功！")
            sys.exit(0)
        else:
            logger.error("❌ 部署失败")
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("\n已取消部署")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ 部署出错: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
