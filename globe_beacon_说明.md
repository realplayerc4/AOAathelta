# Globe Beacon 全局坐标话题实现说明

## 功能概述

本文档说明 **`/globe_beacon`** 话题的实现，该话题用于发布卡尔曼滤波后的信标 (beacon) 的全局坐标位置，供实时地图显示使用。

## 核心流程

```
/tracked_pose (Anchor 全局位置和朝向)
    ↓
    获取卡尔曼滤波后的 beacon 局部坐标 (AOA Worker)
    ↓
    局部坐标 → 全局坐标 (坐标变换)
    ↓
    发布 /globe_beacon 话题
    ↓
    地图显示（红色圆点标记）
```

## 坐标系说明

### Anchor 局部坐标系

- **Y 轴**：Anchor 正前方（机器人前进方向）
- **X 轴**：Anchor 右侧（面向前进方向时的右手方向）
- **原点**：Anchor 的位置
- **遵循**：右手规则

### 全局坐标系

- 同实时地图中的坐标系
- Beacon 全局坐标基于地图原点

## 坐标变换公式

从 Anchor 局部坐标系转换到全局坐标系：

```
x_global = x_anchor + local_x * cos(theta) - local_y * sin(theta)
y_global = y_anchor + local_x * sin(theta) + local_y * cos(theta)
```

其中：
- `(x_anchor, y_anchor)`：Anchor 的全局位置（米）
- `(local_x, local_y)`：Beacon 在 Anchor 局部坐标系中的位置（米）
- `theta`：Anchor 的全局朝向（弧度，从 /tracked_pose 话题中获取）

### 坐标变换验证

运行单元测试验证坐标变换的正确性：

```bash
python3 test_globe_beacon_unit.py
```

## 实现细节

### 1. AOA Worker (`workers/aoa_worker.py`)

新增方法 `get_filtered_beacon_coordinates(tag_id=1)` 用于获取卡尔曼滤波后的信标坐标：

```python
def get_filtered_beacon_coordinates(self, tag_id: int = 1) -> dict:
    """
    获取指定标签的当前滤波坐标（Anchor 局部坐标系）
    
    Args:
        tag_id: 标签 ID，默认为 1
    
    Returns:
        {
            'tag_id': int,
            'x': float,           # Anchor 局部坐标 X (米)
            'y': float,           # Anchor 局部坐标 Y (米)
            'confidence': float,  # 置信度 0-1
            'velocity_x': float,  # X 速度 (米/秒)
            'velocity_y': float,  # Y 速度 (米/秒)
            'acceleration_x': float,  # X 加速度 (米/秒²)
            'acceleration_y': float,  # Y 加速度 (米/秒²)
            'initialized': bool   # 滤波器是否已初始化
        }
    """
```

### 2. 主窗口 (`ui/main_window.py`)

#### 坐标变换方法
```python
def _transform_local_to_global(self, local_x, local_y, anchor_x, anchor_y, anchor_theta) -> dict:
    """将 Anchor 局部坐标转换为全局坐标"""
```

#### 话题发布方法
```python
def _publish_globe_beacon(self, beacon_data: dict):
    """发布 /globe_beacon 话题（内部信号）"""
```

#### 集成点

在 `/tracked_pose` 话题处理中：
1. 获取 Anchor 全局位置和朝向
2. 查询卡尔曼滤波后的 beacon 局部坐标
3. 进行坐标变换
4. 发布 `/globe_beacon` 话题
5. 更新地图显示

### 3. 地图查看器 (`ui/widgets/map_viewer.py`)

#### 更新 Beacon 位置
```python
def update_beacon_position(self, beacon_data: dict):
    """更新 beacon 全局坐标位置"""
```

#### 绘制 Beacon 标记
```python
def _mark_beacon_on_image(self, pixmap, map_data, beacon_data) -> QPixmap:
    """在地图上绘制 beacon 标记（红色圆点）"""
```

**标记特点**：
- 颜色：红色 (RGB: 255, 0, 0)
- 大小：根据置信度动态调整（置信度越高，圆点越大）
- 范围：3-8 像素半径

## 话题格式

### `/globe_beacon` 话题消息格式

```json
{
    "topic": "/globe_beacon",
    "tag_id": 1,
    "x": 2.5,          # 全局坐标 X（米）
    "y": 3.7,          # 全局坐标 Y（米）
    "confidence": 0.92, # 滤波器置信度（0-1）
    "timestamp": 1234567890.123
}
```

## 使用场景

### 实时地图显示

当地图查看器打开时，每次收到 `/tracked_pose` 话题消息：
1. 自动查询最新的 beacon 位置
2. 计算全局坐标
3. 在地图上用红色圆点标记
4. 置信度高时圆点更大，提示用户定位更准确

### 数据日志记录

可以记录所有 `/globe_beacon` 消息用于分析：
- Beacon 的运动轨迹
- 定位准确性（通过置信度）
- 时间序列数据

## 配置参数

目前配置参数硬编码在代码中：

- `tag_id = 1`：监测的信标 ID
- 坐标变换：基于 `/tracked_pose` 实时获取的 Anchor 状态
- 卡尔曼滤波：使用 AOA Worker 中配置的参数

可在 `config.py` 中扩展配置项：

```python
# Beacon 话题发布配置
GLOBE_BEACON_TAG_ID = 1  # 监测的信标 ID
GLOBE_BEACON_UPDATE_MODE = 'on_tracked_pose'  # 更新触发模式
```

## 地图显示标记说明

地图上包含三种标记：

| 标记 | 颜色 | 含义 |
|-----|------|------|
| **×** | 绿色 | 地图坐标原点 (0, 0) |
| **→** | 蓝色 | Anchor 位置和朝向 |
| **●** | 红色 | Beacon 全局位置（置信度越高越大） |

## 测试验证

### 单元测试

```bash
# 验证坐标变换逻辑
python3 test_globe_beacon_unit.py
```

测试覆盖：
- ✓ 基本坐标变换（无旋转）
- ✓ 旋转坐标变换（90°）
- ✓ 平移和旋转组合
- ✓ 多角度验证（0°, 45°, 90°）

### 集成测试

待 AOA 串口读取完全集成后进行实际测试。

## 故障排查

### Beacon 不显示

**可能原因**：
1. 卡尔曼滤波器未初始化 → 需要收到足够的 AOA 数据
2. `/tracked_pose` 数据格式错误 → 检查数据来源
3. 地图查看器未打开 → 打开地图查看器窗口

**排查步骤**：
```python
# 检查滤波器状态
state = aoa_worker.kalman_filter.get_filter_state(tag_id=1)
print(f"滤波器状态: {state}")

# 检查 beacon 坐标
coords = aoa_worker.get_filtered_beacon_coordinates(tag_id=1)
print(f"Beacon 坐标: {coords}")
```

### 坐标显示不正确

**可能原因**：
1. Anchor 朝向角度单位错误 → `/tracked_pose` 使用弧度，确保转换正确
2. 坐标系定义不一致 → 重新确认 Y 轴正前方的定义

**验证方式**：
```bash
# 运行坐标变换单元测试
python3 test_globe_beacon_unit.py
```

## 性能考虑

- **更新频率**：由 `/tracked_pose` 话题的发布频率决定
- **计算开销**：极低（仅包含三角函数计算）
- **内存使用**：固定，只保存最新 beacon 位置

## 扩展方向

### 多信标支持

当前实现只监测 `tag_id=1` 的信标。若需支持多信标：

1. 修改 `get_filtered_beacon_coordinates()` 支持多标签
2. 在主窗口中循环处理所有活跃标签
3. 在地图上绘制多个圆点（可用不同大小区分）

### 话题订阅

可以在其他模块中订阅 `/globe_beacon` 话题：

```python
# 注册话题回调
ws_subscriber.enable_topic('/globe_beacon')

# 在话题消息处理中
def on_globe_beacon(self, payload):
    beacon_x = payload['x']
    beacon_y = payload['y']
    confidence = payload['confidence']
    # ... 处理全局 beacon 坐标
```

## 相关文档

- [卡尔曼滤波系统架构](卡尔曼滤波系统架构.md)
- [实时地图显示功能说明](实时地图显示功能说明.md)
- [追踪位置标注说明](追踪位置标注说明.md)

## 修改记录

| 日期 | 版本 | 说明 |
|-----|------|------|
| 2026-01-08 | 1.0 | 初始版本 - 实现 /globe_beacon 话题 |
