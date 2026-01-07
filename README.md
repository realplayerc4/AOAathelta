# AMR 设备监控系统

基于 PyQt6 的桌面应用，用于监控和管理 AMR（自主移动机器人）设备。

## 功能特性

- 🔌 **一键获取**：点击按钮即可从 API 获取设备数据
- 📊 **表格展示**：清晰展示设备信息（ID、状态、电池、位置等）
- 📄 **JSON 视图**：查看原始 API 响应数据
- 🎨 **状态标识**：通过颜色区分设备状态（在线/离线）和电池电量
- ⚡ **异步请求**：后台线程处理 API 调用，界面不卡顿
- 🛡️ **错误处理**：完善的异常处理和用户提示

## 项目结构

```
AUTOXINGAOA/
├── main.py                      # 应用入口
├── config.py                    # 配置文件（API地址、密钥等）
├── requirements.txt             # 依赖项
├── README.md                    # 本文件
│
├── ui/                          # UI 界面层
│   ├── main_window.py          # 主窗口
│   └── widgets/
│       └── device_table.py     # 设备表格组件
│
├── core/                        # 业务逻辑层
│   └── api_client.py           # API 客户端
│
├── models/                      # 数据模型层
│   └── device.py               # 设备数据模型
│
└── workers/                     # 后台工作线程
    └── api_worker.py           # API 工作线程
```

## 安装步骤

### 1. 克隆项目

```bash
cd /home/han14/gitw/AUTOXINGAOA
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

或手动安装：

```bash
pip install PyQt6 requests
```

### 3. 配置

编辑 `config.py` 文件，设置以下参数：

```python
# API 配置
API_BASE_URL = "http://192.168.25.25:8090"
API_SECRET = "YOUR_ACTUAL_SECRET_KEY"  # 替换为实际的 Secret 密钥

# 设备配置
DEVICE_SN = "1382310402363C7"  # AMR 设备序列号
```

## 使用方法

### 启动应用

```bash
python main.py
```

### 操作步骤

1. **启动程序**：运行 `main.py`
2. **获取数据**：点击 "📡 获取设备数据" 按钮
3. **查看数据**：
   - 在 "📊 表格视图" 标签页查看格式化的设备信息
   - 在 "📄 原始 JSON" 标签页查看完整的 API 响应
4. **清空数据**：点击 "🗑️ 清空数据" 按钮清除显示

## API 接口说明

### 请求格式

```
GET http://192.168.25.25:8090/device/info?sn=1382310402363C7
Headers:
  Secret: XXXXXXXXXXXXXXXXX
  Content-Type: application/json
```

### 响应格式（示例）

系统支持多种 JSON 响应格式：

**格式 1：单个设备对象**
```json
{
  "id": "device001",
  "name": "AMR-01",
  "status": "online",
  "sn": "1382310402363C7",
  "battery": 85.5,
  "location": "仓库A"
}
```

**格式 2：设备数组**
```json
[
  {
    "id": "device001",
    "name": "AMR-01",
    "status": "online"
  }
]
```

**格式 3：包装格式**
```json
{
  "data": {
    "id": "device001",
    "name": "AMR-01"
  }
}
```

## 技术栈

- **PyQt6** - GUI 框架
- **requests** - HTTP 请求库
- **Python 3.8+** - 编程语言

## 故障排查

### 问题：无法连接到 API

**解决方案**：
1. 检查网络连接是否正常
2. 确认 API 地址 `http://192.168.25.25:8090` 可访问
3. 尝试 ping 192.168.25.25

### 问题：认证失败

**解决方案**：
1. 检查 `config.py` 中的 `API_SECRET` 是否正确
2. 确认 Secret 密钥格式是否正确（无多余空格）

### 问题：数据解析失败

**解决方案**：
1. 在 "原始 JSON" 标签页查看实际返回的数据格式
2. 修改 `ui/main_window.py` 中的 `_parse_devices()` 方法以适配实际格式

### 问题：依赖安装失败

**解决方案**：
```bash
# 升级 pip
pip install --upgrade pip

# 重新安装依赖
pip install --force-reinstall PyQt6 requests
```

## 扩展功能

### 添加定时自动刷新

在 `ui/main_window.py` 的 `__init__` 方法中添加：

```python
from PyQt6.QtCore import QTimer

# 创建定时器（每30秒刷新一次）
self.timer = QTimer()
self.timer.timeout.connect(self._on_fetch_clicked)
self.timer.start(30000)  # 30秒
```

### 导出数据为 CSV

添加导出按钮和功能：

```python
import csv

def export_to_csv(self):
    with open('devices.csv', 'w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        # 写入表头和数据
```

## 开发者信息

- **版本**：1.0.0
- **开发时间**：2026-01-07
- **Python 版本**：3.8+

## 许可证

本项目仅供内部使用。

## 联系方式

如有问题或建议，请联系开发团队。
