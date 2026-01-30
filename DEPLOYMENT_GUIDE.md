# AOA 定位系统 - 部署指南

## 快速部署到树莓派

### 前置条件
- 树莓派地址: `192.168.0.144`
- 用户名: `han16`
- 密码: `1`
- 树莓派已安装 Python 3.7+ 和 SSH

### 方法1：使用 Python 部署脚本（推荐）

```bash
# 在本地电脑上执行
cd /home/han14/gitw/AOAathelta
python3 deploy_to_raspi.py
```

这个脚本会自动：
- 上传项目文件
- 安装所有依赖
- 创建启动脚本
- 验证安装

### 方法2：使用 Bash 部署脚本

```bash
# 在本地电脑上执行
cd /home/han14/gitw/AOAathelta
bash deploy_to_raspi.sh
```

### 方法3：手动部署

#### 第1步：上传项目到树莓派
```bash
scp -r /home/han14/gitw/AOAathelta han16@192.168.0.144:/home/han16/
```

#### 第2步：连接树莓派并安装依赖
```bash
ssh han16@192.168.0.144
cd /home/han16/AOAathelta
pip3 install -r requirements.txt
```

#### 第3步：启动服务
```bash
# 前台运行（查看日志）
python3 start_services.py

# 或后台运行
nohup python3 start_services.py > services.log 2>&1 &
```

---

## 在树莓派上启动服务

### 方式1：前台运行（推荐用于测试）
```bash
ssh han16@192.168.0.144 '/home/han16/AOAathelta/run_services.sh'
```

### 方式2：后台运行（推荐用于生产）
```bash
ssh han16@192.168.0.144 '/home/han16/AOAathelta/run_services_background.sh'
```

### 方式3：直接运行
```bash
ssh han16@192.168.0.144 'cd /home/han16/AOAathelta && python3 start_services.py'
```

---

## 停止服务

```bash
# 使用停止脚本
ssh han16@192.168.0.144 '/home/han16/AOAathelta/stop_services.sh'

# 或手动停止
ssh han16@192.168.0.144 'pkill -f start_services.py'
```

---

## 访问服务

### 从树莓派本地访问
- Web UI: http://localhost:5000
- API: http://localhost:5001/api/beacon

### 从其他电脑访问
- Web UI: http://192.168.0.144:5000
- API: http://192.168.0.144:5001/api/beacon

### 使用 curl 测试
```bash
# 测试 Web 服务
curl http://192.168.0.144:5000/

# 获取 Beacon 数据
curl http://192.168.0.144:5001/api/beacon

# 获取统计信息
curl http://192.168.0.144:5001/api/stats
```

---

## 查看日志

### 实时查看日志（后台运行时）
```bash
ssh han16@192.168.0.144 'tail -f /home/han16/AOAathelta/services.log'
```

### 查看所有日志
```bash
ssh han16@192.168.0.144 'cat /home/han16/AOAathelta/services.log'
```

---

## 配置开机自启

### 方法1：使用 crontab

在树莓派上编辑 crontab：
```bash
crontab -e
```

添加以下行：
```bash
@reboot cd /home/han16/AOAathelta && python3 start_services.py > /home/han16/services.log 2>&1 &
```

### 方法2：使用 systemd service（推荐）

在树莓派上创建服务文件：
```bash
sudo nano /etc/systemd/system/aoa-services.service
```

粘贴以下内容：
```ini
[Unit]
Description=AOA Localization System Services
After=network.target

[Service]
Type=simple
User=han16
WorkingDirectory=/home/han16/AOAathelta
ExecStart=/usr/bin/python3 /home/han16/AOAathelta/start_services.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启用服务：
```bash
sudo systemctl daemon-reload
sudo systemctl enable aoa-services
sudo systemctl start aoa-services
```

查看状态：
```bash
sudo systemctl status aoa-services
sudo journalctl -u aoa-services -f
```

---

## 故障排除

### 连接被拒绝
```bash
# 检查 SSH 连接
ssh -v han16@192.168.0.144 'echo OK'

# 检查树莓派 IP
ping 192.168.0.144
```

### 端口已占用
```bash
# 查看占用 5000/5001 的进程
lsof -i :5000
lsof -i :5001

# 停止冲突的进程
pkill -f "python.*5000"
```

### Python 模块缺失
```bash
# 重新安装依赖
pip3 install -r /home/han16/AOAathelta/requirements.txt --upgrade
```

### 串口连接失败
```bash
# 查看可用的串口设备
ls -la /dev/ttyUSB*

# 检查权限
groups han16
```

---

## 性能监控

### 监控进程资源使用
```bash
ssh han16@192.168.0.144 'watch -n 1 "ps aux | grep python3"'
```

### 查看系统资源
```bash
ssh han16@192.168.0.144 'free -h && df -h && top -b -n 1 | head -20'
```

---

## 常用命令参考

| 命令 | 说明 |
|-----|------|
| `python3 deploy_to_raspi.py` | 自动部署到树莓派 |
| `ssh han16@192.168.0.144 '/home/han16/AOAathelta/run_services.sh'` | 启动服务（前台） |
| `ssh han16@192.168.0.144 '/home/han16/AOAathelta/stop_services.sh'` | 停止服务 |
| `curl http://192.168.0.144:5000/` | 测试 Web 服务 |
| `curl http://192.168.0.144:5001/api/beacon` | 获取 Beacon 数据 |
| `ssh han16@192.168.0.144 'tail -f /home/han16/AOAathelta/services.log'` | 查看实时日志 |

