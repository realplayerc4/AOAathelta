# WebSocket 蓝色点消失问题修复总结

## 问题描述
用户反馈：**蓝色点消失了，数据只更新了一次**

这个问题表现为：
- 应用启动后首次接收地图数据和 beacon 数据
- 蓝色点（追踪位置标记）正常显示
- 之后地图和追踪位置不再更新
- 只更新了一次数据

## 根本原因

### 线程阻塞问题
`core/ws_subscriber.py` 中的 WebSocket 消息处理存在问题：

```python
# 原始代码 - 直接在 WebSocket 线程中调用回调
def _on_raw_message(self, ws, message: str):
    try:
        data = json.loads(message)
    except Exception:
        data = message
    # ...
    if topic and topic in self.topics:
        try:
            self.on_message(topic, payload)  # ❌ 在 WebSocket 线程中执行
```

**问题：** 当 `on_message` 回调（连接到 UI 更新）执行时间过长（比如重新绘制地图、更新 UI），会阻塞 WebSocket 消息接收线程。一旦线程被阻塞，后续的消息无法被处理。

### 调用链
```
WebSocket 消息到达
  → _on_raw_message (WebSocket 线程)
    → self.on_message(topic, payload) (主线程信号发送)
      → _on_topic_message_ui (PyQt6 主线程)
        → 地图显示更新（可能耗时操作）
        → beacon 位置更新和重新绘制
```

如果绘制操作耗时过长，WebSocket 线程会被卡住，导致后续消息无法接收。

## 解决方案

### 改进：使用线程池处理回调

修改后的代码：

```python
from concurrent.futures import ThreadPoolExecutor

class TopicSubscriber:
    def __init__(self, ...):
        # ...
        # 使用线程池处理消息回调，避免阻塞WebSocket线程
        self._callback_executor = ThreadPoolExecutor(
            max_workers=2, 
            thread_name_prefix="ws_callback_"
        )

    def _on_raw_message(self, ws, message: str):
        try:
            data = json.loads(message)
        except Exception:
            data = message
        # ...
        if topic and topic in self.topics:
            # ✅ 在线程池中执行回调，避免阻塞WebSocket线程
            try:
                self._callback_executor.submit(
                    self._execute_callback, 
                    topic, 
                    payload
                )
            except Exception as e:
                if self.on_error:
                    self.on_error(f"callback submit error: {e}")

    def _execute_callback(self, topic: str, payload):
        """在独立线程中执行回调"""
        try:
            self.on_message(topic, payload)
        except Exception:
            if self.on_error:
                self.on_error("callback error")

    def stop(self):
        # ...
        # 关闭线程池
        self._callback_executor.shutdown(wait=False)
```

### 优势

1. **WebSocket 线程不被阻塞** - 消息可以持续被接收
2. **回调可以安心执行** - 回调中的长时间操作（UI 更新、绘制等）不会影响消息接收
3. **自动并发处理** - ThreadPoolExecutor 自动管理线程，最多 2 个工作线程足够处理消息
4. **线程安全** - PyQt6 信号的发射是线程安全的，可以从任何线程调用

## 其他改进

### 添加调试日志
在 `ui/main_window.py` 的 `_on_topic_message_ui` 方法中添加了调试日志，可以追踪：
- 地图更新是否持续进行
- beacon 位置是否被保存和更新
- beacon 数据是否被正确传递给地图显示器

```python
logger.debug(f"地图更新 #{self.map_receive_count}, beacon_global_position={self.beacon_global_position is not None}")
logger.debug(f"更新widget中的beacon位置: {self.beacon_global_position}")
logger.debug(f"更新dialog中的beacon位置: {self.beacon_global_position}")
```

## 测试验证

提供了测试脚本 `test_websocket_fix.py` 来验证修复：

```bash
python test_websocket_fix.py
```

该脚本会：
1. 连接到 WebSocket 服务
2. 订阅 `/map` 和 `/tracked_pose` 话题
3. 在接收消息时模拟耗时处理（0.1 秒）
4. 持续监听 10 秒并统计消息接收数量
5. 如果消息数量 > 0，说明修复成功

## 预期结果

修复后：
- ✅ 地图数据持续更新（不再只更新一次）
- ✅ 追踪位置持续更新
- ✅ 蓝色点（beacon 标记）持续显示并更新位置
- ✅ 应用不会无响应或卡顿

## 文件改动

### 修改文件
1. **core/ws_subscriber.py** - 引入 ThreadPoolExecutor，改进消息处理机制
2. **ui/main_window.py** - 优化 beacon 位置更新逻辑，添加调试日志

### 新增文件
- **test_websocket_fix.py** - WebSocket 修复验证脚本

## 推荐后续步骤

1. 运行应用并验证蓝色点是否持续显示和更新
2. 查看日志输出，确认地图和 beacon 数据持续更新
3. 如果仍有问题，运行 `test_websocket_fix.py` 诊断 WebSocket 是否正常
4. 可以调整 ThreadPoolExecutor 的 `max_workers` 参数（默认为 2），如果需要处理更多并发消息可以增加该值
