#!/usr/bin/env python3
"""
启动脚本 - 同时启动 Beacon Filter Service (5001) 和 Web App (5000)
"""

import subprocess
import sys
import time
import signal
import os
import logging
from pathlib import Path

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 获取项目根目录
PROJECT_ROOT = Path(__file__).parent.absolute()

# 进程列表
processes = []

def signal_handler(sig, frame):
    """处理 Ctrl+C 信号"""
    logger.info("\n收到停止信号，正在关闭服务...")
    
    # 终止所有子进程
    for proc in processes:
        try:
            if proc.poll() is None:  # 进程仍在运行
                logger.info(f"正在停止进程 (PID {proc.pid})...")
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    logger.warning(f"进程未能在3秒内停止，强制杀死...")
                    proc.kill()
        except Exception as e:
            logger.error(f"停止进程时出错: {e}")
    
    logger.info("✅ 所有服务已停止")
    sys.exit(0)

def start_service(name, command, port):
    """启动一个服务"""
    logger.info(f"🚀 启动 {name}...")
    try:
        proc = subprocess.Popen(
            command,
            cwd=PROJECT_ROOT,
            stdin=subprocess.DEVNULL
        )
        processes.append(proc)
        logger.info(f"✅ {name} 已启动 (PID {proc.pid}) - 监听端口 {port}")
        return proc
    except Exception as e:
        logger.error(f"❌ 启动 {name} 失败: {e}")
        return None

def check_port_available(port):
    """检查端口是否可用"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result != 0

def main():
    """主函数"""
    logger.info("=" * 60)
    logger.info("AOA 定位系统 - 一键启动脚本")
    logger.info("=" * 60)
    
    # 检查端口是否被占用
    if not check_port_available(5001):
        logger.error("❌ 端口 5001 已被占用，请先停止其他服务")
        sys.exit(1)
    
    if not check_port_available(5000):
        logger.error("❌ 端口 5000 已被占用，请先停止其他服务")
        sys.exit(1)
    
    logger.info("✓ 端口检查完成")
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # 启动 Beacon Filter Service
    beacon_proc = start_service(
        "Beacon Filter Service (5001)",
        ["python3", "beacon_filter_service.py"],
        5001
    )
    
    if not beacon_proc:
        logger.error("❌ 无法启动 Beacon Filter Service，退出")
        sys.exit(1)
    
    # 等待 beacon 服务启动
    time.sleep(2)
    
    # 启动 Web App
    web_proc = start_service(
        "Web App (5000)",
        ["python3", "web_app.py"],
        5000
    )
    
    if not web_proc:
        logger.error("❌ 无法启动 Web App，退出")
        beacon_proc.terminate()
        sys.exit(1)
    
    # 等待服务启动完成
    time.sleep(2)
    
    logger.info("=" * 60)
    logger.info("✅ 所有服务已启动")
    logger.info("=" * 60)
    logger.info("")
    logger.info("📊 服务信息:")
    logger.info("  • Beacon Filter Service: http://127.0.0.1:5001")
    logger.info("    - API: /api/beacon (获取滤波数据)")
    logger.info("    - API: /api/stats (获取统计信息)")
    logger.info("")
    logger.info("  • Web UI: http://127.0.0.1:5000")
    logger.info("    - 实时定位可视化界面")
    logger.info("")
    logger.info("📝 按 Ctrl+C 停止所有服务")
    logger.info("=" * 60)
    logger.info("")
    
    # 监控进程
    try:
        while True:
            time.sleep(1)
            
            # 检查进程是否还在运行
            for i, proc in enumerate(processes):
                if proc.poll() is not None:  # 进程已退出
                    logger.error(f"❌ 进程 {i} (PID {proc.pid}) 已意外退出")
                    
                    # 终止所有进程
                    for p in processes:
                        if p.poll() is None:
                            p.terminate()
                    
                    sys.exit(1)
    
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == '__main__':
    main()
