"""
AOA 串口数据接收工作线程
负责持续从串口接收数据并解析 AOA 协议
"""
import logging
import threading
import time
import queue
from typing import Optional, Callable, List
from serial import Serial, SerialException
from core.aoa_protocol import AOAProtocolParser, SerialProtocolExtractor
from models.aoa_data import AOAFrame


logger = logging.getLogger(__name__)


class AOASerialReader(threading.Thread):
    """
    AOA 串口读取线程
    """
    
    def __init__(self, 
                 port: str,
                 baudrate: int = 115200,
                 timeout: float = 1.0,
                 buffer_size: int = 8192):
        """
        初始化读取线程
        
        Args:
            port: 串口名称 (e.g., 'COM3' or '/dev/ttyUSB0')
            baudrate: 波特率，默认 115200
            timeout: 读取超时时间（秒）
            buffer_size: 接收缓冲区大小
        """
        super().__init__(daemon=True)
        
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.buffer_size = buffer_size
        
        self.serial: Optional[Serial] = None
        self.running = False
        self.parser = AOAProtocolParser()
        self.extractor = SerialProtocolExtractor(use_cpp_library=False)
        
        # 数据队列
        self.frame_queue: queue.Queue[AOAFrame] = queue.Queue(maxsize=100)
        self.raw_data_queue: queue.Queue[bytes] = queue.Queue(maxsize=10)
        
        # 统计信息
        self.bytes_received = 0
        self.frames_received = 0
        self.errors = 0
        
        # 回调列表
        self.callbacks: List[Callable[[AOAFrame], None]] = []
        self.lock = threading.Lock()
    
    def connect(self) -> bool:
        """
        连接串口
        
        Returns:
            连接成功返回 True，否则 False
        """
        try:
            if self.serial and self.serial.is_open:
                return True
            
            self.serial = Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout
            )
            
            if self.serial.is_open:
                logger.info(f"成功连接串口: {self.port} @ {self.baudrate} baud")
                return True
            else:
                logger.error(f"无法打开串口: {self.port}")
                return False
                
        except SerialException as e:
            logger.error(f"串口连接失败: {e}")
            self.serial = None
            return False
    
    def disconnect(self):
        """断开串口连接"""
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
                logger.info(f"已断开串口: {self.port}")
            except Exception as e:
                logger.error(f"关闭串口失败: {e}")
            self.serial = None
    
    def register_callback(self, callback: Callable[[AOAFrame], None]):
        """注册帧处理回调"""
        with self.lock:
            if callback not in self.callbacks:
                self.callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[AOAFrame], None]):
        """取消注册回调"""
        with self.lock:
            if callback in self.callbacks:
                self.callbacks.remove(callback)
    
    def run(self):
        """线程主循环"""
        self.running = True
        
        if not self.connect():
            logger.error("初始化失败，无法连接串口")
            self.running = False
            return
        
        buffer = bytearray()
        
        try:
            while self.running:
                try:
                    # 从串口读取数据
                    if self.serial and self.serial.in_waiting > 0:
                        data = self.serial.read(self.serial.in_waiting)
                        buffer.extend(data)
                        
                        with self.lock:
                            self.bytes_received += len(data)
                        
                        # 当缓冲区足够大时处理数据
                        if len(buffer) >= 33:  # 最小协议长度
                            # 使用提取器解析数据
                            frames = self.extractor.extract_data(bytes(buffer))
                            
                            # 处理解析得到的帧
                            for frame in frames:
                                try:
                                    # 加入队列
                                    if not self.frame_queue.full():
                                        self.frame_queue.put_nowait(frame)
                                    
                                    with self.lock:
                                        self.frames_received += 1
                                    
                                    # 调用回调函数
                                    with self.lock:
                                        callbacks = self.callbacks.copy()
                                    
                                    for callback in callbacks:
                                        try:
                                            callback(frame)
                                        except Exception as e:
                                            logger.error(f"回调函数执行失败: {e}")
                                
                                except queue.Full:
                                    logger.warning("帧队列已满，丢弃旧帧")
                            
                            # 清空缓冲区（保留可能的不完整帧）
                            # 找到最后一个完整帧的位置
                            last_frame_pos = 0
                            for i in range(len(buffer) - 32, -1, -1):
                                if buffer[i] == 0x55:  # HEADER
                                    if i + 33 <= len(buffer):
                                        last_frame_pos = i + 33
                                    break
                            
                            if last_frame_pos > 0:
                                buffer = buffer[last_frame_pos:]
                            else:
                                # 清空整个缓冲区，等待新数据
                                buffer.clear()
                    
                    else:
                        # 没有可读数据时短暂延迟，避免 CPU 占用过高
                        time.sleep(0.01)
                
                except SerialException as e:
                    logger.error(f"读取串口出错: {e}")
                    with self.lock:
                        self.errors += 1
                    
                    # 尝试重新连接
                    self.disconnect()
                    time.sleep(1.0)
                    if not self.connect():
                        self.running = False
                
                except Exception as e:
                    logger.error(f"处理数据时出错: {e}")
                    with self.lock:
                        self.errors += 1
                    time.sleep(0.1)
        
        finally:
            self.disconnect()
            self.running = False
            logger.info("AOA 串口读取线程已停止")
    
    def stop(self):
        """停止读取线程"""
        self.running = False
    
    def get_latest_frame(self, timeout: float = 1.0) -> Optional[AOAFrame]:
        """
        获取最新的 AOA 帧
        
        Args:
            timeout: 等待超时时间（秒）
            
        Returns:
            最新的 AOAFrame 或 None
        """
        try:
            return self.frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        with self.lock:
            return {
                'port': self.port,
                'baudrate': self.baudrate,
                'is_running': self.running,
                'bytes_received': self.bytes_received,
                'frames_received': self.frames_received,
                'errors': self.errors,
                'queue_size': self.frame_queue.qsize(),
                'parser_stats': self.parser.get_statistics()
            }
