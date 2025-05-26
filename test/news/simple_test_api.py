#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
import json

# CryptoPanic API URL
CRYPTOPANIC_API_URL = "https://cryptopanic.com/api/v1/posts/"

def test_api():
    print("开始测试CryptoPanic API...")
    
    # 从配置文件中获取API密钥
    api_key = "8bc39f860c35443b9d2a61adbc0f5f7e953b0c2b"  # 直接使用配置文件中的密钥
    
    params = {
        "auth_token": api_key,
        "limit": 5,
        "currencies": "BTC,ETH,SOL,BNB",
        "filter": "hot",
        "public": "true"
    }
    
    try:
        print(f"正在请求CryptoPanic API: {CRYPTOPANIC_API_URL}")
        print(f"参数: {params}")
        
        response = requests.get(CRYPTOPANIC_API_URL, params=params)
        print(f"状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("\n获取到的数据:")
            print(json.dumps(result, indent=2, ensure_ascii=False)[:500] + "...")  # 只打印前500个字符
            
            if "results" in result:
                news_list = result.get("results", [])
                print(f"\n获取到 {len(news_list)} 条新闻")
                
                for i, item in enumerate(news_list[:2]):  # 只打印前2条
                    print(f"\n新闻 {i+1}:")
                    print(f"标题: {item.get('title', '无标题')}")
                    
                    # 获取URL和来源
                    source = "CryptoPanic"
                    if "source" in item:
                        source_info = item.get("source", {})
                        source = source_info.get("title", "CryptoPanic")
                    
                    print(f"来源: {source}")
            else:
                print("API响应中没有'results'字段")
        else:
            print(f"API请求失败，状态码: {response.status_code}")
            print(f"响应内容: {response.text}")
    
    except Exception as e:
        print(f"测试API时出错: {e}")

if __name__ == "__main__":
    test_api()
