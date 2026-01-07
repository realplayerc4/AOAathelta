"""
API 工作线程 - 在后台执行 API 调用，避免阻塞 UI
"""
from PyQt6.QtCore import QThread, pyqtSignal
from core.api_client import APIClient
from typing import Dict, Any


class APIWorker(QThread):
    """后台线程用于执行 API 调用"""
    
    # 信号定义
    finished = pyqtSignal(dict)  # 成功时发送数据
    error = pyqtSignal(str)      # 失败时发送错误消息
    
    def __init__(self):
        super().__init__()
        self.api_client = APIClient()
    
    def run(self):
        """
        在后台线程中执行 API 调用
        此方法会在调用 start() 时自动执行
        """
        try:
            # 调用 API 获取设备信息
            data = self.api_client.fetch_device_info()
            
            # 发送成功信号
            self.finished.emit(data)
            
        except Exception as e:
            # 发送错误信号
            self.error.emit(str(e))
