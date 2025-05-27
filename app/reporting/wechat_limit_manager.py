#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
微信推送限制管理器
管理Server酱免费版的每日发送限制
"""
import os
import json
import datetime
import logging
from typing import Dict, Any

logger = logging.getLogger('wechat_limit_manager')

class WeChatLimitManager:
    """微信推送限制管理器"""
    
    def __init__(self, config, limit_file_path: str = None):
        """初始化限制管理器
        
        Args:
            config: 配置对象
            limit_file_path: 限制记录文件路径
        """
        self.config = config
        self.daily_limit = getattr(config, 'WECHAT_DAILY_LIMIT', 1)
        self.priority_only = getattr(config, 'WECHAT_PRIORITY_ONLY', True)
        
        # 设置限制记录文件路径
        if limit_file_path is None:
            app_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            self.limit_file_path = os.path.join(app_dir, 'logs', 'wechat_send_limit.json')
        else:
            self.limit_file_path = limit_file_path
        
        # 确保日志目录存在
        os.makedirs(os.path.dirname(self.limit_file_path), exist_ok=True)
        
        # 加载今日发送记录
        self.today_record = self._load_today_record()
    
    def _load_today_record(self) -> Dict[str, Any]:
        """加载今日发送记录"""
        today = datetime.date.today().strftime('%Y-%m-%d')
        
        try:
            if os.path.exists(self.limit_file_path):
                with open(self.limit_file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 如果是今天的记录，返回；否则重置
                if data.get('date') == today:
                    return data
        except Exception as e:
            logger.warning(f"加载发送记录失败: {e}")
        
        # 返回新的今日记录
        return {
            'date': today,
            'sent_count': 0,
            'sent_messages': []
        }
    
    def _save_today_record(self):
        """保存今日发送记录"""
        try:
            with open(self.limit_file_path, 'w', encoding='utf-8') as f:
                json.dump(self.today_record, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存发送记录失败: {e}")
    
    def can_send_message(self, message_type: str = "normal") -> bool:
        """检查是否可以发送消息
        
        Args:
            message_type: 消息类型 ("normal", "daily_report", "urgent")
            
        Returns:
            bool: 是否可以发送
        """
        # 检查是否是新的一天
        today = datetime.date.today().strftime('%Y-%m-%d')
        if self.today_record['date'] != today:
            # 重置记录
            self.today_record = {
                'date': today,
                'sent_count': 0,
                'sent_messages': []
            }
        
        # 如果启用了优先级模式，只允许每日报告
        if self.priority_only and message_type not in ["daily_report", "urgent"]:
            logger.info(f"优先级模式已启用，跳过 {message_type} 类型消息")
            return False
        
        # 检查是否超过每日限制
        if self.today_record['sent_count'] >= self.daily_limit:
            logger.warning(f"已达到每日发送限制 ({self.daily_limit} 条)")
            return False
        
        # 对于每日报告，检查今天是否已经发送过
        if message_type == "daily_report":
            for msg in self.today_record['sent_messages']:
                if msg.get('type') == 'daily_report':
                    logger.info("今日报告已发送，跳过重复发送")
                    return False
        
        return True
    
    def record_sent_message(self, message_type: str, title: str, success: bool = True):
        """记录已发送的消息
        
        Args:
            message_type: 消息类型
            title: 消息标题
            success: 是否发送成功
        """
        if success:
            self.today_record['sent_count'] += 1
            self.today_record['sent_messages'].append({
                'type': message_type,
                'title': title,
                'timestamp': datetime.datetime.now().isoformat(),
                'success': success
            })
            
            self._save_today_record()
            logger.info(f"记录发送消息: {title} (类型: {message_type})")
        else:
            logger.warning(f"消息发送失败，不计入限制: {title}")
    
    def get_today_status(self) -> Dict[str, Any]:
        """获取今日发送状态
        
        Returns:
            Dict: 包含今日发送状态的字典
        """
        return {
            'date': self.today_record['date'],
            'sent_count': self.today_record['sent_count'],
            'daily_limit': self.daily_limit,
            'remaining': max(0, self.daily_limit - self.today_record['sent_count']),
            'priority_only': self.priority_only,
            'sent_messages': self.today_record['sent_messages']
        }
    
    def reset_today_limit(self):
        """重置今日限制（管理员功能）"""
        today = datetime.date.today().strftime('%Y-%m-%d')
        self.today_record = {
            'date': today,
            'sent_count': 0,
            'sent_messages': []
        }
        self._save_today_record()
        logger.info("已重置今日发送限制")

# 测试代码
if __name__ == "__main__":
    # 创建模拟配置
    class MockConfig:
        WECHAT_DAILY_LIMIT = 1
        WECHAT_PRIORITY_ONLY = True
    
    config = MockConfig()
    manager = WeChatLimitManager(config)
    
    print("今日发送状态:")
    status = manager.get_today_status()
    print(json.dumps(status, indent=2, ensure_ascii=False))
    
    print(f"\n可以发送普通消息: {manager.can_send_message('normal')}")
    print(f"可以发送每日报告: {manager.can_send_message('daily_report')}")
    print(f"可以发送紧急消息: {manager.can_send_message('urgent')}")
