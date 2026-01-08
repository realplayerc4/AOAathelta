#!/usr/bin/env python3
"""
诊断工具 - 帮助诊断蓝色点消失和数据更新问题
"""
import sys
import logging
import time
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import Qt

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('diagnosis.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


def check_websocket_connection():
    """检查 WebSocket 连接"""
    logger.info("\n" + "="*60)
    logger.info("检查 1: WebSocket 连接")
    logger.info("="*60)
    
    try:
        import websocket
        logger.info("✓ websocket-client 已安装")
    except ImportError:
        logger.error("✗ websocket-client 未安装")
        logger.error("  请运行: pip install websocket-client")
        return False
    
    try:
        import config
        logger.info(f"✓ 配置加载成功")
        logger.info(f"  WebSocket URL: {config.API_WS_URL}")
        return True
    except Exception as e:
        logger.error(f"✗ 配置加载失败: {e}")
        return False


def check_threading_support():
    """检查线程池支持"""
    logger.info("\n" + "="*60)
    logger.info("检查 2: 线程池支持")
    logger.info("="*60)
    
    try:
        from concurrent.futures import ThreadPoolExecutor
        logger.info("✓ concurrent.futures.ThreadPoolExecutor 可用")
        
        # 测试线程池
        with ThreadPoolExecutor(max_workers=2) as executor:
            def dummy_task():
                return "success"
            
            future = executor.submit(dummy_task)
            result = future.result(timeout=1)
            if result == "success":
                logger.info("✓ 线程池工作正常")
                return True
    except Exception as e:
        logger.error(f"✗ 线程池测试失败: {e}")
        return False


def check_pyqt6_signals():
    """检查 PyQt6 信号机制"""
    logger.info("\n" + "="*60)
    logger.info("检查 3: PyQt6 信号机制")
    logger.info("="*60)
    
    try:
        from PyQt6.QtCore import QObject, pyqtSignal
        logger.info("✓ PyQt6 信号机制可用")
        
        # 测试信号
        class TestSignal(QObject):
            test_signal = pyqtSignal(str)
        
        obj = TestSignal()
        signal_triggered = False
        
        def on_signal(msg):
            nonlocal signal_triggered
            signal_triggered = True
        
        obj.test_signal.connect(on_signal)
        obj.test_signal.emit("test")
        
        if signal_triggered:
            logger.info("✓ 信号发射和连接工作正常")
            return True
        else:
            logger.error("✗ 信号未被触发")
            return False
    except Exception as e:
        logger.error(f"✗ PyQt6 信号测试失败: {e}")
        return False


def check_websocket_subscriber():
    """检查修改后的 WebSocket 订阅器"""
    logger.info("\n" + "="*60)
    logger.info("检查 4: WebSocket 订阅器")
    logger.info("="*60)
    
    try:
        from core.ws_subscriber import TopicSubscriber
        logger.info("✓ TopicSubscriber 导入成功")
        
        # 检查线程池初始化
        import inspect
        source = inspect.getsource(TopicSubscriber.__init__)
        if "ThreadPoolExecutor" in source:
            logger.info("✓ 检测到 ThreadPoolExecutor 初始化")
            return True
        else:
            logger.error("✗ 未检测到 ThreadPoolExecutor")
            return False
    except Exception as e:
        logger.error(f"✗ WebSocket 订阅器检查失败: {e}")
        return False


def check_beacon_update_logic():
    """检查 beacon 更新逻辑"""
    logger.info("\n" + "="*60)
    logger.info("检查 5: Beacon 更新逻辑")
    logger.info("="*60)
    
    try:
        from ui.main_window import MainWindow
        import inspect
        
        source = inspect.getsource(MainWindow._on_topic_message_ui)
        
        checks = {
            "自动删除 hasattr 检查": "beacon_global_position" in source and "hasattr" not in source,
            "直接检查 beacon_global_position": "if self.beacon_global_position" in source,
            "调试日志": "logger.debug" in source,
            "地图话题处理": "if topic == \"/map\"" in source,
            "追踪位置话题处理": "elif topic == \"/tracked_pose\"" in source,
        }
        
        all_passed = True
        for check_name, passed in checks.items():
            if passed:
                logger.info(f"  ✓ {check_name}")
            else:
                logger.warning(f"  ⚠ {check_name}")
                all_passed = all_passed and passed
        
        return all_passed
    except Exception as e:
        logger.error(f"✗ Beacon 更新逻辑检查失败: {e}")
        return False


def generate_report():
    """生成诊断报告"""
    logger.info("\n\n" + "="*60)
    logger.info("诊断报告生成")
    logger.info("="*60)
    
    checks = [
        ("WebSocket 连接", check_websocket_connection),
        ("线程池支持", check_threading_support),
        ("PyQt6 信号", check_pyqt6_signals),
        ("WebSocket 订阅器", check_websocket_subscriber),
        ("Beacon 更新逻辑", check_beacon_update_logic),
    ]
    
    results = []
    for name, check_func in checks:
        try:
            result = check_func()
            results.append((name, result))
        except Exception as e:
            logger.error(f"检查失败: {name} - {e}")
            results.append((name, False))
    
    logger.info("\n" + "="*60)
    logger.info("诊断摘要")
    logger.info("="*60)
    
    passed_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    for name, result in results:
        status = "✓ 通过" if result else "✗ 失败"
        logger.info(f"{status}: {name}")
    
    logger.info("\n" + f"总体: {passed_count}/{total_count} 检查通过")
    
    if passed_count == total_count:
        logger.info("\n✅ 所有检查通过！修复应该有效。")
        logger.info("\n后续步骤:")
        logger.info("  1. 运行应用: python main.py")
        logger.info("  2. 观察蓝色点是否持续显示和更新")
        logger.info("  3. 查看日志确认数据持续更新")
    else:
        logger.warning(f"\n⚠️  {total_count - passed_count} 个检查失败，请检查上面的错误信息")
    
    return passed_count == total_count


if __name__ == "__main__":
    logger.info("开始诊断...")
    logger.info("日志也被保存到 diagnosis.log")
    
    success = generate_report()
    sys.exit(0 if success else 1)
