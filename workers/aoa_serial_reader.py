"""
AOA 串口数据接收工作线程
负责持续从串口接收数据并将原始字节流交给上层处理
"""
import os
import sys
import logging
import threading
import time
import queue
import re
from typing import Optional, Callable, List

# Allow running this file directly by ensuring project root is on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
from serial import (
    Serial,
    SerialException,
    PARITY_NONE,
    PARITY_EVEN,
    PARITY_ODD,
    STOPBITS_ONE,
    STOPBITS_TWO,
    EIGHTBITS,
    SEVENBITS,
)


logger = logging.getLogger(__name__)


def _format_ascii_preview(data: bytes, max_len: int = 80) -> str:
    """Return a printable ASCII preview, replacing non-printables with '.'"""
    if not data:
        return ""
    trimmed = data[:max_len]
    return "".join(chr(b) if 32 <= b < 127 else '.' for b in trimmed)


class AOASerialReader(threading.Thread):
    """
    AOA 串口读取线程
    """
    
    def __init__(self, 
                 port: str,
                 baudrate: int = 115200,
                 timeout: float = 1.0,
                 buffer_size: int = 8192,
                 bytesize: int = 8,
                 parity: str = "N",
                 stopbits: int = 1):
        """
        初始化读取线程
        
        Args:
            port: 串口名称 (e.g., 'COM3' or '/dev/ttyUSB0')
            baudrate: 波特率，默认 115200
            timeout: 读取超时时间（秒）
            buffer_size: 接收缓冲区大小
        """
        super().__init__(daemon=True)
        
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.buffer_size = buffer_size
        self.bytesize = bytesize
        self.parity = parity
        self.stopbits = stopbits
        
        self.serial: Optional[Serial] = None
        self.running = False

        # 数据队列（仅原始字节流）
        self.raw_data_queue: queue.Queue[bytes] = queue.Queue(maxsize=50)

        # 统计信息
        self.bytes_received = 0
        self.chunks_received = 0
        self.errors = 0

        # 回调列表（回调签名: Callable[[bytes], None]）
        self.callbacks: List[Callable[[bytes], None]] = []
        self.lock = threading.Lock()

    def connect(self) -> bool:
        """
        连接串口
        
        Returns:
            连接成功返回 True，否则 False
        """
        try:
            if self.serial and self.serial.is_open:
                return True
            
            parity_value = {
                "N": PARITY_NONE,
                "E": PARITY_EVEN,
                "O": PARITY_ODD,
            }.get(self.parity.upper(), PARITY_NONE)

            bytesize_value = {
                7: SEVENBITS,
                8: EIGHTBITS,
            }.get(self.bytesize, EIGHTBITS)

            stopbits_value = {
                1: STOPBITS_ONE,
                2: STOPBITS_TWO,
            }.get(self.stopbits, STOPBITS_ONE)

            self.serial = Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=self.timeout,
                parity=parity_value,
                bytesize=bytesize_value,
                stopbits=stopbits_value,
            )
            
            if self.serial.is_open:
                logger.info(
                    "成功连接串口: %s @ %s baud (%s%s%g)",
                    self.port,
                    self.baudrate,
                    self.bytesize,
                    self.parity.upper(),
                    self.stopbits,
                )
                return True
            else:
                logger.error(f"无法打开串口: {self.port}")
                return False
                
        except SerialException as e:
            logger.error(f"串口连接失败: {e}")
            self.serial = None
            return False
    
    def disconnect(self):
        """断开串口连接"""
        if self.serial and self.serial.is_open:
            try:
                self.serial.close()
                logger.info(f"已断开串口: {self.port}")
            except Exception as e:
                logger.error(f"关闭串口失败: {e}")
            self.serial = None
    
    def register_callback(self, callback: Callable[[bytes], None]):
        """注册数据回调（原始字节流）"""
        with self.lock:
            if callback not in self.callbacks:
                self.callbacks.append(callback)
    
    def unregister_callback(self, callback: Callable[[bytes], None]):
        """取消注册回调"""
        with self.lock:
            if callback in self.callbacks:
                self.callbacks.remove(callback)
    
    def run(self):
        """线程主循环"""
        self.running = True
        
        if not self.connect():
            logger.error("初始化失败，无法连接串口")
            self.running = False
            return
        
        try:
            while self.running:
                try:
                    # 从串口读取数据
                    if self.serial and self.serial.in_waiting > 0:
                        data = self.serial.read(self.serial.in_waiting)
                        
                        with self.lock:
                            self.bytes_received += len(data)
                            self.chunks_received += 1
                        
                        # 将数据推送到队列和回调
                        try:
                            if not self.raw_data_queue.full():
                                self.raw_data_queue.put_nowait(data)
                        except queue.Full:
                            logger.warning("原始数据队列已满，丢弃最新数据块")

                        with self.lock:
                            callbacks = self.callbacks.copy()
                        for callback in callbacks:
                            try:
                                callback(data)
                            except Exception as e:
                                logger.error(f"回调函数执行失败: {e}")
                    
                    else:
                        # 没有可读数据时短暂延迟，避免 CPU 占用过高
                        time.sleep(0.01)
                
                except SerialException as e:
                    logger.error(f"读取串口出错: {e}")
                    with self.lock:
                        self.errors += 1
                    
                    # 尝试重新连接
                    self.disconnect()
                    time.sleep(1.0)
                    if not self.connect():
                        self.running = False
                
                except Exception as e:
                    logger.error(f"处理数据时出错: {e}")
                    with self.lock:
                        self.errors += 1
                    time.sleep(0.1)
        
        finally:
            self.disconnect()
            self.running = False
            logger.info("AOA 串口读取线程已停止")
    
    def stop(self):
        """停止读取线程"""
        self.running = False
    
    def get_latest_data(self, timeout: float = 1.0) -> Optional[bytes]:
        """获取最新原始数据块"""
        try:
            return self.raw_data_queue.get(timeout=timeout)
        except queue.Empty:
            return None
    
    def get_statistics(self) -> dict:
        """获取统计信息"""
        with self.lock:
            return {
                'port': self.port,
                'baudrate': self.baudrate,
                'bytesize': self.bytesize,
                'parity': self.parity,
                'stopbits': self.stopbits,
                'is_running': self.running,
                'bytes_received': self.bytes_received,
                'chunks_received': self.chunks_received,
                'errors': self.errors,
                'queue_size': self.raw_data_queue.qsize(),
                'parser_stats': {}
            }
    
    def test_received_data(self):
        """测试接收原始数据"""
        try:
            self.connect()
            data = self.get_latest_data(timeout=5)
            if data:
                preview_hex = data[:32].hex(" ")
                preview_ascii = _format_ascii_preview(data, 80)
                logger.info(
                    "Received %d bytes | HEX: %s | ASCII: %s",
                    len(data), preview_hex, preview_ascii,
                )
            else:
                logger.warning("No data received within the timeout period.")
        except SerialException as e:
            logger.error(f"Serial exception occurred: {e}")
        finally:
            self.disconnect()

class ASCIIProtocolParser:
    """解析设备输出的ASCII日志，提取SEQ、RSSI/SNR、距离与方位角。"""

    def __init__(self):
        self.last_seq: Optional[int] = None
        self._re_seq = re.compile(r"Custom\s+DS-TWR\s+Responder\s+SEQ\s+NUM\s+(\d+)")
        self._re_rssi = re.compile(r"RSSI:\s*(-?\d+)dBm,\s*SNR:\s*(\d+)dB")
        self._re_peer = re.compile(r"Peer\s+(\S+),\s*Distance\s+(\d+)cm,\s*PDoA\s+Azimuth\s+(-?\d+)")

    def parse_line(self, line: str) -> List[dict]:
        events: List[dict] = []
        # SEQ
        m_seq = self._re_seq.search(line)
        if m_seq:
            self.last_seq = int(m_seq.group(1))
            events.append({'type': 'seq', 'seq': self.last_seq})

        # RSSI/SNR
        m_rs = self._re_rssi.search(line)
        if m_rs:
            rssi = int(m_rs.group(1))
            snr = int(m_rs.group(2))
            events.append({'type': 'rssi_snr', 'seq': self.last_seq, 'rssi_dbm': rssi, 'snr_db': snr})

        # Peer/Distance/Azimuth
        m_peer = self._re_peer.search(line)
        if m_peer:
            peer = m_peer.group(1)
            dist_cm = int(m_peer.group(2))
            azimuth_deg = int(m_peer.group(3))
            events.append({
                'type': 'range',
                'seq': self.last_seq,
                'peer': peer,
                'distance_m': dist_cm / 100.0,
                'azimuth_deg': azimuth_deg,
            })

        return events


if __name__ == "__main__":
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    parser = argparse.ArgumentParser(description="AOA 串口数据接收测试")
    parser.add_argument("--port", required=True, help="串口名称，例如 /dev/ttyUSB0")
    parser.add_argument("--baudrate", type=int, default=115200, help="波特率，默认 115200")
    parser.add_argument("--timeout", type=float, default=1.0, help="读取超时，单位秒")
    parser.add_argument("--bytesize", type=int, choices=[7, 8], default=8, help="数据位，7 或 8，默认 8")
    parser.add_argument("--parity", choices=["N", "E", "O"], default="N", help="校验位 N/E/O，默认 N")
    parser.add_argument("--stopbits", type=int, choices=[1, 2], default=1, help="停止位 1 或 2，默认 1")
    parser.add_argument(
        "--poll",
        type=float,
        default=1.0,
        help="获取最新数据块的等待时间，单位秒",
    )
    parser.add_argument(
        "--parse",
        action="store_true",
        help="解析ASCII协议并输出提取的字段(SEQ、RSSI/SNR、距离m、Azimuth度)",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=0.0,
        help="运行时长（秒），0 表示无限制",
    )
    args = parser.parse_args()

    reader = AOASerialReader(
        port=args.port,
        baudrate=args.baudrate,
        timeout=args.timeout,
        bytesize=args.bytesize,
        parity=args.parity,
        stopbits=args.stopbits,
    )
    reader.start()
    logger.info("AOA 串口读取线程已启动，按 Ctrl+C 停止")

    try:
        text_buffer = ""
        ascii_parser = ASCIIProtocolParser() if args.parse else None
        # 记录每个 seq 的聚合字段：rssi、snr、distance_m、azimuth_deg
        records = {} if ascii_parser else None
        # 统计每秒的解析数量
        start_time = time.time()
        per_sec_counts = {} if ascii_parser else None
        total_records = 0
        while reader.is_alive():
            # 达到设定运行时长则退出循环
            if args.duration and args.duration > 0 and (time.time() - start_time) >= args.duration:
                break
            data = reader.get_latest_data(timeout=args.poll)
            if data:
                if ascii_parser:
                    # 逐行解析，保留未完成行到缓冲区
                    text_buffer += data.decode('utf-8', errors='ignore')
                    if '\n' in text_buffer:
                        lines = text_buffer.split('\n')
                        text_buffer = lines.pop()  # 保留最后可能未完整的一行
                        for line in lines:
                            line = line.strip()
                            if not line:
                                continue
                            events = ascii_parser.parse_line(line)
                            for ev in events:
                                seq = ev.get('seq')
                                if seq is None:
                                    continue
                                rec = records.get(seq) if records is not None else None
                                if rec is None and records is not None:
                                    rec = {'rssi': None, 'snr': None, 'distance_m': None, 'azimuth_deg': None}
                                # 更新记录
                                if ev['type'] == 'rssi_snr' and rec is not None:
                                    rec['rssi'] = ev.get('rssi_dbm')
                                    rec['snr'] = ev.get('snr_db')
                                elif ev['type'] == 'range' and rec is not None:
                                    rec['distance_m'] = ev.get('distance_m')
                                    rec['azimuth_deg'] = ev.get('azimuth_deg')
                                if records is not None:
                                    records[seq] = rec
                                    # 当五项数据具备时，打印一行用于调试
                                    if (
                                        rec['rssi'] is not None and
                                        rec['snr'] is not None and
                                        rec['distance_m'] is not None and
                                        rec['azimuth_deg'] is not None
                                    ):
                                        logger.info(
                                            "seq=%d, distance=%.2fm, azimuth=%ddeg, rssi=%ddBm, snr=%ddB",
                                            seq, rec['distance_m'], rec['azimuth_deg'], rec['rssi'], rec['snr']
                                        )
                                        # 更新每秒统计
                                        if per_sec_counts is not None:
                                            ts = time.time() - start_time
                                            sec_bucket = int(ts) if ts >= 0 else 0
                                            per_sec_counts[sec_bucket] = per_sec_counts.get(sec_bucket, 0) + 1
                                            total_records += 1
                                        # 输出后移除该 seq 的记录，避免重复打印
                                        records.pop(seq, None)
    except KeyboardInterrupt:
        logger.info("收到退出指令，正在停止...")
    finally:
        reader.stop()
        reader.join(timeout=2.0)
        # 打印统计结果（每秒数量与平均速率）
        if ascii_parser and per_sec_counts is not None:
            elapsed = time.time() - start_time
            effective_duration = args.duration if (args.duration and args.duration > 0) else elapsed
            # 构造按秒排序的分布
            distribution = []
            if effective_duration > 0:
                max_bucket = int(effective_duration)
                for i in range(max_bucket):
                    distribution.append(per_sec_counts.get(i, 0))
            avg_rate = (total_records / effective_duration) if effective_duration > 0 else 0.0
            logger.info("运行时长: %.2fs, 总条数: %d, 平均每秒: %.2f", effective_duration, total_records, avg_rate)
            logger.info("每秒分布: %s", distribution)
        logger.info("统计信息: %s", reader.get_statistics())
