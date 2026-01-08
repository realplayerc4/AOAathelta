#!/usr/bin/env python3
"""
集成测试：验证 /tracked_pose 话题消息被正确传递到地图查看器
"""
import sys
import json
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from unittest.mock import Mock, MagicMock, patch
from ui.main_window import MainWindow


def test_tracked_pose_handling():
    """测试 /tracked_pose 话题消息处理"""
    print("=" * 60)
    print("测试 /tracked_pose 话题消息处理")
    print("=" * 60)
    
    # 创建主窗口实例（使用 mock 避免 Qt 显示）
    with patch('ui.main_window.QMainWindow.__init__', return_value=None):
        main_window = MainWindow.__new__(MainWindow)
        
        # 初始化必要的属性
        main_window.status_bar = Mock()
        main_window.map_viewer_dialog = Mock()
        main_window.map_viewer_dialog.isVisible = Mock(return_value=True)
        main_window._append_live_log = Mock()
        main_window.map_receive_count = 0
        
        # 测试数据 1：列表格式位置
        test_case_1 = {
            "pos": [1.5, 2.5],
            "ori": 0.785398  # 45 度
        }
        
        print("\n测试用例 1：列表格式位置")
        print(f"输入数据: {test_case_1}")
        main_window._on_topic_message_ui("/tracked_pose", test_case_1)
        
        # 验证 update_tracked_pose 被调用
        if main_window.map_viewer_dialog.update_tracked_pose.called:
            call_args = main_window.map_viewer_dialog.update_tracked_pose.call_args
            print(f"✓ update_tracked_pose 被调用")
            print(f"  传入参数: {call_args[0][0]}")
            assert call_args[0][0]["pos"] == [1.5, 2.5], "位置数据错误"
            assert call_args[0][0]["ori"] == 0.785398, "朝向数据错误"
            print("✓ 位置和朝向数据正确")
        else:
            print("✗ update_tracked_pose 未被调用！")
            return False
        
        # 重置 mock
        main_window.map_viewer_dialog.reset_mock()
        
        # 测试数据 2：字典格式位置
        test_case_2 = {
            "pos": {"x": 3.0, "y": 4.0},
            "ori": 1.5708  # 90 度
        }
        
        print("\n测试用例 2：字典格式位置")
        print(f"输入数据: {test_case_2}")
        main_window._on_topic_message_ui("/tracked_pose", test_case_2)
        
        if main_window.map_viewer_dialog.update_tracked_pose.called:
            call_args = main_window.map_viewer_dialog.update_tracked_pose.call_args
            print(f"✓ update_tracked_pose 被调用")
            print(f"  传入参数: {call_args[0][0]}")
            assert call_args[0][0]["pos"] == [3.0, 4.0], "位置数据错误"
            assert call_args[0][0]["ori"] == 1.5708, "朝向数据错误"
            print("✓ 位置和朝向数据正确")
        else:
            print("✗ update_tracked_pose 未被调用！")
            return False
        
        # 重置 mock
        main_window.map_viewer_dialog.reset_mock()
        
        # 测试数据 3：无效数据（缺少必要字段）
        test_case_3 = {
            "pos": [1.0, 2.0]
            # 缺少 "ori"
        }
        
        print("\n测试用例 3：无效数据（缺少朝向）")
        print(f"输入数据: {test_case_3}")
        main_window._on_topic_message_ui("/tracked_pose", test_case_3)
        
        if not main_window.map_viewer_dialog.update_tracked_pose.called:
            print("✓ update_tracked_pose 未被调用（符合预期）")
        else:
            print("✗ 不应该处理无效数据")
            return False
        
        # 测试数据 4：地图话题（确保不影响）
        test_map_data = {
            "size": [100, 100],
            "resolution": 0.05,
            "data": "base64encodeddata"
        }
        
        print("\n测试用例 4：/map 话题（确保不被影响）")
        print(f"输入数据: map")
        main_window.map_viewer_dialog.reset_mock()
        main_window._on_topic_message_ui("/map", test_map_data)
        
        # 应该调用 update_map，而不是 update_tracked_pose
        if main_window.map_viewer_dialog.update_map.called:
            print("✓ update_map 被调用")
        else:
            print("✗ update_map 未被调用")
            return False
        
        if not main_window.map_viewer_dialog.update_tracked_pose.called:
            print("✓ update_tracked_pose 未被调用（符合预期）")
        else:
            print("✗ 不应该处理 /map 话题中的追踪位置")
            return False
    
    print("\n" + "=" * 60)
    print("✓ 所有集成测试通过！")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = test_tracked_pose_handling()
    sys.exit(0 if success else 1)
