#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from app.database.db_manager import DatabaseManager
from app.utils import load_config, get_db_config

def check_database():
    config = load_config()
    db_config = get_db_config(config)
    db = DatabaseManager(db_config)
    
    print("Database config:", db_config)
    
    # Check hot_topics table
    try:
        results = db.execute_query('SELECT COUNT(*) as count FROM hot_topics', dictionary=True)
        print('Hot topics count:', results[0]['count'] if results else 0)
        
        if results and results[0]['count'] > 0:
            sample = db.execute_query('SELECT * FROM hot_topics LIMIT 1', dictionary=True)
            print('Sample hot topic:', sample[0] if sample else None)
    except Exception as e:
        print('Error querying hot_topics:', e)
    
    # Check market_fund_flows table
    try:
        results = db.execute_query('SELECT COUNT(*) as count FROM market_fund_flows', dictionary=True)
        print('Market fund flows count:', results[0]['count'] if results else 0)
        
        if results and results[0]['count'] > 0:
            sample = db.execute_query('SELECT * FROM market_fund_flows LIMIT 1', dictionary=True)
            print('Sample market fund flow:', sample[0] if sample else None)
    except Exception as e:
        print('Error querying market_fund_flows:', e)
    
    # Check daily_summary table
    try:
        results = db.execute_query('SELECT * FROM daily_summary ORDER BY date DESC', dictionary=True)
        print('Daily summaries count:', len(results))
        
        if results:
            for summary in results:
                print(f"Summary for {summary['date']}:")
                print(f"  Hot topics: {summary['aggregated_hot_topics_summary']}")
                print(f"  Fund flows: {summary['aggregated_fund_flow_summary']}")
    except Exception as e:
        print('Error querying daily_summary:', e)

if __name__ == "__main__":
    check_database()
