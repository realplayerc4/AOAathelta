"""
AOA 工作线程 - 在后台处理 AOA 数据接收和解析
"""
from PyQt6.QtCore import QThread, pyqtSignal
import logging
import time
from typing import Optional
from workers.aoa_serial_reader import AOASerialReader
from models.aoa_data import AOAFrame, AOAPosition
from utils.kalman_filter import MultiTargetKalmanFilter


logger = logging.getLogger(__name__)


class AOAWorker(QThread):
    """后台线程用于处理 AOA 数据接收"""
    
    # 信号定义
    frame_received = pyqtSignal(dict)  # 接收到新的 AOA 帧
    position_updated = pyqtSignal(dict)  # 位置更新
    statistics_updated = pyqtSignal(dict)  # 统计信息更新
    error = pyqtSignal(str)  # 错误信息
    status_changed = pyqtSignal(str)  # 状态变化
    
    def __init__(self, port: str = '/dev/ttyCH343USB0', baudrate: int = 921600):
        """
        初始化 AOA 工作线程
        
        Args:
            port: 串口名称
            baudrate: 波特率
        """
        super().__init__()
        
        self.port = port
        self.baudrate = baudrate
        self.reader: Optional[AOASerialReader] = None
        self.is_running = False
        self.frame_count = 0
        
        # 初始化卡尔曼滤波器 (启用多目标跟踪)
        self.kalman_filter = MultiTargetKalmanFilter(
            process_noise=0.1,
            measurement_noise=0.5,
            prediction_horizon=0.5,
            min_confidence=0.3,
            target_lost_timeout=2.0
        )
        
        self.filter_enabled = True  # 是否启用卡尔曼滤波
    
    def run(self):
        """线程主循环"""
        try:
            # 创建串口读取器
            self.reader = AOASerialReader(
                port=self.port,
                baudrate=self.baudrate
            )
            
            # 注册帧接收回调
            self.reader.register_callback(self._on_frame_received)
            
            # 启动读取线程
            self.reader.start()
            self.is_running = True
            
            self.status_changed.emit(f"已连接到 {self.port} @ {self.baudrate} baud")
            
            # 定期更新统计信息
            last_stats_time = time.time()
            last_cleanup_time = time.time()
            
            while self.is_running:
                time.sleep(0.1)
                
                # 每秒更新一次统计信息
                current_time = time.time()
                if current_time - last_stats_time >= 1.0:
                    stats = self.reader.get_statistics()
                    self.statistics_updated.emit(stats)
                    last_stats_time = current_time
                
                # 每 2 秒清理一次丢失的目标
                if current_time - last_cleanup_time >= 2.0:
                    self.kalman_filter.remove_lost_targets(current_time)
                    last_cleanup_time = current_time
        
        except Exception as e:
            error_msg = f"AOA 工作线程错误: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)
            self.status_changed.emit("错误")
    
    def _on_frame_received(self, frame: AOAFrame):
        """处理接收到的帧"""
        self.frame_count += 1
        
        if frame.is_valid and frame.tag_data and frame.anchor_data:
            # 极坐标数据
            distance = frame.tag_data.distance / 1000.0  # 转换为米
            angle = frame.tag_data.angle
            tag_id = frame.tag_data.tag_id
            
            # 应用卡尔曼滤波
            if self.filter_enabled:
                filtered_x, filtered_y, filter_info = self.kalman_filter.filter_measurement(
                    tag_id=tag_id,
                    distance=distance,
                    angle_deg=angle,
                    timestamp=time.time()
                )
                
                # 创建位置信息 (使用滤波后的坐标)
                position = AOAPosition(
                    anchor_id=frame.anchor_data.anchor_id,
                    tag_id=tag_id,
                    distance=distance,  # 原始距离
                    angle=angle,  # 原始角度
                    confidence=filter_info.get('confidence', 0.7)
                )
                
                # 在 frame_info 中添加滤波后的结果
                frame_info = frame.get_summary()
                frame_info['frame_number'] = self.frame_count
                frame_info['filtered_x'] = filtered_x
                frame_info['filtered_y'] = filtered_y
                frame_info['filter_confidence'] = filter_info.get('confidence', 0.0)
                frame_info['velocity_x'] = filter_info.get('velocity_x', 0.0)
                frame_info['velocity_y'] = filter_info.get('velocity_y', 0.0)
            else:
                # 不使用滤波，直接转换极坐标
                import math
                angle_rad = math.radians(angle)
                filtered_x = distance * math.cos(angle_rad)
                filtered_y = distance * math.sin(angle_rad)
                
                # 创建位置信息
                position = AOAPosition(
                    anchor_id=frame.anchor_data.anchor_id,
                    tag_id=tag_id,
                    distance=distance,
                    angle=angle,
                    confidence=0.95 if frame.tag_data.fp_db > -100 else 0.7
                )
                
                frame_info = frame.get_summary()
                frame_info['frame_number'] = self.frame_count
                frame_info['filtered_x'] = filtered_x
                frame_info['filtered_y'] = filtered_y
            
            self.frame_received.emit(frame_info)
            
            # 发送位置更新信号
            self.position_updated.emit(position.to_dict())
    
    def stop(self):
        """停止工作线程"""
        self.is_running = False
        if self.reader:
            self.reader.stop()
    
    def enable_filter(self, enabled: bool = True):
        """
        启用或禁用卡尔曼滤波
        
        Args:
            enabled: True 为启用，False 为禁用
        """
        self.filter_enabled = enabled
        logger.info(f"卡尔曼滤波器已{'启用' if enabled else '禁用'}")
    
    def reset_filter(self):
        """重置卡尔曼滤波器"""
        self.kalman_filter.reset()
        logger.info("卡尔曼滤波器已重置")
    
    def get_filter_state(self, tag_id: int) -> dict:
        """
        获取指定标签的滤波器状态
        
        Args:
            tag_id: 标签 ID
        
        Returns:
            滤波器状态字典
        """
        return self.kalman_filter.get_filter_state(tag_id)
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        if self.reader:
            return self.reader.get_statistics()
        return {'error': 'Reader not initialized'}


class AOADataProcessor(QThread):
    """
    AOA 数据处理线程 - 处理多个 ANCHER 的位置计算
    使用三角测量法计算标签的绝对位置，并应用卡尔曼滤波
    """
    
    # 信号定义
    position_calculated = pyqtSignal(dict)  # 计算出的绝对位置
    error = pyqtSignal(str)
    
    def __init__(self):
        """初始化数据处理线程"""
        super().__init__()
        
        self.position_data = {}  # 存储各 ANCHER 的位置数据
        self.anchors = {}  # ANCHER 的已知位置
        self.is_running = False
        
        # 初始化卡尔曼滤波器用于多 ANCHER 融合定位
        self.kalman_filter = MultiTargetKalmanFilter(
            process_noise=0.05,  # 较低的过程噪声
            measurement_noise=0.3,  # 较低的测量噪声 (多 ANCHER 更精确)
            prediction_horizon=0.5,
            min_confidence=0.3,
            target_lost_timeout=2.0
        )
        
        self.filter_enabled = True
    
    def register_anchor(self, anchor_id: int, x: float, y: float):
        """
        注册 ANCHER 的已知位置
        
        Args:
            anchor_id: ANCHER ID
            x: X 坐标（米）
            y: Y 坐标（米）
        """
        self.anchors[anchor_id] = {'x': x, 'y': y}
    
    def process_aoa_position(self, position: AOAPosition):
        """
        处理 AOA 位置数据
        
        Args:
            position: AOAPosition 实例
        """
        key = position.tag_id
        
        if key not in self.position_data:
            self.position_data[key] = {}
        
        # 存储当前 ANCHER 的位置数据
        anchor_id = position.anchor_id
        self.position_data[key][anchor_id] = position
        
        # 当至少有 2 个 ANCHER 的数据时，尝试计算绝对位置
        if len(self.position_data[key]) >= 2:
            result = self._calculate_position(key)
            if result:
                self.position_calculated.emit(result)
    
    def _calculate_position(self, tag_id: int) -> Optional[dict]:
        """
        使用多个 ANCHER 的距离和角度数据计算标签绝对位置，并应用卡尔曼滤波
        
        Args:
            tag_id: 标签 ID
            
        Returns:
            计算结果或 None
        """
        try:
            positions = self.position_data.get(tag_id, {})
            
            if len(positions) < 2:
                return None
            
            # 这是一个简化的实现，实际应用需要更复杂的三角测量算法
            # 目前只使用第一个 ANCHER 的极坐标直接转换
            
            first_anchor_id = min(positions.keys())
            first_pos = positions[first_anchor_id]
            anchor = self.anchors.get(first_anchor_id, {'x': 0, 'y': 0})
            
            # 简单的极坐标到笛卡尔坐标的转换
            import math
            angle_rad = math.radians(first_pos.angle)
            
            tag_x = anchor['x'] + first_pos.distance * math.cos(angle_rad)
            tag_y = anchor['y'] + first_pos.distance * math.sin(angle_rad)
            
            # 计算计算出的位置相对于原点的距离和角度
            calc_distance = math.sqrt(tag_x * tag_x + tag_y * tag_y)
            calc_angle = math.degrees(math.atan2(tag_y, tag_x))
            
            # 应用卡尔曼滤波到计算结果
            if self.filter_enabled:
                filtered_x, filtered_y, filter_info = self.kalman_filter.filter_measurement(
                    tag_id=tag_id,
                    distance=calc_distance,
                    angle_deg=calc_angle,
                    timestamp=time.time()
                )
                
                return {
                    'tag_id': tag_id,
                    'x': filtered_x,
                    'y': filtered_y,
                    'calc_x': tag_x,  # 原始计算结果
                    'calc_y': tag_y,
                    'distance': calc_distance,
                    'angle': calc_angle,
                    'confidence': filter_info.get('confidence', first_pos.confidence),
                    'filtered': True,
                    'velocity_x': filter_info.get('velocity_x', 0.0),
                    'velocity_y': filter_info.get('velocity_y', 0.0),
                    'timestamp': first_pos.timestamp.isoformat() if hasattr(first_pos, 'timestamp') else None
                }
            else:
                return {
                    'tag_id': tag_id,
                    'x': tag_x,
                    'y': tag_y,
                    'distance': calc_distance,
                    'angle': calc_angle,
                    'confidence': first_pos.confidence,
                    'filtered': False,
                    'timestamp': first_pos.timestamp.isoformat() if hasattr(first_pos, 'timestamp') else None
                }
        
        except Exception as e:
            logger.error(f"计算位置失败: {e}")
            return None
    
    def run(self):
        """线程主循环"""
        self.is_running = True
        # 处理线程的主循环逻辑可以在这里实现
        # 目前通过 process_aoa_position 方法进行事件驱动处理    
    def enable_filter(self, enabled: bool = True):
        """
        启用或禁用卡尔曼滤波
        
        Args:
            enabled: True 为启用，False 为禁用
        """
        self.filter_enabled = enabled
        logger.info(f"数据处理器卡尔曼滤波器已{'启用' if enabled else '禁用'}")
    
    def reset_filter(self):
        """重置卡尔曼滤波器"""
        self.kalman_filter.reset()
        logger.info("数据处理器卡尔曼滤波器已重置")