#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
配置文件验证工具
检查配置文件中的交易对和其他设置是否正确
"""
import os
import sys

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.utils import load_config

def validate_trading_pairs(config):
    """验证交易对配置"""
    print("=== 交易对配置验证 ===")

    # 检查是否存在重复的配置
    binance_trading_pairs = getattr(config, 'BINANCE_TRADING_PAIRS', None)
    if binance_trading_pairs is not None:
        print("⚠️  警告: 发现过时的配置 BINANCE_TRADING_PAIRS")
        print("   建议删除 BINANCE_TRADING_PAIRS，统一使用 TRADING_PAIRS")

    # 检查主要交易对列表
    trading_pairs = getattr(config, 'TRADING_PAIRS', [])
    if not trading_pairs:
        print("❌ 错误: TRADING_PAIRS 未配置或为空")
        return False

    print(f"✅ 主要交易对: {len(trading_pairs)}个")
    for i, pair in enumerate(trading_pairs, 1):
        print(f"   {i}. {pair}")

    # 检查高优先级交易对
    high_priority_pairs = getattr(config, 'HIGH_PRIORITY_PAIRS', [])
    if not high_priority_pairs:
        print("⚠️  警告: HIGH_PRIORITY_PAIRS 未配置，将使用默认值")
    else:
        print(f"✅ 高优先级交易对: {len(high_priority_pairs)}个")
        for pair in high_priority_pairs:
            print(f"   - {pair}")
            if pair not in trading_pairs:
                print(f"   ⚠️  警告: {pair} 不在主要交易对列表中")

    # 检查低优先级交易对
    low_priority_pairs = getattr(config, 'LOW_PRIORITY_PAIRS', [])
    if low_priority_pairs:
        print(f"✅ 低优先级交易对: {len(low_priority_pairs)}个")
        for pair in low_priority_pairs:
            print(f"   - {pair}")
            if pair not in trading_pairs:
                print(f"   ⚠️  警告: {pair} 不在主要交易对列表中")

    # 检查币种符号
    crypto_symbols = getattr(config, 'CRYPTO_SYMBOLS', [])
    if crypto_symbols:
        print(f"✅ 币种符号: {len(crypto_symbols)}个")
        print(f"   {', '.join(crypto_symbols)}")
    else:
        print("⚠️  警告: CRYPTO_SYMBOLS 未配置")

    # 验证交易对格式
    print("\n--- 交易对格式验证 ---")
    valid_pairs = []
    invalid_pairs = []

    for pair in trading_pairs:
        if isinstance(pair, str) and pair.endswith('USDT') and len(pair) > 4:
            valid_pairs.append(pair)
        else:
            invalid_pairs.append(pair)

    if invalid_pairs:
        print(f"❌ 无效的交易对格式: {invalid_pairs}")
        return False
    else:
        print(f"✅ 所有交易对格式正确")

    return True

def validate_kline_config(config):
    """验证K线配置"""
    print("\n=== K线数据配置验证 ===")

    # 检查K线间隔
    kline_intervals = getattr(config, 'KLINE_INTERVALS', [])
    if not kline_intervals:
        print("⚠️  警告: KLINE_INTERVALS 未配置，将使用默认值")
    else:
        print(f"✅ K线间隔: {kline_intervals}")

        # 验证间隔格式
        valid_intervals = ['1m', '3m', '5m', '15m', '30m', '1h', '2h', '4h', '6h', '8h', '12h', '1d', '3d', '1w', '1M']
        invalid_intervals = [interval for interval in kline_intervals if interval not in valid_intervals]

        if invalid_intervals:
            print(f"❌ 无效的K线间隔: {invalid_intervals}")
            print(f"   有效的间隔: {valid_intervals}")
            return False

    # 检查K线限制
    kline_limits = getattr(config, 'KLINE_LIMITS', {})
    if not kline_limits:
        print("⚠️  警告: KLINE_LIMITS 未配置，将使用默认值")
    else:
        print(f"✅ K线数据限制:")
        for interval, limit in kline_limits.items():
            print(f"   {interval}: {limit}条")

            # 验证限制值
            if not isinstance(limit, int) or limit <= 0:
                print(f"❌ 无效的限制值: {interval} = {limit}")
                return False

            if limit > 1000:
                print(f"⚠️  警告: {interval} 的限制值 {limit} 可能过大，建议不超过1000")

    return True

def validate_risk_config(config):
    """验证风险管理配置"""
    print("\n=== 风险管理配置验证 ===")

    # 检查风险百分比
    risk_percentage = getattr(config, 'DEFAULT_RISK_PERCENTAGE', 2.0)
    print(f"✅ 默认风险百分比: {risk_percentage}%")

    if risk_percentage <= 0 or risk_percentage > 10:
        print(f"⚠️  警告: 风险百分比 {risk_percentage}% 可能不合理，建议设置在1-5%之间")

    # 检查最大仓位数量
    max_positions = getattr(config, 'MAX_OPEN_POSITIONS', 5)
    print(f"✅ 最大开放仓位: {max_positions}个")

    if max_positions <= 0 or max_positions > 20:
        print(f"⚠️  警告: 最大仓位数量 {max_positions} 可能不合理，建议设置在3-10之间")

    # 检查最小交易金额
    min_trade_amount = getattr(config, 'MIN_TRADE_AMOUNT', 10.0)
    print(f"✅ 最小交易金额: {min_trade_amount} USDT")

    if min_trade_amount < 5:
        print(f"⚠️  警告: 最小交易金额 {min_trade_amount} USDT 可能过小")

    # 检查最大杠杆
    max_leverage = getattr(config, 'MAX_LEVERAGE', 3.0)
    print(f"✅ 最大杠杆倍数: {max_leverage}x")

    if max_leverage > 10:
        print(f"⚠️  警告: 最大杠杆 {max_leverage}x 风险较高，建议不超过5x")

    return True

def validate_api_config(config):
    """验证API配置"""
    print("\n=== API配置验证 ===")

    # 检查Binance API
    binance_key = getattr(config, 'BINANCE_API_KEY', '')
    binance_secret = getattr(config, 'BINANCE_API_SECRET', '')
    binance_testnet = getattr(config, 'BINANCE_TESTNET', True)

    if binance_key == 'YOUR_BINANCE_API_KEY_HERE':
        print("❌ 错误: Binance API Key 未配置")
        return False
    else:
        print("✅ Binance API Key 已配置")

    if binance_secret == 'YOUR_BINANCE_API_SECRET_HERE':
        print("❌ 错误: Binance API Secret 未配置")
        return False
    else:
        print("✅ Binance API Secret 已配置")

    print(f"✅ Binance 测试网络: {'启用' if binance_testnet else '禁用'}")
    if not binance_testnet:
        print("⚠️  警告: 已禁用测试网络，将使用实盘交易！")

    # 检查OpenAI API
    openai_key = getattr(config, 'OPENAI_API_KEY', '')
    if openai_key == 'YOUR_OPENAI_API_KEY_HERE':
        print("⚠️  警告: OpenAI API Key 未配置，AI功能将使用模拟响应")
    else:
        print("✅ OpenAI API Key 已配置")

    return True

def validate_trading_config(config):
    """验证交易配置"""
    print("\n=== 交易配置验证 ===")

    # 检查自动交易开关
    auto_trading = getattr(config, 'ENABLE_AUTO_TRADING', False)
    print(f"✅ 自动交易: {'启用' if auto_trading else '禁用'}")

    if auto_trading:
        print("⚠️  警告: 自动交易已启用，请确保已充分测试！")

    # 检查价格监控
    price_monitoring = getattr(config, 'ENABLE_PRICE_MONITORING', True)
    print(f"✅ 价格监控: {'启用' if price_monitoring else '禁用'}")

    # 检查止盈止损配置
    stop_loss_pct = getattr(config, 'DEFAULT_STOP_LOSS_PERCENTAGE', 2.0)
    take_profit_pct = getattr(config, 'DEFAULT_TAKE_PROFIT_PERCENTAGE', 4.0)

    print(f"✅ 默认止损百分比: {stop_loss_pct}%")
    print(f"✅ 默认止盈百分比: {take_profit_pct}%")

    if stop_loss_pct >= take_profit_pct:
        print("❌ 错误: 止损百分比应该小于止盈百分比")
        return False

    return True

def main():
    """主函数"""
    print("配置文件验证工具")
    print("=" * 50)

    try:
        # 加载配置
        config = load_config()
        print("✅ 配置文件加载成功\n")

        # 执行各项验证
        validations = [
            validate_trading_pairs(config),
            validate_kline_config(config),
            validate_risk_config(config),
            validate_api_config(config),
            validate_trading_config(config)
        ]

        # 总结验证结果
        print("\n" + "=" * 50)
        print("验证结果总结:")

        if all(validations):
            print("✅ 所有配置验证通过！")
            print("系统可以正常运行。")
        else:
            print("❌ 配置验证失败！")
            print("请修复上述错误后重新运行验证。")

        # 显示配置摘要
        print(f"\n配置摘要:")
        trading_pairs = getattr(config, 'TRADING_PAIRS', [])
        print(f"- 交易对数量: {len(trading_pairs)}")
        print(f"- 自动交易: {'启用' if getattr(config, 'ENABLE_AUTO_TRADING', False) else '禁用'}")
        print(f"- 测试网络: {'启用' if getattr(config, 'BINANCE_TESTNET', True) else '禁用'}")
        print(f"- 风险百分比: {getattr(config, 'DEFAULT_RISK_PERCENTAGE', 2.0)}%")

    except Exception as e:
        print(f"❌ 配置文件验证失败: {e}")
        print("\n请检查:")
        print("1. config/config.py 文件是否存在")
        print("2. 配置文件语法是否正确")
        print("3. 是否从 config.py.template 正确复制")

if __name__ == "__main__":
    main()
