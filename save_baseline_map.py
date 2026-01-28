#!/usr/bin/env python3
"""
获取激光探索栅格地图作为底图基线
生成标准格式的地图文件和元数据，供其他程序使用
"""

import sys
import os
import json
import struct
import requests
from PIL import Image
import numpy as np

# 添加项目根路径
PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from config import API_BASE_URL, API_SECRET, API_TIMEOUT

# 地图存储目录
MAPS_DIR = os.path.join(PROJECT_ROOT, 'maps')
BASELINE_MAP_DIR = os.path.join(MAPS_DIR, 'baseline')


def ensure_map_dirs():
    """创建地图目录结构"""
    os.makedirs(BASELINE_MAP_DIR, exist_ok=True)
    print(f"✓ 地图目录: {BASELINE_MAP_DIR}")


def fetch_explore_map(min_x=None, min_y=None, max_x=None, max_y=None):
    """获取激光探索栅格地图"""
    url = f"{API_BASE_URL}/api/core/slam/v1/maps/explore"
    
    params = {}
    if min_x is not None:
        params['min_x'] = min_x
    if min_y is not None:
        params['min_y'] = min_y
    if max_x is not None:
        params['max_x'] = max_x
    if max_y is not None:
        params['max_y'] = max_y
    
    print(f"获取地图: {url}")
    
    try:
        response = requests.get(
            url,
            params=params,
            headers={'Authorization': f'Bearer {API_SECRET}'},
            timeout=API_TIMEOUT
        )
        response.raise_for_status()
        print(f"✓ 成功获取 {len(response.content)} 字节")
        return response.content
        
    except requests.exceptions.RequestException as e:
        print(f"✗ 获取失败: {e}")
        return None


def parse_map_data(data):
    """解析地图数据"""
    if len(data) < 36:
        return None
    
    # 解析元数据（小端字节序）
    origin_x = struct.unpack('<f', data[0:4])[0]
    origin_y = struct.unpack('<f', data[4:8])[0]
    width = struct.unpack('<I', data[8:12])[0]
    height = struct.unpack('<I', data[12:16])[0]
    resolution = struct.unpack('<f', data[16:20])[0]
    data_size = struct.unpack('<I', data[32:36])[0]
    
    # 提取地图数据
    map_bytes = data[36:36 + data_size]
    map_array = np.frombuffer(map_bytes[:data_size], dtype=np.uint8)
    map_array = map_array.reshape((height, width))
    
    metadata = {
        'origin_x': float(origin_x),
        'origin_y': float(origin_y),
        'width': int(width),
        'height': int(height),
        'resolution': float(resolution),
        'data_size': int(data_size)
    }
    
    return metadata, map_array


def create_map_image(map_array):
    """创建三色地图图像"""
    map_colored = np.zeros_like(map_array, dtype=np.uint8)
    map_colored[map_array == 0] = 128           # 未知区 -> 灰色
    map_colored[(map_array > 0) & (map_array < 200)] = 255  # 探索区域 -> 白色
    map_colored[map_array >= 200] = 0           # 障碍物 -> 黑色
    return map_colored


def save_baseline_map(metadata, map_colored):
    """
    保存地图文件和元数据
    
    文件结构:
    maps/baseline/
    ├── baseline_map.png       # 地图图像
    ├── baseline_map.json      # 地图元数据
    └── README.md             # 使用说明
    """
    
    # 保存地图图像
    img_path = os.path.join(BASELINE_MAP_DIR, 'baseline_map.png')
    Image.fromarray(map_colored).save(img_path)
    print(f"✓ 地图图像: {os.path.relpath(img_path)}")
    
    # 保存元数据JSON
    metadata_path = os.path.join(BASELINE_MAP_DIR, 'baseline_map.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    print(f"✓ 元数据文件: {os.path.relpath(metadata_path)}")
    
    # 创建使用说明
    readme_path = os.path.join(BASELINE_MAP_DIR, 'README.md')
    readme_content = f"""# 基线地图 (Baseline Map)

## 地图参数

### 尺寸与分辨率
- **栅格宽度**: {metadata['width']} 像素
- **栅格高度**: {metadata['height']} 像素
- **分辨率**: {metadata['resolution']:.4f} 米/像素
- **真实宽度**: {metadata['width'] * metadata['resolution']:.2f} 米
- **真实高度**: {metadata['height'] * metadata['resolution']:.2f} 米
- **面积**: {metadata['width'] * metadata['resolution'] * metadata['height'] * metadata['resolution']:.2f} 平方米

### 坐标系统
- **原点坐标**: ({metadata['origin_x']:.2f}, {metadata['origin_y']:.2f}) 米
- **中心坐标**: (0, 0) 米（地图中心）
- **坐标轴**: X向右（红），Y向上（绿）
- **手性**: 右手定则

## 地图数据

### 文件列表
- `baseline_map.png` - 地图图像 (PNG格式)
- `baseline_map.json` - 地图元数据 (JSON格式)

### 图像说明
- **白色**: 激光雷达已探索的区域
- **灰色**: 未知/未探索区域
- **黑色**: 确定的障碍物

## 使用方法

### 在Python中加载地图

```python
import json
from PIL import Image
import numpy as np

# 加载元数据
with open('baseline_map.json', 'r') as f:
    metadata = json.load(f)

# 加载地图图像
map_image = Image.open('baseline_map.png')
map_array = np.array(map_image)

# 获取地图参数
origin_x = metadata['origin_x']
origin_y = metadata['origin_y']
width = metadata['width']
height = metadata['height']
resolution = metadata['resolution']

print(f"地图尺寸: {{width}} × {{height}} 像素")
print(f"分辨率: {{resolution}} 米/像素")
print(f"原点: ({{origin_x}}, {{origin_y}}) 米")
```

### 坐标转换

#### 栅格坐标 → 真实坐标
```python
real_x = origin_x + grid_x * resolution
real_y = origin_y + grid_y * resolution
```

#### 真实坐标 → 栅格坐标
```python
grid_x = int((real_x - origin_x) / resolution)
grid_y = int((real_y - origin_y) / resolution)
```

### 检查点的地图值

```python
if 0 <= grid_x < width and 0 <= grid_y < height:
    pixel_value = map_array[grid_y, grid_x]
    
    if pixel_value == 128:
        print("未知区域")
    elif pixel_value == 255:
        print("可通行区域")
    elif pixel_value == 0:
        print("障碍物")
```

## 更新地图

若需要更新基线地图，运行：
```bash
python save_baseline_map.py
```

这将重新获取最新的地图并覆盖当前文件。

---
生成时间: {metadata.get('timestamp', 'N/A')}
API端点: /api/core/slam/v1/maps/explore
"""
    
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    print(f"✓ 说明文件: {os.path.relpath(readme_path)}")


def main():
    print("\n" + "=" * 80)
    print("获取激光探索地图作为基线底图")
    print("=" * 80)
    print()
    
    # 创建目录
    ensure_map_dirs()
    print()
    
    # 获取地图
    print("【获取地图】")
    data = fetch_explore_map()
    if data is None:
        return 1
    print()
    
    # 解析地图
    print("【解析地图】")
    result = parse_map_data(data)
    if result is None:
        print("✗ 解析失败")
        return 1
    
    metadata, map_array = result
    print(f"  栅格尺寸: {metadata['width']} × {metadata['height']}")
    print(f"  分辨率: {metadata['resolution']:.4f} 米/像素")
    print(f"  原点: ({metadata['origin_x']:.2f}, {metadata['origin_y']:.2f}) 米")
    print()
    
    # 创建地图图像
    print("【创建地图图像】")
    map_colored = create_map_image(map_array)
    print(f"  三色地图已创建")
    print()
    
    # 保存地图文件
    print("【保存地图文件】")
    save_baseline_map(metadata, map_colored)
    print()
    
    print("=" * 80)
    print("✓ 基线地图保存完成")
    print(f"  位置: {os.path.relpath(BASELINE_MAP_DIR)}")
    print("=" * 80)
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
