#!/usr/bin/env python3
"""
测试脚本 - 验证小车位置 API 调用
"""

import requests
import json
from datetime import datetime

# 配置
API_URL = "http://192.168.11.1:1448/api/core/slam/v1/localization/pose"
HEADERS = {
    'Secret': '123456',
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}

def test_robot_pose_api():
    """测试获取小车位置和朝向"""
    print("=" * 60)
    print("测试小车位置 API")
    print("=" * 60)
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"API 地址: {API_URL}")
    print("-" * 60)
    
    try:
        response = requests.get(
            API_URL,
            headers=HEADERS,
            timeout=5
        )
        
        print(f"HTTP 状态码: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("\n✓ 成功获取数据!")
            print("\n响应数据:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            
            # 检查必要字段
            required_fields = ['x', 'y', 'yaw']
            print("\n字段检查:")
            for field in required_fields:
                if field in data:
                    value = data[field]
                    print(f"  ✓ {field}: {value}")
                else:
                    print(f"  ✗ {field}: 缺失")
            
            # 显示美化后的位置信息
            print("\n小车状态:")
            print(f"  位置 X: {data.get('x', 'N/A'):.3f} m")
            print(f"  位置 Y: {data.get('y', 'N/A'):.3f} m")
            print(f"  朝向角: {data.get('yaw', 'N/A'):.3f} rad")
            if 'pitch' in data:
                print(f"  俯仰角: {data.get('pitch', 'N/A'):.3f} rad")
            if 'roll' in data:
                print(f"  翻滚角: {data.get('roll', 'N/A'):.3f} rad")
                
        else:
            print(f"\n✗ 请求失败!")
            print(f"响应内容: {response.text}")
    
    except requests.Timeout:
        print("\n✗ 超时错误: API 响应超时 (5秒)")
        print("请检查:")
        print("  1. 地盘 IP 地址和端口是否正确")
        print("  2. 网络连接是否正常")
        print("  3. 地盘服务是否正在运行")
    
    except requests.ConnectionError:
        print("\n✗ 连接错误: 无法连接到 API")
        print("请检查:")
        print("  1. 地盘 IP 地址: 192.168.11.1")
        print("  2. 地盘端口: 1448")
        print("  3. 网络连接")
    
    except json.JSONDecodeError:
        print("\n✗ JSON 解析错误: 响应不是有效的 JSON")
        print(f"响应内容: {response.text[:200]}")
    
    except Exception as e:
        print(f"\n✗ 未知错误: {type(e).__name__}")
        print(f"错误信息: {str(e)}")
    
    print("-" * 60)
    print()

if __name__ == '__main__':
    test_robot_pose_api()
