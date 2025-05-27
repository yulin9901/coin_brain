#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
数据清理和保留策略模块
负责清理旧数据、维护数据库性能和实施数据保留策略
"""
import os
import sys
import datetime
import logging
from typing import Dict, Any, Optional

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.database.db_manager import DatabaseManager

# 配置日志
logger = logging.getLogger('data_cleanup')

class DataCleanupManager:
    """数据清理管理器"""
    
    def __init__(self, db_config: Dict[str, Any]):
        """
        初始化数据清理管理器
        
        Args:
            db_config (Dict[str, Any]): 数据库配置
        """
        self.db_manager = DatabaseManager(db_config)
        
    def cleanup_old_hot_topics(self, retention_days: int = 30) -> int:
        """
        清理旧的热点话题数据
        
        Args:
            retention_days (int): 数据保留天数，默认30天
            
        Returns:
            int: 删除的记录数
        """
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
            
            delete_sql = """
            DELETE FROM hot_topics 
            WHERE retrieved_at < %s
            """
            
            deleted_count = self.db_manager.execute_update(
                delete_sql, 
                (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),)
            )
            
            logger.info(f"清理了{deleted_count}条超过{retention_days}天的热点话题数据")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理热点话题数据时出错: {e}")
            return 0
    
    def cleanup_old_market_flows(self, retention_days: int = 7) -> int:
        """
        清理旧的市场资金流向数据
        
        Args:
            retention_days (int): 数据保留天数，默认7天
            
        Returns:
            int: 删除的记录数
        """
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
            
            delete_sql = """
            DELETE FROM market_fund_flows 
            WHERE retrieved_at < %s
            """
            
            deleted_count = self.db_manager.execute_update(
                delete_sql, 
                (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),)
            )
            
            logger.info(f"清理了{deleted_count}条超过{retention_days}天的市场资金流向数据")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理市场资金流向数据时出错: {e}")
            return 0
    
    def cleanup_old_kline_data(self, retention_days: int = 30) -> int:
        """
        清理旧的K线数据
        
        Args:
            retention_days (int): 数据保留天数，默认30天
            
        Returns:
            int: 删除的记录数
        """
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
            
            delete_sql = """
            DELETE FROM kline_data 
            WHERE retrieved_at < %s
            """
            
            deleted_count = self.db_manager.execute_update(
                delete_sql, 
                (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),)
            )
            
            logger.info(f"清理了{deleted_count}条超过{retention_days}天的K线数据")
            return deleted_count
            
        except Exception as e:
            logger.error(f"清理K线数据时出错: {e}")
            return 0
    
    def archive_old_data(self, table_name: str, retention_days: int = 90) -> int:
        """
        将旧数据归档到归档表
        
        Args:
            table_name (str): 源表名
            retention_days (int): 数据保留天数，默认90天
            
        Returns:
            int: 归档的记录数
        """
        try:
            cutoff_date = datetime.datetime.now() - datetime.timedelta(days=retention_days)
            archive_table = f"{table_name}_archive"
            
            # 创建归档表（如果不存在）
            create_archive_sql = f"""
            CREATE TABLE IF NOT EXISTS {archive_table} LIKE {table_name}
            """
            self.db_manager.execute_update(create_archive_sql)
            
            # 将旧数据插入归档表
            archive_sql = f"""
            INSERT INTO {archive_table} 
            SELECT * FROM {table_name} 
            WHERE retrieved_at < %s
            """
            
            archived_count = self.db_manager.execute_update(
                archive_sql, 
                (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),)
            )
            
            # 从原表删除已归档的数据
            if archived_count > 0:
                delete_sql = f"""
                DELETE FROM {table_name} 
                WHERE retrieved_at < %s
                """
                
                deleted_count = self.db_manager.execute_update(
                    delete_sql, 
                    (cutoff_date.strftime("%Y-%m-%d %H:%M:%S"),)
                )
                
                logger.info(f"归档了{archived_count}条{table_name}数据，删除了{deleted_count}条原始数据")
            
            return archived_count
            
        except Exception as e:
            logger.error(f"归档{table_name}数据时出错: {e}")
            return 0
    
    def get_table_statistics(self) -> Dict[str, Dict[str, Any]]:
        """
        获取各表的统计信息
        
        Returns:
            Dict[str, Dict[str, Any]]: 表统计信息
        """
        stats = {}
        tables = ['hot_topics', 'market_fund_flows', 'kline_data', 'daily_summary']
        
        try:
            for table in tables:
                # 获取记录总数
                count_sql = f"SELECT COUNT(*) as count FROM {table}"
                count_result = self.db_manager.execute_query(count_sql, dictionary=True)
                total_count = count_result[0]['count'] if count_result else 0
                
                # 获取最早和最新的记录时间
                time_sql = f"""
                SELECT 
                    MIN(retrieved_at) as earliest,
                    MAX(retrieved_at) as latest
                FROM {table}
                """
                time_result = self.db_manager.execute_query(time_sql, dictionary=True)
                
                stats[table] = {
                    'total_records': total_count,
                    'earliest_record': time_result[0]['earliest'] if time_result and time_result[0]['earliest'] else None,
                    'latest_record': time_result[0]['latest'] if time_result and time_result[0]['latest'] else None
                }
                
        except Exception as e:
            logger.error(f"获取表统计信息时出错: {e}")
            
        return stats
    
    def perform_full_cleanup(self, 
                           hot_topics_retention: int = 30,
                           market_flows_retention: int = 7,
                           kline_retention: int = 30) -> Dict[str, int]:
        """
        执行完整的数据清理
        
        Args:
            hot_topics_retention (int): 热点话题保留天数
            market_flows_retention (int): 市场流向保留天数
            kline_retention (int): K线数据保留天数
            
        Returns:
            Dict[str, int]: 各表清理的记录数
        """
        logger.info("开始执行完整数据清理...")
        
        cleanup_results = {}
        
        # 清理热点话题
        cleanup_results['hot_topics'] = self.cleanup_old_hot_topics(hot_topics_retention)
        
        # 清理市场资金流向
        cleanup_results['market_fund_flows'] = self.cleanup_old_market_flows(market_flows_retention)
        
        # 清理K线数据
        cleanup_results['kline_data'] = self.cleanup_old_kline_data(kline_retention)
        
        total_cleaned = sum(cleanup_results.values())
        logger.info(f"数据清理完成，总共清理了{total_cleaned}条记录")
        
        return cleanup_results


def cleanup_old_data(db_config: Dict[str, Any], 
                    hot_topics_retention: int = 30,
                    market_flows_retention: int = 7,
                    kline_retention: int = 30) -> Dict[str, int]:
    """
    清理旧数据的便捷函数
    
    Args:
        db_config (Dict[str, Any]): 数据库配置
        hot_topics_retention (int): 热点话题保留天数
        market_flows_retention (int): 市场流向保留天数
        kline_retention (int): K线数据保留天数
        
    Returns:
        Dict[str, int]: 各表清理的记录数
    """
    cleanup_manager = DataCleanupManager(db_config)
    return cleanup_manager.perform_full_cleanup(
        hot_topics_retention,
        market_flows_retention,
        kline_retention
    )


if __name__ == "__main__":
    # 测试数据清理功能
    from app.utils import load_config, get_db_config
    
    try:
        config = load_config()
        db_config = get_db_config(config)
        
        cleanup_manager = DataCleanupManager(db_config)
        
        # 获取统计信息
        print("数据库表统计信息:")
        stats = cleanup_manager.get_table_statistics()
        for table, info in stats.items():
            print(f"{table}: {info['total_records']}条记录")
            if info['earliest_record']:
                print(f"  最早记录: {info['earliest_record']}")
            if info['latest_record']:
                print(f"  最新记录: {info['latest_record']}")
        
        # 执行清理（测试模式，保留更多数据）
        print("\n执行数据清理...")
        results = cleanup_manager.perform_full_cleanup(
            hot_topics_retention=60,  # 保留60天的热点话题
            market_flows_retention=14,  # 保留14天的市场流向
            kline_retention=60  # 保留60天的K线数据
        )
        
        print("清理结果:")
        for table, count in results.items():
            print(f"{table}: 清理了{count}条记录")
            
    except Exception as e:
        print(f"测试数据清理功能时出错: {e}")
