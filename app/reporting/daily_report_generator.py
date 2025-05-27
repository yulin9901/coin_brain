#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
每日报告生成器
汇总加密货币市场数据、交易策略、盈亏统计等信息
"""
import os
import sys
import datetime
import logging
import json
from typing import Dict, Any, List, Optional
from decimal import Decimal

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.database.db_manager import DatabaseManager

logger = logging.getLogger('daily_report_generator')

class DailyReportGenerator:
    """每日报告生成器"""

    def __init__(self, config, db_config):
        """初始化报告生成器

        Args:
            config: 配置对象
            db_config: 数据库配置
        """
        self.config = config
        self.db_config = db_config
        self.db_manager = DatabaseManager(db_config)
        self.trading_pairs = getattr(config, 'TRADING_PAIRS', [])

    def generate_daily_report(self, target_date: Optional[str] = None) -> Dict[str, Any]:
        """生成每日报告

        Args:
            target_date: 目标日期，格式为YYYY-MM-DD，默认为今天

        Returns:
            Dict: 包含所有报告数据的字典
        """
        if target_date is None:
            target_date = datetime.date.today().strftime('%Y-%m-%d')

        logger.info(f"开始生成 {target_date} 的每日报告")

        report_data = {
            'date': target_date,
            'generated_at': datetime.datetime.now().isoformat()
        }

        try:
            # 生成市场概况
            if getattr(self.config, 'REPORT_INCLUDE_MARKET_SUMMARY', True):
                report_data['market_summary'] = self._generate_market_summary(target_date)

            # 生成表现最佳币种
            if getattr(self.config, 'REPORT_INCLUDE_TOP_PERFORMERS', True):
                report_data['top_performers'] = self._generate_top_performers(target_date)

            # 生成交易策略
            if getattr(self.config, 'REPORT_INCLUDE_TRADING_STRATEGY', True):
                report_data['trading_strategy'] = self._generate_trading_strategy(target_date)

            # 生成盈亏统计
            if getattr(self.config, 'REPORT_INCLUDE_PROFIT_LOSS', True):
                report_data['profit_loss'] = self._generate_profit_loss(target_date)

            # 生成新闻摘要
            if getattr(self.config, 'REPORT_INCLUDE_NEWS_SUMMARY', True):
                report_data['news_summary'] = self._generate_news_summary(target_date)

            logger.info(f"成功生成 {target_date} 的每日报告")
            return report_data

        except Exception as e:
            logger.error(f"生成每日报告时出错: {e}")
            return report_data

    def _generate_market_summary(self, target_date: str) -> Dict[str, Any]:
        """生成市场概况"""
        logger.info("生成市场概况...")

        try:
            with self.db_manager.get_connection(dictionary=True) as (connection, cursor):
                # 获取主要币种的24小时变化
                # 从market_fund_flows表获取数据，因为这个表存在
                query = """
                SELECT
                    crypto_symbol as symbol,
                    change_rate as price_change_percent_24h,
                    volume_24h,
                    inflow_amount
                FROM market_fund_flows
                WHERE DATE(timestamp) = %s
                AND crypto_symbol IN ({})
                ORDER BY timestamp DESC
                """.format(','.join(['%s'] * len(self.trading_pairs)))

                # 提取交易对的基础币种符号（去掉USDT后缀）
                crypto_symbols = [pair.replace('USDT', '') for pair in self.trading_pairs]
                cursor.execute(query, [target_date] + crypto_symbols)
                market_data = cursor.fetchall()

                if not market_data:
                    return {'error': '无市场数据'}

                # 计算整体趋势
                positive_changes = sum(1 for data in market_data if data.get('price_change_percent_24h', 0) > 0)
                total_coins = len(market_data)

                if positive_changes / total_coins > 0.6:
                    overall_trend = 'bullish'
                elif positive_changes / total_coins < 0.4:
                    overall_trend = 'bearish'
                else:
                    overall_trend = 'neutral'

                # 计算总市值（如果有数据）
                total_market_cap = sum(data.get('market_cap', 0) for data in market_data if data.get('market_cap'))

                # 计算BTC占比
                btc_data = next((data for data in market_data if 'BTC' in data.get('symbol', '')), None)
                btc_dominance = 0
                if btc_data and btc_data.get('market_cap') and total_market_cap > 0:
                    btc_dominance = (btc_data['market_cap'] / total_market_cap) * 100

                return {
                    'overall_trend': overall_trend,
                    'total_market_cap': total_market_cap,
                    'btc_dominance': btc_dominance,
                    'positive_coins': positive_changes,
                    'total_coins': total_coins,
                    'market_data_count': len(market_data)
                }

        except Exception as e:
            logger.error(f"生成市场概况时出错: {e}")
            return {'error': str(e)}

    def _generate_top_performers(self, target_date: str) -> Dict[str, Any]:
        """生成表现最佳币种"""
        logger.info("生成表现最佳币种...")

        try:
            with self.db_manager.get_connection(dictionary=True) as (connection, cursor):
                # 获取24小时涨跌幅数据
                query = """
                SELECT
                    crypto_symbol as symbol,
                    change_rate as change_24h,
                    volume_24h,
                    inflow_amount
                FROM market_fund_flows
                WHERE DATE(timestamp) = %s
                AND crypto_symbol IN ({})
                AND change_rate IS NOT NULL
                ORDER BY change_rate DESC
                """.format(','.join(['%s'] * len(self.trading_pairs)))

                # 提取交易对的基础币种符号（去掉USDT后缀）
                crypto_symbols = [pair.replace('USDT', '') for pair in self.trading_pairs]
                cursor.execute(query, [target_date] + crypto_symbols)
                performance_data = cursor.fetchall()

                if not performance_data:
                    return {'error': '无表现数据'}

                # 分离涨幅和跌幅
                gainers = [data for data in performance_data if data['change_24h'] > 0]
                losers = [data for data in performance_data if data['change_24h'] < 0]
                losers.reverse()  # 跌幅从大到小排序

                return {
                    'gainers': gainers[:10],  # 前10名涨幅
                    'losers': losers[:10],    # 前10名跌幅
                    'total_gainers': len(gainers),
                    'total_losers': len(losers)
                }

        except Exception as e:
            logger.error(f"生成表现最佳币种时出错: {e}")
            return {'error': str(e)}

    def _generate_trading_strategy(self, target_date: str) -> Dict[str, Any]:
        """生成交易策略"""
        logger.info("生成交易策略...")

        try:
            with self.db_manager.get_connection(dictionary=True) as (connection, cursor):
                # 获取最新的交易策略
                query = """
                SELECT
                    crypto_symbol as symbol,
                    position_type as action,
                    position_size_percentage as confidence_score,
                    reasoning,
                    entry_price_suggestion as target_price,
                    stop_loss_price as stop_loss,
                    decision_timestamp as created_at
                FROM trading_strategies
                WHERE DATE(decision_timestamp) = %s
                ORDER BY position_size_percentage DESC, decision_timestamp DESC
                """

                cursor.execute(query, (target_date,))
                strategies = cursor.fetchall()

                if not strategies:
                    return {'error': '无交易策略数据'}

                # 统计策略分布
                buy_count = sum(1 for s in strategies if s.get('action') == 'BUY')
                sell_count = sum(1 for s in strategies if s.get('action') == 'SELL')
                hold_count = sum(1 for s in strategies if s.get('action') == 'HOLD')

                # 计算平均置信度
                avg_confidence = sum(s.get('confidence_score', 0) for s in strategies) / len(strategies) if strategies else 0

                # 确定风险等级
                if avg_confidence > 0.8:
                    risk_level = '低风险'
                elif avg_confidence > 0.6:
                    risk_level = '中等风险'
                else:
                    risk_level = '高风险'

                return {
                    'recommendations': strategies[:5],  # 前5个推荐
                    'strategy_distribution': {
                        'buy': buy_count,
                        'sell': sell_count,
                        'hold': hold_count
                    },
                    'average_confidence': avg_confidence,
                    'risk_level': risk_level,
                    'total_strategies': len(strategies)
                }

        except Exception as e:
            logger.error(f"生成交易策略时出错: {e}")
            return {'error': str(e)}

    def _generate_profit_loss(self, target_date: str) -> Dict[str, Any]:
        """生成盈亏统计"""
        logger.info("生成盈亏统计...")

        try:
            with self.db_manager.get_connection(dictionary=True) as (connection, cursor):
                # 获取每日盈亏数据
                query = """
                SELECT
                    total_realized_profit_loss,
                    total_unrealized_profit_loss,
                    total_fees_paid,
                    portfolio_value
                FROM daily_profit_loss
                WHERE date = %s
                """

                cursor.execute(query, (target_date,))
                pnl_data = cursor.fetchone()

                if not pnl_data:
                    return {'error': '无盈亏数据'}

                # 计算总盈亏
                total_pnl = (pnl_data.get('total_realized_profit_loss', 0) +
                           pnl_data.get('total_unrealized_profit_loss', 0))

                return {
                    'realized_pnl': float(pnl_data.get('total_realized_profit_loss', 0)),
                    'unrealized_pnl': float(pnl_data.get('total_unrealized_profit_loss', 0)),
                    'total_pnl': float(total_pnl),
                    'total_fees': float(pnl_data.get('total_fees_paid', 0)),
                    'portfolio_value': float(pnl_data.get('portfolio_value', 0))
                }

        except Exception as e:
            logger.error(f"生成盈亏统计时出错: {e}")
            return {'error': str(e)}

    def _generate_news_summary(self, target_date: str) -> Dict[str, Any]:
        """生成新闻摘要"""
        logger.info("生成新闻摘要...")

        try:
            with self.db_manager.get_connection(dictionary=True) as (connection, cursor):
                # 获取热点新闻
                query = """
                SELECT
                    title,
                    content_summary as summary,
                    CASE
                        WHEN sentiment = 'positive' THEN 0.8
                        WHEN sentiment = 'negative' THEN 0.2
                        ELSE 0.5
                    END as sentiment_score,
                    source,
                    timestamp as published_at
                FROM hot_topics
                WHERE DATE(timestamp) = %s
                ORDER BY timestamp DESC
                LIMIT 10
                """

                cursor.execute(query, (target_date,))
                news_data = cursor.fetchall()

                if not news_data:
                    return {'error': '无新闻数据'}

                # 计算平均情绪分数
                avg_sentiment = sum(news.get('sentiment_score', 0) for news in news_data) / len(news_data) if news_data else 0

                # 确定市场情绪
                if avg_sentiment > 0.6:
                    market_sentiment = '积极'
                elif avg_sentiment > 0.4:
                    market_sentiment = '中性'
                else:
                    market_sentiment = '消极'

                return {
                    'hot_topics': news_data,
                    'average_sentiment': avg_sentiment,
                    'market_sentiment': market_sentiment,
                    'total_news': len(news_data)
                }

        except Exception as e:
            logger.error(f"生成新闻摘要时出错: {e}")
            return {'error': str(e)}

# 测试代码
if __name__ == "__main__":
    from app.utils import load_config, get_db_config

    try:
        config = load_config()
        db_config = get_db_config(config)

        generator = DailyReportGenerator(config, db_config)
        report = generator.generate_daily_report()

        print("生成的报告数据:")
        print(json.dumps(report, indent=2, ensure_ascii=False, default=str))

    except Exception as e:
        print(f"测试失败: {e}")
