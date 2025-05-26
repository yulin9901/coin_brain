#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
交易模块使用示例
演示如何使用交易执行、价格监控和仓位管理功能
"""
import os
import sys
import time
import logging

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.utils import load_config, get_db_config
from app.trading import TradingManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('trading_example')

def main():
    """主函数"""
    print("=== 交易模块使用示例 ===\n")

    try:
        # 1. 初始化交易管理器
        print("1. 初始化交易管理器...")
        config = load_config()
        db_config = get_db_config(config)

        trading_manager = TradingManager(config, db_config)
        print("✓ 交易管理器初始化成功\n")

        # 2. 获取投资组合状态
        print("2. 获取投资组合状态...")
        portfolio_status = trading_manager.get_portfolio_status()

        if 'error' not in portfolio_status:
            summary = portfolio_status['portfolio_summary']
            print(f"✓ 投资组合状态:")
            print(f"   开放仓位数量: {summary.get('open_positions', 0)}")
            print(f"   总保证金使用: {summary.get('total_margin_used', 0):.2f} USDT")
            print(f"   总未实现盈亏: {summary.get('total_unrealized_pnl', 0):.2f} USDT")
            print(f"   今日已实现盈亏: {summary.get('daily_realized_pnl', 0):.2f} USDT")

            # 显示余额信息
            balances = summary.get('balances', {})
            if balances:
                print(f"   账户余额:")
                for asset, balance in balances.items():
                    print(f"     {asset}: {balance:.2f}")
        else:
            print(f"✗ 获取投资组合状态失败: {portfolio_status['error']}")

        print()

        # 3. 仓位大小计算示例
        print("3. 仓位大小计算示例...")
        position_calc = trading_manager.position_manager.calculate_position_size(
            trading_pair='BTCUSDT',
            entry_price=50000.0,
            risk_percentage=2.0,
            stop_loss_price=48000.0
        )

        if 'error' not in position_calc:
            print(f"✓ 仓位大小计算结果:")
            print(f"   交易对: BTCUSDT")
            print(f"   入场价格: {position_calc['entry_price']:.2f} USDT")
            print(f"   建议数量: {position_calc['quantity']:.6f} BTC")
            print(f"   总价值: {position_calc['total_value']:.2f} USDT")
            print(f"   风险金额: {position_calc['risk_amount']:.2f} USDT")
            print(f"   风险百分比: {position_calc['risk_percentage']:.1f}%")
        else:
            print(f"✗ 仓位大小计算失败: {position_calc['error']}")

        print()

        # 4. 模拟策略执行
        print("4. 模拟策略执行...")
        test_strategy = {
            'id': 999,
            'trading_pair': 'BTCUSDT',
            'position_type': 'LONG',
            'entry_price_suggestion': 50000.0,
            'stop_loss_price': 48000.0,
            'take_profit_price': 52000.0,
            'position_size_percentage': 2.0,
            'leverage': 1.0
        }

        result = trading_manager.execute_strategy(test_strategy)
        print(f"✓ 策略执行结果: {result['status']}")
        print(f"   消息: {result['message']}")

        if result['status'] == 'simulated' and 'position_calc' in result:
            calc = result['position_calc']
            print(f"   模拟交易详情:")
            print(f"     数量: {calc['quantity']:.6f} BTC")
            print(f"     价值: {calc['total_value']:.2f} USDT")

        print()

        # 5. 价格监控演示
        print("5. 价格监控演示...")

        # 从配置文件获取高优先级交易对用于监控
        monitor_pairs = getattr(config, 'HIGH_PRIORITY_PAIRS', ['BTCUSDT', 'ETHUSDT'])
        print(f"   启动价格监控: {monitor_pairs}")
        trading_manager.start_monitoring(monitor_pairs)

        print("   等待价格数据...")
        time.sleep(10)  # 等待10秒接收价格数据

        current_prices = trading_manager.get_current_prices()
        if current_prices:
            print("✓ 实时价格数据:")
            for symbol, price in current_prices.items():
                print(f"     {symbol}: {price:.2f} USDT")
        else:
            print("⚠ 暂未接收到价格数据")

        print("   停止价格监控...")
        trading_manager.stop_monitoring()
        print("✓ 价格监控已停止")

        print()

        # 6. 获取交易历史
        print("6. 获取交易历史...")
        trading_history = trading_manager.get_trading_history(days=7)
        print(f"✓ 最近7天交易历史: {len(trading_history)}条记录")

        if trading_history:
            print("   最近的交易记录:")
            for i, trade in enumerate(trading_history[:3]):  # 只显示前3条
                print(f"     {i+1}. {trade['trading_pair']} - {trade['position_type']} - {trade['status']}")
                print(f"        开仓时间: {trade['open_time']}")
                if trade['unrealized_pnl']:
                    print(f"        盈亏: {float(trade['unrealized_pnl']):.2f} USDT")

        print()

        # 7. 显示配置信息
        print("7. 当前配置信息...")
        print(f"✓ 配置状态:")
        print(f"   自动交易: {'启用' if getattr(config, 'ENABLE_AUTO_TRADING', False) else '禁用'}")
        print(f"   测试网络: {'是' if getattr(config, 'BINANCE_TESTNET', True) else '否'}")
        print(f"   价格监控: {'启用' if getattr(config, 'ENABLE_PRICE_MONITORING', True) else '禁用'}")
        print(f"   默认风险百分比: {getattr(config, 'DEFAULT_RISK_PERCENTAGE', 2.0):.1f}%")
        print(f"   最大开放仓位: {getattr(config, 'MAX_OPEN_POSITIONS', 5)}")

        # 显示交易对配置
        trading_pairs = getattr(config, 'TRADING_PAIRS', [])
        high_priority_pairs = getattr(config, 'HIGH_PRIORITY_PAIRS', [])
        print(f"   配置的交易对: {len(trading_pairs)}个")
        print(f"   高优先级交易对: {high_priority_pairs}")
        if len(trading_pairs) > len(high_priority_pairs):
            print(f"   其他交易对: {[pair for pair in trading_pairs if pair not in high_priority_pairs]}")

        print("\n=== 示例完成 ===")

        # 安全提醒
        print("\n⚠️  重要提醒:")
        print("   1. 这是一个演示示例，实际使用前请仔细配置")
        print("   2. 确保在测试网络上进行测试")
        print("   3. 设置合理的风险管理参数")
        print("   4. 定期监控系统运行状态")

    except Exception as e:
        logger.error(f"示例执行失败: {e}")
        print(f"\n✗ 示例执行失败: {e}")
        print("\n请检查:")
        print("   1. 配置文件是否正确设置")
        print("   2. 数据库连接是否正常")
        print("   3. Binance API密钥是否有效")

if __name__ == "__main__":
    main()
