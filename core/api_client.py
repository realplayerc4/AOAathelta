"""
API 客户端 - 处理与 AMR 设备的通信
"""
import requests
from typing import Dict, Any
import struct
import config


class APIClient:
    """AMR 设备 API 客户端"""
    
    def __init__(self):
        self.base_url = config.API_BASE_URL
        self.timeout = config.API_TIMEOUT
        self.secret = config.API_SECRET
        self.device_sn = config.DEVICE_SN
    
    def _get_headers(self) -> Dict[str, str]:
        """
        获取 API 请求头
        
        Returns:
            包含认证信息的请求头字典
        """
        return {
            'Secret': self.secret,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    
    def fetch_device_info(self) -> Dict[str, Any]:
        """
        获取设备信息
        
        Returns:
            dict: API 返回的 JSON 数据
            
        Raises:
            Exception: 当 API 调用失败时抛出异常
        """
        try:
            # 尝试作为查询参数传递 SN
            params = {'sn': self.device_sn} if self.device_sn else {}
            
            response = requests.get(
                config.API_DEVICE_INFO,
                headers=self._get_headers(),
                params=params,
                timeout=self.timeout
            )
            
            # 检查 HTTP 状态码
            response.raise_for_status()
            
            # 返回 JSON 数据
            return response.json()
            
        except requests.Timeout:
            raise Exception(f"请求超时：API 未在 {self.timeout} 秒内响应")
        except requests.ConnectionError:
            raise Exception(f"连接失败：无法连接到 {self.base_url}")
        except requests.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:
                raise Exception("认证失败：Secret 密钥无效")
            elif status_code == 403:
                raise Exception("权限不足：无权访问此资源")
            elif status_code == 404:
                raise Exception("未找到：设备或端点不存在")
            else:
                raise Exception(f"HTTP 错误：{status_code} - {e.response.text[:100]}")
        except requests.exceptions.JSONDecodeError:
            raise Exception("数据解析失败：API 返回的不是有效的 JSON 格式")
        except Exception as e:
            raise Exception(f"未知错误：{str(e)}")
    
    def fetch_maps(self) -> Dict[str, Any]:
        """
        获取 AMR 内所有地图列表
        
        Returns:
            dict: API 返回的地图列表 JSON 数据（包装后的字典格式）
            
        Raises:
            Exception: 当 API 调用失败时抛出异常
        """
        try:
            response = requests.get(
                f"{self.base_url}/mappings/",
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            # 检查 HTTP 状态码
            response.raise_for_status()
            
            # 获取 JSON 数据
            data = response.json()
            
            # 如果返回的是列表，包装成字典格式
            if isinstance(data, list):
                return {"mappings": data}
            
            # 如果已经是字典，直接返回
            return data
            
        except requests.Timeout:
            raise Exception(f"请求超时：API 未在 {self.timeout} 秒内响应")
        except requests.ConnectionError:
            raise Exception(f"连接失败：无法连接到 {self.base_url}")
        except requests.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:
                raise Exception("认证失败：Secret 密钥无效")
            elif status_code == 403:
                raise Exception("权限不足：无权访问此资源")
            elif status_code == 404:
                raise Exception("未找到：地图端点不存在")
            else:
                raise Exception(f"HTTP 错误：{status_code} - {e.response.text[:100]}")
        except requests.exceptions.JSONDecodeError:
            raise Exception("数据解析失败：API 返回的不是有效的 JSON 格式")
        except Exception as e:
            raise Exception(f"未知错误：{str(e)}")
    
    def fetch_pose(self) -> Dict[str, Any]:
        """
        获取地盘的当前位姿态 - 在地图全局坐标系中的位置和朝向
        
        Returns:
            dict: 包含以下字段的位姿态信息
                - x (float): 地图坐标系中的X位置
                - y (float): 地图坐标系中的Y位置
                - yaw (float): 朝向角（弧度）
                - z (float): 高度（通常为0）
                - pitch (float): 俯仰角（通常为0）
                - roll (float): 翻滚角（通常为0）
            
        Raises:
            Exception: 当 API 调用失败时抛出异常
        """
        try:
            # 构建完整的URL
            url = f"{self.base_url}/api/core/slam/v1/localization/pose"
            
            response = requests.get(
                url,
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            # 检查 HTTP 状态码
            response.raise_for_status()
            
            # 获取 JSON 数据
            data = response.json()
            
            # 处理不同的返回格式
            # 格式1: {"pose": {"x": ..., "y": ..., "yaw": ...}}
            if isinstance(data, dict) and 'pose' in data:
                pose_data = data['pose']
            # 格式2: {"x": ..., "y": ..., "yaw": ...}
            elif isinstance(data, dict) and 'x' in data:
                pose_data = data
            else:
                raise Exception(f"未知的位姿态数据格式: {data}")
            
            # 确保必需的字段存在，添加默认值
            result = {
                'x': float(pose_data.get('x', 0)),
                'y': float(pose_data.get('y', 0)),
                'yaw': float(pose_data.get('yaw', 0)),
                'z': float(pose_data.get('z', 0)),
                'pitch': float(pose_data.get('pitch', 0)),
                'roll': float(pose_data.get('roll', 0))
            }
            
            return result
            
        except requests.Timeout:
            raise Exception(f"请求超时：API 未在 {self.timeout} 秒内响应")
        except requests.ConnectionError:
            raise Exception(f"连接失败：无法连接到 {self.base_url}")
        except requests.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:
                raise Exception("认证失败：Secret 密钥无效")
            elif status_code == 403:
                raise Exception("权限不足：无权访问此资源")
            elif status_code == 404:
                raise Exception("未找到：位姿态端点不存在")
            else:
                raise Exception(f"HTTP 错误：{status_code} - {e.response.text[:100]}")
        except requests.exceptions.JSONDecodeError:
            raise Exception("数据解析失败：API 返回的不是有效的 JSON 格式")
        except Exception as e:
            raise Exception(f"未知错误：{str(e)}")
    
    def fetch_explore_map(self) -> Dict[str, Any]:
        """
        获取实时栅格地图（探索地图）
        
        Returns:
            dict: 包含元数据和地图数据的字典，格式：
                {
                    'metadata': {
                        'origin_x': float,
                        'origin_y': float,
                        'width': int,
                        'height': int,
                        'resolution': float
                    },
                    'data': bytes  # 栅格数据
                }
        
        Raises:
            Exception: 当 API 调用失败时抛出异常
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/core/slam/v1/maps/explore",
                headers=self._get_headers(),
                timeout=self.timeout
            )
            
            # 检查 HTTP 状态码
            response.raise_for_status()
            
            # 解析二进制数据
            data = response.content
            if len(data) < 36:
                raise Exception(f"地图数据过短：{len(data)} 字节，至少需要 36 字节")
            
            # 解析元数据（前32字节）
            origin_x = struct.unpack('<f', data[0:4])[0]
            origin_y = struct.unpack('<f', data[4:8])[0]
            width = struct.unpack('<I', data[8:12])[0]
            height = struct.unpack('<I', data[12:16])[0]
            resolution = struct.unpack('<f', data[16:20])[0]
            
            # 解析数据长度（32-36字节）
            data_length = struct.unpack('<I', data[32:36])[0]
            
            # 提取地图数据
            map_data = data[36:36+data_length]
            
            return {
                'metadata': {
                    'origin_x': origin_x,
                    'origin_y': origin_y,
                    'width': width,
                    'height': height,
                    'resolution': resolution
                },
                'data': map_data
            }
            
        except requests.Timeout:
            raise Exception(f"请求超时：API 未在 {self.timeout} 秒内响应")
        except requests.ConnectionError:
            raise Exception(f"连接失败：无法连接到 {self.base_url}")
        except requests.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:
                raise Exception("认证失败：Secret 密钥无效")
            elif status_code == 403:
                raise Exception("权限不足：无权访问此资源")
            elif status_code == 404:
                raise Exception("未找到：地图端点不存在")
            else:
                raise Exception(f"HTTP 错误：{status_code} - {e.response.text[:100]}")
        except struct.error as e:
            raise Exception(f"二进制数据解析失败：{e}")
        except Exception as e:
            raise Exception(f"未知错误：{str(e)}")
