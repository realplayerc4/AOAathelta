"""
AOA 协议解析模块 - 解析 protocol_extracter 库的数据
"""
import struct
import logging
from typing import Optional, Callable, List
from threading import Lock
from models.aoa_data import AOAFrame, AnchorData, TagData


logger = logging.getLogger(__name__)


class AOAProtocolParser:
    """
    AOA 协议解析器
    负责解析来自串口的原始字节数据，提取 ANCHER 和 TAG 信息
    """
    
    # 协议常量
    HEADER = 0x55
    PROTOCOL_LENGTH = 33
    HEADER_SIZE = 2  # 头部和功能码
    ANCHER_DATA_SIZE = 20  # 字节 2-21
    TAG_DATA_SIZE = 10  # 字节 22-31
    CHECKSUM_BYTE = 32
    
    def __init__(self):
        """初始化解析器"""
        self.frame_count = 0
        self.error_count = 0
        self.callbacks: List[Callable[[AOAFrame], None]] = []
        self.lock = Lock()
        
    def register_callback(self, callback: Callable[[AOAFrame], None]):
        """
        注册数据回调函数
        
        Args:
            callback: 处理 AOAFrame 的函数
        """
        self.callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[AOAFrame], None]):
        """取消注册回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def parse_frame(self, data: bytes) -> Optional[AOAFrame]:
        """
        解析单个完整的 AOA 帧
        
        Args:
            data: 33 字节的完整协议数据
            
        Returns:
            解析成功返回 AOAFrame，失败返回 None
        """
        try:
            if len(data) != self.PROTOCOL_LENGTH:
                logger.warning(f"数据长度错误: 期望 {self.PROTOCOL_LENGTH} 字节, 实际 {len(data)} 字节")
                return None
            
            if data[0] != self.HEADER:
                logger.warning(f"头部错误: 期望 0x{self.HEADER:02X}, 实际 0x{data[0]:02X}")
                return None
            
            with self.lock:
                self.frame_count += 1
                
            # 创建 AOA 帧
            frame = AOAFrame.from_bytes(data, frame_id=self.frame_count)
            
            if not frame.is_valid:
                # 高频数据下偶尔校验失败属正常，降级为调试日志以减少噪音
                logger.debug(f"帧 #{self.frame_count} 校验和验证失败")
                with self.lock:
                    self.error_count += 1
                return None
            
            # 调用所有回调函数
            for callback in self.callbacks:
                try:
                    callback(frame)
                except Exception as e:
                    logger.error(f"回调函数执行失败: {e}")
            
            return frame
            
        except Exception as e:
            logger.error(f"解析帧失败: {e}")
            with self.lock:
                self.error_count += 1
            return None
    
    def parse_stream(self, data: bytes) -> List[AOAFrame]:
        """
        从字节流中解析多个完整的 AOA 帧
        
        Args:
            data: 连续的字节数据流
            
        Returns:
            解析成功的 AOAFrame 列表
        """
        frames = []
        i = 0
        
        while i <= len(data) - self.PROTOCOL_LENGTH:
            # 查找下一个协议头
            if data[i] == self.HEADER:
                try:
                    frame_data = bytes(data[i:i + self.PROTOCOL_LENGTH])
                    frame = self.parse_frame(frame_data)
                    if frame:
                        frames.append(frame)
                    i += self.PROTOCOL_LENGTH
                except Exception as e:
                    logger.error(f"处理帧数据失败: {e}")
                    i += 1
            else:
                i += 1
        
        return frames
    
    def get_statistics(self) -> dict:
        """获取解析统计信息"""
        with self.lock:
            return {
                'total_frames': self.frame_count,
                'error_count': self.error_count,
                'success_count': self.frame_count - self.error_count,
                'error_rate': (self.error_count / self.frame_count * 100 
                             if self.frame_count > 0 else 0)
            }


class SerialProtocolExtractor:
    """
    使用 protocol_extracter 库的协议提取器
    可以选择使用 C++ 库进行高性能解析
    """
    
    def __init__(self, use_cpp_library: bool = False):
        """
        初始化提取器
        
        Args:
            use_cpp_library: 是否使用 C++ 库（需要编译和 ctypes 绑定）
        """
        self.use_cpp_library = use_cpp_library
        self.cpp_lib = None
        
        if use_cpp_library:
            self._load_cpp_library()
    
    def _load_cpp_library(self):
        """加载 C++ 库（可选）"""
        try:
            import ctypes
            import os
            
            # protocol_extracter 库的路径
            lib_path = "/home/han14/gitw/protocol_extracter/build"
            lib_file = None
            
            # 尝试找到编译好的库文件
            if os.path.exists(lib_path):
                for root, dirs, files in os.walk(lib_path):
                    for file in files:
                        if file.endswith('.so') or file.endswith('.a'):
                            lib_file = os.path.join(root, file)
                            break
            
            if lib_file:
                try:
                    self.cpp_lib = ctypes.CDLL(lib_file)
                    logger.info(f"成功加载 C++ 库: {lib_file}")
                except Exception as e:
                    logger.warning(f"无法加载 C++ 库: {e}，将使用纯 Python 实现")
                    self.cpp_lib = None
            else:
                logger.warning("未找到编译好的 protocol_extracter 库")
                
        except ImportError:
            logger.warning("ctypes 模块不可用，将使用纯 Python 实现")
    
    def extract_data(self, data: bytes) -> List[AOAFrame]:
        """
        提取数据
        
        Args:
            data: 原始字节数据
            
        Returns:
            AOAFrame 列表
        """
        if self.cpp_lib and self.use_cpp_library:
            return self._extract_with_cpp(data)
        else:
            return self._extract_with_python(data)
    
    def _extract_with_python(self, data: bytes) -> List[AOAFrame]:
        """使用纯 Python 提取"""
        parser = AOAProtocolParser()
        return parser.parse_stream(data)
    
    def _extract_with_cpp(self, data: bytes) -> List[AOAFrame]:
        """使用 C++ 库提取（需要实现 ctypes 绑定）"""
        logger.info("使用 C++ 库进行协议解析")
        # 这里需要实现具体的 ctypes 调用逻辑
        # 由于 protocol_extracter 是 C++ 代码，需要创建适当的绑定
        # 目前返回使用 Python 实现的结果
        return self._extract_with_python(data)
