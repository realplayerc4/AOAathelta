#!/usr/bin/env python3
"""
单元测试 - 验证坐标变换的正确性
"""

import sys
import os
import math

# 添加项目根路径到sys.path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from coordinate_transform import CoordinateTransformer, transform_beacon_position


def test_validate_robot_pose():
    """测试位姿态验证"""
    print("测试 1: 位姿态验证")
    print("-" * 60)
    
    transformer = CoordinateTransformer()
    
    # 有效的位姿态
    valid_pose = {'x': 0.0, 'y': 0.0, 'yaw': 0.0}
    assert transformer.validate_robot_pose(valid_pose), "有效位姿态应该通过验证"
    print("✓ 有效位姿态验证通过")
    
    # 缺少字段
    invalid_pose = {'x': 0.0, 'y': 0.0}  # 缺少yaw
    assert not transformer.validate_robot_pose(invalid_pose), "缺少yaw的位姿态应该验证失败"
    print("✓ 缺少字段的检测正确")
    
    # 无效类型
    invalid_pose = {'x': 'invalid', 'y': 0.0, 'yaw': 0.0}
    assert not transformer.validate_robot_pose(invalid_pose), "无效数据类型应该验证失败"
    print("✓ 无效数据类型的检测正确")
    
    print()


def test_identity_transform():
    """测试恒等变换（地盘在原点，朝向为0）"""
    print("测试 2: 恒等变换")
    print("-" * 60)
    
    transformer = CoordinateTransformer()
    robot_pose = {'x': 0.0, 'y': 0.0, 'yaw': 0.0}
    
    # 局部坐标应该等于全局坐标
    test_cases = [
        (1.0, 0.0),
        (0.0, 1.0),
        (1.0, 1.0),
        (-1.0, 0.5),
    ]
    
    for local_x, local_y in test_cases:
        global_x, global_y = transformer.transform_beacon_to_global(
            local_x, local_y, robot_pose
        )
        
        assert abs(global_x - local_x) < 1e-6, f"X不匹配: {global_x} != {local_x}"
        assert abs(global_y - local_y) < 1e-6, f"Y不匹配: {global_y} != {local_y}"
        print(f"✓ ({local_x:5.1f}, {local_y:5.1f}) -> ({global_x:5.1f}, {global_y:5.1f})")
    
    print()


def test_translation():
    """测试平移变换"""
    print("测试 3: 平移变换（地盘位移，朝向为0）")
    print("-" * 60)
    
    transformer = CoordinateTransformer()
    robot_pose = {'x': 10.0, 'y': 20.0, 'yaw': 0.0}
    
    # 局部坐标应该加上地盘位移
    local_x, local_y = 1.0, 1.0
    global_x, global_y = transformer.transform_beacon_to_global(
        local_x, local_y, robot_pose
    )
    
    assert abs(global_x - (robot_pose['x'] + local_x)) < 1e-6
    assert abs(global_y - (robot_pose['y'] + local_y)) < 1e-6
    print(f"✓ 平移: ({local_x}, {local_y}) + robot({robot_pose['x']}, {robot_pose['y']}) "
          f"= ({global_x:.1f}, {global_y:.1f})")
    
    print()


def test_90_degree_rotation():
    """测试90度旋转"""
    print("测试 4: 旋转变换（90度）")
    print("-" * 60)
    
    transformer = CoordinateTransformer()
    robot_pose = {'x': 0.0, 'y': 0.0, 'yaw': math.pi / 2}  # 90度
    
    # 当地盘朝向为90度（向左），本地X轴（右侧）应该指向负Y方向
    test_cases = [
        (1.0, 0.0, 0.0, 1.0),    # 右侧1米 -> 前方1米
        (0.0, 1.0, -1.0, 0.0),   # 前方1米 -> 左侧1米
    ]
    
    for local_x, local_y, expected_x, expected_y in test_cases:
        global_x, global_y = transformer.transform_beacon_to_global(
            local_x, local_y, robot_pose
        )
        
        assert abs(global_x - expected_x) < 1e-6, f"X不匹配: {global_x} != {expected_x}"
        assert abs(global_y - expected_y) < 1e-6, f"Y不匹配: {global_y} != {expected_y}"
        print(f"✓ ({local_x:5.1f}, {local_y:5.1f}) @ 90° -> ({global_x:5.1f}, {global_y:5.1f})")
    
    print()


def test_heading_transform():
    """测试朝向变换"""
    print("测试 5: 朝向变换")
    print("-" * 60)
    
    transformer = CoordinateTransformer()
    robot_yaw = 0.0
    
    # 局部朝向就是全局朝向
    test_cases = [
        (0.0, 0.0),
        (math.pi / 4, math.pi / 4),
        (math.pi, math.pi),
        (-math.pi / 2, -math.pi / 2),
    ]
    
    for local_yaw, expected_global in test_cases:
        global_yaw = transformer.transform_beacon_heading(local_yaw, robot_yaw)
        
        # 归一化后比较
        diff = global_yaw - expected_global
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
        
        assert abs(diff) < 1e-6, f"朝向不匹配: {global_yaw} != {expected_global}"
        print(f"✓ 本地{math.degrees(local_yaw):6.1f}° + robot{math.degrees(robot_yaw):6.1f}° "
              f"= 全局{math.degrees(global_yaw):6.1f}°")
    
    print()


def test_heading_with_robot_rotation():
    """测试朝向变换（地盘旋转）"""
    print("测试 6: 朝向变换（地盘旋转）")
    print("-" * 60)
    
    transformer = CoordinateTransformer()
    robot_yaw = math.pi / 4  # 地盘朝向45度
    
    local_yaw = 0.0  # Beacon朝向本地0度（向右）
    global_yaw = transformer.transform_beacon_heading(local_yaw, robot_yaw)
    
    # 全局朝向应该是45度
    assert abs(global_yaw - math.pi / 4) < 1e-6
    print(f"✓ 本地0° + robot45° = 全局{math.degrees(global_yaw):.1f}°")
    
    print()


def test_complete_position_transform():
    """测试完整的位置变换"""
    print("测试 7: 完整位置变换（位置+速度+朝向）")
    print("-" * 60)
    
    robot_pose = {
        'x': 5.0,
        'y': 10.0,
        'yaw': math.pi / 6  # 30度
    }
    
    filtered_position = {
        'x': 1.0,
        'y': 2.0,
        'vx': 0.1,
        'vy': 0.2,
        'confidence': 0.85
    }
    
    result = transform_beacon_position(filtered_position, robot_pose)
    
    # 验证关键字段存在
    assert 'x' in result, "结果应包含x"
    assert 'y' in result, "结果应包含y"
    assert 'yaw' in result, "结果应包含yaw"
    assert 'confidence' in result, "结果应保留confidence"
    
    # 验证坐标被正确变换
    transformer = CoordinateTransformer()
    expected_x, expected_y = transformer.transform_beacon_to_global(
        filtered_position['x'], filtered_position['y'], robot_pose
    )
    
    assert abs(result['x'] - expected_x) < 1e-6
    assert abs(result['y'] - expected_y) < 1e-6
    
    print(f"✓ 位置: ({filtered_position['x']}, {filtered_position['y']}) "
          f"-> ({result['x']:.1f}, {result['y']:.1f})")
    print(f"✓ 朝向: {math.degrees(result.get('yaw', 0)):.1f}°")
    print(f"✓ 置信度保留: {result['confidence']}")
    
    print()


def normalize_angle_diff(a, b):
    """计算两个角度之间的最小差值 (在[-π, π]范围内)"""
    diff = a - b
    # 将差值映射到[-π, π]范围
    while diff > math.pi:
        diff -= 2 * math.pi
    while diff <= -math.pi:  # 注意这里是 <=
        diff += 2 * math.pi
    return diff


def test_angle_normalization():
    """测试角度归一化"""
    print("测试 8: 角度归一化")
    print("-" * 60)
    
    transformer = CoordinateTransformer()
    
    # 超出[-π, π]范围的角度应该被归一化到[-π, π]
    test_cases = [
        (2.5 * math.pi, 0.5 * math.pi),     # 2.5π -> 0.5π (不是-0.5π)
        (3.5 * math.pi, -0.5 * math.pi),    # 3.5π -> -0.5π
        (math.pi / 4, math.pi / 4),         # π/4 -> π/4
        (9 * math.pi / 4, math.pi / 4),     # 9π/4 -> π/4
    ]
    
    for robot_yaw, expected in test_cases:
        local_yaw = 0.0
        global_yaw = transformer.transform_beacon_heading(local_yaw, robot_yaw)
        
        # 直接比较，因为归一化应该产生在[-π, π]范围内的值
        assert -math.pi <= global_yaw <= math.pi, \
            f"结果超出范围: {global_yaw} 不在 [-π, π]"
        
        # 使用角度差函数检查
        angle_diff = normalize_angle_diff(global_yaw, expected)
        assert abs(angle_diff) < 1e-5, \
            f"角度不匹配: {global_yaw:.6f} 和期望 {expected:.6f} 的差为 {angle_diff:.6f}"
        
        print(f"✓ {robot_yaw/math.pi:.2f}π -> {global_yaw/math.pi:.3f}π ≈ {expected/math.pi:.3f}π")
    
    print()


def run_all_tests():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("坐标变换单元测试")
    print("=" * 60 + "\n")
    
    try:
        test_validate_robot_pose()
        test_identity_transform()
        test_translation()
        test_90_degree_rotation()
        test_heading_transform()
        test_heading_with_robot_rotation()
        test_complete_position_transform()
        test_angle_normalization()
        
        print("=" * 60)
        print("✅ 所有测试通过")
        print("=" * 60)
        return 0
    
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(run_all_tests())
