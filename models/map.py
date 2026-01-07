"""
地图数据模型
"""
from dataclasses import dataclass
from typing import Optional, Dict, Any, List


@dataclass
class Map:
    """AMR 地图数据模型"""
    id: str
    name: str
    state: Optional[str] = None  # 地图状态：finished, failed, cancelled
    description: Optional[str] = None
    created_at: Optional[str] = None
    modified_at: Optional[str] = None
    size: Optional[str] = None
    resolution: Optional[float] = None  # 单个像素的大小，通常为 0.05 m/pixel
    grid_origin_x: Optional[float] = None  # 左下角的X坐标
    grid_origin_y: Optional[float] = None  # 左下角的Y坐标
    thumbnail_url: Optional[str] = None  # 缩略图 URL
    image_url: Optional[str] = None  # 完整图片 URL
    continue_mapping: Optional[bool] = None
    raw_data: Optional[Dict[str, Any]] = None
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Map':
        """
        从 API 响应字典创建 Map 对象
        
        Args:
            data: API 返回的 JSON 字典
            
        Returns:
            Map 实例
        """
        from datetime import datetime
        
        map_id = str(data.get('id', 'N/A'))
        state = data.get('state', 'unknown')
        
        # 生成地图名称：使用ID和状态
        name = f"地图 {map_id} ({state})"
        
        # 转换时间戳为可读格式
        start_time = data.get('start_time')
        created_at = None
        if start_time:
            try:
                created_at = datetime.fromtimestamp(start_time).strftime('%Y-%m-%d %H:%M:%S')
            except:
                created_at = str(start_time)
        
        end_time = data.get('end_time')
        modified_at = None
        if end_time:
            try:
                modified_at = datetime.fromtimestamp(end_time).strftime('%Y-%m-%d %H:%M:%S')
            except:
                modified_at = str(end_time)
        
        return cls(
            id=map_id,
            name=name,
            state=state,
            description=f"继续建图: {data.get('continue_mapping', False)}" if data.get('continue_mapping') is not None else None,
            created_at=created_at,
            modified_at=modified_at,
            size=None,
            resolution=data.get('grid_resolution'),
            grid_origin_x=data.get('grid_origin_x'),
            grid_origin_y=data.get('grid_origin_y'),
            thumbnail_url=data.get('thumbnail_url'),
            image_url=data.get('image_url'),
            continue_mapping=data.get('continue_mapping'),
            raw_data=data
        )
