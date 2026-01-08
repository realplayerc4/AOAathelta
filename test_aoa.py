#!/usr/bin/env python3
"""
AOA 功能测试脚本 - 测试数据模型和协议解析
"""

import sys
import logging
from datetime import datetime
from models.aoa_data import AOAFrame, AnchorData, TagData, AOAPosition
from core.aoa_protocol import AOAProtocolParser, SerialProtocolExtractor

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_aoa_data_models():
    """测试 AOA 数据模型"""
    print("\n" + "="*60)
    print("测试 1: AOA 数据模型")
    print("="*60)
    
    # 测试 ANCHER 数据
    anchor = AnchorData(
        role=1,
        anchor_id=10,
        local_time=1234567890,
        system_time=9876543210,
        voltage=3300
    )
    print(f"✓ ANCHER 数据创建成功:")
    print(f"  - ID: {anchor.anchor_id}")
    print(f"  - 电压: {anchor.voltage} mV")
    
    # 测试 TAG 数据
    tag = TagData(
        tag_id=20,
        distance=5000,  # 5000 mm = 5 m
        angle=45.5,
        fp_db=-70,
        rx_db=-80
    )
    print(f"✓ TAG 数据创建成功:")
    print(f"  - ID: {tag.tag_id}")
    print(f"  - 距离: {tag.distance} mm")
    print(f"  - 角度: {tag.angle}°")
    
    # 测试 AOA 位置
    position = AOAPosition(
        anchor_id=anchor.anchor_id,
        tag_id=tag.tag_id,
        distance=tag.distance / 1000.0,  # 转换为米
        angle=tag.angle,
        confidence=0.95
    )
    print(f"✓ AOA 位置创建成功:")
    print(f"  - 相对位置: ({position.distance:.3f}m, {position.angle:.1f}°)")
    print(f"  - 信心度: {position.confidence:.2%}")


def test_aoa_frame_parsing():
    """测试 AOA 帧解析"""
    print("\n" + "="*60)
    print("测试 2: AOA 帧解析")
    print("="*60)
    
    # 创建一个模拟的 33 字节协议数据
    # 协议格式：
    # 字节0: 头部 (0x55)
    # 字节1: 功能码
    # 字节2-3: 数据长度
    # 字节4: ANCHER role
    # 字节5: ANCHER id
    # 字节6-9: 地方时间
    # 字节10-13: 系统时间
    # 字节14-17: 保留
    # 字节18-19: 电压
    # 字节20: 节点数/保留
    # 字节21: TAG role
    # 字节22: TAG id
    # 字节23-25: 距离 (int24)
    # 字节26-27: 角度 (int16)
    # 字节28: fp_db
    # 字节29: rx_db
    # 字节30-31: 保留
    # 字节32: 校验和
    
    # 构造测试数据
    data = bytearray(33)
    data[0] = 0x55  # 头部
    data[1] = 0x00  # 功能码
    data[2] = 0x00
    data[3] = 0x14  # 数据长度 = 20
    data[4] = 0x01  # ANCHER role
    data[5] = 0x0A  # ANCHER id = 10
    data[6] = 0x32  # 地方时间低字节
    data[7] = 0x00
    data[8] = 0x00
    data[9] = 0x00
    data[10] = 0xB2  # 系统时间低字节
    data[11] = 0x0D
    data[12] = 0x00
    data[13] = 0x00
    data[14] = 0x00  # 保留
    data[15] = 0x00
    data[16] = 0x00
    data[17] = 0x00
    data[18] = 0xE4  # 电压 = 3300 (0x0CE4) 小端序
    data[19] = 0x0C
    data[20] = 0x00  # 节点数
    data[21] = 0x02  # TAG role
    data[22] = 0x14  # TAG id = 20
    # 距离 = 5000 (0x1388) 小端序
    data[23] = 0x88
    data[24] = 0x13
    data[25] = 0x00
    # 角度 = 4550 (45.50°) 小端序
    data[26] = 0x86
    data[27] = 0x11
    data[28] = 0xBA  # fp_db = -70 (as signed byte)
    data[29] = 0xB0  # rx_db = -80 (as signed byte)
    data[30] = 0x00  # 保留
    data[31] = 0x00
    
    # 计算校验和（前 32 字节的和）
    checksum = sum(data[:32]) & 0xFF
    data[32] = checksum
    
    print(f"✓ 创建测试数据 (33 字节):")
    print(f"  - 十六进制: {' '.join(f'{b:02X}' for b in data[:10])}...")
    print(f"  - 头部: 0x{data[0]:02X}")
    print(f"  - 校验和: 0x{data[32]:02X}")
    
    # 解析帧
    try:
        frame = AOAFrame.from_bytes(bytes(data), frame_id=1)
        print(f"\n✓ 帧解析成功:")
        print(f"  - 有效性: {'✓' if frame.is_valid else '✗'}")
        print(f"  - ANCHER ID: {frame.anchor_data.anchor_id}")
        print(f"  - TAG ID: {frame.tag_data.tag_id}")
        print(f"  - 距离: {frame.tag_data.distance} mm")
        print(f"  - 角度: {frame.tag_data.angle:.2f}°")
        print(f"  - 摘要: {frame.get_summary()}")
    except Exception as e:
        print(f"✗ 帧解析失败: {e}")
        import traceback
        traceback.print_exc()


def test_protocol_parser():
    """测试协议解析器"""
    print("\n" + "="*60)
    print("测试 3: 协议解析器")
    print("="*60)
    
    parser = AOAProtocolParser()
    
    # 创建多个帧数据流
    frames_data = bytearray()
    
    for frame_num in range(3):
        data = bytearray(33)
        data[0] = 0x55
        data[1] = 0x00
        data[2] = 0x00
        data[3] = 0x14
        data[4] = 0x01
        data[5] = 0x0A + frame_num  # ANCHER id 变化
        data[6:20] = bytes([0x00] * 14)
        data[20] = 0x00
        data[21] = 0x02
        data[22] = 0x14 + frame_num  # TAG id 变化
        data[23] = 0x88
        data[24] = 0x13
        data[25] = 0x00
        data[26] = 0x86
        data[27] = 0x11
        data[28] = 0xBA
        data[29] = 0xB0
        data[30:32] = bytes([0x00, 0x00])
        
        # 计算校验和
        checksum = sum(data[:32]) & 0xFF
        data[32] = checksum
        
        frames_data.extend(data)
    
    print(f"✓ 创建 3 个帧的数据流 ({len(frames_data)} 字节)")
    
    # 解析数据流
    parsed_frames = parser.parse_stream(bytes(frames_data))
    print(f"✓ 解析结果:")
    print(f"  - 解析出的帧数: {len(parsed_frames)}")
    
    for frame in parsed_frames:
        print(f"  - 帧 #{frame.frame_id}: "
              f"ANCHER={frame.anchor_data.anchor_id}, "
              f"TAG={frame.tag_data.tag_id}, "
              f"有效={frame.is_valid}")
    
    # 获取统计信息
    stats = parser.get_statistics()
    print(f"\n✓ 统计信息:")
    print(f"  - 总帧数: {stats['total_frames']}")
    print(f"  - 成功帧: {stats['success_count']}")
    print(f"  - 错误帧: {stats['error_count']}")
    print(f"  - 错误率: {stats['error_rate']:.2f}%")


def test_protocol_extractor():
    """测试串口协议提取器"""
    print("\n" + "="*60)
    print("测试 4: 串口协议提取器")
    print("="*60)
    
    extractor = SerialProtocolExtractor(use_cpp_library=False)
    
    # 创建包含多个帧的数据流
    frames_data = bytearray()
    
    for frame_num in range(5):
        data = bytearray(33)
        data[0] = 0x55
        data[1] = 0x00
        data[2] = 0x00
        data[3] = 0x14
        data[4] = 0x01
        data[5] = frame_num % 4  # ANCHER id
        data[6:20] = bytes([0x00] * 14)
        data[20] = 0x00
        data[21] = 0x02
        data[22] = frame_num % 8  # TAG id
        data[23] = (frame_num * 1000) & 0xFF
        data[24] = ((frame_num * 1000) >> 8) & 0xFF
        data[25] = 0x00
        data[26] = 0x86
        data[27] = 0x11
        data[28] = 0xBA
        data[29] = 0xB0
        data[30:32] = bytes([0x00, 0x00])
        
        checksum = sum(data[:32]) & 0xFF
        data[32] = checksum
        
        frames_data.extend(data)
    
    print(f"✓ 创建包含 5 个帧的数据流")
    
    # 使用提取器解析
    frames = extractor.extract_data(bytes(frames_data))
    print(f"✓ 提取结果:")
    print(f"  - 成功提取的帧数: {len(frames)}")
    
    for frame in frames[:3]:  # 只显示前 3 个
        summary = frame.get_summary()
        print(f"  - 帧 #{summary['frame_id']}: "
              f"距离={summary['distance_mm']}mm, "
              f"角度={summary['angle_degrees']:.1f}°")


def main():
    """主测试函数"""
    print("\n" + "="*60)
    print("AOA 功能集成测试套件")
    print("="*60)
    
    try:
        test_aoa_data_models()
        test_aoa_frame_parsing()
        test_protocol_parser()
        test_protocol_extractor()
        
        print("\n" + "="*60)
        print("✓ 所有测试完成！")
        print("="*60 + "\n")
        
        return 0
    
    except Exception as e:
        print(f"\n✗ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
