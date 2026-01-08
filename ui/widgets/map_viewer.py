"""
地图查看器 - 显示实时地图数据
"""
import base64
from datetime import datetime
from io import BytesIO
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QWidget, QTextEdit, QGroupBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage


class MapViewerDialog(QDialog):
    """地图查看对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_map_data = None
        self.last_update_time = None
        self.map_receive_count = 0
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化UI"""
        self.setWindowTitle("实时地图查看器")
        self.setMinimumSize(900, 700)
        
        layout = QVBoxLayout(self)
        
        # 状态信息组
        status_group = QGroupBox("📊 地图状态")
        status_layout = QVBoxLayout(status_group)
        
        # 地图基本信息标签
        self.info_label = QLabel("暂无地图数据")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.info_label.setStyleSheet("""
            QLabel {
                background-color: #f0f0f0;
                padding: 8px;
                border-radius: 3px;
                font-size: 11px;
                font-family: monospace;
            }
        """)
        status_layout.addWidget(self.info_label)
        
        # 更新状态标签
        self.status_label = QLabel("等待接收地图数据...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #e3f2fd;
                padding: 6px;
                border-radius: 3px;
                font-size: 10px;
                color: #1976d2;
            }
        """)
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(status_group)
        
        # 滚动区域用于显示地图
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 地图显示标签
        self.map_label = QLabel("等待地图数据...")
        self.map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_label.setMinimumSize(400, 300)
        self.map_label.setStyleSheet("""
            QLabel {
                background-color: #e0e0e0;
                border: 2px dashed #999999;
            }
        """)
        
        scroll_area.setWidget(self.map_label)
        layout.addWidget(scroll_area, 1)
        
        # 详细信息文本框
        details_group = QGroupBox("📝 详细信息")
        details_layout = QVBoxLayout(details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(100)
        self.details_text.setStyleSheet("""
            QTextEdit {
                background-color: #f5f5f5;
                border: 1px solid #ddd;
                font-family: monospace;
                font-size: 10px;
            }
        """)
        self.details_text.setPlainText("等待地图数据...")
        details_layout.addWidget(self.details_text)
        
        layout.addWidget(details_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        
        refresh_button = QPushButton("🔄 刷新显示")
        refresh_button.clicked.connect(self._refresh_map)
        refresh_button.setMinimumHeight(35)
        refresh_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        close_button.setMinimumHeight(35)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #757575;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12px;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton:hover {
                background-color: #616161;
            }
        """)
        
        button_layout.addWidget(refresh_button)
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
    
    def update_map(self, map_data: dict):
        """
        更新地图数据并显示
        
        Args:
            map_data: 包含地图信息的字典
        """
        self.current_map_data = map_data
        self.last_update_time = datetime.now()
        self.map_receive_count += 1
        self._refresh_map()
    
    def _validate_map_data(self, map_data: dict) -> tuple[bool, str]:
        """
        验证地图数据的完整性
        
        Returns:
            (是否有效, 错误信息)
        """
        if not map_data:
            return False, "地图数据为空"
        
        # 检查必需字段
        required_fields = ['topic', 'resolution', 'size', 'origin', 'data']
        missing_fields = [f for f in required_fields if f not in map_data]
        if missing_fields:
            return False, f"缺少字段: {', '.join(missing_fields)}"
        
        # 验证 topic
        if map_data.get('topic') != '/map':
            return False, f"错误的话题: {map_data.get('topic')}"
        
        # 验证 resolution
        resolution = map_data.get('resolution')
        if not isinstance(resolution, (int, float)) or resolution <= 0:
            return False, f"无效的分辨率: {resolution}"
        
        # 验证 size
        size = map_data.get('size')
        if not isinstance(size, list) or len(size) != 2:
            return False, f"无效的尺寸格式: {size}"
        if not all(isinstance(s, int) and s > 0 for s in size):
            return False, f"无效的尺寸值: {size}"
        
        # 验证 origin
        origin = map_data.get('origin')
        if not isinstance(origin, list) or len(origin) != 2:
            return False, f"无效的原点格式: {origin}"
        if not all(isinstance(o, (int, float)) for o in origin):
            return False, f"无效的原点值: {origin}"
        
        # 验证 data
        data = map_data.get('data', '')
        if not data:
            return False, "地图数据为空"
        if not isinstance(data, str):
            return False, "地图数据格式错误"
        
        return True, "数据验证通过"
    
    def _calculate_map_metrics(self, map_data: dict) -> dict:
        """
        计算地图的各种度量指标
        
        Returns:
            包含度量指标的字典
        """
        resolution = map_data.get('resolution', 0)
        size = map_data.get('size', [0, 0])
        origin = map_data.get('origin', [0, 0])
        data = map_data.get('data', '')
        
        # 计算实际尺寸（米）
        width_m = size[0] * resolution
        height_m = size[1] * resolution
        
        # 计算地图覆盖范围
        x_min = origin[0]
        y_min = origin[1]
        x_max = x_min + width_m
        y_max = y_min + height_m
        
        # 计算数据大小
        data_size_bytes = len(data) * 3 // 4  # Base64 解码后的大约大小
        data_size_kb = data_size_bytes / 1024
        
        return {
            'width_m': width_m,
            'height_m': height_m,
            'area_m2': width_m * height_m,
            'x_range': (x_min, x_max),
            'y_range': (y_min, y_max),
            'data_size_kb': data_size_kb,
            'pixel_count': size[0] * size[1]
        }
    
    def _refresh_map(self):
        """刷新地图显示"""
        if not self.current_map_data:
            self.info_label.setText("暂无地图数据")
            self.status_label.setText("等待接收地图数据...")
            self.details_text.setPlainText("等待地图数据...")
            self.map_label.setText("等待地图数据...")
            return
        
        try:
            # 验证地图数据
            is_valid, validation_msg = self._validate_map_data(self.current_map_data)
            
            if not is_valid:
                self.info_label.setText(f"❌ 数据验证失败")
                self.status_label.setText(f"错误: {validation_msg}")
                self.status_label.setStyleSheet("""
                    QLabel {
                        background-color: #ffebee;
                        padding: 6px;
                        border-radius: 3px;
                        font-size: 10px;
                        color: #c62828;
                    }
                """)
                self.details_text.setPlainText(f"验证失败: {validation_msg}")
                self.map_label.setText(f"❌ {validation_msg}")
                self.map_label.setPixmap(QPixmap())
                return
            
            # 提取地图信息
            resolution = self.current_map_data.get('resolution', 'N/A')
            size = self.current_map_data.get('size', [0, 0])
            origin = self.current_map_data.get('origin', [0, 0])
            base64_data = self.current_map_data.get('data', '')
            
            # 计算地图度量
            metrics = self._calculate_map_metrics(self.current_map_data)
            
            # 更新基本信息标签
            info_text = (
                f"✓ 分辨率: {resolution} m/px  |  "
                f"尺寸: {size[0]}×{size[1]} px ({metrics['width_m']:.1f}×{metrics['height_m']:.1f} m)  |  "
                f"原点: ({origin[0]}, {origin[1]}) m"
            )
            self.info_label.setText(info_text)
            
            # 更新状态标签
            update_time_str = self.last_update_time.strftime("%H:%M:%S") if self.last_update_time else "未知"
            status_text = (
                f"✓ 数据有效  |  更新时间: {update_time_str}  |  "
                f"接收次数: {self.map_receive_count}  |  数据大小: {metrics['data_size_kb']:.1f} KB"
            )
            self.status_label.setText(status_text)
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #e8f5e9;
                    padding: 6px;
                    border-radius: 3px;
                    font-size: 10px;
                    color: #2e7d32;
                }
            """)
            
            # 更新详细信息
            details_lines = [
                f"话题: {self.current_map_data.get('topic')}",
                f"分辨率: {resolution} 米/像素",
                f"图像尺寸: {size[0]} × {size[1]} 像素",
                f"实际尺寸: {metrics['width_m']:.2f} × {metrics['height_m']:.2f} 米",
                f"覆盖面积: {metrics['area_m2']:.2f} 平方米",
                f"原点坐标: ({origin[0]}, {origin[1]}) 米",
                f"X 范围: {metrics['x_range'][0]:.2f} 至 {metrics['x_range'][1]:.2f} 米",
                f"Y 范围: {metrics['y_range'][0]:.2f} 至 {metrics['y_range'][1]:.2f} 米",
                f"像素总数: {metrics['pixel_count']:,}",
                f"数据大小: {metrics['data_size_kb']:.2f} KB",
                f"最后更新: {update_time_str}",
                f"接收计数: {self.map_receive_count}",
                f"验证状态: {validation_msg}"
            ]
            self.details_text.setPlainText("\n".join(details_lines))
            
            # 解码并显示图片
            if base64_data:
                try:
                    # 解码 base64 数据
                    image_data = base64.b64decode(base64_data)
                    
                    # 创建 QImage
                    qimage = QImage()
                    if qimage.loadFromData(image_data):
                        # 转换为 QPixmap 并显示
                        pixmap = QPixmap.fromImage(qimage)
                        
                        # 缩放图片以适应窗口（保持宽高比）
                        scaled_pixmap = pixmap.scaled(
                            self.map_label.size(),
                            Qt.AspectRatioMode.KeepAspectRatio,
                            Qt.TransformationMode.SmoothTransformation
                        )
                        
                        self.map_label.setPixmap(scaled_pixmap)
                        self.map_label.setStyleSheet("""
                            QLabel {
                                background-color: white;
                                border: 2px solid #4CAF50;
                            }
                        """)
                    else:
                        self.map_label.setText("❌ 无法加载图片数据\n图片格式可能不正确")
                        self.map_label.setPixmap(QPixmap())
                        self.map_label.setStyleSheet("""
                            QLabel {
                                background-color: #ffebee;
                                border: 2px solid #f44336;
                                color: #c62828;
                            }
                        """)
                except Exception as img_error:
                    self.map_label.setText(f"❌ 图片解码失败\n{str(img_error)}")
                    self.map_label.setPixmap(QPixmap())
                    self.map_label.setStyleSheet("""
                        QLabel {
                            background-color: #ffebee;
                            border: 2px solid #f44336;
                            color: #c62828;
                        }
                    """)
            else:
                self.map_label.setText("❌ 地图数据为空")
                self.map_label.setPixmap(QPixmap())
                
        except Exception as e:
            error_msg = f"错误: {str(e)}"
            self.info_label.setText(f"❌ 处理失败")
            self.status_label.setText(error_msg)
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #ffebee;
                    padding: 6px;
                    border-radius: 3px;
                    font-size: 10px;
                    color: #c62828;
                }
            """)
            self.details_text.setPlainText(f"解析地图数据时发生错误:\n{str(e)}")
            self.map_label.setText(f"❌ 解析地图数据失败\n{str(e)}")
            self.map_label.setPixmap(QPixmap())
    
    def resizeEvent(self, event):
        """窗口大小改变时重新调整地图显示"""
        super().resizeEvent(event)
        if self.current_map_data and self.map_label.pixmap():
            self._refresh_map()
