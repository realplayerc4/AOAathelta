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

def _get_listening_pids(port: int):
    """获取监听指定端口的 PID（尽量兼容不同系统工具）。"""
    candidates = []

    # 优先 lsof
    try:
        res = subprocess.run(
            ["lsof", "-nP", "-t", f"-iTCP:{port}", "-sTCP:LISTEN"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout.strip():
            for line in res.stdout.splitlines():
                line = line.strip()
                if line.isdigit():
                    candidates.append(int(line))
            return sorted(set(candidates))
    except FileNotFoundError:
        pass

    # 再尝试 ss
    try:
        res = subprocess.run(
            ["ss", "-lptn", f"sport = :{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout:
            import re
            for m in re.finditer(r"pid=(\d+)", res.stdout):
                candidates.append(int(m.group(1)))
            return sorted(set(candidates))
    except FileNotFoundError:
        pass

    # 兜底 netstat
    try:
        res = subprocess.run(
            ["netstat", "-lntp"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if res.returncode == 0 and res.stdout:
            for line in res.stdout.splitlines():
                if f":{port} " in line or line.rstrip().endswith(f":{port}"):
                    # 最后一列类似 "1234/python3"
                    parts = line.split()
                    if parts:
                        last = parts[-1]
                        pid = last.split("/", 1)[0]
                        if pid.isdigit():
                            candidates.append(int(pid))
            return sorted(set(candidates))
    except FileNotFoundError:
        pass

    return []


def _stop_processes(pids, name: str, timeout_sec: float = 5.0):
    if not pids:
        return

    logger.warning(f"⚠️  发现旧服务占用端口（{name}），尝试停止: {pids}")

    # 先 SIGTERM
    for pid in pids:
        try:
            os.kill(pid, 0)
        except OSError:
            continue
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            continue

    # 等待
    end = time.time() + timeout_sec
    while time.time() < end:
        alive = False
        for pid in pids:
            try:
                os.kill(pid, 0)
                alive = True
                break
            except OSError:
                continue
        if not alive:
            logger.info(f"✅ 旧服务已停止（{name}）")
            return
        time.sleep(0.2)

    # 强杀
    for pid in pids:
        try:
            os.kill(pid, 0)
        except OSError:
            continue
        try:
            os.kill(pid, signal.SIGKILL)
        except OSError:
            continue
    logger.info(f"✅ 旧服务已强制停止（{name}）")


def ensure_port_free(port: int, name: str):
    """若端口被占用则先停止占用进程，然后再次确认端口可用。"""
    if check_port_available(port):
        return

    pids = _get_listening_pids(port)
    _stop_processes(pids, f"{name} :{port}")

    # 再次确认
    if not check_port_available(port):
        logger.error(f"❌ 端口 {port} 仍被占用，无法启动新服务")
        sys.exit(1)

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
    
    # 启动前先关闭旧服务（若占用端口）
    ensure_port_free(5001, "Beacon Filter Service")
    ensure_port_free(5000, "Web App")
    
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
