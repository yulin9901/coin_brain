#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json
import datetime
import sys
import os

# 添加项目根目录到Python路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.utils import load_config

# API接口
CRYPTOPANIC_API_URL = "https://cryptopanic.com/api/v1/posts/"

def test_cryptopanic_api():
    """测试CryptoPanic API"""
    print("开始测试CryptoPanic API...")

    try:
        config = load_config()
        print("配置加载成功")
    except Exception as e:
        print(f"加载配置失败: {e}")
        return

    print(f"CRYPTOPANIC_API_KEY: {getattr(config, 'CRYPTOPANIC_API_KEY', '未设置')}")

    if not hasattr(config, "CRYPTOPANIC_API_KEY") or config.CRYPTOPANIC_API_KEY == "YOUR_CRYPTOPANIC_API_KEY_HERE":
        print("未配置CryptoPanic API密钥或使用了占位符")
        return

    api_key = config.CRYPTOPANIC_API_KEY
    limit = 5  # 只获取5条用于测试

    params = {
        "auth_token": api_key,
        "limit": limit,
        "currencies": "BTC,ETH,SOL,BNB",  # 关注的主要加密货币
        "filter": "hot",  # 获取热门新闻
        "public": "true"  # 只获取公开的新闻
    }

    try:
        print(f"正在请求CryptoPanic API: {CRYPTOPANIC_API_URL}")
        print(f"参数: {params}")

        response = requests.get(CRYPTOPANIC_API_URL, params=params)
        print(f"状态码: {response.status_code}")

        if response.status_code == 200:
            result = response.json()

            # 打印完整的响应
            print("\n完整的API响应:")
            print(json.dumps(result, indent=2, ensure_ascii=False))

            if "results" in result:
                news_list = result.get("results", [])
                print(f"\n获取到 {len(news_list)} 条新闻")

                for i, item in enumerate(news_list):
                    print(f"\n新闻 {i+1}:")
                    print(f"标题: {item.get('title', '无标题')}")
                    print(f"时间: {item.get('created_at', '未知时间')}")

                    # 获取URL和来源
                    source = "CryptoPanic"
                    url = ""
                    if "source" in item:
                        source_info = item.get("source", {})
                        source = source_info.get("title", "CryptoPanic")
                        url = source_info.get("url", "")

                    print(f"来源: {source}")
                    print(f"URL: {url}")

                    # 获取内容摘要
                    description = item.get("body", "")
                    if not description and "currencies" in item:
                        currencies = [c.get("code", "") for c in item.get("currencies", [])]
                        description = f"这是关于 {', '.join(currencies)} 的新闻。"

                    print(f"内容摘要: {description}")

                    # 获取相关货币
                    if "currencies" in item:
                        currencies = [c.get("code", "") for c in item.get("currencies", [])]
                        print(f"相关货币: {', '.join(currencies)}")

                    # 获取投票情况
                    if "votes" in item:
                        votes = item.get("votes", {})
                        print(f"投票: 正面 {votes.get('positive', 0)}, 负面 {votes.get('negative', 0)}")
            else:
                print("API响应中没有'results'字段")
        else:
            print(f"API请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")

    except requests.exceptions.RequestException as e:
        print(f"请求CryptoPanic API失败: {e}")
    except json.JSONDecodeError:
        print("解析CryptoPanic API响应失败")
    except Exception as e:
        print(f"测试CryptoPanic API时出错: {e}")

if __name__ == "__main__":
    test_cryptopanic_api()
