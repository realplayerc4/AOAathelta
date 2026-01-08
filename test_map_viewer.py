"""
测试地图查看器功能
"""
import sys
import base64
from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget
from ui.widgets.map_viewer import MapViewerDialog


def generate_test_map_data():
    """生成测试地图数据"""
    # 创建一个简单的测试PNG图片（10x10像素，红色方块）
    import io
    try:
        from PIL import Image
        img = Image.new('RGB', (182, 59), color='white')
        # 添加一些图案
        for x in range(0, 182, 10):
            for y in range(0, 59, 10):
                if (x + y) % 20 == 0:
                    img.putpixel((x, y), (0, 0, 0))
        
        buffer = io.BytesIO()
        img.save(buffer, format='PNG')
        base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    except ImportError:
        # 如果没有PIL，使用一个最小的PNG
        # 1x1 白色像素的PNG
        minimal_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x00\x00\x00\x00IEND\xaeB`\x82'
        base64_data = base64.b64encode(minimal_png).decode('utf-8')
    
    return {
        "topic": "/map",
        "resolution": 0.1,
        "size": [182, 59],
        "origin": [-8.1, -4.8],
        "data": base64_data
    }


def main():
    app = QApplication(sys.argv)
    
    # 创建测试窗口
    test_window = QWidget()
    test_window.setWindowTitle("地图查看器测试")
    layout = QVBoxLayout(test_window)
    
    # 创建地图查看器
    viewer = MapViewerDialog(test_window)
    
    # 创建测试按钮
    test_button = QPushButton("📍 测试显示地图")
    test_button.clicked.connect(lambda: viewer.update_map(generate_test_map_data()))
    test_button.clicked.connect(viewer.show)
    
    layout.addWidget(test_button)
    
    test_window.setGeometry(100, 100, 300, 100)
    test_window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
