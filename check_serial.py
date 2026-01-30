#!/usr/bin/env python3
"""
串口诊断脚本 - 检查树莓派上的串口设备状态
"""

import os
import subprocess
import sys

def run_cmd(cmd, show_output=True):
    """运行命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        output = result.stdout.strip()
        if show_output and output:
            print(output)
        return output
    except Exception as e:
        print(f"❌ 执行命令失败: {e}")
        return ""

def check_serial_devices():
    """检查可用的串口设备"""
    print("=" * 60)
    print("🔍 串口设备检查")
    print("=" * 60)
    print("")
    
    print("📋 可用的串口设备:")
    output = run_cmd("ls -la /dev/tty* 2>/dev/null | grep -E 'USB|ACM|AMA|S0'")
    if not output:
        print("  ⚠️ 未找到标准的串口设备")
    print("")
    
    print("📊 USB 设备信息:")
    output = run_cmd("lsusb 2>/dev/null")
    if output:
        print(output)
    else:
        print("  ⚠️ 无法获取 USB 设备信息")
    print("")
    
    print("🔌 检查 /dev/ttyUSB* 设备:")
    found_any = False
    for i in range(5):
        port = f'/dev/ttyUSB{i}'
        if os.path.exists(port):
            print(f"  ✓ {port} 存在")
            found_any = True
        else:
            print(f"  ✗ {port} 不存在")
    
    if not found_any:
        print("  ℹ️ 检查其他可能的串口设备...")
        for port in ['/dev/ttyACM0', '/dev/ttyAMA0', '/dev/ttyS0']:
            if os.path.exists(port):
                print(f"  ✓ {port} 存在（备选设备）")
    
    print("")

def check_permissions():
    """检查用户权限"""
    print("=" * 60)
    print("👤 权限检查")
    print("=" * 60)
    print("")
    
    print("📝 当前用户信息:")
    run_cmd("whoami")
    print("")
    
    print("👥 用户所属的组:")
    run_cmd("groups")
    print("")
    
    print("🔐 检查 dialout 组成员:")
    output = run_cmd("getent group dialout")
    if output:
        print(f"  {output}")
    else:
        print("  ⚠️ dialout 组不存在或为空")
    print("")
    
    print("⚠️ 注意: 如果当前用户不在 dialout 组中，需要运行:")
    print("  sudo usermod -a -G dialout $USER")
    print("  然后重新登录 shell")
    print("")

def check_serial_settings():
    """检查串口配置"""
    print("=" * 60)
    print("⚙️ 串口配置检查")
    print("=" * 60)
    print("")
    
    print("📡 检查是否支持 921600 波特率:")
    cmd = "stty -F /dev/null 921600 speed 2>/dev/null && echo '✓ 支持' || echo '⚠️ 可能不支持'"
    run_cmd(cmd)
    print("")
    
    print("🔧 尝试列出可用的波特率:")
    run_cmd("stty --help 2>/dev/null | grep -A 20 'speed'")
    print("")

def test_serial_connection(port='/dev/ttyUSB0', timeout=2):
    """测试串口连接"""
    print("=" * 60)
    print(f"🧪 串口连接测试: {port}")
    print("=" * 60)
    print("")
    
    if not os.path.exists(port):
        print(f"❌ 设备 {port} 不存在")
        print("")
        return
    
    print(f"📌 尝试连接 {port}...")
    
    # 使用 Python pyserial 测试
    try:
        import serial
        print("  ✓ pyserial 已安装")
        
        try:
            ser = serial.Serial(port, 921600, timeout=timeout)
            print(f"  ✓ 成功打开 {port}")
            
            # 读取数据
            print(f"  📖 尝试读取数据（等待 {timeout} 秒）...")
            data = ser.read(100)
            
            if data:
                print(f"  ✓ 收到 {len(data)} 字节数据")
                print(f"    数据预览: {data[:50]}")
            else:
                print(f"  ⚠️ 未收到任何数据（可能设备未发送数据）")
            
            ser.close()
            print(f"  ✓ 成功关闭 {port}")
        
        except serial.SerialException as e:
            print(f"  ❌ 串口错误: {e}")
        except Exception as e:
            print(f"  ❌ 错误: {e}")
    
    except ImportError:
        print("  ⚠️ pyserial 未安装")
        print("     运行: pip3 install pyserial")
    
    print("")

def main():
    """主函数"""
    print("")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 58 + "║")
    print("║" + "  AOA Beacon - 串口诊断工具".center(58) + "║")
    print("║" + " " * 58 + "║")
    print("╚" + "=" * 58 + "╝")
    print("")
    
    try:
        # 执行检查
        check_serial_devices()
        check_permissions()
        check_serial_settings()
        
        # 选择第一个可用的端口进行测试
        for port in ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyAMA0']:
            if os.path.exists(port):
                test_serial_connection(port)
                break
        else:
            print("=" * 60)
            print("⚠️ 未找到可用的串口设备进行测试")
            print("=" * 60)
            print("")
    
    except KeyboardInterrupt:
        print("\n已取消诊断")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 诊断出错: {e}")
        sys.exit(1)
    
    print("=" * 60)
    print("✅ 诊断完成")
    print("=" * 60)
    print("")
    print("💡 建议:")
    print("  1. 如果串口设备不存在，检查硬件连接")
    print("  2. 如果权限不足，运行: sudo usermod -a -G dialout $USER")
    print("  3. 如果无法连接，尝试不同的串口设备")
    print("  4. 检查 Beacon 设备是否正常工作")
    print("")

if __name__ == '__main__':
    main()
