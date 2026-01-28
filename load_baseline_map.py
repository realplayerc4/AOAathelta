#!/usr/bin/env python3
"""
地图加载工具
供其他程序加载基线地图和进行坐标转换
"""

import os
import json
from PIL import Image
import numpy as np


class BaselineMap:
    """基线地图加载和处理类"""
    
    def __init__(self, map_dir=None):
        """
        初始化地图加载器
        
        Args:
            map_dir: 地图目录，默认为 maps/baseline
        """
        if map_dir is None:
            PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
            map_dir = os.path.join(PROJECT_ROOT, 'maps', 'baseline')
        
        self.map_dir = map_dir
        self.metadata = None
        self.map_image = None
        self.map_array = None
        
        self._load_map()
    
    def _load_map(self):
        """加载地图文件"""
        # 加载元数据
        metadata_file = os.path.join(self.map_dir, 'baseline_map.json')
        if not os.path.exists(metadata_file):
            raise FileNotFoundError(f"地图元数据文件不存在: {metadata_file}")
        
        with open(metadata_file, 'r') as f:
            self.metadata = json.load(f)
        
        # 加载地图图像
        image_file = os.path.join(self.map_dir, 'baseline_map.png')
        if not os.path.exists(image_file):
            raise FileNotFoundError(f"地图图像文件不存在: {image_file}")
        
        self.map_image = Image.open(image_file)
        self.map_array = np.array(self.map_image)
    
    # 坐标转换方法
    
    def grid_to_real(self, grid_x, grid_y):
        """
        栅格坐标 → 真实坐标
        
        Args:
            grid_x, grid_y: 栅格坐标 (像素)
            
        Returns:
            (real_x, real_y): 真实坐标 (米)
        """
        real_x = self.metadata['origin_x'] + grid_x * self.metadata['resolution']
        real_y = self.metadata['origin_y'] + grid_y * self.metadata['resolution']
        return real_x, real_y
    
    def real_to_grid(self, real_x, real_y):
        """
        真实坐标 → 栅格坐标
        
        Args:
            real_x, real_y: 真实坐标 (米)
            
        Returns:
            (grid_x, grid_y): 栅格坐标 (像素)
        """
        grid_x = int((real_x - self.metadata['origin_x']) / self.metadata['resolution'])
        grid_y = int((real_y - self.metadata['origin_y']) / self.metadata['resolution'])
        return grid_x, grid_y
    
    def is_valid_grid(self, grid_x, grid_y):
        """检查栅格坐标是否在地图范围内"""
        return (0 <= grid_x < self.metadata['width'] and 
                0 <= grid_y < self.metadata['height'])
    
    def get_grid_value(self, grid_x, grid_y):
        """
        获取栅格值
        
        Args:
            grid_x, grid_y: 栅格坐标
            
        Returns:
            grid_value: 栅格值 (0-255)
                0: 障碍物
                128: 未知区
                255: 可通行区域
        """
        if not self.is_valid_grid(grid_x, grid_y):
            return None
        return int(self.map_array[grid_y, grid_x])
    
    def get_grid_value_at_real(self, real_x, real_y):
        """
        获取真实坐标处的栅格值
        
        Args:
            real_x, real_y: 真实坐标 (米)
            
        Returns:
            grid_value: 栅格值
        """
        grid_x, grid_y = self.real_to_grid(real_x, real_y)
        return self.get_grid_value(grid_x, grid_y)
    
    def is_navigable(self, real_x, real_y):
        """检查位置是否可通行（不是障碍物）"""
        value = self.get_grid_value_at_real(real_x, real_y)
        return value is not None and value > 0
    
    def is_obstacle(self, real_x, real_y):
        """检查位置是否是障碍物"""
        value = self.get_grid_value_at_real(real_x, real_y)
        return value == 0
    
    def is_unknown(self, real_x, real_y):
        """检查位置是否未知"""
        value = self.get_grid_value_at_real(real_x, real_y)
        return value == 128
    
    # 地图信息方法
    
    def get_info(self):
        """获取地图信息字典"""
        return {
            'origin_x': self.metadata['origin_x'],
            'origin_y': self.metadata['origin_y'],
            'width': self.metadata['width'],
            'height': self.metadata['height'],
            'resolution': self.metadata['resolution'],
            'real_width': self.metadata['width'] * self.metadata['resolution'],
            'real_height': self.metadata['height'] * self.metadata['resolution'],
            'area': self.metadata['width'] * self.metadata['height'] * self.metadata['resolution']**2
        }
    
    def get_image_base64(self):
        """获取地图图像的 Base64 编码字符串"""
        import base64
        import io
        
        if self.map_image is None:
            raise RuntimeError("地图图像未加载")
        
        # 将图像转换为 PNG 字节
        buffer = io.BytesIO()
        self.map_image.save(buffer, format='PNG')
        image_bytes = buffer.getvalue()
        
        # 转换为 Base64 字符串
        image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        return image_base64
    
    def print_info(self):
        """打印地图信息"""
        info = self.get_info()
        print("=" * 60)
        print("基线地图信息")
        print("=" * 60)
        print(f"原点: ({info['origin_x']:.2f}, {info['origin_y']:.2f}) 米")
        print(f"栅格尺寸: {info['width']} × {info['height']} 像素")
        print(f"分辨率: {info['resolution']:.4f} 米/像素")
        print(f"真实尺寸: {info['real_width']:.2f} × {info['real_height']:.2f} 米")
        print(f"面积: {info['area']:.2f} 平方米")
        print("=" * 60)


def demo():
    """演示地图加载和使用"""
    import sys
    
    try:
        # 加载地图
        print("\n【加载基线地图】")
        baseline_map = BaselineMap()
        print("✓ 地图加载成功\n")
        
        # 打印信息
        baseline_map.print_info()
        print()
        
        # 坐标转换示例
        print("【坐标转换示例】")
        print("-" * 60)
        
        # 示例1：栅格坐标转真实坐标
        grid_x, grid_y = 525, 214
        real_x, real_y = baseline_map.grid_to_real(grid_x, grid_y)
        print(f"栅格({grid_x}, {grid_y}) → 真实({real_x:.2f}, {real_y:.2f})")
        
        # 示例2：真实坐标转栅格坐标
        real_x, real_y = 5.0, 3.0
        grid_x, grid_y = baseline_map.real_to_grid(real_x, real_y)
        print(f"真实({real_x:.2f}, {real_y:.2f}) → 栅格({grid_x}, {grid_y})")
        
        # 示例3：获取位置信息
        real_x, real_y = 0, 0  # 地图中心
        value = baseline_map.get_grid_value_at_real(real_x, real_y)
        navigable = baseline_map.is_navigable(real_x, real_y)
        print(f"位置(0, 0)的栅格值: {value}，可通行: {navigable}")
        
        print("-" * 60)
        print()
        
        return 0
        
    except FileNotFoundError as e:
        print(f"✗ 错误: {e}")
        print("请先运行 'python save_baseline_map.py' 获取地图")
        return 1
    except Exception as e:
        print(f"✗ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == '__main__':
    import sys
    sys.exit(demo())
