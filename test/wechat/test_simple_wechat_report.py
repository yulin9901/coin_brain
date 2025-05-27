#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
测试简化版微信报告功能
"""
import os
import sys
import datetime

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.utils import load_config, get_db_config
from app.reporting.simple_daily_report import SimpleDailyReportGenerator
from app.reporting.wechat_reporter import WeChatReporter

def test_simple_wechat_report():
    """测试简化版微信报告"""
    print("🤖 测试简化版微信报告功能")
    print("=" * 50)
    
    try:
        # 加载配置
        config = load_config()
        db_config = get_db_config(config)
        
        # 初始化组件
        report_generator = SimpleDailyReportGenerator(config, db_config)
        wechat_reporter = WeChatReporter(config)
        
        print("✅ 配置加载成功")
        
        # 生成简化报告
        print("\n📊 生成简化报告...")
        report_data = report_generator.generate_simple_report()
        
        print("生成的报告数据:")
        import json
        print(json.dumps(report_data, indent=2, ensure_ascii=False, default=str))
        
        # 发送微信报告
        print("\n📱 发送微信报告...")
        success = wechat_reporter.send_simple_daily_report(report_data)
        
        if success:
            print("✅ 简化版微信报告发送成功！")
            print("请检查您的微信是否收到了报告")
        else:
            print("❌ 简化版微信报告发送失败")
            
        return success
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_manual_simple_report():
    """测试手动创建的简化报告"""
    print("\n🔧 测试手动创建的简化报告")
    print("=" * 50)
    
    try:
        config = load_config()
        wechat_reporter = WeChatReporter(config)
        
        # 手动创建简化报告数据
        today = datetime.date.today().strftime('%Y-%m-%d')
        report_data = {
            'date': today,
            'generated_at': datetime.datetime.now().isoformat(),
            'system_status': {
                'database': '正常',
                'config': '正常',
                'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            },
            'market_summary': {
                'status': '数据已收集',
                'data_points': 20,
                'overall_trend': 'neutral'
            },
            'news_summary': {
                'total_news': 5,
                'positive_news': 2,
                'negative_news': 1,
                'hot_topics': [
                    {
                        'title': 'Bitcoin价格突破新高',
                        'source': 'CryptoPanic',
                        'sentiment': 'positive'
                    },
                    {
                        'title': '以太坊网络升级完成',
                        'source': 'CoinDesk',
                        'sentiment': 'positive'
                    }
                ]
            }
        }
        
        print("手动创建的报告数据:")
        import json
        print(json.dumps(report_data, indent=2, ensure_ascii=False, default=str))
        
        # 发送微信报告
        print("\n📱 发送手动创建的微信报告...")
        success = wechat_reporter.send_simple_daily_report(report_data)
        
        if success:
            print("✅ 手动创建的微信报告发送成功！")
        else:
            print("❌ 手动创建的微信报告发送失败")
            
        return success
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("🚀 开始测试简化版微信报告功能")
    print("=" * 60)
    
    # 测试1: 从数据库生成简化报告
    success1 = test_simple_wechat_report()
    
    # 测试2: 手动创建简化报告
    success2 = test_manual_simple_report()
    
    print("\n" + "=" * 60)
    print("📋 测试结果总结:")
    print(f"  数据库简化报告: {'✅ 成功' if success1 else '❌ 失败'}")
    print(f"  手动简化报告: {'✅ 成功' if success2 else '❌ 失败'}")
    
    if success1 or success2:
        print("\n🎉 至少有一个测试成功，简化版微信报告功能可用！")
    else:
        print("\n😞 所有测试都失败了，请检查配置和网络连接")

if __name__ == "__main__":
    main()
