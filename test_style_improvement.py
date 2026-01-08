"""
地图查看器UI样式改进测试
演示改进后的深色主题和高对比度设计
"""
import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QLabel
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class StyleShowcaseWindow(QMainWindow):
    """样式展示窗口"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("地图查看器UI样式改进 - 预览")
        self.setGeometry(100, 100, 800, 600)
        
        # 创建主窗口
        main_widget = QWidget()
        layout = QVBoxLayout(main_widget)
        
        # 1. 基本信息标签样式
        title1 = QLabel("📊 地图基本信息 (改进前: 浅灰 → 改进后: 深色+青色)")
        title1.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                margin-top: 10px;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(title1)
        
        info_label = QLabel("✓ 分辨率: 0.1 m/px  |  尺寸: 182×59 px  |  原点: (-8.1, -4.8) m")
        info_label.setStyleSheet("""
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
        layout.addWidget(info_label)
        
        # 2. 状态标签样式
        title2 = QLabel("✓ 成功状态 (改进前: 浅蓝 → 改进后: 深绿+浅绿)")
        title2.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                margin-top: 10px;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(title2)
        
        status_ok = QLabel("✓ 数据有效  |  更新时间: 10:30:45  |  接收次数: 5  |  数据大小: 15.3 KB")
        status_ok.setStyleSheet("""
            QLabel {
                background-color: #1b5e20;
                color: #c8e6c9;
                padding: 6px;
                border-radius: 3px;
                font-size: 10px;
                border: 1px solid #2e7d32;
            }
        """)
        layout.addWidget(status_ok)
        
        # 3. 错误状态标签样式
        title3 = QLabel("❌ 错误状态 (改进前: 浅红 → 改进后: 深红+浅红)")
        title3.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                margin-top: 10px;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(title3)
        
        status_error = QLabel("❌ 错误: 地图数据格式不正确")
        status_error.setStyleSheet("""
            QLabel {
                background-color: #b71c1c;
                color: #ffcdd2;
                padding: 6px;
                border-radius: 3px;
                font-size: 10px;
                border: 1px solid #c62828;
            }
        """)
        layout.addWidget(status_error)
        
        # 4. 详细信息框样式
        title4 = QLabel("📝 详细信息 (改进前: 浅灰 → 改进后: 深色+浅灰)")
        title4.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                margin-top: 10px;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(title4)
        
        details = QLabel(
            "话题: /map\n"
            "分辨率: 0.1 米/像素\n"
            "图像尺寸: 182 × 59 像素\n"
            "实际尺寸: 18.20 × 5.90 米\n"
            "覆盖面积: 107.38 平方米\n"
            "原点坐标: (-8.1, -4.8) 米\n"
            "X 范围: -8.10 至 10.10 米\n"
            "Y 范围: -4.80 至 1.10 米"
        )
        details.setStyleSheet("""
            QLabel {
                background-color: #263238;
                color: #e0e0e0;
                border: 1px solid #455a64;
                font-family: monospace;
                font-size: 10px;
                padding: 6px;
                border-radius: 3px;
            }
        """)
        layout.addWidget(details)
        
        # 5. 比较说明
        title5 = QLabel("\n🎨 样式改进总结")
        title5.setStyleSheet("""
            QLabel {
                font-size: 12px;
                font-weight: bold;
                color: #1976d2;
            }
        """)
        layout.addWidget(title5)
        
        summary = QLabel(
            "改进内容：\n"
            "  • 基本信息: 浅灰 (#f0f0f0) → 深色 (#263238) + 青色文字\n"
            "  • 状态标签: 浅蓝/浅红 → 深绿/深红 + 高对比度文字\n"
            "  • 详细信息: 浅灰 (#f5f5f5) → 深色 (#263238) + 浅灰文字\n"
            "  • 边框: 增加深色边框，提升UI层次感\n\n"
            "效果：\n"
            "  ✓ 对比度提高，信息清晰易读\n"
            "  ✓ 深色主题，减少眼睛疲劳\n"
            "  ✓ 错误信息更突出，便于识别问题\n"
            "  ✓ 整体视觉效果更专业"
        )
        summary.setStyleSheet("""
            QLabel {
                background-color: #f5f5f5;
                padding: 8px;
                border-radius: 3px;
                font-size: 10px;
                border: 1px solid #ddd;
            }
        """)
        layout.addWidget(summary)
        
        layout.addStretch()
        
        # 设置主窗口
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)


def main():
    """运行样式预览"""
    app = QApplication(sys.argv)
    window = StyleShowcaseWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
