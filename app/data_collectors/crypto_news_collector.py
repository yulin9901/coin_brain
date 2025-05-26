#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
加密货币新闻收集模块
用于从各种来源收集加密货币相关的新闻和社交媒体数据
"""
import os
import sys
import json
import datetime
import logging
import requests
from typing import List, Dict, Any
from textblob import TextBlob

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.database.db_manager import DatabaseManager

# 配置日志
logger = logging.getLogger('crypto_news_collector')

# API接口
CRYPTOPANIC_API_URL = "https://cryptopanic.com/api/v1/posts/"
COINMARKETCAL_API_URL = "https://developers.coinmarketcal.com/v1/events"

def analyze_sentiment(text: str) -> str:
    """
    使用TextBlob分析文本情感

    Args:
        text (str): 要分析的文本

    Returns:
        str: 情感分析结果 (positive, negative, neutral)
    """
    if not text:
        return "neutral"

    try:
        analysis = TextBlob(text)
        # 获取极性分数 (-1.0 到 1.0)
        polarity = analysis.sentiment.polarity

        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        else:
            return "neutral"
    except Exception as e:
        logger.error(f"情感分析失败: {e}")
        return "neutral"

def fetch_cryptopanic_news(api_key: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    从CryptoPanic获取加密货币新闻

    Args:
        api_key (str): CryptoPanic API密钥
        limit (int): 获取的新闻数量

    Returns:
        List[Dict[str, Any]]: 新闻数据列表
    """
    news_data = []
    params = {
        "auth_token": api_key,
        "limit": limit,
        "currencies": "BTC,ETH,SOL,BNB",  # 关注的主要加密货币
        "filter": "hot",  # 获取热门新闻
        "public": "true"  # 只获取公开的新闻
    }

    try:
        response = requests.get(CRYPTOPANIC_API_URL, params=params)
        response.raise_for_status()
        result = response.json()

        if "results" in result:
            news_list = result.get("results", [])

            for item in news_list:
                # 解析时间戳
                try:
                    timestamp_str = item.get("created_at", "")
                    timestamp_val = datetime.datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
                except (ValueError, TypeError):
                    timestamp_val = datetime.datetime.now()

                # 获取新闻内容
                title = item.get("title", "")
                if not title and "currencies" in item:
                    # 如果没有标题，使用货币名称作为标题的一部分
                    currencies = [c.get("code", "") for c in item.get("currencies", [])]
                    title = f"关于 {', '.join(currencies)} 的新闻"

                # 获取URL和来源
                url = ""
                source = "CryptoPanic"
                if "source" in item:
                    source_info = item.get("source", {})
                    source = source_info.get("title", "CryptoPanic")
                    url = source_info.get("url", "")

                # 如果URL为空，使用CryptoPanic的ID作为URL的一部分，确保唯一性
                if not url and "id" in item:
                    url = f"https://cryptopanic.com/news/{item.get('id', '')}/click/"

                # 获取内容摘要
                description = item.get("body", "")
                if not description and "currencies" in item:
                    # 如果没有内容，使用货币信息作为摘要的一部分
                    currencies = [c.get("code", "") for c in item.get("currencies", [])]
                    description = f"这是关于 {', '.join(currencies)} 的新闻。"

                # 分析情感
                sentiment_value = item.get("votes", {}).get("positive", 0) - item.get("votes", {}).get("negative", 0)
                if sentiment_value > 3:
                    sentiment = "positive"
                elif sentiment_value < -3:
                    sentiment = "negative"
                else:
                    sentiment = analyze_sentiment(description)

                news_item = {
                    "timestamp": timestamp_val.strftime("%Y-%m-%d %H:%M:%S"),
                    "source": source,
                    "title": title,
                    "url": url,
                    "content_summary": description,
                    "sentiment": sentiment,
                    "retrieved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                news_data.append(news_item)

            logger.info(f"成功从CryptoPanic获取{len(news_data)}条加密货币新闻")
        else:
            logger.error("CryptoPanic API返回格式不正确")

    except requests.exceptions.RequestException as e:
        logger.error(f"请求CryptoPanic API失败: {e}")
    except json.JSONDecodeError:
        logger.error("解析CryptoPanic API响应失败")
    except Exception as e:
        logger.error(f"获取CryptoPanic新闻时出错: {e}")

    return news_data

def fetch_coinmarketcal_events(api_key: str, x_api_key: str, limit: int = 30) -> List[Dict[str, Any]]:
    """
    从CoinMarketCal获取加密货币相关事件

    Args:
        api_key (str): CoinMarketCal API密钥
        x_api_key (str): CoinMarketCal X-API-KEY
        limit (int): 获取的事件数量

    Returns:
        List[Dict[str, Any]]: 事件数据列表
    """
    news_data = []

    # 设置请求头和参数
    headers = {
        "x-api-key": x_api_key,
        "Accept-Encoding": "gzip",
        "Accept": "application/json"
    }

    params = {
        "max": limit,
        "dateRangeStart": datetime.date.today().strftime("%Y-%m-%d"),
        "dateRangeEnd": (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
        "showOnly": "hot",  # 只显示热门事件
        "sortBy": "created_desc"  # 按创建时间降序排序
    }

    try:
        response = requests.get(COINMARKETCAL_API_URL, headers=headers, params=params)
        response.raise_for_status()
        result = response.json()

        if "body" in result:
            events_list = result.get("body", [])

            for event in events_list:
                # 解析时间戳
                try:
                    date_str = event.get("date_event", "")
                    event_date = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                except (ValueError, TypeError):
                    event_date = datetime.datetime.now()

                # 获取事件内容
                title = event.get("title", {}).get("en", "无标题")
                description = event.get("description", {}).get("en", "")

                # 获取相关币种
                coins = event.get("coins", [])
                coin_names = []
                for coin in coins:
                    coin_names.append(coin.get("fullname", ""))

                coin_str = ", ".join(coin_names) if coin_names else "加密货币"

                # 如果描述为空，使用标题和币种信息
                if not description:
                    description = f"{title} - 相关币种: {coin_str}"

                # 分析情感
                sentiment = analyze_sentiment(description)

                # 构建URL
                url = f"https://coinmarketcal.com/en/event/{event.get('id', '')}"

                news_item = {
                    "timestamp": event_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "source": "CoinMarketCal",
                    "title": title,
                    "url": url,
                    "content_summary": description,
                    "sentiment": sentiment,
                    "retrieved_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }

                news_data.append(news_item)

            logger.info(f"成功从CoinMarketCal获取{len(news_data)}条加密货币事件")
        else:
            logger.error("CoinMarketCal API返回格式不正确")

    except requests.exceptions.RequestException as e:
        logger.error(f"请求CoinMarketCal API失败: {e}")
    except json.JSONDecodeError:
        logger.error("解析CoinMarketCal API响应失败")
    except Exception as e:
        logger.error(f"获取CoinMarketCal事件时出错: {e}")

    return news_data

def store_crypto_news_data(db_config: Dict[str, Any], news_data: List[Dict[str, Any]]) -> int:
    """
    将加密货币新闻数据存储到数据库

    Args:
        db_config (Dict[str, Any]): 数据库配置
        news_data (List[Dict[str, Any]]): 新闻数据列表

    Returns:
        int: 成功插入的记录数
    """
    if not news_data:
        logger.warning("没有加密货币新闻数据可存储")
        return 0

    db_manager = DatabaseManager(db_config)
    inserted_count = 0

    try:
        with db_manager.get_connection() as (connection, cursor):
            add_news_sql = ("""
            INSERT INTO hot_topics
            (timestamp, source, title, url, content_summary, sentiment, retrieved_at)
            VALUES (%(timestamp)s, %(source)s, %(title)s, %(url)s, %(content_summary)s, %(sentiment)s, %(retrieved_at)s)
            ON DUPLICATE KEY UPDATE
            title=VALUES(title),
            content_summary=VALUES(content_summary),
            sentiment=VALUES(sentiment),
            retrieved_at=VALUES(retrieved_at)
            """)

            for news_item in news_data:
                try:
                    cursor.execute(add_news_sql, news_item)
                    inserted_count += 1
                except Exception as err:
                    logger.error(f"数据库错误，无法存储新闻 '{news_item.get('title')}': {err}")

            connection.commit()
            logger.info(f"成功存储了{inserted_count}条加密货币新闻")

    except Exception as err:
        logger.error(f"连接数据库或执行查询时出错: {err}")
        return 0

    return inserted_count

def fetch_crypto_hot_topics(config) -> List[Dict[str, Any]]:
    """
    获取加密货币热点话题（整合多个来源）

    Args:
        config: 配置对象，包含API密钥

    Returns:
        List[Dict[str, Any]]: 热点话题数据列表
    """
    all_news = []

    # 从CryptoPanic获取新闻
    if hasattr(config, "CRYPTOPANIC_API_KEY") and config.CRYPTOPANIC_API_KEY != "YOUR_CRYPTOPANIC_API_KEY_HERE":
        try:
            cryptopanic_news = fetch_cryptopanic_news(config.CRYPTOPANIC_API_KEY)
            all_news.extend(cryptopanic_news)
            logger.info(f"从CryptoPanic获取了{len(cryptopanic_news)}条新闻")
        except Exception as e:
            logger.error(f"获取CryptoPanic新闻时出错: {e}")
    else:
        logger.warning("未配置CryptoPanic API密钥或使用了占位符，跳过获取CryptoPanic新闻")

    # 从CoinMarketCal获取事件
    if (hasattr(config, "COINMARKETCAL_API_KEY") and config.COINMARKETCAL_API_KEY != "YOUR_COINMARKETCAL_API_KEY_HERE" and
        hasattr(config, "COINMARKETCAL_X_API_KEY") and config.COINMARKETCAL_X_API_KEY != "YOUR_COINMARKETCAL_X_API_KEY_HERE"):
        try:
            coinmarketcal_events = fetch_coinmarketcal_events(
                config.COINMARKETCAL_API_KEY,
                config.COINMARKETCAL_X_API_KEY
            )
            all_news.extend(coinmarketcal_events)
            logger.info(f"从CoinMarketCal获取了{len(coinmarketcal_events)}条事件")
        except Exception as e:
            logger.error(f"获取CoinMarketCal事件时出错: {e}")
    else:
        logger.warning("未配置CoinMarketCal API密钥或使用了占位符，跳过获取CoinMarketCal事件")

    # 可以添加更多来源...

    logger.info(f"总共获取了{len(all_news)}条加密货币热点话题")
    return all_news

# 如果直接运行此脚本，执行测试
if __name__ == "__main__":
    print("执行crypto_news_collector.py作为独立脚本（用于测试）")

    # 使用统一的配置加载方式
    try:
        from app.utils import load_config, get_db_config
        config = load_config()
        db_config = get_db_config(config)

        print("成功加载配置文件")
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        print("使用测试配置...")
        # 创建一个模拟配置对象
        class MockConfig:
            def __init__(self):
                self.CRYPTOPANIC_API_KEY = "YOUR_CRYPTOPANIC_API_KEY_HERE"
                self.COINMARKETCAL_API_KEY = "YOUR_COINMARKETCAL_API_KEY_HERE"
                self.COINMARKETCAL_X_API_KEY = "YOUR_COINMARKETCAL_X_API_KEY_HERE"

        config = MockConfig()
        db_config = {
            "DB_HOST": "localhost",
            "DB_PORT": 3306,
            "DB_USER": "your_db_user",
            "DB_PASSWORD": "your_db_password",
            "DB_NAME": "crypto_trading"
        }

    # 检查是否配置了CryptoPanic API密钥
    has_cryptopanic_key = hasattr(config, "CRYPTOPANIC_API_KEY") and config.CRYPTOPANIC_API_KEY != "YOUR_CRYPTOPANIC_API_KEY_HERE"
    # 检查是否配置了CoinMarketCal API密钥
    has_coinmarketcal_keys = (hasattr(config, "COINMARKETCAL_API_KEY") and config.COINMARKETCAL_API_KEY != "YOUR_COINMARKETCAL_API_KEY_HERE" and
                             hasattr(config, "COINMARKETCAL_X_API_KEY") and config.COINMARKETCAL_X_API_KEY != "YOUR_COINMARKETCAL_X_API_KEY_HERE")

    if has_cryptopanic_key or has_coinmarketcal_keys:
        # 测试获取加密货币热点话题
        hot_topics = fetch_crypto_hot_topics(config)

        if hot_topics:
            print(f"获取到{len(hot_topics)}条加密货币热点话题")

            # 打印前3条热点话题
            for i, topic in enumerate(hot_topics[:3]):
                print(f"\n热点话题 {i+1}:")
                print(f"标题: {topic['title']}")
                print(f"来源: {topic['source']}")
                print(f"情感: {topic['sentiment']}")
                print(f"摘要: {topic['content_summary'][:100]}...")

            # 如果数据库配置有效，存储热点话题
            if db_config["DB_USER"] != "your_db_user":
                inserted = store_crypto_news_data(db_config, hot_topics)
                print(f"存储了{inserted}条热点话题")
    else:
        print("未提供有效的CryptoPanic或CoinMarketCal API密钥，无法执行测试")
