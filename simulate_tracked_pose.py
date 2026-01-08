#!/usr/bin/env python3
"""
模拟发送 /tracked_pose 消息来测试 beacon 显示
"""

import json
import time
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)

def simulate_tracked_pose():
    """模拟发送 /tracked_pose 消息"""
    
    # 导入 WebSocket 模块
    import websocket
    import threading
    
    def on_message(ws, message):
        logger.info(f"收到消息: {message}")
    
    def on_error(ws, error):
        logger.error(f"WebSocket 错误: {error}")
    
    def on_close(ws, close_status_code, close_msg):
        logger.info("WebSocket 连接关闭")
    
    def on_open(ws):
        logger.info("WebSocket 连接已打开")
        
        # 发送 /tracked_pose 消息
        def run():
            for i in range(10):
                # 模拟 AMR 在 (5, 5) 处，朝向 0 弧度
                message = {
                    'topic': '/tracked_pose',
                    'pos': [5.0, 5.0],
                    'ori': 0.0
                }
                
                logger.info(f"发送 /tracked_pose: {message}")
                ws.send(json.dumps(message))
                time.sleep(1)
            
            ws.close()
        
        thread = threading.Thread(target=run)
        thread.daemon = True
        thread.start()
    
    # 连接到应用的 WebSocket（如果有的话）
    try:
        ws = websocket.WebSocketApp(
            "ws://localhost:9090",
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        logger.info("尝试连接到 ws://localhost:9090...")
        ws.run_forever()
    except Exception as e:
        logger.warning(f"无法连接到 WebSocket: {e}")
        logger.info("应用程序可能不支持 WebSocket，或者没有启动 WebSocket 服务器")
        
        # 尝试通过本地消息系统
        logger.info("尝试通过本地 IPC 发送消息...")
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        
        if app:
            logger.info("✅ 请手动打开地图查看器窗口以查看 beacon 标记")
            logger.info("你应该会看到一个红色圆点在地图中央")
        else:
            logger.error("❌ 无法访问 Qt 应用程序")

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🧪 模拟 /tracked_pose 消息")
    logger.info("=" * 60)
    
    simulate_tracked_pose()
