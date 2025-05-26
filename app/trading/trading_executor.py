#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
交易执行模块
用于调用Binance API执行买入和卖出操作
"""
import os
import sys
import time
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
logger = logging.getLogger('trading_executor')

class TradingExecutor:
    """交易执行器类"""

    def __init__(self, binance_client: Client, db_config: Dict[str, Any]):
        """
        初始化交易执行器

        Args:
            binance_client (Client): Binance API客户端
            db_config (Dict[str, Any]): 数据库配置
        """
        self.client = binance_client
        self.db_manager = DatabaseManager(db_config)

    def get_account_info(self) -> Optional[Dict[str, Any]]:
        """
        获取账户信息

        Returns:
            Optional[Dict[str, Any]]: 账户信息字典，失败时返回None
        """
        try:
            account_info = self.client.get_account()
            logger.info("成功获取账户信息")
            return account_info
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"获取账户信息失败: {e}")
            return None

    def get_balance(self, asset: str = 'USDT') -> Optional[Dict[str, Any]]:
        """
        获取指定资产余额

        Args:
            asset (str): 资产符号，默认为USDT

        Returns:
            Optional[Dict[str, Any]]: 余额信息，失败时返回None
        """
        try:
            balance = self.client.get_asset_balance(asset=asset)
            if balance:
                logger.info(f"获取{asset}余额成功: 可用={balance['free']}, 冻结={balance['locked']}")
                return {
                    'asset': asset,
                    'free': float(balance['free']),
                    'locked': float(balance['locked']),
                    'total': float(balance['free']) + float(balance['locked'])
                }
            return None
        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"获取{asset}余额失败: {e}")
            return None

    def place_market_order(self, symbol: str, side: str, quantity: float,
                          strategy_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        下市价单

        Args:
            symbol (str): 交易对，例如BTCUSDT
            side (str): 买卖方向，BUY或SELL
            quantity (float): 交易数量
            strategy_id (Optional[int]): 关联的策略ID

        Returns:
            Optional[Dict[str, Any]]: 订单信息，失败时返回None
        """
        try:
            order = self.client.order_market(
                symbol=symbol,
                side=side,
                quantity=quantity
            )

            logger.info(f"市价{side}订单成功: {symbol}, 数量={quantity}, 订单ID={order['orderId']}")

            # 存储订单到数据库
            self._store_order_to_db(order, 'MARKET', strategy_id)

            return order

        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"下市价{side}订单失败: {symbol}, 数量={quantity}, 错误={e}")
            return None

    def place_limit_order(self, symbol: str, side: str, quantity: float, price: float,
                         strategy_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        下限价单

        Args:
            symbol (str): 交易对，例如BTCUSDT
            side (str): 买卖方向，BUY或SELL
            quantity (float): 交易数量
            price (float): 限价价格
            strategy_id (Optional[int]): 关联的策略ID

        Returns:
            Optional[Dict[str, Any]]: 订单信息，失败时返回None
        """
        try:
            order = self.client.order_limit(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=str(price)
            )

            logger.info(f"限价{side}订单成功: {symbol}, 数量={quantity}, 价格={price}, 订单ID={order['orderId']}")

            # 存储订单到数据库
            self._store_order_to_db(order, 'LIMIT', strategy_id)

            return order

        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"下限价{side}订单失败: {symbol}, 数量={quantity}, 价格={price}, 错误={e}")
            return None

    def place_stop_loss_order(self, symbol: str, side: str, quantity: float, stop_price: float,
                             strategy_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        下止损单

        Args:
            symbol (str): 交易对，例如BTCUSDT
            side (str): 买卖方向，BUY或SELL
            quantity (float): 交易数量
            stop_price (float): 止损触发价格
            strategy_id (Optional[int]): 关联的策略ID

        Returns:
            Optional[Dict[str, Any]]: 订单信息，失败时返回None
        """
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type='STOP_LOSS_LIMIT',
                timeInForce='GTC',
                quantity=quantity,
                stopPrice=str(stop_price),
                price=str(stop_price * 0.99 if side == 'SELL' else stop_price * 1.01)  # 设置一个合理的限价
            )

            logger.info(f"止损{side}订单成功: {symbol}, 数量={quantity}, 止损价={stop_price}, 订单ID={order['orderId']}")

            # 存储订单到数据库
            self._store_order_to_db(order, 'STOP_LOSS_LIMIT', strategy_id)

            return order

        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"下止损{side}订单失败: {symbol}, 数量={quantity}, 止损价={stop_price}, 错误={e}")
            return None

    def place_take_profit_order(self, symbol: str, side: str, quantity: float, take_profit_price: float,
                               strategy_id: Optional[int] = None) -> Optional[Dict[str, Any]]:
        """
        下止盈单

        Args:
            symbol (str): 交易对，例如BTCUSDT
            side (str): 买卖方向，BUY或SELL
            quantity (float): 交易数量
            take_profit_price (float): 止盈触发价格
            strategy_id (Optional[int]): 关联的策略ID

        Returns:
            Optional[Dict[str, Any]]: 订单信息，失败时返回None
        """
        try:
            order = self.client.create_order(
                symbol=symbol,
                side=side,
                type='TAKE_PROFIT_LIMIT',
                timeInForce='GTC',
                quantity=quantity,
                stopPrice=str(take_profit_price),
                price=str(take_profit_price * 1.01 if side == 'SELL' else take_profit_price * 0.99)  # 设置一个合理的限价
            )

            logger.info(f"止盈{side}订单成功: {symbol}, 数量={quantity}, 止盈价={take_profit_price}, 订单ID={order['orderId']}")

            # 存储订单到数据库
            self._store_order_to_db(order, 'TAKE_PROFIT_LIMIT', strategy_id)

            return order

        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"下止盈{side}订单失败: {symbol}, 数量={quantity}, 止盈价={take_profit_price}, 错误={e}")
            return None

    def cancel_order(self, symbol: str, order_id: int) -> bool:
        """
        取消订单

        Args:
            symbol (str): 交易对
            order_id (int): 订单ID

        Returns:
            bool: 取消成功返回True，失败返回False
        """
        try:
            result = self.client.cancel_order(symbol=symbol, orderId=order_id)
            logger.info(f"取消订单成功: {symbol}, 订单ID={order_id}")

            # 更新数据库中的订单状态
            self._update_order_status_in_db(order_id, 'CANCELED')

            return True

        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"取消订单失败: {symbol}, 订单ID={order_id}, 错误={e}")
            return False

    def get_order_status(self, symbol: str, order_id: int) -> Optional[Dict[str, Any]]:
        """
        查询订单状态

        Args:
            symbol (str): 交易对
            order_id (int): 订单ID

        Returns:
            Optional[Dict[str, Any]]: 订单信息，失败时返回None
        """
        try:
            order = self.client.get_order(symbol=symbol, orderId=order_id)
            logger.info(f"查询订单状态成功: {symbol}, 订单ID={order_id}, 状态={order['status']}")

            # 更新数据库中的订单状态
            self._update_order_status_in_db(order_id, order['status'])

            return order

        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"查询订单状态失败: {symbol}, 订单ID={order_id}, 错误={e}")
            return None

    def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        获取未完成订单

        Args:
            symbol (Optional[str]): 交易对，如果为None则获取所有交易对的未完成订单

        Returns:
            List[Dict[str, Any]]: 未完成订单列表
        """
        try:
            if symbol:
                orders = self.client.get_open_orders(symbol=symbol)
            else:
                orders = self.client.get_open_orders()

            logger.info(f"获取未完成订单成功: 数量={len(orders)}")
            return orders

        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"获取未完成订单失败: 错误={e}")
            return []

    def update_account_balance(self) -> bool:
        """
        更新账户余额到数据库

        Returns:
            bool: 更新成功返回True，失败返回False
        """
        try:
            account_info = self.get_account_info()
            if not account_info:
                return False

            balances = account_info.get('balances', [])

            with self.db_manager.get_connection() as (connection, cursor):
                for balance in balances:
                    asset = balance['asset']
                    free = float(balance['free'])
                    locked = float(balance['locked'])
                    total = free + locked

                    # 只更新有余额的资产
                    if total > 0:
                        cursor.execute("""
                            INSERT INTO account_balance (asset, free_balance, locked_balance, total_balance)
                            VALUES (%s, %s, %s, %s)
                            ON DUPLICATE KEY UPDATE
                            free_balance = VALUES(free_balance),
                            locked_balance = VALUES(locked_balance),
                            total_balance = VALUES(total_balance),
                            last_updated = CURRENT_TIMESTAMP
                        """, (asset, free, locked, total))

                connection.commit()
                logger.info("账户余额更新成功")
                return True

        except Exception as e:
            logger.error(f"更新账户余额失败: {e}")
            return False

    def _store_order_to_db(self, order: Dict[str, Any], order_type: str,
                          strategy_id: Optional[int] = None) -> bool:
        """
        将订单信息存储到数据库

        Args:
            order (Dict[str, Any]): Binance订单信息
            order_type (str): 订单类型
            strategy_id (Optional[int]): 关联的策略ID

        Returns:
            bool: 存储成功返回True，失败返回False
        """
        try:
            with self.db_manager.get_connection() as (connection, cursor):
                cursor.execute("""
                    INSERT INTO orders
                    (binance_order_id, trading_pair, order_type, side, quantity, price, stop_price,
                     executed_quantity, executed_price, status, time_in_force, order_time, related_strategy_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    order['orderId'],
                    order['symbol'],
                    order_type,
                    order['side'],
                    float(order['origQty']),
                    float(order.get('price', 0)) if order.get('price') else None,
                    float(order.get('stopPrice', 0)) if order.get('stopPrice') else None,
                    float(order['executedQty']),
                    float(order.get('avgPrice', 0)) if order.get('avgPrice') else None,
                    order['status'],
                    order.get('timeInForce', 'GTC'),
                    datetime.datetime.fromtimestamp(order['transactTime'] / 1000),
                    strategy_id
                ))

                connection.commit()
                logger.info(f"订单存储到数据库成功: 订单ID={order['orderId']}")
                return True

        except Exception as e:
            logger.error(f"存储订单到数据库失败: {e}")
            return False

    def _update_order_status_in_db(self, order_id: int, status: str) -> bool:
        """
        更新数据库中的订单状态

        Args:
            order_id (int): 订单ID
            status (str): 新状态

        Returns:
            bool: 更新成功返回True，失败返回False
        """
        try:
            with self.db_manager.get_connection() as (connection, cursor):
                cursor.execute("""
                    UPDATE orders
                    SET status = %s, update_time = CURRENT_TIMESTAMP
                    WHERE binance_order_id = %s
                """, (status, order_id))

                connection.commit()
                logger.info(f"订单状态更新成功: 订单ID={order_id}, 状态={status}")
                return True

        except Exception as e:
            logger.error(f"更新订单状态失败: {e}")
            return False
