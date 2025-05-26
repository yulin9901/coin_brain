#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
交易模块测试脚本
"""
import os
import sys
import time
import logging

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.utils import load_config, get_db_config
from app.trading import TradingManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_trading')

def test_trading_manager():
    """测试交易管理器"""
    try:
        # 加载配置
        config = load_config()
        db_config = get_db_config(config)

        print("=== 交易模块测试 ===")

        # 初始化交易管理器
        print("1. 初始化交易管理器...")
        trading_manager = TradingManager(config, db_config)
        print("✓ 交易管理器初始化成功")

        # 测试获取投资组合状态
        print("\n2. 获取投资组合状态...")
        portfolio_status = trading_manager.get_portfolio_status()
        if 'error' not in portfolio_status:
            print("✓ 投资组合状态获取成功")
            print(f"   开放仓位数量: {portfolio_status['portfolio_summary'].get('open_positions', 0)}")
            print(f"   总未实现盈亏: {portfolio_status['portfolio_summary'].get('total_unrealized_pnl', 0)}")
        else:
            print(f"✗ 投资组合状态获取失败: {portfolio_status['error']}")

        # 测试仓位大小计算
        print("\n3. 测试仓位大小计算...")
        position_calc = trading_manager.position_manager.calculate_position_size(
            trading_pair='BTCUSDT',
            entry_price=50000.0,
            risk_percentage=2.0,
            stop_loss_price=48000.0
        )

        if 'error' not in position_calc:
            print("✓ 仓位大小计算成功")
            print(f"   建议数量: {position_calc['quantity']}")
            print(f"   总价值: {position_calc['total_value']}")
            print(f"   风险金额: {position_calc['risk_amount']}")
        else:
            print(f"✗ 仓位大小计算失败: {position_calc['error']}")

        # 测试模拟策略执行
        print("\n4. 测试模拟策略执行...")
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
        print(f"✓ 策略执行结果: {result['status']} - {result['message']}")

        # 测试价格监控（短时间）
        print("\n5. 测试价格监控...")

        # 从配置文件获取高优先级交易对用于测试
        monitor_pairs = getattr(config, 'HIGH_PRIORITY_PAIRS', ['BTCUSDT', 'ETHUSDT'])
        trading_manager.start_monitoring(monitor_pairs)
        print(f"✓ 价格监控已启动: {monitor_pairs}")

        # 等待几秒钟接收价格数据
        print("   等待价格数据...")
        time.sleep(5)

        current_prices = trading_manager.get_current_prices()
        if current_prices:
            print("✓ 价格数据接收成功")
            for symbol, price in current_prices.items():
                print(f"   {symbol}: {price}")
        else:
            print("⚠ 暂未接收到价格数据")

        # 停止监控
        trading_manager.stop_monitoring()
        print("✓ 价格监控已停止")

        # 测试交易历史
        print("\n6. 获取交易历史...")
        trading_history = trading_manager.get_trading_history(days=7)
        print(f"✓ 获取到{len(trading_history)}条交易历史记录")

        print("\n=== 测试完成 ===")

    except Exception as e:
        logger.error(f"测试失败: {e}")
        print(f"✗ 测试失败: {e}")

def test_individual_modules():
    """测试各个模块的独立功能"""
    try:
        # 加载配置
        config = load_config()
        db_config = get_db_config(config)

        print("\n=== 独立模块测试 ===")

        # 测试交易执行器
        print("1. 测试交易执行器...")
        from app.data_collectors.binance_data_collector import initialize_binance_client
        from app.trading.trading_executor import TradingExecutor

        client = initialize_binance_client(
            api_key=config.BINANCE_API_KEY,
            api_secret=config.BINANCE_API_SECRET,
            testnet=config.BINANCE_TESTNET
        )

        if client:
            executor = TradingExecutor(client, db_config)

            # 测试获取账户信息
            account_info = executor.get_account_info()
            if account_info:
                print("✓ 账户信息获取成功")
            else:
                print("✗ 账户信息获取失败")

            # 测试获取余额
            balance = executor.get_balance('USDT')
            if balance:
                print(f"✓ USDT余额: {balance['free']}")
            else:
                print("✗ 余额获取失败")

            # 测试更新账户余额到数据库
            if executor.update_account_balance():
                print("✓ 账户余额更新到数据库成功")
            else:
                print("✗ 账户余额更新到数据库失败")
        else:
            print("✗ Binance客户端初始化失败")

        # 测试仓位管理器
        print("\n2. 测试仓位管理器...")
        from app.trading.position_manager import PositionManager

        if client:
            position_manager = PositionManager(client, db_config)

            # 测试获取开放仓位
            open_positions = position_manager.get_open_positions()
            print(f"✓ 当前开放仓位数量: {len(open_positions)}")

            # 测试投资组合摘要
            portfolio_summary = position_manager.get_portfolio_summary()
            if portfolio_summary:
                print("✓ 投资组合摘要获取成功")
                print(f"   开放仓位: {portfolio_summary.get('open_positions', 0)}")
                print(f"   总保证金: {portfolio_summary.get('total_margin_used', 0)}")
            else:
                print("✗ 投资组合摘要获取失败")

        print("\n=== 独立模块测试完成 ===")

    except Exception as e:
        logger.error(f"独立模块测试失败: {e}")
        print(f"✗ 独立模块测试失败: {e}")

if __name__ == "__main__":
    print("开始交易模块测试...")

    try:
        # 测试交易管理器
        test_trading_manager()

        # 测试独立模块
        test_individual_modules()

    except Exception as e:
        print(f"测试过程中发生错误: {e}")

    print("\n测试结束")
