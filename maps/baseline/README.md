# 基线地图 (Baseline Map)

## 地图参数

### 尺寸与分辨率
- **栅格宽度**: 1051 像素
- **栅格高度**: 428 像素
- **分辨率**: 0.0500 米/像素
- **真实宽度**: 52.55 米
- **真实高度**: 21.40 米
- **面积**: 1124.57 平方米

### 坐标系统
- **原点坐标**: (-29.20, -8.55) 米
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

print(f"地图尺寸: {width} × {height} 像素")
print(f"分辨率: {resolution} 米/像素")
print(f"原点: ({origin_x}, {origin_y}) 米")
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
生成时间: N/A
API端点: /api/core/slam/v1/maps/explore
