#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
微信报告推送模块
使用Server酱服务将报告推送到微信
"""
import os
import sys
import requests
import logging
import datetime
from typing import Dict, Any, Optional

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

logger = logging.getLogger('wechat_reporter')

class WeChatReporter:
    """微信报告推送器"""
    
    def __init__(self, config):
        """初始化微信报告推送器
        
        Args:
            config: 配置对象，包含Server酱相关配置
        """
        self.config = config
        self.sendkey = getattr(config, 'SERVERCHAN_SENDKEY', '')
        self.enabled = getattr(config, 'ENABLE_WECHAT_REPORT', False)
        self.base_url = "https://sctapi.ftqq.com"
        
        if not self.sendkey or self.sendkey == "YOUR_SERVERCHAN_SENDKEY_HERE":
            logger.warning("Server酱SendKey未配置，微信推送功能将被禁用")
            self.enabled = False
    
    def send_message(self, title: str, content: str, channel: str = "9") -> bool:
        """发送消息到微信
        
        Args:
            title: 消息标题
            content: 消息内容（支持Markdown格式）
            channel: 推送渠道，默认为"9"（微信）
            
        Returns:
            bool: 发送是否成功
        """
        if not self.enabled:
            logger.info("微信推送功能已禁用，跳过发送")
            return False
            
        if not self.sendkey:
            logger.error("Server酱SendKey未配置")
            return False
        
        url = f"{self.base_url}/{self.sendkey}.send"
        
        data = {
            "title": title,
            "desp": content,
            "channel": channel
        }
        
        try:
            logger.info(f"正在发送微信消息: {title}")
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            
            result = response.json()
            if result.get("code") == 0:
                logger.info("微信消息发送成功")
                return True
            else:
                logger.error(f"微信消息发送失败: {result.get('message', '未知错误')}")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"发送微信消息时网络错误: {e}")
            return False
        except Exception as e:
            logger.error(f"发送微信消息时出错: {e}")
            return False
    
    def send_daily_report(self, report_data: Dict[str, Any]) -> bool:
        """发送每日报告
        
        Args:
            report_data: 报告数据字典
            
        Returns:
            bool: 发送是否成功
        """
        if not self.enabled:
            return False
        
        try:
            title = self._generate_report_title(report_data)
            content = self._generate_report_content(report_data)
            
            return self.send_message(title, content)
            
        except Exception as e:
            logger.error(f"生成每日报告时出错: {e}")
            return False
    
    def _generate_report_title(self, report_data: Dict[str, Any]) -> str:
        """生成报告标题"""
        base_title = getattr(self.config, 'WECHAT_REPORT_TITLE', 'CoinBrain每日报告')
        date_str = report_data.get('date', datetime.date.today().strftime('%Y-%m-%d'))
        
        # 添加市场趋势指示器
        market_trend = report_data.get('market_summary', {}).get('overall_trend', '')
        if market_trend:
            trend_emoji = {
                'bullish': '📈',
                'bearish': '📉',
                'neutral': '➡️'
            }.get(market_trend.lower(), '')
            return f"{trend_emoji} {base_title} - {date_str}"
        
        return f"{base_title} - {date_str}"
    
    def _generate_report_content(self, report_data: Dict[str, Any]) -> str:
        """生成报告内容（Markdown格式）"""
        content_parts = []
        
        # 报告时间
        report_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        content_parts.append(f"**报告时间**: {report_time}\n")
        
        # 市场概况
        if (getattr(self.config, 'REPORT_INCLUDE_MARKET_SUMMARY', True) and 
            'market_summary' in report_data):
            content_parts.append(self._format_market_summary(report_data['market_summary']))
        
        # 表现最佳币种
        if (getattr(self.config, 'REPORT_INCLUDE_TOP_PERFORMERS', True) and 
            'top_performers' in report_data):
            content_parts.append(self._format_top_performers(report_data['top_performers']))
        
        # 交易策略
        if (getattr(self.config, 'REPORT_INCLUDE_TRADING_STRATEGY', True) and 
            'trading_strategy' in report_data):
            content_parts.append(self._format_trading_strategy(report_data['trading_strategy']))
        
        # 盈亏统计
        if (getattr(self.config, 'REPORT_INCLUDE_PROFIT_LOSS', True) and 
            'profit_loss' in report_data):
            content_parts.append(self._format_profit_loss(report_data['profit_loss']))
        
        # 新闻摘要
        if (getattr(self.config, 'REPORT_INCLUDE_NEWS_SUMMARY', True) and 
            'news_summary' in report_data):
            content_parts.append(self._format_news_summary(report_data['news_summary']))
        
        return "\n---\n".join(content_parts)
    
    def _format_market_summary(self, market_data: Dict[str, Any]) -> str:
        """格式化市场概况"""
        content = ["## 📊 市场概况\n"]
        
        if 'overall_trend' in market_data:
            trend_text = {
                'bullish': '看涨 📈',
                'bearish': '看跌 📉',
                'neutral': '中性 ➡️'
            }.get(market_data['overall_trend'].lower(), market_data['overall_trend'])
            content.append(f"**整体趋势**: {trend_text}")
        
        if 'total_market_cap' in market_data:
            content.append(f"**总市值**: ${market_data['total_market_cap']:,.0f}")
        
        if 'btc_dominance' in market_data:
            content.append(f"**BTC占比**: {market_data['btc_dominance']:.1f}%")
        
        if 'fear_greed_index' in market_data:
            content.append(f"**恐慌贪婪指数**: {market_data['fear_greed_index']}")
        
        return "\n".join(content)
    
    def _format_top_performers(self, performers_data: Dict[str, Any]) -> str:
        """格式化表现最佳币种"""
        content = ["## 🏆 今日表现\n"]
        
        if 'gainers' in performers_data:
            content.append("**涨幅榜**:")
            for coin in performers_data['gainers'][:5]:  # 显示前5名
                content.append(f"• {coin['symbol']}: +{coin['change_24h']:.2f}%")
        
        if 'losers' in performers_data:
            content.append("\n**跌幅榜**:")
            for coin in performers_data['losers'][:5]:  # 显示前5名
                content.append(f"• {coin['symbol']}: {coin['change_24h']:.2f}%")
        
        return "\n".join(content)
    
    def _format_trading_strategy(self, strategy_data: Dict[str, Any]) -> str:
        """格式化交易策略"""
        content = ["## 💡 交易策略\n"]
        
        if 'recommendations' in strategy_data:
            for rec in strategy_data['recommendations'][:3]:  # 显示前3个推荐
                action_emoji = {'BUY': '🟢', 'SELL': '🔴', 'HOLD': '🟡'}.get(rec.get('action', ''), '')
                content.append(f"{action_emoji} **{rec.get('symbol', '')}**: {rec.get('action', '')} - {rec.get('reason', '')}")
        
        if 'risk_level' in strategy_data:
            content.append(f"\n**风险等级**: {strategy_data['risk_level']}")
        
        return "\n".join(content)
    
    def _format_profit_loss(self, pnl_data: Dict[str, Any]) -> str:
        """格式化盈亏统计"""
        content = ["## 💰 盈亏统计\n"]
        
        if 'realized_pnl' in pnl_data:
            pnl_emoji = '📈' if pnl_data['realized_pnl'] >= 0 else '📉'
            content.append(f"{pnl_emoji} **已实现盈亏**: ${pnl_data['realized_pnl']:.2f}")
        
        if 'unrealized_pnl' in pnl_data:
            pnl_emoji = '📈' if pnl_data['unrealized_pnl'] >= 0 else '📉'
            content.append(f"{pnl_emoji} **未实现盈亏**: ${pnl_data['unrealized_pnl']:.2f}")
        
        if 'portfolio_value' in pnl_data:
            content.append(f"💼 **组合价值**: ${pnl_data['portfolio_value']:.2f}")
        
        if 'total_fees' in pnl_data:
            content.append(f"💸 **交易费用**: ${pnl_data['total_fees']:.2f}")
        
        return "\n".join(content)
    
    def _format_news_summary(self, news_data: Dict[str, Any]) -> str:
        """格式化新闻摘要"""
        content = ["## 📰 热点新闻\n"]
        
        if 'hot_topics' in news_data:
            for i, topic in enumerate(news_data['hot_topics'][:3], 1):  # 显示前3条
                content.append(f"{i}. {topic.get('title', '')}")
                if topic.get('summary'):
                    content.append(f"   {topic['summary'][:100]}...")
        
        return "\n".join(content)

# 测试代码
if __name__ == "__main__":
    # 测试微信推送功能
    from app.utils import load_config
    
    try:
        config = load_config()
        reporter = WeChatReporter(config)
        
        # 测试数据
        test_data = {
            'date': '2024-01-15',
            'market_summary': {
                'overall_trend': 'bullish',
                'total_market_cap': 1500000000000,
                'btc_dominance': 42.5
            },
            'top_performers': {
                'gainers': [
                    {'symbol': 'BTC', 'change_24h': 5.2},
                    {'symbol': 'ETH', 'change_24h': 3.8}
                ]
            }
        }
        
        success = reporter.send_daily_report(test_data)
        print(f"测试报告发送{'成功' if success else '失败'}")
        
    except Exception as e:
        print(f"测试失败: {e}")
