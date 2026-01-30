"""
Beacon 卡尔曼滤波服务
自动连接串口，接收 beacon 数据，应用卡尔曼滤波，并通过 Flask API 提供结果
"""

from flask import Flask, jsonify, request
from flask_cors import CORS
import threading
import time
import logging
import re
from collections import deque
from typing import Optional, Dict
from workers.aoa_serial_reader import AOASerialReader
from workers.aoa_kalman_filter import MultiTargetKalmanFilter

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)

# 关闭 werkzeug 的 HTTP 访问日志（例如："GET /api/beacon" 200 -），避免刷屏
# 保留 ERROR 级别以上，便于看到真正的异常
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask(__name__)
CORS(app)

# 全局状态
class BeaconFilterState:
    def __init__(self):
        self.reader: Optional[AOASerialReader] = None
        self.kalman: Optional[MultiTargetKalmanFilter] = None
        self.running = False
        self.lock = threading.Lock()
        
        # 最新的滤波结果
        self.latest_result = {
            'x': 0.0,
            'y': 0.0,
            'velocity_x': 0.0,
            'velocity_y': 0.0,
            'confidence': 0.0,
            'distance': 0.0,
            'angle': 0.0,
            'timestamp': 0.0,
            'initialized': False
        }

        # 最近一段时间的结果缓冲，用于按时间戳取“同一时刻”的结果
        # 存储格式与 latest_result 一致，包含 timestamp（秒）
        self.history = deque(maxlen=200)
        self.history.append(self.latest_result.copy())
        
        # 统计信息
        self.stats = {
            'total_packets': 0,
            'filtered_packets': 0,
            'parse_errors': 0,
            'last_update': 0.0
        }

state = BeaconFilterState()


def get_nearest_result(target_ts: float) -> Dict:
    """从 history 中取与 target_ts 最近的一条结果；若无有效历史则返回 latest_result。"""
    with state.lock:
        if not state.history:
            return state.latest_result.copy()

        best = None
        best_dt = None
        for item in state.history:
            try:
                ts = float(item.get('timestamp', 0.0))
            except Exception:
                continue
            dt = abs(ts - float(target_ts))
            if best is None or dt < best_dt:
                best = item
                best_dt = dt

        return (best or state.latest_result).copy()


def parse_beacon_line(line: str) -> Optional[Dict]:
    """
    解析 beacon 数据行
    格式: "Peer AAA1, Distance 232cm, PDoA Azimuth 67 Elevation 0 Azimuth FoM 96"
    """
    try:
        # 提取距离和角度
        distance_match = re.search(r'Distance\s+(\d+)cm', line)
        azimuth_match = re.search(r'Azimuth\s+(-?\d+)', line)
        peer_match = re.search(r'Peer\s+([A-Z0-9]+)', line)
        
        if distance_match and azimuth_match:
            return {
                'distance': float(distance_match.group(1)) / 100.0,  # 转换为米
                'angle': float(azimuth_match.group(1)),  # 度
                'peer': peer_match.group(1) if peer_match else 'UNKNOWN',
                'timestamp': time.time()
            }
    except Exception as e:
        logger.debug(f"解析失败: {e}")
    
    return None


def beacon_processing_thread():
    """后台线程：处理 beacon 数据并应用卡尔曼滤波"""
    logger.info("🚀 Beacon 处理线程已启动")
    
    text_buffer = ""
    
    while state.running:
        try:
            if not state.reader or not state.reader.running:
                time.sleep(0.1)
                continue
            
            # 从队列获取原始数据
            raw_data = state.reader.get_latest_data(timeout=0.5)
            if not raw_data:
                continue
            
            # 解码并按行处理
            text_buffer += raw_data.decode('utf-8', errors='ignore')
            
            if '\n' in text_buffer:
                lines = text_buffer.split('\n')
                text_buffer = lines.pop()  # 保留最后一行（可能不完整）
                
                for line in lines:
                    state.stats['total_packets'] += 1
                    
                    # 解析 beacon 数据
                    beacon_data = parse_beacon_line(line)
                    
                    if beacon_data:
                        # 应用卡尔曼滤波
                        tag_id = 1  # 默认使用 tag_id = 1
                        
                        try:
                            x, y, info = state.kalman.filter_measurement(
                                tag_id=tag_id,
                                distance=beacon_data['distance'],
                                angle_deg=beacon_data['angle'],
                                timestamp=beacon_data['timestamp']
                            )
                            
                            # 获取完整的滤波器状态（包含速度信息）
                            filter_state = state.kalman.get_filter_state(tag_id)
                            
                            # 更新最新结果
                            result = {
                                'x': float(x),
                                'y': float(y),
                                'velocity_x': float(filter_state.get('vx', 0.0)),
                                'velocity_y': float(filter_state.get('vy', 0.0)),
                                'confidence': float(info.get('confidence', 0.0)),
                                'distance': float(beacon_data['distance']),
                                'angle': float(beacon_data['angle']),
                                'timestamp': float(beacon_data['timestamp']),
                                'initialized': bool(filter_state.get('initialized', False)),
                                'peer': beacon_data['peer']
                            }
                            with state.lock:
                                state.latest_result = result
                                state.history.append(result)
                                state.stats['filtered_packets'] += 1
                                state.stats['last_update'] = time.time()
                            
                            # 每10个数据包打印一次
                            if state.stats['filtered_packets'] % 10 == 0:
                                vx = filter_state.get('vx', 0.0)
                                vy = filter_state.get('vy', 0.0)
                                logger.info(
                                    f"🔦 Beacon滤波: x={x:.3f}m, y={y:.3f}m, "
                                    f"速度=({vx:.2f}, {vy:.2f})m/s, "
                                    f"置信度={info.get('confidence', 0):.2f}"
                                )
                        
                        except Exception as e:
                            logger.error(f"卡尔曼滤波错误: {e}")
                            state.stats['parse_errors'] += 1
        
        except Exception as e:
            logger.error(f"处理线程错误: {e}")
            time.sleep(0.1)
    
    logger.info("Beacon 处理线程已停止")


def init_services(port: str = '/dev/ttyUSB1', baudrate: int = 921600):
    """初始化串口和卡尔曼滤波器"""
    try:
        # 初始化卡尔曼滤波器
        state.kalman = MultiTargetKalmanFilter(
            process_noise=0.1,
            measurement_noise=0.5,
            min_confidence=0.3,
            max_human_speed=5.0,
            angle_jump_threshold_deg=90.0
        )
        logger.info("✅ 卡尔曼滤波器初始化完成")
        
        # 初始化串口读取器
        state.reader = AOASerialReader(port=port, baudrate=baudrate)
        if state.reader.connect():
            state.reader.start()
            logger.info(f"✅ 串口 {port} 连接成功，开始接收 Beacon 数据")
        else:
            logger.warning(f"⚠️ 串口连接失败: {port}")
            logger.warning(f"   • 检查硬件是否连接")
            logger.warning(f"   • 运行: ls -la /dev/tty* 查看可用设备")
            logger.warning(f"   • Beacon 数据将显示为 (0, 0)")
            logger.warning(f"   • 服务将继续运行但无实时定位数据")
        
        # 启动处理线程
        state.running = True
        thread = threading.Thread(target=beacon_processing_thread, daemon=True)
        thread.start()
        logger.info("✅ Beacon 处理线程已启动")
        
        return True
    
    except Exception as e:
        logger.error(f"❌ 初始化失败: {e}")
        return False


# ==================== Flask 路由 ====================

@app.route('/')
def index():
    """服务信息"""
    return jsonify({
        'service': 'Beacon Kalman Filter Service',
        'status': 'running' if state.running else 'stopped',
        'endpoints': {
            '/api/beacon': 'GET - 获取最新的滤波后 beacon 数据',
            '/api/stats': 'GET - 获取统计信息',
            '/api/status': 'GET - 获取服务状态'
        }
    })


@app.route('/api/beacon')
def get_beacon():
    """获取滤波后 beacon 数据

    - 默认：返回最新一条结果
    - 可选：/api/beacon?timestamp=1700000000.123  返回与该时间戳最近的结果
    """
    ts = request.args.get('timestamp', type=float)
    if ts is not None:
        return jsonify(get_nearest_result(ts))

    with state.lock:
        return jsonify(state.latest_result)


@app.route('/api/stats')
def get_stats():
    """获取统计信息"""
    with state.lock:
        stats = state.stats.copy()
    
    # 添加实时信息
    stats['queue_size'] = state.reader.raw_data_queue.qsize() if state.reader else 0
    stats['uptime'] = time.time() - stats.get('last_update', time.time()) if stats.get('last_update') else 0
    
    return jsonify(stats)


@app.route('/api/status')
def get_status():
    """获取服务状态"""
    return jsonify({
        'running': state.running,
        'reader_connected': state.reader is not None and state.reader.running,
        'kalman_initialized': state.kalman is not None,
        'beacon_initialized': state.latest_result['initialized'],
        'last_update': state.stats.get('last_update', 0),
        'timestamp': time.time()
    })


# ==================== 主程序 ====================

if __name__ == '__main__':
    logger.info("=" * 60)
    logger.info("🔦 Beacon 卡尔曼滤波服务")
    logger.info("=" * 60)
    
    # 自动检测可用的串口设备
    import os
    port = '/dev/ttyUSB0'  # 默认使用 USB0
    
    # 检查可用的串口
    available_ports = []
    for i in range(10):
        test_port = f'/dev/ttyUSB{i}'
        if os.path.exists(test_port):
            available_ports.append(test_port)
    
    if available_ports:
        port = available_ports[0]
        logger.info(f"🔍 检测到可用串口: {available_ports}")
        logger.info(f"📍 使用串口: {port}")
    else:
        logger.warning("⚠️ 未检测到USB串口设备，仍尝试连接 /dev/ttyUSB0")
    
    # 初始化服务
    if init_services(port=port, baudrate=921600):
        logger.info("✅ 所有服务初始化完成")
        
        # 启动 Flask 服务器
        try:
            app.run(
                host='127.0.0.1',
                port=5001,  # 使用 5001 端口避免与 web_app.py 冲突
                debug=False,  # 保持为False，防止debug信息输出
                use_reloader=False
            )
        except KeyboardInterrupt:
            logger.info("\n收到停止信号...")
        finally:
            state.running = False
            if state.reader:
                state.reader.stop()
            logger.info("服务已停止")
    else:
        logger.error("❌ 初始化失败，无法启动服务")
