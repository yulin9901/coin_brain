#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
微信报告推送模块
使用Server酱服务将报告推送到微信
"""
import os
import sys
import time
import requests
import logging
import datetime
from typing import Dict, Any, Optional

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.reporting.wechat_limit_manager import WeChatLimitManager

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

        # 初始化限制管理器
        self.limit_manager = WeChatLimitManager(config)

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

        # 获取重试配置
        retry_times = getattr(self.config, 'WECHAT_RETRY_TIMES', 3)
        retry_delay = getattr(self.config, 'WECHAT_RETRY_DELAY', 5)
        timeout = getattr(self.config, 'WECHAT_TIMEOUT', 30)

        url = f"{self.base_url}/{self.sendkey}.send"

        data = {
            "title": title,
            "desp": content,
            "channel": channel
        }

        # 重试发送
        for attempt in range(retry_times):
            try:
                if attempt > 0:
                    logger.info(f"第 {attempt + 1} 次尝试发送微信消息: {title}")
                else:
                    logger.info(f"正在发送微信消息: {title}")

                response = requests.post(url, data=data, timeout=timeout)
                response.raise_for_status()

                result = response.json()
                if result.get("code") == 0:
                    logger.info("微信消息发送成功")
                    return True
                else:
                    error_msg = result.get('message', '未知错误')
                    logger.error(f"微信消息发送失败: {error_msg}")

                    # 如果是配置错误，不需要重试
                    if "invalid" in error_msg.lower() or "unauthorized" in error_msg.lower():
                        logger.error("SendKey配置错误，停止重试")
                        return False

                    # 其他错误继续重试
                    if attempt < retry_times - 1:
                        logger.info(f"等待 {retry_delay} 秒后重试...")
                        time.sleep(retry_delay)

            except requests.exceptions.Timeout:
                logger.error(f"发送微信消息超时 (超时时间: {timeout}秒)")
                if attempt < retry_times - 1:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)

            except requests.exceptions.RequestException as e:
                logger.error(f"发送微信消息时网络错误: {e}")
                if attempt < retry_times - 1:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)

            except Exception as e:
                logger.error(f"发送微信消息时出错: {e}")
                if attempt < retry_times - 1:
                    logger.info(f"等待 {retry_delay} 秒后重试...")
                    time.sleep(retry_delay)

        logger.error(f"微信消息发送失败，已重试 {retry_times} 次")
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

    def send_simple_daily_report(self, report_data: Dict[str, Any]) -> bool:
        """发送简化版每日报告

        Args:
            report_data: 简化报告数据字典

        Returns:
            bool: 发送是否成功
        """
        if not self.enabled:
            return False

        # 检查发送限制
        if not self.limit_manager.can_send_message("daily_report"):
            logger.info("受发送限制约束，跳过每日报告发送")
            return False

        try:
            title = self._generate_simple_report_title(report_data)
            content = self._generate_simple_report_content(report_data)

            success = self.send_message(title, content)

            # 记录发送结果
            self.limit_manager.record_sent_message("daily_report", title, success)

            return success

        except Exception as e:
            logger.error(f"生成简化每日报告时出错: {e}")
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

        full_content = "\n---\n".join(content_parts)

        # 限制内容长度，Server酱有字符限制
        max_length = 1500  # Server酱推荐的最大长度
        if len(full_content) > max_length:
            full_content = full_content[:max_length-3] + "..."

        return full_content

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
                title = topic.get('title', '')[:50]  # 限制标题长度
                content.append(f"{i}. {title}")
                if topic.get('summary'):
                    summary = topic['summary'][:60]  # 限制摘要长度
                    content.append(f"   {summary}...")

        return "\n".join(content)

    def _generate_simple_report_title(self, report_data: Dict[str, Any]) -> str:
        """生成简化报告标题"""
        base_title = getattr(self.config, 'WECHAT_REPORT_TITLE', 'CoinBrain每日报告')
        date_str = report_data.get('date', datetime.date.today().strftime('%Y-%m-%d'))
        return f"📊 {base_title} - {date_str}"

    def _generate_simple_report_content(self, report_data: Dict[str, Any]) -> str:
        """生成简化报告内容"""
        content_parts = []

        # 报告时间
        report_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        content_parts.append(f"**报告时间**: {report_time}")

        # 系统状态
        if 'system_status' in report_data:
            system_status = report_data['system_status']
            content_parts.append(f"**系统状态**: {system_status.get('database', '未知')}")

        # 市场概况
        if 'market_summary' in report_data:
            market_summary = report_data['market_summary']
            if 'data_points' in market_summary:
                content_parts.append(f"**市场数据**: 已收集 {market_summary['data_points']} 个数据点")
            else:
                content_parts.append(f"**市场数据**: {market_summary.get('status', '未知')}")

        # 新闻摘要
        if 'news_summary' in report_data:
            news_summary = report_data['news_summary']
            if 'total_news' in news_summary and news_summary['total_news'] > 0:
                content_parts.append(f"**今日新闻**: {news_summary['total_news']} 条")

                # 显示前2条新闻标题
                if 'hot_topics' in news_summary:
                    content_parts.append("**热点新闻**:")
                    for i, topic in enumerate(news_summary['hot_topics'][:2], 1):
                        title = topic.get('title', '')[:40]  # 限制长度
                        sentiment_emoji = {'positive': '📈', 'negative': '📉', 'neutral': '➡️'}.get(topic.get('sentiment', 'neutral'), '➡️')
                        content_parts.append(f"{i}. {sentiment_emoji} {title}")
            else:
                content_parts.append(f"**今日新闻**: {news_summary.get('status', '暂无数据')}")

        # 添加简单的结尾
        content_parts.append("---")
        content_parts.append("🤖 CoinBrain自动报告")

        return "\n".join(content_parts)

    def get_send_status(self) -> Dict[str, Any]:
        """获取发送状态

        Returns:
            Dict: 包含发送状态信息的字典
        """
        return self.limit_manager.get_today_status()

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
