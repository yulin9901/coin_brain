#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
价格监控模块
用于监控价格变动并在达到止盈或止损价格时执行卖出操作
"""
import os
import sys
import time
import json
import logging
import threading
import datetime
from typing import Dict, Any, Optional, List, Callable
from decimal import Decimal

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

import websocket
from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from app.database.db_manager import DatabaseManager
from app.trading.trading_executor import TradingExecutor

# 配置日志
logger = logging.getLogger('price_monitor')

class PriceMonitor:
    """价格监控器类"""
    
    def __init__(self, binance_client: Client, db_config: Dict[str, Any], 
                 trading_executor: TradingExecutor):
        """
        初始化价格监控器
        
        Args:
            binance_client (Client): Binance API客户端
            db_config (Dict[str, Any]): 数据库配置
            trading_executor (TradingExecutor): 交易执行器
        """
        self.client = binance_client
        self.db_manager = DatabaseManager(db_config)
        self.trading_executor = trading_executor
        
        # 监控状态
        self.is_monitoring = False
        self.monitor_thread = None
        self.websocket_thread = None
        self.ws = None
        
        # 价格数据缓存
        self.current_prices = {}
        self.price_callbacks = []
        
        # 监控的交易对
        self.monitored_symbols = set()
        
        # 止盈止损触发器
        self.stop_loss_triggers = {}  # {symbol: {position_id: {price: float, quantity: float}}}
        self.take_profit_triggers = {}  # {symbol: {position_id: {price: float, quantity: float}}}
    
    def add_price_callback(self, callback: Callable[[str, float], None]):
        """
        添加价格变化回调函数
        
        Args:
            callback: 回调函数，接收symbol和price参数
        """
        self.price_callbacks.append(callback)
    
    def start_monitoring(self, symbols: List[str]):
        """
        开始价格监控
        
        Args:
            symbols (List[str]): 要监控的交易对列表
        """
        if self.is_monitoring:
            logger.warning("价格监控已在运行中")
            return
        
        self.monitored_symbols = set(symbols)
        self.is_monitoring = True
        
        # 启动WebSocket监控线程
        self.websocket_thread = threading.Thread(target=self._start_websocket_monitoring)
        self.websocket_thread.daemon = True
        self.websocket_thread.start()
        
        # 启动主监控线程
        self.monitor_thread = threading.Thread(target=self._monitoring_loop)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()
        
        logger.info(f"开始监控价格: {symbols}")
    
    def stop_monitoring(self):
        """停止价格监控"""
        self.is_monitoring = False
        
        if self.ws:
            self.ws.close()
        
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=5)
        
        if self.websocket_thread and self.websocket_thread.is_alive():
            self.websocket_thread.join(timeout=5)
        
        logger.info("价格监控已停止")
    
    def add_stop_loss_trigger(self, symbol: str, position_id: int, stop_price: float, quantity: float):
        """
        添加止损触发器
        
        Args:
            symbol (str): 交易对
            position_id (int): 仓位ID
            stop_price (float): 止损价格
            quantity (float): 止损数量
        """
        if symbol not in self.stop_loss_triggers:
            self.stop_loss_triggers[symbol] = {}
        
        self.stop_loss_triggers[symbol][position_id] = {
            'price': stop_price,
            'quantity': quantity
        }
        
        logger.info(f"添加止损触发器: {symbol}, 仓位ID={position_id}, 止损价={stop_price}")
    
    def add_take_profit_trigger(self, symbol: str, position_id: int, take_profit_price: float, quantity: float):
        """
        添加止盈触发器
        
        Args:
            symbol (str): 交易对
            position_id (int): 仓位ID
            take_profit_price (float): 止盈价格
            quantity (float): 止盈数量
        """
        if symbol not in self.take_profit_triggers:
            self.take_profit_triggers[symbol] = {}
        
        self.take_profit_triggers[symbol][position_id] = {
            'price': take_profit_price,
            'quantity': quantity
        }
        
        logger.info(f"添加止盈触发器: {symbol}, 仓位ID={position_id}, 止盈价={take_profit_price}")
    
    def remove_triggers_for_position(self, symbol: str, position_id: int):
        """
        移除指定仓位的所有触发器
        
        Args:
            symbol (str): 交易对
            position_id (int): 仓位ID
        """
        if symbol in self.stop_loss_triggers and position_id in self.stop_loss_triggers[symbol]:
            del self.stop_loss_triggers[symbol][position_id]
            logger.info(f"移除止损触发器: {symbol}, 仓位ID={position_id}")
        
        if symbol in self.take_profit_triggers and position_id in self.take_profit_triggers[symbol]:
            del self.take_profit_triggers[symbol][position_id]
            logger.info(f"移除止盈触发器: {symbol}, 仓位ID={position_id}")
    
    def get_current_price(self, symbol: str) -> Optional[float]:
        """
        获取当前价格
        
        Args:
            symbol (str): 交易对
            
        Returns:
            Optional[float]: 当前价格，如果没有数据则返回None
        """
        return self.current_prices.get(symbol)
    
    def _start_websocket_monitoring(self):
        """启动WebSocket价格监控"""
        try:
            # 构建WebSocket URL
            streams = [f"{symbol.lower()}@ticker" for symbol in self.monitored_symbols]
            stream_url = f"wss://stream.binance.com:9443/ws/{'/'.join(streams)}"
            
            # 创建WebSocket连接
            self.ws = websocket.WebSocketApp(
                stream_url,
                on_message=self._on_websocket_message,
                on_error=self._on_websocket_error,
                on_close=self._on_websocket_close,
                on_open=self._on_websocket_open
            )
            
            # 运行WebSocket
            self.ws.run_forever()
            
        except Exception as e:
            logger.error(f"WebSocket监控出错: {e}")
    
    def _on_websocket_open(self, ws):
        """WebSocket连接打开回调"""
        logger.info("WebSocket价格监控连接已建立")
    
    def _on_websocket_message(self, ws, message):
        """WebSocket消息回调"""
        try:
            data = json.loads(message)
            
            # 处理单个ticker数据
            if 'stream' in data:
                stream_data = data['data']
                symbol = stream_data['s']
                price = float(stream_data['c'])
                
                # 更新价格缓存
                self.current_prices[symbol] = price
                
                # 调用价格回调函数
                for callback in self.price_callbacks:
                    try:
                        callback(symbol, price)
                    except Exception as e:
                        logger.error(f"价格回调函数执行出错: {e}")
                
                # 检查止盈止损触发
                self._check_triggers(symbol, price)
            
        except Exception as e:
            logger.error(f"处理WebSocket消息出错: {e}")
    
    def _on_websocket_error(self, ws, error):
        """WebSocket错误回调"""
        logger.error(f"WebSocket错误: {error}")
    
    def _on_websocket_close(self, ws, close_status_code, close_msg):
        """WebSocket关闭回调"""
        logger.info("WebSocket连接已关闭")
    
    def _monitoring_loop(self):
        """主监控循环"""
        while self.is_monitoring:
            try:
                # 更新仓位信息
                self._update_position_triggers()
                
                # 休眠一段时间
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"监控循环出错: {e}")
                time.sleep(5)
    
    def _update_position_triggers(self):
        """更新仓位触发器"""
        try:
            with self.db_manager.get_connection() as (connection, cursor):
                # 查询所有开放仓位
                cursor.execute("""
                    SELECT id, trading_pair, position_type, quantity, stop_loss_price, take_profit_price
                    FROM positions 
                    WHERE status = 'OPEN'
                """)
                
                positions = cursor.fetchall()
                
                for position in positions:
                    position_id = position[0]
                    symbol = position[1]
                    position_type = position[2]
                    quantity = float(position[3])
                    stop_loss_price = float(position[4]) if position[4] else None
                    take_profit_price = float(position[5]) if position[5] else None
                    
                    # 添加止损触发器
                    if stop_loss_price:
                        self.add_stop_loss_trigger(symbol, position_id, stop_loss_price, quantity)
                    
                    # 添加止盈触发器
                    if take_profit_price:
                        self.add_take_profit_trigger(symbol, position_id, take_profit_price, quantity)
                
        except Exception as e:
            logger.error(f"更新仓位触发器失败: {e}")
    
    def _check_triggers(self, symbol: str, current_price: float):
        """
        检查触发器
        
        Args:
            symbol (str): 交易对
            current_price (float): 当前价格
        """
        # 检查止损触发器
        if symbol in self.stop_loss_triggers:
            for position_id, trigger_info in list(self.stop_loss_triggers[symbol].items()):
                stop_price = trigger_info['price']
                quantity = trigger_info['quantity']
                
                # 如果当前价格低于或等于止损价格，触发止损
                if current_price <= stop_price:
                    logger.warning(f"触发止损: {symbol}, 仓位ID={position_id}, 当前价={current_price}, 止损价={stop_price}")
                    self._execute_stop_loss(symbol, position_id, quantity)
        
        # 检查止盈触发器
        if symbol in self.take_profit_triggers:
            for position_id, trigger_info in list(self.take_profit_triggers[symbol].items()):
                take_profit_price = trigger_info['price']
                quantity = trigger_info['quantity']
                
                # 如果当前价格高于或等于止盈价格，触发止盈
                if current_price >= take_profit_price:
                    logger.info(f"触发止盈: {symbol}, 仓位ID={position_id}, 当前价={current_price}, 止盈价={take_profit_price}")
                    self._execute_take_profit(symbol, position_id, quantity)
    
    def _execute_stop_loss(self, symbol: str, position_id: int, quantity: float):
        """
        执行止损
        
        Args:
            symbol (str): 交易对
            position_id (int): 仓位ID
            quantity (float): 止损数量
        """
        try:
            # 下市价卖单
            order = self.trading_executor.place_market_order(symbol, 'SELL', quantity)
            
            if order:
                # 更新仓位状态
                self._close_position(position_id, 'STOP_LOSS')
                
                # 移除触发器
                self.remove_triggers_for_position(symbol, position_id)
                
                logger.info(f"止损执行成功: {symbol}, 仓位ID={position_id}")
            else:
                logger.error(f"止损执行失败: {symbol}, 仓位ID={position_id}")
                
        except Exception as e:
            logger.error(f"执行止损出错: {e}")
    
    def _execute_take_profit(self, symbol: str, position_id: int, quantity: float):
        """
        执行止盈
        
        Args:
            symbol (str): 交易对
            position_id (int): 仓位ID
            quantity (float): 止盈数量
        """
        try:
            # 下市价卖单
            order = self.trading_executor.place_market_order(symbol, 'SELL', quantity)
            
            if order:
                # 更新仓位状态
                self._close_position(position_id, 'TAKE_PROFIT')
                
                # 移除触发器
                self.remove_triggers_for_position(symbol, position_id)
                
                logger.info(f"止盈执行成功: {symbol}, 仓位ID={position_id}")
            else:
                logger.error(f"止盈执行失败: {symbol}, 仓位ID={position_id}")
                
        except Exception as e:
            logger.error(f"执行止盈出错: {e}")
    
    def _close_position(self, position_id: int, close_reason: str):
        """
        关闭仓位
        
        Args:
            position_id (int): 仓位ID
            close_reason (str): 关闭原因
        """
        try:
            with self.db_manager.get_connection() as (connection, cursor):
                cursor.execute("""
                    UPDATE positions 
                    SET status = 'CLOSED', last_updated = CURRENT_TIMESTAMP
                    WHERE id = %s
                """, (position_id,))
                
                connection.commit()
                logger.info(f"仓位已关闭: ID={position_id}, 原因={close_reason}")
                
        except Exception as e:
            logger.error(f"关闭仓位失败: {e}")
