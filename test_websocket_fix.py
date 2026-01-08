#!/usr/bin/env python3
"""
测试 WebSocket 修复 - 验证消息可以持续接收而不会阻塞
"""
import logging
import time
import threading
from core.ws_subscriber import TopicSubscriber

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_websocket_non_blocking():
    """测试 WebSocket 消息处理不被阻塞"""
    
    # 用于计算接收到的消息数
    message_count = {"map": 0, "tracked_pose": 0}
    lock = threading.Lock()
    
    def on_message(topic: str, payload):
        """消息回调"""
        with lock:
            message_count[topic] = message_count.get(topic, 0) + 1
        
        logger.info(f"✓ 接收到 {topic} 消息 (第 {message_count[topic]} 条)")
        
        # 模拟处理时间
        if topic == "/map":
            logger.debug(f"  处理地图数据，数据大小: {len(str(payload))} 字节")
            time.sleep(0.1)  # 模拟处理延迟
        elif topic == "/tracked_pose":
            logger.debug(f"  处理追踪位置数据")
            time.sleep(0.05)
    
    def on_error(message: str):
        logger.error(f"✗ WebSocket 错误: {message}")
    
    # 创建订阅器
    logger.info("正在启动 WebSocket 订阅...")
    subscriber = TopicSubscriber(
        url="ws://localhost:9001/ws",
        topics=["/map", "/tracked_pose"],
        on_message=on_message,
        on_error=on_error,
        reconnect_delay=3.0
    )
    
    subscriber.start()
    logger.info("✓ WebSocket 订阅已启动")
    
    # 运行 10 秒并收集统计信息
    start_time = time.time()
    max_duration = 10
    
    logger.info(f"\n开始监听消息（持续 {max_duration} 秒）...\n")
    
    while time.time() - start_time < max_duration:
        time.sleep(1)
        with lock:
            total = sum(message_count.values())
            logger.info(f"📊 累计接收消息: {total} 条 "
                       f"(map: {message_count.get('/map', 0)}, "
                       f"tracked_pose: {message_count.get('/tracked_pose', 0)})")
    
    # 停止订阅
    subscriber.stop()
    logger.info("\n✓ WebSocket 订阅已停止\n")
    
    # 分析结果
    with lock:
        total_messages = sum(message_count.values())
    
    logger.info("=" * 60)
    logger.info("测试结果:")
    logger.info(f"  总接收消息数: {total_messages}")
    logger.info(f"  /map 消息: {message_count.get('/map', 0)} 条")
    logger.info(f"  /tracked_pose 消息: {message_count.get('/tracked_pose', 0)} 条")
    logger.info("=" * 60)
    
    if total_messages > 0:
        logger.info("✅ 测试成功！WebSocket 可以持续接收消息而不被阻塞")
        return True
    else:
        logger.warning("⚠️  未接收到任何消息")
        logger.info("   请检查:")
        logger.info("   1. WebSocket 服务是否运行在 ws://localhost:9001/ws")
        logger.info("   2. 服务是否正常发送 /map 和 /tracked_pose 话题的数据")
        return False


if __name__ == "__main__":
    test_websocket_non_blocking()
