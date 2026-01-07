"""
配置文件 - API 端点和设备信息
"""

# API 配置
API_BASE_URL = "http://192.168.25.25:8090"
API_DEVICE_INFO = f"{API_BASE_URL}/device/info"
API_TIMEOUT = 10  # 秒
API_SECRET = "XXXXXXXXXXXXXXXXX"  # 请替换为实际的 Secret 密钥

# 设备配置
DEVICE_SN = "1382310402363C7"  # AMR 设备序列号

# UI 配置
WINDOW_TITLE = "AMR 设备监控系统"
WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 700
