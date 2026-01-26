"""
AOA 过滤线程（原 AOAWorker）
负责接收串口原始字节，解析为帧与位置，并（可选）应用卡尔曼滤波输出稳定坐标。

本模块包含卡尔曼滤波器实现，提供多目标跟踪和运动预测功能。
"""
try:
    from PyQt6.QtCore import QThread, pyqtSignal
    PYQT6_AVAILABLE = True
except ImportError:
    PYQT6_AVAILABLE = False
    # 提供占位类，避免在非GUI环境下导入错误
    QThread = object
    pyqtSignal = lambda *args, **kwargs: None

import logging
import time
import numpy as np
import math
from typing import Optional, Tuple, Dict, Any
from threading import Lock
from dataclasses import dataclass, field
from datetime import datetime

from workers.aoa_serial_reader import AOASerialReader


logger = logging.getLogger(__name__)


@dataclass
class AOAPosition:
    """标签相对于 Anchor 的位置信息（简化版，移除 0x55 协议依赖）。"""
    anchor_id: int
    tag_id: int
    distance: float  # 米
    angle: float  # 度
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0

    def to_dict(self) -> dict:
        return {
            'anchor_id': self.anchor_id,
            'tag_id': self.tag_id,
            'distance': self.distance,
            'angle': self.angle,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence
        }


# =====================================================================
# 卡尔曼滤波器实现 (原 utils/aoa_kalman_filter.py)
# =====================================================================

class PolarKalmanFilter:
    """
    极坐标卡尔曼滤波器 - 直接在极坐标空间工作（距离、角度）
    
    状态向量: [distance, angle, v_distance, v_angle]
    - distance: 距离 (米)
    - angle: 角度 (度)
    - v_distance: 距离变化率 (米/秒)
    - v_angle: 角度变化率 (度/秒)
    
    优点：
    - 直接在原始传感器空间滤波，噪声模型更准确
    - 避免极坐标到笛卡尔坐标的非线性变换
    - 角度360°包裹处理更自然
    - 状态维度低，收敛快
    """
    
    def __init__(
        self,
        process_noise: float = 0.1,
        measurement_noise: float = 0.5,
        min_confidence: float = 0.3,
        max_human_speed: float = 5.0,
        angle_jump_threshold_deg: float = 90.0,
        stale_reset_sec: float = 0.8
    ):
        """
        初始化极坐标卡尔曼滤波器
        
        Args:
            process_noise: 过程噪声强度
            measurement_noise: 测量噪声强度
            min_confidence: 最小置信度
            max_human_speed: 人体最大合理速度 (米/秒)，用于过滤异常瞬时速度
            angle_jump_threshold_deg: 角度突变剔除阈值（度），超过则拒绝该观测
            stale_reset_sec: 角度连续性超时时间（秒），超过后视作重新开始
        """
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.min_confidence = min_confidence
        self.max_human_speed = max_human_speed  # 人体跑步约 5m/s，超过判为异常
        self.angle_jump_threshold_deg = angle_jump_threshold_deg
        self.stale_reset_sec = stale_reset_sec
        
        # 状态向量: [distance, angle, v_distance, v_angle]
        self.state = np.zeros(4)
        
        # 协方差矩阵 P
        self.P = np.eye(4) * 10.0
        
        # 过程噪声协方差矩阵 Q
        self.Q = np.eye(4) * self.process_noise
        self.Q[2:4, 2:4] *= 2.0  # 速度的噪声更大
        
        # 测量噪声协方差矩阵 R (只测量距离和角度)
        self.R = np.eye(2) * self.measurement_noise
        
        # 滤波器状态
        self.initialized = False
        self.last_update_time = None
        self.confidence = 0.0
        self.update_count = 0
        self.last_measurement_angle: Optional[float] = None
        self.last_measurement_time: Optional[float] = None
        
        logger.info('极坐标卡尔曼滤波器已初始化')
    
    def initialize(self, distance: float, angle_deg: float, timestamp: Optional[float] = None):
        """
        用第一次测量初始化滤波器
        
        Args:
            distance: 初始距离 (米)
            angle_deg: 初始角度 (度)
            timestamp: 时间戳 (秒)
        """
        self.state[0] = distance  # 距离
        self.state[1] = angle_deg  # 角度
        self.state[2:4] = 0.0  # 速度为0
        self.P = np.eye(4) * 10.0
        self.confidence = 0.5
        self.initialized = True
        self.last_update_time = timestamp
        self.last_measurement_angle = angle_deg
        self.last_measurement_time = timestamp
        logger.info(f'极坐标卡尔曼滤波器已初始化，初始: 距离={distance:.3f}m, 角度={angle_deg:.1f}°')

    def _is_angle_jump(self, angle_deg: float, timestamp: Optional[float]) -> bool:
        """检测是否为异常角度跳变（如 60° → -60° 突变）。"""
        if self.last_measurement_angle is None or self.last_measurement_time is None:
            return False
        if timestamp is None:
            return False

        dt = timestamp - self.last_measurement_time
        if dt >= self.stale_reset_sec:
            # 数据间隔过长视为重新开始
            return False

        delta = angle_deg - self.last_measurement_angle
        while delta > 180.0:
            delta -= 360.0
        while delta < -180.0:
            delta += 360.0

        if abs(delta) > self.angle_jump_threshold_deg:
            logger.debug(
                f'角度跳变 {delta:+.1f}° 超过阈值 {self.angle_jump_threshold_deg:.1f}°，拒绝本次观测'
            )
            return True

        return False
    
    def predict(self, dt: float):
        """
        卡尔曼滤波预测步骤
        
        Args:
            dt: 时间差 (秒)
        """
        # 状态转移矩阵 F (匀速运动模型)
        F = np.eye(4)
        F[0, 2] = dt  # distance += v_distance * dt
        F[1, 3] = dt  # angle += v_angle * dt
        
        # 预测状态
        self.state = F @ self.state
        
        # 预测协方差
        self.P = F @ self.P @ F.T + self.Q
        
        # 预测期间置信度略微下降
        self.confidence *= 0.98
    
    def update(self, distance: float, angle_deg: float):
        """
        卡尔曼滤波更新步骤
        
        Args:
            distance: 测量的距离 (米)
            angle_deg: 测量的角度 (度)
        """
        measurement = np.array([distance, angle_deg])
        
        # 测量矩阵 H (只测量距离和角度)
        H = np.zeros((2, 4))
        H[0, 0] = 1.0  # 测量距离
        H[1, 1] = 1.0  # 测量角度
        
        # 新息 (Innovation)
        y_innov = measurement - H @ self.state
        
        # 处理角度360°包裹问题
        # 确保角度差在 [-180, 180] 范围内
        while y_innov[1] > 180.0:
            y_innov[1] -= 360.0
        while y_innov[1] < -180.0:
            y_innov[1] += 360.0
        
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
        
        # 更新后处理角度，确保在合理范围
        while self.state[1] > 180.0:
            self.state[1] -= 360.0
        while self.state[1] < -180.0:
            self.state[1] += 360.0
        
        # 更新协方差
        self.P = (np.eye(4) - K @ H) @ self.P
        
        # 速度合理性检查（人体速度上限）
        v_distance = float(self.state[2])
        v_angle = float(self.state[3])
        distance = float(self.state[0])
        angle_rad = math.radians(float(self.state[1]))
        
        # 速度的笛卡尔分量（线性近似）
        vx = -v_distance * math.sin(angle_rad)
        vy = v_distance * math.cos(angle_rad)
        speed = math.sqrt(vx * vx + vy * vy)
        
        # 超过人体速度上限时，限制速度并对置信度加惩罚
        speed_penalty = 0.0
        if speed > self.max_human_speed:
            speed_ratio = speed / self.max_human_speed
            speed_penalty = min(1.0, (speed_ratio - 1.0) * 0.5)
            scale = self.max_human_speed / speed
            self.state[2] *= scale  # 限制距离速度
            self.state[3] *= scale  # 限制角速度
            logger.debug(f'检测到异常瞬时速度 {speed:.2f}m/s，已限制到 {self.max_human_speed:.2f}m/s')
        
        # 根据新息幅度更新置信度（归一化处理）
        # 距离误差归一化：按米计算，期望误差范围0-1米
        # 角度误差归一化：按度计算，期望误差范围0-30度
        normalized_dist_error = abs(y_innov[0]) / 1.0
        normalized_angle_error = abs(y_innov[1]) / 30.0
        
        # 综合误差（包含速度惩罚）
        total_error = (normalized_dist_error + normalized_angle_error) / 2.0 + speed_penalty
        
        # 基于归一化误差计算置信度更新
        confidence_update = 1.0 / (1.0 + total_error * 2.0)
        
        # 平滑更新置信度
        self.confidence = 0.9 * self.confidence + 0.1 * confidence_update
        self.confidence = min(1.0, max(self.min_confidence, self.confidence))
    
    def filter_measurement(
        self,
        distance: float,
        angle_deg: float,
        timestamp: Optional[float] = None
    ) -> Tuple[float, float, Dict]:
        """
        对测量值进行滤波并返回滤波后的位置（极坐标和笛卡尔坐标）
        
        Args:
            distance: 距离 (米)
            angle_deg: 角度 (度)
            timestamp: 时间戳 (秒)
        
        Returns:
            (x, y, info_dict) - 笛卡尔坐标和信息字典
        """
        # 首次测量时初始化
        if not self.initialized:
            self.initialize(distance, angle_deg, timestamp)
            # 转换为笛卡尔坐标返回
            angle_rad = math.radians(angle_deg)
            y = distance * math.cos(angle_rad)
            x = -distance * math.sin(angle_rad)
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

        # 角度突变剔除：如果观测与最近一次角度相差过大且时间间隔短，则拒绝更新
        if self._is_angle_jump(angle_deg, timestamp):
            if timestamp is not None:
                self.last_update_time = timestamp
            # 轻微衰减置信度，但保持当前预测状态
            self.confidence = max(self.min_confidence, self.confidence * 0.95)

            filtered_distance = float(self.state[0])
            filtered_angle = float(self.state[1])
            angle_rad = math.radians(filtered_angle)
            filtered_y = filtered_distance * math.cos(angle_rad)
            filtered_x = -filtered_distance * math.sin(angle_rad)

            return filtered_x, filtered_y, {
                'status': 'rejected_angle_jump',
                'confidence': float(self.confidence),
                'filtered_x': filtered_x,
                'filtered_y': filtered_y,
                'filtered_distance': filtered_distance,
                'filtered_angle': filtered_angle,
                'v_distance': float(self.state[2]),
                'v_angle': float(self.state[3])
            }
        
        # 更新步骤
        self.update(distance, angle_deg)
        
        # 更新时间戳
        if timestamp is not None:
            self.last_update_time = timestamp
            self.last_measurement_time = timestamp
        self.last_measurement_angle = angle_deg
        
        self.update_count += 1
        
        # 获取滤波后的极坐标值
        filtered_distance = float(self.state[0])
        filtered_angle = float(self.state[1])
        
        # 转换为笛卡尔坐标
        angle_rad = math.radians(filtered_angle)
        filtered_y = filtered_distance * math.cos(angle_rad)  # Y轴=前方
        filtered_x = -filtered_distance * math.sin(angle_rad)  # X轴=右侧
        
        return filtered_x, filtered_y, {
            'status': 'filtered',
            'confidence': float(self.confidence),
            'filtered_x': filtered_x,
            'filtered_y': filtered_y,
            'filtered_distance': filtered_distance,
            'filtered_angle': filtered_angle,
            'v_distance': float(self.state[2]),
            'v_angle': float(self.state[3])
        }
    
    def get_current_state(self) -> Dict:
        """
        获取当前状态向量
        
        Returns:
            包含极坐标和笛卡尔坐标的字典
        """
        if not self.initialized:
            return {
                'initialized': False,
                'confidence': 0.0
            }
        
        # 极坐标数据
        distance = float(self.state[0])
        angle = float(self.state[1])
        v_distance = float(self.state[2])
        v_angle = float(self.state[3])
        
        # 转换为笛卡尔坐标
        angle_rad = math.radians(angle)
        y = distance * math.cos(angle_rad)
        x = -distance * math.sin(angle_rad)
        
        # 速度的笛卡尔坐标近似 (线性化)
        vx = -v_distance * math.sin(angle_rad)
        vy = v_distance * math.cos(angle_rad)
        
        return {
            'initialized': True,
            'x': float(x),
            'y': float(y),
            'vx': float(vx),
            'vy': float(vy),
            'distance': float(distance),
            'angle': float(angle),
            'v_distance': float(v_distance),
            'v_angle': float(v_angle),
            'speed': float(math.sqrt(vx**2 + vy**2)),
            'confidence': float(self.confidence),
            'update_count': self.update_count
        }
    
    def reset(self):
        """重置滤波器"""
        self.state = np.zeros(4)
        self.P = np.eye(4) * 10.0
        self.initialized = False
        self.last_update_time = None
        self.confidence = 0.0
        self.update_count = 0
        self.last_measurement_angle = None
        self.last_measurement_time = None
        logger.info('极坐标卡尔曼滤波器已重置')


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
        # 车辆坐标系：Y轴=前方, X轴=右侧
        angle_rad = math.radians(angle_deg)
        y = distance * math.cos(angle_rad)   # 前方（Y轴）
        x = -distance * math.sin(angle_rad)  # 右侧（X轴，负号因角度逆时针）
        
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
    多目标卡尔曼滤波器 - 为每个标签维护一个极坐标滤波器实例
    """
    
    def __init__(
        self,
        process_noise: float = 0.1,
        measurement_noise: float = 0.5,
        min_confidence: float = 0.3,
        target_lost_timeout: float = 2.0,
        max_human_speed: float = 5.0,
        angle_jump_threshold_deg: float = 90.0,
        stale_reset_sec: float = 0.8,
        prediction_horizon: float = 0.5
    ):
        """
        初始化多目标卡尔曼滤波器（极坐标版本）
        
        Args:
            process_noise: 过程噪声强度
            measurement_noise: 测量噪声强度
            min_confidence: 最小置信度
            target_lost_timeout: 目标丢失超时时间 (秒)
            max_human_speed: 人体最大合理速度 (米/秒)
            angle_jump_threshold_deg: 角度突变剔除阈值（度），超过则拒绝该观测
            stale_reset_sec: 角度连续性超时时间（秒）
            prediction_horizon: 兼容旧参数，占位不用
        """
        self.process_noise = process_noise
        self.measurement_noise = measurement_noise
        self.min_confidence = min_confidence
        self.target_lost_timeout = target_lost_timeout
        self.max_human_speed = max_human_speed
        self.angle_jump_threshold_deg = angle_jump_threshold_deg
        self.stale_reset_sec = stale_reset_sec
        self.prediction_horizon = prediction_horizon
        
        # 每个标签 ID 对应一个极坐标滤波器实例
        self.filters: Dict[int, PolarKalmanFilter] = {}
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
            (x, y, info_dict) - 滤波后的笛卡尔坐标和信息字典
        """
        # 如果该标签没有滤波器，创建一个
        if tag_id not in self.filters:
            self.filters[tag_id] = PolarKalmanFilter(
                process_noise=self.process_noise,
                measurement_noise=self.measurement_noise,
                min_confidence=self.min_confidence,
                max_human_speed=self.max_human_speed,
                angle_jump_threshold_deg=self.angle_jump_threshold_deg,
                stale_reset_sec=self.stale_reset_sec
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


# =====================================================================
# AOA 过滤线程实现
# =====================================================================


class AOAFilter(QThread):
    """后台线程用于处理 AOA 数据接收与滤波"""

    # 信号定义
    frame_received = pyqtSignal(dict)  # 接收到新的 AOA 帧
    position_updated = pyqtSignal(dict)  # 位置更新
    statistics_updated = pyqtSignal(dict)  # 统计信息更新
    error = pyqtSignal(str)  # 错误信息
    status_changed = pyqtSignal(str)  # 状态变化

    def __init__(self, port: str = '/dev/ttyCH343USB0', baudrate: int = 921600,
                 angle_jump_threshold_deg: float = 60.0,
                 stale_reset_sec: float = 0.8):
        """
        初始化 AOA 过滤线程

        Args:
            port: 串口名称
            baudrate: 波特率
            angle_jump_threshold_deg: 角度突变剔除阈值（度），超过则认为是异常帧
            stale_reset_sec: 当两次观测时间间隔超过该值时，重置连续性判断
            
        Note:
            卡尔曼滤波器使用 utils/aoa_kalman_filter.py 中的 MultiTargetKalmanFilter 类
            坐标系定义：Y轴=前方, X轴=右侧（与 utils/aoa_kalman_filter.py 一致）
        """
        super().__init__()

        self.port = port
        self.baudrate = baudrate
        self.reader: Optional[AOASerialReader] = None
        self.is_running = False
        self.frame_count = 0
        self.buffer = bytearray()
        self.buffer_lock = Lock()
        # 注意：二进制帧解析已移除，新产品采用ASCII文本协议
        self.angle_jump_threshold_deg = angle_jump_threshold_deg
        self.stale_reset_sec = stale_reset_sec
        self._last_measurements = {}  # {tag_id: {"angle": float, "distance": float, "ts": float}}
        self.dropped_frames = 0

        # 初始化卡尔曼滤波器 (启用多目标跟踪)
        self.kalman_filter = MultiTargetKalmanFilter(
            process_noise=0.1,
            measurement_noise=0.5,
            min_confidence=0.3,
            target_lost_timeout=2.0,
            angle_jump_threshold_deg=self.angle_jump_threshold_deg,
            stale_reset_sec=self.stale_reset_sec
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

            # 注册原始数据回调
            self.reader.register_callback(self._on_raw_data_received)

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
                    # 注意：parser_stats 已移除，新产品使用ASCII解析器
                    stats['dropped_frames'] = self.dropped_frames
                    self.statistics_updated.emit(stats)
                    last_stats_time = current_time

                # 每 2 秒清理一次丢失的目标
                if current_time - last_cleanup_time >= 2.0:
                    self.kalman_filter.remove_lost_targets(current_time)
                    last_cleanup_time = current_time

        except Exception as e:
            error_msg = f"AOA 过滤线程错误: {str(e)}"
            logger.error(error_msg)
            self.error.emit(error_msg)
            self.status_changed.emit("错误")

    def _on_raw_data_received(self, data: bytes):
        """接收原始字节流并在此线程内解析"""
        with self.buffer_lock:
            self.buffer.extend(data)
            buffer = self.buffer

        frames, remaining = self.parser.parse_stream(buffer)

        # 保留未完整的尾部数据
        with self.buffer_lock:
            self.buffer = bytearray(remaining)

        for frame in frames:
            self._handle_frame(frame)

    def _handle_frame(self, frame: Any):
        self.frame_count += 1

        # 不依赖校验和(is_valid)，只要能解析出tag_data和anchor_data就处理
        if frame.tag_data and frame.anchor_data:
            distance = frame.tag_data.distance / 1000.0  # 转米
            angle = frame.tag_data.angle
            tag_id = frame.tag_data.tag_id
            ts = time.time()

            # 1) 异常帧剔除（角度连续性）
            if self._is_outlier(tag_id, distance, angle, ts):
                self.dropped_frames += 1
                return

            if self.filter_enabled:
                # 使用卡尔曼滤波处理测量值
                filtered_x, filtered_y, filter_info = self.kalman_filter.filter_measurement(
                    tag_id=tag_id,
                    distance=distance,
                    angle_deg=angle,
                    timestamp=ts
                )

                # 构建滤波后的结果（锚点局部坐标）
                kalman_result = {
                    'anchor_id': frame.anchor_data.anchor_id,
                    'tag_id': tag_id,
                    'x': filtered_x,
                    'y': filtered_y,
                    'confidence': filter_info.get('confidence', 0.0),
                    'velocity_x': filter_info.get('velocity_x', 0.0),
                    'velocity_y': filter_info.get('velocity_y', 0.0),
                    'acceleration_x': filter_info.get('acceleration_x', 0.0),
                    'acceleration_y': filter_info.get('acceleration_y', 0.0),
                    'timestamp': ts,
                    'status': filter_info.get('status', 'unknown')
                }

                frame_info = frame.get_summary()
                frame_info['frame_number'] = self.frame_count
                frame_info['filtered_x'] = filtered_x
                frame_info['filtered_y'] = filtered_y
                frame_info['filter_confidence'] = filter_info.get('confidence', 0.0)
                frame_info['velocity_x'] = filter_info.get('velocity_x', 0.0)
                frame_info['velocity_y'] = filter_info.get('velocity_y', 0.0)
                frame_info['acceleration_x'] = filter_info.get('acceleration_x', 0.0)
                frame_info['acceleration_y'] = filter_info.get('acceleration_y', 0.0)
                frame_info['filter_status'] = filter_info.get('status', 'unknown')
            else:
                # 未启用滤波时直接进行极坐标到笛卡尔坐标转换
                # 坐标系：Y轴=前方, X轴=右侧（与 utils/aoa_kalman_filter.py 一致）
                import math
                angle_rad = math.radians(angle)
                filtered_y = distance * math.cos(angle_rad)   # 前方（Y轴）
                filtered_x = -distance * math.sin(angle_rad)  # 右侧（X轴，负号因角度逆时针）
                
                kalman_result = {
                    'anchor_id': frame.anchor_data.anchor_id,
                    'tag_id': tag_id,
                    'x': filtered_x,
                    'y': filtered_y,
                    'confidence': 0.95 if frame.tag_data.fp_db > -100 else 0.7,
                    'velocity_x': 0.0,
                    'velocity_y': 0.0,
                    'acceleration_x': 0.0,
                    'acceleration_y': 0.0,
                    'timestamp': ts,
                    'status': 'no_filter'
                }

                frame_info = frame.get_summary()
                frame_info['frame_number'] = self.frame_count
                frame_info['filtered_x'] = filtered_x
                frame_info['filtered_y'] = filtered_y
                frame_info['filter_status'] = 'no_filter'

            self.frame_received.emit(frame_info)
            # 仅显示卡尔曼滤波（或简化推算）结果
            self.position_updated.emit(kalman_result)
            # 更新最后一次有效测量
            self._last_measurements[tag_id] = {'angle': angle, 'distance': distance, 'ts': ts}

    def stop(self):
        """停止过滤线程"""
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
            base = self.reader.get_statistics()
            base['dropped_frames'] = self.dropped_frames
            base['parser_stats'] = self.parser.get_statistics()
            return base
        return {'error': 'Reader not initialized', 'dropped_frames': self.dropped_frames}

    def get_filtered_beacon_coordinates(self, tag_id: int = 1) -> dict:
        """
        获取指定标签的当前滤波坐标（Anchor 局部坐标系）

        Args:
            tag_id: 标签 ID，默认为 1

        Returns:
            字典包含：
            {
                'tag_id': int,
                'x': float,  # Anchor 局部坐标 (米)
                'y': float,  # Anchor 局部坐标 (米)
                'confidence': float,  # 置信度 0-1
                'velocity_x': float,  # X 速度 (米/秒)
                'velocity_y': float,  # Y 速度 (米/秒)
                'acceleration_x': float,  # X 加速度 (米/秒²)
                'acceleration_y': float,  # Y 加速度 (米/秒²)
                'initialized': bool  # 滤波器是否已初始化
            }
        """
        state = self.kalman_filter.get_filter_state(tag_id)
        return {
            'tag_id': tag_id,
            'x': state.get('x', 0.0),
            'y': state.get('y', 0.0),
            'confidence': state.get('confidence', 0.0),
            'velocity_x': state.get('vx', 0.0),
            'velocity_y': state.get('vy', 0.0),
            'acceleration_x': state.get('ax', 0.0),
            'acceleration_y': state.get('ay', 0.0),
            'initialized': state.get('initialized', False)
        }


    def _is_outlier(self, tag_id: int, distance_m: float, angle_deg: float, ts: float) -> bool:
        """
        基于角度连续性剔除异常帧
        
        Args:
            tag_id: 标签 ID
            distance_m: 距离 (米)
            angle_deg: 角度 (度)
            ts: 时间戳 (秒)
        
        Returns:
            True 表示是异常值,False 表示正常值
        
        规则：
        - 若该标签无历史值，视为有效
        - 若当前与上次时间间隔超过 stale_reset_sec，视为重置，有效
        - 否则计算角度差（考虑 360° 包裹），若绝对值超过阈值，则判为异常
        """
        last = self._last_measurements.get(tag_id)
        if not last:
            # 无历史数据,接受首次测量
            return False
        
        dt = ts - last['ts']
        if dt >= self.stale_reset_sec:
            # 时间间隔过长,重置连续性判断
            logger.debug(f'标签 {tag_id} 时间间隔 {dt:.3f}s 超过阈值,重置连续性判断')
            return False
        
        # 归一化角度差到 [-180, 180]
        delta = angle_deg - last['angle']
        while delta > 180.0:
            delta -= 360.0
        while delta < -180.0:
            delta += 360.0
        
        is_outlier = abs(delta) > self.angle_jump_threshold_deg
        if is_outlier:
            logger.debug(
                f'标签 {tag_id} 角度突变 {abs(delta):.1f}° 超过阈值 '
                f'{self.angle_jump_threshold_deg:.1f}°, 剔除异常帧'
            )
        
        return is_outlier

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
        # 使用与 utils/aoa_kalman_filter.py 一致的参数
        self.kalman_filter = MultiTargetKalmanFilter(
            process_noise=0.1,        # 过程噪声强度
            measurement_noise=0.5,     # 测量噪声强度
            prediction_horizon=0.5,    # 预测时间 (秒)
            min_confidence=0.3,        # 最小置信度
            target_lost_timeout=2.0    # 目标丢失超时时间 (秒)
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
            # TODO: 使用至少两个 ANCHER 的位置进行融合计算
            return None
        except Exception as e:
            logger.error(f"计算位置失败: {e}")
            return None


# 注意：原 0x55 二进制帧解析器已移除
# 新产品采用ASCII文本协议，由 BeaconDataParser (test_realtime_beacon.py) 处理
