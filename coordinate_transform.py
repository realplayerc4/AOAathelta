"""
坐标变换模块 - 将Beacon的Anchor局部坐标转换到地图全局坐标系

关键概念：
- Anchor安装在地盘上，随地盘一起移动
- Anchor的位置 = 地盘的位置
- 原始的Beacon检测结果是相对于Anchor局部坐标系的
- 需要转换到地图全局坐标系（使用当前地盘位姿态）
"""

import math
from typing import Dict, Tuple, Any
import logging

logger = logging.getLogger(__name__)


class CoordinateTransformer:
    """坐标变换器 - 处理Anchor局部坐标到地图全局坐标的转换"""
    
    def __init__(self):
        """初始化坐标变换器"""
        pass
    
    @staticmethod
    def transform_beacon_to_global(
        beacon_local_x: float,
        beacon_local_y: float,
        robot_pose: Dict[str, float]
    ) -> Tuple[float, float]:
        """
        将Beacon从Anchor局部坐标系转换到地图全局坐标系
        
        变换原理：
        假设Anchor在地盘上，坐标系定义为：
        - Anchor局部X轴：右侧（相对地盘前向）
        - Anchor局部Y轴：前方（相对地盘朝向）
        
        地盘在地图中的位姿态为 (x_robot, y_robot, yaw_robot)
        Beacon在Anchor局部坐标系中为 (x_local, y_local)
        
        转换公式（2D旋转 + 平移）：
        x_global = x_robot + x_local * cos(yaw_robot) - y_local * sin(yaw_robot)
        y_global = y_robot + x_local * sin(yaw_robot) + y_local * cos(yaw_robot)
        
        Args:
            beacon_local_x: Beacon在Anchor局部坐标系中的X坐标（右侧为正）
            beacon_local_y: Beacon在Anchor局部坐标系中的Y坐标（前方为正）
            robot_pose: 地盘位姿态字典，包含：
                - 'x': 地盘在地图中的X位置
                - 'y': 地盘在地图中的Y位置
                - 'yaw': 地盘的朝向角（弧度或度数）
        
        Returns:
            Tuple[float, float]: 地图全局坐标系中的 (x_global, y_global)
        
        Raises:
            KeyError: 当robot_pose缺少必要字段时抛出
            ValueError: 当输入参数无效时抛出
        """
        try:
            # 提取地盘位姿态
            x_robot = float(robot_pose['x'])
            y_robot = float(robot_pose['y'])
            yaw_robot = float(robot_pose['yaw'])
            
            # 验证输入
            beacon_local_x = float(beacon_local_x)
            beacon_local_y = float(beacon_local_y)
            
            # 如果 yaw 超过 2π，可能是度数，需要转换为弧度
            if abs(yaw_robot) > 2 * math.pi:
                yaw_robot = math.radians(yaw_robot)
            
            # 预计算旋转角的三角函数值
            cos_yaw = math.cos(yaw_robot)
            sin_yaw = math.sin(yaw_robot)
            
            # 应用旋转矩阵和平移
            x_global = x_robot + beacon_local_x * cos_yaw - beacon_local_y * sin_yaw
            y_global = y_robot + beacon_local_x * sin_yaw + beacon_local_y * cos_yaw
            
            return x_global, y_global
            
        except KeyError as e:
            raise KeyError(f"robot_pose 缺少必要字段：{e}")
        except (TypeError, ValueError) as e:
            raise ValueError(f"坐标值转换失败，请确保为有效的数值：{e}")
    
    @staticmethod
    def transform_beacon_heading(
        beacon_local_heading: float,
        robot_yaw: float
    ) -> float:
        """
        将Beacon的相对朝向转换到全局朝向
        
        Args:
            beacon_local_heading: Beacon在Anchor局部坐标系中的朝向角（弧度）
                通常从速度矢量估计：atan2(vy, vx)
            robot_yaw: 地盘/Anchor在地图中的朝向角（弧度）
        
        Returns:
            float: 全局坐标系中的朝向角（弧度），范围 [-π, π]
        """
        try:
            beacon_local_heading = float(beacon_local_heading)
            robot_yaw = float(robot_yaw)
            
            # 简单叠加：全局朝向 = 地盘朝向 + 相对朝向
            global_heading = robot_yaw + beacon_local_heading
            
            # 归一化到 [-π, π] 范围
            while global_heading > math.pi:
                global_heading -= 2 * math.pi
            while global_heading < -math.pi:
                global_heading += 2 * math.pi
            
            return global_heading
            
        except (TypeError, ValueError) as e:
            raise ValueError(f"朝向角转换失败：{e}")
    
    @staticmethod
    def validate_robot_pose(robot_pose: Dict[str, Any]) -> bool:
        """
        验证robot_pose字典是否包含必要的有效字段
        
        Args:
            robot_pose: 要验证的位姿态字典
        
        Returns:
            bool: 如果有效则返回 True，否则返回 False
        """
        required_keys = ['x', 'y', 'yaw']
        
        if not isinstance(robot_pose, dict):
            logger.warning(f"robot_pose 不是字典类型：{type(robot_pose)}")
            return False
        
        for key in required_keys:
            if key not in robot_pose:
                logger.warning(f"robot_pose 缺少必要字段：{key}")
                return False
            
            try:
                float(robot_pose[key])
            except (TypeError, ValueError):
                logger.warning(f"robot_pose['{key}'] 无法转换为浮点数：{robot_pose[key]}")
                return False
        
        return True


def transform_beacon_position(
    filtered_position: Dict[str, float],
    robot_pose: Dict[str, float]
) -> Dict[str, float]:
    """
    便利函数：转换完整的Beacon过滤位置信息
    
    Args:
        filtered_position: 从卡尔曼滤波器得到的结果，包含：
            - 'x': 局部X坐标
            - 'y': 局部Y坐标
            - 'vx': 局部速度X分量（可选）
            - 'vy': 局部速度Y分量（可选）
            - 'confidence': 置信度（可选）
            - 其他字段
        robot_pose: 地盘位姿态，包含 'x', 'y', 'yaw'
    
    Returns:
        Dict[str, float]: 转换后的全局坐标信息，包含：
            - 'x': 全局X坐标
            - 'y': 全局Y坐标
            - 'yaw': 全局朝向（从速度矢量估计）
            - 'vx': 全局速度X分量（可选）
            - 'vy': 全局速度Y分量（可选）
            - 其他原始字段
    """
    transformer = CoordinateTransformer()
    
    # 验证输入
    if not transformer.validate_robot_pose(robot_pose):
        raise ValueError("Invalid robot_pose")
    
    # 转换位置
    x_global, y_global = transformer.transform_beacon_to_global(
        filtered_position.get('x', 0),
        filtered_position.get('y', 0),
        robot_pose
    )
    
    # 构建结果
    result = dict(filtered_position)  # 复制原始字段
    result['x'] = x_global
    result['y'] = y_global
    
    # 如果有速度信息，估计全局朝向
    if 'vx' in filtered_position and 'vy' in filtered_position:
        vx = filtered_position['vx']
        vy = filtered_position['vy']
        
        # 从速度矢量估计局部朝向（相对于Anchor前向）
        local_heading = math.atan2(vy, vx)
        
        # 转换到全局朝向
        global_heading = transformer.transform_beacon_heading(
            local_heading,
            robot_pose['yaw']
        )
        result['yaw'] = global_heading
    
    return result
