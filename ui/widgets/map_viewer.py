"""
地图查看器 - 显示实时地图数据
"""
import base64
import math
from datetime import datetime
from io import BytesIO
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QScrollArea, QWidget, QTextEdit, QGroupBox, QSplitter
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush


class MapViewerDialog(QDialog):
    """地图查看对话框"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_map_data = None
        self.last_update_time = None
        self.map_receive_count = 0
        self.tracked_pose = None  # 追踪位置数据 {"pos": [x, y], "ori": angle}
        self.beacon_position = None  # beacon 全局坐标 {"x": float, "y": float, "confidence": float}
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
                background-color: #263238;
                color: #4fc3f7;
                padding: 8px;
                border-radius: 3px;
                font-size: 11px;
                font-family: monospace;
                border: 1px solid #455a64;
            }
        """)
        status_layout.addWidget(self.info_label)
        
        # 更新状态标签
        self.status_label = QLabel("等待接收地图数据...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #263238;
                color: #81c784;
                padding: 6px;
                border-radius: 3px;
                font-size: 10px;
                border: 1px solid #455a64;
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
                background-color: #263238;
                color: #e0e0e0;
                border: 1px solid #455a64;
                font-family: monospace;
                font-size: 10px;
                padding: 6px;
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
    
    def update_tracked_pose(self, pose_data: dict):
        """
        更新追踪位置数据
        
        Args:
            pose_data: 包含位置和朝向信息的字典
                      {"pos": [x, y], "ori": angle_in_radians}
        """
        self.tracked_pose = pose_data
        self._refresh_map()
    
    def update_beacon_position(self, beacon_data: dict):
        """
        更新 beacon（信标）全局坐标位置
        
        Args:
            beacon_data: 包含 beacon 位置和置信度的字典
                        {"x": float, "y": float, "confidence": float, "tag_id": int}
        """
        self.beacon_position = beacon_data
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
    
    def _mark_origin_on_image(self, pixmap: QPixmap, map_data: dict) -> QPixmap:
        """
        在图像上标注坐标原点 [0, 0]
        
        Args:
            pixmap: 原始的图片像素图
            map_data: 地图数据
            
        Returns:
            标注后的图片像素图
        """
        resolution = map_data.get('resolution', 1)
        origin = map_data.get('origin', [0, 0])
        size = map_data.get('size', [0, 0])
        
        # 计算原点 [0, 0] 的像素坐标
        # origin 代表左下角的距离坐标
        # 实际坐标 (0, 0) 相对于左下角的像素位置
        origin_x_pixel = -origin[0] / resolution  # 从左边缘算起的像素位置
        origin_y_pixel_from_bottom = -origin[1] / resolution  # 从下边缘算起的像素位置
        
        # 转换为PNG坐标系（从左上角开始）
        origin_y_pixel = size[1] - origin_y_pixel_from_bottom
        
        # 创建副本用于绘制
        marked_pixmap = QPixmap(pixmap)
        
        # 检查原点是否在图像范围内
        if (0 <= origin_x_pixel < size[0] and 0 <= origin_y_pixel < size[1]):
            painter = QPainter(marked_pixmap)
            
            # 设置绿色画笔和笔刷
            green_color = QColor(0, 255, 0)  # 纯绿色
            painter.setPen(QPen(green_color, 2))
            painter.setBrush(QBrush(green_color))
            
            # 绘制标注点（圆形点，半径为5像素）
            radius = 5
            painter.drawEllipse(
                int(origin_x_pixel) - radius,
                int(origin_y_pixel) - radius,
                radius * 2,
                radius * 2
            )
            
            # 绘制十字标记
            cross_size = 10
            painter.setPen(QPen(green_color, 2))
            # 水平线
            painter.drawLine(
                int(origin_x_pixel) - cross_size,
                int(origin_y_pixel),
                int(origin_x_pixel) + cross_size,
                int(origin_y_pixel)
            )
            # 竖直线
            painter.drawLine(
                int(origin_x_pixel),
                int(origin_y_pixel) - cross_size,
                int(origin_x_pixel),
                int(origin_y_pixel) + cross_size
            )
            
            painter.end()
        
        return marked_pixmap
    
    def _mark_tracked_pose_on_image(self, pixmap: QPixmap, map_data: dict, pose_data: dict) -> QPixmap:
        """
        在图像上标注追踪位置和朝向（蓝色箭头）
        
        Args:
            pixmap: 原始的图片像素图
            map_data: 地图数据
            pose_data: 追踪位置数据 {"pos": [x, y], "ori": angle}
            
        Returns:
            标注后的图片像素图
        """
        if not pose_data or 'pos' not in pose_data or 'ori' not in pose_data:
            return pixmap
        
        resolution = map_data.get('resolution', 1)
        origin = map_data.get('origin', [0, 0])
        size = map_data.get('size', [0, 0])
        
        pos = pose_data.get('pos', [0, 0])
        ori = pose_data.get('ori', 0)  # 弧度
        
        # 计算追踪位置的像素坐标
        # pos[0], pos[1] 是基于地图坐标系的物理坐标（米）
        # origin是米单位，先相减再除以resolution
        pixel_x = (pos[0] - origin[0]) / resolution
        pixel_y_from_bottom = (pos[1] - origin[1]) / resolution
        pixel_y = size[1] - pixel_y_from_bottom  # 转换到PNG坐标系
        
        import logging
        logger = logging.getLogger(__name__)
        
        # 计算地图覆盖的全局坐标范围
        map_x_min = origin[0]
        map_x_max = origin[0] + size[0] * resolution
        map_y_min = origin[1]
        map_y_max = origin[1] + size[1] * resolution
        
        logger.info(f"🚗 小车位置标注 (Dialog):")
        logger.info(f"   物理坐标: ({pos[0]:.2f}, {pos[1]:.2f})m, 朝向: {ori:.2f}rad ({ori*180/3.14159:.1f}°)")
        logger.info(f"   地图范围: X[{map_x_min:.2f}, {map_x_max:.2f}]m, Y[{map_y_min:.2f}, {map_y_max:.2f}]m")
        logger.info(f"   像素坐标: ({pixel_x:.1f}, {pixel_y:.1f})px")
        logger.info(f"   地图尺寸: {size[0]}x{size[1]}px")
        
        # 放宽边界限制，允许超出地图范围的标注（扩展100像素）
        boundary_margin = 100
        if not (-boundary_margin <= pixel_x < size[0] + boundary_margin and 
                -boundary_margin <= pixel_y < size[1] + boundary_margin):
            logger.warning(f"   ⚠️ 小车位置严重超出显示范围，跳过标注")
            logger.warning(f"   允许范围: X[-{boundary_margin}, {size[0]+boundary_margin}]px, "
                         f"Y[-{boundary_margin}, {size[1]+boundary_margin}]px")
            return pixmap
        
        # 检查是否在实际地图范围内
        in_map_range = (0 <= pixel_x < size[0] and 0 <= pixel_y < size[1])
        if not in_map_range:
            logger.warning(f"   ⚠️ 小车位置超出地图范围但仍然标注（部分可见）")
        else:
            logger.info(f"   ✅ 小车位置在地图范围内")
        
        marked_pixmap = QPixmap(pixmap)
        painter = QPainter(marked_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 设置蓝色画笔
        blue_color = QColor(0, 150, 255)  # 深蓝色
        painter.setPen(QPen(blue_color, 2))
        painter.setBrush(QBrush(blue_color))
        
        # 绘制箭头圆点
        radius = 4
        painter.drawEllipse(
            int(pixel_x) - radius,
            int(pixel_y) - radius,
            radius * 2,
            radius * 2
        )
        
        # 绘制箭头指针
        # ori = 0 时指向X正方向（向右）
        # ori = π/2 时指向Y正方向（向上）
        arrow_length = 15
        arrow_end_x = pixel_x + arrow_length * math.cos(ori)
        arrow_end_y = pixel_y - arrow_length * math.sin(ori)  # Y轴反向（PNG坐标系）
        
        painter.setPen(QPen(blue_color, 2))
        painter.drawLine(
            int(pixel_x),
            int(pixel_y),
            int(arrow_end_x),
            int(arrow_end_y)
        )
        
        # 绘制箭头头部（三角形）
        arrow_size = 5
        angle1 = ori + math.pi * 0.85
        angle2 = ori - math.pi * 0.85
        
        point1_x = arrow_end_x + arrow_size * math.cos(angle1)
        point1_y = arrow_end_y - arrow_size * math.sin(angle1)
        point2_x = arrow_end_x + arrow_size * math.cos(angle2)
        point2_y = arrow_end_y - arrow_size * math.sin(angle2)
        
        painter.drawLine(
            int(arrow_end_x), int(arrow_end_y),
            int(point1_x), int(point1_y)
        )
        painter.drawLine(
            int(arrow_end_x), int(arrow_end_y),
            int(point2_x), int(point2_y)
        )
        
        painter.end()
        
        return marked_pixmap
    
    def _mark_beacon_on_image(self, pixmap: QPixmap, map_data: dict, beacon_data: dict) -> QPixmap:
        """
        在图像上标注 beacon（信标）位置（红色圆点）
        
        Args:
            pixmap: 原始的图片像素图
            map_data: 地图数据
            beacon_data: beacon 位置数据 {"x": float, "y": float, "confidence": float}
            
        Returns:
            标注后的图片像素图
        """
        if not beacon_data or 'x' not in beacon_data or 'y' not in beacon_data:
            return pixmap
        
        resolution = map_data.get('resolution', 1)
        origin = map_data.get('origin', [0, 0])
        size = map_data.get('size', [0, 0])
        
        beacon_x = beacon_data.get('x', 0)
        beacon_y = beacon_data.get('y', 0)
        confidence = beacon_data.get('confidence', 1.0)
        
        # 检查分辨率有效性
        if resolution <= 0:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"无效的地图分辨率: {resolution}")
            return pixmap
        
        # 计算 beacon 的像素坐标
        # beacon_x, beacon_y 是基于地图坐标系的物理坐标（米）
        # origin是米单位，先相减再除以resolution
        pixel_x = (beacon_x - origin[0]) / resolution
        pixel_y_from_bottom = (beacon_y - origin[1]) / resolution
        pixel_y = size[1] - pixel_y_from_bottom  # 转换到PNG坐标系（Y轴反向）
        
        # 调试信息
        import logging
        logger = logging.getLogger(__name__)
        
        # 计算地图覆盖的全局坐标范围
        map_x_min = origin[0]
        map_x_max = origin[0] + size[0] * resolution
        map_y_min = origin[1]
        map_y_max = origin[1] + size[1] * resolution
        
        logger.info(f"🔴 Beacon位置标注:")
        logger.info(f"   物理坐标: ({beacon_x:.2f}, {beacon_y:.2f})m, 置信度: {confidence:.2f}")
        logger.info(f"   地图范围: X[{map_x_min:.2f}, {map_x_max:.2f}]m, Y[{map_y_min:.2f}, {map_y_max:.2f}]m")
        logger.info(f"   像素坐标: ({pixel_x:.2f}, {pixel_y:.2f})px")
        logger.info(f"   地图尺寸: {size[0]}x{size[1]}px, 分辨率: {resolution}m/px")
        
        # 检查位置是否在图像范围内（放宽边界，允许部分显示）
        boundary_margin = 100
        if not (-boundary_margin <= pixel_x < size[0] + boundary_margin and 
                -boundary_margin <= pixel_y < size[1] + boundary_margin):
            logger.warning(f"   ⚠️ Beacon位置严重超出显示范围，跳过标注")
            logger.warning(f"   允许范围: X[-{boundary_margin}, {size[0]+boundary_margin}]px, "
                         f"Y[-{boundary_margin}, {size[1]+boundary_margin}]px")
            return pixmap
        
        # 检查是否在实际地图范围内
        in_map_range = (0 <= pixel_x < size[0] and 0 <= pixel_y < size[1])
        if not in_map_range:
            logger.warning(f"   ⚠️ Beacon位置超出地图范围但仍然标注（部分可见）")
        else:
            logger.info(f"   ✅ Beacon位置在地图范围内")
        
        marked_pixmap = QPixmap(pixmap)
        painter = QPainter(marked_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # 绘制置信度外圈（淡红色，先画在底层）
        outer_color = QColor(255, 100, 100, 120)
        painter.setPen(QPen(outer_color, 1))
        painter.setBrush(QBrush(outer_color))
        
        # 根据置信度调整圆点大小（置信度越高，圆点越大）
        # confidence: 0.0 -> 5px, 1.0 -> 10px
        radius = int(5 + confidence * 5)
        outer_radius = int(radius + 4)
        
        painter.drawEllipse(
            int(pixel_x) - outer_radius,
            int(pixel_y) - outer_radius,
            outer_radius * 2,
            outer_radius * 2
        )
        
        # 绘制 beacon 圆点（纯红色）
        red_color = QColor(255, 0, 0)  # 纯红色
        painter.setPen(QPen(red_color, 2))
        painter.setBrush(QBrush(red_color))
        
        painter.drawEllipse(
            int(pixel_x) - radius,
            int(pixel_y) - radius,
            radius * 2,
            radius * 2
        )
        
        # 绘制中心点（白色小点，增强可见性）
        center_color = QColor(255, 255, 255)
        painter.setPen(QPen(center_color, 1))
        painter.setBrush(QBrush(center_color))
        painter.drawEllipse(
            int(pixel_x) - 2,
            int(pixel_y) - 2,
            4,
            4
        )
        
        painter.end()
        
        logger.debug(f"Beacon标注完成: radius={radius}px")
        
        return marked_pixmap
    
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
                        background-color: #b71c1c;
                        color: #ffcdd2;
                        padding: 6px;
                        border-radius: 3px;
                        font-size: 10px;
                        border: 1px solid #c62828;
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
                    background-color: #1b5e20;
                    color: #c8e6c9;
                    padding: 6px;
                    border-radius: 3px;
                    font-size: 10px;
                    border: 1px solid #2e7d32;
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
            
            # 添加追踪位置信息 (Dialog)
            if self.tracked_pose:
                pos = self.tracked_pose.get('pos', [0, 0])
                ori = self.tracked_pose.get('ori', 0)
                in_x_range = metrics['x_range'][0] <= pos[0] <= metrics['x_range'][1]
                in_y_range = metrics['y_range'][0] <= pos[1] <= metrics['y_range'][1]
                status = "✅" if (in_x_range and in_y_range) else "⚠️ 超出范围"
                details_lines.append("")
                details_lines.append(f"🚗 小车位置: ({pos[0]:.2f}, {pos[1]:.2f})m {status}")
                details_lines.append(f"   朝向: {ori:.2f}rad ({ori*180/3.14159:.1f}°)")
            
            # 添加beacon位置信息 (Dialog)
            if self.beacon_position:
                bx = self.beacon_position.get('m_x', self.beacon_position.get('x', 0))
                by = self.beacon_position.get('m_y', self.beacon_position.get('y', 0))
                conf = self.beacon_position.get('confidence', 0)
                in_x_range = metrics['x_range'][0] <= bx <= metrics['x_range'][1]
                in_y_range = metrics['y_range'][0] <= by <= metrics['y_range'][1]
                status = "✅" if (in_x_range and in_y_range) else "⚠️ 超出范围"
                details_lines.append("")
                details_lines.append(f"🔴 Beacon位置: ({bx:.2f}, {by:.2f})m {status}")
                details_lines.append(f"   置信度: {conf:.2f}")
            
            self.details_text.setPlainText("\n".join(details_lines))
            
            # 解码并显示图片
            if base64_data:
                try:
                    # 解码 base64 数据
                    image_data = base64.b64decode(base64_data)
                    
                    # 创建 QImage
                    qimage = QImage()
                    if qimage.loadFromData(image_data):
                        # 转换为 QPixmap
                        pixmap = QPixmap.fromImage(qimage)
                        
                        # 在图像上标注坐标原点
                        pixmap = self._mark_origin_on_image(pixmap, self.current_map_data)
                        
                        # 在图像上标注追踪位置和朝向
                        if self.tracked_pose:
                            pixmap = self._mark_tracked_pose_on_image(pixmap, self.current_map_data, self.tracked_pose)
                        
                        # 在图像上标注 beacon 位置（红色圆点）
                        if self.beacon_position:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.debug(f"标注 beacon 位置: {self.beacon_position}")
                            pixmap = self._mark_beacon_on_image(pixmap, self.current_map_data, self.beacon_position)
                        else:
                            import logging
                            logger = logging.getLogger(__name__)
                            logger.debug("Beacon 位置为空，跳过标注")
                        
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
                                background-color: #b71c1c;
                                border: 2px solid #d32f2f;
                                color: #ffcdd2;
                            }
                        """)
                except Exception as img_error:
                    self.map_label.setText(f"❌ 图片解码失败\n{str(img_error)}")
                    self.map_label.setPixmap(QPixmap())
                    self.map_label.setStyleSheet("""
                        QLabel {
                            background-color: #b71c1c;
                            border: 2px solid #d32f2f;
                            color: #ffcdd2;
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
                    background-color: #b71c1c;
                    color: #ffcdd2;
                    padding: 6px;
                    border-radius: 3px;
                    font-size: 10px;
                    border: 1px solid #c62828;
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


class MapViewerWidget(QWidget):
    """地图查看器组件（用于选项卡）"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_map_data = None
        self.last_update_time = None
        self.map_receive_count = 0
        self.tracked_pose = None  # 追踪位置数据 {"pos": [x, y], "ori": angle}
        self.beacon_position = None  # beacon 全局坐标 {"x": float, "y": float, "confidence": float}
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # 创建水平分割器，左侧为地图，右侧为信息面板
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === 左侧：地图显示区域 ===
        map_container = QWidget()
        map_layout = QVBoxLayout(map_container)
        map_layout.setContentsMargins(0, 0, 0, 0)
        
        # 滚动区域用于显示地图
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 地图显示标签
        self.map_label = QLabel("等待地图数据...")
        self.map_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.map_label.setMinimumSize(600, 500)
        self.map_label.setStyleSheet("""
            QLabel {
                background-color: #e0e0e0;
                border: 2px dashed #999999;
            }
        """)
        
        scroll_area.setWidget(self.map_label)
        map_layout.addWidget(scroll_area)
        
        splitter.addWidget(map_container)
        
        # === 右侧：信息面板 ===
        info_container = QWidget()
        info_layout = QVBoxLayout(info_container)
        info_layout.setSpacing(8)
        info_layout.setContentsMargins(5, 5, 5, 5)
        
        # Beacon 坐标信息显示区域
        beacon_group = QGroupBox("🎯 Beacon 位置")
        beacon_layout = QVBoxLayout(beacon_group)
        
        self.beacon_info_label = QLabel("等待数据...")
        self.beacon_info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.beacon_info_label.setWordWrap(True)
        self.beacon_info_label.setStyleSheet("""
            QLabel {
                background-color: #1e1e1e;
                color: #00ff00;
                padding: 8px;
                border-radius: 4px;
                font-size: 11px;
                font-family: 'Courier New', monospace;
                border: 2px solid #00ff00;
                font-weight: bold;
            }
        """)
        beacon_layout.addWidget(self.beacon_info_label)
        
        info_layout.addWidget(beacon_group)
        
        # 地图状态信息组
        status_group = QGroupBox("📊 地图状态")
        status_layout = QVBoxLayout(status_group)
        
        self.info_label = QLabel("暂无地图数据")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet("""
            QLabel {
                background-color: #263238;
                color: #4fc3f7;
                padding: 5px;
                border-radius: 3px;
                font-size: 9px;
                font-family: monospace;
                border: 1px solid #455a64;
            }
        """)
        status_layout.addWidget(self.info_label)
        
        # 更新状态标签
        self.status_label = QLabel("等待接收地图数据...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("""
            QLabel {
                background-color: #263238;
                color: #81c784;
                padding: 5px;
                border-radius: 3px;
                font-size: 9px;
                border: 1px solid #455a64;
            }
        """)
        status_layout.addWidget(self.status_label)
        
        info_layout.addWidget(status_group)
        
        # 详细信息文本框
        details_group = QGroupBox("📝 详细信息")
        details_layout = QVBoxLayout(details_group)
        
        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMinimumHeight(120)
        self.details_text.setStyleSheet("""
            QTextEdit {
                background-color: #263238;
                color: #e0e0e0;
                border: 1px solid #455a64;
                font-family: monospace;
                font-size: 9px;
                padding: 5px;
            }
        """)
        self.details_text.setPlainText("等待地图数据...")
        details_layout.addWidget(self.details_text)
        
        info_layout.addWidget(details_group)
        info_layout.addStretch()  # 添加弹性空间，将内容推到顶部
        
        splitter.addWidget(info_container)
        
        # 设置分割器的初始比例（地图：信息 = 3:1）
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([800, 300])  # 初始宽度分配
        
        layout.addWidget(splitter)
    
    def update_map(self, map_data: dict):
        """更新地图显示"""
        self.current_map_data = map_data
        self.last_update_time = datetime.now()
        self.map_receive_count += 1
        self._refresh_map()
    
    def update_tracked_pose(self, pose_data: dict):
        """更新追踪位置"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"MapViewerWidget 收到 tracked_pose 更新: {pose_data}")
        self.tracked_pose = pose_data
        self._refresh_map()
    
    def update_beacon_position(self, beacon_data: dict):
        """
        更新 beacon 位置
        
        Args:
            beacon_data: {'m_x': float, 'm_y': float, 'confidence': float, 'tag_id': int}
        """
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"MapViewerWidget 收到 beacon 更新: {beacon_data}, 当前地图数据: {self.current_map_data is not None}")
        
        self.beacon_position = beacon_data
        
        # 更新 beacon 信息显示
        if beacon_data:
            beacon_x = beacon_data.get('m_x', 0)
            beacon_y = beacon_data.get('m_y', 0)
            
            if self.current_map_data:
                # 有地图数据，计算像素坐标
                resolution = self.current_map_data.get('resolution', 0.05)
                origin = self.current_map_data.get('origin', [0.0, 0.0])
                size = self.current_map_data.get('size', [0, 0])
                
                # 计算像素坐标
                pixel_x = (beacon_x - origin[0]) / resolution
                pixel_y_from_bottom = (beacon_y - origin[1]) / resolution
                pixel_y = size[1] - pixel_y_from_bottom
                
                beacon_info = (
                    f"📍 全局坐标 (米):  X = {beacon_x:.3f} m,  Y = {beacon_y:.3f} m\n"
                    f"📐 像素坐标:      X = {pixel_x:.0f} px,  Y = {pixel_y:.0f} px\n"
                    f"🎯 置信度:        {beacon_data.get('confidence', 0):.2%}\n"
                    f"🏷️  标签ID:        {beacon_data.get('tag_id', 'N/A')}"
                )
            else:
                # 没有地图数据，只显示全局坐标
                beacon_info = (
                    f"📍 全局坐标 (米):  X = {beacon_x:.3f} m,  Y = {beacon_y:.3f} m\n"
                    f"📐 像素坐标:      等待地图数据...\n"
                    f"🎯 置信度:        {beacon_data.get('confidence', 0):.2%}\n"
                    f"🏷️  标签ID:        {beacon_data.get('tag_id', 'N/A')}"
                )
            
            self.beacon_info_label.setText(beacon_info)
        else:
            self.beacon_info_label.setText("等待 Beacon 数据...")
        
        self._refresh_map()
    
    def _validate_map_data(self, map_data: dict) -> tuple[bool, str]:
        """验证地图数据的完整性"""
        if not map_data:
            return False, "地图数据为空"
        
        required_fields = ['topic', 'resolution', 'size', 'origin', 'data']
        missing_fields = [f for f in required_fields if f not in map_data]
        if missing_fields:
            return False, f"缺少字段: {', '.join(missing_fields)}"
        
        if map_data.get('topic') != '/map':
            return False, f"错误的话题: {map_data.get('topic')}"
        
        resolution = map_data.get('resolution')
        if not isinstance(resolution, (int, float)) or resolution <= 0:
            return False, f"无效的分辨率: {resolution}"
        
        size = map_data.get('size')
        if not isinstance(size, list) or len(size) != 2:
            return False, f"无效的尺寸格式: {size}"
        if not all(isinstance(s, int) and s > 0 for s in size):
            return False, f"无效的尺寸值: {size}"
        
        origin = map_data.get('origin')
        if not isinstance(origin, list) or len(origin) != 2:
            return False, f"无效的原点格式: {origin}"
        if not all(isinstance(o, (int, float)) for o in origin):
            return False, f"无效的原点值: {origin}"
        
        data = map_data.get('data', '')
        if not data:
            return False, "地图数据为空"
        if not isinstance(data, str):
            return False, "地图数据格式错误"
        
        return True, "数据验证通过"
    
    def _calculate_map_metrics(self, map_data: dict) -> dict:
        """计算地图的各种度量指标"""
        resolution = map_data.get('resolution', 0)
        size = map_data.get('size', [0, 0])
        origin = map_data.get('origin', [0, 0])
        data = map_data.get('data', '')
        
        width_m = size[0] * resolution
        height_m = size[1] * resolution
        
        x_min = origin[0]
        y_min = origin[1]
        x_max = x_min + width_m
        y_max = y_min + height_m
        
        data_size_bytes = len(data) * 3 // 4
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
    
    def _mark_origin_on_image(self, pixmap: QPixmap, map_data: dict) -> QPixmap:
        """在图像上标注坐标原点 [0, 0]"""
        resolution = map_data.get('resolution', 1)
        origin = map_data.get('origin', [0, 0])
        size = map_data.get('size', [0, 0])
        
        origin_x_pixel = -origin[0] / resolution
        origin_y_pixel_from_bottom = -origin[1] / resolution
        origin_y_pixel = size[1] - origin_y_pixel_from_bottom
        
        marked_pixmap = QPixmap(pixmap)
        
        if (0 <= origin_x_pixel < size[0] and 0 <= origin_y_pixel < size[1]):
            painter = QPainter(marked_pixmap)
            
            green_color = QColor(0, 255, 0)
            painter.setPen(QPen(green_color, 2))
            painter.setBrush(QBrush(green_color))
            
            radius = 5
            painter.drawEllipse(
                int(origin_x_pixel) - radius,
                int(origin_y_pixel) - radius,
                radius * 2,
                radius * 2
            )
            
            cross_size = 10
            painter.setPen(QPen(green_color, 2))
            painter.drawLine(
                int(origin_x_pixel) - cross_size,
                int(origin_y_pixel),
                int(origin_x_pixel) + cross_size,
                int(origin_y_pixel)
            )
            painter.drawLine(
                int(origin_x_pixel),
                int(origin_y_pixel) - cross_size,
                int(origin_x_pixel),
                int(origin_y_pixel) + cross_size
            )
            
            painter.end()
        
        return marked_pixmap
    
    def _mark_tracked_pose_on_image(self, pixmap: QPixmap, map_data: dict, pose_data: dict) -> QPixmap:
        """在图像上标注追踪位置和朝向（蓝色箭头）"""
        if not pose_data or 'pos' not in pose_data or 'ori' not in pose_data:
            return pixmap
        
        resolution = map_data.get('resolution', 1)
        origin = map_data.get('origin', [0, 0])
        size = map_data.get('size', [0, 0])
        
        pos = pose_data.get('pos', [0, 0])
        ori = pose_data.get('ori', 0)
        
        # 坐标转换：米 -> 像素
        # origin是米单位，先相减再除以resolution
        pixel_x = (pos[0] - origin[0]) / resolution
        pixel_y_from_bottom = (pos[1] - origin[1]) / resolution
        pixel_y = size[1] - pixel_y_from_bottom
        
        import logging
        logger = logging.getLogger(__name__)
        
        # 计算地图覆盖的全局坐标范围
        map_x_min = origin[0]
        map_x_max = origin[0] + size[0] * resolution
        map_y_min = origin[1]
        map_y_max = origin[1] + size[1] * resolution
        
        logger.info(f"🚗 小车位置标注 (Widget):")
        logger.info(f"   物理坐标: ({pos[0]:.2f}, {pos[1]:.2f})m, 朝向: {ori:.2f}rad ({ori*180/3.14159:.1f}°)")
        logger.info(f"   地图范围: X[{map_x_min:.2f}, {map_x_max:.2f}]m, Y[{map_y_min:.2f}, {map_y_max:.2f}]m")
        logger.info(f"   像素坐标: ({pixel_x:.1f}, {pixel_y:.1f})px")
        logger.info(f"   地图尺寸: {size[0]}x{size[1]}px")
        
        # 放宽边界限制，允许超出地图范围的标注（扩展100像素）
        boundary_margin = 100
        if not (-boundary_margin <= pixel_x < size[0] + boundary_margin and 
                -boundary_margin <= pixel_y < size[1] + boundary_margin):
            logger.warning(f"   ⚠️ 小车位置严重超出显示范围，跳过标注")
            logger.warning(f"   允许范围: X[-{boundary_margin}, {size[0]+boundary_margin}]px, "
                         f"Y[-{boundary_margin}, {size[1]+boundary_margin}]px")
            return pixmap
        
        # 检查是否在实际地图范围内
        in_map_range = (0 <= pixel_x < size[0] and 0 <= pixel_y < size[1])
        if not in_map_range:
            logger.warning(f"   ⚠️ 小车位置超出地图范围但仍然标注（部分可见）")
        else:
            logger.info(f"   ✅ 小车位置在地图范围内")
        
        marked_pixmap = QPixmap(pixmap)
        painter = QPainter(marked_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        blue_color = QColor(0, 150, 255)
        painter.setPen(QPen(blue_color, 2))
        painter.setBrush(QBrush(blue_color))
        
        radius = 4
        painter.drawEllipse(
            int(pixel_x) - radius,
            int(pixel_y) - radius,
            radius * 2,
            radius * 2
        )
        
        arrow_length = 15
        arrow_end_x = pixel_x + arrow_length * math.cos(ori)
        arrow_end_y = pixel_y - arrow_length * math.sin(ori)
        
        painter.setPen(QPen(blue_color, 2))
        painter.drawLine(
            int(pixel_x),
            int(pixel_y),
            int(arrow_end_x),
            int(arrow_end_y)
        )
        
        arrow_size = 5
        angle1 = ori + math.pi * 0.85
        angle2 = ori - math.pi * 0.85
        
        point1_x = arrow_end_x + arrow_size * math.cos(angle1)
        point1_y = arrow_end_y - arrow_size * math.sin(angle1)
        point2_x = arrow_end_x + arrow_size * math.cos(angle2)
        point2_y = arrow_end_y - arrow_size * math.sin(angle2)
        
        painter.drawLine(
            int(arrow_end_x), int(arrow_end_y),
            int(point1_x), int(point1_y)
        )
        painter.drawLine(
            int(arrow_end_x), int(arrow_end_y),
            int(point2_x), int(point2_y)
        )
        
        painter.end()
        
        return marked_pixmap
    
    def _mark_beacon_on_image(self, pixmap: QPixmap, map_data: dict, beacon_data: dict) -> QPixmap:
        """在图像上标注 beacon（信标）位置（红色圆点）"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not beacon_data or 'm_x' not in beacon_data or 'm_y' not in beacon_data:
            logger.warning(f"Beacon数据无效或缺少m_x/m_y字段: {beacon_data}")
            return pixmap
        
        resolution = map_data.get('resolution', 1)
        origin = map_data.get('origin', [0, 0])
        size = map_data.get('size', [0, 0])
        
        beacon_x = beacon_data.get('m_x', 0)
        beacon_y = beacon_data.get('m_y', 0)
        confidence = beacon_data.get('confidence', 1.0)
        
        logger.info(f"🎯 开始标注Beacon: 全局坐标=({beacon_x:.3f}, {beacon_y:.3f})m")
        logger.info(f"   地图参数: origin={origin}, size={size}, resolution={resolution}")
        
        if resolution <= 0:
            logger.warning(f"无效的地图分辨率: {resolution}")
            return pixmap
        
        # 坐标转换：米 -> 像素
        # origin是米单位，先相减再除以resolution
        pixel_x = (beacon_x - origin[0]) / resolution
        pixel_y_from_bottom = (beacon_y - origin[1]) / resolution
        pixel_y = size[1] - pixel_y_from_bottom
        
        # 计算地图覆盖的全局坐标范围
        map_x_min = origin[0]
        map_x_max = origin[0] + size[0] * resolution
        map_y_min = origin[1]
        map_y_max = origin[1] + size[1] * resolution
        
        logger.info(f"🔴 Beacon位置标注 (Widget):")
        logger.info(f"   物理坐标: ({beacon_x:.2f}, {beacon_y:.2f})m, 置信度: {confidence:.2f}")
        logger.info(f"   地图范围: X[{map_x_min:.2f}, {map_x_max:.2f}]m, Y[{map_y_min:.2f}, {map_y_max:.2f}]m")
        logger.info(f"   像素坐标: ({pixel_x:.1f}, {pixel_y:.1f})px")
        logger.info(f"   地图尺寸: {size[0]}x{size[1]}px, 分辨率: {resolution}m/px")
        
        # 检查位置是否在图像范围内（放宽边界，允许部分显示）
        boundary_margin = 100
        if not (-boundary_margin <= pixel_x < size[0] + boundary_margin and 
                -boundary_margin <= pixel_y < size[1] + boundary_margin):
            logger.warning(f"   ⚠️ Beacon位置严重超出显示范围，跳过标注")
            logger.warning(f"   允许范围: X[-{boundary_margin}, {size[0]+boundary_margin}]px, "
                         f"Y[-{boundary_margin}, {size[1]+boundary_margin}]px")
            return pixmap
        
        # 检查是否在实际地图范围内
        in_map_range = (0 <= pixel_x < size[0] and 0 <= pixel_y < size[1])
        if not in_map_range:
            logger.warning(f"   ⚠️ Beacon位置超出地图范围但仍然标注（部分可见）")
        else:
            logger.info(f"   ✅ Beacon位置在地图范围内")
        
        marked_pixmap = QPixmap(pixmap)
        painter = QPainter(marked_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        outer_color = QColor(255, 100, 100, 120)
        painter.setPen(QPen(outer_color, 1))
        painter.setBrush(QBrush(outer_color))
        
        radius = int(5 + confidence * 5)
        outer_radius = int(radius + 4)
        
        painter.drawEllipse(
            int(pixel_x) - outer_radius,
            int(pixel_y) - outer_radius,
            outer_radius * 2,
            outer_radius * 2
        )
        
        red_color = QColor(255, 0, 0)
        painter.setPen(QPen(red_color, 2))
        painter.setBrush(QBrush(red_color))
        
        painter.drawEllipse(
            int(pixel_x) - radius,
            int(pixel_y) - radius,
            radius * 2,
            radius * 2
        )
        
        center_color = QColor(255, 255, 255)
        painter.setPen(QPen(center_color, 1))
        painter.setBrush(QBrush(center_color))
        painter.drawEllipse(
            int(pixel_x) - 2,
            int(pixel_y) - 2,
            4,
            4
        )
        
        painter.end()
        
        return marked_pixmap
    
    def _refresh_map(self):
        """刷新地图显示"""
        if not self.current_map_data:
            self.info_label.setText("暂无地图数据")
            self.status_label.setText("等待接收地图数据...")
            self.details_text.setPlainText("等待地图数据...")
            self.map_label.setText("等待地图数据...")
            return
        
        try:
            is_valid, validation_msg = self._validate_map_data(self.current_map_data)
            
            if not is_valid:
                self.info_label.setText(f"❌ 数据验证失败")
                self.status_label.setText(f"错误: {validation_msg}")
                self.status_label.setStyleSheet("""
                    QLabel {
                        background-color: #b71c1c;
                        color: #ffcdd2;
                        padding: 6px;
                        border-radius: 3px;
                        font-size: 10px;
                        border: 1px solid #c62828;
                    }
                """)
                self.details_text.setPlainText(f"验证失败: {validation_msg}")
                self.map_label.setText(f"❌ {validation_msg}")
                self.map_label.setPixmap(QPixmap())
                return
            
            resolution = self.current_map_data.get('resolution', 'N/A')
            size = self.current_map_data.get('size', [0, 0])
            origin = self.current_map_data.get('origin', [0, 0])
            base64_data = self.current_map_data.get('data', '')
            
            metrics = self._calculate_map_metrics(self.current_map_data)
            
            info_text = (
                f"✓ 分辨率: {resolution} m/px  |  "
                f"尺寸: {size[0]}×{size[1]} px ({metrics['width_m']:.1f}×{metrics['height_m']:.1f} m)  |  "
                f"原点: ({origin[0]}, {origin[1]}) m"
            )
            self.info_label.setText(info_text)
            
            update_time_str = self.last_update_time.strftime("%H:%M:%S") if self.last_update_time else "未知"
            status_text = (
                f"✓ 数据有效  |  更新时间: {update_time_str}  |  "
                f"接收次数: {self.map_receive_count}  |  数据大小: {metrics['data_size_kb']:.1f} KB"
            )
            self.status_label.setText(status_text)
            self.status_label.setStyleSheet("""
                QLabel {
                    background-color: #1b5e20;
                    color: #c8e6c9;
                    padding: 6px;
                    border-radius: 3px;
                    font-size: 10px;
                    border: 1px solid #2e7d32;
                }
            """)
            
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
            
            # 添加追踪位置信息 (Widget)
            if self.tracked_pose:
                pos = self.tracked_pose.get('pos', [0, 0])
                ori = self.tracked_pose.get('ori', 0)
                in_x_range = metrics['x_range'][0] <= pos[0] <= metrics['x_range'][1]
                in_y_range = metrics['y_range'][0] <= pos[1] <= metrics['y_range'][1]
                status = "✅" if (in_x_range and in_y_range) else "⚠️ 超出范围"
                details_lines.append("")
                details_lines.append(f"🚗 小车位置: ({pos[0]:.2f}, {pos[1]:.2f})m {status}")
                details_lines.append(f"   朝向: {ori:.2f}rad ({ori*180/3.14159:.1f}°)")
            
            # 添加beacon位置信息 (Widget)
            if self.beacon_position:
                bx = self.beacon_position.get('m_x', 0)
                by = self.beacon_position.get('m_y', 0)
                conf = self.beacon_position.get('confidence', 0)
                in_x_range = metrics['x_range'][0] <= bx <= metrics['x_range'][1]
                in_y_range = metrics['y_range'][0] <= by <= metrics['y_range'][1]
                status = "✅" if (in_x_range and in_y_range) else "⚠️ 超出范围"
                details_lines.append("")
                details_lines.append(f"🔴 Beacon位置: ({bx:.2f}, {by:.2f})m {status}")
                details_lines.append(f"   置信度: {conf:.2f}")
            
            self.details_text.setPlainText("\n".join(details_lines))
            
            if base64_data:
                try:
                    image_data = base64.b64decode(base64_data)
                    
                    qimage = QImage()
                    if qimage.loadFromData(image_data):
                        pixmap = QPixmap.fromImage(qimage)
                        
                        import logging
                        logger = logging.getLogger(__name__)
                        
                        # 标注坐标原点
                        pixmap = self._mark_origin_on_image(pixmap, self.current_map_data)
                        logger.debug("已标注坐标原点")
                        
                        # 标注追踪位置（小车）
                        if self.tracked_pose:
                            logger.info(f"准备标注小车位置: {self.tracked_pose}")
                            pixmap = self._mark_tracked_pose_on_image(pixmap, self.current_map_data, self.tracked_pose)
                            logger.info("已完成小车位置标注")
                        else:
                            logger.warning("tracked_pose 为空，跳过小车标注")
                        
                        # 标注beacon位置
                        if self.beacon_position:
                            logger.info(f"准备标注beacon位置: {self.beacon_position}")
                            pixmap = self._mark_beacon_on_image(pixmap, self.current_map_data, self.beacon_position)
                            logger.info("已完成beacon位置标注")
                        else:
                            logger.debug("beacon_position 为空，跳过beacon标注")
                        
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
                        self.map_label.setText("❌ 无法加载图片数据")
                        self.map_label.setStyleSheet("""
                            QLabel {
                                background-color: #ffebee;
                                border: 2px dashed #f44336;
                                color: #c62828;
                            }
                        """)
                except Exception as e:
                    self.map_label.setText(f"❌ 图片解码失败: {str(e)}")
            else:
                self.map_label.setText("❌ 地图数据为空")
                
        except Exception as e:
            self.info_label.setText(f"❌ 处理失败: {str(e)}")
