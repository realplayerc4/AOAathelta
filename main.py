"""
AMR 设备监控系统 - 主入口
"""
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from ui.main_window import MainWindow


def main():
    """应用程序入口函数"""
    # 启用高DPI缩放（必须在创建QApplication之前调用）
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough     
    )
    
    # 创建应用实例
    app = QApplication(sys.argv)
    app.setApplicationName("AMR 设备监控系统")
    
    # 创建并显示主窗口
    window = MainWindow()
    window.show()
    
    # 进入事件循环
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
