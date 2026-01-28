#!/usr/bin/env python3
"""
AOA Web UI - 环境检查脚本
检查是否已安装所有必要的依赖和文件
"""

import os
import sys
import subprocess
from pathlib import Path

def check_python_version():
    """检查 Python 版本"""
    version = sys.version_info
    print(f"✓ Python 版本: {version.major}.{version.minor}.{version.micro}")
    if version.major < 3 or (version.major == 3 and version.minor < 6):
        print("✗ 需要 Python 3.6 或更高版本")
        return False
    return True

def check_packages():
    """检查是否已安装必要的包"""
    packages = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'pyserial': 'pyserial',
        'requests': 'requests',
        'numpy': 'numpy'
    }
    
    missing = []
    for module, name in packages.items():
        try:
            __import__(module)
            print(f"✓ {name} 已安装")
        except ImportError:
            print(f"✗ {name} 未安装")
            missing.append(name)
    
    return len(missing) == 0, missing

def check_files():
    """检查是否存在必要的文件"""
    required_files = [
        'web_app.py',
        'templates/index.html',
        'static/css/style.css',
        'static/js/map.js',
        'core/api_client.py',
        'workers/aoa_kalman_filter.py',
        'workers/aoa_serial_reader.py',
        'coordinate_transform.py',
        'load_baseline_map.py',
        'maps/baseline/baseline_map.json'
    ]
    
    missing = []
    for file in required_files:
        if Path(file).exists():
            print(f"✓ {file}")
        else:
            print(f"✗ {file} 缺失")
            missing.append(file)
    
    return len(missing) == 0, missing

def main():
    print("=" * 60)
    print("AOA Web UI - 环境检查")
    print("=" * 60)
    print()
    
    # 检查 Python 版本
    print("【1】检查 Python 版本")
    print("-" * 60)
    py_ok = check_python_version()
    print()
    
    # 检查依赖包
    print("【2】检查依赖包")
    print("-" * 60)
    pkg_ok, missing_pkgs = check_packages()
    print()
    
    # 检查文件
    print("【3】检查项目文件")
    print("-" * 60)
    file_ok, missing_files = check_files()
    print()
    
    # 总结
    print("=" * 60)
    print("【检查结果】")
    print("=" * 60)
    
    all_ok = py_ok and pkg_ok and file_ok
    
    if py_ok:
        print("✓ Python 版本满足要求")
    else:
        print("✗ Python 版本不满足要求")
    
    if pkg_ok:
        print("✓ 所有依赖包已安装")
    else:
        print(f"✗ 缺少依赖包: {', '.join(missing_pkgs)}")
        print()
        print("  安装命令:")
        print(f"    pip3 install {' '.join(missing_pkgs)}")
        print("  或者：")
        print("    pip3 install -r requirements.txt")
    
    if file_ok:
        print("✓ 所有必要的文件都存在")
    else:
        print(f"✗ 缺少文件: {', '.join(missing_files)}")
    
    print()
    
    if all_ok:
        print("=" * 60)
        print("✓✓✓ 环境检查通过！")
        print("=" * 60)
        print()
        print("可以运行以下命令启动应用：")
        print("  python3 web_app.py")
        print()
        print("然后在浏览器中打开：")
        print("  http://127.0.0.1:5000")
        print()
        return 0
    else:
        print("=" * 60)
        print("✗✗✗ 环境检查失败")
        print("=" * 60)
        print()
        print("请先安装缺少的依赖和文件")
        return 1

if __name__ == '__main__':
    sys.exit(main())
