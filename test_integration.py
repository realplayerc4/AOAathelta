#!/usr/bin/env python3
"""
集成测试脚本 - 验证地盘位姿态获取和坐标变换功能
"""

import sys
import os
import math
import time

# 添加项目根路径到sys.path
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.api_client import APIClient
from coordinate_transform import CoordinateTransformer, transform_beacon_position


def test_api_connectivity():
    """测试API连接"""
    print("=" * 80)
    print("测试 1: API 连接")
    print("=" * 80)
    
    try:
        client = APIClient()
        print(f"✓ API 客户端初始化成功")
        print(f"  - 服务器地址: {client.base_url}")
        print(f"  - 超时时间: {client.timeout}秒")
        
        # 测试获取位姿态
        print("\n尝试获取地盘位姿态...")
        pose = client.fetch_pose()
        print(f"✓ 成功获取位姿态:")
        print(f"  - x: {pose.get('x', 'N/A')}")
        print(f"  - y: {pose.get('y', 'N/A')}")
        print(f"  - yaw: {pose.get('yaw', 'N/A')} rad ({math.degrees(pose.get('yaw', 0)):.1f}°)")
        print(f"  - z: {pose.get('z', 'N/A')}")
        print(f"  - pitch: {pose.get('pitch', 'N/A')}")
        print(f"  - roll: {pose.get('roll', 'N/A')}")
        
        return pose
    
    except Exception as e:
        print(f"✗ API 测试失败: {e}")
        return None


def test_coordinate_transform(robot_pose):
    """测试坐标变换"""
    print("\n" + "=" * 80)
    print("测试 2: 坐标变换 - 从Anchor局部坐标到地图全局坐标")
    print("=" * 80)
    
    if not robot_pose:
        print("✗ 跳过此测试（未获得地盘位姿态）")
        return
    
    transformer = CoordinateTransformer()
    
    # 验证位姿态
    print(f"地盘位姿态: x={robot_pose['x']:.3f}, y={robot_pose['y']:.3f}, yaw={robot_pose['yaw']:.3f}rad")
    
    # 测试几个不同位置的Beacon
    test_cases = [
        {"name": "前方1米", "x": 0.0, "y": 1.0},
        {"name": "右侧1米", "x": 1.0, "y": 0.0},
        {"name": "左侧1米", "x": -1.0, "y": 0.0},
        {"name": "右前45°", "x": 0.707, "y": 0.707},
    ]
    
    print("\n测试用例 (局部坐标 -> 全局坐标):")
    print("-" * 80)
    
    for test in test_cases:
        local_x, local_y = test['x'], test['y']
        global_x, global_y = transformer.transform_beacon_to_global(
            local_x, local_y, robot_pose
        )
        
        print(f"{test['name']:12} | 局部: ({local_x:6.3f}, {local_y:6.3f})m -> "
              f"全局: ({global_x:8.3f}, {global_y:8.3f})m")
    
    # 测试朝向变换
    print("\n朝向变换测试 (局部朝向 + 地盘朝向 -> 全局朝向):")
    print("-" * 80)
    
    beacon_headings = [0, math.pi/4, math.pi/2, math.pi, -math.pi/2]
    
    for local_yaw in beacon_headings:
        global_yaw = transformer.transform_beacon_heading(local_yaw, robot_pose['yaw'])
        print(f"局部朝向: {math.degrees(local_yaw):6.1f}° -> 全局朝向: {math.degrees(global_yaw):7.1f}°")


def test_complete_position_transform(robot_pose):
    """测试完整的位置信息变换"""
    print("\n" + "=" * 80)
    print("测试 3: 完整位置信息变换（包括速度和朝向）")
    print("=" * 80)
    
    if not robot_pose:
        print("✗ 跳过此测试（未获得地盘位姿态）")
        return
    
    # 模拟从卡尔曼滤波器得到的局部位置
    filtered_position = {
        'x': 0.5,           # 局部X
        'y': 1.2,           # 局部Y
        'vx': 0.1,          # 速度X分量
        'vy': 0.3,          # 速度Y分量
        'confidence': 0.85,  # 置信度
    }
    
    print(f"输入 - 局部坐标 (Anchor相对):")
    print(f"  - 位置: ({filtered_position['x']:.3f}, {filtered_position['y']:.3f})m")
    print(f"  - 速度: ({filtered_position['vx']:.3f}, {filtered_position['vy']:.3f})m/s")
    print(f"  - 置信度: {filtered_position['confidence']:.3f}")
    
    # 进行变换
    result = transform_beacon_position(filtered_position, robot_pose)
    
    print(f"\n输出 - 全局坐标 (地图参考系):")
    print(f"  - 位置: ({result['x']:.3f}, {result['y']:.3f})m")
    print(f"  - 朝向 (yaw): {result.get('yaw', 0):.3f}rad ({math.degrees(result.get('yaw', 0)):.1f}°)")
    print(f"  - 置信度: {result.get('confidence', 0):.3f}")
    
    # 显示位移关系
    print(f"\n地盘参考信息:")
    print(f"  - 地盘位置: ({robot_pose['x']:.3f}, {robot_pose['y']:.3f})m")
    print(f"  - 地盘朝向: {robot_pose['yaw']:.3f}rad ({math.degrees(robot_pose['yaw']):.1f}°)")


def main():
    print("\n" + "🔧" * 40)
    print("AOA Beacon 定位系统 - 集成功能测试")
    print("🔧" * 40 + "\n")
    
    # 测试 1: API 连接
    robot_pose = test_api_connectivity()
    
    # 测试 2: 坐标变换
    if robot_pose:
        test_coordinate_transform(robot_pose)
        test_complete_position_transform(robot_pose)
    
    print("\n" + "=" * 80)
    print("✅ 测试完成")
    print("=" * 80)
    
    if robot_pose:
        print("\n提示: 运行主程序获取实时Beacon位置")
        print("  python test_realtime_beacon.py")
    else:
        print("\n⚠️  警告: API连接失败，请检查:")
        print("  1. 地盘AMR是否已启动并运行")
        print("  2. 网络连接是否正常")
        print("  3. config.py中的API_BASE_URL是否正确")
    
    return 0 if robot_pose else 1


if __name__ == '__main__':
    sys.exit(main())
