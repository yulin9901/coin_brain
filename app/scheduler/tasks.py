#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
加密货币定时任务定义
定义了加密货币系统中的各种定时任务
"""
import os
import sys
import datetime
import logging
from typing import List, Optional

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.utils import load_config, get_db_config
from app.data_collectors.crypto_news_collector import fetch_crypto_hot_topics, store_crypto_news_data
from app.data_collectors.binance_data_collector import (
    initialize_binance_client,
    fetch_market_fund_flow_data,
    store_market_fund_flow_data,
    fetch_kline_data,
    store_kline_data
)
from app.data_processors.daily_summary_processor import process_and_store_crypto_daily_summary
from app.decision_makers.trading_strategy_ai import generate_trading_strategy

# 配置日志
logger = logging.getLogger('crypto_tasks')

def collect_crypto_news():
    """收集加密货币热点新闻任务"""
    logger.info("开始收集加密货币热点新闻...")

    try:
        config = load_config()
        db_config = get_db_config(config)

        news_data = fetch_crypto_hot_topics(config)
        if news_data:
            inserted_count = store_crypto_news_data(db_config=db_config, news_data=news_data)
            logger.info(f"成功收集并存储了 {inserted_count} 条加密货币热点新闻")
            return True
        else:
            logger.warning("未能获取加密货币热点新闻或返回为空")
            return False
    except Exception as e:
        logger.error(f"收集加密货币热点新闻时出错: {e}")
        return False

def collect_crypto_market_data(trading_pairs: List[str] = None):
    """收集加密货币市场数据任务"""
    logger.info("开始收集加密货币市场数据...")

    try:
        config = load_config()
        db_config = get_db_config(config)

        # 如果没有传入交易对，从配置文件读取
        if trading_pairs is None:
            trading_pairs = getattr(config, 'TRADING_PAIRS', ["BTCUSDT", "ETHUSDT", "SOLUSDT"])

        logger.info(f"收集交易对: {trading_pairs}")

        # 初始化Binance客户端
        client = initialize_binance_client(
            api_key=config.BINANCE_API_KEY,
            api_secret=config.BINANCE_API_SECRET,
            testnet=config.BINANCE_TESTNET
        )

        if not client:
            logger.error("初始化Binance客户端失败")
            return False

        # 收集市场资金流向数据
        market_flows = fetch_market_fund_flow_data(client, trading_pairs)
        if market_flows:
            inserted_count = store_market_fund_flow_data(db_config=db_config, flows_data=market_flows)
            logger.info(f"成功收集并存储了 {inserted_count} 条市场资金流向数据")
        else:
            logger.warning("未能获取市场资金流向数据或返回为空")

        # 收集K线数据
        kline_success = True

        # 从配置文件读取K线间隔和限制
        kline_intervals = getattr(config, 'KLINE_INTERVALS', ["1m", "5m", "1h", "1d"])
        kline_limits = getattr(config, 'KLINE_LIMITS', {
            "1m": 100, "5m": 200, "1h": 500, "1d": 1000
        })

        for pair in trading_pairs:
            # 收集不同时间周期的K线数据
            for interval in kline_intervals:
                # 从配置文件获取对应间隔的数据量限制
                limit = kline_limits.get(interval, 500)

                klines = fetch_kline_data(client, symbol=pair, interval=interval, limit=limit)
                if klines:
                    inserted_count = store_kline_data(db_config=db_config, kline_data=klines)
                    logger.info(f"成功收集并存储了 {inserted_count} 条 {pair} {interval} K线数据")
                else:
                    logger.warning(f"未能获取 {pair} {interval} K线数据或返回为空")
                    kline_success = False

        return kline_success
    except Exception as e:
        logger.error(f"收集加密货币市场数据时出错: {e}")
        return False

def summarize_crypto_daily_data(target_date_str: Optional[str] = None):
    """汇总加密货币每日数据任务"""
    if not target_date_str:
        target_date_str = datetime.date.today().strftime("%Y-%m-%d")

    logger.info(f"开始汇总 {target_date_str} 的加密货币数据...")

    try:
        config = load_config()
        db_config = get_db_config(config)

        success = process_and_store_crypto_daily_summary(db_config=db_config, target_date_str=target_date_str)
        if success:
            logger.info(f"成功汇总 {target_date_str} 的加密货币数据")
            return True
        else:
            logger.warning(f"汇总 {target_date_str} 的加密货币数据失败或未完成")
            return False
    except Exception as e:
        logger.error(f"汇总 {target_date_str} 的加密货币数据时出错: {e}")
        return False

def generate_coin_brain_strategy(target_date_str: Optional[str] = None, trading_pairs: List[str] = None):
    """生成加密货币交易策略任务"""
    if not target_date_str:
        target_date_str = datetime.date.today().strftime("%Y-%m-%d")

    logger.info(f"开始生成 {target_date_str} 的加密货币交易策略...")

    try:
        config = load_config()
        db_config = get_db_config(config)

        # 如果没有传入交易对，从配置文件读取
        if trading_pairs is None:
            trading_pairs = getattr(config, 'TRADING_PAIRS', ["BTCUSDT", "ETHUSDT", "SOLUSDT"])

        logger.info(f"生成策略的交易对: {trading_pairs}")

        # 获取AI模型名称，如果配置中没有，则使用默认值
        ai_model_name = getattr(config, "AI_MODEL_NAME", "gpt-3.5-turbo")

        success = generate_trading_strategy(
            db_config=db_config,
            openai_api_key=config.OPENAI_API_KEY,
            sealos_api_url=config.SEALOS_API_URL,
            target_date_str=target_date_str,
            trading_pairs=trading_pairs,
            ai_model_name=ai_model_name
        )
        if success:
            logger.info(f"成功生成 {target_date_str} 的加密货币交易策略")
            return True
        else:
            logger.warning(f"生成 {target_date_str} 的加密货币交易策略失败或未完成")
            return False
    except Exception as e:
        logger.error(f"生成 {target_date_str} 的加密货币交易策略时出错: {e}")
        return False

def run_crypto_full_workflow(target_date_str: Optional[str] = None, trading_pairs: List[str] = None):
    """运行完整的加密货币工作流程"""
    if not target_date_str:
        target_date_str = datetime.date.today().strftime("%Y-%m-%d")

    logger.info(f"开始运行 {target_date_str} 的完整加密货币工作流程...")

    # 如果没有传入交易对，从配置文件读取
    if trading_pairs is None:
        try:
            config = load_config()
            trading_pairs = getattr(config, 'TRADING_PAIRS', ["BTCUSDT", "ETHUSDT", "SOLUSDT"])
        except Exception as e:
            logger.error(f"加载配置失败，使用默认交易对: {e}")
            trading_pairs = ["BTCUSDT", "ETHUSDT", "SOLUSDT"]

    logger.info(f"工作流程使用的交易对: {trading_pairs}")

    # 1. 收集加密货币热点新闻
    news_success = collect_crypto_news()
    if not news_success:
        logger.warning("收集加密货币热点新闻失败，但继续执行后续步骤")

    # 2. 收集加密货币市场数据
    market_success = collect_crypto_market_data(trading_pairs)
    if not market_success:
        logger.warning("收集加密货币市场数据失败，但继续执行后续步骤")

    # 3. 汇总加密货币每日数据
    summary_success = summarize_crypto_daily_data(target_date_str)
    if not summary_success:
        logger.error("汇总加密货币每日数据失败，无法继续执行后续步骤")
        return False

    # 4. 生成加密货币交易策略
    strategy_success = generate_coin_brain_strategy(target_date_str, trading_pairs)
    if not strategy_success:
        logger.error("生成加密货币交易策略失败")
        return False

    logger.info(f"成功完成 {target_date_str} 的完整加密货币工作流程")
    return True

# 测试代码
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 测试收集加密货币热点新闻
    collect_crypto_news()

    # 测试收集加密货币市场数据
    collect_crypto_market_data()

    # 测试汇总加密货币每日数据
    summarize_crypto_daily_data()

    # 测试生成加密货币交易策略
    generate_coin_brain_strategy()

    # 测试运行完整的加密货币工作流程
    # run_crypto_full_workflow()
