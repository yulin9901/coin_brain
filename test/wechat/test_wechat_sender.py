#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
微信发送功能测试脚本
用于测试Server酱微信推送功能是否正常工作
"""
import os
import sys
import datetime
import logging

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.utils import load_config, get_db_config
from app.reporting.wechat_reporter import WeChatReporter
from app.reporting.daily_report_generator import DailyReportGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('wechat_test')

def test_simple_message():
    """测试发送简单消息"""
    print("=" * 50)
    print("测试1: 发送简单测试消息")
    print("=" * 50)
    
    try:
        config = load_config()
        reporter = WeChatReporter(config)
        
        # 检查配置
        if not reporter.enabled:
            print("❌ 微信推送功能未启用或配置不正确")
            print("请检查以下配置项：")
            print(f"  - ENABLE_WECHAT_REPORT: {getattr(config, 'ENABLE_WECHAT_REPORT', 'Not Set')}")
            print(f"  - SERVERCHAN_SENDKEY: {getattr(config, 'SERVERCHAN_SENDKEY', 'Not Set')}")
            return False
        
        # 发送测试消息
        title = "CoinBrain测试消息"
        content = f"""
## 🧪 系统测试

**测试时间**: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

**测试内容**: 微信推送功能测试

**状态**: ✅ 如果您收到这条消息，说明微信推送功能配置正确！

---
*这是一条自动生成的测试消息*
        """
        
        success = reporter.send_message(title, content)
        
        if success:
            print("✅ 测试消息发送成功！")
            print("请检查您的微信是否收到了测试消息")
            return True
        else:
            print("❌ 测试消息发送失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

def test_daily_report():
    """测试发送每日报告"""
    print("\n" + "=" * 50)
    print("测试2: 发送每日报告")
    print("=" * 50)
    
    try:
        config = load_config()
        db_config = get_db_config(config)
        
        reporter = WeChatReporter(config)
        generator = DailyReportGenerator(config, db_config)
        
        if not reporter.enabled:
            print("❌ 微信推送功能未启用")
            return False
        
        print("正在生成报告数据...")
        
        # 生成测试报告数据
        test_report_data = {
            'date': datetime.date.today().strftime('%Y-%m-%d'),
            'market_summary': {
                'overall_trend': 'bullish',
                'total_market_cap': 1500000000000,
                'btc_dominance': 42.5,
                'positive_coins': 8,
                'total_coins': 10
            },
            'top_performers': {
                'gainers': [
                    {'symbol': 'BTCUSDT', 'change_24h': 5.2, 'current_price': 45000},
                    {'symbol': 'ETHUSDT', 'change_24h': 3.8, 'current_price': 3200},
                    {'symbol': 'SOLUSDT', 'change_24h': 7.1, 'current_price': 120}
                ],
                'losers': [
                    {'symbol': 'DOGEUSDT', 'change_24h': -2.1, 'current_price': 0.08}
                ]
            },
            'trading_strategy': {
                'recommendations': [
                    {
                        'symbol': 'BTCUSDT',
                        'action': 'BUY',
                        'confidence_score': 0.85,
                        'reasoning': '技术指标显示强势突破'
                    },
                    {
                        'symbol': 'ETHUSDT', 
                        'action': 'HOLD',
                        'confidence_score': 0.75,
                        'reasoning': '等待进一步确认'
                    }
                ],
                'risk_level': '中等风险',
                'average_confidence': 0.8
            },
            'profit_loss': {
                'realized_pnl': 150.50,
                'unrealized_pnl': 75.25,
                'total_fees': 12.30,
                'portfolio_value': 5000.00
            },
            'news_summary': {
                'hot_topics': [
                    {
                        'title': '比特币突破新高',
                        'summary': '比特币价格创下历史新高，市场情绪乐观...'
                    },
                    {
                        'title': '以太坊升级进展',
                        'summary': '以太坊网络升级顺利进行，交易费用下降...'
                    }
                ],
                'market_sentiment': '积极'
            }
        }
        
        print("正在发送报告...")
        success = reporter.send_daily_report(test_report_data)
        
        if success:
            print("✅ 每日报告发送成功！")
            print("请检查您的微信是否收到了完整的每日报告")
            return True
        else:
            print("❌ 每日报告发送失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

def test_real_daily_report():
    """测试发送真实的每日报告（从数据库获取数据）"""
    print("\n" + "=" * 50)
    print("测试3: 发送真实每日报告（从数据库）")
    print("=" * 50)
    
    try:
        config = load_config()
        db_config = get_db_config(config)
        
        reporter = WeChatReporter(config)
        generator = DailyReportGenerator(config, db_config)
        
        if not reporter.enabled:
            print("❌ 微信推送功能未启用")
            return False
        
        print("正在从数据库生成报告数据...")
        
        # 生成真实报告数据
        report_data = generator.generate_daily_report()
        
        if not report_data or 'date' not in report_data:
            print("⚠️  无法生成报告数据，可能是数据库中没有数据")
            print("建议先运行数据收集任务")
            return False
        
        print("正在发送真实报告...")
        success = reporter.send_daily_report(report_data)
        
        if success:
            print("✅ 真实每日报告发送成功！")
            print("请检查您的微信是否收到了基于真实数据的报告")
            return True
        else:
            print("❌ 真实每日报告发送失败")
            return False
            
    except Exception as e:
        print(f"❌ 测试过程中出错: {e}")
        return False

def check_configuration():
    """检查配置是否正确"""
    print("=" * 50)
    print("配置检查")
    print("=" * 50)
    
    try:
        config = load_config()
        
        print("当前配置状态：")
        print(f"  ENABLE_WECHAT_REPORT: {getattr(config, 'ENABLE_WECHAT_REPORT', '❌ 未设置')}")
        print(f"  SERVERCHAN_SENDKEY: {'✅ 已设置' if getattr(config, 'SERVERCHAN_SENDKEY', '') and getattr(config, 'SERVERCHAN_SENDKEY') != 'YOUR_SERVERCHAN_SENDKEY_HERE' else '❌ 未设置或使用默认值'}")
        print(f"  DAILY_REPORT_TIME: {getattr(config, 'DAILY_REPORT_TIME', '❌ 未设置')}")
        print(f"  WECHAT_REPORT_TITLE: {getattr(config, 'WECHAT_REPORT_TITLE', '❌ 未设置')}")
        
        if not getattr(config, 'ENABLE_WECHAT_REPORT', False):
            print("\n⚠️  微信报告功能已禁用")
            
        if not getattr(config, 'SERVERCHAN_SENDKEY', '') or getattr(config, 'SERVERCHAN_SENDKEY') == 'YOUR_SERVERCHAN_SENDKEY_HERE':
            print("\n❌ Server酱SendKey未正确配置")
            print("请按以下步骤配置：")
            print("1. 访问 https://sct.ftqq.com/")
            print("2. 注册账号并关注微信公众号")
            print("3. 获取SendKey")
            print("4. 在config/config.py中设置SERVERCHAN_SENDKEY")
            return False
        
        print("\n✅ 配置检查通过")
        return True
        
    except Exception as e:
        print(f"❌ 配置检查失败: {e}")
        return False

def main():
    """主函数"""
    print("🤖 CoinBrain微信推送功能测试")
    print("=" * 50)
    
    # 检查配置
    if not check_configuration():
        print("\n❌ 配置检查失败，请先正确配置后再测试")
        return
    
    # 运行测试
    tests = [
        ("简单消息测试", test_simple_message),
        ("模拟报告测试", test_daily_report),
        ("真实报告测试", test_real_daily_report)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name}执行失败: {e}")
            results.append((test_name, False))
    
    # 显示测试结果
    print("\n" + "=" * 50)
    print("测试结果汇总")
    print("=" * 50)
    
    for test_name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{test_name}: {status}")
    
    success_count = sum(1 for _, result in results if result)
    total_count = len(results)
    
    print(f"\n总计: {success_count}/{total_count} 个测试通过")
    
    if success_count == total_count:
        print("🎉 所有测试通过！微信推送功能工作正常")
    else:
        print("⚠️  部分测试失败，请检查配置和网络连接")

if __name__ == "__main__":
    main()
