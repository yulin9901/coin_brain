#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
测试CoinMarketCal API
"""
import os
import sys
import requests
import json
import datetime

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.utils import load_config

def test_coinmarketcal_api():
    """测试CoinMarketCal API"""
    print("🔍 测试CoinMarketCal API")
    print("=" * 50)
    
    try:
        # 加载配置
        config = load_config()
        
        api_key = getattr(config, 'COINMARKETCAL_API_KEY', '')
        x_api_key = getattr(config, 'COINMARKETCAL_X_API_KEY', '')
        
        print(f"API Key: {api_key[:10]}..." if api_key else "API Key: 未设置")
        print(f"X-API-Key: {x_api_key[:10]}..." if x_api_key else "X-API-Key: 未设置")
        
        if not api_key or not x_api_key:
            print("❌ API密钥未配置")
            return False
        
        # 测试不同的API参数组合
        test_cases = [
            {
                "name": "原始参数",
                "params": {
                    "max": 30,
                    "dateRangeStart": datetime.date.today().strftime("%Y-%m-%d"),
                    "dateRangeEnd": (datetime.date.today() + datetime.timedelta(days=30)).strftime("%Y-%m-%d"),
                    "showOnly": "hot",
                    "sortBy": "created_desc"
                }
            },
            {
                "name": "简化参数",
                "params": {
                    "max": 10
                }
            },
            {
                "name": "无过滤参数",
                "params": {
                    "max": 5,
                    "dateRangeStart": datetime.date.today().strftime("%Y-%m-%d"),
                    "dateRangeEnd": (datetime.date.today() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")
                }
            }
        ]
        
        base_url = "https://developers.coinmarketcal.com/v1/events"
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n📋 测试 {i}: {test_case['name']}")
            print("-" * 30)
            
            headers = {
                "x-api-key": x_api_key,
                "Accept-Encoding": "gzip",
                "Accept": "application/json"
            }
            
            print(f"请求URL: {base_url}")
            print(f"请求参数: {test_case['params']}")
            print(f"请求头: {headers}")
            
            try:
                response = requests.get(base_url, headers=headers, params=test_case['params'], timeout=10)
                
                print(f"响应状态码: {response.status_code}")
                print(f"响应头: {dict(response.headers)}")
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        print(f"✅ 成功获取数据")
                        print(f"响应结构: {list(result.keys()) if isinstance(result, dict) else type(result)}")
                        
                        if isinstance(result, dict) and "body" in result:
                            events = result.get("body", [])
                            print(f"获取到 {len(events)} 个事件")
                            
                            if events:
                                print("第一个事件示例:")
                                first_event = events[0]
                                print(json.dumps(first_event, indent=2, ensure_ascii=False))
                        
                        return True
                        
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON解析失败: {e}")
                        print(f"响应内容: {response.text[:500]}...")
                        
                else:
                    print(f"❌ 请求失败: {response.status_code}")
                    print(f"错误信息: {response.text}")
                    
            except requests.exceptions.RequestException as e:
                print(f"❌ 网络请求失败: {e}")
        
        return False
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_alternative_endpoints():
    """测试替代的API端点"""
    print("\n🔄 测试替代API端点")
    print("=" * 50)
    
    try:
        config = load_config()
        x_api_key = getattr(config, 'COINMARKETCAL_X_API_KEY', '')
        
        if not x_api_key:
            print("❌ X-API-Key未配置")
            return False
        
        # 测试不同的端点
        endpoints = [
            "https://api.coinmarketcal.com/v1/events",
            "https://coinmarketcal.com/api/v1/events",
            "https://developers.coinmarketcal.com/v1/categories"
        ]
        
        headers = {
            "x-api-key": x_api_key,
            "Accept": "application/json"
        }
        
        for endpoint in endpoints:
            print(f"\n📡 测试端点: {endpoint}")
            try:
                response = requests.get(endpoint, headers=headers, timeout=10)
                print(f"状态码: {response.status_code}")
                
                if response.status_code == 200:
                    print("✅ 端点可用")
                    try:
                        result = response.json()
                        print(f"响应结构: {list(result.keys()) if isinstance(result, dict) else type(result)}")
                    except:
                        print("响应不是JSON格式")
                else:
                    print(f"❌ 端点不可用: {response.text[:200]}")
                    
            except Exception as e:
                print(f"❌ 请求失败: {e}")
        
    except Exception as e:
        print(f"❌ 测试失败: {e}")

def main():
    """主函数"""
    print("🧪 CoinMarketCal API 测试工具")
    print("=" * 60)
    
    # 测试主要API
    success = test_coinmarketcal_api()
    
    # 如果主要API失败，测试替代端点
    if not success:
        test_alternative_endpoints()
    
    print("\n" + "=" * 60)
    print("💡 建议:")
    print("1. 检查API密钥是否有效")
    print("2. 确认API配额是否用完")
    print("3. 查看CoinMarketCal官方文档是否有更新")
    print("4. 考虑使用其他新闻源作为备选")

if __name__ == "__main__":
    main()
