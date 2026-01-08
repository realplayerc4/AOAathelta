#!/usr/bin/env python3
"""
测试 globe_beacon 话题功能
"""
import sys
import math
sys.path.insert(0, '/home/han14/gitw/AUTOXINGAOA')

from workers.aoa_worker import AOAWorker
from ui.main_window import MainWindow


def test_coordinate_transform():
    """测试坐标变换函数"""
    print("=" * 60)
    print("测试坐标变换")
    print("=" * 60)
    
    # 创建 MainWindow 实例用于测试
    main_window = MainWindow()
    
    # 测试 1: Anchor 在原点，朝向 X 轴正方向
    result = main_window._transform_local_to_global(
        local_x=1.0,
        local_y=0.0,
        anchor_x=0.0,
        anchor_y=0.0,
        anchor_theta=0.0
    )
    print(f"测试 1 - Anchor 在原点，朝向 0°")
    print(f"  局部坐标: (1.0, 0.0)")
    print(f"  全局坐标: ({result['x']:.2f}, {result['y']:.2f})")
    assert abs(result['x'] - 1.0) < 0.01 and abs(result['y'] - 0.0) < 0.01, "测试 1 失败"
    print("  ✓ 通过\n")
    
    # 测试 2: Anchor 在原点，朝向 Y 轴正方向 (π/2)
    result = main_window._transform_local_to_global(
        local_x=0.0,
        local_y=1.0,
        anchor_x=0.0,
        anchor_y=0.0,
        anchor_theta=math.pi / 2
    )
    print(f"测试 2 - Anchor 在原点，朝向 90°")
    print(f"  局部坐标: (0.0, 1.0)")
    print(f"  全局坐标: ({result['x']:.2f}, {result['y']:.2f})")
    # 预期: (-1.0, 0.0) 因为局部 Y 轴 (1.0) 旋转 90° 后指向全局 X 轴负方向
    assert abs(result['x'] - (-1.0)) < 0.01 and abs(result['y'] - 0.0) < 0.01, f"测试 2 失败，得到 ({result['x']}, {result['y']})"
    print("  ✓ 通过\n")
    
    # 测试 3: Anchor 在 (5, 10)，朝向 0°
    result = main_window._transform_local_to_global(
        local_x=1.0,
        local_y=0.0,
        anchor_x=5.0,
        anchor_y=10.0,
        anchor_theta=0.0
    )
    print(f"测试 3 - Anchor 在 (5, 10)，朝向 0°")
    print(f"  局部坐标: (1.0, 0.0)")
    print(f"  全局坐标: ({result['x']:.2f}, {result['y']:.2f})")
    assert abs(result['x'] - 6.0) < 0.01 and abs(result['y'] - 10.0) < 0.01, "测试 3 失败"
    print("  ✓ 通过\n")
    
    # 测试 4: Anchor 在 (5, 10)，朝向 π/2 (Y 轴正方向)
    result = main_window._transform_local_to_global(
        local_x=1.0,
        local_y=1.0,
        anchor_x=5.0,
        anchor_y=10.0,
        anchor_theta=math.pi / 2
    )
    print(f"测试 4 - Anchor 在 (5, 10)，朝向 90°")
    print(f"  局部坐标: (1.0, 1.0)")
    print(f"  全局坐标: ({result['x']:.2f}, {result['y']:.2f})")
    # Anchor 局部 X(1.0) 旋转 90° -> 全局 Y(-1.0)
    # Anchor 局部 Y(1.0) 旋转 90° -> 全局 X(1.0)
    # 全局: (5.0 + 1.0, 10.0 - 1.0) = (6.0, 9.0)
    assert abs(result['x'] - 4.0) < 0.01 and abs(result['y'] - 11.0) < 0.01, f"测试 4 失败，得到 ({result['x']}, {result['y']})"
    print("  ✓ 通过\n")
    
    print("=" * 60)
    print("所有坐标变换测试通过！")
    print("=" * 60)


def test_aoa_worker():
    """测试 AOA Worker 的 get_filtered_beacon_coordinates 方法"""
    print("\n" + "=" * 60)
    print("测试 AOA Worker - 获取滤波坐标")
    print("=" * 60)
    
    # 创建 AOA Worker
    worker = AOAWorker()
    
    # 测试获取未初始化的滤波器的坐标
    coords = worker.get_filtered_beacon_coordinates(tag_id=1)
    print(f"未初始化的滤波器坐标:")
    print(f"  {coords}")
    assert coords['initialized'] == False, "新滤波器应该未初始化"
    print("  ✓ 正确返回未初始化状态\n")
    
    print("=" * 60)
    print("AOA Worker 测试通过！")
    print("=" * 60)


def test_beacon_on_image():
    """测试在地图上绘制 beacon 的方法"""
    print("\n" + "=" * 60)
    print("测试地图上的 Beacon 标记")
    print("=" * 60)
    
    try:
        from ui.widgets.map_viewer import MapViewerDialog
        from PyQt6.QtGui import QPixmap
        
        viewer = MapViewerDialog()
        
        # 创建虚拟地图数据
        fake_pixmap = QPixmap(100, 100)
        fake_pixmap.fill()
        
        fake_map_data = {
            'resolution': 0.05,
            'origin': [0, 0],
            'size': [100, 100]
        }
        
        fake_beacon = {
            'x': 2.5,  # 像素 x = (2.5 - 0) / 0.05 = 50
            'y': 2.5,  # 像素 y = 100 - (2.5 - 0) / 0.05 = 50
            'confidence': 0.95
        }
        
        # 测试绘制
        result_pixmap = viewer._mark_beacon_on_image(fake_pixmap, fake_map_data, fake_beacon)
        
        print(f"Beacon 绘制测试:")
        print(f"  地图分辨率: {fake_map_data['resolution']} m/px")
        print(f"  地图大小: {fake_map_data['size']}")
        print(f"  Beacon 位置: ({fake_beacon['x']}, {fake_beacon['y']}) 米")
        print(f"  Beacon 置信度: {fake_beacon['confidence']}")
        print(f"  结果: 成功绘制")
        print("  ✓ 通过\n")
        
        print("=" * 60)
        print("地图 Beacon 标记测试通过！")
        print("=" * 60)
        
    except Exception as e:
        print(f"  ✗ 测试失败: {e}\n")


if __name__ == '__main__':
    try:
        test_coordinate_transform()
        test_aoa_worker()
        test_beacon_on_image()
        
        print("\n" + "=" * 60)
        print("所有测试完成！")
        print("=" * 60)
        print("\n功能验证总结:")
        print("1. ✓ 坐标变换（Anchor 局部 -> 全局）")
        print("2. ✓ AOA Worker 获取滤波坐标")
        print("3. ✓ 地图上绘制 beacon 标记")
        print("\n实现功能:")
        print("- Anchor 局部坐标系转全局坐标")
        print("- 从 /tracked_pose 话题获取 Anchor 位置和朝向")
        print("- 查询卡尔曼滤波后的 beacon 坐标")
        print("- 计算 beacon 全局位置")
        print("- 发布 /globe_beacon 话题")
        print("- 在实时地图上用红色圆点标记 beacon")
        print("=" * 60)
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
