"""
完整的追踪位置功能集成示例
演示如何在实际应用中使用追踪位置标注功能
"""
import sys
import json
import base64
import math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
    QWidget, QPushButton, QLabel, QSlider, QSpinBox, QDoubleSpinBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
from PIL import Image
import io

# 导入地图查看器
from ui.widgets.map_viewer import MapViewerDialog


class TrackedPoseDemo(QMainWindow):
    """追踪位置功能演示应用"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("追踪位置标注功能演示")
        self.setGeometry(100, 100, 1000, 800)
        
        # 创建地图查看器
        self.map_viewer = MapViewerDialog(self)
        
        # 创建控制面板
        self.create_control_panel()
        
        # 初始化地图数据
        self.init_map_data()
        
        # 定时更新追踪位置（模拟机器人运动）
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_robot_position)
        self.timer.interval = 100  # 100ms更新一次
        
        self.robot_x = 0.0
        self.robot_y = 0.0
        self.robot_ori = 0.0
        self.is_moving = False
        
    def create_control_panel(self):
        """创建控制面板"""
        main_widget = QWidget()
        main_layout = QHBoxLayout()
        
        # 左侧：地图显示
        main_layout.addWidget(self.map_viewer, 1)
        
        # 右侧：控制面板
        control_widget = QWidget()
        control_layout = QVBoxLayout()
        
        # 标题
        title = QLabel("机器人位置控制")
        title.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        control_layout.addWidget(title)
        
        # X位置控制
        x_layout = QHBoxLayout()
        x_label = QLabel("X位置 (米):")
        self.x_spinbox = QDoubleSpinBox()
        self.x_spinbox.setRange(-10, 10)
        self.x_spinbox.setValue(0)
        self.x_spinbox.setSingleStep(0.1)
        self.x_spinbox.valueChanged.connect(self.on_position_changed)
        x_layout.addWidget(x_label)
        x_layout.addWidget(self.x_spinbox)
        control_layout.addLayout(x_layout)
        
        # Y位置控制
        y_layout = QHBoxLayout()
        y_label = QLabel("Y位置 (米):")
        self.y_spinbox = QDoubleSpinBox()
        self.y_spinbox.setRange(-10, 10)
        self.y_spinbox.setValue(0)
        self.y_spinbox.setSingleStep(0.1)
        self.y_spinbox.valueChanged.connect(self.on_position_changed)
        y_layout.addWidget(y_label)
        y_layout.addWidget(self.y_spinbox)
        control_layout.addLayout(y_layout)
        
        # 朝向控制
        ori_layout = QHBoxLayout()
        ori_label = QLabel("朝向 (度):")
        self.ori_spinbox = QDoubleSpinBox()
        self.ori_spinbox.setRange(0, 360)
        self.ori_spinbox.setValue(0)
        self.ori_spinbox.setSingleStep(1)
        self.ori_spinbox.valueChanged.connect(self.on_position_changed)
        ori_layout.addWidget(ori_label)
        ori_layout.addWidget(self.ori_spinbox)
        control_layout.addLayout(ori_layout)
        
        # 分隔线
        control_layout.addSpacing(20)
        
        # 预设位置按钮
        preset_label = QLabel("预设位置:")
        preset_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        control_layout.addWidget(preset_label)
        
        # 原点
        origin_btn = QPushButton("📍 原点 [0, 0]")
        origin_btn.clicked.connect(lambda: self.set_position(0, 0, 0))
        control_layout.addWidget(origin_btn)
        
        # 向右
        right_btn = QPushButton("➡️ 向右 [2, 0]")
        right_btn.clicked.connect(lambda: self.set_position(2, 0, 0))
        control_layout.addWidget(right_btn)
        
        # 向上
        up_btn = QPushButton("⬆️ 向上 [0, 2]")
        up_btn.clicked.connect(lambda: self.set_position(0, 2, 90))
        control_layout.addWidget(up_btn)
        
        # 向左
        left_btn = QPushButton("⬅️ 向左 [-2, 0]")
        left_btn.clicked.connect(lambda: self.set_position(-2, 0, 180))
        control_layout.addWidget(left_btn)
        
        # 向下
        down_btn = QPushButton("⬇️ 向下 [0, -2]")
        down_btn.clicked.connect(lambda: self.set_position(0, -2, 270))
        control_layout.addWidget(down_btn)
        
        # 对角线
        diagonal_btn = QPushButton("↗️ 对角线 [2, 2]")
        diagonal_btn.clicked.connect(lambda: self.set_position(2, 2, 45))
        control_layout.addWidget(diagonal_btn)
        
        # 分隔线
        control_layout.addSpacing(20)
        
        # 自动运动
        motion_label = QLabel("自动运动:")
        motion_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        control_layout.addWidget(motion_label)
        
        # 启动/停止按钮
        self.motion_btn = QPushButton("▶️ 启动")
        self.motion_btn.clicked.connect(self.toggle_motion)
        control_layout.addWidget(self.motion_btn)
        
        # 信息显示
        control_layout.addSpacing(20)
        info_label = QLabel("当前信息:")
        info_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        control_layout.addWidget(info_label)
        
        self.info_text = QLabel(
            "X: 0.00 m\nY: 0.00 m\nOri: 0°\n\n"
            "✓ 绿色 = 原点\n"
            "✓ 蓝色 = 机器人"
        )
        self.info_text.setFont(QFont("Courier", 9))
        self.info_text.setStyleSheet("""
            QLabel {
                background-color: #263238;
                color: #e0e0e0;
                padding: 8px;
                border: 1px solid #455a64;
                border-radius: 3px;
            }
        """)
        control_layout.addWidget(self.info_text)
        
        control_layout.addStretch()
        
        control_widget.setLayout(control_layout)
        control_widget.setMaximumWidth(250)
        
        main_layout.addWidget(control_widget)
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)
    
    def init_map_data(self):
        """初始化地图数据"""
        # 创建测试地图
        img = Image.new('RGB', (182, 59), color='white')
        
        # 绘制网格
        from PIL import ImageDraw
        draw = ImageDraw.Draw(img)
        for x in range(0, 182, 20):
            draw.line([(x, 0), (x, 59)], fill=(200, 200, 200), width=1)
        for y in range(0, 59, 20):
            draw.line([(0, y), (182, y)], fill=(200, 200, 200), width=1)
        draw.rectangle([(0, 0), (181, 58)], outline=(100, 100, 100), width=2)
        
        # 保存为base64
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # 地图数据
        map_data = {
            "topic": "/map",
            "resolution": 0.1,
            "size": [182, 59],
            "origin": [-8.1, -4.8],
            "data": base64_data
        }
        
        # 更新地图
        self.map_viewer.update_map(map_data)
    
    def set_position(self, x, y, ori_deg):
        """设置机器人位置"""
        self.x_spinbox.blockSignals(True)
        self.y_spinbox.blockSignals(True)
        self.ori_spinbox.blockSignals(True)
        
        self.x_spinbox.setValue(x)
        self.y_spinbox.setValue(y)
        self.ori_spinbox.setValue(ori_deg)
        
        self.x_spinbox.blockSignals(False)
        self.y_spinbox.blockSignals(False)
        self.ori_spinbox.blockSignals(False)
        
        self.on_position_changed()
    
    def on_position_changed(self):
        """位置改变时更新追踪数据"""
        self.robot_x = self.x_spinbox.value()
        self.robot_y = self.y_spinbox.value()
        self.robot_ori = math.radians(self.ori_spinbox.value())
        
        self.update_tracked_pose()
    
    def toggle_motion(self):
        """切换自动运动"""
        self.is_moving = not self.is_moving
        if self.is_moving:
            self.motion_btn.setText("⏸️ 停止")
            self.timer.start()
        else:
            self.motion_btn.setText("▶️ 启动")
            self.timer.stop()
    
    def update_robot_position(self):
        """更新机器人位置（自动运动）"""
        # 圆形运动
        angle = (self.robot_ori * 180 / math.pi) % 360
        angle += 2  # 每100ms转2度
        
        self.robot_ori = math.radians(angle)
        self.robot_x = 3 * math.cos(self.robot_ori)
        self.robot_y = 3 * math.sin(self.robot_ori)
        
        # 更新控制盘显示
        self.x_spinbox.blockSignals(True)
        self.y_spinbox.blockSignals(True)
        self.ori_spinbox.blockSignals(True)
        
        self.x_spinbox.setValue(self.robot_x)
        self.y_spinbox.setValue(self.robot_y)
        self.ori_spinbox.setValue(angle)
        
        self.x_spinbox.blockSignals(False)
        self.y_spinbox.blockSignals(False)
        self.ori_spinbox.blockSignals(False)
        
        self.update_tracked_pose()
    
    def update_tracked_pose(self):
        """更新地图上的追踪位置"""
        pose_data = {
            "pos": [self.robot_x, self.robot_y],
            "ori": self.robot_ori
        }
        self.map_viewer.update_tracked_pose(pose_data)
        
        # 更新信息显示
        self.info_text.setText(
            f"X: {self.robot_x:.2f} m\n"
            f"Y: {self.robot_y:.2f} m\n"
            f"Ori: {math.degrees(self.robot_ori):.0f}°\n\n"
            f"✓ 绿色 = 原点\n"
            f"✓ 蓝色 = 机器人"
        )


def main():
    """运行演示应用"""
    app = QApplication(sys.argv)
    demo = TrackedPoseDemo()
    demo.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
