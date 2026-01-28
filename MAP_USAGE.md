# 地图获取和可视化工具

## 概述

从SLAM系统获取激光探索栅格地图并进行可视化。

## API端点

```
GET /api/core/slam/v1/maps/explore
```

可选参数：`min_x`, `min_y`, `max_x`, `max_y`（指定地图范围）

## 地图格式

响应为二进制字节流：

### 元数据（前36字节，小端字节序）

| 位置   | 类型    | 描述                    |
|--------|---------|-------------------------|
| 0-3    | float   | 地图起始X坐标（米）      |
| 4-7    | float   | 地图起始Y坐标（米）      |
| 8-11   | uint32  | X轴栅格数量（宽度）      |
| 12-15  | uint32  | Y轴栅格数量（高度）      |
| 16-19  | float   | 分辨率（米/格子）        |
| 20-31  | byte[]  | 预留                    |
| 32-35  | uint32  | 地图数据字节数          |

### 地图数据（从第36字节开始）

每个字节代表一个栅格：
- **0**: 未探索区域（灰色）
- **1-199**: 探索区域/可通行空间（白色）
- **200-255**: 障碍物（黑色）

常见值：
- **0**: 未探索
- **127**: 已探索的可通行区域
- **255**: 确定的障碍物

## 使用方法

### 1. 获取和可视化完整地图

```bash
python fetch_explore_map.py
```

生成文件：
- `explore_map.bin` - 原始二进制数据
- `explore_map_visualization.png` - 综合可视化（4个子图）
- `explore_map_raw.png` - 原始地图
- `explore_map_inverted.png` - 反转地图（白色=可通行）
- `explore_map_classified.png` - 分类地图（白/灰/黑）

### 2. 获取指定范围的地图

```bash
python fetch_explore_map.py --min-x -10 --min-y -5 --max-x 10 --max-y 5
```

### 3. 只保存数据不可视化

```bash
python fetch_explore_map.py --save
```

### 4. 验证地图元数据

```bash
python verify_map.py
```

## 示例输出

```
地图信息:
  尺寸: 1051 × 428 栅格
  真实尺寸: 52.55 × 21.40 米
  面积: 1124.57 平方米
  原点: (-29.20, -8.55) 米
  分辨率: 5.00 厘米/格子

地图数据统计:
  唯一值数量: 79
  值0（未探索）: 353077 (78.5%)
  值127（可通行）: 60294 (13.4%)
  值255（障碍）: 0 (0.0%)
```

## 在应用中使用

```python
from fetch_explore_map import fetch_explore_map, parse_explore_map

# 获取地图
data = fetch_explore_map()

# 解析
metadata, map_array = parse_explore_map(data)

# 访问信息
print(f"地图尺寸: {metadata['width']} × {metadata['height']}")
print(f"分辨率: {metadata['resolution']} 米/格子")
print(f"原点: ({metadata['origin_x']}, {metadata['origin_y']})")

# map_array 是 numpy 数组 (height, width)
# 可以直接使用进行坐标转换
```

## 坐标系统

- **栅格坐标**: (0, 0) 到 (width-1, height-1)
- **真实坐标**: 从 origin 开始，每个格子 resolution 米

转换公式：
```python
real_x = origin_x + grid_x * resolution
real_y = origin_y + grid_y * resolution
```

## 相关文件

- `fetch_explore_map.py` - 主工具（获取、解析、可视化）
- `verify_map.py` - 验证工具
- `config.py` - API配置（URL、密钥等）
