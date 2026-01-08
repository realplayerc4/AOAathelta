# Beacon 全局坐标计算 - 坐标系说明

## 坐标系定义

### 1. Anchor 局部坐标系 (相对坐标系)
- **原点**: Anchor 的位置（即小车上 Anchor 的装置位置）
- **X 轴**: 车体右侧方向（横向，向右为正）
- **Y 轴**: 车体前方方向（纵向，向前为正）
- **参考**: 与车体朝向一致

**关键点**: Anchor 给出的坐标就是在这个坐标系中的值，由卡尔曼滤波器输出

### 2. 全局坐标系 (世界坐标系)
- **原点**: 地图/环境的固定参考点
- **X 轴**: 固定方向（例如东方）
- **Y 轴**: 固定方向（例如北方）
- **参考**: 不随车体旋转

**关键点**: 地图上的所有固定物体坐标都在这个系统中

## 坐标转换过程

### 已知量
1. **Beacon 局部坐标** (来自卡尔曼滤波器):
   - `local_x`: Beacon 相对 Anchor 的 X 坐标（车体右侧）
   - `local_y`: Beacon 相对 Anchor 的 Y 坐标（车体前方）

2. **Anchor 全局信息** (来自 /tracked_pose):
   - `anchor_x`: Anchor 在全局坐标系中的 X 坐标
   - `anchor_y`: Anchor 在全局坐标系中的 Y 坐标
   - `anchor_theta`: Anchor 的全局朝向（弧度）

### 转换公式

使用二维旋转矩阵进行坐标变换：

```
[x_global]   [cos(θ) -sin(θ)] [local_x]   [anchor_x]
[y_global] = [sin(θ)  cos(θ)] [local_y] + [anchor_y]
```

展开后：
```
x_global = anchor_x + local_x * cos(θ) - local_y * sin(θ)
y_global = anchor_y + local_x * sin(θ) + local_y * cos(θ)
```

其中：
- θ = anchor_theta（Anchor 的全局朝向）
- cos(θ) = 全局 X 轴方向在车体坐标系中的 X 分量
- sin(θ) = 全局 X 轴方向在车体坐标系中的 Y 分量

### 理解这个公式

#### 例1: Anchor 朝向东（θ=0）
```
x_global = anchor_x + local_x * 1 - local_y * 0 = anchor_x + local_x
y_global = anchor_y + local_x * 0 + local_y * 1 = anchor_y + local_y
```
- Beacon 在车的右侧(+X_local)时，会向东(+X_global)
- Beacon 在车的前方(+Y_local)时，会向北(+Y_global)

#### 例2: Anchor 朝向北（θ=π/2）
```
cos(π/2) = 0, sin(π/2) = 1

x_global = anchor_x + local_x * 0 - local_y * 1 = anchor_x - local_y
y_global = anchor_y + local_x * 1 + local_y * 0 = anchor_y + local_x
```
- Beacon 在车的右侧(+X_local)时，会向北(+Y_global)
- Beacon 在车的前方(+Y_local)时，会向西(-X_global)

## 实现代码

```python
def _transform_local_to_global(self, local_x: float, local_y: float, 
                               anchor_x: float, anchor_y: float, 
                               anchor_theta: float) -> dict:
    """将 Beacon 在 Anchor 坐标系中的坐标转换为全局坐标"""
    import math
    
    # 计算旋转矩阵的三角函数
    cos_theta = math.cos(anchor_theta)
    sin_theta = math.sin(anchor_theta)
    
    # 应用旋转和平移变换
    x_global = anchor_x + local_x * cos_theta - local_y * sin_theta
    y_global = anchor_y + local_x * sin_theta + local_y * cos_theta
    
    return {'x': x_global, 'y': y_global}
```

## 调试和验证

### 日志输出
应用会输出如下格式的日志：

```
【Beacon坐标计算】
  1️⃣ Beacon在Anchor坐标系中的局部坐标:
     x_local=1.234m (车体右侧)
     y_local=0.567m (车头前方)
     confidence=0.89

  2️⃣ Anchor在全局坐标系中的位置和朝向:
     x_anchor=10.000m
     y_anchor=20.000m
     theta=0.785rad (45.0°)

  3️⃣ Beacon在全局坐标系中的位置:
     x_global=10.827m
     y_global=20.827m
  ✅ 坐标转换完成
```

### 手工验证例子

**场景**: 
- Anchor 在全局 (10, 20)，朝向 45°
- Beacon 在 Anchor 局部 (1.0, 1.0)

**计算**:
```
cos(45°) = 0.707
sin(45°) = 0.707

x_global = 10 + 1.0 * 0.707 - 1.0 * 0.707 = 10
y_global = 20 + 1.0 * 0.707 + 1.0 * 0.707 = 21.414
```

**验证**: Beacon 相对于 Anchor 向右上方 45° 方向 √2 米处，在朝向为 45° 的坐标系中就是正北方向（因为坐标系也旋转了 45°）

## 地图显示

beacon 的全局坐标经过转换后，会：
1. 存储到 `beacon_global_position` 字典中
2. 发布到 `/globe_beacon` 话题
3. 在地图查看器中显示为红色圆点

## 可能的问题和解决方案

### 问题: 红点显示在错误的位置

**检查清单**:
1. ✓ Anchor 的朝向 (theta) 是否正确
   - 查看日志中 theta 的值，对应的度数是否合理
   
2. ✓ Beacon 局部坐标是否合理
   - 距离和方向是否符合实际的信号源位置
   
3. ✓ Anchor 的全局位置是否正确
   - 查看 /tracked_pose 中的 pos 值
   - 与地图上的显示是否一致（蓝色箭头位置）

### 问题: 坐标变换不对

如果需要修改坐标系定义（例如 X 和 Y 轴含义不同），需要修改:
- `_transform_local_to_global()` 方法中的公式
- 坐标系的注释说明

## 文件位置

- **坐标转换实现**: [ui/main_window.py](ui/main_window.py) - `_transform_local_to_global()` 方法 (第 845 行)
- **beacon 数据计算**: [ui/main_window.py](ui/main_window.py) - `/tracked_pose` 处理部分 (第 610 行)
- **地图显示标注**: [ui/widgets/map_viewer.py](ui/widgets/map_viewer.py) - `_mark_beacon_on_image()` 方法

## 更新日期
2026-01-08
