"""
测试坐标原点标注功能
"""
import sys
import base64
from PIL import Image
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush
import io


def mark_origin_on_image(pixmap: QPixmap, map_data: dict) -> QPixmap:
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
    
    print(f"地图数据:")
    print(f"  原点 (origin): {origin}")
    print(f"  分辨率 (resolution): {resolution} m/pixel")
    print(f"  尺寸 (size): {size}")
    print(f"\n计算结果:")
    print(f"  原点像素位置 (X): {origin_x_pixel:.1f} px")
    print(f"  原点像素位置 (Y from bottom): {origin_y_pixel_from_bottom:.1f} px")
    print(f"  原点像素位置 (Y from top): {origin_y_pixel:.1f} px")
    print(f"  图像范围: X=[0, {size[0]}), Y=[0, {size[1]})")
    
    # 检查原点是否在图像范围内
    if (0 <= origin_x_pixel < size[0] and 0 <= origin_y_pixel < size[1]):
        print(f"✓ 原点在图像范围内，进行标注")
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
    else:
        print(f"✗ 原点超出图像范围，无法标注")
    
    return marked_pixmap


def main():
    """测试原点标注"""
    # 必须先创建QApplication
    app = QApplication(sys.argv)
    
    # 创建测试地图数据
    img = Image.new('RGB', (182, 59), color='white')
    # 添加网格线
    for x in range(0, 182, 20):
        for y in range(0, 59, 20):
            img.putpixel((x, y), (200, 200, 200))
    
    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    base64_data = base64.b64encode(buffer.getvalue()).decode('utf-8')
    
    map_data = {
        "topic": "/map",
        "resolution": 0.1,  # 0.1 m/pixel
        "size": [182, 59],
        "origin": [-8.1, -4.8],  # 左下角的距离坐标
        "data": base64_data
    }
    
    # 解码并标注
    image_bytes = base64.b64decode(base64_data)
    qimage = QImage()
    qimage.loadFromData(image_bytes)
    pixmap = QPixmap.fromImage(qimage)
    
    marked_pixmap = mark_origin_on_image(pixmap, map_data)
    
    # 保存结果
    output_path = "/tmp/map_with_origin.png"
    marked_pixmap.save(output_path)
    print(f"\n✓ 标注后的地图已保存到: {output_path}")


if __name__ == "__main__":
    main()
