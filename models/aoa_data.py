"""
AOA (Angle of Arrival) 数据模型
包含 ANCHER（基站）和 TAG（标签）数据
"""
from dataclasses import dataclass, field
from typing import Optional, List
from datetime import datetime


@dataclass
class AnchorData:
    """ANCHER（基站）数据结构"""
    role: int
    anchor_id: int
    local_time: int
    system_time: int
    voltage: int  # 单位：mV
    
    @classmethod
    def from_bytes(cls, data: bytes, start_index: int = 0) -> 'AnchorData':
        """
        从字节数据创建 ANCHER 数据
        
        Args:
            data: 字节数据
            start_index: 数据起始位置（ANCHER 角色的字节位置）
            
        Returns:
            AnchorData 实例
        """
        # 字节位置相对于完整消息的位置
        # data[3-4]: 数据长度 (不使用，已知长度)
        role = data[start_index]  # data[4]
        anchor_id = data[start_index + 1]  # data[5]
        
        # 地方时间 uint32，小端序
        local_time = (data[start_index + 2] | 
                     (data[start_index + 3] << 8) |
                     (data[start_index + 4] << 16) |
                     (data[start_index + 5] << 24))
        
        # 系统时间 uint32，小端序
        system_time = (data[start_index + 6] |
                      (data[start_index + 7] << 8) |
                      (data[start_index + 8] << 16) |
                      (data[start_index + 9] << 24))
        
        # 电压 uint16，小端序
        voltage = (data[start_index + 14] | (data[start_index + 15] << 8))
        
        return cls(
            role=role,
            anchor_id=anchor_id,
            local_time=local_time,
            system_time=system_time,
            voltage=voltage
        )


@dataclass
class TagData:
    """TAG（标签）数据结构"""
    tag_id: int
    distance: int  # 单位：mm
    angle: float  # 单位：度数
    fp_db: int  # 第一路径信号强度
    rx_db: int  # 接收信号强度
    
    @classmethod
    def from_bytes(cls, data: bytes, start_index: int = 0) -> 'TagData':
        """
        从字节数据创建 TAG 数据
        
        Args:
            data: 字节数据
            start_index: 数据起始位置（TAG ID 的字节位置）
            
        Returns:
            TagData 实例
        """
        tag_id = data[start_index]  # data[22]
        
        # 距离 int24（24位有符号整数），小端序
        distance_raw = (data[start_index + 1] |
                       (data[start_index + 2] << 8) |
                       (data[start_index + 3] << 16))
        # 处理有符号24位数
        if distance_raw & 0x800000:
            distance_raw |= 0xFF000000
        distance = distance_raw & 0xFFFFFFFF
        # 转换为有符号整数
        if distance & 0x80000000:
            distance = distance - 0x100000000
        
        # 角度 int16（16位有符号整数），小端序，数值是角度的100倍
        angle_raw = (data[start_index + 4] | (data[start_index + 5] << 8))
        # 处理有符号16位数
        if angle_raw & 0x8000:
            angle_raw |= 0xFFFF0000
        angle_raw = angle_raw & 0xFFFFFFFF
        if angle_raw & 0x80000000:
            angle_raw = angle_raw - 0x100000000
        angle = angle_raw / 100.0
        
        fp_db = data[start_index + 6]
        rx_db = data[start_index + 7]
        
        return cls(
            tag_id=tag_id,
            distance=distance,
            angle=angle,
            fp_db=fp_db,
            rx_db=rx_db
        )


@dataclass
class AOAFrame:
    """完整的 AOA 数据帧（0x55 协议）"""
    frame_id: int = 0  # 帧序号
    timestamp: Optional[datetime] = None
    header: int = 0x55
    function_code: int = 0
    anchor_data: Optional[AnchorData] = None
    tag_data: Optional[TagData] = None
    checksum: int = 0
    is_valid: bool = False
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @classmethod
    def from_bytes(cls, data: bytes, frame_id: int = 0) -> 'AOAFrame':
        """
        从字节数据创建完整的 AOA 帧
        
        协议结构（33 字节）：
        - 字节 0: 头部 0x55
        - 字节 1: 功能码
        - 字节 2-21: ANCHER 数据 (20 字节)
        - 字节 22-31: TAG 数据 (10 字节)
        - 字节 32: 校验和
        
        Args:
            data: 字节数据（必须是 33 字节）
            frame_id: 帧序号
            
        Returns:
            AOAFrame 实例
        """
        if len(data) < 33:
            raise ValueError(f"数据长度不足，期望 33 字节，实际 {len(data)} 字节")
        
        frame = cls(frame_id=frame_id)
        frame.header = data[0]
        frame.function_code = data[1]
        
        # 解析 ANCHER 数据（从字节 4 开始，即 data[4]）
        frame.anchor_data = AnchorData.from_bytes(data, start_index=4)
        
        # 解析 TAG 数据（从字节 22 开始，即 data[22]）
        frame.tag_data = TagData.from_bytes(data, start_index=22)
        
        frame.checksum = data[32]
        frame.is_valid = cls._verify_checksum(data)
        
        return frame
    
    @staticmethod
    def _verify_checksum(data: bytes) -> bool:
        """
        验证校验和（前 32 字节的和）
        
        Args:
            data: 字节数据
            
        Returns:
            校验和是否有效
        """
        checksum = sum(data[:32]) & 0xFF
        return checksum == data[32]
    
    def get_summary(self) -> dict:
        """获取数据摘要"""
        return {
            'frame_id': self.frame_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'is_valid': self.is_valid,
            'anchor_id': self.anchor_data.anchor_id if self.anchor_data else None,
            'anchor_role': self.anchor_data.role if self.anchor_data else None,
            'anchor_local_time': self.anchor_data.local_time if self.anchor_data else None,
            'anchor_system_time': self.anchor_data.system_time if self.anchor_data else None,
            'tag_id': self.tag_data.tag_id if self.tag_data else None,
            'distance_mm': self.tag_data.distance if self.tag_data else None,
            'angle_degrees': self.tag_data.angle if self.tag_data else None,
            'voltage_mv': self.anchor_data.voltage if self.anchor_data else None,
        }


@dataclass
class AOAPosition:
    """
    标签相对于 ANCHER 的位置信息
    """
    anchor_id: int
    tag_id: int
    distance: float  # 单位：米
    angle: float  # 单位：度数
    timestamp: datetime = field(default_factory=datetime.now)
    confidence: float = 1.0  # 信心度 0-1
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            'anchor_id': self.anchor_id,
            'tag_id': self.tag_id,
            'distance': self.distance,
            'angle': self.angle,
            'timestamp': self.timestamp.isoformat(),
            'confidence': self.confidence
        }
