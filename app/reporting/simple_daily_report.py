#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
简化版每日报告生成器
专门用于微信推送，避免复杂的数据库查询
"""
import os
import sys
import datetime
import logging
from typing import Dict, Any

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.database.db_manager import DatabaseManager

logger = logging.getLogger('simple_daily_report')

class SimpleDailyReportGenerator:
    """简化版每日报告生成器"""
    
    def __init__(self, config, db_config):
        """初始化报告生成器
        
        Args:
            config: 配置对象
            db_config: 数据库配置
        """
        self.config = config
        self.db_config = db_config
        self.db_manager = DatabaseManager(db_config)
    
    def generate_simple_report(self, target_date: str = None) -> Dict[str, Any]:
        """生成简化版每日报告
        
        Args:
            target_date: 目标日期，格式为YYYY-MM-DD，默认为今天
            
        Returns:
            Dict: 包含报告数据的字典
        """
        if target_date is None:
            target_date = datetime.date.today().strftime('%Y-%m-%d')
        
        logger.info(f"开始生成 {target_date} 的简化版每日报告")
        
        report_data = {
            'date': target_date,
            'generated_at': datetime.datetime.now().isoformat()
        }
        
        try:
            # 生成市场概况
            report_data['market_summary'] = self._get_market_summary(target_date)
            
            # 生成新闻摘要
            report_data['news_summary'] = self._get_news_summary(target_date)
            
            # 生成系统状态
            report_data['system_status'] = self._get_system_status()
            
            logger.info(f"成功生成 {target_date} 的简化版每日报告")
            return report_data
            
        except Exception as e:
            logger.error(f"生成简化版每日报告时出错: {e}")
            # 返回基础报告
            return {
                'date': target_date,
                'generated_at': datetime.datetime.now().isoformat(),
                'market_summary': {'status': '数据收集中'},
                'news_summary': {'status': '新闻收集中'},
                'system_status': {'status': '系统运行正常'}
            }
    
    def _get_market_summary(self, target_date: str) -> Dict[str, Any]:
        """获取市场概况"""
        try:
            with self.db_manager.get_connection(dictionary=True) as (connection, cursor):
                # 检查是否有市场数据
                query = """
                SELECT COUNT(*) as count
                FROM market_fund_flows 
                WHERE DATE(timestamp) = %s
                """
                cursor.execute(query, (target_date,))
                result = cursor.fetchone()
                
                if result and result['count'] > 0:
                    return {
                        'status': '数据已收集',
                        'data_points': result['count'],
                        'overall_trend': 'neutral'
                    }
                else:
                    return {
                        'status': '暂无数据',
                        'data_points': 0,
                        'overall_trend': 'neutral'
                    }
                    
        except Exception as e:
            logger.error(f"获取市场概况时出错: {e}")
            return {'status': '数据获取失败', 'error': str(e)}
    
    def _get_news_summary(self, target_date: str) -> Dict[str, Any]:
        """获取新闻摘要"""
        try:
            with self.db_manager.get_connection(dictionary=True) as (connection, cursor):
                # 获取今日新闻数量和最新的几条
                query = """
                SELECT title, source, sentiment
                FROM hot_topics 
                WHERE DATE(timestamp) = %s 
                ORDER BY timestamp DESC
                LIMIT 5
                """
                cursor.execute(query, (target_date,))
                news_list = cursor.fetchall()
                
                if news_list:
                    # 统计情感分布
                    positive_count = sum(1 for news in news_list if news.get('sentiment') == 'positive')
                    negative_count = sum(1 for news in news_list if news.get('sentiment') == 'negative')
                    
                    return {
                        'total_news': len(news_list),
                        'positive_news': positive_count,
                        'negative_news': negative_count,
                        'hot_topics': [
                            {
                                'title': news['title'][:50] + '...' if len(news['title']) > 50 else news['title'],
                                'source': news['source'],
                                'sentiment': news['sentiment']
                            }
                            for news in news_list[:3]  # 只取前3条
                        ]
                    }
                else:
                    return {
                        'total_news': 0,
                        'status': '暂无新闻数据'
                    }
                    
        except Exception as e:
            logger.error(f"获取新闻摘要时出错: {e}")
            return {'status': '新闻获取失败', 'error': str(e)}
    
    def _get_system_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        try:
            # 检查数据库连接
            with self.db_manager.get_connection() as (connection, cursor):
                cursor.execute("SELECT 1")
                db_status = "正常"
        except Exception:
            db_status = "异常"
        
        # 检查配置状态
        config_status = "正常"
        if not hasattr(self.config, 'SERVERCHAN_SENDKEY') or not self.config.SERVERCHAN_SENDKEY:
            config_status = "微信推送未配置"
        
        return {
            'database': db_status,
            'config': config_status,
            'timestamp': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

# 测试代码
if __name__ == "__main__":
    from app.utils import load_config, get_db_config
    
    try:
        config = load_config()
        db_config = get_db_config(config)
        
        generator = SimpleDailyReportGenerator(config, db_config)
        report = generator.generate_simple_report()
        
        print("生成的简化报告数据:")
        import json
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))
        
    except Exception as e:
        print(f"测试失败: {e}")
