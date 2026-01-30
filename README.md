# AOA 信标定位系统

实时信标定位和地图可视化系统，集成卡尔曼滤波和坐标转换，支持树莓派部署。

## 系统架构

```
┌─────────────────────────────────────────┐
│         地图 SLAM 系统                    │
│   (192.168.11.1:1448 - AMR 地盘)        │
└──────────────┬──────────────────────────┘
               │ 获取位姿态
               ▼
        ┌──────────────┐
        │  Web 应用     │  Port 5000
        │  (5000)      │ - 实时定位可视化
        └──────────────┘ - 地图显示
               ▲          - 坐标转换
               │ 获取滤波数据
        ┌──────────────┐
        │ Beacon 服务  │  Port 5001
        │  (5001)      │ - 串口读取
        └──────────────┘ - 卡尔曼滤波
               ▲
               │ 原始数据
        ┌──────────────┐
        │   串口设备    │
        │  (Beacon)    │
        └──────────────┘
```

## 项目结构

```
AOAathelta/
├── beacon_filter_service.py    # Beacon 卡尔曼滤波服务 (5001)
├── web_app.py                  # Web 可视化应用 (5000)
├── start_services.py           # 启动两个服务的脚本
├── config.py                   # 项目配置文件
├── requirements.txt            # Python 依赖
├── core/
│   ├── api_client.py          # AMR API 客户端
│   └── __init__.py
├── workers/
│   ├── aoa_serial_reader.py    # 串口读取模块
│   ├── aoa_kalman_filter.py    # 卡尔曼滤波模块
│   └── __init__.py
├── static/
│   ├── css/
│   │   └── style.css           # 样式文件
│   └── js/
│       └── map.js              # 地图交互脚本
├── templates/
│   └── index.html              # Web 界面
└── maps/                        # 地图数据目录
```

## 快速开始

### 本地运行

```bash
# 1. 安装依赖
pip3 install -r requirements.txt

# 2. 启动服务
python3 start_services.py

# 3. 打开浏览器
# Web UI: http://127.0.0.1:5000
# API: http://127.0.0.1:5001/api/beacon
```

### 部署到树莓派

**推荐方式：一键部署**

```bash
python3 deploy_to_raspi.py
```

或手动部署：

```bash
# 1. 上传项目
scp -r . han16@192.168.0.144:/home/han16/AOAathelta

# 2. SSH 连接
ssh han16@192.168.0.144

# 3. 安装依赖
cd /home/han16/AOAathelta
pip3 install -r requirements.txt

# 4. 启动服务
python3 start_services.py
```

更详细的部署指南见 [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)

## 服务说明

### Beacon Filter Service (5001)

卡尔曼滤波处理服务，处理从串口接收的信标数据。

**主要功能：**
- 串口数据采集 (921600 baud)
- 实时卡尔曼滤波
- 极坐标到笛卡尔坐标转换
- 速度估计

**API 端点：**

| 路由 | 方法 | 说明 |
|------|------|------|
| `/api/beacon` | GET | 获取最新滤波后的 Beacon 数据 |
| `/api/stats` | GET | 获取处理统计信息 |
| `/api/status` | GET | 获取服务状态 |
| `/` | GET | 服务信息 |

**示例响应 `/api/beacon`：**
```json
{
  "x": -2.85,
  "y": -1.23,
  "distance": 3.12,
  "angle": 112.5,
  "confidence": 0.72,
  "velocity_x": 0.02,
  "velocity_y": -0.01,
  "initialized": true,
  "timestamp": 1672531200.123,
  "peer": "AAA1"
}
```

### Web App (5000)

实时定位和可视化界面。

**主要功能：**
- 实时定位显示
- 坐标系转换
- EMA 位置平滑
- 地图加载和显示
- 区域检测

**API 端点：**

| 路由 | 方法 | 说明 |
|------|------|------|
| `/` | GET | 主页面 |
| `/api/position` | GET | 获取当前 Beacon 相对位置 |
| `/api/robot-pose` | GET | 获取机器人位姿态和全局位置 |
| `/api/map-info` | GET | 获取地图元数据 |
| `/api/map-data` | GET | 获取地图栅格数据 (Base64 PNG) |
| `/api/zones` | GET/POST | 管理检测区域 |
| `/api/status` | GET | 获取系统状态 |
| `/api/start` | POST | 启动系统 |
| `/api/stop` | POST | 停止系统 |

## 关键模块

### Core 模块

**api_client.py** - AMR 设备 API 客户端
- 获取机器人位姿态
- 获取地图数据
- 错误重试机制

### Workers 模块

**aoa_serial_reader.py** - 串口读取模块
- 自动连接 /dev/ttyUSB0/1
- 队列式数据缓存
- 错误处理

**aoa_kalman_filter.py** - 卡尔曼滤波模块
- 多目标追踪
- 极坐标滤波
- 速度估计
- 可信度评分

## 配置参数

[config.py](config.py) 中的主要参数：

```python
# AMR API 地址
API_BASE_URL = "http://192.168.11.1:1448"
API_TIMEOUT = 5
API_SECRET = "123456"

# 串口配置
SERIAL_BAUDRATE = 921600
SERIAL_TIMEOUT = 0.1

# 卡尔曼滤波参数
KALMAN_PROCESS_NOISE = 0.1        # 过程噪声
KALMAN_MEASUREMENT_NOISE = 0.5    # 测量噪声
KALMAN_MIN_CONFIDENCE = 0.3       # 最小置信度阈值

# 位姿态查询频率
POSE_QUERY_INTERVAL = 0.1  # 10Hz
```

## 数据流

```
串口数据
  ↓
[Beacon Service]
  • 解析数据
  • 提取距离和角度
  • 卡尔曼滤波
  ↓
API (5001) - /api/beacon
  ↓
[Web App]
  • 获取滤波数据
  • 获取机器人位姿态
  • 坐标变换 (Anchor → Global)
  • EMA 平滑
  ↓
API (5000) - /api/robot-pose
  ↓
[浏览器]
  • 实时可视化
  • 交互控制
```

## 坐标系统

### 本地坐标系（Anchor 相对）
- X 轴：右手方向（横向）
- Y 轴：前方向（纵向）
- 原点：Anchor 中心

### 全局坐标系（地图坐标）
- X 轴：向右
- Y 轴：向上
- 原点：地图左下角
- 使用 2D 旋转矩阵进行变换

## 常用命令

### 启动/停止

```bash
# 启动服务
python3 start_services.py

# 后台启动
nohup python3 start_services.py > services.log 2>&1 &

# 停止服务
pkill -f start_services.py
```

### 查看日志

```bash
# 实时查看
tail -f services.log

# 查看特定行数
tail -n 50 services.log

# 搜索错误
grep ERROR services.log
```

### 调试

```bash
# 测试 Web App
curl http://127.0.0.1:5000/

# 测试 Beacon 服务
curl http://127.0.0.1:5001/api/beacon

# 测试 Robot 位姿态
curl http://127.0.0.1:5000/api/robot-pose

# 查看统计信息
curl http://127.0.0.1:5001/api/stats
```

## 故障排除

### 无法连接到 AMR

```bash
# 检查网络连接
ping 192.168.11.1

# 测试 API
curl http://192.168.11.1:1448/api/core/slam/v1/localization/pose
```

### 串口连接失败

```bash
# 查看可用串口
ls -la /dev/ttyUSB*

# 检查权限
sudo usermod -a -G dialout $USER

# 需要重新登录生效
```

### 端口已占用

```bash
# 查看占用进程
lsof -i :5000
lsof -i :5001

# 停止进程
pkill -f start_services.py
```

## 性能指标

- **更新频率**：10Hz (0.1s)
- **Beacon 滤波**：30Hz
- **位置响应时间**：< 200ms
- **Web 页面加载**：< 1s

## 依赖项

- Python 3.7+
- Flask 2.0+
- NumPy 1.19+
- Requests 2.25+
- PySerial 3.5+

完整依赖见 [requirements.txt](requirements.txt)

## 许可证

MIT

## 联系方式

如有问题，请提交 Issue 或联系开发团队。

