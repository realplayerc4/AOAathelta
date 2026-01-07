"""
地图列表显示组件
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QScrollArea,
    QLabel, QFrame, QDialog, QPushButton
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QPointF
from PyQt6.QtGui import (
    QPixmap, QColor, QCursor, QPainter, QPen, QFont
)
from typing import List
import requests
import config
from models.map import Map


class ImageViewDialog(QDialog):
    """显示完整图片的对话框，支持叠加标记点"""
    
    def __init__(self, parent=None, map_obj: Map | None = None):
        super().__init__(parent)
        self.map_obj = map_obj
        self.image_url = (map_obj.image_url or map_obj.thumbnail_url) if map_obj else None
        self.full_pixmap = None
        self.landmarks = None
        self.setWindowTitle(f"地图详情 - {map_obj.name}" if map_obj else "地图详情")
        self.setModal(True)
        self.resize(800, 600)
        self._setup_ui()
        
        if self.image_url:
            self._load_full_image()
        if map_obj:
            self._load_landmarks()
    
    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        
        # 图片显示标签
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #000000;
                border: 2px solid #444444;
                color: #888888;
            }
        """)
        self.image_label.setText("加载中...")
        
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.image_label)
        scroll_area.setWidgetResizable(True)
        layout.addWidget(scroll_area)
        
        # 状态信息
        self.status_label = QLabel("正在加载地图和标记点...")
        self.status_label.setStyleSheet("color: #CCCCCC; font-size: 12px;")
        layout.addWidget(self.status_label)
        
        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.close)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px;
                font-size: 14px;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        layout.addWidget(close_btn)
    
    def _load_full_image(self):
        """加载完整图片"""
        self.downloader = ImageDownloader("full", self.image_url)
        self.downloader.finished.connect(self._on_full_image_loaded)
        self.downloader.start()
    
    def _load_landmarks(self):
        """后台获取标记点信息"""
        self.landmark_loader = LandmarkDownloader(self.map_obj.id)
        self.landmark_loader.finished.connect(self._on_landmarks_loaded)
        self.landmark_loader.error.connect(self._on_landmarks_error)
        self.landmark_loader.start()
    
    def _on_full_image_loaded(self, _, pixmap: QPixmap):
        """完整图片加载完成"""
        self.full_pixmap = pixmap
        self.image_label.setText("")
        self.image_label.setScaledContents(False)
        self.image_label.resize(pixmap.size())
        self._maybe_render()
    
    def _on_landmarks_loaded(self, map_id: str, landmarks: list):
        """标记点加载完成"""
        if self.map_obj and self.map_obj.id != map_id:
            return
        self.landmarks = landmarks
        self.status_label.setText("标记点已加载")
        self._maybe_render()
    
    def _on_landmarks_error(self, map_id: str, message: str):
        """标记点加载失败"""
        if self.map_obj and self.map_obj.id != map_id:
            return
        # 保留图片但提示失败
        self.status_label.setText(f"标记点加载失败: {message}")
    
    def _maybe_render(self):
        """在完整图片上绘制标记点"""
        if self.full_pixmap is None:
            return
        rendered = self.full_pixmap.copy()
        if self.landmarks and self.map_obj:
            resolution = self.map_obj.resolution or (
                (self.map_obj.raw_data or {}).get('grid_resolution')
            )
            origin_x = self.map_obj.grid_origin_x or (
                (self.map_obj.raw_data or {}).get('grid_origin_x')
            )
            origin_y = self.map_obj.grid_origin_y or (
                (self.map_obj.raw_data or {}).get('grid_origin_y')
            )
            if resolution and origin_x is not None and origin_y is not None:
                painter = QPainter(rendered)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                pen = QPen(QColor("#FF5722"))
                pen.setWidth(4)
                painter.setPen(pen)
                painter.setBrush(QColor(255, 87, 34, 150))
                painter.setFont(QFont("Arial", 10, QFont.Weight.Bold))
                h = rendered.height()
                w = rendered.width()
                for idx, lm in enumerate(self.landmarks):
                    x = lm.get('x')
                    y = lm.get('y')
                    name = lm.get('name') or lm.get('id') or f"LM{idx+1}"
                    if x is None or y is None:
                        continue
                    px = (x - origin_x) / resolution
                    py = h - ((y - origin_y) / resolution)
                    if 0 <= px <= w and 0 <= py <= h:
                        painter.drawEllipse(QPointF(px, py), 6, 6)
                        painter.drawText(px + 8, py - 8, name)
                painter.end()
            else:
                self.status_label.setText("缺少分辨率或原点坐标，无法绘制标记点")
        self.image_label.setPixmap(rendered)
        self.image_label.setText("")


class ImageDownloader(QThread):
    """后台下载图片的线程"""
    finished = pyqtSignal(str, QPixmap)  # map_id, pixmap
    
    def __init__(self, map_id: str, url: str):
        super().__init__()
        self.map_id = map_id
        self.url = url
    
    def run(self):
        """下载图片"""
        try:
            response = requests.get(self.url, timeout=10)
            if response.status_code == 200:
                pixmap = QPixmap()
                pixmap.loadFromData(response.content)
                if not pixmap.isNull():
                    self.finished.emit(self.map_id, pixmap)
        except Exception:
            pass  # 静默处理错误


class LandmarkDownloader(QThread):
    """后台获取地图标记点"""
    finished = pyqtSignal(str, list)  # map_id, landmarks list
    error = pyqtSignal(str, str)      # map_id, error message
    
    def __init__(self, map_id: str):
        super().__init__()
        self.map_id = map_id
        self.url = f"{config.API_BASE_URL}/mappings/{map_id}/landmarks.json"
    
    def run(self):
        try:
            response = requests.get(self.url, timeout=10)
            response.raise_for_status()
            data = response.json()
            landmarks = self._normalize_landmarks(data)
            self.finished.emit(self.map_id, landmarks)
        except Exception as e:
            self.error.emit(self.map_id, str(e))
    
    def _normalize_landmarks(self, data):
        raw_list = []
        if isinstance(data, list):
            raw_list = data
        elif isinstance(data, dict):
            if isinstance(data.get('landmarks'), list):
                raw_list = data['landmarks']
            elif isinstance(data.get('data'), list):
                raw_list = data['data']
            else:
                raw_list = [data]
        results = []
        for item in raw_list:
            if not isinstance(item, dict):
                continue
            x = item.get('x') or item.get('pos_x') or item.get('position_x')
            y = item.get('y') or item.get('pos_y') or item.get('position_y')
            name = item.get('name') or item.get('label') or item.get('id')
            if x is None or y is None:
                continue
            results.append({'x': float(x), 'y': float(y), 'name': str(name) if name else None})
        return results


class MapTableWidget(QWidget):
    """显示地图列表的组件"""
    
    def __init__(self):
        super().__init__()
        self.map_items = {}  # 存储地图项 {map_id: widget}
        self.downloaders = []  # 存储下载线程
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化UI"""
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 顶部统计信息栏
        self.info_label = QLabel("地图数量: 0")
        self.info_label.setStyleSheet("""
            QLabel {
                background-color: #1A1A1A;
                color: #FFFFFF;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
                border-bottom: 2px solid #2196F3;
            }
        """)
        main_layout.addWidget(self.info_label)
        
        # 滚动区域
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #000000;
            }
        """)
        
        # 容器widget
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setSpacing(10)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        self.container_layout.addStretch()
        
        scroll_area.setWidget(self.container)
        main_layout.addWidget(scroll_area)
    
    def load_maps(self, maps: List[Map]):
        """
        加载地图数据
        
        Args:
            maps: Map 对象列表
        """
        # 清空现有数据
        self.clear_data()
        
        # 更新统计信息
        self.info_label.setText(f"地图数量: {len(maps)}")
        
        # 为每个地图创建一个显示项
        for map_obj in maps:
            map_widget = self._create_map_item(map_obj)
            self.map_items[map_obj.id] = map_widget
            # 插入到 stretch 之前
            self.container_layout.insertWidget(
                self.container_layout.count() - 1, 
                map_widget
            )
            
            # 如果有缩略图URL，启动下载
            if map_obj.thumbnail_url:
                self._download_thumbnail(map_obj.id, map_obj.thumbnail_url)
    
    def _create_map_item(self, map_obj: Map) -> QFrame:
        """创建单个地图显示项"""
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background-color: #1A1A1A;
                border: 1px solid #333333;
                border-radius: 5px;
            }
            QFrame:hover {
                border: 1px solid #2196F3;
            }
        """)
        
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)
        
        # 缩略图区域（可点击）
        thumbnail_label = QLabel()
        thumbnail_label.setFixedSize(150, 150)
        thumbnail_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thumbnail_label.setStyleSheet("""
            QLabel {
                background-color: #000000;
                border: 2px solid #444444;
                border-radius: 5px;
                color: #888888;
            }
            QLabel:hover {
                border: 2px solid #2196F3;
            }
        """)
        thumbnail_label.setText("加载中...")
        thumbnail_label.setObjectName(f"thumbnail_{map_obj.id}")
        thumbnail_label.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        
        # 存储图片URL和地图信息到标签属性中
        thumbnail_label.setProperty("image_url", map_obj.thumbnail_url)
        thumbnail_label.setProperty("map_name", map_obj.name)
        
        # 设置鼠标点击事件
        thumbnail_label.mousePressEvent = lambda event: self._on_thumbnail_clicked(map_obj)
        
        layout.addWidget(thumbnail_label)
        
        # 信息区域
        info_layout = QVBoxLayout()
        info_layout.setSpacing(8)
        
        # 地图名称
        name_label = QLabel(f"<b style='color: #00FFFF; font-size: 16px;'>{map_obj.name}</b>")
        name_label.setStyleSheet("color: #FFFFFF;")
        info_layout.addWidget(name_label)
        
        # 地图ID
        id_label = QLabel(f"地图ID: {map_obj.id}")
        id_label.setStyleSheet("color: #CCCCCC; font-size: 12px;")
        info_layout.addWidget(id_label)
        
        # 描述
        if map_obj.description:
            desc_label = QLabel(f"描述: {map_obj.description}")
            desc_label.setStyleSheet("color: #AAAAAA; font-size: 12px;")
            desc_label.setWordWrap(True)
            info_layout.addWidget(desc_label)
        
        # 详细信息
        details = []
        if map_obj.resolution is not None:
            details.append(f"分辨率: {map_obj.resolution:.3f}")
        if map_obj.grid_origin_x is not None and map_obj.grid_origin_y is not None:
            details.append(f"原点坐标: ({map_obj.grid_origin_x:.2f}, {map_obj.grid_origin_y:.2f})")
        if map_obj.size:
            details.append(f"大小: {map_obj.size}")
        if map_obj.created_at:
            details.append(f"创建时间: {map_obj.created_at}")
        
        if details:
            details_label = QLabel(" | ".join(details))
            details_label.setStyleSheet("color: #888888; font-size: 11px;")
            details_label.setWordWrap(True)
            info_layout.addWidget(details_label)
        
        info_layout.addStretch()
        layout.addLayout(info_layout, 1)
        
        return frame
    
    def _download_thumbnail(self, map_id: str, url: str):
        """启动缩略图下载"""
        downloader = ImageDownloader(map_id, url)
        downloader.finished.connect(self._on_thumbnail_downloaded)
        self.downloaders.append(downloader)
        downloader.start()
    
    def _on_thumbnail_clicked(self, map_obj: Map):
        """缩略图点击事件处理"""
        image_url = map_obj.image_url or map_obj.thumbnail_url
        if image_url:
            dialog = ImageViewDialog(self, map_obj)
            dialog.exec()
    
    def _on_thumbnail_downloaded(self, map_id: str, pixmap: QPixmap):
        """缩略图下载完成"""
        if map_id in self.map_items:
            # 查找缩略图标签
            frame = self.map_items[map_id]
            thumbnail_label = frame.findChild(QLabel, f"thumbnail_{map_id}")
            if thumbnail_label:
                # 缩放图片以适应标签
                scaled_pixmap = pixmap.scaled(
                    thumbnail_label.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
                thumbnail_label.setPixmap(scaled_pixmap)
                thumbnail_label.setText("")  # 清除"加载中..."文本
    
    def clear_data(self):
        """清空数据"""
        # 停止所有下载
        for downloader in self.downloaders:
            downloader.quit()
            downloader.wait()
        self.downloaders.clear()
        
        # 清除所有地图项
        for map_id, widget in self.map_items.items():
            widget.deleteLater()
        self.map_items.clear()
        
        # 重置统计
        self.info_label.setText("地图数量: 0")
