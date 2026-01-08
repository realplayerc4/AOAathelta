"""
追踪位置标注功能测试
演示在地图上标注机器人位置和朝向
"""
import sys
import base64
import math
from PIL import Image, ImageDraw
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QPixmap, QImage, QPainter, QColor, QPen, QBrush
import io


def create_test_map_with_grid(width=182, height=59, resolution=0.1):
    """创建带网格的测试地图"""
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
    """标注坐标原点 [0, 0]"""
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


def mark_tracked_pose_on_image(pixmap: QPixmap, map_data: dict, pose_data: dict) -> QPixmap:
    """标注追踪位置和朝向（蓝色箭头）"""
    if not pose_data or 'pos' not in pose_data or 'ori' not in pose_data:
        return pixmap
    
    resolution = map_data.get('resolution', 1)
    origin = map_data.get('origin', [0, 0])
    size = map_data.get('size', [0, 0])
    
    pos = pose_data.get('pos', [0, 0])
    ori = pose_data.get('ori', 0)  # 弧度
    
    # 计算追踪位置的像素坐标
    pixel_x = (pos[0] - origin[0]) / resolution
    pixel_y_from_bottom = (pos[1] - origin[1]) / resolution
    pixel_y = size[1] - pixel_y_from_bottom
    
    # 检查位置是否在图像范围内
    if not (0 <= pixel_x < size[0] and 0 <= pixel_y < size[1]):
        return pixmap
    
    marked_pixmap = QPixmap(pixmap)
    painter = QPainter(marked_pixmap)
    
    # 设置蓝色画笔
    blue_color = QColor(0, 150, 255)
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
    
    # 绘制箭头头部
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


def main():
    """运行测试"""
    app = QApplication(sys.argv)
    
    # 创建测试地图数据
    map_data = {
        "topic": "/map",
        "resolution": 0.1,
        "size": [182, 59],
        "origin": [-8.1, -4.8],
        "data": create_test_map_with_grid(182, 59, 0.1)
    }
    
    # 解码地图
    image_bytes = base64.b64decode(map_data['data'])
    qimage = QImage()
    qimage.loadFromData(image_bytes)
    pixmap = QPixmap.fromImage(qimage)
    
    # 标注原点
    pixmap = mark_origin_on_image(pixmap, map_data)
    
    print("=" * 80)
    print("追踪位置标注功能测试")
    print("=" * 80)
    
    # 测试不同的追踪位置和朝向
    test_cases = [
        {
            "name": "朝向X正方向（向右）",
            "pos": [0.0, 0.0],
            "ori": 0,
        },
        {
            "name": "朝向Y正方向（向上）",
            "pos": [1.0, 1.0],
            "ori": math.pi / 2,
        },
        {
            "name": "朝向X负方向（向左）",
            "pos": [-1.0, 1.0],
            "ori": math.pi,
        },
        {
            "name": "朝向Y负方向（向下）",
            "pos": [-1.0, -1.0],
            "ori": -math.pi / 2,
        },
        {
            "name": "45度朝向",
            "pos": [2.0, 2.0],
            "ori": math.pi / 4,
        },
    ]
    
    for i, case in enumerate(test_cases):
        pose_data = {"pos": case["pos"], "ori": case["ori"]}
        test_pixmap = mark_origin_on_image(pixmap, map_data)
        test_pixmap = mark_tracked_pose_on_image(test_pixmap, map_data, pose_data)
        
        output_path = f"/tmp/test_tracked_pose_{i+1}.png"
        test_pixmap.save(output_path)
        
        print(f"\n【测试 {i+1}】{case['name']}")
        print(f"  位置: ({case['pos'][0]:.1f}, {case['pos'][1]:.1f}) 米")
        print(f"  朝向: {case['ori']:.2f} 弧度 ({math.degrees(case['ori']):.0f}°)")
        print(f"  结果: {output_path}")
    
    print("\n" + "=" * 80)
    print("✓ 所有测试完成")
    print("=" * 80)
    print("\n图例：")
    print("  🟢 绿色圆点 + 十字 = 坐标原点 [0, 0]")
    print("  🔵 蓝色圆点 + 箭头 = 追踪位置，箭头指向朝向")


if __name__ == "__main__":
    main()
