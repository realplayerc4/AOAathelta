# Beacon 全局坐标计算 - 改进总结

## 问题描述
beacon 的全局位置计算需要根据 Anchor 的坐标系进行正确的转换。Anchor 是绑定在小车上的，其坐标系是相对于车体朝向的。

## 解决方案

### 1. 坐标系统的明确定义

#### Anchor 局部坐标系
- **原点**: Anchor 的位置（小车上 Anchor 的装置位置）
- **X 轴**: 车体右侧（横向）
- **Y 轴**: 车体前方（纵向）
- **特点**: 与车体朝向完全一致

#### 全局坐标系
- **原点**: 地图/环境的固定参考点
- **X、Y 轴**: 固定不变，不随车体旋转

### 2. 坐标转换公式

使用二维旋转矩阵，将 Beacon 在 Anchor 坐标系中的坐标转换为全局坐标：

```
x_global = anchor_x + local_x * cos(θ) - local_y * sin(θ)
y_global = anchor_y + local_x * sin(θ) + local_y * cos(θ)
```

其中：
- `local_x, local_y`: Beacon 在 Anchor 坐标系中的坐标（来自卡尔曼滤波器）
- `anchor_x, anchor_y`: Anchor 的全局位置（来自 /tracked_pose）
- `θ = anchor_theta`: Anchor 的全局朝向（来自 /tracked_pose 的 ori）

### 3. 数据流

```
原始测量数据（极坐标）
    ↓
卡尔曼滤波
    ↓ [get_filtered_beacon_coordinates()]
Beacon 在 Anchor 坐标系中的笛卡尔坐标 (local_x, local_y)
    ↓
获取 Anchor 的全局位置和朝向 (/tracked_pose 消息)
    ↓ [_transform_local_to_global()]
Beacon 的全局坐标 (x_global, y_global)
    ↓
发布 /globe_beacon 话题
    ↓
地图显示为红色圆点
```

## 代码改进

### 1. 改进坐标转换方法文档

文件: `ui/main_window.py`
位置: 第 865 行 `_transform_local_to_global()` 方法

**改进内容**:
- 添加了详细的坐标系定义说明
- 明确标注了各参数的含义
- 加入了旋转矩阵的数学说明
- 添加了理解公式的例子

### 2. 改进日志输出

文件: `ui/main_window.py`
位置: 第 610 行和第 673 行的 /tracked_pose 处理

**改进内容**:
- 使用 `logger.info()` 而不是 `logger.debug()`，使信息更容易看到
- 分三步显示坐标转换过程：
  1. Beacon 局部坐标
  2. Anchor 全局位置和朝向
  3. 转换后的 Beacon 全局坐标
- 添加了中文标注说明坐标轴方向
- 添加了朝向的度数表示

**日志示例**:
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

### 3. 新增文档

文件: `BEACON_坐标转换说明.md`

**包含内容**:
- 详细的坐标系定义
- 转换公式的推导和说明
- 实际例子和手工验证
- 地图显示的说明
- 问题排查指南

## 验证方法

### 方式 1: 查看日志
1. 启动应用: `python main.py`
2. 观察控制台输出，查看是否有【Beacon坐标计算】的日志
3. 检查坐标值是否合理

### 方式 2: 手工计算验证
1. 从日志中获取三个数值：
   - local_x, local_y
   - anchor_x, anchor_y, theta
2. 使用公式手工计算 x_global, y_global
3. 与日志中显示的值对比

### 方式 3: 可视化验证
1. 打开地图查看器（点击"📍 显示实时地图"）
2. 观察红点位置是否合理
3. 与蓝色箭头（Anchor 位置）的相对位置是否合理

## 可能需要调整的地方

如果红点显示的位置与预期不符，可能需要：

1. **检查坐标轴定义**
   - X 轴是否应该是车体左侧而不是右侧？
   - Y 轴是否应该是车体后方而不是前方？
   - 如果是，修改 `_transform_local_to_global()` 中的公式

2. **检查角度定义**
   - θ = 0 时车体朝向是否应该是不同方向？
   - 需要调整朝向的参考系统

3. **检查坐标原点**
   - Anchor 的位置是否就是小车的位置？
   - 还是有偏移？
   - 如果有偏移，需要在计算前加上偏移量

## 文件清单

### 修改的文件
1. `ui/main_window.py`
   - `_transform_local_to_global()` 方法（第 865 行）
   - /tracked_pose 处理部分（第 610 行和第 673 行）

### 新建的文件
1. `BEACON_坐标转换说明.md` - 坐标转换的详细说明
2. `BEACON_显示故障排查.md` - 红点显示的故障排查指南

### 保持不变的文件
1. `workers/aoa_worker.py` - `get_filtered_beacon_coordinates()` 方法
2. `ui/widgets/map_viewer.py` - `_mark_beacon_on_image()` 方法
3. `core/`, `models/`, `utils/` - 所有文件保持不变

## 下一步

1. **测试验证**: 用实际数据测试坐标转换是否正确
2. **参数调整**: 根据实际结果调整坐标系定义
3. **多信标支持**: 扩展到支持多个 beacon (tag_id > 1)
4. **轨迹记录**: 记录 beacon 的历史位置

## 版本信息
- 更新日期: 2026-01-08
- 版本: 1.1
- 主要改进: 改进坐标转换日志和文档
