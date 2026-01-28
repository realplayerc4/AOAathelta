# AOA Beacon 实时定位系统 - 地盘地图坐标集成

## 功能概述

该系统已集成地盘位姿态API，实现了将Beacon信号从Anchor局部坐标系变换到地图全局坐标系的完整功能。

### 核心功能

1. **地盘位姿态获取** - 通过REST API实时获取地盘在地图中的位置和朝向
2. **坐标系变换** - 将Anchor局部极坐标自动转换到地图全局笛卡尔坐标
3. **朝向估计** - 从速度矢量估计Beacon的运动方向
4. **多数据源融合** - 整合串口Beacon数据、卡尔曼滤波和地盘API信息

## 系统架构

```
┌──────────────┐
│   Beacon     │  （UWB信标设备）
└──────┬───────┘
       │ 极坐标数据 (距离, 角度)
       ▼
┌──────────────────────────┐
│  AOASerialReader         │  （串口接收）
└──────┬───────────────────┘
       │ ASCII字节流
       ▼
┌──────────────────────────┐
│  BeaconDataParser        │  （解析）
└──────┬───────────────────┘
       │ 解析后的测量值
       ▼
┌──────────────────────────┐
│  MultiTargetKalmanFilter │  （极坐标滤波）
└──────┬───────────────────┘
       │ 局部笛卡尔坐标 (x_local, y_local)
       │
       ├──────────────────────┐
       │                      ▼
       │          ┌──────────────────────┐
       │          │  APIClient           │  ←─ GET /api/core/slam/v1/localization/pose
       │          │  fetch_pose()        │
       │          └──────┬───────────────┘
       │                 │ 地盘位姿态 (x_robot, y_robot, yaw_robot)
       │                 │
       ▼                 ▼
┌────────────────────────────────────┐
│  CoordinateTransformer             │
│  transform_beacon_position()       │  （坐标变换）
└────────┬─────────────────────────┘
         │
         ▼
    全局坐标 (x_global, y_global, yaw)
    地图参考系中的Beacon位置和朝向
```

## 配置说明

编辑 `config.py` 配置API连接参数：

```python
# API 服务器地址
API_BASE_URL = "http://192.168.11.1:1448"

# API 认证密钥
API_SECRET = "123456"

# 其他参数...
```

## 使用方法

### 1. 验证集成功能

运行集成测试脚本验证API连接和坐标变换：

```bash
python test_integration.py
```

这将测试：
- API连接和地盘位姿态获取
- 坐标变换的正确性
- 朝向估计算法

### 2. 实时定位

启动实时Beacon定位系统：

```bash
python test_realtime_beacon.py
```

或指定串口：

```bash
python test_realtime_beacon.py --port /dev/ttyUSB0 --duration 60
```

### 3. 输出格式

实时输出包括：

```
t=  0.05s d= 1.50m a=-25° | local= 0.55/ 1.20m | global= -0.25/ 1.95m yaw= 0.125rad conf=0.92 speed= 0.15m/s status=✓(CONNECTED)|pose=ok
```

字段说明：
- `t`: 运行时间
- `d`: 极坐标距离
- `a`: 极坐标角度
- `local`: Anchor局部笛卡尔坐标
- `global`: 地图全局笛卡尔坐标和朝向
- `conf`: 滤波置信度
- `speed`: 速度
- `pose`: 地盘位姿态获取状态

## 坐标变换原理

### 极坐标到笛卡尔坐标（Anchor局部）

```
angle_rad = angle_deg * π / 180
y_local = distance * cos(angle_rad)      （前方为正）
x_local = -distance * sin(angle_rad)     （右侧为正）
```

### Anchor局部到地图全局

Anchor安装在地盘上，其位置就是地盘位置。使用2D旋转矩阵：

```
x_global = x_robot + x_local * cos(yaw_robot) - y_local * sin(yaw_robot)
y_global = y_robot + x_local * sin(yaw_robot) + y_local * cos(yaw_robot)
```

其中：
- `(x_robot, y_robot)`: 地盘在地图中的位置
- `yaw_robot`: 地盘的朝向角（弧度）
- `(x_local, y_local)`: Beacon相对于Anchor的局部坐标

### 朝向角估计

从速度矢量估计Beacon的运动方向：

```
local_heading = atan2(vy, vx)           （相对于Anchor）
global_heading = yaw_robot + local_heading  （在地图坐标系中）
```

## 数据流

### 单次更新的完整流程

1. **接收** - Beacon通过串口发送数据
2. **解析** - 提取极坐标(距离, 角度)
3. **滤波** - 卡尔曼滤波产生平滑的极坐标
4. **转换** - 转换到Anchor局部笛卡尔坐标
5. **获取位姿** - 从API查询当前地盘位置和朝向（20Hz）
6. **变换** - 使用旋转矩阵变换到地图全局坐标
7. **输出** - 显示完整的(x_global, y_global, yaw)信息

### 坐标系定义

**Anchor局部坐标系**：
- 原点：Anchor位置
- X轴：右侧（相对地盘前向）
- Y轴：前方（与极坐标0°方向对齐）

**地图全局坐标系**：
- 原点：SLAM系统的参考点
- X/Y轴：由地盘API的yaw定义

## API接口

### 获取地盘位姿态

```http
GET /api/core/slam/v1/localization/pose
```

**响应示例**：
```json
{
  "pitch": 0,
  "roll": 0,
  "x": -0.1406204525543451,
  "y": 0.04085133452255775,
  "yaw": -3.080654650191927,
  "z": 0
}
```

**字段说明**：
- `x`, `y`, `z`: 位置（米，其中z通常为0）
- `yaw`: 偏航角（弧度，范围通常为[-π, π]）
- `pitch`, `roll`: 俯仰角和翻滚角（通常为0）

## 类和方法参考

### CoordinateTransformer

```python
from coordinate_transform import CoordinateTransformer

transformer = CoordinateTransformer()

# 将局部坐标转换到全局坐标
global_x, global_y = transformer.transform_beacon_to_global(
    beacon_local_x=0.5,
    beacon_local_y=1.2,
    robot_pose={'x': 10.0, 'y': 20.0, 'yaw': 0.785}
)

# 验证位姿态的有效性
is_valid = transformer.validate_robot_pose(robot_pose)
```

### APIClient

```python
from core.api_client import APIClient

client = APIClient()

# 获取地盘位姿态
pose = client.fetch_pose()
# Returns: {'x': float, 'y': float, 'yaw': float, 'z': float, 'pitch': float, 'roll': float}
```

### 便利函数

```python
from coordinate_transform import transform_beacon_position

# 完整的位置变换（包括朝向）
global_position = transform_beacon_position(
    filtered_position={'x': 0.5, 'y': 1.2, 'vx': 0.1, 'vy': 0.3, 'confidence': 0.85},
    robot_pose={'x': 10.0, 'y': 20.0, 'yaw': 0.785}
)
# Returns: {'x': float, 'y': float, 'yaw': float, ...其他字段}
```

## 故障排除

### API连接失败

**症状**：获取地盘位姿态API的错误

**解决方案**：
1. 验证地盘AMR是否正常运行
2. 检查网络连接：`ping 192.168.11.1`
3. 验证config.py中的API_BASE_URL
4. 检查防火墙设置

### 坐标值异常

**症状**：全局坐标明显错误或不符合预期

**解决方案**：
1. 验证Anchor的安装位置是否正确
2. 检查极坐标滤波是否工作正常（confidence > 0.3）
3. 确认地盘位姿态信息的准确性
4. 查看坐标系定义是否与实际硬件一致

### 朝向角异常

**症状**：yaw角度不合理或跳变

**解决方案**：
1. 确保Beacon有足够的运动速度（静止时朝向不可靠）
2. 检查速度估计是否准确
3. 使用filter_measurement的更长窗口改进速度估计

## 性能指标

- **位姿态查询频率**：20Hz（可配置）
- **Beacon数据处理**：实时（< 10ms延迟）
- **坐标变换开销**：< 1ms
- **内存占用**：< 50MB

## 扩展方向

未来可以考虑的改进：

1. **多Anchor支持** - 支持多个Anchor的加权融合定位
2. **IMU融合** - 结合IMU传感器改进朝向估计
3. **地图栅格化** - 支持地图自碰撞检测
4. **WebSocket发布** - 实时推送定位数据到AMR系统
5. **可视化工具** - 地图上的实时位置标记

## 许可证

MIT License
