"""
设备数据模型
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any


@dataclass
class Device:
    """AMR 设备数据模型"""
    id: str
    name: str
    status: str
    sn: Optional[str] = None
    ip_address: Optional[str] = None
    battery_level: Optional[float] = None
    location: Optional[str] = None
    position_x: Optional[float] = None
    position_y: Optional[float] = None
    speed: Optional[float] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Device':
        """
        从 API 响应字典创建 Device 对象
        
        Args:
            data: API 返回的 JSON 字典
            
        Returns:
            Device 实例
        """
        return cls(
            id=str(data.get('id', data.get('deviceId', 'N/A'))),
            name=data.get('name', data.get('deviceName', 'Unknown')),
            status=data.get('status', data.get('state', 'Unknown')),
            sn=data.get('sn', data.get('serialNumber', None)),
            ip_address=data.get('ip', data.get('ipAddress', None)),
            battery_level=data.get('battery', data.get('batteryLevel', None)),
            location=data.get('location', data.get('area', None)),
            position_x=data.get('x', data.get('posX', None)),
            position_y=data.get('y', data.get('posY', None)),
            speed=data.get('speed', data.get('velocity', None)),
            raw_data=data
        )
