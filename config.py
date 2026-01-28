"""
配置文件 - AMR 设备 API 连接参数
"""

# API 服务器地址
API_BASE_URL = "http://192.168.11.1:1448"

# API 端点
API_DEVICE_INFO = f"{API_BASE_URL}/api/core/amr/v1/device/info"
API_MAPS_LIST = f"{API_BASE_URL}/mappings/"
API_POSE = f"{API_BASE_URL}/api/core/slam/v1/localization/pose"

# API 请求超时时间（秒）
API_TIMEOUT = 5

# API 认证密钥（Secret）
API_SECRET = "123456"

# 设备序列号（可选）
DEVICE_SN = None

# 串口配置
SERIAL_BAUDRATE = 921600
SERIAL_TIMEOUT = 0.1

# 卡尔曼滤波器配置
KALMAN_PROCESS_NOISE = 0.1
KALMAN_MEASUREMENT_NOISE = 0.5
KALMAN_MIN_CONFIDENCE = 0.3

# 位姿态查询间隔（秒）
POSE_QUERY_INTERVAL = 0.05  # 20Hz
