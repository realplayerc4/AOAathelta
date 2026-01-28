#!/usr/bin/env python3
"""
验证地图元数据解析
"""

import struct

def verify_map_metadata():
    """验证explore_map.bin的元数据"""
    
    with open('explore_map.bin', 'rb') as f:
        data = f.read()
    
    print("=" * 80)
    print("验证地图元数据")
    print("=" * 80)
    print()
    
    print(f"文件大小: {len(data)} 字节")
    print()
    
    # 显示前36字节的十六进制
    print("前36字节（元数据）:")
    for i in range(0, 36, 4):
        hex_str = ' '.join(f'{b:02x}' for b in data[i:i+4])
        print(f"  {i:2d}-{i+3:2d}: {hex_str}")
    print()
    
    # 解析元数据（小端）
    print("解析结果（小端字节序 '<'）:")
    origin_x = struct.unpack('<f', data[0:4])[0]
    origin_y = struct.unpack('<f', data[4:8])[0]
    width = struct.unpack('<I', data[8:12])[0]
    height = struct.unpack('<I', data[12:16])[0]
    resolution = struct.unpack('<f', data[16:20])[0]
    reserved = data[20:32]
    data_size = struct.unpack('<I', data[32:36])[0]
    
    print(f"  [0-3]   origin_x:    {origin_x:.6f}")
    print(f"  [4-7]   origin_y:    {origin_y:.6f}")
    print(f"  [8-11]  width:       {width}")
    print(f"  [12-15] height:      {height}")
    print(f"  [16-19] resolution:  {resolution:.6f}")
    print(f"  [20-31] reserved:    {reserved.hex()}")
    print(f"  [32-35] data_size:   {data_size}")
    print()
    
    # 验证
    print("验证:")
    expected_size = width * height
    print(f"  ✓ width × height = {width} × {height} = {expected_size}")
    print(f"  ✓ data_size = {data_size}")
    print(f"  {'✓' if data_size == expected_size else '✗'} 一致性检查: {data_size == expected_size}")
    
    actual_map_data = len(data) - 36
    print(f"  ✓ 实际地图数据: {actual_map_data} 字节")
    print(f"  {'✓' if actual_map_data >= data_size else '✗'} 数据完整性: {actual_map_data >= data_size}")
    print()
    
    # 地图信息
    print("地图信息:")
    print(f"  尺寸: {width} × {height} 栅格")
    print(f"  真实尺寸: {width * resolution:.2f} × {height * resolution:.2f} 米")
    print(f"  面积: {width * resolution * height * resolution:.2f} 平方米")
    print(f"  原点: ({origin_x:.2f}, {origin_y:.2f}) 米")
    print(f"  分辨率: {resolution * 100:.2f} 厘米/格子")
    print()
    
    # 地图数据统计
    map_data = data[36:36+data_size]
    unique_values = len(set(map_data))
    
    print("地图数据统计:")
    print(f"  唯一值数量: {unique_values}")
    print(f"  值0（未探索，灰色）: {map_data.count(0)} ({map_data.count(0)/len(map_data)*100:.1f}%)")
    print(f"  值127（探索区域，白色）: {map_data.count(127)} ({map_data.count(127)/len(map_data)*100:.1f}%)")
    print(f"  值255（障碍物，黑色）: {map_data.count(255)} ({map_data.count(255)/len(map_data)*100:.1f}%)")
    
    # 统计探索区域（所有非0值）
    explored = sum(1 for v in map_data if v > 0)
    print(f"  探索区域总计（值>0）: {explored} ({explored/len(map_data)*100:.1f}%)")
    print()
    
    print("=" * 80)


if __name__ == '__main__':
    verify_map_metadata()
