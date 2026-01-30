# Beacon 5001 服务 - 串口初始化故障排除

## 快速检查

### 1️⃣ 检查串口设备是否存在

```bash
# 列出所有串口设备
ls -la /dev/tty*

# 或更精确的检查
ls -la /dev/ttyUSB* 2>/dev/null || echo "未找到 /dev/ttyUSB*"
```

### 2️⃣ 检查 USB 设备

```bash
# 查看已连接的 USB 设备
lsusb

# 监控 USB 连接状态
dmesg | tail -20
```

### 3️⃣ 检查用户权限

```bash
# 查看当前用户
whoami

# 查看用户所属的组
groups

# 检查是否在 dialout 组中
id -G | grep -o '20'  # 20 是 dialout 组的 GID（可能不同）
```

如果不在 `dialout` 组，运行：
```bash
sudo usermod -a -G dialout $USER
# 然后重新登录 shell 使变更生效
```

### 4️⃣ 运行诊断脚本

在树莓派上运行：
```bash
cd /home/han16/AOAathelta
python3 check_serial.py
```

### 5️⃣ 运行调试版本的服务

```bash
python3 beacon_filter_service_debug.py
```

此脚本会：
- ✓ 检查前置条件
- ✓ 检查串口设备
- ✓ 检查用户权限
- ✓ 测试串口连接
- ✓ 测试卡尔曼滤波器
- ✓ 启动服务并显示详细日志

---

## 常见问题

### ❌ "Connection refused" - 连接被拒绝

**原因**: 串口设备不可用或权限不足

**解决方案**:
```bash
# 1. 检查设备是否存在
ls -la /dev/ttyUSB0

# 2. 检查权限
stat /dev/ttyUSB0

# 3. 添加到 dialout 组
sudo usermod -a -G dialout $USER
```

### ❌ "No such file or directory" - 找不到串口设备

**原因**: Beacon 设备未连接或未被识别

**解决方案**:
```bash
# 1. 检查硬件连接
lsusb

# 2. 检查 dmesg 日志
dmesg | tail -30

# 3. 如果是新设备，可能需要驱动
# 查看 Beacon 设备的说明文档
```

### ⚠️ "Device not initialized" - 设备未初始化

**原因**: 串口初始化失败

**解决方案**:
```bash
# 1. 运行调试脚本
python3 beacon_filter_service_debug.py

# 2. 检查波特率是否正确
# 默认: 921600
# 也可以尝试: 115200

# 3. 检查串口参数
# 数据位: 8
# 停止位: 1
# 奇偶校验: 无
```

### ⚠️ 收不到数据

**原因**: 连接正常但 Beacon 设备无数据输出

**解决方案**:
```bash
# 1. 检查 Beacon 设备是否工作
# 使用串口监视工具
sudo minicom -D /dev/ttyUSB0 -b 921600

# 或
cat /dev/ttyUSB0

# 2. 检查 Beacon 设备配置
# 查看设备文档或制造商说明

# 3. 尝试不同的波特率
# 115200, 460800, 921600 等
```

---

## 修复步骤

### 方案 1：最小化重启

如果修改了权限或进行了系统配置，需要重新登录：
```bash
# 退出当前 SSH 连接
exit

# 重新连接
ssh han16@192.168.0.144
```

### 方案 2：手动指定串口

编辑 `beacon_filter_service.py` 中的主程序，直接指定串口：

```python
# 第 280 行附近
port = '/dev/ttyUSB0'  # 改为你的实际串口
```

### 方案 3：检查驱动

某些 Beacon 设备需要特定的 USB 驱动：

```bash
# 查看已安装的驱动
lsmod | grep usb

# 安装常见的驱动
sudo apt-get install usb-serial-simple
```

### 方案 4：尝试不同的波特率

如果 921600 无法工作，尝试其他波特率：

编辑 `beacon_filter_service.py`：
```python
# 第 298 行附近
if init_services(port=port, baudrate=115200):  # 改为 115200
```

---

## 高级诊断

### 使用 strace 跟踪系统调用

```bash
python3 -m pip install strace  # 如果需要

strace -e trace=open,openat,read,write python3 beacon_filter_service.py 2>&1 | grep -i "tty\|dev"
```

### 使用 minicom 测试串口

```bash
# 安装 minicom
sudo apt-get install minicom

# 打开串口
sudo minicom -D /dev/ttyUSB0 -b 921600

# 按 Ctrl+A 然后 Q 退出
```

### 检查串口设置

```bash
# 查看串口配置
stty -F /dev/ttyUSB0

# 设置串口参数
stty -F /dev/ttyUSB0 921600 cs8 -cstopb -parenb
```

---

## 验证修复

修复后，确认服务正常工作：

```bash
# 1. 启动服务
python3 beacon_filter_service.py

# 2. 在另一个终端测试 API
curl http://127.0.0.1:5001/api/beacon

# 3. 应该返回类似的 JSON:
# {
#   "x": 1.23,
#   "y": 4.56,
#   "distance": 5.0,
#   "angle": 45.5,
#   "confidence": 0.85,
#   ...
# }
```

---

## 联系支持

如果问题仍未解决：

1. 收集诊断信息：
```bash
python3 check_serial.py > diagnostic.log 2>&1
python3 beacon_filter_service_debug.py > service_debug.log 2>&1
```

2. 查看日志：
```bash
cat diagnostic.log
cat service_debug.log
```

3. 提供以下信息：
   - `check_serial.py` 的输出
   - `dmesg | tail -50` 的输出
   - `lsusb` 的输出
   - 相关的错误消息

