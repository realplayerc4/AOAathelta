#!/usr/bin/env python
"""
诊断小车位置显示问题的脚本
"""
import json
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def diagnose_position_display():
    """诊断位置显示问题"""
    print("=" * 80)
    print("小车位置显示问题诊断")
    print("=" * 80)
    
    # 1. 检查地图数据示例
    print("\n1️⃣ 检查地图数据格式:")
    print("-" * 80)
    
    sample_map = {
        "topic": "/map",
        "resolution": 0.1,  # 米/像素
        "size": [182, 59],  # 宽x高（像素）
        "origin": [-8.1, -4.8],  # 原点坐标（米）
        "data": "base64_encoded_png_data..."
    }
    
    print(f"分辨率: {sample_map['resolution']} m/px")
    print(f"地图尺寸: {sample_map['size'][0]} x {sample_map['size'][1]} px")
    print(f"原点坐标: ({sample_map['origin'][0]}, {sample_map['origin'][1]}) m")
    print(f"地图覆盖范围:")
    print(f"  X: {sample_map['origin'][0]:.2f} 到 {sample_map['origin'][0] + sample_map['size'][0] * sample_map['resolution']:.2f} m")
    print(f"  Y: {sample_map['origin'][1]:.2f} 到 {sample_map['origin'][1] + sample_map['size'][1] * sample_map['resolution']:.2f} m")
    
    # 2. 检查小车位置数据示例
    print("\n2️⃣ 检查小车位置数据格式:")
    print("-" * 80)
    
    sample_pose = {
        "pos": [2.5, 1.3],  # 全局坐标（米）
        "ori": 0.785  # 朝向（弧度，约45度）
    }
    
    print(f"位置: ({sample_pose['pos'][0]:.2f}, {sample_pose['pos'][1]:.2f}) m")
    print(f"朝向: {sample_pose['ori']:.3f} rad = {sample_pose['ori'] * 180 / 3.14159:.1f}°")
    
    # 3. 模拟坐标转换
    print("\n3️⃣ 模拟坐标转换:")
    print("-" * 80)
    
    resolution = sample_map['resolution']
    origin = sample_map['origin']
    size = sample_map['size']
    pos = sample_pose['pos']
    
    # 全局坐标 -> 像素坐标
    pixel_x = (pos[0] - origin[0]) / resolution
    pixel_y_from_bottom = (pos[1] - origin[1]) / resolution
    pixel_y = size[1] - pixel_y_from_bottom
    
    print(f"全局坐标: ({pos[0]:.2f}, {pos[1]:.2f}) m")
    print(f"  ↓ 转换公式:")
    print(f"    pixel_x = (pos_x - origin_x) / resolution")
    print(f"    pixel_x = ({pos[0]} - {origin[0]}) / {resolution}")
    print(f"    pixel_x = {pixel_x:.1f}")
    print(f"")
    print(f"    pixel_y_from_bottom = (pos_y - origin_y) / resolution")
    print(f"    pixel_y_from_bottom = ({pos[1]} - {origin[1]}) / {resolution}")
    print(f"    pixel_y_from_bottom = {pixel_y_from_bottom:.1f}")
    print(f"")
    print(f"    pixel_y = size[1] - pixel_y_from_bottom")
    print(f"    pixel_y = {size[1]} - {pixel_y_from_bottom:.1f}")
    print(f"    pixel_y = {pixel_y:.1f}")
    print(f"  ↓ 结果:")
    print(f"像素坐标: ({pixel_x:.1f}, {pixel_y:.1f}) px")
    
    # 检查是否在地图范围内
    is_in_range = (0 <= pixel_x < size[0] and 0 <= pixel_y < size[1])
    print(f"\n✅ 是否在地图范围内: {is_in_range}")
    if not is_in_range:
        print(f"❌ 超出范围！")
        print(f"   地图范围: (0, 0) 到 ({size[0]}, {size[1]})")
        print(f"   当前位置: ({pixel_x:.1f}, {pixel_y:.1f})")
        
        # 给出可能的原因
        print(f"\n🔍 可能的原因:")
        if pixel_x < 0:
            print(f"   - 小车 X 坐标太小（{pos[0]:.2f} < {origin[0]:.2f}）")
        elif pixel_x >= size[0]:
            max_x = origin[0] + size[0] * resolution
            print(f"   - 小车 X 坐标太大（{pos[0]:.2f} > {max_x:.2f}）")
        if pixel_y < 0:
            max_y = origin[1] + size[1] * resolution
            print(f"   - 小车 Y 坐标太大（{pos[1]:.2f} > {max_y:.2f}）")
        elif pixel_y >= size[1]:
            print(f"   - 小车 Y 坐标太小（{pos[1]:.2f} < {origin[1]:.2f}）")
    
    # 4. 检查实际数据（如果有）
    print("\n4️⃣ 检查实际数据:")
    print("-" * 80)
    print("请运行程序并检查以下内容：")
    print("  1. 查看终端日志中的调试信息")
    print("  2. 检查 /tracked_pose 话题是否收到数据")
    print("  3. 检查 /map 话题是否收到数据")
    print("  4. 查看地图查看器中的状态信息")
    
    # 5. 常见问题检查清单
    print("\n5️⃣ 常见问题检查清单:")
    print("-" * 80)
    issues = [
        ("topics.txt 文件是否包含 /tracked_pose 和 /map?", "cat topics.txt"),
        ("WebSocket 连接是否正常?", "检查状态栏信息"),
        ("小车位置是否超出地图范围?", "比较位置坐标和地图范围"),
        ("坐标转换公式是否正确?", "检查 map_viewer.py 中的转换代码"),
        ("地图分辨率和原点是否正确?", "检查地图数据的 resolution 和 origin 字段"),
        ("日志级别是否设置为 DEBUG?", "在 main.py 中设置 logging.DEBUG"),
    ]
    
    for i, (issue, check) in enumerate(issues, 1):
        print(f"  ✓ {issue}")
        print(f"    检查方法: {check}")
    
    print("\n" + "=" * 80)
    print("诊断完成！")
    print("=" * 80)

if __name__ == "__main__":
    diagnose_position_display()
