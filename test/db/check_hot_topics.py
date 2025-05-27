#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.database.db_manager import DatabaseManager
from app.utils import load_config, get_db_config

def check_hot_topics():
    """检查热点话题数据"""
    config = load_config()
    db_config = get_db_config(config)
    db = DatabaseManager(db_config)

    # 查询热点话题数据
    results = db.execute_query('SELECT id, title, content_summary FROM hot_topics', dictionary=True)

    print(f"热点话题数量: {len(results)}")
    print("\n热点话题内容摘要:")
    for row in results:
        print(f'ID: {row["id"]}, Title: {row["title"]}, Content Summary: "{row["content_summary"]}"')

if __name__ == "__main__":
    check_hot_topics()
