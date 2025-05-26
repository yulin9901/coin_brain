#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import datetime
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import load_config, get_db_config
from app.database.db_manager import DatabaseManager

# CryptoPanic API URL
CRYPTOPANIC_API_URL = "https://cryptopanic.com/api/v1/posts/"

def fetch_and_store_news():
    print("开始获取和存储新闻...")

    # 从配置文件中获取API密钥
    api_key = "8bc39f860c35443b9d2a61adbc0f5f7e953b0c2b"  # 直接使用配置文件中的密钥

    params = {
        "auth_token": api_key,
        "limit": 10,
        "currencies": "BTC,ETH,SOL,BNB",
        "filter": "hot",
        "public": "true"
    }

    news_data = []

    try:
        print(f"正在请求CryptoPanic API: {CRYPTOPANIC_API_URL}")

        response = requests.get(CRYPTOPANIC_API_URL, params=params)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            if "results" in result:
                news_list = result.get("results", [])
                print(f"获取到 {len(news_list)} 条新闻")

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
                        currencies = [c.get("code", "") for c in item.get("currencies", [])]
                        description = f"这是关于 {', '.join(currencies)} 的新闻。"

                    # 分析情感
                    sentiment_value = item.get("votes", {}).get("positive", 0) - item.get("votes", {}).get("negative", 0)
                    if sentiment_value > 3:
                        sentiment = "positive"
                    elif sentiment_value < -3:
                        sentiment = "negative"
                    else:
                        sentiment = "neutral"

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
                    print(f"处理新闻: {title}")
            else:
                print("API响应中没有'results'字段")
        else:
            print(f"API请求失败，状态码: {response.status_code}")

    except Exception as e:
        print(f"获取新闻时出错: {e}")
        return

    # 存储新闻数据到数据库
    if news_data:
        try:
            config = load_config()
            db_config = get_db_config(config)

            print("开始存储新闻数据到数据库...")
            print(f"数据库配置: {db_config}")

            db_manager = DatabaseManager(db_config)
            inserted_count = 0

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
                        print(f"存储新闻: {news_item['title']}")
                        cursor.execute(add_news_sql, news_item)
                        inserted_count += 1
                    except Exception as err:
                        print(f"数据库错误，无法存储新闻 '{news_item.get('title')}': {err}")

                connection.commit()
                print(f"成功存储了{inserted_count}条加密货币新闻")

        except Exception as err:
            print(f"连接数据库或执行查询时出错: {err}")

if __name__ == "__main__":
    fetch_and_store_news()
