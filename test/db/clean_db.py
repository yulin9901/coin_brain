#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.database.db_manager import DatabaseManager
from app.utils import load_config, get_db_config

def clean_database():
    """清除旧的市场资金流向数据"""
    config = load_config()
    db_config = get_db_config(config)
    db = DatabaseManager(db_config)

    # 清除所有市场资金流向数据
    deleted_count = db.execute_update("DELETE FROM market_fund_flows")
    print(f"已删除 {deleted_count} 条市场资金流向数据")

    # 清除所有热点话题数据
    deleted_count = db.execute_update("DELETE FROM hot_topics")
    print(f"已删除 {deleted_count} 条热点话题数据")

    # 清除旧的每日摘要数据
    deleted_count = db.execute_update('DELETE FROM daily_summary')
    print(f"已删除 {deleted_count} 条旧的每日摘要数据")

if __name__ == "__main__":
    clean_database()
