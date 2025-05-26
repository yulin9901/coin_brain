#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.database.db_manager import DatabaseManager
from app.utils import load_config, get_db_config

def check_hot_topics():
    """检查热点话题数据"""
    config = load_config()
    db_config = get_db_config(config)
    db = DatabaseManager(db_config)
    
    # 查询热点话题数据
    try:
        # 获取总数
        count_results = db.execute_query('SELECT COUNT(*) as count FROM hot_topics', dictionary=True)
        print(f"热点话题总数: {count_results[0]['count'] if count_results else 0}")
        
        # 获取最新的20条记录
        results = db.execute_query('''
            SELECT id, timestamp, source, title, url, content_summary, sentiment, retrieved_at 
            FROM hot_topics 
            ORDER BY retrieved_at DESC 
            LIMIT 20
        ''', dictionary=True)
        
        print("\n最新热点话题:")
        for row in results:
            print(f"\nID: {row['id']}")
            print(f"时间: {row['timestamp']}")
            print(f"来源: {row['source']}")
            print(f"标题: {row['title']}")
            print(f"URL: {row['url']}")
            print(f"内容摘要: {row['content_summary']}")
            print(f"情感: {row['sentiment']}")
            print(f"获取时间: {row['retrieved_at']}")
            print("-" * 50)
    except Exception as e:
        print(f"查询数据库时出错: {e}")

if __name__ == "__main__":
    check_hot_topics()
