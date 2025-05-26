#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
加密货币交易系统主入口
用于启动加密货币定时任务调度器
"""
import os
import sys
import time
import argparse
import logging
import datetime

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.abspath(__file__))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.scheduler.scheduler import CryptoTradingScheduler
from app.scheduler.tasks import (
    collect_crypto_news,
    collect_crypto_market_data,
    summarize_crypto_daily_data,
    generate_coin_brain_strategy,
    run_crypto_full_workflow
)
from app.utils import load_config, get_db_config

# 创建日志目录
os.makedirs(os.path.join(APP_DIR, 'logs'), exist_ok=True)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(APP_DIR, 'logs', 'coin_brain.log'), encoding='utf-8')
    ]
)
logger = logging.getLogger('coin_brain')

def run_scheduler():
    """运行加密货币定时任务调度器"""
    logger.info("启动加密货币交易系统定时任务调度器...")

    scheduler = CryptoTradingScheduler()
    scheduler.start()

    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("接收到停止信号，正在停止调度器...")
        scheduler.stop()
        logger.info("调度器已停止")

def run_task(task_name, date_str=None, trading_pairs=None):
    """运行指定的任务"""
    logger.info(f"运行任务: {task_name}")

    # 默认交易对
    if trading_pairs is None:
        config = load_config()
        trading_pairs = getattr(config, 'TRADING_PAIRS', ["BTCUSDT", "ETHUSDT", "SOLUSDT"])

    # 当前日期
    today = date_str or datetime.date.today().strftime("%Y-%m-%d")

    if task_name == "collect_crypto_news":
        success = collect_crypto_news()
    elif task_name == "collect_crypto_market_data":
        success = collect_crypto_market_data(trading_pairs)
    elif task_name == "summarize_crypto_daily_data":
        success = summarize_crypto_daily_data(today)
    elif task_name == "generate_coin_brain_strategy":
        success = generate_coin_brain_strategy(today, trading_pairs)
    elif task_name == "collect_hourly_data":
        # 收集加密货币新闻和市场数据
        success1 = collect_crypto_news()
        success2 = collect_crypto_market_data(trading_pairs)
        success = success1 and success2
    elif task_name == "daily_strategy":
        # 汇总数据并生成交易策略
        success1 = summarize_crypto_daily_data(today)
        if success1:
            success2 = generate_coin_brain_strategy(today, trading_pairs)
            success = success1 and success2
        else:
            success = False
    elif task_name == "full_workflow":
        # 运行完整工作流程
        success = run_crypto_full_workflow(today, trading_pairs)
    else:
        logger.error(f"未知任务: {task_name}")
        return

    if success:
        logger.info(f"任务 {task_name} 成功完成")
    else:
        logger.warning(f"任务 {task_name} 失败或未完成")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="加密货币交易系统")
    parser.add_argument("--run", choices=["scheduler", "task"], help="运行模式: scheduler(调度器) 或 task(单个任务)", default="scheduler")
    parser.add_argument("--task", choices=["collect_crypto_news", "collect_crypto_market_data", "summarize_crypto_daily_data",
                                          "generate_coin_brain_strategy", "collect_hourly_data", "daily_strategy", "full_workflow"],
                        help="要运行的任务名称")
    parser.add_argument("--date", help="目标日期 (YYYY-MM-DD)，默认为今天")
    parser.add_argument("--pairs", help="交易对列表，用逗号分隔，例如: BTCUSDT,ETHUSDT,SOLUSDT")

    args = parser.parse_args()

    # 解析交易对
    trading_pairs = None
    if args.pairs:
        trading_pairs = args.pairs.split(",")
        logger.info(f"使用指定的交易对: {trading_pairs}")

    try:
        if args.run == "scheduler":
            run_scheduler()
        elif args.run == "task":
            if not args.task:
                logger.error("运行单个任务时必须指定 --task 参数")
                parser.print_help()
                return
            run_task(args.task, args.date, trading_pairs)
        else:
            logger.error(f"未知运行模式: {args.run}")
            parser.print_help()
    except Exception as e:
        logger.error(f"运行时出错: {e}", exc_info=True)

if __name__ == "__main__":
    main()
