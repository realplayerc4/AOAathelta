"""
设备信息表格组件
"""
from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from typing import List
from models.device import Device


class DeviceTableWidget(QTableWidget):
    """显示设备信息的表格组件"""
    
    # 表格列头定义 - 简化显示关键信息
    HEADERS = ["设备名称", "状态", "序列号", "电池(%)", "位置"]
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
    
    def _setup_ui(self):
        """初始化表格UI"""
        # 设置列数和表头
        self.setColumnCount(len(self.HEADERS))
        self.setHorizontalHeaderLabels(self.HEADERS)
        
        # 表格样式配置 - 黑色主题
        self.setStyleSheet("""
            QTableWidget {
                background-color: #000000;
                color: #FFFFFF;
                gridline-color: #333333;
                border: 1px solid #444444;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #333333;
            }
            QTableWidget::item:selected {
                background-color: #1E5A8E;
                color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #1A1A1A;
                color: #FFFFFF;
                padding: 10px;
                border: 1px solid #333333;
                font-weight: bold;
            }
        """)
        
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)  # 选择整行
        self.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)  # 单选
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)  # 只读
        
        # 列宽自适应
        header = self.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setStretchLastSection(True)  # 最后一列拉伸填充
        
        # 设置最小列宽
        self.setColumnWidth(0, 150)  # 设备名称
        self.setColumnWidth(1, 100)  # 状态
        self.setColumnWidth(2, 150)  # 序列号
    
    def load_devices(self, devices: List[Device]):
        """
        加载设备数据到表格 - 只显示关键信息
        
        Args:
            devices: Device 对象列表
        """
        self.setRowCount(len(devices))
        
        for row, device in enumerate(devices):
            # 设备名称
            name_item = QTableWidgetItem(device.name)
            name_item.setForeground(QColor(255, 255, 255))  # 白色
            self.setItem(row, 0, name_item)
            
            # 状态（带颜色标记）
            status_item = QTableWidgetItem(device.status)
            status_lower = device.status.lower()
            if 'online' in status_lower or '在线' in status_lower or 'active' in status_lower:
                status_item.setForeground(QColor(0, 255, 0))  # 亮绿色
            elif 'offline' in status_lower or '离线' in status_lower:
                status_item.setForeground(QColor(255, 0, 0))  # 红色
            elif 'warning' in status_lower or '警告' in status_lower:
                status_item.setForeground(QColor(255, 165, 0))  # 橙色
            else:
                status_item.setForeground(QColor(255, 255, 255))  # 白色
            self.setItem(row, 1, status_item)
            
            # 序列号
            sn_item = QTableWidgetItem(device.sn or "N/A")
            sn_item.setForeground(QColor(255, 255, 255))  # 白色
            self.setItem(row, 2, sn_item)
            
            # 电池电量
            if device.battery_level is not None:
                battery_text = f"{device.battery_level:.1f}"
                battery_item = QTableWidgetItem(battery_text)
                # 根据电量设置颜色
                if device.battery_level < 20:
                    battery_item.setForeground(QColor(255, 0, 0))  # 红色
                elif device.battery_level < 50:
                    battery_item.setForeground(QColor(255, 165, 0))  # 橙色
                else:
                    battery_item.setForeground(QColor(0, 255, 0))  # 亮绿色
                self.setItem(row, 3, battery_item)
            else:
                na_item = QTableWidgetItem("N/A")
                na_item.setForeground(QColor(150, 150, 150))  # 灰色
                self.setItem(row, 3, na_item)
            
            # 位置
            location_item = QTableWidgetItem(device.location or "N/A")
            location_item.setForeground(QColor(255, 255, 255))  # 白色
            self.setItem(row, 4, location_item)
    
    def clear_data(self):
        """清空表格数据"""
        self.setRowCount(0)
