"""
配置文件 - API 端点和设备信息
"""

# API 配置
API_BASE_URL = "http://192.168.25.25:8090"
API_DEVICE_INFO = f"{API_BASE_URL}/device/info"
API_TIMEOUT = 10  # 秒
API_SECRET = "XXXXXXXXXXXXXXXXX"  # 请替换为实际的 Secret 密钥
API_WS_URL = "ws://192.168.25.25:8090/ws/v2/topics"

# 设备配置
DEVICE_SN = "1382310402363C7"  # AMR 设备序列号

# 话题配置
TOPICS_FILE = "topics.txt"  # 监听的话题列表文件，每行一个话题

# UI 配置
WINDOW_TITLE = "AMR 设备监控系统"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 700

# Beacon 数据过滤配置
BEACON_MIN_CONFIDENCE = 0.65  # 最小置信度阈值（0.0-1.0），低于此值的数据将被过滤
