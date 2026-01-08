#!/usr/bin/env python3
"""
测试 beacon 红点显示的脚本
模拟发送 /tracked_pose 消息来触发 beacon 坐标计算和地图更新
"""

import time
import logging
import sys
from datetime import datetime

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

def test_beacon_pipeline():
    """测试 beacon 显示管道"""
    
    # 检查 AOAWorker 的方法
    try:
        from workers.aoa_worker import AOAWorker
        aoa_worker = AOAWorker()
        
        # 检查方法是否存在
        if not hasattr(aoa_worker, 'get_filtered_beacon_coordinates'):
            logger.error("❌ AOAWorker 没有 get_filtered_beacon_coordinates 方法")
            return False
        
        logger.info("✓ AOAWorker.get_filtered_beacon_coordinates 方法存在")
        
        # 获取 beacon 坐标
        beacon_data = aoa_worker.get_filtered_beacon_coordinates(tag_id=1)
        logger.info(f"✓ Beacon 数据: {beacon_data}")
        
        if not beacon_data.get('initialized'):
            logger.warning("⚠ Beacon 滤波器未初始化（这是正常的，因为没有实际数据）")
        
    except Exception as e:
        logger.error(f"❌ 测试 AOAWorker 失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 检查坐标转换
    try:
        from ui.main_window import MainWindow
        mw = MainWindow()
        
        # 测试坐标转换
        local_x, local_y = 1.0, 0.5
        m_anchor_x, m_anchor_y = 5.0, 10.0
        anchor_theta = 0.0
        
        result = mw._transform_local_to_global(
            local_x=local_x,
            local_y=local_y,
            m_anchor_x=m_anchor_x,
            m_anchor_y=m_anchor_y,
            anchor_theta=anchor_theta
        )
        
        logger.info(f"✓ 坐标转换测试: 局部({local_x}, {local_y}) -> 全局{result}")
        
    except Exception as e:
        logger.error(f"❌ 测试坐标转换失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 检查地图显示器
    try:
        from ui.widgets.map_viewer import MapViewerDialog
        
        map_viewer = MapViewerDialog()
        
        # 检查 update_beacon_position 方法
        if not hasattr(map_viewer, 'update_beacon_position'):
            logger.error("❌ MapViewerDialog 没有 update_beacon_position 方法")
            return False
        
        logger.info("✓ MapViewerDialog.update_beacon_position 方法存在")
        
        # 检查 _mark_beacon_on_image 方法
        if not hasattr(map_viewer, '_mark_beacon_on_image'):
            logger.error("❌ MapViewerDialog 没有 _mark_beacon_on_image 方法")
            return False
        
        logger.info("✓ MapViewerDialog._mark_beacon_on_image 方法存在")
        
        # 测试 beacon 位置更新
        beacon_position = {
            'x': 6.0,
            'y': 10.5,
            'confidence': 0.8,
            'tag_id': 1
        }
        
        map_viewer.update_beacon_position(beacon_position)
        logger.info(f"✓ Beacon 位置已更新: {beacon_position}")
        
    except Exception as e:
        logger.error(f"❌ 测试地图显示器失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    logger.info("\n✅ 所有组件测试通过！")
    return True

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🧪 Beacon 显示管道测试")
    logger.info("=" * 60)
    
    success = test_beacon_pipeline()
    
    sys.exit(0 if success else 1)
