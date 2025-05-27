#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
检查微信推送状态
"""
import os
import sys
import json

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.utils import load_config
from app.reporting.wechat_reporter import WeChatReporter
from app.reporting.wechat_limit_manager import WeChatLimitManager

def check_wechat_status():
    """检查微信推送状态"""
    print("🔍 检查微信推送状态")
    print("=" * 50)
    
    try:
        # 加载配置
        config = load_config()
        
        # 检查配置
        print("📋 配置检查:")
        print(f"  ENABLE_WECHAT_REPORT: {getattr(config, 'ENABLE_WECHAT_REPORT', False)}")
        print(f"  SERVERCHAN_SENDKEY: {'✅ 已设置' if getattr(config, 'SERVERCHAN_SENDKEY', '') else '❌ 未设置'}")
        print(f"  DAILY_REPORT_TIME: {getattr(config, 'DAILY_REPORT_TIME', '未设置')}")
        print(f"  WECHAT_DAILY_LIMIT: {getattr(config, 'WECHAT_DAILY_LIMIT', 1)}")
        print(f"  WECHAT_PRIORITY_ONLY: {getattr(config, 'WECHAT_PRIORITY_ONLY', True)}")
        
        # 初始化组件
        reporter = WeChatReporter(config)
        limit_manager = WeChatLimitManager(config)
        
        # 检查发送状态
        print("\n📊 今日发送状态:")
        status = reporter.get_send_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
        # 检查是否可以发送
        print("\n🚦 发送权限检查:")
        can_send_normal = limit_manager.can_send_message("normal")
        can_send_daily = limit_manager.can_send_message("daily_report")
        can_send_urgent = limit_manager.can_send_message("urgent")
        
        print(f"  普通消息: {'✅ 可发送' if can_send_normal else '❌ 不可发送'}")
        print(f"  每日报告: {'✅ 可发送' if can_send_daily else '❌ 不可发送'}")
        print(f"  紧急消息: {'✅ 可发送' if can_send_urgent else '❌ 不可发送'}")
        
        # 给出建议
        print("\n💡 建议:")
        if status['remaining'] == 0:
            print("  ⚠️  今日发送限制已用完，明天重置")
            print("  💰 考虑升级到Server酱付费版以获得更多发送次数")
        elif status['remaining'] == 1:
            print("  ⚠️  今日还剩1次发送机会，请谨慎使用")
        else:
            print(f"  ✅ 今日还剩 {status['remaining']} 次发送机会")
        
        if getattr(config, 'WECHAT_PRIORITY_ONLY', True):
            print("  📋 当前启用优先级模式，只发送每日报告")
        
        return True
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def reset_daily_limit():
    """重置今日发送限制（管理员功能）"""
    print("\n🔄 重置今日发送限制")
    print("=" * 50)
    
    try:
        config = load_config()
        limit_manager = WeChatLimitManager(config)
        
        # 显示当前状态
        print("重置前状态:")
        status = limit_manager.get_today_status()
        print(json.dumps(status, indent=2, ensure_ascii=False))
        
        # 确认重置
        confirm = input("\n确定要重置今日发送限制吗？(y/N): ")
        if confirm.lower() == 'y':
            limit_manager.reset_today_limit()
            print("✅ 今日发送限制已重置")
            
            # 显示重置后状态
            print("\n重置后状态:")
            status = limit_manager.get_today_status()
            print(json.dumps(status, indent=2, ensure_ascii=False))
        else:
            print("❌ 取消重置操作")
            
    except Exception as e:
        print(f"❌ 重置失败: {e}")

def main():
    """主函数"""
    print("🤖 微信推送状态检查工具")
    print("=" * 60)
    
    # 检查状态
    check_wechat_status()
    
    # 询问是否需要重置限制
    print("\n" + "=" * 60)
    reset_choice = input("是否需要重置今日发送限制？(y/N): ")
    if reset_choice.lower() == 'y':
        reset_daily_limit()

if __name__ == "__main__":
    main()
