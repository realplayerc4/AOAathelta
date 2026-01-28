"""
Flask Web 应用 - AOA 定位系统可视化界面
支持实时 Beacon 定位、地图显示、矩形框绘制和区域检测
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import threading
import time
import logging
import json
import math
from pathlib import Path
from typing import Dict, List, Tuple
import numpy as np

# 导入项目模块
from core.api_client import APIClient

# 日志配置
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

app = Flask(__name__)
CORS(app)

# ==================== 坐标转换和平滑处理函数 ====================

def smooth_beacon_globe(beacon_globe_raw):
    """
    对Beacon全局坐标进行指数移动平均（EMA）平滑处理
    减少漂移问题，使显示更稳定
    
    Args:
        beacon_globe_raw: 原始的beacon_globe {'x': float, 'y': float}
    
    Returns:
        dict: 平滑后的坐标 {'x': float, 'y': float}
    """
    global smoothed_beacon_globe, beacon_globe_init, BEACON_GLOBE_EMA_ALPHA
    
    if not beacon_globe_init:
        # 第一次初始化
        smoothed_beacon_globe = {
            'x': float(beacon_globe_raw.get('x', 0)),
            'y': float(beacon_globe_raw.get('y', 0))
        }
        beacon_globe_init = True
        return smoothed_beacon_globe.copy()
    
    # 指数移动平均：新值 = alpha * 原始值 + (1-alpha) * 平滑值
    alpha = BEACON_GLOBE_EMA_ALPHA
    raw_x = float(beacon_globe_raw.get('x', 0))
    raw_y = float(beacon_globe_raw.get('y', 0))
    
    smoothed_beacon_globe['x'] = alpha * raw_x + (1 - alpha) * smoothed_beacon_globe['x']
    smoothed_beacon_globe['y'] = alpha * raw_y + (1 - alpha) * smoothed_beacon_globe['y']
    
    return smoothed_beacon_globe.copy()

def transform_beacon_to_global(robot_x, robot_y, robot_yaw, beacon_x, beacon_y):
    """
    将Beacon相对坐标转换为全局坐标
    坐标系定义：
    - 机器人坐标系：X 向右（右手方向），Y 向前（车头方向）
    - 全局坐标系：X 向右，Y 向上
    - yaw=0 时，车头指向 Y 正方向
    
    使用2D旋转矩阵进行坐标变换：
    beacon_globe_x = robot_x + beacon_x*sin(yaw) + beacon_y*cos(yaw)
    beacon_globe_y = robot_y - beacon_x*cos(yaw) + beacon_y*sin(yaw)
    
    Args:
        robot_x: 机器人全局X坐标
        robot_y: 机器人全局Y坐标
        robot_yaw: 机器人偏航角（弧度）
        beacon_x: Beacon相对X坐标（右手方向为正）
        beacon_y: Beacon相对Y坐标（车头方向为正）
    
    Returns:
        dict: {'x': beacon_globe_x, 'y': beacon_globe_y}
    """
    try:
        cos_yaw = math.cos(float(robot_yaw))
        sin_yaw = math.sin(float(robot_yaw))
        
        beacon_x = float(beacon_x)
        beacon_y = float(beacon_y)
        robot_x = float(robot_x)
        robot_y = float(robot_y)
        
        # 正确的坐标系转换
        beacon_globe_x = robot_x + beacon_x * sin_yaw + beacon_y * cos_yaw
        beacon_globe_y = robot_y - beacon_x * cos_yaw + beacon_y * sin_yaw
        
        return {
            'x': beacon_globe_x,
            'y': beacon_globe_y
        }
    except Exception as e:
        logger.error(f"坐标变换失败: {e}")
        return {'x': 0, 'y': 0}

# ==================== 全局配置 ====================

# Beacon Globe 坐标平滑参数
BEACON_GLOBE_EMA_ALPHA = 0.3  # 指数移动平均系数 (0-1，越小越平滑)
smoothed_beacon_globe = {'x': 0.0, 'y': 0.0}  # 平滑后的beacon_globe
beacon_globe_init = False  # 是否初始化过

# 实时位置数据缓存（线程安全）
position_cache = {
    'current_position': None,
    'robot_pose': None,
    'timestamp': 0,
    'confidence': 0
}
position_lock = threading.Lock()

# 矩形框数据（用户绘制的检测区域）
detection_zones = []
zones_lock = threading.Lock()

# 地图数据缓存（线程安全）
map_cache = {
    'map_info': None,
    'map_data': None,
    'timestamp': 0
}
map_lock = threading.Lock()

# 应用状态
app_state = {
    'is_running': False,
    'reader': None,
    'kalman': None,
    'api_client': None,
    'transformer': None,
    'baseline_map': None
}

# ==================== 初始化 ====================

def init_workers():
    """初始化数据处理模块"""
    global app_state
    
    try:
        # 初始化 API 客户端（仅需API客户端）
        app_state['api_client'] = APIClient()
        
        logger.info("✓ 数据处理模块初始化完成")
        return True
    except Exception as e:
        logger.error(f"✗ 初始化失败: {e}")
        return False


def start_serial_reader(port='/dev/ttyUSB1', baudrate=921600):
    """已移除 - Beacon数据直接从5001端口读取"""
    logger.info("注意: Beacon数据已从5001端口(beacon_filter_service)获取，无需串口读取")
    return True


def update_position_worker():
    """后台线程：持续更新实时位置数据（10Hz）"""
    global app_state, position_cache, detection_zones
    
    import config
    import requests
    
    logger.info("启动位置更新线程（10Hz）...")
    app_state['is_running'] = True
    
    while app_state['is_running']:
        try:
            api_client = app_state.get('api_client')
            
            # 即使没有api_client，也继续运行
            if not api_client:
                time.sleep(config.POSE_QUERY_INTERVAL)
                continue
            
            # 获取地盘位姿态
            robot_pose = None
            try:
                robot_pose = api_client.fetch_pose()
                
                if robot_pose:
                    with position_lock:
                        position_cache['robot_pose'] = robot_pose
                        position_cache['timestamp'] = time.time()
                    
                    # 使用 INFO 级别日志，便于查看（每10次更新打印一次，避免刷屏）
                    if int(time.time() * 10) % 10 == 0:
                        logger.info(f"🤖 机器人位置: ({robot_pose.get('x', 0):.2f}, {robot_pose.get('y', 0):.2f}, yaw={robot_pose.get('yaw', 0):.2f}°)")
            except Exception as e:
                logger.warning(f"获取地盘位姿态失败: {e}")
            
            # 从5001端口获取Beacon滤波数据
            try:
                response = requests.get('http://127.0.0.1:5001/api/beacon', timeout=1.0)
                if response.status_code == 200:
                    beacon_data = response.json()
                    
                    # 更新缓存
                    with position_lock:
                        position_cache['filtered_beacon'] = {
                            'x': float(beacon_data.get('x', 0.0)),
                            'y': float(beacon_data.get('y', 0.0)),
                            'confidence': float(beacon_data.get('confidence', 0.0)),
                            'velocity_x': float(beacon_data.get('velocity_x', 0.0)),
                            'velocity_y': float(beacon_data.get('velocity_y', 0.0)),
                            'initialized': beacon_data.get('initialized', False),
                            'distance': float(beacon_data.get('distance', 0.0)),
                            'angle': float(beacon_data.get('angle', 0.0))
                        }
                    
                    if int(time.time() * 10) % 10 == 0:
                        logger.info(f"🔦 Beacon滤波数据: ({beacon_data.get('x', 0):.2f}, {beacon_data.get('y', 0):.2f}), 可信度={beacon_data.get('confidence', 0):.2f}")
            except requests.exceptions.ConnectionError:
                logger.debug("⚠️ 无法连接到5001端口的beacon_filter_service")
            except Exception as e:
                logger.debug(f"从5001获取Beacon数据失败: {e}")
            
            time.sleep(0.1)  # 10Hz 处理频率
        
        except Exception as e:
            logger.error(f"位置更新线程错误: {e}")
            time.sleep(0.1)
    
    logger.info("位置更新线程已停止")


def parse_beacon_data(raw_data):
    """已移除 - Beacon数据直接从5001端口读取"""
    pass


def check_point_in_zones(x: float, y: float, zones: List[Dict]) -> bool:
    """检查点是否在任何检测区域内"""
    for zone in zones:
        if is_point_in_rect(x, y, zone):
            return True
    return False


def is_point_in_rect(x: float, y: float, rect: Dict) -> bool:
    """检查点是否在矩形内"""
    x1, y1 = rect['x1'], rect['y1']
    x2, y2 = rect['x2'], rect['y2']
    
    min_x = min(x1, x2)
    max_x = max(x1, x2)
    min_y = min(y1, y2)
    max_y = max(y1, y2)
    
    return min_x <= x <= max_x and min_y <= y <= max_y


# ==================== Flask 路由 ====================

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/api/position')
def get_position():
    """获取当前 Beacon 位置（相对坐标）"""
    with position_lock:
        if position_cache.get('filtered_beacon'):
            beacon = position_cache['filtered_beacon']
            return jsonify({
                'beacon_filter_x': float(beacon.get('x', 0.0)),
                'beacon_filter_y': float(beacon.get('y', 0.0)),
                'distance': float(beacon.get('distance', 0.0)),
                'angle': float(beacon.get('angle', 0.0)),
                'confidence': float(beacon.get('confidence', 0.0)),
                'velocity_x': float(beacon.get('velocity_x', 0.0)),
                'velocity_y': float(beacon.get('velocity_y', 0.0)),
                'initialized': beacon.get('initialized', False),
                'status': 'active'
            })
    
    # 返回默认数据而不是 404（注意字段名保持一致）
    return jsonify({
        'beacon_filter_x': 0.0,
        'beacon_filter_y': 0.0,
        'distance': 0.0,
        'angle': 0.0,
        'confidence': 0.0,
        'velocity_x': 0.0,
        'velocity_y': 0.0,
        'initialized': False,
        'status': 'waiting'
    })


@app.route('/api/robot-pose')
def get_robot_pose():
    """获取机器人位姿态 + 滤波后的Beacon坐标 + 全局Beacon坐标"""
    with position_lock:
        if position_cache['robot_pose']:
            pose = position_cache['robot_pose']
            
            # 处理可能的嵌套结构：如果数据在 'pose' 字段中
            if isinstance(pose, dict):
                if 'pose' in pose and isinstance(pose['pose'], dict):
                    pose = pose['pose']
                
                # 获取滤波后的beacon数据
                filtered_beacon = position_cache.get('filtered_beacon', {})
                
                # 获取机器人位置和朝向
                robot_x = float(pose.get('x', 0))
                robot_y = float(pose.get('y', 0))
                robot_yaw = float(pose.get('yaw', 0))
                
                # 计算Beacon全局坐标
                beacon_globe = None
                if filtered_beacon and filtered_beacon.get('x') is not None and filtered_beacon.get('y') is not None:
                    beacon_globe_raw = transform_beacon_to_global(
                        robot_x, robot_y, robot_yaw,
                        filtered_beacon.get('x', 0),
                        filtered_beacon.get('y', 0)
                    )
                    # 对beacon_globe进行EMA平滑处理
                    beacon_globe = smooth_beacon_globe(beacon_globe_raw)
                
                # 确保有 x, y, yaw 字段
                response = {
                    'x': robot_x,
                    'y': robot_y,
                    'yaw': robot_yaw,
                    'z': float(pose.get('z', 0)),
                    'pitch': float(pose.get('pitch', 0)),
                    'roll': float(pose.get('roll', 0)),
                    'filtered_beacon': {
                        'x': float(filtered_beacon.get('x', 0)),
                        'y': float(filtered_beacon.get('y', 0)),
                        'confidence': float(filtered_beacon.get('confidence', 0)),
                        'velocity_x': float(filtered_beacon.get('velocity_x', 0)),
                        'velocity_y': float(filtered_beacon.get('velocity_y', 0))
                    }
                }
                
                # 添加平滑后的beacon_globe字段
                if beacon_globe:
                    response['beacon_globe'] = beacon_globe
                
                return jsonify(response)
    
    # 返回默认数据而不是 404
    return jsonify({
        'x': 0.0,
        'y': 0.0,
        'yaw': 0.0,
        'z': 0.0,
        'pitch': 0.0,
        'roll': 0.0,
        'filtered_beacon': {
            'x': 0.0,
            'y': 0.0,
            'confidence': 0.0,
            'velocity_x': 0.0,
            'velocity_y': 0.0
        },
        'beacon_globe': {
            'x': 0.0,
            'y': 0.0
        },
        'status': 'waiting'
    })
@app.route('/api/map-info')
def get_map_info():
    """获取地图元数据 - 从实时 API 获取"""
    try:
        api_client = app_state.get('api_client')
        if not api_client:
            return jsonify({'error': 'API client not initialized'}), 500
        
        # 从实时 API 获取地图数据并缓存
        map_data = api_client.fetch_explore_map()
        if map_data and 'metadata' in map_data:
            metadata = map_data['metadata']
            
            # 保存到缓存
            with map_lock:
                map_cache['map_info'] = metadata
                map_cache['map_data'] = map_data.get('data')
                map_cache['timestamp'] = time.time()
            
            logger.info(f"✓ 地图信息已获取并缓存")
            return jsonify({
                'origin_x': float(metadata['origin_x']),
                'origin_y': float(metadata['origin_y']),
                'width': int(metadata['width']),
                'height': int(metadata['height']),
                'resolution': float(metadata['resolution'])
            })
    except Exception as e:
        logger.error(f"获取地图信息失败: {e}")
        return jsonify({'error': str(e)}), 500
    
    return jsonify({'error': 'Map not loaded'}), 404


@app.route('/api/map-data')
def get_map_data():
    """获取地图栅格数据 - 从缓存或实时 API 获取，并应用自定义颜色映射"""
    try:
        from PIL import Image
        import numpy as np
        import io
        import base64
        
        # 先尝试从缓存获取
        with map_lock:
            grid_data = map_cache.get('map_data')
            map_info = map_cache.get('map_info')
        
        # 如果缓存为空，从 API 获取
        if grid_data is None or map_info is None:
            api_client = app_state.get('api_client')
            if not api_client:
                return jsonify({'error': 'API client not initialized'}), 500
            
            map_data = api_client.fetch_explore_map()
            if not map_data or 'data' not in map_data or 'metadata' not in map_data:
                return jsonify({'error': 'Map data not available'}), 404
            
            grid_data = map_data['data']
            map_info = map_data['metadata']
            
            # 保存到缓存
            with map_lock:
                map_cache['map_info'] = map_info
                map_cache['map_data'] = grid_data
                map_cache['timestamp'] = time.time()
        
        width = map_info['width']
        height = map_info['height']
        
        # 将栅格数据转换为数组
        grid_array = np.frombuffer(grid_data, dtype=np.uint8).reshape((height, width))
        
        # 垂直翻转栅格数据以纠正图像方向
        grid_array = np.flipud(grid_array)
        
        # 创建RGB图像（自定义颜色映射）
        rgb_array = np.zeros((height, width, 3), dtype=np.uint8)
        
        # 颜色映射规则：
        # 值 = 127 → 白色 (255, 255, 255)
        # 值 < 127 → 灰色 (128, 128, 128)
        # 值 > 127 → 黑色 (0, 0, 0)
        white_mask = (grid_array == 127)
        gray_mask = (grid_array < 127)
        black_mask = (grid_array > 127)
        
        # 应用颜色映射
        rgb_array[white_mask] = [255, 255, 255]  # 白色
        rgb_array[gray_mask] = [128, 128, 128]   # 灰色
        rgb_array[black_mask] = [0, 0, 0]        # 黑色
        
        # 创建 PIL 图像
        image = Image.fromarray(rgb_array, mode='RGB')
        
        # 在图像上绘制坐标轴
        from PIL import ImageDraw
        draw = ImageDraw.Draw(image)
        
        # 计算原点在图像中的位置（以左下角作为原点）
        origin_grid_x = int(-map_info['origin_x'] / map_info['resolution'])
        origin_grid_y = int(-map_info['origin_y'] / map_info['resolution'])
        
        # 由于图像已经垂直翻转，需要调整Y坐标
        origin_image_y = height - origin_grid_y
        origin_image_x = origin_grid_x
        
        # 限制原点在图像范围内
        if 0 <= origin_image_x < width and 0 <= origin_image_y < height:
            arrow_length = 15  # 箭头长度（像素，不超过20）
            arrow_head_size = 6  # 箭头头大小
            
            # X轴（红色）- 向右
            draw.line(
                [(origin_image_x, origin_image_y), (origin_image_x + arrow_length, origin_image_y)],
                fill=(255, 0, 0),
                width=2
            )
            # X轴箭头头部
            x_arrow_tip = origin_image_x + arrow_length
            draw.polygon(
                [(x_arrow_tip, origin_image_y),
                 (x_arrow_tip - arrow_head_size, origin_image_y - arrow_head_size // 2),
                 (x_arrow_tip - arrow_head_size, origin_image_y + arrow_head_size // 2)],
                fill=(255, 0, 0)
            )
            
            # Y轴（绿色）- 向上（Y轴正方向向上）
            draw.line(
                [(origin_image_x, origin_image_y), (origin_image_x, origin_image_y - arrow_length)],
                fill=(0, 200, 0),
                width=2
            )
            # Y轴箭头头部（指向上方）
            y_arrow_tip = origin_image_y - arrow_length
            draw.polygon(
                [(origin_image_x, y_arrow_tip),
                 (origin_image_x - arrow_head_size // 2, y_arrow_tip + arrow_head_size),
                 (origin_image_x + arrow_head_size // 2, y_arrow_tip + arrow_head_size)],
                fill=(0, 200, 0)
            )
            
            # 原点（黑色圆点）
            dot_radius = 3
            draw.ellipse(
                [(origin_image_x - dot_radius, origin_image_y - dot_radius),
                 (origin_image_x + dot_radius, origin_image_y + dot_radius)],
                fill=(0, 0, 0)
            )
            
            logger.info(f"✓ 坐标轴已绘制到图像: 原点位置=({origin_image_x}, {origin_image_y})")
        else:
            logger.warning(f"⚠ 原点超出图像范围，跳过绘制: ({origin_image_x}, {origin_image_y})")
        
        # 转换为 Base64
        buffer = io.BytesIO()
        image.save(buffer, format='PNG')
        image_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # 统计各颜色像素数
        white_count = np.sum(white_mask)
        gray_count = np.sum(gray_mask)
        black_count = np.sum(black_mask)
        
        logger.info(f"✓ 地图栅格数据已处理: {width}x{height}")
        logger.info(f"  颜色分布: 白色={white_count}, 灰色={gray_count}, 黑色={black_count}")
        
        return jsonify({'image': image_base64})
    except Exception as e:
        logger.error(f"获取地图数据失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500


@app.route('/api/zones', methods=['GET', 'POST'])
def manage_zones():
    """获取或保存检测区域"""
    global detection_zones
    
    if request.method == 'GET':
        with zones_lock:
            return jsonify({'zones': detection_zones})
    
    elif request.method == 'POST':
        try:
            data = request.json
            with zones_lock:
                if 'zones' in data:
                    detection_zones = data['zones']
                    logger.info(f"检测区域已更新: {len(detection_zones)} 个区域")
                    return jsonify({'status': 'ok', 'count': len(detection_zones)})
        except Exception as e:
            logger.error(f"保存检测区域失败: {e}")
            return jsonify({'error': str(e)}), 400
    
    return jsonify({'error': 'Invalid request'}), 400


@app.route('/api/status')
def get_status():
    """获取应用状态"""
    reader_status = 'disconnected'
    try:
        import requests
        response = requests.get('http://127.0.0.1:5001/api/status', timeout=1.0)
        if response.status_code == 200:
            reader_status = 'connected'
    except:
        pass
    
    return jsonify({
        'is_running': app_state['is_running'],
        'beacon_service': reader_status,
        'timestamp': time.time()
    })


@app.route('/api/start', methods=['POST'])
def start_system():
    """启动数据采集"""
    try:
        if not app_state['is_running']:
            if init_workers():
                # 启动位置更新线程
                thread = threading.Thread(target=update_position_worker, daemon=True)
                thread.start()
                return jsonify({'status': 'started'})
        
        return jsonify({'status': 'already running'})
    except Exception as e:
        logger.error(f"启动系统失败: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/stop', methods=['POST'])
def stop_system():
    """停止数据采集"""
    try:
        app_state['is_running'] = False
        if app_state['reader']:
            app_state['reader'].stop()
        return jsonify({'status': 'stopped'})
    except Exception as e:
        logger.error(f"停止系统失败: {e}")
        return jsonify({'error': str(e)}), 500


# ==================== 主程序 ====================

if __name__ == '__main__':
    logger.info("=" * 50)
    logger.info("AOA 定位系统 - Web 可视化界面")
    logger.info("=" * 50)
    
    # 自动初始化系统
    logger.info("正在初始化系统...")
    if init_workers():
        logger.info("✓ 系统初始化完成")
        logger.info("ℹ️  Beacon数据将从 http://127.0.0.1:5001/api/beacon 获取")
        # 启动位置更新线程
        thread = threading.Thread(target=update_position_worker, daemon=True)
        thread.start()
        logger.info("✓ 位置更新线程已启动")
        app_state['is_running'] = True
    else:
        logger.error("✗ 系统初始化失败")
    
    # 启动 Flask 服务器（树莓派上设置 host='0.0.0.0' 供其他设备访问）
    app.run(
        host='127.0.0.1',  # 改为 '0.0.0.0' 可从其他设备访问
        port=5000,
        debug=False,
        use_reloader=False
    )
