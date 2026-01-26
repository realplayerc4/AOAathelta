"""
离线测试：角度突变剔除 + 距离/角度卡尔曼滤波
不依赖串口与 PyQt6，直接构造观测序列进行验证。
"""
import math
import time
import os
import sys

# Ensure project root on sys.path
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from workers.aoa_kalman_filter import MultiTargetKalmanFilter


class FakeFilter:
    def __init__(self, angle_jump_threshold_deg=60.0, stale_reset_sec=0.8):
        self.angle_jump_threshold_deg = angle_jump_threshold_deg
        self.stale_reset_sec = stale_reset_sec
        self._last_measurements = {}
        self.kalman = MultiTargetKalmanFilter(
            process_noise=0.1,
            measurement_noise=0.5,
            prediction_horizon=0.5,
            min_confidence=0.3,
            target_lost_timeout=2.0,
        )
        self.dropped = 0

    def _is_outlier(self, tag_id: int, distance_m: float, angle_deg: float, ts: float) -> bool:
        last = self._last_measurements.get(tag_id)
        if not last:
            return False
        dt = ts - last['ts']
        if dt >= self.stale_reset_sec:
            return False
        delta = angle_deg - last['angle']
        while delta > 180.0:
            delta -= 360.0
        while delta < -180.0:
            delta += 360.0
        return abs(delta) > self.angle_jump_threshold_deg

    def process(self, tag_id: int, distance_m: float, angle_deg: float, ts: float):
        if self._is_outlier(tag_id, distance_m, angle_deg, ts):
            self.dropped += 1
            print(f"drop=> t={ts:.2f} angle={angle_deg:.1f} dist={distance_m:.2f}")
            return None
        x, y, info = self.kalman.filter_measurement(tag_id, distance_m, angle_deg, ts)
        self._last_measurements[tag_id] = {"angle": angle_deg, "distance": distance_m, "ts": ts}
        print(
            f"keep=> t={ts:.2f} angle={angle_deg:.1f} dist={distance_m:.2f} | x={x:.3f} y={y:.3f} conf={info.get('confidence',0.0):.2f}"
        )
        return x, y, info


if __name__ == "__main__":
    f = FakeFilter(angle_jump_threshold_deg=60.0, stale_reset_sec=0.8)
    tag = 1
    t0 = time.time()

    # 生成序列：稳定 -> 大幅逆转（应被剔除） -> 稳定 -> 轻微变化（保留）
    seq = []
    # 稳定 10 帧
    for i in range(10):
        seq.append((5.0, 30.0, t0 + i * 0.1))
    # 注入异常角度逆转（-150°），紧邻上一帧，应该剔除
    seq.append((5.0, -150.0, t0 + 10 * 0.1))
    # 恢复稳定若干帧
    for i in range(11, 16):
        seq.append((5.0, 32.0, t0 + i * 0.1))
    # 观测间隔过长，重置连续性，然后大的变化也允许（举例）
    seq.append((5.5, -170.0, t0 + 5.0))
    # 轻微变化保留
    seq.append((5.6, -160.0, t0 + 5.2))

    for dist, ang, ts in seq:
        f.process(tag, dist, ang, ts)

    print(f"summary=> dropped={f.dropped}")
