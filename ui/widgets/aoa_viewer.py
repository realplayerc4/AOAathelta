"""
AOA 数据显示小部件
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QTableWidget, QTableWidgetItem, QPushButton,
    QGroupBox, QComboBox, QSpinBox, QGridLayout,
    QMessageBox, QDialog
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtCharts import QChart, QChartView, QLineSeries, QValueAxis, QDateTimeAxis
from datetime import datetime
from collections import deque
from typing import Dict, List, Optional


class AOADataWidget(QWidget):
    """AOA 数据显示面板"""
    
    # 信号
    anchor_selected = pyqtSignal(int)  # 选择了某个 ANCHER
    tag_selected = pyqtSignal(int)  # 选择了某个 TAG
    
    def __init__(self):
        super().__init__()
        
        # 数据存储
        self.latest_frames: Dict[int, dict] = {}  # {frame_id: frame_info}
        self.position_history: Dict[str, deque] = {}  # {tag_id: deque of positions}
        self.max_history_size = 100
        
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化 UI"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # 标题
        title = QLabel("AOA 角度到达数据")
        title.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        main_layout.addWidget(title)
        
        # 控制面板
        control_group = QGroupBox("控制面板")
        control_layout = QHBoxLayout()
        
        # 串口选择
        control_layout.addWidget(QLabel("串口:"))
        self.port_combo = QComboBox()
        self.port_combo.addItems([
            "/dev/ttyCH343USB0",
            "/dev/ttyUSB0",
            "/dev/ttyUSB1",
            "COM3",
            "COM4",
        ])
        self.port_combo.setCurrentText("/dev/ttyCH343USB0")
        control_layout.addWidget(self.port_combo)
        
        # 波特率选择
        control_layout.addWidget(QLabel("波特率:"))
        self.baudrate_spin = QSpinBox()
        self.baudrate_spin.setMinimum(9600)
        self.baudrate_spin.setMaximum(921600)
        self.baudrate_spin.setValue(921600)
        self.baudrate_spin.setSingleStep(9600)
        control_layout.addWidget(self.baudrate_spin)
        
        # 连接/断开按钮
        self.connect_button = QPushButton("🔌 连接")
        self.connect_button.clicked.connect(self._on_connect_clicked)
        self.connect_button.setMinimumWidth(100)
        control_layout.addWidget(self.connect_button)
        
        # 清空历史
        self.clear_button = QPushButton("🗑️ 清空")
        self.clear_button.clicked.connect(self._on_clear_clicked)
        control_layout.addWidget(self.clear_button)
        
        control_layout.addStretch()
        control_group.setLayout(control_layout)
        main_layout.addWidget(control_group)
        
        # 实时数据表格
        data_group = QGroupBox("实时数据")
        data_layout = QVBoxLayout()
        
        # 创建表格
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(8)
        self.data_table.setHorizontalHeaderLabels([
            "帧#", "时间戳", "ANCHER ID", "TAG ID",
            "距离 (m)", "角度 (°)", "电压 (mV)", "有效性"
        ])
        self.data_table.setMaximumHeight(250)
        self.data_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.data_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        data_layout.addWidget(self.data_table)
        
        data_group.setLayout(data_layout)
        main_layout.addWidget(data_group)
        
        # 统计信息
        stats_group = QGroupBox("统计信息")
        stats_layout = QGridLayout()
        
        self.stats_labels = {}
        stats_items = [
            ("总帧数", "total_frames"),
            ("成功帧", "success_frames"),
            ("错误帧", "error_frames"),
            ("错误率", "error_rate")
        ]
        
        for i, (label_text, key) in enumerate(stats_items):
            label = QLabel(label_text + ":")
            label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            value = QLabel("0")
            value.setFont(QFont("Courier", 10))
            stats_layout.addWidget(label, i // 2, (i % 2) * 2)
            stats_layout.addWidget(value, i // 2, (i % 2) * 2 + 1)
            self.stats_labels[key] = value
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)
        
        # 底部状态
        self.status_label = QLabel("未连接")
        self.status_label.setStyleSheet("color: red; font-weight: bold;")
        main_layout.addWidget(self.status_label)
        
        main_layout.addStretch()
    
    def add_frame(self, frame_info: dict):
        """
        添加新的 AOA 帧数据
        
        Args:
            frame_info: 帧信息字典
        """
        frame_id = frame_info.get('frame_id', 0)
        self.latest_frames[frame_id] = frame_info
        
        # 更新表格
        self._update_data_table(frame_info)
    
    def _update_data_table(self, frame_info: dict):
        """更新数据表格"""
        row = self.data_table.rowCount()
        self.data_table.insertRow(row)
        
        # 限制行数，删除最旧的行
        if row > 50:
            self.data_table.removeRow(0)
            row -= 1
        
        # 填充数据
        items = [
            str(frame_info.get('frame_id', '')),
            frame_info.get('timestamp', '')[:19],  # 只显示日期时间，不显示微秒
            str(frame_info.get('anchor_id', '')),
            str(frame_info.get('tag_id', '')),
            f"{frame_info.get('distance_mm', 0) / 1000:.3f}",
            f"{frame_info.get('angle_degrees', 0):.2f}",
            str(frame_info.get('voltage_mv', '')),
            "✓" if frame_info.get('is_valid') else "✗"
        ]
        
        for col, text in enumerate(items):
            item = QTableWidgetItem(text)
            item.setFont(QFont("Courier", 10))
            
            # 设置有效性列的颜色
            if col == 7:  # 有效性列
                if text == "✓":
                    item.setForeground(QColor("green"))
                else:
                    item.setForeground(QColor("red"))
            
            self.data_table.setItem(row, col, item)
        
        # 滚动到最新行
        self.data_table.scrollToBottom()
    
    def update_statistics(self, stats: dict):
        """
        更新统计信息
        
        Args:
            stats: 统计信息字典
        """
        parser_stats = stats.get('parser_stats', {})
        
        self.stats_labels['total_frames'].setText(
            str(parser_stats.get('total_frames', 0))
        )
        self.stats_labels['success_frames'].setText(
            str(parser_stats.get('success_count', 0))
        )
        self.stats_labels['error_frames'].setText(
            str(parser_stats.get('error_count', 0))
        )
        
        error_rate = parser_stats.get('error_rate', 0)
        self.stats_labels['error_rate'].setText(f"{error_rate:.2f}%")
    
    def update_status(self, status: str):
        """更新连接状态"""
        self.status_label.setText(status)
        
        if "已连接" in status or "连接到" in status:
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.connect_button.setText("🔌 断开")
        else:
            self.status_label.setStyleSheet("color: red; font-weight: bold;")
            self.connect_button.setText("🔌 连接")
    
    def _on_connect_clicked(self):
        """连接/断开按钮点击"""
        if self.connect_button.text() == "🔌 连接":
            port = self.port_combo.currentText()
            baudrate = self.baudrate_spin.value()
            # 这里应该触发连接信号，由主窗口处理
            print(f"连接到 {port} @ {baudrate} baud")
        else:
            # 断开连接
            print("断开连接")
    
    def _on_clear_clicked(self):
        """清空数据"""
        self.data_table.setRowCount(0)
        self.latest_frames.clear()
        self.position_history.clear()
        self.status_label.setText("数据已清空")
    
    def add_status_message(self, message: str):
        """
        添加状态消息到状态标签
        
        Args:
            message: 状态消息文本
        """
        self.status_label.setText(message)


class AOAPositionViewer(QDialog):
    """AOA 位置查看器 - 显示标签相对于 ANCHER 的位置"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AOA 位置查看器")
        self.setMinimumSize(800, 600)
        
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化 UI"""
        layout = QVBoxLayout(self)
        
        # 创建图表
        self.chart = QChart()
        self.chart.setTitle("标签位置分布 (相对于 ANCHER)")
        self.chart.setAnimationOptions(QChart.AnimationOption.SeriesAnimations)
        
        self.chart_view = QChartView(self.chart)
        self.chart_view.setRenderHint(self.chart_view.RenderHint.Antialiasing)
        
        layout.addWidget(self.chart_view)
        
        # 控制按钮
        button_layout = QHBoxLayout()
        
        refresh_button = QPushButton("刷新")
        refresh_button.clicked.connect(self._refresh_chart)
        button_layout.addWidget(refresh_button)
        
        close_button = QPushButton("关闭")
        close_button.clicked.connect(self.close)
        button_layout.addWidget(close_button)
        
        button_layout.addStretch()
        layout.addLayout(button_layout)
    
    def _refresh_chart(self):
        """刷新图表"""
        # 这里可以添加从数据源读取数据并更新图表的逻辑
        pass
