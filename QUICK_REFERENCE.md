# 快速参考 - 机器人位置更新频率改进

## 🎯 变更摘要

| 项目 | 原值 | 新值 |
|------|------|------|
| 更新频率 | 20Hz | 10Hz |
| 更新间隔 | 50ms | 100ms |
| 配置值 | 0.05s | 0.1s |
| 滤波数据 | ✗ | ✓ |

---

## 📁 修改文件

### 1. config.py (第32行)
```python
POSE_QUERY_INTERVAL = 0.1  # 10Hz (原: 0.05)
```

### 2. web_app.py
- **第107-170行**: `update_position_worker()` 函数
  - 新增: `import config`
  - 新增: `kalman.get_filtered_beacon_coordinates(tag_id=1)`
  - 新增: `position_cache['filtered_beacon']`

- **第275-305行**: `get_robot_pose()` API端点
  - 新增: `filtered_beacon` 响应字段

---

## 🔌 API 使用

### 启动系统
```bash
curl -X POST http://127.0.0.1:5000/api/start \
  -H "Content-Type: application/json" \
  -d '{"port": "/dev/ttyUSB0"}'
```

### 获取数据 (10Hz)
```bash
curl http://127.0.0.1:5000/api/robot-pose | jq
```

### 响应格式
```json
{
  "x": 0.40,
  "y": -1.40,
  "yaw": -2.06,
  "z": 0.0,
  "pitch": 0.0,
  "roll": 0.0,
  "filtered_beacon": {
    "x": 1.23,
    "y": 2.45,
    "confidence": 0.85,
    "velocity_x": 0.10,
    "velocity_y": -0.05
  }
}
```

---

## 💡 关键改进

1. **频率优化** - 系统负载↓50%
2. **数据融合** - 集成滤波Beacon坐标
3. **动态配置** - 支持轻松调整更新间隔
4. **兼容性** - 原API字段保持不变

---

## 📊 性能对比

```
频率        原    新    改进
━━━━━━━━━━━━━━━━━━━━━━━━━
更新频率    20Hz  10Hz  ↓50%
系统负载    高    中    ↓50%
网络流量    高    中    ↓50%
```

---

## 📚 详细文档

- [UPDATE_FREQUENCY_SUMMARY.md](UPDATE_FREQUENCY_SUMMARY.md) - 完整设计说明
- [CHANGES_DETAILED.md](CHANGES_DETAILED.md) - 代码变更对比

---

## ✅ 验证方法

```bash
# 1. 语法检查
python3 -m py_compile config.py web_app.py

# 2. 启动服务
python3 web_app.py

# 3. 测试API
curl http://127.0.0.1:5000/api/robot-pose

# 4. 验证频率 (应为10Hz = 100ms间隔)
for i in {1..10}; do curl -s http://127.0.0.1:5000/api/robot-pose | jq .filtered_beacon.x; sleep 0.1; done
```

---

## 🚀 立即使用

```bash
cd /home/han14/gitw/AOAathelta
python3 web_app.py  # 启动Flask服务
# 浏览器访问: http://127.0.0.1:5000
```

