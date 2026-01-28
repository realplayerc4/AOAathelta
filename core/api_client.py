"""
API 客户端 - 处理与 AMR 设备的通信
"""
import requests
from typing import Dict, Any
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
                - yaw (float): 朝向角（弧度或度，取决于API返回值）
                - z (float): 高度（通常为0）
                - pitch (float): 俯仰角（通常为0）
                - roll (float): 翻滚角（通常为0）
            
        Raises:
            Exception: 当 API 调用失败时抛出异常
        """
        try:
            response = requests.get(
                f"{self.base_url}/api/core/slam/v1/localization/pose",
                headers=self._get_headers(),
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
                raise Exception("未找到：位姿态端点不存在")
            else:
                raise Exception(f"HTTP 错误：{status_code} - {e.response.text[:100]}")
        except requests.exceptions.JSONDecodeError:
            raise Exception("数据解析失败：API 返回的不是有效的 JSON 格式")
        except Exception as e:
            raise Exception(f"未知错误：{str(e)}")
