#!/usr/bin/env python3
"""
调试模式 - Beacon 卡尔曼滤波服务
用于诊断串口初始化问题

运行方法:
    python3 beacon_filter_service_debug.py
"""

import os
import sys
import logging
import time

# 日志配置 - 更详细的输出
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

def print_header(title):
    """打印标题"""
    print("")
    print("=" * 70)
    print(f"  {title}")
    print("=" * 70)
    print("")

def check_prerequisites():
    """检查前置条件"""
    print_header("1️⃣ 前置条件检查")
    
    # 检查 Python 版本
    print(f"✓ Python 版本: {sys.version}")
    print("")
    
    # 检查必要的模块
    print("检查必要的 Python 模块...")
    required_modules = {
        'flask': 'Flask',
        'flask_cors': 'Flask-CORS',
        'serial': 'pyserial',
        'numpy': 'NumPy',
        'requests': 'requests',
    }
    
    missing = []
    for module, name in required_modules.items():
        try:
            __import__(module)
            print(f"  ✓ {name}")
        except ImportError:
            print(f"  ✗ {name} (缺失)")
            missing.append(name)
    
    if missing:
        print(f"\n⚠️ 缺少的模块: {', '.join(missing)}")
        print("运行以下命令安装:")
        print(f"  pip3 install {' '.join([m.lower().replace('-', '_') for m in missing])}")
        return False
    
    print("\n✅ 所有模块已安装")
    return True

def check_serial_devices():
    """检查串口设备"""
    print_header("2️⃣ 串口设备检查")
    
    print("检查可用的串口设备...")
    print("")
    
    available_ports = []
    candidates = ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyAMA0', '/dev/ttyS0']
    
    for port in candidates:
        exists = os.path.exists(port)
        status = "✓ 存在" if exists else "✗ 不存在"
        print(f"  {status}: {port}")
        if exists:
            available_ports.append(port)
    
    print("")
    
    if available_ports:
        print(f"✅ 检测到 {len(available_ports)} 个串口设备")
        print(f"📍 将使用: {available_ports[0]}")
        return available_ports[0]
    else:
        print("❌ 未检测到任何串口设备")
        print("\n可能的原因:")
        print("  1. Beacon 设备未连接")
        print("  2. USB 驱动未安装")
        print("  3. 设备文件权限不足")
        print("\n尝试运行:")
        print("  ls -la /dev/tty*")
        print("  lsusb")
        return None

def check_user_permissions():
    """检查用户权限"""
    print_header("3️⃣ 用户权限检查")
    
    current_user = os.getenv('USER', 'unknown')
    print(f"当前用户: {current_user}")
    print("")
    
    # 检查是否在 dialout 组
    try:
        import grp
        dialout_members = grp.getgrall()[grp.getgrnam('dialout').gr_mem]
        if current_user in dialout_members:
            print("✓ 用户在 dialout 组中")
        else:
            print("⚠️ 用户不在 dialout 组中")
            print("  运行以下命令添加:")
            print(f"  sudo usermod -a -G dialout {current_user}")
            print("  然后重新登录 shell")
    except Exception as e:
        print(f"⚠️ 无法检查组成员: {e}")
    
    print("")

def test_serial_connection(port):
    """测试串口连接"""
    print_header(f"4️⃣ 串口连接测试: {port}")
    
    if not os.path.exists(port):
        print(f"❌ 串口设备 {port} 不存在")
        return False
    
    print(f"正在连接 {port}...")
    print("")
    
    try:
        from serial import Serial, SerialException
        
        print("参数设置:")
        print(f"  • 端口: {port}")
        print(f"  • 波特率: 921600")
        print(f"  • 数据位: 8")
        print(f"  • 停止位: 1")
        print(f"  • 奇偶校验: 无")
        print("")
        
        print("正在打开串口...")
        ser = Serial(port, 921600, timeout=2)
        print(f"✓ 成功打开 {port}")
        
        print("")
        print("等待接收数据（5 秒）...")
        
        data_received = False
        start_time = time.time()
        total_bytes = 0
        
        while time.time() - start_time < 5:
            try:
                data = ser.read(1024)
                if data:
                    data_received = True
                    total_bytes += len(data)
                    print(f"  收到 {len(data)} 字节")
                    
                    # 打印前 100 字节
                    if total_bytes <= 100:
                        preview = data.decode('utf-8', errors='ignore')[:80]
                        print(f"  内容预览: {preview}")
                    
                    if total_bytes > 1000:
                        print(f"  已接收 {total_bytes} 字节，停止等待")
                        break
            except Exception as e:
                print(f"  读取错误: {e}")
                break
            
            time.sleep(0.1)
        
        ser.close()
        print(f"✓ 成功关闭 {port}")
        
        print("")
        if data_received:
            print(f"✅ 成功接收数据 ({total_bytes} 字节)")
            print("✅ 串口连接正常")
            return True
        else:
            print("⚠️ 未收到任何数据")
            print("可能原因:")
            print("  1. Beacon 设备未发送数据")
            print("  2. 设备已连接但无数据传输")
            print("  3. 波特率设置不正确")
            return False
    
    except ImportError:
        print("❌ pyserial 未安装")
        print("运行: pip3 install pyserial")
        return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        return False

def test_kalman_filter():
    """测试卡尔曼滤波器初始化"""
    print_header("5️⃣ 卡尔曼滤波器测试")
    
    try:
        from workers.aoa_kalman_filter import MultiTargetKalmanFilter
        
        print("正在初始化卡尔曼滤波器...")
        kalman = MultiTargetKalmanFilter(
            process_noise=0.1,
            measurement_noise=0.5,
            min_confidence=0.3,
            max_human_speed=5.0,
            angle_jump_threshold_deg=90.0
        )
        print("✓ 卡尔曼滤波器初始化成功")
        
        print("")
        print("测试滤波功能...")
        x, y, info = kalman.filter_measurement(
            tag_id=1,
            distance=3.0,
            angle_deg=45,
            timestamp=time.time()
        )
        print(f"✓ 滤波测试成功")
        print(f"  输出位置: ({x:.3f}, {y:.3f})")
        print(f"  置信度: {info.get('confidence', 0):.2f}")
        
        print("")
        print("✅ 卡尔曼滤波器正常")
        return True
    
    except Exception as e:
        print(f"❌ 卡尔曼滤波器初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_service(port):
    """运行实际的服务"""
    print_header("6️⃣ 启动 Beacon 服务")
    
    print(f"使用串口: {port}")
    print("")
    
    try:
        from beacon_filter_service import init_services, state, app
        
        print("正在初始化服务...")
        if init_services(port=port, baudrate=921600):
            print("✅ 服务初始化成功")
            print("")
            print("启动 Flask 服务器...")
            print("📍 Web API: http://127.0.0.1:5001")
            print("📍 Beacon API: http://127.0.0.1:5001/api/beacon")
            print("")
            print("按 Ctrl+C 停止服务")
            print("")
            
            try:
                app.run(
                    host='0.0.0.0',
                    port=5001,
                    debug=False,
                    use_reloader=False,
                    threaded=True
                )
            except KeyboardInterrupt:
                print("\n已停止服务")
                state.running = False
                if state.reader:
                    state.reader.stop()
        else:
            print("❌ 服务初始化失败")
            return False
    
    except Exception as e:
        print(f"❌ 启动失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主程序"""
    print("")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 68 + "║")
    print("║" + "  AOA Beacon 服务 - 调试模式".center(68) + "║")
    print("║" + " " * 68 + "║")
    print("╚" + "=" * 68 + "╝")
    
    try:
        # 第1步: 前置条件检查
        if not check_prerequisites():
            return 1
        
        # 第2步: 检查串口设备
        port = check_serial_devices()
        if not port:
            print("\n⚠️ 未找到串口设备，仍然尝试启动服务...")
            port = '/dev/ttyUSB0'
        
        # 第3步: 检查权限
        check_user_permissions()
        
        # 第4步: 测试串口连接
        if os.path.exists(port):
            test_serial_connection(port)
        
        # 第5步: 测试卡尔曼滤波器
        if not test_kalman_filter():
            return 1
        
        # 第6步: 运行服务
        print_header("准备就绪！")
        print("按 Enter 键启动服务，或按 Ctrl+C 退出...")
        input()
        
        run_service(port)
    
    except KeyboardInterrupt:
        print("\n已取消")
        return 1
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
