"""
地图原点标注功能集成测试
演示在不同的原点配置下如何标注坐标 [0, 0]
"""
import sys
import base64
from PIL import Image, ImageDraw, ImageFont
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush
import io


def create_test_map_with_grid(width=182, height=59, resolution=0.1):
    """
    创建带网格的测试地图
    
    Args:
        width: 图片宽度（像素）
        height: 图片高度（像素）
        resolution: 分辨率（米/像素）
    """
    img = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(img)
    
    # 绘制网格线（每20像素一条，即2米间距）
    grid_spacing = 20
    for x in range(0, width, grid_spacing):
        draw.line([(x, 0), (x, height)], fill=(200, 200, 200), width=1)
    for y in range(0, height, grid_spacing):
        draw.line([(0, y), (width, y)], fill=(200, 200, 200), width=1)
    
    # 绘制边界
    draw.rectangle([(0, 0), (width-1, height-1)], outline=(100, 100, 100), width=2)
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def mark_origin_on_image(pixmap: QPixmap, map_data: dict) -> QPixmap:
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
        
        # 绘制圆点
        radius = 5
        painter.drawEllipse(
            int(origin_x_pixel) - radius,
            int(origin_y_pixel) - radius,
            radius * 2,
            radius * 2
        )
        
        # 绘制十字
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


def test_origin_marking(test_cases):
    """
    测试多个原点标注场景
    
    Args:
        test_cases: 包含不同测试用例的列表
    """
    print("=" * 80)
    print("地图原点标注功能集成测试")
    print("=" * 80)
    
    for case_name, map_data in test_cases:
        print(f"\n【测试用例】{case_name}")
        print("-" * 80)
        
        resolution = map_data.get('resolution', 1)
        origin = map_data.get('origin', [0, 0])
        size = map_data.get('size', [0, 0])
        
        # 计算像素位置
        origin_x_pixel = -origin[0] / resolution
        origin_y_pixel_from_bottom = -origin[1] / resolution
        origin_y_pixel = size[1] - origin_y_pixel_from_bottom
        
        print(f"配置信息:")
        print(f"  分辨率:     {resolution} m/pixel")
        print(f"  图像尺寸:   {size[0]} × {size[1]} pixels")
        print(f"  原点坐标:   ({origin[0]}, {origin[1]}) m (左下角)")
        print(f"  实际范围:   X=[{origin[0]:.1f}, {origin[0] + size[0]*resolution:.1f}]m")
        print(f"             Y=[{origin[1]:.1f}, {origin[1] + size[1]*resolution:.1f}]m")
        
        print(f"\n计算结果:")
        print(f"  X 像素位置:  {origin_x_pixel:.1f} px")
        print(f"  Y 像素位置:  {origin_y_pixel:.1f} px (从上边缘)")
        
        # 检查是否在范围内
        in_range = (0 <= origin_x_pixel < size[0] and 0 <= origin_y_pixel < size[1])
        status = "✓ 在范围内" if in_range else "✗ 超出范围"
        print(f"  范围检查:   {status}")
        
        # 创建和标注地图
        if 'data' not in map_data:
            map_data['data'] = create_test_map_with_grid(size[0], size[1], resolution)
        
        image_bytes = base64.b64decode(map_data['data'])
        qimage = QImage()
        if qimage.loadFromData(image_bytes):
            pixmap = QPixmap.fromImage(qimage)
            marked_pixmap = mark_origin_on_image(pixmap, map_data)
            
            output_path = f"/tmp/map_test_{case_name.replace(' ', '_')}.png"
            marked_pixmap.save(output_path)
            print(f"\n结果: 已保存到 {output_path}")
        else:
            print(f"\n结果: 无法加载图像数据")


def main():
    """运行测试"""
    app = QApplication(sys.argv)
    
    # 定义测试用例
    test_cases = [
        (
            "标准配置（原点在图片内部）",
            {
                "topic": "/map",
                "resolution": 0.1,
                "size": [182, 59],
                "origin": [-8.1, -4.8],
            }
        ),
        (
            "原点在左下角",
            {
                "topic": "/map",
                "resolution": 0.05,
                "size": [200, 100],
                "origin": [0, 0],
            }
        ),
        (
            "原点在左上角",
            {
                "topic": "/map",
                "resolution": 0.1,
                "size": [100, 100],
                "origin": [0, 9],  # 左上角
            }
        ),
        (
            "原点偏左且在上方",
            {
                "topic": "/map",
                "resolution": 0.05,
                "size": [200, 200],
                "origin": [-5, 5],
            }
        ),
        (
            "原点超出范围（右下）",
            {
                "topic": "/map",
                "resolution": 0.1,
                "size": [100, 100],
                "origin": [5, 5],  # 原点在右下，超出范围
            }
        ),
    ]
    
    # 运行测试
    test_origin_marking(test_cases)
    
    print("\n" + "=" * 80)
    print("✓ 所有测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
