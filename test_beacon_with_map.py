#!/usr/bin/env python3
"""
完整的 beacon 显示测试 - 模拟 /map 和 /tracked_pose 消息
"""

import json
import base64
import logging
import sys
from io import BytesIO
from PIL import Image
import numpy as np

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# 初始化 QApplication
from PyQt6.QtWidgets import QApplication
app = QApplication.instance()
if app is None:
    app = QApplication(sys.argv)

def create_test_map_image(width: int = 200, height: int = 200) -> str:
    """创建测试地图图片（白色背景）"""
    # 创建白色图片
    img_array = np.ones((height, width, 3), dtype=np.uint8) * 200
    img = Image.fromarray(img_array, 'RGB')
    
    # 转换为 base64
    buffered = BytesIO()
    img.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()
    
    return img_base64

def test_beacon_with_map():
    """测试 beacon 显示与地图数据"""
    
    from ui.main_window import MainWindow
    from ui.widgets.map_viewer import MapViewerDialog
    
    logger.info("创建主窗口...")
    main_window = MainWindow()
    
    logger.info("创建地图查看器...")
    map_viewer = MapViewerDialog(main_window)
    
    # 创建测试地图数据
    logger.info("创建测试地图数据...")
    test_map_data = {
        'topic': '/map',
        'resolution': 0.05,  # 0.05 米/像素
        'size': [200, 200],  # 200x200 像素
        'origin': [0, 0],    # 原点在 (0, 0)
        'data': create_test_map_image(200, 200)
    }
    
    logger.info(f"地图数据: 分辨率={test_map_data['resolution']}m/px, "
               f"尺寸={test_map_data['size']}, 原点={test_map_data['origin']}")
    
    # 更新地图
    logger.info("更新地图显示器...")
    map_viewer.update_map(test_map_data)
    
    # 模拟 beacon 位置（物理坐标）
    logger.info("模拟 beacon 全局坐标...")
    beacon_position = {
        'x': 5.0,  # 5 米
        'y': 5.0,  # 5 米
        'confidence': 0.8,
        'tag_id': 1
    }
    
    logger.info(f"Beacon 位置: {beacon_position}")
    logger.info(f"Beacon 像素位置: x_pixel={(beacon_position['x'] - 0) / 0.05:.1f}px, "
               f"y_pixel={200 - (beacon_position['y'] - 0) / 0.05:.1f}px")
    
    # 更新 beacon 位置
    logger.info("更新地图查看器中的 beacon 位置...")
    map_viewer.update_beacon_position(beacon_position)
    
    # 显示地图查看器
    logger.info("显示地图查看器窗口...")
    map_viewer.show()
    
    # 处理事件循环
    logger.info("运行事件循环（等待 3 秒）...")
    
    # 使用 QTimer 在 3 秒后退出
    from PyQt6.QtCore import QTimer
    timer = QTimer()
    timer.timeout.connect(app.quit)
    timer.start(3000)
    
    app.exec()
    
    logger.info("✅ 测试完成！检查地图窗口中是否显示红色圆点")
    
    return True

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🧪 Beacon 显示完整测试（包含地图）")
    logger.info("=" * 60)
    
    try:
        success = test_beacon_with_map()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
