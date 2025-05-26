#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
加密货币每日数据汇总处理模块
用于汇总每日加密货币市场数据和热点资讯
"""
import os
import sys
import json
import datetime
import logging
import decimal
from typing import Dict, Any, List, Optional

# 自定义JSON编码器，处理Decimal类型
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.database.db_manager import DatabaseManager

# 配置日志
logger = logging.getLogger('daily_summary_processor')

def calculate_market_sentiment(topics_data: List[Dict[str, Any]]) -> str:
    """
    根据热点话题的情感分析结果计算整体市场情绪

    Args:
        topics_data (List[Dict[str, Any]]): 热点话题数据列表

    Returns:
        str: 市场情绪指标 (Bullish, Bearish, Neutral)
    """
    if not topics_data:
        return "Neutral"

    sentiment_counts = {"positive": 0, "negative": 0, "neutral": 0}

    for topic in topics_data:
        sentiment = topic.get("sentiment", "neutral")
        sentiment_counts[sentiment] += 1

    total = len(topics_data)
    positive_ratio = sentiment_counts["positive"] / total
    negative_ratio = sentiment_counts["negative"] / total

    if positive_ratio > 0.6:
        return "Bullish"
    elif negative_ratio > 0.6:
        return "Bearish"
    elif positive_ratio > negative_ratio and positive_ratio > 0.4:
        return "Slightly Bullish"
    elif negative_ratio > positive_ratio and negative_ratio > 0.4:
        return "Slightly Bearish"
    else:
        return "Neutral"

def process_and_store_crypto_daily_summary(db_config: Dict[str, Any], target_date_str: Optional[str] = None) -> bool:
    """
    从hot_topics和market_fund_flows获取每日数据，汇总后存储到daily_summary表

    Args:
        db_config (Dict[str, Any]): 数据库配置
        target_date_str (Optional[str]): 目标日期，格式为'YYYY-MM-DD'，默认为今天

    Returns:
        bool: 操作是否成功
    """
    if target_date_str:
        try:
            target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"无效的日期格式: {target_date_str}，请使用YYYY-MM-DD格式")
            return False
    else:
        target_date = datetime.date.today()

    logger.info(f"开始{target_date.strftime('%Y-%m-%d')}的加密货币每日数据汇总...")

    db_manager = DatabaseManager(db_config)

    try:
        # 使用数据库管理器的上下文管理器
        with db_manager.get_connection(dictionary=True) as (connection, cursor):
            # 1. 获取并汇总当日热点话题
            query_topics = """
            SELECT title, source, content_summary, sentiment FROM hot_topics
            WHERE DATE(retrieved_at) = %(target_date)s
            ORDER BY timestamp DESC LIMIT 15
            """
            cursor.execute(query_topics, {"target_date": target_date.strftime("%Y-%m-%d")})
            topics = cursor.fetchall()

            if topics:
                topic_details = []
                for t in topics:
                    sentiment_emoji = "😐"  # 默认中性
                    if t.get('sentiment') == 'positive':
                        sentiment_emoji = "🔥"
                    elif t.get('sentiment') == 'negative':
                        sentiment_emoji = "❄️"

                    if t.get('content_summary'):
                        topic_details.append(f"{sentiment_emoji} {t['title']} ({t['source']}): {t['content_summary']}")
                    else:
                        topic_details.append(f"{sentiment_emoji} {t['title']} ({t['source']})")

                aggregated_hot_topics_summary = "Today's key crypto topics: " + "; ".join(topic_details)
            else:
                aggregated_hot_topics_summary = "No specific crypto hot topics found for today in the database."

            # 2. 获取并汇总当日市场资金流向
            query_flows = """
            SELECT crypto_symbol, inflow_amount, change_rate, volume_24h, funding_rate, open_interest
            FROM market_fund_flows
            WHERE DATE(retrieved_at) = %(target_date)s
            ORDER BY volume_24h DESC
            """
            cursor.execute(query_flows, {"target_date": target_date.strftime("%Y-%m-%d")})
            flows = cursor.fetchall()

            if flows:
                market_details = []
                key_market_indicators = {}

                for f in flows:
                    crypto = f['crypto_symbol']
                    change = f.get('change_rate', 0)
                    volume = f.get('volume_24h', 0)
                    funding = f.get('funding_rate', 0)

                    # 格式化数字
                    change_str = f"{change:.2f}%" if change is not None else "N/A"
                    volume_str = f"{volume:.2f}" if volume is not None else "N/A"
                    funding_str = f"{funding*100:.4f}%" if funding is not None else "N/A"

                    market_details.append(f"{crypto}: Change {change_str}, Vol {volume_str}, Funding {funding_str}")

                    # 存储关键市场指标
                    key_market_indicators[crypto] = {
                        "change_rate": change,
                        "volume_24h": volume,
                        "funding_rate": funding,
                        "open_interest": f.get('open_interest', 0)
                    }

                aggregated_market_summary = f"Crypto market overview: {'; '.join(market_details)}"
            else:
                aggregated_market_summary = "No specific crypto market data found for today in the database."
                key_market_indicators = {}

            # 3. 计算市场情绪指标
            market_sentiment_indicator = calculate_market_sentiment(topics)

            # 4. 存储汇总数据到daily_summary表
            insert_summary_sql = ("""
            INSERT INTO daily_summary
            (date, aggregated_hot_topics_summary, aggregated_market_summary, market_sentiment_indicator, key_market_indicators)
            VALUES (%(date)s, %(topics_summary)s, %(market_summary)s, %(sentiment)s, %(market_indicators)s)
            ON DUPLICATE KEY UPDATE
            aggregated_hot_topics_summary = VALUES(aggregated_hot_topics_summary),
            aggregated_market_summary = VALUES(aggregated_market_summary),
            market_sentiment_indicator = VALUES(market_sentiment_indicator),
            key_market_indicators = VALUES(key_market_indicators),
            created_at = CURRENT_TIMESTAMP
            """)

            summary_data = {
                "date": target_date.strftime("%Y-%m-%d"),
                "topics_summary": aggregated_hot_topics_summary,
                "market_summary": aggregated_market_summary,
                "sentiment": market_sentiment_indicator,
                "market_indicators": json.dumps(key_market_indicators, cls=DecimalEncoder)
            }

            cursor.execute(insert_summary_sql, summary_data)
            connection.commit()
            logger.info(f"成功存储/更新{target_date.strftime('%Y-%m-%d')}的每日汇总数据")
            return True

    except Exception as err:
        logger.error(f"每日汇总过程中数据库错误: {err}")
        return False

# 如果直接运行此脚本，执行测试
if __name__ == "__main__":
    print("执行daily_summary_processor.py作为独立脚本（用于测试）")

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 使用统一的配置加载方式
    try:
        from app.utils import load_config, get_db_config
        config = load_config()
        db_config = get_db_config(config)
        print("成功加载配置文件")
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        print("使用测试配置...")
        # 测试配置
        db_config = {
            "DB_HOST": "localhost",
            "DB_PORT": 3306,
            "DB_USER": "your_db_user",
            "DB_PASSWORD": "your_db_password",
            "DB_NAME": "crypto_trading"
        }

    if db_config["DB_USER"] == "your_db_user":
        print("警告: 使用占位符数据库凭据进行直接脚本执行")
        print("如果要使用真实数据进行测试，请配置它们")
    else:
        # 使用今天的日期进行测试
        success = process_and_store_crypto_daily_summary(db_config=db_config)
        # 使用特定日期进行测试
        # success = process_and_store_crypto_daily_summary(db_config=db_config, target_date_str="2023-05-13")
        if success:
            print("加密货币每日数据汇总过程成功完成（来自测试调用）")
        else:
            print("加密货币每日数据汇总过程失败或遇到错误（来自测试调用）")
