# AOA 功能快速参考

## 快速开始

### 1. 启动应用

```bash
cd /home/han14/gitw/AUTOXINGAOA
python main.py
```

### 2. AOA 数据标签页

1. 在主窗口中找到 "📡 AOA 数据" 标签页
2. 选择串口（默认 `/dev/ttyUSB0`）
3. 确认波特率（默认 115200）
4. 点击 "🔌 连接" 按钮

### 3. 监控数据

- **实时数据表**：显示最新接收的帧
- **统计信息**：显示总帧数、成功帧、错误率

## 数据含义

### 帧信息

| 字段 | 说明 | 单位 |
|------|------|------|
| 帧# | 帧序号 | - |
| 时间戳 | 接收时间 | ISO 8601 |
| ANCHER ID | 基站 ID | - |
| TAG ID | 标签 ID | - |
| 距离 | 标签到基站的距离 | 米 (m) |
| 角度 | 标签相对于基站的角度 | 度 (°) |
| 电压 | 基站电压 | 毫伏 (mV) |
| 有效性 | 校验和是否通过 | ✓/✗ |

## 协议格式速查

### 0x55 协议 - 33 字节

```
[0x55][FN]┌─ANCHER─┬─TIMESTAMP─┬VOLTS┬─TAG ID─┬─DISTANCE─┬ANGLE┬SIGNAL┬[CS]
           │ ROLE/ID│ Local/Sys │     │Role/ID │  int24   │int16│FP/RX │
           └─5B────┴─8B────────┴2B──┴─2B────┴─3B──────┴2B──┴2B───┘
```

### 字段详解

- **ANCHER**: 基站角色和 ID（字节 4-5）
- **TIMESTAMP**: 地方时间和系统时间，各 4 字节（字节 6-13）
- **VOLTS**: 电压（字节 18-19），小端序，单位 mV
- **TAG**: 标签角色和 ID（字节 21-22）
- **DISTANCE**: 距离（字节 23-25），int24，小端序，单位 mm
- **ANGLE**: 角度（字节 26-27），int16，小端序，实际角度×100
- **SIGNAL**: 信号强度（字节 28-29），FP 和 RX dB 值
- **CS**: 校验和（字节 32），前 32 字节的和

## 常用操作

### 查看原始数据

1. 点击 "📄 原始 JSON" 标签页
2. 在 AOA 标签页接收数据后，原始帧数据会显示

### 导出数据

在实现中，您可以扩展 `AOADataWidget` 以添加：

```python
# 导出到 CSV
def export_to_csv(self, filename):
    with open(filename, 'w') as f:
        f.write("Frame,Timestamp,Anchor,Tag,Distance,Angle\n")
        for i in range(self.data_table.rowCount()):
            # 写入行数据
```

### 实时绘图

```python
from PyQt6.QtChart import QChart, QChartView, QLineSeries

# 创建距离随时间的图表
series = QLineSeries()
for frame in frames:
    series.append(time, distance)
```

## 故障排除

### 连接失败

```bash
# 检查串口
ls /dev/ttyUSB*

# 检查权限
sudo usermod -a -G dialout $(whoami)
sudo su

# 测试连接
screen /dev/ttyUSB0 115200
```

### 校验和错误

- 检查波特率是否正确
- 检查硬件连接是否稳定
- 尝试降低波特率

### 没有数据接收

1. 确认设备是否在发送数据
2. 检查串口接线
3. 查看终端日志信息

## Python API 快速参考

### 基本解析

```python
from models.aoa_data import AOAFrame

# 从字节解析单个帧
frame = AOAFrame.from_bytes(data_bytes, frame_id=1)

# 访问数据
print(f"距离: {frame.tag_data.distance}mm")
print(f"角度: {frame.tag_data.angle}°")
print(f"校验和: {'✓' if frame.is_valid else '✗'}")
```

### 协议解析

```python
from core.aoa_protocol import AOAProtocolParser

parser = AOAProtocolParser()

# 解析数据流
frames = parser.parse_stream(byte_stream)

# 获取统计
stats = parser.get_statistics()
```

### 串口读取

```python
from workers.aoa_serial_reader import AOASerialReader

reader = AOASerialReader(port="/dev/ttyUSB0")

# 注册回调
reader.register_callback(lambda frame: print(frame.get_summary()))

# 启动
reader.start()

# 获取最新数据
frame = reader.get_latest_frame()
```

## 信号与槽（PyQt6）

```python
from workers.aoa_worker import AOAWorker

worker = AOAWorker()

# 连接信号
worker.frame_received.connect(handle_frame)
worker.statistics_updated.connect(update_stats)
worker.error.connect(handle_error)

worker.start()
```

## 性能优化

### 减少 UI 更新

```python
# 每 10 帧更新一次 UI
if self.frame_count % 10 == 0:
    self.update_display()
```

### 限制历史记录

```python
# 只保留最近 100 帧
MAX_HISTORY = 100
if len(self.frames) > MAX_HISTORY:
    self.frames.pop(0)
```

### 使用线程

所有 I/O 操作都在后台线程进行，避免阻塞 UI。

## 常见配置

### 修改默认串口

编辑 `ui/main_window.py`：

```python
self.aoa_worker = AOAWorker(
    port="/dev/ttyUSB1",  # 改为其他串口
    baudrate=115200       # 改为其他波特率
)
```

### 修改 ANCHER 位置

编辑 `workers/aoa_worker.py`：

```python
# AOADataProcessor.__init__()
self.anchors[1] = {'x': 0.0, 'y': 0.0}
self.anchors[2] = {'x': 10.0, 'y': 0.0}
```

## 数据转换示例

```python
# mm 转 m
distance_m = frame.tag_data.distance / 1000.0

# 极坐标转笛卡尔坐标
import math
angle_rad = math.radians(frame.tag_data.angle)
x = distance_m * math.cos(angle_rad)
y = distance_m * math.sin(angle_rad)
```

## 调试技巧

### 启用详细日志

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### 打印原始数据

```python
# 在 aoa_protocol.py 中添加
print(f"Raw: {' '.join(f'{b:02X}' for b in data)}")
```

### 监视队列状态

```python
# 在 AOASerialReader 中
stats = reader.get_statistics()
print(f"Queue size: {stats['queue_size']}")
print(f"Error count: {stats['errors']}")
```

## 更多信息

- 详见 `AOA_INTEGRATION_GUIDE.md`
- 查看源代码注释
- 运行 `python test_aoa.py` 了解更多例子

## 反馈与支持

如有问题，请检查：
1. 硬件连接
2. 驱动程序和权限
3. 日志输出
4. 协议文档
