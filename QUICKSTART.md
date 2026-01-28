# 快速启动指南 - AOA Beacon 地盘定位系统

## 功能简介

本系统实现了：
- ✅ **地盘地图读取** - 通过API获取地盘的实时位置和朝向
- ✅ **2D位置提取** - 将Beacon信号转换到地图全局坐标系
- ✅ **姿态（朝向）提取** - 从Beacon速度矢量估计运动方向

## 安装依赖

```bash
pip install requests numpy PySerial
```

## 配置

编辑 `config.py`，设置API地址和密钥：

```python
API_BASE_URL = "http://192.168.11.1:1448"  # 地盘API地址
API_SECRET = "123456"                       # 认证密钥
```

## 快速开始

### 步骤 1: 验证功能

运行集成测试，验证API连接和坐标变换：

```bash
python test_integration.py
```

预期输出：
```
✓ API 客户端初始化成功
✓ 成功获取位姿态:
  - x: -0.140620
  - y: 0.040851
  - yaw: -3.080655 rad (-176.5°)
```

### 步骤 2: 启动实时定位

自动检测串口：
```bash
python test_realtime_beacon.py
```

或手动指定串口：
```bash
python test_realtime_beacon.py --port /dev/ttyUSB0 --duration 60
```

### 步骤 3: 查看实时数据

实时输出示例：
```
t=  0.05s d= 1.50m a=-25° | local= 0.55/ 1.20m | global= -0.25/ 1.95m yaw= 0.125rad conf=0.92 speed= 0.15m/s status=✓(CONNECTED)|pose=ok
t=  0.10s d= 1.52m a=-24° | local= 0.58/ 1.22m | global= -0.22/ 1.97m yaw= 0.128rad conf=0.93 speed= 0.18m/s status=✓(CONNECTED)|pose=ok
```

## 输出数据说明

| 字段 | 含义 | 单位 |
|------|------|------|
| t | 运行时间 | 秒 |
| d | 极坐标距离 | 米 |
| a | 极坐标角度 | 度 |
| local | Anchor局部坐标（相对位置） | x/y 米 |
| global | 地图全局坐标（绝对位置） | x/y 米 |
| yaw | Beacon朝向角 | 弧度 |
| conf | 滤波置信度 | 0-1 |
| speed | Beacon运动速度 | 米/秒 |

## 坐标系说明

- **Anchor局部坐标** (local)：相对于Anchor/地盘的局部坐标
  - X轴：右侧（相对地盘前向）
  - Y轴：前方（与Beacon 0°方向对齐）

- **地图全局坐标** (global)：地盘在地图中的参考坐标系
  - 获取自地盘SLAM系统
  - (x, y)为位置，yaw为朝向角

## 常见问题

**Q: API连接失败怎么办？**

A: 检查：
1. 地盘是否已启动
2. IP地址是否正确：`ping 192.168.11.1`
3. 网络连接是否正常

**Q: 为什么没有全局坐标数据？**

A: 可能原因：
1. API连接失败（见上）
2. 地盘初始定位未完成
3. SLAM系统未初始化

**Q: 为什么朝向角(yaw)为0？**

A: 朝向是从速度矢量估计的，需要Beacon在运动状态。静止时朝向不可靠。

**Q: 如何改变数据更新频率？**

A: 修改 `config.py` 中的 `POSE_QUERY_INTERVAL`（单位：秒）

```python
POSE_QUERY_INTERVAL = 0.05  # 20Hz
```

## 技术细节

### 坐标变换公式

从Anchor局部坐标转换到地图全局坐标：

```
x_global = x_robot + x_local * cos(yaw_robot) - y_local * sin(yaw_robot)
y_global = y_robot + x_local * sin(yaw_robot) + y_local * cos(yaw_robot)
```

其中：
- (x_robot, y_robot, yaw_robot) = 地盘在地图中的位置和朝向
- (x_local, y_local) = Beacon在Anchor局部的坐标

### 朝向估计

从速度矢量估计Beacon的朝向（运动方向）：

```
local_heading = atan2(vy, vx)
global_heading = yaw_robot + local_heading
```

## 性能指标

- 地盘位姿态查询：20Hz
- 坐标变换延迟：< 1ms
- 内存占用：< 50MB

## 系统架构

```
串口 (Beacon)
    ↓
解析 (ASCII → 极坐标)
    ↓
滤波 (Kalman 极坐标)
    ↓ (局部笛卡尔坐标)
    ├─→ 坐标变换 ←─ API客户端 (地盘位姿态)
            ↓
        全局坐标 (地图参考系)
            ↓
        显示 + 统计
```

## 下一步

1. **集成到应用** - 使用 `coordinate_transform` 模块的接口在自己的程序中
2. **WebSocket发布** - 实时推送定位数据到其他系统
3. **多Anchor支持** - 使用多个Anchor进行三角测量定位

## 相关文件

- `coordinate_transform.py` - 坐标变换模块
- `core/api_client.py` - API客户端
- `test_realtime_beacon.py` - 主程序
- `config.py` - 配置文件
- `INTEGRATION_README.md` - 详细文档
