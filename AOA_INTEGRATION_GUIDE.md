# AOA (角度到达) 功能集成说明

## 概述

本文档说明如何在 AUTOXINGAOA 项目中集成 `/home/han14/gitw/protocol_extracter` 库的 AOA (Angle of Arrival) 功能。

## 功能说明

### AOA 是什么？

AOA（角度到达，Angle of Arrival）是一种位置定位技术，通过测量射频信号从多个接收点（ANCHER/基站）到传输源（TAG/标签）的角度和距离，来确定源的相对或绝对位置。

### 系统架构

```
序列口数据 → AOA 串口读取线程 → 协议解析 → AOA 数据模型 → UI 显示
                                                    ↓
                                              位置计算线程
```

## 集成的新文件

### 1. 数据模型 (`models/aoa_data.py`)

定义了 AOA 相关的数据结构：

- **AnchorData**: ANCHER（基站）数据
  - `role`: 角色代码
  - `anchor_id`: 基站 ID
  - `local_time`: 地方时间戳
  - `system_time`: 系统时间戳
  - `voltage`: 电压（mV）

- **TagData**: TAG（标签）数据
  - `tag_id`: 标签 ID
  - `distance`: 距离（mm）
  - `angle`: 角度（度数）
  - `fp_db`: 第一路径信号强度（dB）
  - `rx_db`: 接收信号强度（dB）

- **AOAFrame**: 完整的 AOA 协议帧（0x55 协议，33 字节）
  - 包含 ANCHER 和 TAG 数据
  - 校验和验证
  - 从字节数据自动解析

- **AOAPosition**: 标签相对于基站的位置
  - 距离和角度信息
  - 时间戳和信心度

### 2. 协议解析 (`core/aoa_protocol.py`)

实现了 AOA 协议的解析功能：

- **AOAProtocolParser**: 单帧解析器
  - 解析 33 字节的 0x55 协议
  - 支持数据流中多帧解析
  - 回调机制处理解析结果
  - 统计信息收集

- **SerialProtocolExtractor**: 串口协议提取器
  - 支持纯 Python 实现
  - 支持 C++ 库绑定（可选）
  - 自动数据流处理

### 3. 串口读取线程 (`workers/aoa_serial_reader.py`)

**AOASerialReader**: 后台串口读取线程
- 连续从串口读取数据
- 自动解析 AOA 协议
- 队列和回调输出数据
- 统计帧接收和错误信息

### 4. 工作线程 (`workers/aoa_worker.py`)

- **AOAWorker**: PyQt6 集成的工作线程
  - 启动串口读取
  - 信号机制与 UI 通信
  - 接收统计信息更新

- **AOADataProcessor**: 位置计算线程
  - 多个 ANCHER 数据融合
  - 三角定位计算

### 5. UI 小部件 (`ui/widgets/aoa_viewer.py`)

- **AOADataWidget**: 实时数据显示面板
  - 串口连接控制
  - 实时数据表格
  - 统计信息显示

- **AOAPositionViewer**: 位置可视化对话框
  - 显示标签与基站的相对位置
  - 支持图表可视化

### 6. 主窗口集成 (`ui/main_window.py`)

在主窗口添加了：
- 新的 AOA 数据标签页
- AOA 工作线程启动和管理
- 信号处理和 UI 更新

## 协议格式

### 0x55 协议（33 字节）

| 字节 | 含义 | 描述 |
|------|------|------|
| 0 | 头部 | 0x55 |
| 1 | 功能码 | 协议类型 |
| 2-3 | 数据长度 | 数据段长度 |
| 4 | ANCHER role | 基站角色代码 |
| 5 | ANCHER id | 基站 ID |
| 6-9 | 地方时间 | uint32, 小端序 |
| 10-13 | 系统时间 | uint32, 小端序 |
| 14-17 | 保留 | 保留字节 |
| 18-19 | 电压 | uint16, 小端序, 单位 mV |
| 20 | 节点数 | 基站节点数 |
| 21 | TAG role | 标签角色代码 |
| 22 | TAG id | 标签 ID |
| 23-25 | 距离 | int24, 小端序, 单位 mm |
| 26-27 | 角度 | int16, 小端序, 实际值×100 |
| 28 | fp_db | 第一路径信号强度 |
| 29 | rx_db | 接收信号强度 |
| 30-31 | 保留 | 保留字节 |
| 32 | 校验和 | 前 32 字节的和 |

## 使用示例

### 基本使用

```python
from models.aoa_data import AOAFrame
from core.aoa_protocol import AOAProtocolParser

# 创建解析器
parser = AOAProtocolParser()

# 注册回调函数
def handle_frame(frame):
    print(f"距离: {frame.tag_data.distance}mm")
    print(f"角度: {frame.tag_data.angle}°")

parser.register_callback(handle_frame)

# 解析数据
frame = parser.parse_frame(raw_bytes)  # raw_bytes 是 33 字节的数据
```

### 后台线程使用

```python
from workers.aoa_serial_reader import AOASerialReader

# 创建读取线程
reader = AOASerialReader(port="/dev/ttyUSB0", baudrate=115200)

# 注册处理函数
def on_frame(frame):
    print(f"TAG #{frame.tag_data.tag_id} at {frame.tag_data.distance}mm, "
          f"{frame.tag_data.angle}°")

reader.register_callback(on_frame)

# 启动线程
reader.start()

# 获取最新帧
frame = reader.get_latest_frame(timeout=1.0)

# 获取统计信息
stats = reader.get_statistics()

# 停止线程
reader.stop()
```

### PyQt6 集成

```python
from workers.aoa_worker import AOAWorker

# 创建工作线程
worker = AOAWorker(port="/dev/ttyUSB0")

# 连接信号
worker.frame_received.connect(on_frame_received)
worker.statistics_updated.connect(on_stats_updated)

# 启动
worker.start()

# 停止
worker.stop()
```

## 配置

### 串口设置

在主窗口中，可以通过 AOA 小部件配置：
- **串口**: `/dev/ttyUSB0`, `/dev/ttyUSB1` 等
- **波特率**: 9600 - 921600（默认 115200）

### ANCHER 位置配置

在 `workers/aoa_worker.py` 中的 `AOADataProcessor` 中配置已知的基站位置：

```python
processor = AOADataProcessor()
processor.register_anchor(anchor_id=1, x=0.0, y=0.0)
processor.register_anchor(anchor_id=2, x=10.0, y=0.0)
processor.register_anchor(anchor_id=3, x=5.0, y=8.66)
```

## 测试

### 运行测试脚本

```bash
cd /home/han14/gitw/AUTOXINGAOA
python test_aoa.py
```

测试脚本包括：
1. AOA 数据模型测试
2. AOA 帧解析测试
3. 协议解析器测试
4. 串口协议提取器测试

### 手动测试

1. 启动应用：`python main.py`
2. 点击连接按钮连接到串口
3. 查看实时数据显示
4. 观察统计信息

## 错误排查

### 无法连接到串口

1. 检查设备是否连接：`ls -la /dev/ttyUSB*`
2. 检查权限：`sudo usermod -a -G dialout $USER`
3. 确认波特率匹配：设备和软件配置应相同

### 校验和失败

- 检查数据传输质量
- 增加延迟或降低波特率
- 检查是否有干扰

### 帧解析失败

- 检查协议格式是否正确
- 查看原始十六进制数据
- 确保数据长度为 33 字节

## 与 protocol_extracter 的关系

`protocol_extracter` 库是一个 C++ 协议解析框架，包含：
- 基础协议类 (`NProtocolBase`)
- 协议提取器 (`NProtocolExtracter`)
- 串口辅助工具

当前实现使用纯 Python 解析 AOA 协议，但可以通过 ctypes 绑定使用 C++ 库以获得更高的性能。

## 未来扩展

1. **C++ 库集成**：通过 ctypes 调用 protocol_extracter 库
2. **高级位置计算**：实现卡尔曼滤波器进行位置平滑
3. **多标签追踪**：支持同时追踪多个标签
4. **地图融合**：将 AOA 位置与地图数据融合
5. **历史回放**：记录和回放位置数据

## 文件清单

```
models/
  ├── aoa_data.py              # AOA 数据模型
  └── ...

core/
  ├── aoa_protocol.py          # AOA 协议解析
  └── ...

workers/
  ├── aoa_serial_reader.py     # 串口读取线程
  ├── aoa_worker.py            # PyQt6 工作线程
  └── ...

ui/
  └── widgets/
      ├── aoa_viewer.py        # AOA UI 小部件
      └── ...

test_aoa.py                     # 测试脚本
```

## 参考资源

- `/home/han14/gitw/protocol_extracter/`: 原始 C++ 库
- `/home/han14/gitw/protocol_extracter/serial_example.cpp`: 协议实现参考
- AOA 协议文档（在 protocol_extracter/SERIAL_USAGE.md）

## 许可证

与主项目相同
