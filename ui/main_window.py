"""
主窗口 - AMR 设备监控系统
"""
import logging
import time
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QTabWidget, QMessageBox,
    QStatusBar, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject
from PyQt6.QtGui import QFont
import json
import config
from ui.widgets.device_table import DeviceTableWidget
from ui.widgets.map_table import MapTableWidget
from ui.widgets.map_viewer import MapViewerDialog, MapViewerWidget
from ui.widgets.aoa_viewer import AOADataWidget, AOAPositionViewer
from workers.api_worker import APIWorker
from workers.map_worker import MapAPIWorker
from workers.aoa_worker import AOAWorker
from models.device import Device
from models.map import Map
from core.ws_subscriber import TopicSubscriber
from utils.config_loader import load_topics_from_file


logger = logging.getLogger(__name__)


class _TopicRelay(QObject):
    """将后台线程的 WebSocket 消息转发到主线程"""
    topic_message = pyqtSignal(str, object)
    topic_error = pyqtSignal(str)


class MainWindow(QMainWindow):
    """主应用窗口"""
    
    def __init__(self):
        super().__init__()
        self.api_worker = None
        self.map_worker = None
        self.aoa_worker = None
        self.ws_subscriber = None
        self._topic_relay = _TopicRelay()
        self._topic_relay.topic_message.connect(self._on_topic_message_ui)
        self._topic_relay.topic_error.connect(self._on_topic_error_ui)
        self.latest_map_data = None  # 保存最新的地图数据
        self.map_viewer_dialog = None  # 地图查看器对话框
        self.map_viewer_widget = None  # 地图查看器组件（选项卡）
        self.aoa_position_viewer = None  # AOA 位置查看器
        self.map_receive_count = 0  # 地图接收计数
        self.beacon_global_position = None  # 保存 beacon 全局坐标
        self.latest_filtered_beacon = None  # 保存最新的滤波后的 beacon 局部坐标 {"m_filter_x": float, "m_filter_y": float, "confidence": float, "tag_id": int}
        self.latest_tracked_pose = None  # 保存最新的小车位置 {"pos": [x, y], "ori": angle}
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化主窗口UI"""
        # 窗口基本设置
        self.setWindowTitle(config.WINDOW_TITLE)
        self.setMinimumSize(config.WINDOW_WIDTH, config.WINDOW_HEIGHT)
        
        # 中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(15, 15, 15, 15)
        
        # 顶部信息栏
        info_layout = QHBoxLayout()
        info_label = QLabel(f"设备序列号: {config.DEVICE_SN}")
        info_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        info_layout.addWidget(info_label)
        info_layout.addStretch()
        main_layout.addLayout(info_layout)
        
        # 控制按钮区
        control_layout = QHBoxLayout()
        
        # 获取数据按钮
        self.fetch_button = QPushButton("📡 获取设备数据")
        self.fetch_button.clicked.connect(self._on_fetch_clicked)
        self.fetch_button.setMinimumHeight(45)
        self.fetch_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:pressed {
                background-color: #3d8b40;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        # 清空按钮
        self.clear_button = QPushButton("🗑️ 清空数据")
        self.clear_button.clicked.connect(self._on_clear_clicked)
        self.clear_button.setMinimumHeight(45)
        self.clear_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:pressed {
                background-color: #c1170a;
            }
        """)
        
        # 获取地图按钮
        self.fetch_maps_button = QPushButton("🗺️ 获取地图列表")
        self.fetch_maps_button.clicked.connect(self._on_fetch_maps_clicked)
        self.fetch_maps_button.setMinimumHeight(45)
        self.fetch_maps_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
            QPushButton:pressed {
                background-color: #0969c3;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        control_layout.addWidget(self.fetch_button, 2)
        control_layout.addWidget(self.clear_button, 1)
        control_layout.addWidget(self.fetch_maps_button, 2)
        
        # AOA 滤波控制按钮
        self.filter_toggle_button = QPushButton("🔬 禁用卡尔曼滤波")
        self.filter_toggle_button.clicked.connect(self._on_filter_toggle_clicked)
        self.filter_toggle_button.setMinimumHeight(45)
        self.filter_toggle_button.setStyleSheet("""
            QPushButton {
                background-color: #9C27B0;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #7B1FA2;
            }
            QPushButton:pressed {
                background-color: #6A1B9A;
            }
        """)
        # 滤波开关按钮将在 AOA 数据选项卡内展示，不放在顶栏
        
        main_layout.addLayout(control_layout)
        
        # 标签页组件
        self.tab_widget = QTabWidget()
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QTabBar::tab {
                background-color: #e0e0e0;
                padding: 10px 20px;
                margin-right: 2px;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                color: #000000;  /* 表头文字为黑色 */
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                font-weight: bold;
                color: #000000;  /* 选中时保持黑色 */
            }
        """)
        
        # 表格视图标签页
        self.device_table = DeviceTableWidget()
        self.tab_widget.addTab(self.device_table, "📊 设备信息")
        
        # 地图列表标签页
        self.map_table = MapTableWidget()
        self.tab_widget.addTab(self.map_table, "🗺️ 地图列表")
        
        # AOA 数据标签页
        self.aoa_widget = AOADataWidget()
        # 将卡尔曼滤波开关移动到 AOA 数据选项卡内
        aoa_layout = self.aoa_widget.layout()
        if aoa_layout is not None:
            # 放在控制面板之后、数据表之前
            aoa_layout.insertWidget(2, self.filter_toggle_button)
        self.tab_widget.addTab(self.aoa_widget, "📡 AOA 数据")
        
        # 实时地图标签页
        self.map_viewer_widget = MapViewerWidget()
        self.tab_widget.addTab(self.map_viewer_widget, "🗺️ 实时地图")
        
        # 原始JSON视图标签页
        self.json_text = QTextEdit()
        self.json_text.setReadOnly(True)
        self.json_text.setPlaceholderText('点击"获取设备数据"按钮后，原始 JSON 数据将显示在这里...')
        self.json_text.setStyleSheet("""
            QTextEdit {
                font-family: 'Courier New', monospace;
                font-size: 12px;
                background-color: #000000;
                color: #00FF00;
                border: 1px solid #333333;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        self.tab_widget.addTab(self.json_text, "📄 原始 JSON")
        
        main_layout.addWidget(self.tab_widget)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪 - 点击按钮获取设备数据")
        
        # 启动 WebSocket 话题订阅
        self._start_topic_subscription()
        
        # 启动 AOA 数据接收
        self._start_aoa_worker()
    
    def _on_fetch_clicked(self):
        """处理"获取设备数据"按钮点击事件"""
        # 禁用按钮防止重复点击
        self.fetch_button.setEnabled(False)
        self.fetch_button.setText("⏳ 正在获取...")
        self.status_bar.showMessage("正在连接 API 并获取设备数据...")
        
        # 创建并启动工作线程
        self.api_worker = APIWorker()
        self.api_worker.finished.connect(self._on_fetch_success)
        self.api_worker.error.connect(self._on_fetch_error)
        self.api_worker.start()
    
    def _on_fetch_success(self, data: dict):
        """
        处理API调用成功
        
        Args:
            data: API 返回的 JSON 数据
        """
        try:
            # 解析设备数据
            devices = self._parse_devices(data)
            
            # 更新表格视图
            self.device_table.load_devices(devices)
            
            # 更新 JSON 视图
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            self.json_text.setPlainText(formatted_json)
            
            # 更新状态栏
            device_count = len(devices)
            self.status_bar.showMessage(
                f"✅ 成功获取 {device_count} 个设备的数据", 5000
            )
            
            # 显示成功消息
            QMessageBox.information(
                self,
                "获取成功",
                f"成功获取设备数据！\n\n共加载 {device_count} 个设备信息。"
            )
            
        except Exception as e:
            self._on_fetch_error(f"数据解析失败：{str(e)}")
        
        finally:
            self._reset_fetch_button()
    
    def _on_fetch_error(self, error_msg: str):
        """
        处理API调用失败
        
        Args:
            error_msg: 错误消息
        """
        self.status_bar.showMessage(f"❌ 错误：{error_msg}", 10000)
        
        QMessageBox.critical(
            self,
            "获取失败",
            f"无法获取设备数据：\n\n{error_msg}\n\n请检查：\n"
            f"1. 网络连接是否正常\n"
            f"2. API 地址是否正确 ({config.API_BASE_URL})\n"
            f"3. Secret 密钥是否有效\n"
            f"4. 设备序列号是否正确 ({config.DEVICE_SN})"
        )
        
        self._reset_fetch_button()
    
    def _reset_fetch_button(self):
        """重置获取按钮状态"""
        self.fetch_button.setEnabled(True)
        self.fetch_button.setText("📡 获取设备数据")
    
    def _on_clear_clicked(self):
        """处理"清空数据"按钮点击事件"""
        # 清空所有表格和JSON视图
        self.device_table.clear_data()
        self.map_table.clear_data()
        self.json_text.clear()
        
        # 更新状态栏
        self.status_bar.showMessage("数据已清空", 3000)
    
    def _on_fetch_maps_clicked(self):
        """处理"获取地图列表"按钮点击事件"""
        # 禁用按钮防止重复点击
        self.fetch_maps_button.setEnabled(False)
        self.fetch_maps_button.setText("⏳ 正在获取...")
        self.status_bar.showMessage("正在连接 API 并获取地图列表...")
        
        # 创建并启动工作线程
        self.map_worker = MapAPIWorker()
        self.map_worker.finished.connect(self._on_fetch_maps_success)
        self.map_worker.error.connect(self._on_fetch_maps_error)
        self.map_worker.start()
    
    def _on_fetch_maps_success(self, data: dict):
        """
        处理地图API调用成功
        
        Args:
            data: API 返回的地图 JSON 数据
        """
        try:
            # 解析地图数据
            maps = self._parse_maps(data)
            
            # 更新地图表格视图
            self.map_table.load_maps(maps)
            
            # 更新 JSON 视图
            formatted_json = json.dumps(data, indent=2, ensure_ascii=False)
            self.json_text.setPlainText(formatted_json)
            
            # 切换到地图列表标签页
            self.tab_widget.setCurrentIndex(1)
            
            # 更新状态栏
            map_count = len(maps)
            self.status_bar.showMessage(
                f"✅ 成功获取 {map_count} 个地图", 5000
            )
            
            # 显示成功消息
            QMessageBox.information(
                self,
                "获取成功",
                f"成功获取地图列表！\n\n共加载 {map_count} 个地图。"
            )
            
        except Exception as e:
            self._on_fetch_maps_error(f"数据解析失败：{str(e)}")
        
        finally:
            self._reset_fetch_maps_button()
    
    def _on_fetch_maps_error(self, error_msg: str):
        """
        处理地图API调用失败
        
        Args:
            error_msg: 错误消息
        """
        self.status_bar.showMessage(f"❌ 错误：{error_msg}", 10000)
        
        QMessageBox.critical(
            self,
            "获取失败",
            f"无法获取地图列表：\n\n{error_msg}\n\n请检查：\n"
            f"1. 网络连接是否正常\n"
            f"2. API 地址是否正确 ({config.API_BASE_URL}/maps)\n"
            f"3. Secret 密钥是否有效"
        )
        
        self._reset_fetch_maps_button()
    
    def _reset_fetch_maps_button(self):
        """重置获取地图按钮状态"""
        self.fetch_maps_button.setEnabled(True)
        self.fetch_maps_button.setText("🗺️ 获取地图列表")
    
    

    def _on_filter_toggle_clicked(self):
        """处理卡尔曼滤波启用/禁用按钮点击事件"""
        if not self.aoa_worker:
            QMessageBox.warning(
                self,
                "AOA 工作线程未启动",
                "AOA 工作线程尚未初始化。"
            )
            return
        
        # 根据当前状态切换
        if self.aoa_worker.filter_enabled:
            # 禁用滤波
            self.aoa_worker.enable_filter(False)
            self.filter_toggle_button.setText("🔬 启用卡尔曼滤波")
            self.filter_toggle_button.setStyleSheet("""
                QPushButton {
                    background-color: #607D8B;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #455A64;
                }
                QPushButton:pressed {
                    background-color: #37474F;
                }
            """)
            self.aoa_widget.add_status_message("✅ 卡尔曼滤波已禁用")
        else:
            # 启用滤波
            self.aoa_worker.enable_filter(True)
            self.filter_toggle_button.setText("🔬 禁用卡尔曼滤波")
            self.filter_toggle_button.setStyleSheet("""
                QPushButton {
                    background-color: #9C27B0;
                    color: white;
                    border: none;
                    border-radius: 5px;
                    font-size: 14px;
                    font-weight: bold;
                    padding: 10px;
                }
                QPushButton:hover {
                    background-color: #7B1FA2;
                }
                QPushButton:pressed {
                    background-color: #6A1B9A;
                }
            """)
            self.aoa_widget.add_status_message("✅ 卡尔曼滤波已启用")

    # --- WebSocket topic subscription ---
    def _start_topic_subscription(self):
        # 从文件中加载要监听的话题
        topics = load_topics_from_file(config.TOPICS_FILE)
        
        if not topics:
            self.status_bar.showMessage("未从话题配置文件中加载到任何话题", 3000)
            return
        
        self.ws_subscriber = TopicSubscriber(
            url=config.API_WS_URL,
            topics=topics,
            on_message=lambda topic, payload: self._topic_relay.topic_message.emit(topic, payload),
            on_error=lambda message: self._topic_relay.topic_error.emit(message),
            reconnect_delay=3.0,
        )
        self.ws_subscriber.start()
        topics_str = ", ".join(topics)
        self.status_bar.showMessage(f"已订阅: {topics_str}", 3000)

    def _on_topic_message_ui(self, topic: str, payload):
        """主线程处理话题消息"""
        # 如果是地图话题，保存地图数据
        if topic == "/map":
            self.latest_map_data = payload
            self.map_receive_count += 1
            
            # 提取关键信息用于状态显示
            resolution = payload.get('resolution', 'N/A')
            size = payload.get('size', [0, 0])
            data_size = len(payload.get('data', '')) * 3 // 4 // 1024  # KB
            
            # 调试信息
            logger.debug(f"地图更新 #{self.map_receive_count}, beacon_global_position={self.beacon_global_position is not None}")
            
            # 更新状态栏显示更详细的地图信息
            self.status_bar.showMessage(
                f"🗺️ 地图已更新 (#{self.map_receive_count}) - "
                f"{size[0]}×{size[1]}px, {resolution}m/px, {data_size}KB",
                5000
            )
            
            # 更新选项卡中的地图查看器
            if self.map_viewer_widget:
                self.map_viewer_widget.update_map(payload)
                # 同时更新 beacon 位置（如果已知）
                if self.beacon_global_position:
                    logger.debug(f"更新widget中的beacon位置: {self.beacon_global_position}")
                    self.map_viewer_widget.update_beacon_position(self.beacon_global_position)
            
            # 如果地图对话框已打开，也更新它
            if self.map_viewer_dialog and self.map_viewer_dialog.isVisible():
                self.map_viewer_dialog.update_map(payload)
                # 同时更新 beacon 位置（如果已知）
                if self.beacon_global_position:
                    logger.debug(f"更新dialog中的beacon位置: {self.beacon_global_position}")
                    self.map_viewer_dialog.update_beacon_position(self.beacon_global_position)
        
        # 处理追踪位置话题
        elif topic == "/tracked_pose":
            try:
                # 验证数据格式
                if not isinstance(payload, dict):
                    return

                # 兼容不同的消息结构: 直接顶层 或 嵌套在 data/payload/pose 字段
                candidate = payload
                for key in ("data", "payload", "pose"):
                    if isinstance(candidate, dict) and key in candidate and isinstance(candidate[key], dict):
                        # 仅当目标字典中含有 pos/ori 或 position/theta/yaw 线索时才下钻
                        probe = candidate[key]
                        if any(k in probe for k in ("pos", "ori", "position", "theta", "yaw")):
                            candidate = probe
                            break

                def _to_float(x):
                    try:
                        return float(x)
                    except Exception:
                        return None

                # 提取位置 pos
                pos = None
                if isinstance(candidate.get("pos"), (list, tuple)) and len(candidate.get("pos")) >= 2:
                    pos = [ _to_float(candidate["pos"][0]), _to_float(candidate["pos"][1]) ]
                elif isinstance(candidate.get("pos"), dict) and {"x","y"} <= candidate["pos"].keys():
                    pos = [ _to_float(candidate["pos"]["x"]), _to_float(candidate["pos"]["y"]) ]
                elif isinstance(candidate.get("position"), dict) and {"x","y"} <= candidate["position"].keys():
                    pos = [ _to_float(candidate["position"]["x"]), _to_float(candidate["position"]["y"]) ]

                # 提取朝向 ori
                ori = None
                if "ori" in candidate:
                    ori = _to_float(candidate["ori"])
                elif "theta" in candidate:
                    ori = _to_float(candidate["theta"])
                elif "yaw" in candidate:
                    ori = _to_float(candidate["yaw"])

                if pos and None not in pos and ori is not None:
                    pose_data = { "pos": pos, "ori": ori }
                    
                    # 保存最新的小车位置（用于实时更新 beacon 全局坐标）
                    self.latest_tracked_pose = pose_data

                    # 更新状态栏
                    self.status_bar.showMessage(
                        f"📍 AMR位置: ({pose_data['pos'][0]:.2f}, {pose_data['pos'][1]:.2f})m, "
                        f"朝向: {pose_data['ori']:.2f}rad",
                        3000
                    )

                    # 重新计算并更新 beacon 全局坐标
                    self._update_beacon_global_position()
                    
                    # 旧代码保留用于日志（已由 _update_beacon_global_position 处理）
                    if self.latest_filtered_beacon is not None:
                        beacon_local = self.latest_filtered_beacon
                        # 记录局部坐标和 Anchor 信息
                        logger.info(f"【Beacon坐标计算 - 使用最新滤波坐标】")
                        logger.info(f"  1️⃣ Beacon在Anchor坐标系中的局部坐标（最新滤波）:")
                        logger.info(f"     m_filter_x={beacon_local['m_filter_x']:.3f}m (车体右侧)")
                        logger.info(f"     m_filter_y={beacon_local['m_filter_y']:.3f}m (车头前方)")
                        logger.info(f"     confidence={beacon_local['confidence']:.2f}")

                        logger.info(f"  2️⃣ Anchor在全局坐标系中的位置和朝向:")
                        logger.info(f"     x_anchor={pose_data['pos'][0]:.3f}m")
                        logger.info(f"     y_anchor={pose_data['pos'][1]:.3f}m")
                        import math
                        logger.info(f"     theta={pose_data['ori']:.3f}rad ({math.degrees(pose_data['ori']):.1f}°)")

                        # 计算全局坐标（使用最新滤波坐标）
                        beacon_global = self._transform_local_to_global(
                            local_x=beacon_local['m_filter_x'],
                            local_y=beacon_local['m_filter_y'],
                            m_anchor_x=pose_data['pos'][0],
                            m_anchor_y=pose_data['pos'][1],
                            anchor_theta=pose_data['ori']
                        )

                        # 记录全局坐标
                        logger.info(f"  3️⃣ Beacon在全局坐标系中的位置:")
                        logger.info(f"     m_x_global={beacon_global['m_x']:.3f}m")
                        logger.info(f"     m_y_global={beacon_global['m_y']:.3f}m")
                        logger.info(f"  ✅ 坐标转换完成（使用最新滤波坐标）")

                        # 保存全局坐标用于地图显示（0.01m精度处理）
                        self.beacon_global_position = {
                            'm_x': round(beacon_global['m_x'], 2),
                            'm_y': round(beacon_global['m_y'], 2),
                            'confidence': beacon_local['confidence'],
                            'tag_id': beacon_local['tag_id']
                        }
                        logger.info(f"保存beacon全局位置: x={beacon_global['m_x']:.2f}, y={beacon_global['m_y']:.2f}")

                        # 发布 /globe_beacon 话题
                        self._publish_globe_beacon(self.beacon_global_position)
                    else:
                        logger.debug("⏳ 尚未接收到滤波后的 Beacon 数据，等待 AOA 测量...")

                    # 实时更新地图查看器中的小车位置
                    if self.map_viewer_dialog and self.map_viewer_dialog.isVisible():
                        logger.debug(f"🗺️ 更新对话框中的小车位置")
                        self.map_viewer_dialog.update_tracked_pose(pose_data)

                    if self.map_viewer_widget:
                        logger.debug(f"🗺️ 更新选项卡中的小车位置")
                        self.map_viewer_widget.update_tracked_pose(pose_data)
            except (ValueError, KeyError, TypeError) as e:
                # 数据格式错误，跳过
                pass
        
        else:
            # 其他话题的正常处理
            self.status_bar.showMessage(f"WS {topic} 已更新", 2000)
        
        try:
            text = json.dumps(payload, ensure_ascii=False)
        except Exception:
            text = str(payload)
        self._append_live_log(topic, text)

    def _on_topic_error_ui(self, message: str):
        """主线程处理话题错误"""
        self.status_bar.showMessage(f"WS 错误: {message}", 5000)

    def _append_live_log(self, topic: str, text: str):
        """在 JSON 视图顶部追加最新话题消息（截断保留最近内容）"""
        prefix = f"[WS {topic}] {text}\n"
        existing = self.json_text.toPlainText()
        truncated = existing[:8000]  # 避免文本过长
        self.json_text.setPlainText(prefix + truncated)

    # --- AOA 工作线程 ---
    def _start_aoa_worker(self):
        """启动 AOA 数据接收工作线程"""
        try:
            self.aoa_worker = AOAWorker(port="/dev/ttyCH343USB0", baudrate=921600)
            
            # 连接信号
            self.aoa_worker.frame_received.connect(self._on_aoa_frame_received)
            self.aoa_worker.position_updated.connect(self._on_aoa_position_updated)
            self.aoa_worker.statistics_updated.connect(self._on_aoa_statistics_updated)
            self.aoa_worker.status_changed.connect(self._on_aoa_status_changed)
            self.aoa_worker.error.connect(self._on_aoa_error)
            
            # 启动工作线程
            self.aoa_worker.start()

            # 反映当前卡尔曼滤波启用状态
            try:
                state_text = "启用" if getattr(self.aoa_worker, "filter_enabled", False) else "禁用"
                self.status_bar.showMessage(f"卡尔曼滤波已{state_text}", 3000)
                if hasattr(self, "aoa_widget") and hasattr(self.aoa_widget, "add_status_message"):
                    self.aoa_widget.add_status_message(f"✅ 卡尔曼滤波已{state_text}")
            except Exception:
                pass
            
        except Exception as e:
            logger.warning(f"无法启动 AOA 工作线程: {e}")
    
    def _on_aoa_frame_received(self, frame_info: dict):
        """处理接收到的 AOA 帧"""
        self.aoa_widget.add_frame(frame_info)
        
        # 保存最新的滤波坐标用于 BEACON 全局坐标计算
        if 'filtered_x' in frame_info and 'filtered_y' in frame_info:
            # 获取置信度
            confidence = frame_info.get('filter_confidence', frame_info.get('confidence', 0.0))
            
            # 检查置信度是否达到阈值
            if confidence < config.BEACON_MIN_CONFIDENCE:
                logger.warning(f"⚠️ Beacon数据置信度过低({confidence:.2%} < {config.BEACON_MIN_CONFIDENCE:.2%})，已过滤")
                logger.debug(f"   被过滤的数据: x={frame_info['filtered_x']:.3f}m, y={frame_info['filtered_y']:.3f}m")
                return  # 丢弃低置信度数据
            
            # 置信度达标，保存数据
            self.latest_filtered_beacon = {
                'm_filter_x': frame_info['filtered_x'],
                'm_filter_y': frame_info['filtered_y'],
                'confidence': confidence,
                'tag_id': frame_info.get('tag_id', 1)
            }
            logger.info(f"✅ 接受Beacon数据: x={self.latest_filtered_beacon['m_filter_x']:.3f}m, "
                       f"y={self.latest_filtered_beacon['m_filter_y']:.3f}m, 置信度={confidence:.2%}")
            
            # 如果已经有小车位置信息，立即重新计算并更新 beacon 全局坐标
            self._update_beacon_global_position()
    
    def _on_aoa_position_updated(self, position: dict):
        """处理位置更新"""
        logger.debug(f"AOA 位置更新: {position}")
    
    def _on_aoa_statistics_updated(self, stats: dict):
        """处理统计信息更新"""
        self.aoa_widget.update_statistics(stats)
    
    def _on_aoa_status_changed(self, status: str):
        """处理状态变化"""
        self.aoa_widget.update_status(status)
    
    def _on_aoa_error(self, error_msg: str):
        """处理 AOA 错误"""
        logger.error(f"AOA 错误: {error_msg}")

    def closeEvent(self, event):
        """窗口关闭时清理后台线程"""
        if self.ws_subscriber:
            self.ws_subscriber.stop()
        if self.aoa_worker:
            self.aoa_worker.stop()
        super().closeEvent(event)
    
    def _parse_devices(self, data: dict) -> list[Device]:
        """
        解析 API 响应为 Device 对象列表
        
        Args:
            data: API 返回的 JSON 数据
            
        Returns:
            Device 对象列表
        """
        devices = []
        
        # 处理不同的响应格式
        if isinstance(data, list):
            # 直接是设备数组
            for item in data:
                devices.append(Device.from_dict(item))
                
        elif isinstance(data, dict):
            # 检查常见的包装键
            device_data = None
            
            # 尝试常见的键名
            for key in ['data', 'devices', 'items', 'result', 'device', 'info']:
                if key in data:
                    device_data = data[key]
                    break
            
            # 如果没找到包装键，把整个字典当作单个设备
            if device_data is None:
                device_data = data
            
            # 处理设备数据
            if isinstance(device_data, list):
                for item in device_data:
                    devices.append(Device.from_dict(item))
            else:
                # 单个设备
                devices.append(Device.from_dict(device_data))
        
        return devices
    
    def _parse_maps(self, data: dict) -> list[Map]:
        """
        解析 API 响应为 Map 对象列表
        
        Args:
            data: API 返回的 JSON 数据
            
        Returns:
            Map 对象列表
        """
        maps = []
        
        # 处理不同的响应格式
        if isinstance(data, list):
            # 直接是地图数组
            for item in data:
                maps.append(Map.from_dict(item))
                
        elif isinstance(data, dict):
            # 检查常见的包装键
            map_data = None
            
            # 尝试常见的键名（优先使用mappings）
            for key in ['mappings', 'data', 'maps', 'items', 'result', 'mapList']:
                if key in data:
                    map_data = data[key]
                    break
            
            # 如果没找到包装键，把整个字典当作单个地图
            if map_data is None:
                map_data = data
            
            # 处理地图数据
            if isinstance(map_data, list):
                for item in map_data:
                    # 过滤掉state为cancelled的地图
                    if item.get('state') != 'cancelled':
                        maps.append(Map.from_dict(item))
            else:
                # 单个地图
                if map_data.get('state') != 'cancelled':
                    maps.append(Map.from_dict(map_data))
        
        return maps
    
    def _transform_local_to_global(self, local_x: float, local_y: float, 
                                   m_anchor_x: float, m_anchor_y: float, 
                                   anchor_theta: float) -> dict:
        """
        将 Beacon 在 Anchor 坐标系中的局部坐标转换为全局坐标
        
        坐标系说明：
        - Anchor 局部坐标系：以 Anchor (小车) 为原点
          * Y 轴：车头前方（与小车朝向 theta 一致）
          * X 轴：车体右侧（垂直于朝向，右手系）
        - 小车全局位置：/tracked_pose 中的 pos (m_x, m_y)
        - anchor_theta: 小车的全局朝向（弧度），/tracked_pose 中的 ori
        
        变换公式：
        - 前方向量（Y轴）：(cos(θ), sin(θ))
        - 右侧向量（X轴）：(sin(θ), -cos(θ))  # 注意：右手系，Y轴逆时针转90°到X轴
        
        Beacon全局位置 = 小车位置 + local_y * 前方向量 + local_x * 右侧向量
        
        即：
        m_x_global = m_anchor_x + local_y * cos(theta) + local_x * sin(theta)
        m_y_global = m_anchor_y + local_y * sin(theta) - local_x * cos(theta)
        
        Args:
            local_x: Beacon 在 Anchor 坐标系中的 X 坐标（米，车体右侧为正）
            local_y: Beacon 在 Anchor 坐标系中的 Y 坐标（米，车头前方为正）
            m_anchor_x: 小车在全局坐标系中的 X 坐标（米）
            m_anchor_y: 小车在全局坐标系中的 Y 坐标（米）
            anchor_theta: 小车的全局朝向（弧度）
        
        Returns:
            {'m_x': float, 'm_y': float} - Beacon 在全局坐标系中的位置（米）
        """
        import math
        
        # 计算旋转矩阵的三角函数
        cos_theta = math.cos(anchor_theta)
        sin_theta = math.sin(anchor_theta)
        
        # 应用坐标变换
        # 前方分量：local_y * (cos_theta, sin_theta)
        # 右侧分量：local_x * (sin_theta, -cos_theta)
        m_x_global = m_anchor_x + local_y * cos_theta + local_x * sin_theta
        m_y_global = m_anchor_y + local_y * sin_theta - local_x * cos_theta
        
        # 进行0.01m精度处理，降低漂移
        m_x_global = round(m_x_global, 2)
        m_y_global = round(m_y_global, 2)
        
        return {
            'm_x': m_x_global,
            'm_y': m_y_global
        }
    
    def _update_beacon_global_position(self):
        """
        根据最新的 beacon 局部坐标和小车位置，计算并更新 beacon 全局坐标
        这个方法会在以下情况被调用：
        1. 收到新的 AOA 数据（beacon 局部坐标更新）
        2. 收到新的 tracked_pose 数据（小车位置更新）
        """
        # 检查是否有必要的数据
        if self.latest_filtered_beacon is None or self.latest_tracked_pose is None:
            return
        
        beacon_local = self.latest_filtered_beacon
        pose_data = self.latest_tracked_pose
        
        # 计算全局坐标
        beacon_global = self._transform_local_to_global(
            local_x=beacon_local['m_filter_x'],
            local_y=beacon_local['m_filter_y'],
            m_anchor_x=pose_data['pos'][0],
            m_anchor_y=pose_data['pos'][1],
            anchor_theta=pose_data['ori']
        )
        
        # 保存全局坐标
        self.beacon_global_position = {
            'm_x': beacon_global['m_x'],
            'm_y': beacon_global['m_y'],
            'confidence': beacon_local['confidence'],
            'tag_id': beacon_local['tag_id']
        }
        
        logger.debug(f"🔄 Beacon全局位置已更新: ({beacon_global['m_x']:.2f}, {beacon_global['m_y']:.2f})m")
        
        # 发布 /globe_beacon 话题
        self._publish_globe_beacon(self.beacon_global_position)
        
        # 实时更新地图显示
        if self.map_viewer_dialog and self.map_viewer_dialog.isVisible():
            logger.debug(f"🗺️ 更新对话框中的beacon位置")
            self.map_viewer_dialog.update_beacon_position(self.beacon_global_position)
            
        if self.map_viewer_widget:
            logger.debug(f"🗺️ 更新选项卡中的beacon位置")
            self.map_viewer_widget.update_beacon_position(self.beacon_global_position)
    
    def _publish_globe_beacon(self, beacon_data: dict):
        """
        发布 /globe_beacon 话题（内部信号，不经过 WebSocket）
        
        Args:
            beacon_data: 包含 {'m_x': float, 'm_y': float, 'confidence': float, 'tag_id': int}
        """
        if not self.ws_subscriber:
            return
        
        # 构建话题消息
        message = {
            'topic': '/globe_beacon',
            'tag_id': beacon_data.get('tag_id', 1),
            'm_x': beacon_data.get('m_x', 0.0),
            'm_y': beacon_data.get('m_y', 0.0),
            'confidence': beacon_data.get('confidence', 0.0),
            'timestamp': time.time()
        }
        
        # 通过话题中继发送信号（模拟发布）
        self._topic_relay.topic_message.emit('/globe_beacon', message)
        
        # 同时记录日志
        logger.debug(f"发布 /globe_beacon: x={message['m_x']:.2f}, y={message['m_y']:.2f}, "
                    f"confidence={message['confidence']:.2f}")

