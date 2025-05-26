#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
import datetime
import json
import os
import sys
from decimal import Decimal, ROUND_HALF_UP
from app.database.db_manager import DatabaseManager

# Append path for data_api module if not running in a standard environment
if os.path.exists("/opt/.manus/.sandbox-runtime"): # Check if in Manus sandbox
    sys.path.append("/opt/.manus/.sandbox-runtime")
    from data_api import ApiClient # type: ignore
else:
    # Provide a mock for ApiClient if not in Manus environment
    class ApiClient:
        def call_api(self, api_name, query):
            print(f"Mock ApiClient: Called {api_name} with query {query}")
            return {"chart": {"result": None, "error": {"code": "MOCK_ENV", "description": "ApiClient not available outside Manus sandbox"}}}

# from ...config import DB_HOST, DB_USER, DB_PASSWORD, DB_NAME # To be loaded via a config utility

def _fetch_latest_close_price_from_db(db_manager, stock_code, on_date):
    """Fetches the latest known close price for a stock on or before a given date from kline_data."""
    query = """
    SELECT close_price FROM kline_data
    WHERE stock_code = %(stock_code)s AND DATE(timestamp) <= %(on_date)s
    ORDER BY timestamp DESC LIMIT 1
    """
    results = db_manager.execute_query(
        query,
        {"stock_code": stock_code, "on_date": on_date.strftime("%Y-%m-%d")},
        dictionary=True
    )
    return Decimal(results[0]["close_price"]) if results and results[0]["close_price"] is not None else None

def _fetch_latest_close_price_from_api(api_client, stock_code, region="US"):
    """Fallback to fetch latest close price from API."""
    print(f"Attempting API fallback for latest price of {stock_code} (region: {region}).")
    try:
        api_response = api_client.call_api(
            'YahooFinance/get_stock_chart',
            query={'symbol': stock_code, 'interval': '1d', 'range': '5d', 'region': region, 'includeAdjustedClose': 'true'}
        )
        if api_response and api_response.get("chart") and api_response["chart"].get("result") and api_response["chart"]["result"][0]:
            res = api_response["chart"]["result"][0]
            if res.get("indicators", {}).get("quote", [{}])[0].get("close"):
                closes = [p for p in res["indicators"]["quote"][0]["close"] if p is not None]
                if closes:
                    return Decimal(closes[-1])
        print(f"Could not fetch latest price via API for {stock_code}.")
        return None
    except Exception as e:
        print(f"API Exception fetching price for {stock_code}: {e}")
        return None

def calculate_and_store_daily_profit_loss(db_config, api_client, target_date_str=None):
    """Calculates daily realized and unrealized P&L and stores it."""
    if target_date_str:
        try:
            target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            print(f"Invalid date format for P&L: {target_date_str}. Please use YYYY-MM-DD.")
            return False
    else:
        target_date = datetime.date.today()

    print(f"Calculating daily P&L for {target_date.strftime('%Y-%m-%d')}...")

    total_realized_pnl = Decimal("0.00")
    total_unrealized_pnl = Decimal("0.00")
    total_fees_paid_today = Decimal("0.00")
    current_portfolio_stock_value = Decimal("0.00")
    calculation_details_list = []

    db_manager = DatabaseManager(db_config)

    try:
        # 使用数据库管理器的上下文管理器
        with db_manager.get_connection(dictionary=True) as (connection, cursor):
            # Table creation should be handled by a separate schema management script or initial setup
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS daily_profit_loss (
                id INT AUTO_INCREMENT PRIMARY KEY,
                date DATE UNIQUE NOT NULL COMMENT '统计日期',
                total_realized_profit_loss DECIMAL(15, 2) DEFAULT 0.00 COMMENT '当日已实现总盈亏',
                total_unrealized_profit_loss DECIMAL(15, 2) DEFAULT 0.00 COMMENT '当日持仓未实现总盈亏',
                total_fees_paid DECIMAL(10, 2) DEFAULT 0.00 COMMENT '当日总支付费用',
                portfolio_value DECIMAL(20,2) COMMENT '当日收盘时组合总价值 (仅股票市值)',
                calculation_details TEXT COMMENT '盈亏计算的简要说明',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '统计数据创建时间'
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            # 1. Calculate Realized P&L from trades made on target_date
            query_sell_trades = """
            SELECT
                t_sell.id AS sell_trade_id, t_sell.stock_code, t_sell.quantity AS sold_quantity,
                t_sell.price AS sell_price, t_sell.commission_fee AS sell_commission, t_sell.stamp_duty AS sell_stamp_duty,
                sbd.executed_buy_price, sbd.executed_quantity AS bought_quantity_for_decision,
                (SELECT SUM(t_buy.commission_fee + IFNULL(t_buy.stamp_duty, 0) + IFNULL(t_buy.other_fees, 0)) FROM trades t_buy
                 WHERE t_buy.related_buy_decision_id = sbd.id AND t_buy.transaction_type = 'BUY'
                ) AS buy_fees_total_for_decision
            FROM trades t_sell
            JOIN stock_buy_decisions sbd ON t_sell.related_buy_decision_id = sbd.id
            WHERE t_sell.transaction_type = 'SELL' AND DATE(t_sell.transaction_time) = %(target_date)s
            """
            cursor.execute(query_sell_trades, {"target_date": target_date.strftime("%Y-%m-%d")})
            sell_trades = cursor.fetchall()

            for sell in sell_trades:
                sell_value = Decimal(str(sell["sell_price"])) * Decimal(str(sell["sold_quantity"]))
                sell_fees = Decimal(str(sell.get("sell_commission", 0))) + Decimal(str(sell.get("sell_stamp_duty", 0)))

                cost_basis_per_share = Decimal(str(sell["executed_buy_price"]))
                buy_fees_for_this_sell = Decimal("0.00")
                if sell["buy_fees_total_for_decision"] is not None and sell["bought_quantity_for_decision"] is not None and sell["bought_quantity_for_decision"] > 0:
                    buy_fees_for_this_sell = (Decimal(str(sell["buy_fees_total_for_decision"])) / Decimal(str(sell["bought_quantity_for_decision"]))) * Decimal(str(sell["sold_quantity"]))

                buy_cost_for_sold_shares = cost_basis_per_share * Decimal(str(sell["sold_quantity"])) + buy_fees_for_this_sell

                realized_pnl_for_trade = (sell_value - sell_fees) - buy_cost_for_sold_shares
                total_realized_pnl += realized_pnl_for_trade
                total_fees_paid_today += sell_fees + buy_fees_for_this_sell
                calculation_details_list.append(f"Sold {sell['stock_code']}: P&L {realized_pnl_for_trade:.2f}")

            # Add fees from BUY trades made today (that haven't been sold today)
            query_buy_trades_today = """
            SELECT commission_fee, stamp_duty, other_fees FROM trades
            WHERE transaction_type = 'BUY' AND DATE(transaction_time) = %(target_date)s
            AND related_buy_decision_id NOT IN (SELECT DISTINCT related_buy_decision_id FROM trades WHERE transaction_type = 'SELL' AND DATE(transaction_time) = %(target_date)s AND related_buy_decision_id IS NOT NULL)
            """
            cursor.execute(query_buy_trades_today, {"target_date": target_date.strftime("%Y-%m-%d")})
            for buy_trade in cursor.fetchall():
                total_fees_paid_today += Decimal(str(buy_trade.get("commission_fee",0))) + Decimal(str(buy_trade.get("stamp_duty",0))) + Decimal(str(buy_trade.get("other_fees",0)))

            # 2. Calculate Unrealized P&L for open positions at end of target_date
            query_open_positions = """
            SELECT
                sbd.id AS decision_id,
                sbd.stock_code,
                sbd.stock_name,
                sbd.executed_quantity AS quantity_held,
                sbd.executed_buy_price
            FROM stock_buy_decisions sbd
            LEFT JOIN trades t_sell ON sbd.id = t_sell.related_buy_decision_id AND t_sell.transaction_type = 'SELL'
            WHERE sbd.is_executed = TRUE AND t_sell.id IS NULL;
            """
            cursor.execute(query_open_positions)
            open_positions = cursor.fetchall()

            for pos in open_positions:
                stock_region = "US" # Default
                if ".SS" in pos['stock_code'].upper(): stock_region = "SS"
                elif ".SZ" in pos['stock_code'].upper(): stock_region = "SZ"
                elif ".HK" in pos['stock_code'].upper(): stock_region = "HK"

                latest_price = _fetch_latest_close_price_from_db(db_manager, pos["stock_code"], target_date)
                if latest_price is None:
                    latest_price = _fetch_latest_close_price_from_api(api_client, pos["stock_code"], region=stock_region)

                if latest_price is not None and pos["quantity_held"] is not None and pos["executed_buy_price"] is not None:
                    current_value = latest_price * Decimal(str(pos["quantity_held"]))
                    cost_basis = Decimal(str(pos["executed_buy_price"])) * Decimal(str(pos["quantity_held"]))
                    unrealized_pnl_for_pos = current_value - cost_basis
                    total_unrealized_pnl += unrealized_pnl_for_pos
                    current_portfolio_stock_value += current_value
                    calculation_details_list.append(f"Held {pos['stock_code']}: Unrealized P&L {unrealized_pnl_for_pos:.2f}, Value {current_value:.2f}")
                elif pos["quantity_held"] is not None and pos["executed_buy_price"] is not None:
                    cost_value = Decimal(str(pos["executed_buy_price"])) * Decimal(str(pos["quantity_held"]))
                    current_portfolio_stock_value += cost_value # Value at cost if no current price
                    calculation_details_list.append(f"Held {pos['stock_code']}: No current price, valued at cost {cost_value:.2f}.")
                else:
                     calculation_details_list.append(f"Held {pos['stock_code']}: Missing data for P&L calculation.")

            # 3. Store results
            insert_sql = ("""
            INSERT INTO daily_profit_loss
            (date, total_realized_profit_loss, total_unrealized_profit_loss, total_fees_paid, portfolio_value, calculation_details)
            VALUES (%(date)s, %(realized_pnl)s, %(unrealized_pnl)s, %(fees_paid)s, %(portfolio_val)s, %(details)s)
            ON DUPLICATE KEY UPDATE
            total_realized_profit_loss = VALUES(total_realized_profit_loss),
            total_unrealized_profit_loss = VALUES(total_unrealized_profit_loss),
            total_fees_paid = VALUES(total_fees_paid),
            portfolio_value = VALUES(portfolio_value),
            calculation_details = VALUES(calculation_details),
            created_at = CURRENT_TIMESTAMP
            """)

            pnl_data = {
                "date": target_date.strftime("%Y-%m-%d"),
                "realized_pnl": total_realized_pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                "unrealized_pnl": total_unrealized_pnl.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                "fees_paid": total_fees_paid_today.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                "portfolio_val": current_portfolio_stock_value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP),
                "details": json.dumps(calculation_details_list)
            }
            cursor.execute(insert_sql, pnl_data)
            connection.commit()
            print(f"Successfully stored P&L for {target_date.strftime('%Y-%m-%d')}.")
            print(f"Realized: {pnl_data['realized_pnl']}, Unrealized: {pnl_data['unrealized_pnl']}, Fees: {pnl_data['fees_paid']}, Portfolio Value: {pnl_data['portfolio_val']}")
            return True

    except Exception as err:
        print(f"Error during P&L calculation: {err}")
        return False

# Example of how this module might be called
if __name__ == "__main__":
    print("Executing profit_loss_calculator.py as a standalone script (for testing purposes).")

    # 使用统一的配置加载方式
    try:
        from app.utils import load_config, get_db_config
        config = load_config()
        db_config = get_db_config(config)
        print("成功加载配置文件")
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        print("使用测试配置...")
        # 测试配置
        db_config = {
            "DB_HOST": "localhost",
            "DB_PORT": 3306,
            "DB_USER": "your_db_user", # 替换为实际测试值
            "DB_PASSWORD": "your_db_password", # 替换为实际测试值
            "DB_NAME": "stock_analysis"
        }

    if db_config["DB_USER"] == "your_db_user":
        print("警告: 使用占位符数据库凭据进行直接脚本执行。")
        print("如果未配置，数据库操作可能会失败。")
        print("此脚本需要数据库中存在交易记录和K线数据。")
    else:
        api_cli = ApiClient() # 初始化ApiClient（如果不在Manus环境中，将使用模拟客户端）
        # 确保目标日期的交易记录和K线数据存在。
        print("在运行此测试之前，请确保数据库中存在目标日期的交易记录和K线数据。")
        # 使用特定日期进行测试
        # success = calculate_and_store_daily_profit_loss(db_config=db_config, api_client=api_cli, target_date_str="2025-05-13")
        success = calculate_and_store_daily_profit_loss(db_config=db_config, api_client=api_cli)
        if success:
            print("每日盈亏计算过程成功完成（来自测试调用）。")
        else:
            print("每日盈亏计算过程失败（来自测试调用）。")

