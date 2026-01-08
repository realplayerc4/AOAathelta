"""
主窗口 - AMR 设备监控系统
"""
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
from ui.widgets.map_viewer import MapViewerDialog
from workers.api_worker import APIWorker
from workers.map_worker import MapAPIWorker
from models.device import Device
from models.map import Map
from core.ws_subscriber import TopicSubscriber
from utils.config_loader import load_topics_from_file


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
        self.ws_subscriber = None
        self._topic_relay = _TopicRelay()
        self._topic_relay.topic_message.connect(self._on_topic_message_ui)
        self._topic_relay.topic_error.connect(self._on_topic_error_ui)
        self.latest_map_data = None  # 保存最新的地图数据
        self.map_viewer_dialog = None  # 地图查看器对话框
        self.map_receive_count = 0  # 地图接收计数
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
        
        # 显示实时地图按钮
        self.show_map_button = QPushButton("📍 显示实时地图")
        self.show_map_button.clicked.connect(self._on_show_map_clicked)
        self.show_map_button.setMinimumHeight(45)
        self.show_map_button.setStyleSheet("""
            QPushButton {
                background-color: #FF9800;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #F57C00;
            }
            QPushButton:pressed {
                background-color: #E65100;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        
        control_layout.addWidget(self.fetch_button, 2)
        control_layout.addWidget(self.fetch_maps_button, 2)
        control_layout.addWidget(self.show_map_button, 2)
        control_layout.addWidget(self.clear_button, 1)
        
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
            }
            QTabBar::tab:selected {
                background-color: #ffffff;
                font-weight: bold;
            }
        """)
        
        # 表格视图标签页
        self.device_table = DeviceTableWidget()
        self.tab_widget.addTab(self.device_table, "📊 设备信息")
        
        # 地图列表标签页
        self.map_table = MapTableWidget()
        self.tab_widget.addTab(self.map_table, "🗺️ 地图列表")
        
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
    
    def _on_show_map_clicked(self):
        """处理显示实时地图按钮点击事件"""
        if not self.latest_map_data:
            QMessageBox.information(
                self,
                "无地图数据",
                "尚未接收到地图数据。\n\n"
                "请确保：\n"
                "1. WebSocket 连接正常\n"
                "2. /map 话题已在 topics.txt 中配置\n"
                "3. 设备正在发布地图数据\n\n"
                f"已接收地图次数: {self.map_receive_count}"
            )
            return
        
        # 创建或显示地图查看器
        if not self.map_viewer_dialog:
            self.map_viewer_dialog = MapViewerDialog(self)
        
        self.map_viewer_dialog.update_map(self.latest_map_data)
        self.map_viewer_dialog.show()
        self.map_viewer_dialog.raise_()
        self.map_viewer_dialog.activateWindow()
        
        # 更新按钮文本显示接收次数
        self.show_map_button.setText(f"📍 显示实时地图 ({self.map_receive_count})")

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
            
            # 更新状态栏显示更详细的地图信息
            self.status_bar.showMessage(
                f"🗺️ 地图已更新 (#{self.map_receive_count}) - "
                f"{size[0]}×{size[1]}px, {resolution}m/px, {data_size}KB",
                5000
            )
            
            # 如果地图查看器已打开，自动更新
            if self.map_viewer_dialog and self.map_viewer_dialog.isVisible():
                self.map_viewer_dialog.update_map(payload)
        
        # 处理追踪位置话题
        elif topic == "/tracked_pose":
            try:
                # 验证数据格式
                if not isinstance(payload, dict):
                    return
                
                # 提取位置和朝向
                if "pos" in payload and "ori" in payload:
                    pos = payload["pos"]
                    ori = payload["ori"]
                    
                    # 验证位置格式
                    if isinstance(pos, (list, tuple)) and len(pos) >= 2:
                        pose_data = {
                            "pos": [float(pos[0]), float(pos[1])],
                            "ori": float(ori)
                        }
                        
                        # 更新状态栏
                        self.status_bar.showMessage(
                            f"📍 AMR位置: ({pose_data['pos'][0]:.2f}, {pose_data['pos'][1]:.2f})m, "
                            f"朝向: {pose_data['ori']:.2f}rad",
                            3000
                        )
                        
                        # 如果地图查看器已打开，更新追踪位置
                        if self.map_viewer_dialog and self.map_viewer_dialog.isVisible():
                            self.map_viewer_dialog.update_tracked_pose(pose_data)
                    elif isinstance(pos, dict) and "x" in pos and "y" in pos:
                        pose_data = {
                            "pos": [float(pos["x"]), float(pos["y"])],
                            "ori": float(ori)
                        }
                        
                        # 更新状态栏
                        self.status_bar.showMessage(
                            f"📍 AMR位置: ({pose_data['pos'][0]:.2f}, {pose_data['pos'][1]:.2f})m, "
                            f"朝向: {pose_data['ori']:.2f}rad",
                            3000
                        )
                        
                        # 如果地图查看器已打开，更新追踪位置
                        if self.map_viewer_dialog and self.map_viewer_dialog.isVisible():
                            self.map_viewer_dialog.update_tracked_pose(pose_data)
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

    def closeEvent(self, event):
        """窗口关闭时清理后台线程"""
        if self.ws_subscriber:
            self.ws_subscriber.stop()
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
