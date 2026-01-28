#!/usr/bin/env python3
"""
实时卡尔曼滤波测试 - 使用串口beacon数据
从AOASerialReader获取实时数据，进行滤波处理和结果对比
集成地盘位姿态API，将Beacon位置转换到地图全局坐标系
"""
import sys
import os
import time
import math
import argparse
import logging
import re
from typing import Optional, Tuple, Dict, List
from collections import deque
import serial.tools.list_ports

# 添加项目根路径到sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from workers.aoa_kalman_filter import MultiTargetKalmanFilter
from workers.aoa_serial_reader import AOASerialReader
from core.api_client import APIClient
from coordinate_transform import transform_beacon_position, CoordinateTransformer

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def find_available_serial_ports() -> List[str]:
    """扫描所有可用的串口"""
    ports = serial.tools.list_ports.comports()
    available_ports = []
    for port in ports:
        available_ports.append(port.device)
    return available_ports


def auto_detect_beacon_port(baudrate: int = 921600, timeout: float = 3.0) -> Optional[str]:
    """
    自动检测带有anchor设备的串口（检测beacon数据或UWB RX fail消息）
    
    Args:
        baudrate: 波特率
        timeout: 每个串口的检测超时时间
    
    Returns:
        检测到的串口名称，如果没有找到返回 None
    """
    ports = find_available_serial_ports()
    
    if not ports:
        logger.warning("未找到任何可用串口")
        return None
    
    logger.info(f"扫描到 {len(ports)} 个可用串口: {', '.join(ports)}")
    
    for port in ports:
        logger.info(f"正在检测串口: {port}")
        try:
            # 创建临时读取器测试串口
            test_reader = AOASerialReader(
                port=port,
                baudrate=baudrate,
                timeout=0.5
            )
            
            if not test_reader.connect():
                logger.debug(f"{port}: 连接失败")
                continue
            
            # 等待并读取数据
            start_time = time.time()
            data_received = False
            
            while time.time() - start_time < timeout:
                try:
                    if test_reader.serial and test_reader.serial.in_waiting > 0:
                        data = test_reader.serial.read(test_reader.serial.in_waiting)
                        if data:
                            # 检查数据是否包含beacon数据或anchor工作特征
                            text = data.decode('utf-8', errors='ignore')
                            # 检测beacon数据或UWB RX fail（表示anchor在工作）
                            if 'DS-TWR' in text or 'PDoA' in text or 'Azimuth' in text:
                                logger.info(f"✓ 在 {port} 检测到beacon数据")
                                test_reader.disconnect()
                                return port
                            elif 'UWB RX fail' in text:
                                logger.info(f"✓ 在 {port} 检测到anchor设备（beacon断连状态）")
                                test_reader.disconnect()
                                return port
                            data_received = True
                except Exception as e:
                    logger.debug(f"{port}: 读取错误 - {e}")
                
                time.sleep(0.1)
            
            test_reader.disconnect()
            
            if data_received:
                logger.debug(f"{port}: 有数据但不是anchor/beacon格式")
            else:
                logger.debug(f"{port}: {timeout}秒内无数据")
                
        except Exception as e:
            logger.debug(f"{port}: 检测异常 - {e}")
            continue
    
    logger.warning("未在任何串口检测到anchor设备")
    return None


class BeaconDataParser:
    """从串口ASCII文本解析beacon信息"""
    
    def __init__(self):
        self.valid_frame_count = 0      # 有效帧计数
        self.parsed_frame_count = 0     # 总解析帧数
        self.error_count = 0             # 错误帧数
        self.text_buffer = ""            # ASCII文本缓冲
        self.beacon_status = "UNKNOWN"   # beacon状态：CONNECTED/DISCONNECTED/UNKNOWN
        self.last_seq = None
        self.last_disconnect_time = None  # 上次断开检测时间
        
        # 正则表达式模式 - 匹配新的ASCII格式
        self._re_seq = re.compile(r"Custom\s+DS-TWR\s+Responder\s+SEQ\s+NUM\s+(\d+)")
        self._re_rssi = re.compile(r"RSSI:\s*(-?\d+)dBm,\s*SNR:\s*(\d+)dB")
        # 新格式：Peer AAA1, Distance 320cm, PDoA Azimuth -18 Elevation ...
        self._re_peer = re.compile(r"Peer\s+(\S+),\s*Distance\s+(\d+)cm,\s*PDoA\s+Azimuth\s+(-?\d+)")
        self._re_uwb_fail = re.compile(r"UWB RX fail")
        
        # 累积字段
        self.current_record: Dict = {}
    
    def feed_data(self, data: bytes) -> list:
        """
        接收原始字节数据，返回解析出的所有beacon数据
        同时检测 beacon 断开的日志消息
        
        Returns:
            List of beacon measurement dicts with keys:
            - tag_id: beacon标签ID
            - distance: 距离（米）
            - angle: 角度（度）
            - rssi: 信号强度（dBm）
            - snr: 信噪比（dB）
        """
        # 解码文本，处理编码错误
        self.text_buffer += data.decode('utf-8', errors='ignore')
        
        frames = []
        
        # 检测beacon断开日志
        if self._re_uwb_fail.search(self.text_buffer):
            current_time = time.time()
            # 避免重复输出断开信息
            if self.beacon_status != "DISCONNECTED" or \
               (self.last_disconnect_time is None or current_time - self.last_disconnect_time > 1.0):
                self.beacon_status = "DISCONNECTED"
                self.last_disconnect_time = current_time
               # logger.info(f"检测到 UWB RX fail - beacon 断开")
                # 返回一个断开状态的帧
                frames.append({
                    'tag_id': 1,
                    'distance': 0.0,
                    'angle': 0.0,
                    'rssi': 0,
                    'snr': 0,
                    'seq': None,
                    'peer': 'DISCONNECTED'
                })
        
        # 逐行处理
        if '\n' in self.text_buffer:
            lines = self.text_buffer.split('\n')
            self.text_buffer = lines[-1]  # 保留最后可能未完整的一行
            
            for line in lines[:-1]:
                line = line.strip()
                if not line:
                    continue
                
                # 解析SEQ
                m_seq = self._re_seq.search(line)
                if m_seq:
                    self.last_seq = int(m_seq.group(1))
                    self.current_record = {'seq': self.last_seq}
                
                # 解析RSSI/SNR
                m_rssi = self._re_rssi.search(line)
                if m_rssi:
                    self.current_record['rssi'] = int(m_rssi.group(1))
                    self.current_record['snr'] = int(m_rssi.group(2))
                
                # 解析距离/角度
                m_peer = self._re_peer.search(line)
                if m_peer:
                    peer = m_peer.group(1)
                    dist_cm = int(m_peer.group(2))
                    azimuth_deg = int(m_peer.group(3))
                    
                    self.current_record['peer'] = peer
                    self.current_record['distance'] = dist_cm / 100.0  # 转为米
                    self.current_record['angle'] = azimuth_deg
                    
                    # 当五项数据具备时，输出一条记录
                    if (
                        'seq' in self.current_record and
                        'rssi' in self.current_record and
                        'snr' in self.current_record and
                        'distance' in self.current_record and
                        'angle' in self.current_record
                    ):
                        # 将peer作为tag_id
                        tag_id = int(self.current_record['peer'], 16) if self.current_record['peer'].startswith('0x') else 1
                        
                        frame_data = {
                            'tag_id': tag_id,
                            'distance': self.current_record['distance'],
                            'angle': self.current_record['angle'],
                            'rssi': self.current_record.get('rssi'),
                            'snr': self.current_record.get('snr'),
                            'seq': self.current_record.get('seq'),
                            'peer': self.current_record.get('peer')
                        }
                        frames.append(frame_data)
                        
                        self.valid_frame_count += 1
                        self.beacon_status = "CONNECTED"
                        self.parsed_frame_count += 1
                        
                        logger.debug(f"解析帧: seq={frame_data['seq']}, peer={frame_data['peer']}, "
                                   f"距离={frame_data['distance']:.2f}m, 角度={frame_data['angle']}°")
                        
                        # 清空当前记录
                        self.current_record = {}
        
        return frames
    
    def get_statistics(self) -> dict:
        return {
            'total_frames': self.parsed_frame_count,
            'error_count': self.error_count,
            'valid_count': self.valid_frame_count,
            'buffer_size': len(self.text_buffer),
            'beacon_status': self.beacon_status
        }


class RealtimeKalmanTest:
    """实时卡尔曼滤波测试 - 集成地盘位姿态和坐标变换"""
    
    def __init__(self, port: Optional[str] = None, baudrate: int = 921600, duration: int = 60):
        """
        初始化测试
        
        Args:
            port: 串口名称（None表示自动检测）
            baudrate: 波特率
            duration: 测试持续时间（秒）
        """
        self.port = port
        self.baudrate = baudrate
        self.duration = duration
        
        # 如果未指定串口，自动检测
        if self.port is None:
            logger.info("未指定串口，开始自动检测...")
            detected_port = auto_detect_beacon_port(baudrate=self.baudrate)
            if detected_port:
                self.port = detected_port
                logger.info(f"自动选择串口: {self.port}")
            else:
                raise RuntimeError("无法自动检测到anchor设备，请手动指定 --port 参数或检查设备连接")
        
        # 初始化读取器（使用self.port而不是port参数）
        self.reader = AOASerialReader(
            port=self.port,
            baudrate=self.baudrate,
            timeout=0.1
        )
        
        # 初始化解析器
        self.parser = BeaconDataParser()
        
        # 初始化卡尔曼滤波器
        self.kalman = MultiTargetKalmanFilter(
            process_noise=0.1,
            measurement_noise=0.5,
            min_confidence=0.3
        )
        
        # 初始化API客户端（用于获取地盘位姿态）
        try:
            self.api_client = APIClient()
            self.last_robot_pose = None
            self.pose_fetch_error_count = 0
            logger.info(f"已初始化API客户端，地址: {self.api_client.base_url}")
        except Exception as e:
            logger.warning(f"API客户端初始化失败，将在本地坐标系工作: {e}")
            self.api_client = None
            self.last_robot_pose = None
        
        # 坐标变换器
        self.transformer = CoordinateTransformer()
        
        # 数据收集
        self.raw_measurements = deque()  # (tag_id, distance, angle, timestamp)
        self.filtered_results = deque()  # (tag_id, x, y, confidence, timestamp)
        self.global_positions = deque()  # (tag_id, x_global, y_global, yaw, confidence, timestamp)
        
        # 统计
        self.total_frames = 0
        self.valid_frames = 0
        self.parse_errors = 0
        self.display_count = 0  # 用于控制表头显示频率
    
    def _fetch_robot_pose(self) -> Optional[Dict]:
        """
        获取地盘的当前位姿态（地图全局坐标）
        
        Returns:
            Dict with keys 'x', 'y', 'yaw'，或None如果获取失败
        """
        if not self.api_client:
            return None
        
        try:
            pose_data = self.api_client.fetch_pose()
            
            # 验证数据
            if not self.transformer.validate_robot_pose(pose_data):
                self.pose_fetch_error_count += 1
                if self.pose_fetch_error_count == 1:
                    logger.warning(f"地盘位姿态数据无效: {pose_data}")
                return None
            
            self.pose_fetch_error_count = 0
            self.last_robot_pose = pose_data
            return pose_data
            
        except Exception as e:
            self.pose_fetch_error_count += 1
            if self.pose_fetch_error_count == 1:  # 只在第一次出错时输出
                logger.warning(f"获取地盘位姿态失败: {e}，将在本地坐标系工作")
            return None
    
    def run(self):
        """运行测试"""
        print("\n" + "=" * 180)
        print(f"实时卡尔曼滤波测试 - 地盘全局坐标定位")
        print("=" * 180)
        print(f"串口: {self.port} @ {self.baudrate} baud")
        if self.duration > 0:
            print(f"测试时长: {self.duration} 秒\n")
        else:
            print(f"测试时长: 无限（按Ctrl+C停止）\n")
        
        # 测试API连接
        if self.api_client:
            try:
                pose = self._fetch_robot_pose()
                if pose:
                    print(f"✓ 地盘API连接成功 - 当前位姿: x={pose['x']:.3f}, y={pose['y']:.3f}, yaw={pose['yaw']:.3f}")
                else:
                    print(f"✗ 地盘位姿态获取失败 - 将在本地坐标系工作")
            except Exception as e:
                print(f"✗ 地盘API连接失败: {e} - 将在本地坐标系工作")
        else:
            print(f"✗ API客户端未初始化 - 将在本地坐标系工作")
        
        print()
        
        # 注册数据回调
        self.reader.register_callback(self._on_raw_data)
        
        # 启动读取线程
        self.reader.start()
        
        print("数据格式: time dis angle local_x local_y filtered_x filtered_y global_x global_y yaw conf speed status")
        print("-" * 180)
        
        # 主循环
        start_time = time.time()
        last_pose_fetch = start_time
        pose_fetch_interval = 0.05  # 20Hz获取位姿态
        
        try:
            if self.duration > 0:
                while time.time() - start_time < self.duration:
                    # 定期获取地盘位姿态
                    now = time.time()
                    if now - last_pose_fetch >= pose_fetch_interval:
                        self._fetch_robot_pose()
                        last_pose_fetch = now
                    time.sleep(0.01)  # 10ms轮询间隔
            else:
                while True:
                    # 定期获取地盘位姿态
                    now = time.time()
                    if now - last_pose_fetch >= pose_fetch_interval:
                        self._fetch_robot_pose()
                        last_pose_fetch = now
                    time.sleep(0.01)  # 10ms轮询间隔
        
        except KeyboardInterrupt:
            print("\n用户中断")
        
        finally:
            elapsed = time.time() - start_time
            self.reader.stop()
            self.reader.join(timeout=2.0)
            
            print("-" * 180)
            self._print_summary(elapsed)
    
    def _on_raw_data(self, data: bytes):
        """原始数据回调"""
        frames = self.parser.feed_data(data)
        
        for frame_data in frames:
            self.total_frames += 1
            
            # 如果beacon已断开，使用0值代替
            if self.parser.beacon_status == "DISCONNECTED":
                tag_id = frame_data['tag_id']
                distance = 0.0
                angle = 0.0
                ts = time.time()
                
                logger.debug(f"Beacon断开，使用0值: tag_id={tag_id}")
            else:
                # 正常使用解析的数据
                tag_id = frame_data['tag_id']
                distance = frame_data['distance']
                angle = frame_data['angle']
                ts = time.time()
                
                self.valid_frames += 1
            
            # 记录原始测量
            self.raw_measurements.append((tag_id, distance, angle, ts))
            
            # 只有beacon连接时才进入kalman滤波
            if self.parser.beacon_status == "CONNECTED":
                filtered_x, filtered_y, info = self.kalman.filter_measurement(
                    tag_id=tag_id,
                    distance=distance,
                    angle_deg=angle,
                    timestamp=ts
                )
                
                # 记录滤波结果
                confidence = info.get('confidence', 0.0)
                self.filtered_results.append((tag_id, filtered_x, filtered_y, confidence, ts))
                
                # 尝试转换到地图全局坐标系
                robot_pose = self.last_robot_pose
                if robot_pose:
                    try:
                        # 构建局部坐标信息
                        local_pos = {
                            'x': filtered_x,
                            'y': filtered_y,
                            'vx': info.get('v_distance', 0) * (-math.sin(math.radians(info.get('filtered_angle', 0)))),
                            'vy': info.get('v_distance', 0) * (math.cos(math.radians(info.get('filtered_angle', 0))))
                        }
                        
                        # 转换到全局坐标
                        global_pos = transform_beacon_position(local_pos, robot_pose)
                        self.global_positions.append((
                            tag_id,
                            global_pos['x'],
                            global_pos['y'],
                            global_pos.get('yaw', 0.0),
                            confidence,
                            ts
                        ))
                    except Exception as e:
                        logger.debug(f"坐标转换失败: {e}")
                
                # 立即显示这一行数据
                self._display_one_result(tag_id, filtered_x, filtered_y, confidence, ts)
            else:
                # Beacon断开时，记录0值结果
                self.filtered_results.append((tag_id, 0.0, 0.0, 0.0, ts))
                self._display_one_result(tag_id, 0.0, 0.0, 0.0, ts)
    
    def _display_one_result(self, tag_id: int, filt_x: float, filt_y: float, confidence: float, ts: float):
        """实时显示单条结果 - 包括全局坐标和朝向"""
        self.display_count += 1
        
        # 对应的原始测量
        raw_x, raw_y, distance, angle = 0.0, 0.0, 0.0, 0.0
        for t_id, d, a, t_ts in reversed(self.raw_measurements):
            if t_id == tag_id and abs(t_ts - ts) < 0.1:  # 10ms内的对应测量
                distance = d
                angle = a
                # 极坐标转笛卡尔坐标
                if distance > 0:
                    angle_rad = math.radians(angle)
                    raw_y = distance * math.cos(angle_rad)
                    raw_x = -distance * math.sin(angle_rad)
                break
        
        state = self.kalman.get_filter_state(tag_id)
        speed = state.get('speed', 0.0) if self.parser.beacon_status == "CONNECTED" else 0.0
        
        elapsed = ts - (self.filtered_results[0][4] if self.filtered_results else ts)
        
        # beacon状态指示符
        status_symbol = "✓" if self.parser.beacon_status == "CONNECTED" else "✗"
        
        # 获取全局坐标
        global_x, global_y, global_yaw = 0.0, 0.0, 0.0
        pose_status = "no_pose"
        if self.last_robot_pose:
            # 查找最新的全局位置
            for g_tag, g_x, g_y, g_yaw, g_conf, g_ts in reversed(self.global_positions):
                if g_tag == tag_id and abs(g_ts - ts) < 0.1:
                    global_x, global_y, global_yaw = g_x, g_y, g_yaw
                    pose_status = "ok"
                    break
            if pose_status == "no_pose":
                pose_status = f"pose_delay"
        
        # 颜色定义
        GREEN = "\033[92m"   # 绿色 - 数据值
        CYAN = "\033[96m"    # 青色 - 全局坐标
        WHITE = "\033[97m"   # 白色 - 字段名
        RESET = "\033[0m"
        
        # 显示格式：时间 距离 角度 | 局部坐标 | 滤波坐标 | 全局坐标 朝向 置信度 速度 状态
        print(f"{WHITE}t={GREEN}{elapsed:6.2f}s {WHITE}d={GREEN}{distance:5.2f}m {WHITE}a={GREEN}{angle:4.0f}° "
              f"{WHITE}| local={GREEN}{filt_x:6.2f}/{filt_y:6.2f}m "
              f"{WHITE}| global={CYAN}{global_x:6.2f}/{global_y:6.2f}m {WHITE}yaw={CYAN}{global_yaw:6.2f}rad "
              f"{WHITE}conf={GREEN}{confidence:4.2f} {WHITE}speed={GREEN}{speed:5.2f}m/s "
              f"{WHITE}status={GREEN}{status_symbol}({self.parser.beacon_status}){WHITE}|pose={CYAN}{pose_status}{RESET}")

    
    def _display_latest_results(self):
        """显示最新的滤波结果"""
        if not self.filtered_results:
            return
        
        # 获取最后一个结果
        tag_id, filt_x, filt_y, confidence, ts = self.filtered_results[-1]
        
        # 对应的原始测量
        raw_x, raw_y, distance, angle = 0.0, 0.0, 0.0, 0.0
        for t_id, d, a, t_ts in reversed(self.raw_measurements):
            if t_id == tag_id and abs(t_ts - ts) < 0.1:  # 10ms内的对应测量
                distance = d
                angle = a
                # 极坐标转笛卡尔坐标
                if distance > 0:
                    angle_rad = math.radians(angle)
                    raw_y = distance * math.cos(angle_rad)
                    raw_x = -distance * math.sin(angle_rad)
                break
        
        state = self.kalman.get_filter_state(tag_id)
        speed = state.get('speed', 0.0) if self.parser.beacon_status == "CONNECTED" else 0.0
        
        elapsed = ts - (self.filtered_results[0][4] if self.filtered_results else ts)
        
        # beacon状态指示符
        status_symbol = "✓" if self.parser.beacon_status == "CONNECTED" else "✗"
        
        print(f"{self.total_frames:>6} {elapsed:>10.2f} {tag_id:>8} {distance:>10.3f} {angle:>10.1f} "
              f"{raw_x:>12.3f} {raw_y:>12.3f} "
              f"{filt_x:>12.3f} {filt_y:>12.3f} {confidence:>8.3f} {speed:>11.3f} "
              f"{status_symbol:>12} {self.parser.beacon_status}")
    
    def _print_summary(self, elapsed: float):
        """打印总结统计"""
        print(f"\n✅ 测试完成")
        print("=" * 180)
        print(f"测试耗时: {elapsed:.2f} 秒")
        print(f"总接收帧数: {self.total_frames}")
        print(f"有效帧数（可解析）: {self.valid_frames}")
        print(f"解析错误: {self.parse_errors}")
        print(f"成功率: {self.valid_frames/self.total_frames*100:.1f}%" if self.total_frames > 0 else "无数据")
        print()
        
        # 按标签汇总统计
        tag_stats = {}
        for tag_id, _, _, conf, _ in self.filtered_results:
            if tag_id not in tag_stats:
                tag_stats[tag_id] = {'count': 0, 'conf_sum': 0}
            tag_stats[tag_id]['count'] += 1
            tag_stats[tag_id]['conf_sum'] += conf
        
        if tag_stats:
            print("标签统计:")
            for tag_id in sorted(tag_stats.keys()):
                stats = tag_stats[tag_id]
                avg_conf = stats['conf_sum'] / stats['count']
                print(f"  Tag {tag_id}: {stats['count']} 样本, 平均置信度 {avg_conf:.3f}")
        
        print()
        print(f"读取器统计:")
        reader_stats = self.reader.get_statistics()
        print(f"  字节接收: {reader_stats.get('bytes_received', 0)}")
        print(f"  数据块: {reader_stats.get('chunks_received', 0)}")
        print(f"  错误: {reader_stats.get('errors', 0)}")
        
        print()
        
        # 全局坐标统计
        if self.global_positions:
            print(f"全局坐标统计:")
            global_tag_stats = {}
            for tag_id, x, y, yaw, conf, ts in self.global_positions:
                if tag_id not in global_tag_stats:
                    global_tag_stats[tag_id] = {
                        'count': 0,
                        'x_list': [],
                        'y_list': [],
                        'yaw_list': [],
                        'conf_sum': 0
                    }
                global_tag_stats[tag_id]['count'] += 1
                global_tag_stats[tag_id]['x_list'].append(x)
                global_tag_stats[tag_id]['y_list'].append(y)
                global_tag_stats[tag_id]['yaw_list'].append(yaw)
                global_tag_stats[tag_id]['conf_sum'] += conf
            
            for tag_id in sorted(global_tag_stats.keys()):
                stats = global_tag_stats[tag_id]
                if stats['count'] > 0:
                    avg_x = sum(stats['x_list']) / stats['count']
                    avg_y = sum(stats['y_list']) / stats['count']
                    avg_yaw = sum(stats['yaw_list']) / stats['count']
                    avg_conf = stats['conf_sum'] / stats['count']
                    
                    # 计算位置标准差
                    var_x = sum((x - avg_x) ** 2 for x in stats['x_list']) / max(1, stats['count'] - 1)
                    var_y = sum((y - avg_y) ** 2 for y in stats['y_list']) / max(1, stats['count'] - 1)
                    std_x = math.sqrt(var_x)
                    std_y = math.sqrt(var_y)
                    
                    print(f"  Tag {tag_id} (全局坐标):")
                    print(f"    样本数: {stats['count']}")
                    print(f"    平均位置: x={avg_x:.3f}m (±{std_x:.3f}), y={avg_y:.3f}m (±{std_y:.3f})")
                    print(f"    平均朝向: {avg_yaw:.3f}rad ({math.degrees(avg_yaw):.1f}°)")
                    print(f"    平均置信度: {avg_conf:.3f}")
        else:
            print(f"全局坐标统计: 无数据（可能API未连接）")
        
        print()
        print(f"Beacon 状态: {self.parser.beacon_status}")
        print(f"解析器统计:")
        parser_stats = self.parser.get_statistics()
        print(f"  总解析帧数: {parser_stats.get('total_frames', 0)}")
        print(f"  成功解析: {parser_stats.get('valid_count', 0)}")
        print(f"  解析异常: {parser_stats.get('error_count', 0)}")
        
        if self.api_client:
            print()
            print(f"API客户端统计:")
            if self.last_robot_pose:
                print(f"  最后获取的地盘位姿: x={self.last_robot_pose['x']:.3f}, y={self.last_robot_pose['y']:.3f}, yaw={self.last_robot_pose['yaw']:.3f}")
            print(f"  获取失败次数: {self.pose_fetch_error_count}")
        
        print("=" * 180)


def main():
    parser = argparse.ArgumentParser(
        description="实时卡尔曼滤波测试 - 从串口beacon数据",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python test_realtime_beacon.py                                    # 自动检测串口
  python test_realtime_beacon.py --port /dev/ttyUSB0                # 手动指定串口
  python test_realtime_beacon.py --port /dev/ttyUSB1 --duration 60  # 指定串口和时长
        """
    )
    
    parser.add_argument(
        '--port',
        default=None,
        help='串口名称（留空自动检测anchor设备，推荐）'
    )
    parser.add_argument(
        '--baudrate',
        type=int,
        default=921600,
        help='波特率（默认: 921600）'
    )
    parser.add_argument(
        '--duration',
        type=int,
        default=0,
        help='测试持续时间（秒，0表示无限运行，默认: 0）'
    )
    
    args = parser.parse_args()
    
    try:
        test = RealtimeKalmanTest(
            port=args.port,
            baudrate=args.baudrate,
            duration=args.duration
        )
    except RuntimeError as e:
        logger.error(f"初始化失败: {e}")
        return 1
    
    try:
        test.run()
    except Exception as e:
        logger.error(f"测试失败: {e}")
        return 1
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
