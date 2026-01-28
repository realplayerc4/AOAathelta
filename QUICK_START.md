# 🚀 快速参考 - 小车位置显示系统

## 🔗 API 端点

| 端点 | 方法 | 用途 | 示例 |
|------|------|------|------|
| `/api/robot-pose` | GET | 获取小车位置和朝向 | `curl http://127.0.0.1:5000/api/robot-pose` |
| `/api/position` | GET | 获取 Beacon 位置 | `curl http://127.0.0.1:5000/api/position` |
| `/api/status` | GET | 系统状态 | `curl http://127.0.0.1:5000/api/status` |
| `/api/start` | POST | 启动后端处理 | `curl -X POST -H "Content-Type: application/json" -d '{}' http://127.0.0.1:5000/api/start` |
| `/api/stop` | POST | 停止后端处理 | `curl -X POST http://127.0.0.1:5000/api/stop` |

## 🎯 数据格式

### robot_pose 响应
```json
{
  "x": 3.714396910859931,      // X 坐标（米）
  "y": -1.207133163499179,      // Y 坐标（米）
  "yaw": -3.093957603719854,    // 朝向角（弧度）
  "z": 0.0,                      // 高度
  "pitch": 0.0,                  // 俯仰角
  "roll": 0.0                    // 翻滚角
}
```

### 朝向角参考
| 角度 | 方向 |
|------|------|
| 0 rad | 向右 (东) |
| π/2 rad | 向上 (北) |
| π rad 或 -π rad | 向左 (西) |
| -π/2 rad | 向下 (南) |

## 💻 快速启动

### 方法 1: 使用启动脚本
```bash
cd /home/han14/gitw/AOAathelta
./run_web_ui.sh
```

### 方法 2: 直接运行
```bash
cd /home/han14/gitw/AOAathelta
python3 web_app.py
```

然后打开浏览器: http://127.0.0.1:5000

## 🎨 Web UI 界面

### 主要元素

| 元素 | 描述 | 颜色 |
|------|------|------|
| 箭头 | 小车位置和朝向 | 🔵 蓝色 |
| 圆点 | Beacon 信标位置 | 🔴 红色 |
| 矩形 | 用户绘制的检测区域 | 🟡 黄色 |
| 网格 | 坐标参考网格 | 灰色 |

### 交互操作

| 操作 | 功能 |
|------|------|
| 滚轮 | 缩放地图 |
| 拖拽 | 移动地图视图 |
| 点击+拖拽 | 绘制检测矩形 |
| 右下面板 | 查看小车坐标和朝向 |

## 📊 系统状态检查

```bash
# 检查系统是否运行
curl http://127.0.0.1:5000/api/status

# 检查小车位置（实时）
curl http://127.0.0.1:5000/api/robot-pose

# 检查 Beacon 位置
curl http://127.0.0.1:5000/api/position
```

## 🔧 故障排除

### 问题: Web UI 无法访问
```bash
# 检查 Flask 是否运行
ps aux | grep web_app

# 检查端口是否被占用
netstat -tlnp | grep 5000

# 重启服务
pkill -f "python3 web_app.py"
python3 web_app.py
```

### 问题: 小车位置不显示
```bash
# 检查小车 API 是否可访问
curl http://192.168.11.1:1448/api/core/slam/v1/localization/pose

# 检查 Flask API 是否返回数据
curl http://127.0.0.1:5000/api/robot-pose

# 检查系统是否已启动
curl http://127.0.0.1:5000/api/status
```

### 问题: 箭头方向不对
```bash
# 检查 yaw 值范围（应为 -π 到 π）
curl http://127.0.0.1:5000/api/robot-pose | python3 -c "import sys,json; print(json.load(sys.stdin)['yaw'])"

# 确认 API 返回的 yaw 单位为弧度
```

## 📈 性能参考

| 指标 | 值 |
|------|-----|
| 小车数据更新频率 | 20 Hz |
| Web 前端刷新频率 | 10 Hz |
| API 响应延迟 | < 100ms |
| 总系统延迟 | ~ 150ms |
| 内存占用 | ~ 50MB |
| CPU 使用率 | < 1% |

## 📁 关键文件

| 文件 | 用途 |
|------|------|
| `web_app.py` | Flask 后端主应用 |
| `templates/index.html` | Web UI 主页 |
| `static/js/map.js` | 地图可视化和交互 |
| `static/css/style.css` | UI 样式 |
| `core/api_client.py` | 小车 API 客户端 |
| `coordinate_transform.py` | 坐标变换 |

## 🎓 代码修改记录

### 小车位置显示实现

**文件**: `static/js/map.js`

```javascript
// 1. 添加 robotYaw 属性（第 32 行）
this.robotYaw = 0;

// 2. 实现 drawRobot() 方法（第 390-432 行）
drawRobot() {
    ctx.save();
    ctx.translate(pos.x, pos.y);
    ctx.rotate(this.robotYaw);
    // 绘制箭头
    ctx.restore();
}

// 3. 更新 updateRobot() 方法（第 476 行）
updateRobot(x, y, yaw = 0) {
    this.robotYaw = yaw;
    this.render();
}

// 4. 传递 yaw 参数（第 601 行）
mapViewer.updateRobot(robot.x, robot.y, robot.yaw);
```

**文件**: `web_app.py`

```python
# 独立更新 robot_pose（第 122-126 行）
if robot_pose:
    with position_lock:
        position_cache['robot_pose'] = robot_pose
        position_cache['timestamp'] = time.time()
```

## 📞 相关文档

- [完整测试报告](./ROBOT_LIVE_TEST.md)
- [实现详细说明](./ROBOT_ARROW_IMPLEMENTATION.md)
- [测试指南](./ROBOT_POSITION_TEST.md)
- [项目检查清单](./PROJECT_CHECKLIST.md)

---

**最后更新**: 2026-01-28  
**系统版本**: Flask 3.0+, Python 3.13+  
**状态**: ✅ 生产就绪
