#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
交易相关的定时任务
"""
import os
import sys
import logging
import datetime
from typing import List, Dict, Any

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.utils import load_config, get_db_config
from app.trading import TradingManager
from app.database.db_manager import DatabaseManager

# 配置日志
logger = logging.getLogger('trading_tasks')

# 全局交易管理器实例
_trading_manager = None

def get_trading_manager():
    """获取交易管理器实例（单例模式）"""
    global _trading_manager
    
    if _trading_manager is None:
        try:
            config = load_config()
            db_config = get_db_config(config)
            _trading_manager = TradingManager(config, db_config)
            logger.info("交易管理器初始化成功")
        except Exception as e:
            logger.error(f"交易管理器初始化失败: {e}")
            return None
    
    return _trading_manager

def execute_trading_strategies():
    """执行交易策略任务"""
    logger.info("开始执行交易策略...")
    
    try:
        trading_manager = get_trading_manager()
        if not trading_manager:
            logger.error("交易管理器未初始化")
            return False
        
        # 获取今日的交易策略
        strategies = _get_latest_trading_strategies()
        
        if not strategies:
            logger.info("没有找到待执行的交易策略")
            return True
        
        executed_count = 0
        success_count = 0
        
        for strategy in strategies:
            try:
                logger.info(f"执行策略: {strategy['trading_pair']} - {strategy['position_type']}")
                
                result = trading_manager.execute_strategy(strategy)
                executed_count += 1
                
                if result['status'] == 'success':
                    success_count += 1
                    logger.info(f"策略执行成功: {strategy['trading_pair']}")
                elif result['status'] == 'simulated':
                    logger.info(f"策略模拟执行: {strategy['trading_pair']}")
                else:
                    logger.warning(f"策略执行失败: {strategy['trading_pair']} - {result['message']}")
                
                # 更新策略执行状态
                _update_strategy_execution_status(strategy['id'], result['status'], result['message'])
                
            except Exception as e:
                logger.error(f"执行策略时出错: {strategy['trading_pair']} - {e}")
        
        logger.info(f"策略执行完成: 总数={executed_count}, 成功={success_count}")
        return True
        
    except Exception as e:
        logger.error(f"执行交易策略任务失败: {e}")
        return False

def monitor_positions():
    """监控仓位任务"""
    logger.info("开始监控仓位...")
    
    try:
        trading_manager = get_trading_manager()
        if not trading_manager:
            logger.error("交易管理器未初始化")
            return False
        
        # 获取投资组合状态
        portfolio_status = trading_manager.get_portfolio_status()
        
        if 'error' in portfolio_status:
            logger.error(f"获取投资组合状态失败: {portfolio_status['error']}")
            return False
        
        # 记录投资组合状态
        portfolio_summary = portfolio_status['portfolio_summary']
        open_positions = portfolio_status['open_positions']
        
        logger.info(f"当前投资组合状态:")
        logger.info(f"  开放仓位数量: {portfolio_summary.get('open_positions', 0)}")
        logger.info(f"  总保证金使用: {portfolio_summary.get('total_margin_used', 0)}")
        logger.info(f"  总未实现盈亏: {portfolio_summary.get('total_unrealized_pnl', 0)}")
        logger.info(f"  今日已实现盈亏: {portfolio_summary.get('daily_realized_pnl', 0)}")
        
        # 检查是否需要启动价格监控
        if open_positions and not trading_manager.is_monitoring_active():
            symbols = list(set([pos['trading_pair'] for pos in open_positions]))
            trading_manager.start_monitoring(symbols)
            logger.info(f"启动价格监控: {symbols}")
        
        # 存储投资组合状态到数据库
        _store_portfolio_status(portfolio_summary)
        
        return True
        
    except Exception as e:
        logger.error(f"监控仓位任务失败: {e}")
        return False

def update_account_balances():
    """更新账户余额任务"""
    logger.info("开始更新账户余额...")
    
    try:
        trading_manager = get_trading_manager()
        if not trading_manager:
            logger.error("交易管理器未初始化")
            return False
        
        # 更新账户余额
        success = trading_manager.trading_executor.update_account_balance()
        
        if success:
            logger.info("账户余额更新成功")
        else:
            logger.error("账户余额更新失败")
        
        return success
        
    except Exception as e:
        logger.error(f"更新账户余额任务失败: {e}")
        return False

def cleanup_closed_positions():
    """清理已关闭仓位的监控任务"""
    logger.info("开始清理已关闭仓位的监控...")
    
    try:
        trading_manager = get_trading_manager()
        if not trading_manager:
            logger.error("交易管理器未初始化")
            return False
        
        # 获取所有已关闭的仓位
        config = load_config()
        db_config = get_db_config(config)
        db_manager = DatabaseManager(db_config)
        
        with db_manager.get_connection() as (connection, cursor):
            cursor.execute("""
                SELECT id, trading_pair FROM positions 
                WHERE status = 'CLOSED' 
                AND last_updated >= DATE_SUB(NOW(), INTERVAL 1 HOUR)
            """)
            
            closed_positions = cursor.fetchall()
            
            for position_id, trading_pair in closed_positions:
                # 移除价格监控触发器
                trading_manager.price_monitor.remove_triggers_for_position(trading_pair, position_id)
                logger.info(f"移除已关闭仓位的监控: {trading_pair} - {position_id}")
        
        logger.info(f"清理了{len(closed_positions)}个已关闭仓位的监控")
        return True
        
    except Exception as e:
        logger.error(f"清理已关闭仓位监控任务失败: {e}")
        return False

def _get_latest_trading_strategies() -> List[Dict[str, Any]]:
    """获取最新的交易策略"""
    try:
        config = load_config()
        db_config = get_db_config(config)
        db_manager = DatabaseManager(db_config)
        
        with db_manager.get_connection() as (connection, cursor):
            # 获取今日生成的策略，且未执行的
            cursor.execute("""
                SELECT * FROM trading_strategies 
                WHERE DATE(decision_timestamp) = CURDATE()
                AND position_type != 'NEUTRAL'
                AND id NOT IN (
                    SELECT DISTINCT related_strategy_id 
                    FROM positions 
                    WHERE related_strategy_id IS NOT NULL
                )
                ORDER BY decision_timestamp DESC
            """)
            
            results = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description]
            
            strategies = []
            for result in results:
                strategy = dict(zip(columns, result))
                strategies.append(strategy)
            
            return strategies
            
    except Exception as e:
        logger.error(f"获取交易策略失败: {e}")
        return []

def _update_strategy_execution_status(strategy_id: int, status: str, message: str):
    """更新策略执行状态"""
    try:
        config = load_config()
        db_config = get_db_config(config)
        db_manager = DatabaseManager(db_config)
        
        with db_manager.get_connection() as (connection, cursor):
            # 这里可以添加一个执行状态字段到trading_strategies表
            # 或者创建一个新的策略执行记录表
            logger.info(f"策略{strategy_id}执行状态: {status} - {message}")
            
    except Exception as e:
        logger.error(f"更新策略执行状态失败: {e}")

def _store_portfolio_status(portfolio_summary: Dict[str, Any]):
    """存储投资组合状态到数据库"""
    try:
        config = load_config()
        db_config = get_db_config(config)
        db_manager = DatabaseManager(db_config)
        
        with db_manager.get_connection() as (connection, cursor):
            # 更新或插入今日的盈亏统计
            today = datetime.date.today()
            
            cursor.execute("""
                INSERT INTO daily_profit_loss 
                (date, total_unrealized_profit_loss, portfolio_value, calculation_details)
                VALUES (%s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                total_unrealized_profit_loss = VALUES(total_unrealized_profit_loss),
                portfolio_value = VALUES(portfolio_value),
                calculation_details = VALUES(calculation_details)
            """, (
                today,
                portfolio_summary.get('total_unrealized_pnl', 0),
                portfolio_summary.get('balances', {}).get('USDT', 0),
                f"开放仓位: {portfolio_summary.get('open_positions', 0)}, 保证金使用: {portfolio_summary.get('total_margin_used', 0)}"
            ))
            
            connection.commit()
            
    except Exception as e:
        logger.error(f"存储投资组合状态失败: {e}")

# 如果直接运行此脚本，执行测试
if __name__ == "__main__":
    print("执行交易任务测试...")
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    try:
        print("1. 测试更新账户余额...")
        update_account_balances()
        
        print("\n2. 测试监控仓位...")
        monitor_positions()
        
        print("\n3. 测试执行交易策略...")
        execute_trading_strategies()
        
        print("\n4. 测试清理已关闭仓位...")
        cleanup_closed_positions()
        
        print("\n测试完成")
        
    except Exception as e:
        print(f"测试失败: {e}")
    
    # 停止价格监控
    trading_manager = get_trading_manager()
    if trading_manager:
        trading_manager.stop_monitoring()
