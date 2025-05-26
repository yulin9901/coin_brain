#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
Binance数据收集模块
用于从Binance API获取加密货币市场数据
"""
import os
import sys
import time
import json
import datetime
import logging
from typing import List, Dict, Any, Optional, Union, Tuple

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from binance.client import Client
from binance.exceptions import BinanceAPIException, BinanceRequestException
from app.database.db_manager import DatabaseManager

# 配置日志
logger = logging.getLogger('binance_data_collector')

def initialize_binance_client(api_key: str, api_secret: str, testnet: bool = True) -> Client:
    """
    初始化Binance API客户端

    Args:
        api_key (str): Binance API Key
        api_secret (str): Binance API Secret
        testnet (bool): 是否使用测试网络

    Returns:
        Client: Binance API客户端实例
    """
    try:
        client = Client(api_key, api_secret, testnet=testnet)
        # 测试连接
        server_time = client.get_server_time()
        logger.info(f"成功连接到Binance API，服务器时间: {datetime.datetime.fromtimestamp(server_time['serverTime']/1000)}")
        return client
    except (BinanceAPIException, BinanceRequestException) as e:
        logger.error(f"连接Binance API失败: {e}")
        return None

def fetch_crypto_price_data(client: Client, symbol: str = 'BTCUSDT') -> Dict[str, Any]:
    """
    获取加密货币当前价格数据

    Args:
        client (Client): Binance API客户端实例
        symbol (str): 交易对，例如：BTCUSDT

    Returns:
        Dict[str, Any]: 价格数据字典
    """
    try:
        ticker = client.get_ticker(symbol=symbol)
        price_data = {
            'symbol': symbol,
            'price': float(ticker['lastPrice']),
            'price_change': float(ticker['priceChange']),
            'price_change_percent': float(ticker['priceChangePercent']),
            'volume_24h': float(ticker['volume']),
            'high_24h': float(ticker['highPrice']),
            'low_24h': float(ticker['lowPrice']),
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'retrieved_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        logger.info(f"成功获取{symbol}价格数据: {price_data['price']} USDT")
        return price_data
    except (BinanceAPIException, BinanceRequestException) as e:
        logger.error(f"获取{symbol}价格数据失败: {e}")
        return None

def fetch_kline_data(client: Client, symbol: str = 'BTCUSDT', interval: str = '1h', limit: int = 100) -> List[Dict[str, Any]]:
    """
    获取加密货币K线数据

    Args:
        client (Client): Binance API客户端实例
        symbol (str): 交易对，例如：BTCUSDT
        interval (str): K线间隔，例如：1m, 5m, 1h, 1d
        limit (int): 获取的K线数量，最大1000

    Returns:
        List[Dict[str, Any]]: K线数据列表
    """
    try:
        klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
        kline_data = []

        for k in klines:
            timestamp = datetime.datetime.fromtimestamp(k[0] / 1000)
            kline_point = {
                'trading_pair': symbol,
                'interval_type': interval,
                'timestamp': timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                'open_price': float(k[1]),
                'high_price': float(k[2]),
                'low_price': float(k[3]),
                'close_price': float(k[4]),
                'volume': float(k[5]),
                'quote_asset_volume': float(k[7]),
                'number_of_trades': int(k[8]),
                'taker_buy_base_volume': float(k[9]),
                'taker_buy_quote_volume': float(k[10]),
                'retrieved_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            kline_data.append(kline_point)

        logger.info(f"成功获取{symbol} {interval}周期K线数据，共{len(kline_data)}条")
        return kline_data
    except (BinanceAPIException, BinanceRequestException) as e:
        logger.error(f"获取{symbol} {interval}周期K线数据失败: {e}")
        return None

def fetch_funding_rate_data(client: Client, symbol: str = 'BTCUSDT') -> Dict[str, Any]:
    """
    获取合约资金费率数据

    Args:
        client (Client): Binance API客户端实例
        symbol (str): 交易对，例如：BTCUSDT

    Returns:
        Dict[str, Any]: 资金费率数据字典
    """
    try:
        # 注意：此API需要合约API权限
        funding_rate = client.futures_funding_rate(symbol=symbol, limit=1)[0]

        funding_data = {
            'symbol': symbol,
            'funding_rate': float(funding_rate['fundingRate']),
            'funding_time': datetime.datetime.fromtimestamp(funding_rate['fundingTime'] / 1000).strftime("%Y-%m-%d %H:%M:%S"),
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'retrieved_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        logger.info(f"成功获取{symbol}资金费率数据: {funding_data['funding_rate']}")
        return funding_data
    except (BinanceAPIException, BinanceRequestException) as e:
        logger.error(f"获取{symbol}资金费率数据失败: {e}")
        return None

def fetch_open_interest_data(client: Client, symbol: str = 'BTCUSDT') -> Dict[str, Any]:
    """
    获取合约未平仓量数据

    Args:
        client (Client): Binance API客户端实例
        symbol (str): 交易对，例如：BTCUSDT

    Returns:
        Dict[str, Any]: 未平仓量数据字典
    """
    try:
        # 注意：此API需要合约API权限
        open_interest = client.futures_open_interest(symbol=symbol)

        interest_data = {
            'symbol': symbol,
            'open_interest': float(open_interest['openInterest']),
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'retrieved_at': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        logger.info(f"成功获取{symbol}未平仓量数据: {interest_data['open_interest']}")
        return interest_data
    except (BinanceAPIException, BinanceRequestException) as e:
        logger.error(f"获取{symbol}未平仓量数据失败: {e}")
        return None

def fetch_market_fund_flow_data(client: Client, symbols: List[str] = ['BTCUSDT', 'ETHUSDT']) -> List[Dict[str, Any]]:
    """
    获取多个加密货币的市场资金流向数据

    Args:
        client (Client): Binance API客户端实例
        symbols (List[str]): 交易对列表

    Returns:
        List[Dict[str, Any]]: 市场资金流向数据列表
    """
    market_data_list = []
    current_time = datetime.datetime.now()

    for symbol in symbols:
        try:
            # 获取24小时价格变动
            ticker = client.get_ticker(symbol=symbol)

            # 获取资金费率（如果可用）
            try:
                funding_rate = client.futures_funding_rate(symbol=symbol, limit=1)[0]['fundingRate']
            except:
                funding_rate = 0

            # 获取未平仓量（如果可用）
            try:
                open_interest = client.futures_open_interest(symbol=symbol)['openInterest']
            except:
                open_interest = 0

            # 计算加密货币符号（例如：从BTCUSDT提取BTC）
            crypto_symbol = symbol.replace('USDT', '')

            market_data = {
                "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
                "crypto_symbol": crypto_symbol,
                "inflow_amount": float(ticker['quoteVolume']) * 0.01,  # 这里用成交量的1%作为净流入的估计值
                "change_rate": float(ticker['priceChangePercent']),
                "volume_24h": float(ticker['volume']),
                "funding_rate": float(funding_rate),
                "open_interest": float(open_interest),
                "liquidations_24h": 0,  # 需要额外API获取，此处暂设为0
                "data_source": "Binance API",
                "retrieved_at": current_time.strftime("%Y-%m-%d %H:%M:%S")
            }

            market_data_list.append(market_data)
            logger.info(f"成功获取{symbol}市场资金流向数据")

        except (BinanceAPIException, BinanceRequestException) as e:
            logger.error(f"获取{symbol}市场资金流向数据失败: {e}")
            continue

    return market_data_list

def store_market_fund_flow_data(db_config: Dict[str, Any], flows_data: List[Dict[str, Any]]) -> int:
    """
    将市场资金流向数据存储到数据库

    Args:
        db_config (Dict[str, Any]): 数据库配置
        flows_data (List[Dict[str, Any]]): 市场资金流向数据列表

    Returns:
        int: 成功插入的记录数
    """
    if not flows_data:
        logger.warning("没有市场资金流向数据可存储")
        return 0

    db_manager = DatabaseManager(db_config)
    inserted_count = 0

    try:
        with db_manager.get_connection() as (connection, cursor):
            add_flow_sql = ("""
            INSERT INTO market_fund_flows
            (timestamp, crypto_symbol, inflow_amount, change_rate, volume_24h, funding_rate, open_interest, liquidations_24h, data_source, retrieved_at)
            VALUES (%(timestamp)s, %(crypto_symbol)s, %(inflow_amount)s, %(change_rate)s, %(volume_24h)s, %(funding_rate)s, %(open_interest)s, %(liquidations_24h)s, %(data_source)s, %(retrieved_at)s)
            ON DUPLICATE KEY UPDATE
            inflow_amount=VALUES(inflow_amount),
            change_rate=VALUES(change_rate),
            volume_24h=VALUES(volume_24h),
            funding_rate=VALUES(funding_rate),
            open_interest=VALUES(open_interest),
            liquidations_24h=VALUES(liquidations_24h),
            retrieved_at=VALUES(retrieved_at)
            """)

            for flow_item in flows_data:
                try:
                    cursor.execute(add_flow_sql, flow_item)
                    inserted_count += 1
                except Exception as err:
                    logger.error(f"数据库错误，无法存储{flow_item.get('crypto_symbol')}的资金流向数据: {err}")

            connection.commit()
            logger.info(f"成功存储了{inserted_count}条市场资金流向数据")

    except Exception as err:
        logger.error(f"连接数据库或执行查询时出错: {err}")
        return 0

    return inserted_count

def store_kline_data(db_config: Dict[str, Any], kline_data: List[Dict[str, Any]]) -> int:
    """
    将K线数据存储到数据库

    Args:
        db_config (Dict[str, Any]): 数据库配置
        kline_data (List[Dict[str, Any]]): K线数据列表

    Returns:
        int: 成功插入的记录数
    """
    if not kline_data:
        logger.warning("没有K线数据可存储")
        return 0

    db_manager = DatabaseManager(db_config)
    inserted_count = 0

    try:
        with db_manager.get_connection() as (connection, cursor):
            add_kline_sql = ("""
            INSERT INTO kline_data
            (trading_pair, interval_type, timestamp, open_price, high_price, low_price, close_price,
             volume, quote_asset_volume, number_of_trades, taker_buy_base_volume, taker_buy_quote_volume, retrieved_at)
            VALUES (%(trading_pair)s, %(interval_type)s, %(timestamp)s, %(open_price)s, %(high_price)s, %(low_price)s,
                    %(close_price)s, %(volume)s, %(quote_asset_volume)s, %(number_of_trades)s,
                    %(taker_buy_base_volume)s, %(taker_buy_quote_volume)s, %(retrieved_at)s)
            ON DUPLICATE KEY UPDATE
            open_price=VALUES(open_price),
            high_price=VALUES(high_price),
            low_price=VALUES(low_price),
            close_price=VALUES(close_price),
            volume=VALUES(volume),
            quote_asset_volume=VALUES(quote_asset_volume),
            number_of_trades=VALUES(number_of_trades),
            taker_buy_base_volume=VALUES(taker_buy_base_volume),
            taker_buy_quote_volume=VALUES(taker_buy_quote_volume),
            retrieved_at=VALUES(retrieved_at)
            """)

            for kline_point in kline_data:
                try:
                    cursor.execute(add_kline_sql, kline_point)
                    inserted_count += 1
                except Exception as err:
                    logger.error(f"数据库错误，无法存储{kline_point.get('trading_pair')}的K线数据: {err}")

            connection.commit()
            logger.info(f"成功存储了{inserted_count}条K线数据")

    except Exception as err:
        logger.error(f"连接数据库或执行查询时出错: {err}")
        return 0

    return inserted_count

# 如果直接运行此脚本，执行测试
if __name__ == "__main__":
    print("执行binance_data_collector.py作为独立脚本（用于测试）")

    # 使用统一的配置加载方式
    try:
        from app.utils import load_config, get_db_config
        config = load_config()
        db_config = get_db_config(config)
        api_key = config.BINANCE_API_KEY
        api_secret = config.BINANCE_API_SECRET
        testnet = config.BINANCE_TESTNET

        print("成功加载配置文件")
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        print("使用测试配置...")
        # 测试配置
        api_key = "YOUR_BINANCE_API_KEY"
        api_secret = "YOUR_BINANCE_API_SECRET"
        testnet = True
        db_config = {
            "DB_HOST": "localhost",
            "DB_PORT": 3306,
            "DB_USER": "your_db_user",
            "DB_PASSWORD": "your_db_password",
            "DB_NAME": "crypto_trading"
        }

    # 初始化Binance客户端
    if api_key != "YOUR_BINANCE_API_KEY" and api_secret != "YOUR_BINANCE_API_SECRET":
        client = initialize_binance_client(api_key, api_secret, testnet)

        if client:
            # 测试获取BTC价格
            btc_price = fetch_crypto_price_data(client, "BTCUSDT")
            if btc_price:
                print(f"BTC当前价格: {btc_price['price']} USDT")

            # 测试获取K线数据
            btc_klines = fetch_kline_data(client, "BTCUSDT", "1h", 10)
            if btc_klines:
                print(f"获取到{len(btc_klines)}条BTC K线数据")

                # 如果数据库配置有效，存储K线数据
                if db_config["DB_USER"] != "your_db_user":
                    inserted = store_kline_data(db_config, btc_klines)
                    print(f"存储了{inserted}条K线数据")

            # 测试获取市场资金流向数据
            market_flows = fetch_market_fund_flow_data(client, ["BTCUSDT", "ETHUSDT"])
            if market_flows:
                print(f"获取到{len(market_flows)}条市场资金流向数据")

                # 如果数据库配置有效，存储市场资金流向数据
                if db_config["DB_USER"] != "your_db_user":
                    inserted = store_market_fund_flow_data(db_config, market_flows)
                    print(f"存储了{inserted}条市场资金流向数据")
    else:
        print("未提供有效的Binance API密钥，无法执行测试")
