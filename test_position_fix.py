#!/usr/bin/env python
"""
测试小车位置显示修复的脚本
"""
import sys
import logging
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from ui.widgets.map_viewer import MapViewerDialog, MapViewerWidget

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def test_position_display():
    """测试位置显示功能"""
    
    logger.info("=" * 80)
    logger.info("开始测试小车位置显示修复")
    logger.info("=" * 80)
    
    # 创建应用
    app = QApplication(sys.argv)
    
    # 测试用的地图数据
    test_map_data = {
        "topic": "/map",
        "resolution": 0.1,  # 0.1米/像素
        "size": [182, 59],  # 182x59像素
        "origin": [-8.1, -4.8],  # 原点：(-8.1, -4.8)米
        "data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="  # 最小PNG
    }
    
    # 计算地图范围
    map_x_min = test_map_data['origin'][0]
    map_x_max = map_x_min + test_map_data['size'][0] * test_map_data['resolution']
    map_y_min = test_map_data['origin'][1]
    map_y_max = map_y_min + test_map_data['size'][1] * test_map_data['resolution']
    
    logger.info(f"\n📊 测试地图信息:")
    logger.info(f"  分辨率: {test_map_data['resolution']} m/px")
    logger.info(f"  尺寸: {test_map_data['size'][0]}x{test_map_data['size'][1]} px")
    logger.info(f"  原点: ({test_map_data['origin'][0]}, {test_map_data['origin'][1]}) m")
    logger.info(f"  X范围: [{map_x_min:.2f}, {map_x_max:.2f}] m")
    logger.info(f"  Y范围: [{map_y_min:.2f}, {map_y_max:.2f}] m")
    
    # 测试场景
    test_scenarios = [
        {
            "name": "场景1: 小车在地图范围内",
            "pose": {"pos": [0.0, 0.0], "ori": 0.0},
            "beacon": {"m_x": 1.0, "m_y": 0.5, "confidence": 0.95, "tag_id": 1},
        },
        {
            "name": "场景2: 小车在地图边缘",
            "pose": {"pos": [10.0, 1.0], "ori": 1.57},  # 接近X最大值
            "beacon": {"m_x": 10.5, "m_y": 1.2, "confidence": 0.85, "tag_id": 1},
        },
        {
            "name": "场景3: 小车稍微超出地图范围（Y方向）",
            "pose": {"pos": [2.5, 1.3], "ori": 0.785},  # Y=1.3 > Y_max=1.1
            "beacon": {"m_x": 3.0, "m_y": 1.5, "confidence": 0.90, "tag_id": 1},
        },
        {
            "name": "场景4: 小车在地图左下角",
            "pose": {"pos": [-8.0, -4.7], "ori": 3.14},
            "beacon": {"m_x": -7.5, "m_y": -4.5, "confidence": 0.80, "tag_id": 1},
        },
    ]
    
    # 创建地图查看器对话框
    dialog = MapViewerDialog()
    dialog.setWindowTitle("小车位置显示测试")
    dialog.update_map(test_map_data)
    
    # 测试每个场景
    current_scenario = [0]  # 使用列表以便在闭包中修改
    
    def update_scenario():
        if current_scenario[0] >= len(test_scenarios):
            logger.info("\n" + "=" * 80)
            logger.info("✅ 所有测试场景完成！")
            logger.info("=" * 80)
            logger.info("\n请检查地图查看器窗口：")
            logger.info("  - 地图上是否显示了位置标注？")
            logger.info("  - 详细信息面板是否显示了位置状态？")
            logger.info("  - 日志中是否有详细的调试信息？")
            return
        
        scenario = test_scenarios[current_scenario[0]]
        logger.info(f"\n{'='*80}")
        logger.info(f"测试 {scenario['name']}")
        logger.info(f"{'='*80}")
        
        pose = scenario['pose']
        beacon = scenario['beacon']
        
        logger.info(f"🚗 设置小车位置:")
        logger.info(f"   位置: ({pose['pos'][0]:.2f}, {pose['pos'][1]:.2f}) m")
        logger.info(f"   朝向: {pose['ori']:.2f} rad ({pose['ori']*180/3.14159:.1f}°)")
        
        # 检查是否在地图范围内
        in_x = map_x_min <= pose['pos'][0] <= map_x_max
        in_y = map_y_min <= pose['pos'][1] <= map_y_max
        status = "✅ 在范围内" if (in_x and in_y) else "⚠️ 超出范围"
        logger.info(f"   状态: {status}")
        
        logger.info(f"\n🔴 设置Beacon位置:")
        logger.info(f"   位置: ({beacon['m_x']:.2f}, {beacon['m_y']:.2f}) m")
        logger.info(f"   置信度: {beacon['confidence']:.2f}")
        
        # 检查beacon是否在地图范围内
        in_x = map_x_min <= beacon['m_x'] <= map_x_max
        in_y = map_y_min <= beacon['m_y'] <= map_y_max
        status = "✅ 在范围内" if (in_x and in_y) else "⚠️ 超出范围"
        logger.info(f"   状态: {status}")
        
        # 更新显示
        dialog.update_tracked_pose(pose)
        dialog.update_beacon_position(beacon)
        
        logger.info(f"\n➡️  请查看地图查看器窗口，按回车键继续下一个场景...")
        
        current_scenario[0] += 1
        
        # 3秒后自动切换到下一个场景
        QTimer.singleShot(3000, update_scenario)
    
    # 显示对话框
    dialog.show()
    
    # 启动第一个场景
    QTimer.singleShot(500, update_scenario)
    
    # 运行应用
    sys.exit(app.exec())


if __name__ == "__main__":
    test_position_display()
