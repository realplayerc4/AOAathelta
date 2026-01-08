#!/usr/bin/env python3
"""
完整的交互式 beacon 测试 - 自动打开地图并测试红点显示
"""

import json
import base64
import logging
import sys
import time
import numpy as np
from io import BytesIO
from PIL import Image

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)

# 初始化 QApplication
from PyQt6.QtWidgets import QApplication, QMessageBox
from PyQt6.QtCore import QTimer

app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

def create_test_map_image(width: int = 200, height: int = 200) -> str:
    """创建测试地图图片"""
    img_array = np.ones((height, width, 3), dtype=np.uint8) * 200
    img = Image.fromarray(img_array, 'RGB')
    
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return img_base64

def test_beacon_display():
    """测试 beacon 显示"""
    
    from ui.main_window import MainWindow
    
    logger.info("=" * 60)
    logger.info("🧪 Beacon 红点显示完整测试")
    logger.info("=" * 60)
    
    # 创建主窗口
    logger.info("1️⃣ 创建主窗口...")
    main_window = MainWindow()
    main_window.show()
    
    # 处理初始化事件
    app.processEvents()
    
    # 创建模拟地图数据
    logger.info("2️⃣ 创建模拟地图数据...")
    map_data = {
        'topic': '/map',
        'resolution': 0.05,
        'size': [200, 200],
        'origin': [0, 0],
        'data': create_test_map_image(200, 200)
    }
    logger.info(f"   分辨率: {map_data['resolution']} m/px")
    logger.info(f"   尺寸: {map_data['size']} 像素")
    logger.info(f"   覆盖范围: {200 * 0.05} x {200 * 0.05} 米")
    
    # 发送地图数据（模拟 /map 话题）
    logger.info("3️⃣ 发送地图数据...")
    main_window._on_topic_message_ui("/map", map_data)
    app.processEvents()
    
    # 发送 /tracked_pose 数据（模拟 AMR 位置）
    logger.info("4️⃣ 发送 /tracked_pose 数据...")
    pose_data = {
        'topic': '/tracked_pose',
        'pos': [5.0, 5.0],
        'ori': 0.0
    }
    logger.info(f"   Anchor 位置: ({pose_data['pos'][0]}, {pose_data['pos'][1]}) 米")
    logger.info(f"   Anchor 朝向: {pose_data['ori']} 弧度")
    main_window._on_topic_message_ui("/tracked_pose", pose_data)
    app.processEvents()
    
    # 打开地图查看器
    logger.info("5️⃣ 打开地图查看器...")
    main_window._on_show_map_clicked()
    app.processEvents()
    
    # 确认地图查看器已打开
    if main_window.map_viewer_dialog and main_window.map_viewer_dialog.isVisible():
        logger.info("   ✅ 地图查看器已打开")
        
        # 显示说明
        logger.info("")
        logger.info("=" * 60)
        logger.info("📍 测试结果:")
        logger.info("=" * 60)
        logger.info("")
        logger.info("你应该在地图查看器中看到:")
        logger.info("  ✓ 一个白色背景的地图")
        logger.info("  ✓ 蓝色箭头 - Anchor 的位置和朝向（在地图中心）")
        logger.info("  ✓ 红色圆点 - Beacon 的位置（应该也在中心附近）")
        logger.info("")
        logger.info("如果你没有看到红色圆点，请检查:")
        logger.info("  □ 地图是否正确加载")
        logger.info("  □ Anchor 位置是否显示正确")
        logger.info("  □ 控制台是否有错误信息")
        logger.info("")
        logger.info("应用将在 10 秒后自动关闭...")
        logger.info("=" * 60)
        
        # 10 秒后关闭
        QTimer.singleShot(10000, app.quit)
    else:
        logger.error("   ❌ 无法打开地图查看器")
        QTimer.singleShot(2000, app.quit)
    
    app.exec()
    logger.info("\n✅ 测试完成！")

if __name__ == '__main__':
    test_beacon_display()
