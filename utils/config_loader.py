"""
工具函数 - 加载配置文件
"""
import os
from pathlib import Path


def load_topics_from_file(filepath: str) -> list[str]:
    """
    从文件中加载要监听的话题列表
    
    Args:
        filepath: 话题列表文件路径
        
    Returns:
        话题名称列表（已去除空行和注释）
    """
    topics = []
    
    if not os.path.exists(filepath):
        print(f"警告：话题文件不存在: {filepath}")
        return topics
    
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 跳过空行和注释行
                if line and not line.startswith('#'):
                    topics.append(line)
    except Exception as e:
        print(f"错误：读取话题文件失败: {e}")
    
    return topics


def save_topics_to_file(filepath: str, topics: list[str]) -> bool:
    """
    保存话题列表到文件
    
    Args:
        filepath: 目标文件路径
        topics: 话题列表
        
    Returns:
        是否保存成功
    """
    try:
        with open(filepath, 'w', encoding='utf-8') as f:
            for topic in topics:
                f.write(topic + '\n')
        return True
    except Exception as e:
        print(f"错误：保存话题文件失败: {e}")
        return False
