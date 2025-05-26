#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
交易管理器
整合交易执行、价格监控和仓位管理功能
"""
import os
import sys
import logging
import datetime
from typing import Dict, Any, Optional, List

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from binance.client import Client
from app.trading.trading_executor import TradingExecutor
from app.trading.price_monitor import PriceMonitor
from app.trading.position_manager import PositionManager
from app.data_collectors.binance_data_collector import initialize_binance_client

# 配置日志
logger = logging.getLogger('trading_manager')

class TradingManager:
    """交易管理器类"""
    
    def __init__(self, config: Any, db_config: Dict[str, Any]):
        """
        初始化交易管理器
        
        Args:
            config: 配置对象
            db_config (Dict[str, Any]): 数据库配置
        """
        self.config = config
        self.db_config = db_config
        
        # 初始化Binance客户端
        self.client = initialize_binance_client(
            api_key=config.BINANCE_API_KEY,
            api_secret=config.BINANCE_API_SECRET,
            testnet=config.BINANCE_TESTNET
        )
        
        if not self.client:
            raise Exception("无法初始化Binance客户端")
        
        # 初始化各个模块
        self.trading_executor = TradingExecutor(self.client, db_config)
        self.position_manager = PositionManager(self.client, db_config)
        self.price_monitor = PriceMonitor(self.client, db_config, self.trading_executor)
        
        # 添加价格监控回调
        self.price_monitor.add_price_callback(self._on_price_update)
        
        logger.info("交易管理器初始化完成")
    
    def execute_strategy(self, strategy: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行交易策略
        
        Args:
            strategy (Dict[str, Any]): 交易策略信息
            
        Returns:
            Dict[str, Any]: 执行结果
        """
        try:
            trading_pair = strategy['trading_pair']
            position_type = strategy['position_type']
            entry_price = float(strategy['entry_price_suggestion'])
            stop_loss_price = float(strategy['stop_loss_price']) if strategy.get('stop_loss_price') else None
            take_profit_price = float(strategy['take_profit_price']) if strategy.get('take_profit_price') else None
            position_size_percentage = float(strategy.get('position_size_percentage', 5.0))
            leverage = float(strategy.get('leverage', 1.0))
            strategy_id = strategy.get('id')
            
            # 如果是观望策略，不执行交易
            if position_type == 'NEUTRAL':
                logger.info(f"策略建议观望: {trading_pair}")
                return {'status': 'neutral', 'message': '策略建议观望，不执行交易'}
            
            # 计算仓位大小
            position_calc = self.position_manager.calculate_position_size(
                trading_pair=trading_pair,
                entry_price=entry_price,
                risk_percentage=position_size_percentage,
                stop_loss_price=stop_loss_price
            )
            
            if 'error' in position_calc:
                return {'status': 'error', 'message': f"仓位计算失败: {position_calc['error']}"}
            
            quantity = position_calc['quantity']
            
            # 检查是否启用自动交易
            if not getattr(self.config, 'ENABLE_AUTO_TRADING', False):
                logger.info(f"自动交易未启用，模拟执行策略: {trading_pair}")
                return {
                    'status': 'simulated',
                    'message': '自动交易未启用，仅模拟执行',
                    'strategy': strategy,
                    'position_calc': position_calc
                }
            
            # 执行开仓交易
            if position_type == 'LONG':
                order = self.trading_executor.place_market_order(
                    symbol=trading_pair,
                    side='BUY',
                    quantity=quantity,
                    strategy_id=strategy_id
                )
            else:  # SHORT
                order = self.trading_executor.place_market_order(
                    symbol=trading_pair,
                    side='SELL',
                    quantity=quantity,
                    strategy_id=strategy_id
                )
            
            if not order:
                return {'status': 'error', 'message': '开仓订单执行失败'}
            
            # 创建仓位记录
            position_id = self.position_manager.create_position(
                trading_pair=trading_pair,
                position_type=position_type,
                quantity=quantity,
                entry_price=float(order.get('avgPrice', entry_price)),
                stop_loss_price=stop_loss_price,
                take_profit_price=take_profit_price,
                leverage=leverage,
                strategy_id=strategy_id
            )
            
            if not position_id:
                return {'status': 'error', 'message': '仓位记录创建失败'}
            
            # 设置止损止盈监控
            if stop_loss_price:
                self.price_monitor.add_stop_loss_trigger(
                    trading_pair, position_id, stop_loss_price, quantity
                )
            
            if take_profit_price:
                self.price_monitor.add_take_profit_trigger(
                    trading_pair, position_id, take_profit_price, quantity
                )
            
            # 更新账户余额
            self.trading_executor.update_account_balance()
            
            logger.info(f"策略执行成功: {trading_pair}, 仓位ID={position_id}")
            
            return {
                'status': 'success',
                'message': '策略执行成功',
                'order': order,
                'position_id': position_id,
                'position_calc': position_calc
            }
            
        except Exception as e:
            logger.error(f"执行策略失败: {e}")
            return {'status': 'error', 'message': f'策略执行失败: {str(e)}'}
    
    def start_monitoring(self, symbols: List[str]):
        """
        开始价格监控
        
        Args:
            symbols (List[str]): 要监控的交易对列表
        """
        self.price_monitor.start_monitoring(symbols)
        logger.info(f"开始监控交易对: {symbols}")
    
    def stop_monitoring(self):
        """停止价格监控"""
        self.price_monitor.stop_monitoring()
        logger.info("停止价格监控")
    
    def get_portfolio_status(self) -> Dict[str, Any]:
        """
        获取投资组合状态
        
        Returns:
            Dict[str, Any]: 投资组合状态信息
        """
        try:
            # 更新所有仓位价格
            self.position_manager.update_all_positions_prices()
            
            # 获取投资组合摘要
            portfolio_summary = self.position_manager.get_portfolio_summary()
            
            # 获取开放仓位
            open_positions = self.position_manager.get_open_positions()
            
            # 获取账户信息
            account_info = self.trading_executor.get_account_info()
            
            return {
                'portfolio_summary': portfolio_summary,
                'open_positions': open_positions,
                'account_info': account_info,
                'last_updated': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"获取投资组合状态失败: {e}")
            return {'error': str(e)}
    
    def close_position_manually(self, position_id: int, close_reason: str = 'MANUAL') -> Dict[str, Any]:
        """
        手动关闭仓位
        
        Args:
            position_id (int): 仓位ID
            close_reason (str): 关闭原因
            
        Returns:
            Dict[str, Any]: 关闭结果
        """
        try:
            # 获取仓位信息
            position = self.position_manager.get_position(position_id)
            if not position:
                return {'status': 'error', 'message': '仓位不存在'}
            
            if position['status'] != 'OPEN':
                return {'status': 'error', 'message': '仓位已关闭'}
            
            trading_pair = position['trading_pair']
            position_type = position['position_type']
            quantity = float(position['quantity'])
            
            # 执行平仓交易
            if position_type == 'LONG':
                order = self.trading_executor.place_market_order(
                    symbol=trading_pair,
                    side='SELL',
                    quantity=quantity
                )
            else:  # SHORT
                order = self.trading_executor.place_market_order(
                    symbol=trading_pair,
                    side='BUY',
                    quantity=quantity
                )
            
            if not order:
                return {'status': 'error', 'message': '平仓订单执行失败'}
            
            # 关闭仓位
            close_price = float(order.get('avgPrice', position['current_price']))
            success = self.position_manager.close_position(position_id, close_price, close_reason)
            
            if not success:
                return {'status': 'error', 'message': '仓位关闭失败'}
            
            # 移除价格监控触发器
            self.price_monitor.remove_triggers_for_position(trading_pair, position_id)
            
            # 更新账户余额
            self.trading_executor.update_account_balance()
            
            logger.info(f"手动关闭仓位成功: ID={position_id}")
            
            return {
                'status': 'success',
                'message': '仓位关闭成功',
                'order': order,
                'close_price': close_price
            }
            
        except Exception as e:
            logger.error(f"手动关闭仓位失败: {e}")
            return {'status': 'error', 'message': f'关闭仓位失败: {str(e)}'}
    
    def get_trading_history(self, days: int = 7) -> List[Dict[str, Any]]:
        """
        获取交易历史
        
        Args:
            days (int): 查询天数
            
        Returns:
            List[Dict[str, Any]]: 交易历史列表
        """
        try:
            return self.position_manager.get_position_history(days=days)
        except Exception as e:
            logger.error(f"获取交易历史失败: {e}")
            return []
    
    def _on_price_update(self, symbol: str, price: float):
        """
        价格更新回调函数
        
        Args:
            symbol (str): 交易对
            price (float): 当前价格
        """
        try:
            # 更新相关仓位的当前价格
            open_positions = self.position_manager.get_open_positions(symbol)
            
            for position in open_positions:
                position_id = position['id']
                self.position_manager.update_position_price(position_id, price)
                
        except Exception as e:
            logger.error(f"价格更新回调处理失败: {e}")
    
    def get_current_prices(self) -> Dict[str, float]:
        """
        获取当前监控的所有交易对价格
        
        Returns:
            Dict[str, float]: 交易对价格字典
        """
        return self.price_monitor.current_prices.copy()
    
    def is_monitoring_active(self) -> bool:
        """
        检查价格监控是否活跃
        
        Returns:
            bool: 监控状态
        """
        return self.price_monitor.is_monitoring
