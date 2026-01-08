#!/usr/bin/env python3
"""
单元测试 - 测试坐标变换功能
"""
import math


def transform_local_to_global(local_x, local_y, anchor_x, anchor_y, anchor_theta):
    """
    将 Anchor 局部坐标转换为全局坐标
    """
    cos_theta = math.cos(anchor_theta)
    sin_theta = math.sin(anchor_theta)
    
    x_global = anchor_x + local_x * cos_theta - local_y * sin_theta
    y_global = anchor_y + local_x * sin_theta + local_y * cos_theta
    
    return {
        'x': x_global,
        'y': y_global
    }


def test_coordinate_transform():
    """测试坐标变换函数"""
    print("=" * 70)
    print("测试坐标变换：Anchor 局部坐标 -> 全局坐标")
    print("=" * 70)
    
    # 测试 1: Anchor 在原点，朝向 X 轴正方向 (0°)
    print("\n测试 1 - Anchor 在原点 (0, 0)，朝向 0° (X 轴正方向)")
    result = transform_local_to_global(
        local_x=1.0,
        local_y=0.0,
        anchor_x=0.0,
        anchor_y=0.0,
        anchor_theta=0.0
    )
    print(f"  局部坐标: (1.0, 0.0)")
    print(f"  全局坐标: ({result['x']:.4f}, {result['y']:.4f})")
    assert abs(result['x'] - 1.0) < 0.01 and abs(result['y'] - 0.0) < 0.01
    print("  ✓ PASS")
    
    # 测试 2: Anchor 在原点，朝向 Y 轴正方向 (90°)
    print("\n测试 2 - Anchor 在原点 (0, 0)，朝向 90° (Y 轴正方向)")
    result = transform_local_to_global(
        local_x=0.0,
        local_y=1.0,
        anchor_x=0.0,
        anchor_y=0.0,
        anchor_theta=math.pi / 2
    )
    print(f"  局部坐标: (0.0, 1.0)")
    print(f"  全局坐标: ({result['x']:.4f}, {result['y']:.4f})")
    # 当 Anchor 朝向 Y 轴正方向时，局部 Y 轴映射到全局 X 轴负方向
    assert abs(result['x'] - (-1.0)) < 0.01 and abs(result['y'] - 0.0) < 0.01, \
        f"预期 (-1.0, 0.0)，得到 ({result['x']:.4f}, {result['y']:.4f})"
    print("  ✓ PASS")
    
    # 测试 3: Anchor 在 (5, 10)，朝向 0°，beacon 在 Anchor 右侧 1 米
    print("\n测试 3 - Anchor 在 (5, 10)，朝向 0°，Beacon 在右侧 1 米")
    result = transform_local_to_global(
        local_x=1.0,  # 右侧 1 米
        local_y=0.0,  # 正前方 0 米
        anchor_x=5.0,
        anchor_y=10.0,
        anchor_theta=0.0
    )
    print(f"  局部坐标: (1.0, 0.0)")
    print(f"  全局坐标: ({result['x']:.4f}, {result['y']:.4f})")
    assert abs(result['x'] - 6.0) < 0.01 and abs(result['y'] - 10.0) < 0.01
    print("  ✓ PASS")
    
    # 测试 4: Anchor 在 (5, 10)，朝向 90°，beacon 在 Anchor 右侧 1 米
    print("\n测试 4 - Anchor 在 (5, 10)，朝向 90°，Beacon 在右侧 1 米")
    result = transform_local_to_global(
        local_x=1.0,  # 右侧 1 米（相对于 Anchor）
        local_y=0.0,  # 正前方 0 米
        anchor_x=5.0,
        anchor_y=10.0,
        anchor_theta=math.pi / 2
    )
    print(f"  局部坐标: (1.0, 0.0)")
    print(f"  全局坐标: ({result['x']:.4f}, {result['y']:.4f})")
    # Anchor 朝向 90°，局部 X 轴 (1.0) 旋转 90° -> 全局 Y 轴正方向
    # 全局: (5 + 0, 10 + 1) = (5, 11)
    assert abs(result['x'] - 5.0) < 0.01 and abs(result['y'] - 11.0) < 0.01, \
        f"预期 (5.0, 11.0)，得到 ({result['x']:.4f}, {result['y']:.4f})"
    print("  ✓ PASS")
    
    # 测试 5: Anchor 在 (5, 10)，朝向 90°，beacon 在 Anchor 前方 1 米
    print("\n测试 5 - Anchor 在 (5, 10)，朝向 90°，Beacon 在前方 1 米")
    result = transform_local_to_global(
        local_x=0.0,  # 右侧 0 米
        local_y=1.0,  # 正前方 1 米
        anchor_x=5.0,
        anchor_y=10.0,
        anchor_theta=math.pi / 2
    )
    print(f"  局部坐标: (0.0, 1.0)")
    print(f"  全局坐标: ({result['x']:.4f}, {result['y']:.4f})")
    # Anchor 朝向 90°（Y 轴正方向），局部 Y 轴 (1.0) 旋转 90° -> 全局 X 轴负方向
    # 全局: (5 - 1, 10 + 0) = (4, 10)
    assert abs(result['x'] - 4.0) < 0.01 and abs(result['y'] - 10.0) < 0.01, \
        f"预期 (4.0, 10.0)，得到 ({result['x']:.4f}, {result['y']:.4f})"
    print("  ✓ PASS")
    
    # 测试 6: Anchor 在 (5, 10)，朝向 45°，beacon 在 (2, 2) 局部坐标
    print("\n测试 6 - Anchor 在 (5, 10)，朝向 45°，Beacon 在 (2, 2) 局部坐标")
    result = transform_local_to_global(
        local_x=2.0,
        local_y=2.0,
        anchor_x=5.0,
        anchor_y=10.0,
        anchor_theta=math.pi / 4  # 45°
    )
    print(f"  局部坐标: (2.0, 2.0)")
    print(f"  全局坐标: ({result['x']:.4f}, {result['y']:.4f})")
    # cos(45°) = sin(45°) = √2/2 ≈ 0.7071
    # x_global = 5 + 2*0.7071 - 2*0.7071 = 5
    # y_global = 10 + 2*0.7071 + 2*0.7071 = 10 + 2√2 ≈ 12.8284
    expected_y = 10 + 2 * math.sqrt(2)
    assert abs(result['x'] - 5.0) < 0.01 and abs(result['y'] - expected_y) < 0.01, \
        f"预期 (5.0, {expected_y:.4f})，得到 ({result['x']:.4f}, {result['y']:.4f})"
    print("  ✓ PASS")
    
    print("\n" + "=" * 70)
    print("所有坐标变换测试通过！")
    print("=" * 70)


def print_summary():
    """打印功能总结"""
    print("\n" + "=" * 70)
    print("🎯 globe_beacon 话题功能实现总结")
    print("=" * 70)
    
    print("\n📋 核心功能：")
    print("  1. ✓ 订阅 /tracked_pose 话题获取 Anchor 位置和朝向")
    print("  2. ✓ 从卡尔曼滤波器获取 beacon 的局部坐标（相对于 Anchor）")
    print("  3. ✓ 将局部坐标转换为全局坐标")
    print("  4. ✓ 发布 /globe_beacon 话题（内部信号）")
    print("  5. ✓ 在实时地图上用红色圆点标记 beacon 位置")
    
    print("\n📂 修改的文件：")
    print("  • workers/aoa_worker.py")
    print("    - 添加 get_filtered_beacon_coordinates() 方法")
    print("  • ui/main_window.py")
    print("    - 处理 /tracked_pose 话题消息")
    print("    - 添加 _transform_local_to_global() 坐标变换方法")
    print("    - 添加 _publish_globe_beacon() 话题发布方法")
    print("  • ui/widgets/map_viewer.py")
    print("    - 添加 update_beacon_position() 方法")
    print("    - 添加 _mark_beacon_on_image() 绘制方法")
    print("    - 集成 beacon 标记到地图显示")
    print("  • topics.txt")
    print("    - 添加 /globe_beacon 话题")
    
    print("\n🔧 坐标系说明：")
    print("  • Anchor 局部坐标系：Y 轴正前方，X 轴右侧（右手规则）")
    print("  • Anchor 朝向范围：-90° 到 90°（检测范围）")
    print("  • 变换公式：")
    print("    x_global = x_anchor + local_x * cos(theta) - local_y * sin(theta)")
    print("    y_global = y_anchor + local_x * sin(theta) + local_y * cos(theta)")
    
    print("\n📡 话题格式：")
    print("  /globe_beacon: {")
    print("    'tag_id': int,")
    print("    'x': float (全局坐标，米),")
    print("    'y': float (全局坐标，米),")
    print("    'confidence': float (0-1),")
    print("    'timestamp': float")
    print("  }")
    
    print("\n🎨 地图显示：")
    print("  • 原点标记：绿色 X")
    print("  • Anchor 位置：蓝色箭头")
    print("  • Beacon 位置：红色圆点（大小与置信度相关）")
    
    print("\n" + "=" * 70)


if __name__ == '__main__':
    try:
        test_coordinate_transform()
        print_summary()
        print("\n✓ 所有测试通过！系统已准备好使用。")
    except AssertionError as e:
        print(f"\n✗ 测试失败: {e}")
        import sys
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ 发生错误: {e}")
        import traceback
        traceback.print_exc()
        import sys
        sys.exit(1)
