#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
仓位管理模块
用于跟踪当前持有的仓位和资金分配
"""
import os
import sys
import logging
import datetime
from typing import Dict, Any, Optional, List
from decimal import Decimal

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from app.database.db_manager import DatabaseManager

# 配置日志
logger = logging.getLogger('position_manager')

class PositionManager:
    """仓位管理器类"""
    
    def __init__(self, binance_client: Client, db_config: Dict[str, Any]):
        """
        初始化仓位管理器
        
        Args:
            binance_client (Client): Binance API客户端
            db_config (Dict[str, Any]): 数据库配置
        """
        self.client = binance_client
        self.db_manager = DatabaseManager(db_config)
    
    def create_position(self, trading_pair: str, position_type: str, quantity: float, 
                       entry_price: float, stop_loss_price: Optional[float] = None,
                       take_profit_price: Optional[float] = None, leverage: float = 1.0,
                       strategy_id: Optional[int] = None) -> Optional[int]:
        """
        创建新仓位
        
        Args:
            trading_pair (str): 交易对
            position_type (str): 仓位类型，LONG或SHORT
            quantity (float): 仓位数量
            entry_price (float): 入场价格
            stop_loss_price (Optional[float]): 止损价格
            take_profit_price (Optional[float]): 止盈价格
            leverage (float): 杠杆倍数
            strategy_id (Optional[int]): 关联的策略ID
            
        Returns:
            Optional[int]: 仓位ID，失败时返回None
        """
        try:
            # 计算保证金
            margin_used = (quantity * entry_price) / leverage
            
            with self.db_manager.get_connection() as (connection, cursor):
                cursor.execute("""
                    INSERT INTO positions 
                    (trading_pair, position_type, quantity, entry_price, current_price, 
                     stop_loss_price, take_profit_price, leverage, margin_used, related_strategy_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    trading_pair, position_type, quantity, entry_price, entry_price,
                    stop_loss_price, take_profit_price, leverage, margin_used, strategy_id
                ))
                
                position_id = cursor.lastrowid
                connection.commit()
                
                logger.info(f"创建仓位成功: ID={position_id}, {trading_pair}, {position_type}, 数量={quantity}")
                return position_id
                
        except Exception as e:
            logger.error(f"创建仓位失败: {e}")
            return None
    
    def get_position(self, position_id: int) -> Optional[Dict[str, Any]]:
        """
        获取指定仓位信息
        
        Args:
            position_id (int): 仓位ID
            
        Returns:
            Optional[Dict[str, Any]]: 仓位信息，失败时返回None
        """
        try:
            with self.db_manager.get_connection() as (connection, cursor):
                cursor.execute("""
                    SELECT * FROM positions WHERE id = %s
                """, (position_id,))
                
                result = cursor.fetchone()
                if result:
                    columns = [desc[0] for desc in cursor.description]
                    position = dict(zip(columns, result))
                    return position
                
                return None
                
        except Exception as e:
            logger.error(f"获取仓位信息失败: {e}")
            return None
    
    def get_open_positions(self, trading_pair: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取所有开放仓位
        
        Args:
            trading_pair (Optional[str]): 交易对过滤，如果为None则获取所有交易对
            
        Returns:
            List[Dict[str, Any]]: 开放仓位列表
        """
        try:
            with self.db_manager.get_connection() as (connection, cursor):
                if trading_pair:
                    cursor.execute("""
                        SELECT * FROM positions 
                        WHERE status = 'OPEN' AND trading_pair = %s
                        ORDER BY open_time DESC
                    """, (trading_pair,))
                else:
                    cursor.execute("""
                        SELECT * FROM positions 
                        WHERE status = 'OPEN'
                        ORDER BY open_time DESC
                    """)
                
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                positions = []
                for result in results:
                    position = dict(zip(columns, result))
                    positions.append(position)
                
                return positions
                
        except Exception as e:
            logger.error(f"获取开放仓位失败: {e}")
            return []
    
    def update_position_price(self, position_id: int, current_price: float) -> bool:
        """
        更新仓位当前价格和未实现盈亏
        
        Args:
            position_id (int): 仓位ID
            current_price (float): 当前价格
            
        Returns:
            bool: 更新成功返回True，失败返回False
        """
        try:
            position = self.get_position(position_id)
            if not position:
                return False
            
            # 计算未实现盈亏
            entry_price = float(position['entry_price'])
            quantity = float(position['quantity'])
            position_type = position['position_type']
            leverage = float(position['leverage'])
            
            if position_type == 'LONG':
                unrealized_pnl = (current_price - entry_price) * quantity * leverage
            else:  # SHORT
                unrealized_pnl = (entry_price - current_price) * quantity * leverage
            
            with self.db_manager.get_connection() as (connection, cursor):
                cursor.execute("""
                    UPDATE positions 
                    SET current_price = %s, unrealized_pnl = %s, last_updated = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (current_price, unrealized_pnl, position_id))
                
                connection.commit()
                return True
                
        except Exception as e:
            logger.error(f"更新仓位价格失败: {e}")
            return False
    
    def close_position(self, position_id: int, close_price: float, close_reason: str = 'MANUAL') -> bool:
        """
        关闭仓位
        
        Args:
            position_id (int): 仓位ID
            close_price (float): 平仓价格
            close_reason (str): 关闭原因
            
        Returns:
            bool: 关闭成功返回True，失败返回False
        """
        try:
            position = self.get_position(position_id)
            if not position:
                return False
            
            # 计算已实现盈亏
            entry_price = float(position['entry_price'])
            quantity = float(position['quantity'])
            position_type = position['position_type']
            leverage = float(position['leverage'])
            
            if position_type == 'LONG':
                realized_pnl = (close_price - entry_price) * quantity * leverage
            else:  # SHORT
                realized_pnl = (entry_price - close_price) * quantity * leverage
            
            with self.db_manager.get_connection() as (connection, cursor):
                cursor.execute("""
                    UPDATE positions 
                    SET status = 'CLOSED', current_price = %s, unrealized_pnl = %s, 
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (close_price, realized_pnl, position_id))
                
                # 记录到交易记录表
                cursor.execute("""
                    INSERT INTO trades 
                    (trading_pair, position_type, transaction_type, quantity, price, 
                     leverage, pnl, related_open_trade_id, close_reason)
                    VALUES (%s, %s, 'CLOSE', %s, %s, %s, %s, %s, %s)
                """, (
                    position['trading_pair'], position_type, quantity, close_price,
                    leverage, realized_pnl, position_id, close_reason
                ))
                
                connection.commit()
                
                logger.info(f"仓位关闭成功: ID={position_id}, 平仓价={close_price}, 盈亏={realized_pnl}")
                return True
                
        except Exception as e:
            logger.error(f"关闭仓位失败: {e}")
            return False
    
    def get_portfolio_summary(self) -> Dict[str, Any]:
        """
        获取投资组合摘要
        
        Returns:
            Dict[str, Any]: 投资组合摘要信息
        """
        try:
            with self.db_manager.get_connection() as (connection, cursor):
                # 获取开放仓位统计
                cursor.execute("""
                    SELECT 
                        COUNT(*) as open_positions,
                        SUM(margin_used) as total_margin_used,
                        SUM(unrealized_pnl) as total_unrealized_pnl
                    FROM positions 
                    WHERE status = 'OPEN'
                """)
                
                open_stats = cursor.fetchone()
                
                # 获取今日已实现盈亏
                cursor.execute("""
                    SELECT SUM(pnl) as daily_realized_pnl
                    FROM trades 
                    WHERE transaction_type = 'CLOSE' 
                    AND DATE(transaction_time) = CURDATE()
                """)
                
                daily_pnl = cursor.fetchone()
                
                # 获取账户余额
                cursor.execute("""
                    SELECT asset, total_balance 
                    FROM account_balance 
                    WHERE asset IN ('USDT', 'BTC', 'ETH')
                """)
                
                balances = cursor.fetchall()
                
                summary = {
                    'open_positions': open_stats[0] if open_stats[0] else 0,
                    'total_margin_used': float(open_stats[1]) if open_stats[1] else 0.0,
                    'total_unrealized_pnl': float(open_stats[2]) if open_stats[2] else 0.0,
                    'daily_realized_pnl': float(daily_pnl[0]) if daily_pnl[0] else 0.0,
                    'balances': {balance[0]: float(balance[1]) for balance in balances},
                    'last_updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
                
                return summary
                
        except Exception as e:
            logger.error(f"获取投资组合摘要失败: {e}")
            return {}
    
    def calculate_position_size(self, trading_pair: str, entry_price: float, 
                               risk_percentage: float = 2.0, stop_loss_price: Optional[float] = None,
                               available_balance: Optional[float] = None) -> Dict[str, Any]:
        """
        计算仓位大小
        
        Args:
            trading_pair (str): 交易对
            entry_price (float): 入场价格
            risk_percentage (float): 风险百分比（默认2%）
            stop_loss_price (Optional[float]): 止损价格
            available_balance (Optional[float]): 可用余额，如果为None则自动获取
            
        Returns:
            Dict[str, Any]: 仓位大小计算结果
        """
        try:
            # 获取可用余额
            if available_balance is None:
                balance_info = self._get_usdt_balance()
                if not balance_info:
                    return {'error': '无法获取账户余额'}
                available_balance = balance_info['free']
            
            # 计算风险金额
            risk_amount = available_balance * (risk_percentage / 100)
            
            # 如果有止损价格，根据止损计算仓位大小
            if stop_loss_price:
                price_diff = abs(entry_price - stop_loss_price)
                if price_diff > 0:
                    quantity = risk_amount / price_diff
                else:
                    quantity = 0
            else:
                # 如果没有止损价格，使用固定风险金额
                quantity = risk_amount / entry_price
            
            # 计算总价值
            total_value = quantity * entry_price
            
            result = {
                'quantity': round(quantity, 8),
                'total_value': round(total_value, 2),
                'risk_amount': round(risk_amount, 2),
                'risk_percentage': risk_percentage,
                'available_balance': round(available_balance, 2),
                'entry_price': entry_price,
                'stop_loss_price': stop_loss_price
            }
            
            logger.info(f"仓位大小计算: {trading_pair}, 数量={quantity}, 总价值={total_value}")
            return result
            
        except Exception as e:
            logger.error(f"计算仓位大小失败: {e}")
            return {'error': str(e)}
    
    def _get_usdt_balance(self) -> Optional[Dict[str, Any]]:
        """
        获取USDT余额
        
        Returns:
            Optional[Dict[str, Any]]: USDT余额信息
        """
        try:
            balance = self.client.get_asset_balance(asset='USDT')
            if balance:
                return {
                    'free': float(balance['free']),
                    'locked': float(balance['locked']),
                    'total': float(balance['free']) + float(balance['locked'])
                }
            return None
            
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"获取USDT余额失败: {e}")
            return None
    
    def update_all_positions_prices(self):
        """更新所有开放仓位的当前价格"""
        try:
            open_positions = self.get_open_positions()
            
            for position in open_positions:
                trading_pair = position['trading_pair']
                position_id = position['id']
                
                # 获取当前价格
                try:
                    ticker = self.client.get_ticker(symbol=trading_pair)
                    current_price = float(ticker['lastPrice'])
                    
                    # 更新仓位价格
                    self.update_position_price(position_id, current_price)
                    
                except Exception as e:
                    logger.error(f"更新仓位{position_id}价格失败: {e}")
            
            logger.info(f"更新了{len(open_positions)}个仓位的价格")
            
        except Exception as e:
            logger.error(f"批量更新仓位价格失败: {e}")
    
    def get_position_history(self, trading_pair: Optional[str] = None, 
                           days: int = 30) -> List[Dict[str, Any]]:
        """
        获取仓位历史
        
        Args:
            trading_pair (Optional[str]): 交易对过滤
            days (int): 查询天数
            
        Returns:
            List[Dict[str, Any]]: 仓位历史列表
        """
        try:
            with self.db_manager.get_connection() as (connection, cursor):
                if trading_pair:
                    cursor.execute("""
                        SELECT * FROM positions 
                        WHERE trading_pair = %s 
                        AND open_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                        ORDER BY open_time DESC
                    """, (trading_pair, days))
                else:
                    cursor.execute("""
                        SELECT * FROM positions 
                        WHERE open_time >= DATE_SUB(NOW(), INTERVAL %s DAY)
                        ORDER BY open_time DESC
                    """, (days,))
                
                results = cursor.fetchall()
                columns = [desc[0] for desc in cursor.description]
                
                positions = []
                for result in results:
                    position = dict(zip(columns, result))
                    positions.append(position)
                
                return positions
                
        except Exception as e:
            logger.error(f"获取仓位历史失败: {e}")
            return []
