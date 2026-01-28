/* ==================== 地图和交互逻辑 ==================== */

class MapViewer {
    constructor(canvasId) {
        this.canvas = document.getElementById(canvasId);
        this.ctx = this.canvas.getContext('2d');
        
        // 地图数据
        this.mapImage = null;
        this.mapInfo = null;
        
        // 缩放和平移
        this.zoom = 1;
        this.offsetX = 0;
        this.offsetY = 0;
        
        // 交互状态
        this.isDrawing = false;
        this.drawMode = false;  // false: 平移/缩放, true: 绘制区域
        this.startX = 0;
        this.startY = 0;
        this.currentZone = null;
        
        // 检测区域列表
        this.zones = [];
        
        // Beacon 位置
        this.beaconX = null;
        this.beaconY = null;
        
        // Beacon 全局坐标
        this.beaconGlobeX = null;
        this.beaconGlobeY = null;
        
        // 机器人位置和朝向
        this.robotX = null;
        this.robotY = null;
        this.robotYaw = 0;
        
        // 事件监听
        this.setupEventListeners();
    }
    
    setupEventListeners() {
        // 鼠标事件
        this.canvas.addEventListener('mousedown', (e) => this.onMouseDown(e));
        this.canvas.addEventListener('mousemove', (e) => this.onMouseMove(e));
        this.canvas.addEventListener('mouseup', (e) => this.onMouseUp(e));
        this.canvas.addEventListener('mouseleave', (e) => this.onMouseLeave(e));
        
        // 滚轮缩放
        this.canvas.addEventListener('wheel', (e) => this.onWheel(e), false);
        
        // 触摸事件（移动设备支持）
        this.canvas.addEventListener('touchstart', (e) => this.onTouchStart(e));
        this.canvas.addEventListener('touchmove', (e) => this.onTouchMove(e));
        this.canvas.addEventListener('touchend', (e) => this.onTouchEnd(e));
    }
    
    // ==================== 坐标转换 ====================
    
    /**
     * 将世界坐标转换为画布坐标
     * 参考标准方法：
     * 1. grid_x = (real_x - origin_x) / resolution
     * 2. grid_y = (real_y - origin_y) / resolution  
     * 3. 再应用缩放和偏移
     * 4. Y轴反转：由于PNG图像行顺序与坐标系相反
     */
    worldToCanvas(x, y) {
        // 转换到栅格坐标（相对于原点的距离）
        const gridX = (x - this.mapInfo.origin_x) / this.mapInfo.resolution;
        const gridY = (y - this.mapInfo.origin_y) / this.mapInfo.resolution;
        
        // 应用缩放和偏移到画布坐标
        const canvasX = gridX * this.zoom + this.offsetX;
        
        // Y轴反转：图像行顺序与坐标系Y方向相反
        const mapHeight = this.mapImage.height;
        const canvasY = (mapHeight - gridY) * this.zoom + this.offsetY;
        
        return { x: canvasX, y: canvasY };
    }
    
    /**
     * 将画布坐标转换为世界坐标
     * 逆向转换
     */
    canvasToWorld(canvasX, canvasY) {
        // 从画布坐标恢复到栅格坐标
        const gridX = (canvasX - this.offsetX) / this.zoom;
        
        // Y轴反转恢复
        const mapHeight = this.mapImage.height;
        const gridY = mapHeight - (canvasY - this.offsetY) / this.zoom;
        
        // 转换到世界坐标
        const x = gridX * this.mapInfo.resolution + this.mapInfo.origin_x;
        const y = gridY * this.mapInfo.resolution + this.mapInfo.origin_y;
        
        return { x, y };
    }
    
    // ==================== 鼠标事件处理 ====================
    
    onMouseDown(e) {
        const rect = this.canvas.getBoundingClientRect();
        this.startX = e.clientX - rect.left;
        this.startY = e.clientY - rect.top;
        this.isDrawing = true;
        
        if (this.drawMode) {
            // 开始绘制矩形
            const world = this.canvasToWorld(this.startX, this.startY);
            this.currentZone = {
                x1: world.x,
                y1: world.y,
                x2: world.x,
                y2: world.y,
                id: Date.now()
            };
        }
    }
    
    onMouseMove(e) {
        const rect = this.canvas.getBoundingClientRect();
        const currentX = e.clientX - rect.left;
        const currentY = e.clientY - rect.top;
        
        // 更新坐标显示
        if (this.mapInfo) {
            const world = this.canvasToWorld(currentX, currentY);
            document.getElementById('coordinates').textContent = 
                `(${world.x.toFixed(2)}, ${world.y.toFixed(2)})`;
        }
        
        if (this.isDrawing) {
            if (this.drawMode && this.currentZone) {
                // 更新正在绘制的矩形
                const world = this.canvasToWorld(currentX, currentY);
                this.currentZone.x2 = world.x;
                this.currentZone.y2 = world.y;
                this.render();
            } else if (!this.drawMode) {
                // 平移模式
                this.offsetX += currentX - this.startX;
                this.offsetY += currentY - this.startY;
                this.startX = currentX;
                this.startY = currentY;
                this.render();
            }
        }
    }
    
    onMouseUp(e) {
        if (this.isDrawing && this.drawMode && this.currentZone) {
            // 完成区域绘制
            this.zones.push(this.currentZone);
            this.currentZone = null;
            this.updateZonesDisplay();
            console.log('✓ 区域已添加');
        }
        this.isDrawing = false;
    }
    
    onMouseLeave(e) {
        this.isDrawing = false;
    }
    
    onWheel(e) {
        e.preventDefault();
        
        if (!this.mapInfo) return;
        
        const rect = this.canvas.getBoundingClientRect();
        const mouseX = e.clientX - rect.left;
        const mouseY = e.clientY - rect.top;
        
        const zoomFactor = e.deltaY > 0 ? 0.9 : 1.1;
        const newZoom = Math.max(0.1, Math.min(10, this.zoom * zoomFactor));
        
        // 保持鼠标位置不变
        this.offsetX = mouseX - (mouseX - this.offsetX) * (newZoom / this.zoom);
        this.offsetY = mouseY - (mouseY - this.offsetY) * (newZoom / this.zoom);
        
        this.zoom = newZoom;
        document.getElementById('zoomLevel').textContent = (this.zoom * 100).toFixed(0) + '%';
        
        this.render();
    }
    
    // ==================== 触摸事件处理 ====================
    
    onTouchStart(e) {
        if (e.touches.length === 1) {
            const touch = e.touches[0];
            const rect = this.canvas.getBoundingClientRect();
            this.startX = touch.clientX - rect.left;
            this.startY = touch.clientY - rect.top;
            this.isDrawing = true;
        }
    }
    
    onTouchMove(e) {
        if (e.touches.length === 1 && this.isDrawing) {
            const touch = e.touches[0];
            const rect = this.canvas.getBoundingClientRect();
            const currentX = touch.clientX - rect.left;
            const currentY = touch.clientY - rect.top;
            
            // 平移
            this.offsetX += currentX - this.startX;
            this.offsetY += currentY - this.startY;
            this.startX = currentX;
            this.startY = currentY;
            
            this.render();
        }
    }
    
    onTouchEnd(e) {
        this.isDrawing = false;
    }
    
    // ==================== 地图加载和显示 ====================
    
    async loadMap() {
        try {
            // 获取地图信息
            const mapInfoResponse = await fetch('/api/map-info');
            this.mapInfo = await mapInfoResponse.json();
            
            console.log('📍 地图信息:', this.mapInfo);
            console.log('📍 原点坐标:', { x: this.mapInfo.origin_x, y: this.mapInfo.origin_y });
            
            // 更新地图信息显示
            document.getElementById('mapOriginX').textContent = 
                this.mapInfo.origin_x.toFixed(2);
            document.getElementById('mapOriginY').textContent = 
                this.mapInfo.origin_y.toFixed(2);
            document.getElementById('mapSize').textContent = 
                `${(this.mapInfo.width * this.mapInfo.resolution).toFixed(1)}m × ${(this.mapInfo.height * this.mapInfo.resolution).toFixed(1)}m`;
            document.getElementById('mapResolution').textContent = 
                `${this.mapInfo.resolution}m/px (${(1/this.mapInfo.resolution).toFixed(0)}px/m)`;
            
            // 获取地图栅格数据
            const mapDataResponse = await fetch('/api/map-data');
            const mapData = await mapDataResponse.json();
            
            // 加载地图图像
            this.mapImage = new Image();
            this.mapImage.onload = () => {
                console.log('✓ 地图加载完成');
                
                // 调整 canvas 尺寸
                this.canvas.width = this.mapImage.width;
                this.canvas.height = this.mapImage.height;
                
                // 重置缩放和偏移
                this.zoom = 1;
                this.offsetX = 0;
                this.offsetY = 0;
                
                this.render();
            };
            
            this.mapImage.onerror = () => {
                console.error('✗ 地图加载失败');
                alert('无法加载地图数据');
            };
            
            this.mapImage.src = 'data:image/png;base64,' + mapData.image;
        } catch (error) {
            console.error('✗ 地图加载异常:', error);
            alert('地图加载失败: ' + error.message);
        }
    }
    
    clearMap() {
        this.mapImage = null;
        this.mapInfo = null;
        this.zones = [];
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        document.getElementById('mapOriginX').textContent = '-';
        document.getElementById('mapOriginY').textContent = '-';
        document.getElementById('mapSize').textContent = '-';
        document.getElementById('mapResolution').textContent = '-';
    }
    
    // ==================== 绘制逻辑 ====================
    
    render() {
        if (!this.mapImage || !this.mapInfo) {
            this.ctx.fillStyle = '#f0f0f0';
            this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
            this.ctx.fillStyle = '#999';
            this.ctx.font = '16px sans-serif';
            this.ctx.textAlign = 'center';
            this.ctx.fillText('点击"加载地图"按钮加载地图', 
                this.canvas.width / 2, this.canvas.height / 2);
            return;
        }
        
        // 清空画布
        this.ctx.fillStyle = '#fff';
        this.ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
        
        // 保存当前状态
        this.ctx.save();
        
        // 应用变换
        this.ctx.translate(this.offsetX, this.offsetY);
        this.ctx.scale(this.zoom, this.zoom);
        
        // 绘制地图
        const mapWidth = this.mapImage.width;
        const mapHeight = this.mapImage.height;
        this.ctx.drawImage(this.mapImage, 0, 0, mapWidth, mapHeight);
        
        // 绘制网格（辅助定位）
        this.drawGrid();
        
        // 坐标轴已经绘制到图片中（后端生成），不再需要这里绘制
        // this.drawOriginAxes();
        
        // 绘制检测区域
        this.drawZones();
        
        // 恢复状态
        this.ctx.restore();
        
        // 绘制 Beacon 全局位置和机器人（画布坐标系）
        // 只显示 beacon globe，隐藏相对位置
        this.drawBeaconGlobe();
        this.drawRobot();
    }
    
    drawGrid() {
        const step = Math.ceil(10 / this.zoom);  // 每 10m 一格
        const mapWidth = this.mapImage.width;
        const mapHeight = this.mapImage.height;
        
        this.ctx.strokeStyle = 'rgba(200, 200, 200, 0.3)';
        this.ctx.lineWidth = 0.5;
        
        // 竖线
        for (let x = 0; x < mapWidth; x += step) {
            this.ctx.beginPath();
            this.ctx.moveTo(x, 0);
            this.ctx.lineTo(x, mapHeight);
            this.ctx.stroke();
        }
        
        // 横线
        for (let y = 0; y < mapHeight; y += step) {
            this.ctx.beginPath();
            this.ctx.moveTo(0, y);
            this.ctx.lineTo(mapWidth, y);
            this.ctx.stroke();
        }
    }
    
    drawOriginAxes() {
        // 绘制坐标原点的XY轴箭头
        // 使用worldToCanvas来确保与其他地方的计算一致
        const originPos = this.worldToCanvas(0, 0);  // 世界坐标原点(0, 0)
        const originCanvasX = originPos.x;
        const originCanvasY = originPos.y;
        
        // 调试日志
        console.log('🎯 原点计算:', {
            worldCoord: { x: 0, y: 0 },
            canvasCoord: { x: originCanvasX, y: originCanvasY },
            mapInfo: {
                origin: { x: this.mapInfo.origin_x, y: this.mapInfo.origin_y },
                resolution: this.mapInfo.resolution,
                imageSize: { width: this.mapImage.width, height: this.mapImage.height }
            },
            transform: {
                zoom: this.zoom,
                offsetX: this.offsetX,
                offsetY: this.offsetY
            }
        });
        
        const arrowLength = 50;  // 箭头长度（像素）
        const arrowHeadSize = 10;  // 箭头头大小
        
        // X轴（红色）- 向右
        this.ctx.strokeStyle = '#ff0000';
        this.ctx.fillStyle = '#ff0000';
        this.ctx.lineWidth = 2;
        
        // X轴线
        this.ctx.beginPath();
        this.ctx.moveTo(originCanvasX, originCanvasY);
        this.ctx.lineTo(originCanvasX + arrowLength, originCanvasY);
        this.ctx.stroke();
        
        // X轴箭头头部
        const xArrowTip = originCanvasX + arrowLength;
        this.ctx.beginPath();
        this.ctx.moveTo(xArrowTip, originCanvasY);
        this.ctx.lineTo(xArrowTip - arrowHeadSize, originCanvasY - arrowHeadSize / 2);
        this.ctx.lineTo(xArrowTip - arrowHeadSize, originCanvasY + arrowHeadSize / 2);
        this.ctx.closePath();
        this.ctx.fill();
        
        // Y轴（绿色）- 向上
        this.ctx.strokeStyle = '#00c800';
        this.ctx.fillStyle = '#00c800';
        this.ctx.lineWidth = 2;
        
        // Y轴线（向上，在Canvas中减少Y值）
        this.ctx.beginPath();
        this.ctx.moveTo(originCanvasX, originCanvasY);
        this.ctx.lineTo(originCanvasX, originCanvasY - arrowLength);
        this.ctx.stroke();
        
        // Y轴箭头头部（指向上方）
        const yArrowTip = originCanvasY - arrowLength;
        this.ctx.beginPath();
        this.ctx.moveTo(originCanvasX, yArrowTip);
        this.ctx.lineTo(originCanvasX - arrowHeadSize / 2, yArrowTip + arrowHeadSize);
        this.ctx.lineTo(originCanvasX + arrowHeadSize / 2, yArrowTip + arrowHeadSize);
        this.ctx.closePath();
        this.ctx.fill();
        
        // 原点圆点
        this.ctx.fillStyle = '#000000';
        this.ctx.beginPath();
        this.ctx.arc(originCanvasX, originCanvasY, 3, 0, Math.PI * 2);
        this.ctx.fill();
    }
    
    drawZones() {
        // 已保存的区域
        for (const zone of this.zones) {
            this.drawZoneRect(zone, '#ffc107', 0.2);
        }
        
        // 正在绘制的区域
        if (this.currentZone) {
            this.drawZoneRect(this.currentZone, '#ff6b6b', 0.3);
        }
    }
    
    drawZoneRect(zone, color, alpha) {
        // 使用标准坐标转换方法（需要Y轴反转）
        const x1 = (zone.x1 - this.mapInfo.origin_x) / this.mapInfo.resolution;
        const x2 = (zone.x2 - this.mapInfo.origin_x) / this.mapInfo.resolution;
        
        const mapHeight = this.mapImage.height;
        const y1 = mapHeight - ((zone.y1 - this.mapInfo.origin_y) / this.mapInfo.resolution);
        const y2 = mapHeight - ((zone.y2 - this.mapInfo.origin_y) / this.mapInfo.resolution);
        
        const minX = Math.min(x1, x2);
        const maxX = Math.max(x1, x2);
        const minY = Math.min(y1, y2);
        const maxY = Math.max(y1, y2);
        
        // 应用缩放和偏移
        const canvasMinX = minX * this.zoom + this.offsetX;
        const canvasMaxX = maxX * this.zoom + this.offsetX;
        const canvasMinY = minY * this.zoom + this.offsetY;
        const canvasMaxY = maxY * this.zoom + this.offsetY;
        
        // 填充
        this.ctx.fillStyle = color;
        this.ctx.globalAlpha = alpha;
        this.ctx.fillRect(canvasMinX, canvasMinY, canvasMaxX - canvasMinX, canvasMaxY - canvasMinY);
        
        // 边框
        this.ctx.globalAlpha = 1;
        this.ctx.strokeStyle = color;
        this.ctx.lineWidth = 2;
        this.ctx.strokeRect(canvasMinX, canvasMinY, canvasMaxX - canvasMinX, canvasMaxY - canvasMinY);
    }
    
    drawBeacon() {
        if (this.beaconX === null || this.beaconY === null || !this.mapInfo) {
            return;
        }
        
        const pos = this.worldToCanvas(this.beaconX, this.beaconY);
        
        // 外圆
        this.ctx.fillStyle = 'rgba(255, 0, 0, 0.3)';
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, 20, 0, Math.PI * 2);
        this.ctx.fill();
        
        // 中心点
        this.ctx.fillStyle = '#ff0000';
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, 6, 0, Math.PI * 2);
        this.ctx.fill();
        
        // 标签
        this.ctx.fillStyle = '#ff0000';
        this.ctx.font = 'bold 12px Arial';
        this.ctx.fillText('Beacon', pos.x + 10, pos.y - 10);
    }
    
    updateBeaconGlobe(x, y) {
        this.beaconGlobeX = x;
        this.beaconGlobeY = y;
    }
    
    drawBeaconGlobe() {
        if (this.beaconGlobeX === null || this.beaconGlobeY === null || !this.mapInfo) {
            return;
        }
        
        const pos = this.worldToCanvas(this.beaconGlobeX, this.beaconGlobeY);
        
        // 红色填充圆点
        this.ctx.fillStyle = '#ff0000';
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, 8, 0, Math.PI * 2);
        this.ctx.fill();
        
        // 深红色边框
        this.ctx.strokeStyle = '#cc0000';
        this.ctx.lineWidth = 2;
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, 8, 0, Math.PI * 2);
        this.ctx.stroke();
        
        // 标签
        this.ctx.fillStyle = '#cc0000';
        this.ctx.font = 'bold 11px Arial';
        this.ctx.fillText('Beacon(Globe)', pos.x + 12, pos.y - 12);
    }
    
    drawRobot() {
        if (this.robotX === null || this.robotY === null || !this.mapInfo) {
            return;
        }
        
        const pos = this.worldToCanvas(this.robotX, this.robotY);
        const arrowLength = 20;  // 箭头长度
        const arrowWidth = 8;    // 箭头宽度
        
        // 外圆
        this.ctx.fillStyle = 'rgba(0, 150, 255, 0.3)';
        this.ctx.beginPath();
        this.ctx.arc(pos.x, pos.y, 15, 0, Math.PI * 2);
        this.ctx.fill();
        
        // 绘制箭头（表示朝向）
        // yaw=0 时指向X轴正方向（右侧）
        // yaw 按逆时针为正方向旋转
        this.ctx.save();
        this.ctx.translate(pos.x, pos.y);
        this.ctx.rotate(-this.robotYaw);
        
        // 箭头主体（矩形）- 初始向右
        this.ctx.fillStyle = '#0096ff';
        this.ctx.fillRect(0, -arrowWidth / 2, arrowLength, arrowWidth);
        
        // 箭头头部（三角形）
        this.ctx.beginPath();
        this.ctx.moveTo(arrowLength, 0);           // 箭头尖端
        this.ctx.lineTo(arrowLength - 8, -arrowWidth); // 上边
        this.ctx.lineTo(arrowLength - 8, arrowWidth);  // 下边
        this.ctx.closePath();
        this.ctx.fillStyle = '#0096ff';
        this.ctx.fill();
        
        // 中心点
        this.ctx.fillStyle = '#ffffff';
        this.ctx.beginPath();
        this.ctx.arc(0, 0, 4, 0, Math.PI * 2);
        this.ctx.fill();
        
        this.ctx.restore();
        
        // 标签
        this.ctx.fillStyle = '#0096ff';
        this.ctx.font = 'bold 12px Arial';
        this.ctx.fillText('Robot', pos.x + 20, pos.y - 10);
    }
    
    // ==================== 区域管理 ====================
    
    toggleDrawMode(enabled) {
        this.drawMode = enabled;
        this.canvas.style.cursor = enabled ? 'crosshair' : 'grab';
        console.log(this.drawMode ? '✏️ 区域绘制模式启用' : '🖱️ 平移模式启用');
    }
    
    clearZones() {
        this.zones = [];
        this.updateZonesDisplay();
        this.render();
        console.log('✓ 所有区域已清除');
    }
    
    updateZonesDisplay() {
        document.getElementById('zoneCount').textContent = this.zones.length;
        const zonesList = document.getElementById('zonesList');
        
        if (this.zones.length === 0) {
            zonesList.textContent = '无';
        } else {
            zonesList.innerHTML = this.zones.map((z, i) => 
                `<div>区域 ${i + 1}: (${z.x1.toFixed(1)}, ${z.y1.toFixed(1)}) → (${z.x2.toFixed(1)}, ${z.y2.toFixed(1)})</div>`
            ).join('');
        }
    }
    
    getZones() {
        return this.zones;
    }
    
    // ==================== 数据更新 ====================
    
    updateBeacon(x, y, yaw) {
        this.beaconX = x;
        this.beaconY = y;
        this.render();
    }
    
    updateRobot(x, y, yaw = 0) {
        this.robotX = x;
        this.robotY = y;
        this.robotYaw = yaw;
        
        // 调试：yaw 角与坐标轴的关系（右手坐标系，Z轴朝顶）
        // 当前实现: rotate(-yaw)
        // yaw=0 时，指向 X 轴正方向（右）
        // yaw=π/2 时（逆时针90度），指向 Y 轴正方向（下）
        // yaw=-π/2 时（顺时针90度），指向 Y 轴负方向（上）
        const yawDeg = (yaw * 180 / Math.PI).toFixed(1);
        console.log(`🤖 机器人: (${x.toFixed(2)}, ${y.toFixed(2)}), yaw=${yaw.toFixed(3)} rad (${yawDeg}°)`);
        
        this.render();
    }
}

// ==================== 应用初始化 ====================

const mapViewer = new MapViewer('mapCanvas');

// 按钮事件绑定
document.getElementById('btnStart').addEventListener('click', async () => {
    try {
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ port: '/dev/ttyUSB0' })
        });
        const data = await response.json();
        console.log('✓ 系统已启动', data);
        systemRunning = true;
        document.getElementById('btnStart').disabled = true;
        document.getElementById('btnStop').disabled = false;
    } catch (error) {
        console.error('✗ 启动失败:', error);
        alert('启动系统失败: ' + error.message);
    }
});

document.getElementById('btnStop').addEventListener('click', async () => {
    try {
        const response = await fetch('/api/stop', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        console.log('✓ 系统已停止', data);
        systemRunning = false;
        document.getElementById('btnStart').disabled = false;
        document.getElementById('btnStop').disabled = true;
    } catch (error) {
        console.error('✗ 停止失败:', error);
        alert('停止系统失败: ' + error.message);
    }
});

document.getElementById('btnLoadMap').addEventListener('click', () => {
    mapViewer.loadMap();
});

document.getElementById('btnClearMap').addEventListener('click', () => {
    mapViewer.clearMap();
});

document.getElementById('btnDrawZone').addEventListener('click', (e) => {
    const btn = e.target.closest('.btn');
    if (mapViewer.drawMode) {
        mapViewer.toggleDrawMode(false);
        btn.classList.remove('active');
    } else {
        if (!mapViewer.mapInfo) {
            alert('请先加载地图');
            return;
        }
        mapViewer.toggleDrawMode(true);
        btn.classList.add('active');
    }
});

document.getElementById('btnClearZones').addEventListener('click', () => {
    mapViewer.clearZones();
});

// 启动/停止系统控制
let systemRunning = false;

async function autoStartSystem() {
    try {
        const response = await fetch('/api/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ port: '/dev/ttyUSB0' })
        });
        const data = await response.json();
        console.log('✓ 系统已自动启动');
        systemRunning = true;
        updateStatus();
    } catch (error) {
        console.error('✗ 自动启动失败:', error);
    }
}

// ==================== 实时数据更新 ====================

async function updatePositionData() {
    if (!systemRunning || !mapViewer.mapInfo) {
        return;
    }
    
    try {
        // 获取 Beacon 位置（相对坐标）
        const posResponse = await fetch('/api/position');
        if (posResponse.ok) {
            const pos = await posResponse.json();
            
            // 调试日志
            console.log('Beacon 数据:', pos);
            
            // 更新显示（Beacon是相对坐标，不是全局坐标）
            const beaconX = pos.beacon_filter_x || 0;
            const beaconY = pos.beacon_filter_y || 0;
            const confidence = pos.confidence || 0;
            const distance = pos.distance || 0;
            const angle = pos.angle || 0;
            
            document.getElementById('beaconX').textContent = Number(beaconX).toFixed(2);
            document.getElementById('beaconY').textContent = Number(beaconY).toFixed(2);
            document.getElementById('beaconYaw').textContent = '─';  // Beacon无方向
            document.getElementById('beaconConf').textContent = (Number(confidence) * 100).toFixed(1) + '%';
            document.getElementById('beaconDist').textContent = Number(distance).toFixed(2);
            document.getElementById('beaconAngle').textContent = Number(angle).toFixed(1);
            
            if (pos.initialized && pos.status === 'active') {
                document.getElementById('beaconStatus').textContent = '✓ 已检测';
            } else {
                document.getElementById('beaconStatus').textContent = '✗ 未检测';
            }
            
            // 更新地图显示（使用相对坐标）
            mapViewer.updateBeacon(Number(beaconX), Number(beaconY), 0);
        }
        
        // 获取机器人位置
        const robotResponse = await fetch('/api/robot-pose');
        if (robotResponse.ok) {
            const robot = await robotResponse.json();
            
            console.log('机器人数据:', robot);
            
            const robotX = robot.x || 0;
            const robotY = robot.y || 0;
            const robotYaw = robot.yaw || 0;
            
            document.getElementById('robotX').textContent = Number(robotX).toFixed(2);
            document.getElementById('robotY').textContent = Number(robotY).toFixed(2);
            document.getElementById('robotYaw').textContent = Number(robotYaw).toFixed(3);
            document.getElementById('robotStatus').textContent = '✓ 在线';
            
            mapViewer.updateRobot(Number(robotX), Number(robotY), Number(robotYaw));
            
            // 更新 Beacon 全局坐标
            if (robot.beacon_globe) {
                const beaconGlobeX = robot.beacon_globe.x || 0;
                const beaconGlobeY = robot.beacon_globe.y || 0;
                mapViewer.updateBeaconGlobe(Number(beaconGlobeX), Number(beaconGlobeY));
                console.log('Beacon Globe:', { x: beaconGlobeX, y: beaconGlobeY });
            }
        }
    } catch (error) {
        console.error('✗ 数据更新失败:', error);
    }
}

async function updateStatus() {
    try {
        const response = await fetch('/api/status');
        const status = await response.json();
        
        const statusDot = document.querySelector('.status-dot');
        const statusText = document.getElementById('statusText');
        
        if (status.is_running && status.reader_connected) {
            statusDot.className = 'status-dot online';
            statusText.textContent = '在线';
        } else {
            statusDot.className = 'status-dot offline';
            statusText.textContent = '离线';
        }
    } catch (error) {
        console.error('✗ 状态更新失败:', error);
    }
}

// 页面初始化时自动加载地图和启动系统
async function initializeMap() {
    try {
        await mapViewer.loadMap();
        console.log('✓ 地图自动加载成功');
        
        // 自动启动系统
        setTimeout(() => {
            autoStartSystem();
        }, 500);
    } catch (error) {
        console.warn('⚠ 地图自动加载失败:', error);
    }
}

// 等待页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initializeMap);
} else {
    initializeMap();
}

// 定期更新数据
setInterval(updatePositionData, 100);  // 10Hz 更新频率
setInterval(updateStatus, 1000);  // 1Hz 更新状态
setInterval(async () => {
    // 定期保存检测区域到服务器
    if (mapViewer.zones.length > 0) {
        try {
            await fetch('/api/zones', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ zones: mapViewer.zones })
            });
        } catch (error) {
            console.error('✗ 保存区域失败:', error);
        }
    }
}, 5000);  // 5秒保存一次

console.log('✓ 应用初始化完成');
