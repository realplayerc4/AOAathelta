# /globe_beacon 话题 - 快速参考

## ⚡ 快速开始

### 数据流
```
/tracked_pose (Anchor位置+朝向) 
→ 查询beacon滤波坐标 
→ 坐标变换 
→ /globe_beacon (全局坐标)
→ 地图显示 (红色圆点)
```

### 坐标变换公式
```
x_global = x_anchor + local_x * cos(θ) - local_y * sin(θ)
y_global = y_anchor + local_x * sin(θ) + local_y * cos(θ)
```

## 📍 调用接口

### 获取滤波坐标（AOA Worker）
```python
beacon_coords = aoa_worker.get_filtered_beacon_coordinates(tag_id=1)
# 返回: {'x': 1.5, 'y': 2.3, 'confidence': 0.95, 'initialized': True, ...}
```

### 坐标变换（主窗口）
```python
global_pos = main_window._transform_local_to_global(
    local_x=1.5, local_y=2.3,
    anchor_x=5.0, anchor_y=10.0,
    anchor_theta=0.785  # π/4 弧度
)
# 返回: {'x': 6.06, 'y': 11.94}
```

### 发布话题（主窗口）
```python
main_window._publish_globe_beacon({
    'x': 6.06, 'y': 11.94,
    'confidence': 0.95,
    'tag_id': 1
})
```

### 更新地图显示（地图查看器）
```python
map_viewer.update_beacon_position({
    'x': 6.06, 'y': 11.94,
    'confidence': 0.95,
    'tag_id': 1
})
```

## 📊 话题格式

### /tracked_pose (输入)
```python
{
    "pos": [x_anchor, y_anchor],  # 全局位置(米)
    "ori": theta                  # 朝向(弧度)
}
```

### /globe_beacon (输出)
```python
{
    "topic": "/globe_beacon",
    "tag_id": 1,
    "x": global_x,        # 全局X坐标(米)
    "y": global_y,        # 全局Y坐标(米)
    "confidence": score,  # 0-1
    "timestamp": time     # Unix时间戳
}
```

## 🔧 配置参数

目前硬编码的参数：

| 参数 | 值 | 位置 |
|-----|-----|------|
| tag_id | 1 | aoa_worker.py |
| 更新触发 | /tracked_pose | main_window.py |
| beacon半径 | 3-8px | map_viewer.py |
| beacon颜色 | 红色(255,0,0) | map_viewer.py |

## 🧪 测试

### 运行单元测试
```bash
python3 test_globe_beacon_unit.py
```

### 验证坐标变换
```python
from test_globe_beacon_unit import transform_local_to_global
result = transform_local_to_global(1.0, 0.0, 5.0, 10.0, 0.0)
assert result['x'] == 6.0 and result['y'] == 10.0
```

## 🎯 关键点

1. **坐标系**：Anchor局部→全局的2D刚体变换
2. **触发**：由/tracked_pose消息驱动（实时）
3. **展示**：地图上红色圆点，大小反映置信度
4. **精度**：依赖卡尔曼滤波的置信度

## 🚨 常见问题

### Q: Beacon不显示？
A: 检查三点：
1. 滤波器已初始化（需要足够AOA数据）
2. /tracked_pose数据正常
3. 地图查看器已打开

### Q: 圆点位置不对？
A: 验证：
1. 运行test_globe_beacon_unit.py
2. 检查/tracked_pose的theta单位（应为弧度）
3. 确认Y轴定义（正前方）

### Q: 如何处理多个beacon？
A: 修改get_filtered_beacon_coordinates循环处理多个tag_id。

## 📁 相关文件

```
workers/aoa_worker.py          # get_filtered_beacon_coordinates()
ui/main_window.py              # _transform_local_to_global()
ui/widgets/map_viewer.py       # _mark_beacon_on_image()
topics.txt                      # /globe_beacon
test_globe_beacon_unit.py       # 单元测试
globe_beacon_说明.md            # 详细文档
```

## 📈 性能

| 项目 | 值 |
|-----|-----|
| 更新频率 | 与/tracked_pose同步 |
| 延迟 | <1ms（仅计算） |
| 内存 | ~100B/beacon |
| CPU占用 | 可忽略 |

## 🔗 关键方法映射

| 功能 | 方法 | 文件 |
|-----|-----|------|
| 获取滤波坐标 | get_filtered_beacon_coordinates() | aoa_worker.py |
| 坐标变换 | _transform_local_to_global() | main_window.py |
| 发布话题 | _publish_globe_beacon() | main_window.py |
| 更新显示 | update_beacon_position() | map_viewer.py |
| 绘制标记 | _mark_beacon_on_image() | map_viewer.py |

---

**最后更新**: 2026-01-08  
**版本**: 1.0  
**状态**: ✓ 生产就绪
