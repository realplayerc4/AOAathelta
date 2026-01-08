"""
卡尔曼滤波模块 - 基于 AOA/src/kalman_filter_node.py
用于提高 AOA 定位标签的准确率
"""
import numpy as np
import math
import logging
from typing import Optional, Tuple, Dict
from datetime import datetime


logger = logging.getLogger(__name__)


class KalmanFilter:
    """
    扩展卡尔曼滤波器 - 用于目标追踪和运动预测
    
    状态向量: [x, y, vx, vy, ax, ay]
    - x, y: 位置 (米)
    - vx, vy: 速度 (米/秒)
    - ax, ay: 加速度 (米/秒²)
    """
    
    def __init__(
        self,
        process_noise: float = 0.1,
        measurement_noise: float = 0.5,
        prediction_horizon: float = 0.5,
        min_confidence: float = 0.3
    ):
        """
        初始化卡尔曼滤波器
        
        Args:
            process_noise: 过程噪声强度
            measurement_noise: 测量噪声强度
            prediction_horizon: 预测时间 (秒)
            min_confidence: 最小置信度
        """
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.prediction_horizon = prediction_horizon
        self.min_confidence = min_confidence
        
        # 状态向量: [x, y, vx, vy, ax, ay]
        self.state = np.zeros(6)
        
        # 协方差矩阵 P
        self.P = np.eye(6) * 10.0
        
        # 过程噪声协方差矩阵 Q
        self.Q = np.eye(6) * self.process_noise
        self.Q[4:6, 4:6] *= 2.0  # 加速度的噪声更大
        
        # 测量噪声协方差矩阵 R
        self.R = np.eye(2) * self.measurement_noise
        
        # 滤波器状态
        self.initialized = False
        self.last_update_time = None
        self.confidence = 0.0
        self.update_count = 0
        
        logger.info('卡尔曼滤波器已初始化')
    
    def initialize(self, x: float, y: float, timestamp: Optional[float] = None):
        """
        用第一次测量初始化滤波器
        
        Args:
            x: 初始 X 坐标
            y: 初始 Y 坐标
            timestamp: 时间戳 (秒)
        """
        self.state[0:2] = [x, y]  # 位置
        self.state[2:4] = 0.0  # 速度
        self.state[4:6] = 0.0  # 加速度
        self.P = np.eye(6) * 10.0
        self.confidence = 0.5
        self.initialized = True
        self.last_update_time = timestamp
        logger.info(f'卡尔曼滤波器已初始化，初始位置: ({x:.3f}, {y:.3f})')
    
    def predict(self, dt: float):
        """
        卡尔曼滤波预测步骤
        
        Args:
            dt: 时间差 (秒)
        """
        # 状态转移矩阵 F
        F = np.eye(6)
        F[0, 2] = dt
        F[1, 3] = dt
        F[0, 4] = 0.5 * dt * dt
        F[1, 5] = 0.5 * dt * dt
        F[2, 4] = dt
        F[3, 5] = dt
        
        # 预测状态
        self.state = F @ self.state
        
        # 预测协方差
        self.P = F @ self.P @ F.T + self.Q
        
        # 预测期间置信度略微下降
        self.confidence *= 0.98
    
    def update(self, x: float, y: float):
        """
        卡尔曼滤波更新步骤
        
        Args:
            x: 测量的 X 坐标
            y: 测量的 Y 坐标
        """
        measurement = np.array([x, y])
        
        # 测量矩阵 H (只测量位置)
        H = np.zeros((2, 6))
        H[0, 0] = 1.0
        H[1, 1] = 1.0
        
        # 新息 (Innovation)
        y_innov = measurement - H @ self.state
        
        # 新息协方差
        S = H @ self.P @ H.T + self.R
        
        # 卡尔曼增益
        try:
            K = self.P @ H.T @ np.linalg.inv(S)
        except np.linalg.LinAlgError:
            logger.warning('卡尔曼增益计算失败，跳过更新')
            return
        
        # 更新状态
        self.state = self.state + K @ y_innov
        
        # 更新协方差
        self.P = (np.eye(6) - K @ H) @ self.P
        
        # 根据新息幅度更新置信度
        innovation_norm = np.linalg.norm(y_innov)
        confidence_update = 1.0 / (1.0 + innovation_norm)
        self.confidence = 0.9 * self.confidence + 0.1 * confidence_update
        self.confidence = min(1.0, max(self.min_confidence, self.confidence))
    
    def filter_measurement(
        self,
        distance: float,
        angle_deg: float,
        timestamp: Optional[float] = None
    ) -> Tuple[float, float, Dict]:
        """
        对测量值进行滤波并返回滤波后的位置
        
        Args:
            distance: 距离 (米)
            angle_deg: 角度 (度)
            timestamp: 时间戳 (秒)
        
        Returns:
            (x, y, info_dict) - 滤波后的坐标和信息字典
        """
        # 极坐标转笛卡尔坐标
        angle_rad = math.radians(angle_deg)
        x = distance * math.cos(angle_rad)
        y = distance * math.sin(angle_rad)
        
        # 首次测量时初始化
        if not self.initialized:
            self.initialize(x, y, timestamp)
            return x, y, {
                'status': 'initialized',
                'confidence': self.confidence,
                'filtered_x': x,
                'filtered_y': y
            }
        
        # 计算时间差
        if timestamp is not None and self.last_update_time is not None:
            dt = timestamp - self.last_update_time
        else:
            dt = 0.01  # 默认 10ms
        
        if dt > 0:
            # 预测步骤
            self.predict(dt)
        
        # 更新步骤
        self.update(x, y)
        
        # 更新时间戳
        if timestamp is not None:
            self.last_update_time = timestamp
        
        self.update_count += 1
        
        # 返回滤波后的位置
        filtered_x = float(self.state[0])
        filtered_y = float(self.state[1])
        
        return filtered_x, filtered_y, {
            'status': 'filtered',
            'confidence': float(self.confidence),
            'filtered_x': filtered_x,
            'filtered_y': filtered_y,
            'velocity_x': float(self.state[2]),
            'velocity_y': float(self.state[3]),
            'acceleration_x': float(self.state[4]),
            'acceleration_y': float(self.state[5])
        }
    
    def predict_future_position(
        self,
        horizon: Optional[float] = None
    ) -> Tuple[float, float, float, float]:
        """
        预测未来位置
        
        Args:
            horizon: 预测时间 (秒)，如果为 None 使用初始化时的预测时间
        
        Returns:
            (future_x, future_y, future_distance, future_angle_deg)
        """
        if not self.initialized:
            return 0.0, 0.0, 0.0, 0.0
        
        dt = horizon if horizon is not None else self.prediction_horizon
        
        # 基于当前状态预测未来位置
        future_x = (self.state[0] + 
                   self.state[2] * dt + 
                   0.5 * self.state[4] * dt * dt)
        future_y = (self.state[1] + 
                   self.state[3] * dt + 
                   0.5 * self.state[5] * dt * dt)
        
        # 笛卡尔坐标转极坐标
        future_distance = math.sqrt(future_x * future_x + future_y * future_y)
        future_angle = math.degrees(math.atan2(future_y, future_x))
        
        return future_x, future_y, future_distance, future_angle
    
    def get_current_state(self) -> Dict:
        """
        获取当前状态向量
        
        Returns:
            包含位置、速度、加速度的字典
        """
        if not self.initialized:
            return {
                'initialized': False,
                'confidence': 0.0
            }
        
        speed = math.sqrt(self.state[2]**2 + self.state[3]**2)
        acceleration = math.sqrt(self.state[4]**2 + self.state[5]**2)
        
        return {
            'initialized': True,
            'x': float(self.state[0]),
            'y': float(self.state[1]),
            'vx': float(self.state[2]),
            'vy': float(self.state[3]),
            'ax': float(self.state[4]),
            'ay': float(self.state[5]),
            'speed': float(speed),
            'acceleration': float(acceleration),
            'confidence': float(self.confidence),
            'update_count': self.update_count
        }
    
    def reset(self):
        """重置滤波器"""
        self.state = np.zeros(6)
        self.P = np.eye(6) * 10.0
        self.initialized = False
        self.last_update_time = None
        self.confidence = 0.0
        self.update_count = 0
        logger.info('卡尔曼滤波器已重置')


class MultiTargetKalmanFilter:
    """
    多目标卡尔曼滤波器 - 为每个标签维护一个滤波器实例
    """
    
    def __init__(
        self,
        process_noise: float = 0.1,
        measurement_noise: float = 0.5,
        prediction_horizon: float = 0.5,
        min_confidence: float = 0.3,
        target_lost_timeout: float = 2.0
    ):
        """
        初始化多目标卡尔曼滤波器
        
        Args:
            process_noise: 过程噪声强度
            measurement_noise: 测量噪声强度
            prediction_horizon: 预测时间 (秒)
            min_confidence: 最小置信度
            target_lost_timeout: 目标丢失超时时间 (秒)
        """
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.prediction_horizon = prediction_horizon
        self.min_confidence = min_confidence
        self.target_lost_timeout = target_lost_timeout
        
        # 每个标签 ID 对应一个滤波器实例
        self.filters: Dict[int, KalmanFilter] = {}
        # 每个标签的最后更新时间
        self.last_update_times: Dict[int, float] = {}
    
    def filter_measurement(
        self,
        tag_id: int,
        distance: float,
        angle_deg: float,
        timestamp: Optional[float] = None
    ) -> Tuple[float, float, Dict]:
        """
        对指定标签的测量值进行滤波
        
        Args:
            tag_id: 标签 ID
            distance: 距离 (米)
            angle_deg: 角度 (度)
            timestamp: 时间戳 (秒)
        
        Returns:
            (x, y, info_dict) - 滤波后的坐标和信息字典
        """
        # 如果该标签没有滤波器，创建一个
        if tag_id not in self.filters:
            self.filters[tag_id] = KalmanFilter(
                process_noise=self.process_noise,
                measurement_noise=self.measurement_noise,
                prediction_horizon=self.prediction_horizon,
                min_confidence=self.min_confidence
            )
        
        # 使用对应的滤波器进行滤波
        filter_obj = self.filters[tag_id]
        x, y, info = filter_obj.filter_measurement(distance, angle_deg, timestamp)
        
        # 更新最后接收时间
        if timestamp is not None:
            self.last_update_times[tag_id] = timestamp
        
        return x, y, info
    
    def get_filter_state(self, tag_id: int) -> Dict:
        """
        获取指定标签的滤波器状态
        
        Args:
            tag_id: 标签 ID
        
        Returns:
            滤波器状态字典
        """
        if tag_id not in self.filters:
            return {'initialized': False, 'tag_id': tag_id}
        
        state = self.filters[tag_id].get_current_state()
        state['tag_id'] = tag_id
        return state
    
    def get_all_targets(self) -> Dict[int, Dict]:
        """
        获取所有目标的状态
        
        Returns:
            {tag_id: state_dict} 的字典
        """
        result = {}
        for tag_id in self.filters.keys():
            result[tag_id] = self.get_filter_state(tag_id)
        return result
    
    def remove_lost_targets(self, current_time: Optional[float] = None):
        """
        移除超时未更新的目标
        
        Args:
            current_time: 当前时间戳 (秒)
        """
        if current_time is None:
            return
        
        lost_targets = []
        for tag_id, last_update_time in self.last_update_times.items():
            if current_time - last_update_time > self.target_lost_timeout:
                lost_targets.append(tag_id)
        
        for tag_id in lost_targets:
            del self.filters[tag_id]
            del self.last_update_times[tag_id]
            logger.info(f'目标 {tag_id} 已移除 (超时)')
    
    def reset(self):
        """重置所有滤波器"""
        self.filters.clear()
        self.last_update_times.clear()
        logger.info('所有滤波器已重置')
