#!/usr/bin/env python3.11
# -*- coding: utf-8 -*-
"""
加密货币交易策略AI决策模块
使用AI生成加密货币交易策略
"""
import os
import sys
import json
import datetime
import logging
import requests
import time
from typing import Dict, Any, List, Optional, Tuple, Tuple, Union

# 确保app目录在Python路径中
APP_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if APP_DIR not in sys.path:
    sys.path.insert(0, APP_DIR)

from app.database.db_manager import DatabaseManager

# 配置日志
logger = logging.getLogger('trading_strategy_ai')

def generate_trading_strategy(
    db_config: Dict[str, Any],
    openai_api_key: str,
    sealos_api_url: str,
    target_date_str: Optional[str] = None,
    trading_pairs: List[str] = ["BTCUSDT", "ETHUSDT"],
    ai_model_name: str = "gpt-3.5-turbo"  # 添加模型名称参数，默认为gpt-3.5-turbo
) -> bool:
    """
    获取每日汇总数据，发送给AI，获取交易策略并存储

    Args:
        db_config (Dict[str, Any]): 数据库配置
        openai_api_key (str): OpenAI API密钥
        sealos_api_url (str): Sealos AI Proxy URL
        target_date_str (Optional[str]): 目标日期，格式为'YYYY-MM-DD'，默认为今天
        trading_pairs (List[str]): 要生成策略的交易对列表

    Returns:
        bool: 操作是否成功
    """
    if target_date_str:
        try:
            target_date = datetime.datetime.strptime(target_date_str, "%Y-%m-%d").date()
        except ValueError:
            logger.error(f"无效的日期格式: {target_date_str}，请使用YYYY-MM-DD格式")
            return False
    else:
        target_date = datetime.date.today()

    logger.info(f"开始为{target_date.strftime('%Y-%m-%d')}生成加密货币交易策略...")

    db_manager = DatabaseManager(db_config)

    # 1. 获取每日汇总数据
    try:
        query_summary = """
        SELECT id, aggregated_hot_topics_summary, aggregated_market_summary,
               market_sentiment_indicator, key_market_indicators
        FROM daily_summary WHERE date = %(target_date)s
        """
        results = db_manager.execute_query(
            query_summary,
            {"target_date": target_date.strftime("%Y-%m-%d")},
            dictionary=True
        )

        if not results:
            logger.error(f"未找到{target_date.strftime('%Y-%m-%d')}的每日汇总数据，无法生成交易策略")
            return False

        summary_row = results[0]
        daily_summary_id = summary_row["id"]
        daily_summary_content = summary_row
        logger.info(f"成功获取每日汇总数据ID {daily_summary_id}")

    except Exception as err:
        logger.error(f"获取每日汇总数据时数据库错误: {err}")
        return False

    # 2. 获取每个交易对的最新价格数据
    try:
        price_data = {}
        for pair in trading_pairs:
            crypto_symbol = pair.replace("USDT", "")

            # 获取最新K线数据
            query_kline = """
            SELECT trading_pair, close_price, high_price, low_price
            FROM kline_data
            WHERE trading_pair = %(pair)s
            ORDER BY timestamp DESC
            LIMIT 1
            """
            kline_results = db_manager.execute_query(
                query_kline,
                {"pair": pair},
                dictionary=True
            )

            if kline_results:
                price_data[crypto_symbol] = {
                    "current_price": kline_results[0]["close_price"],
                    "daily_high": kline_results[0]["high_price"],
                    "daily_low": kline_results[0]["low_price"]
                }
            else:
                logger.warning(f"未找到{pair}的价格数据")
                price_data[crypto_symbol] = {
                    "current_price": "Unknown",
                    "daily_high": "Unknown",
                    "daily_low": "Unknown"
                }

        logger.info(f"成功获取{len(price_data)}个交易对的价格数据")

    except Exception as err:
        logger.error(f"获取价格数据时数据库错误: {err}")
        return False

    # 3. 构建AI提示
    market_indicators = {}
    try:
        market_indicators = json.loads(daily_summary_content.get("key_market_indicators", "{}"))
    except json.JSONDecodeError:
        logger.warning("解析市场指标JSON失败，使用空字典")

    prompt = f"""
你是一位专业的加密货币交易策略分析师。请根据以下市场数据为{target_date.strftime('%Y-%m-%d')}生成交易策略。

市场情绪: {daily_summary_content.get('market_sentiment_indicator', 'Neutral')}

热点话题摘要:
{daily_summary_content.get('aggregated_hot_topics_summary', 'No data')}

市场概况:
{daily_summary_content.get('aggregated_market_summary', 'No data')}

当前价格数据:
"""

    for symbol, data in price_data.items():
        prompt += f"{symbol}: 当前价格 {data['current_price']} USDT, 日内高点 {data['daily_high']} USDT, 日内低点 {data['daily_low']} USDT\n"

    prompt += """
请为以下加密货币提供交易策略建议:
"""

    for pair in trading_pairs:
        crypto_symbol = pair.replace("USDT", "")
        prompt += f"- {crypto_symbol} ({pair})\n"

    prompt += """
对于每个加密货币，请提供以下格式的策略:

1. 交易对: [交易对名称]
2. 仓位类型: [LONG/SHORT/NEUTRAL]
3. 入场价格: [建议入场价格]
4. 止损价格: [止损价格]
5. 止盈价格: [止盈价格]
6. 仓位大小: [占总资金百分比]
7. 杠杆倍数: [建议杠杆倍数，如果适用]
8. 理由: [详细分析理由]

请确保你的建议基于当前市场情况，并考虑技术面和基本面因素。
"""

    # 4. 调用AI获取策略建议
    strategies = []

    # 检查是否提供了有效的API密钥
    if openai_api_key == "YOUR_OPENAI_API_KEY_HERE" or not openai_api_key:
        logger.warning("OpenAI API密钥是占位符或未提供，使用模拟响应")

        # 为每个交易对生成模拟策略
        for pair in trading_pairs:
            crypto_symbol = pair.replace("USDT", "")

            # 获取当前价格（如果有）
            current_price = price_data.get(crypto_symbol, {}).get("current_price", 20000)
            if current_price == "Unknown":
                current_price = 20000 if crypto_symbol == "BTC" else 1000

            # 模拟策略
            strategy = {
                "daily_summary_id": daily_summary_id,  # 添加daily_summary_id
                "crypto_symbol": crypto_symbol,
                "trading_pair": pair,
                "position_type": "NEUTRAL",
                "entry_price_suggestion": float(current_price),
                "stop_loss_price": float(current_price) * 0.95,
                "take_profit_price": float(current_price) * 1.05,
                "position_size_percentage": 10.0,
                "leverage": 1.0,
                "reasoning": f"这是一个模拟的交易策略，基于当前市场情况。建议观望{crypto_symbol}，等待更明确的市场信号。",
                "ai_raw_response": json.dumps({"simulated": True})
            }

            strategies.append(strategy)
    else:
        logger.info("发送数据到AI API...")

        headers = {
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json"
        }

        # 使用传入的模型名称
        model_name = ai_model_name  # 使用函数参数中指定的模型名称

        # 构建请求负载，根据Sealos API的格式
        payload = {
            "model": model_name,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "max_tokens": 2000,
            "temperature": 0.7
        }

        try:
            # 使用配置中提供的API URL，不做修改
            api_url = sealos_api_url
            logger.info(f"使用API URL: {api_url}")

            # 添加重试机制
            max_retries = 3
            retry_delay = 5  # 重试间隔，单位为秒
            retry_count = 0
            last_error = None

            while retry_count < max_retries:
                try:
                    if retry_count > 0:
                        logger.info(f"第 {retry_count} 次重试请求AI API...")
                        # 每次重试前等待一段时间
                        time.sleep(retry_delay)
                        # 增加重试延迟时间，实现指数退避
                        retry_delay *= 2
                    else:
                        logger.info("正在发送请求到AI API，这可能需要一些时间...")

                    # 发送请求，增加超时时间到120秒
                    response = requests.post(api_url, headers=headers, json=payload, timeout=120)

                    # 记录响应状态
                    logger.info(f"API响应状态码: {response.status_code}")

                    # 检查响应状态码
                    if response.status_code == 200:
                        # 请求成功，记录响应内容并跳出循环
                        logger.info(f"API响应内容: {response.text}")  # 记录完整响应内容
                        response.raise_for_status()
                        ai_result = response.json()
                        raw_ai_response = ai_result.get("choices", [{}])[0].get("message", {}).get("content", "")
                        break
                    else:
                        # 请求失败，记录错误并准备重试
                        logger.warning(f"API请求返回非200状态码: {response.status_code}")
                        last_error = f"HTTP错误: {response.status_code}"
                        retry_count += 1
                        continue

                except requests.exceptions.RequestException as e:
                    # 请求异常，记录错误并准备重试
                    logger.warning(f"API请求异常: {e}")
                    last_error = str(e)
                    retry_count += 1
                    continue

            # 如果所有重试都失败，抛出最后一个错误
            if retry_count >= max_retries:
                raise requests.exceptions.RequestException(f"在 {max_retries} 次尝试后仍然失败: {last_error}")

            logger.info("成功收到AI响应")

            # 解析AI响应，获取策略和总结
            strategies, summary = parse_ai_response(raw_ai_response, trading_pairs, daily_summary_id, ai_result)

            # 如果有总结内容，存储到数据库
            if summary:
                store_strategy_summary(db_config, daily_summary_id, summary)

        except requests.exceptions.RequestException as e:
            logger.error(f"AI API请求失败: {e}")
            logger.warning("API请求失败，使用模拟响应作为备选方案")

            # 使用模拟响应作为备选方案
            strategies = []
            for pair in trading_pairs:
                crypto_symbol = pair.replace("USDT", "")

                # 获取当前价格（如果有）
                current_price = price_data.get(crypto_symbol, {}).get("current_price", 20000)
                if current_price == "Unknown":
                    current_price = 20000 if crypto_symbol == "BTC" else 1000

                # 模拟策略
                strategy = {
                    "daily_summary_id": daily_summary_id,
                    "crypto_symbol": crypto_symbol,
                    "trading_pair": pair,
                    "position_type": "NEUTRAL",
                    "entry_price_suggestion": float(current_price),
                    "stop_loss_price": float(current_price) * 0.95,
                    "take_profit_price": float(current_price) * 1.05,
                    "position_size_percentage": 10.0,
                    "leverage": 1.0,
                    "reasoning": f"这是一个模拟的交易策略（API请求失败后的备选方案），基于当前市场情况。建议观望{crypto_symbol}，等待更明确的市场信号。",
                    "ai_raw_response": json.dumps({"simulated": True, "reason": "API request failed"})
                }
                strategies.append(strategy)

            # 继续执行，使用模拟策略

            # 生成模拟总结
            mock_summary = f"根据当前市场情况，建议对大多数加密货币保持谨慎态度。由于API请求失败，这是一个模拟的总结，建议等待更明确的市场信号。"
            store_strategy_summary(db_config, daily_summary_id, mock_summary)

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            logger.error(f"解析AI API响应时出错: {e}")
            logger.warning("API响应解析失败，使用模拟响应作为备选方案")

            # 使用模拟响应作为备选方案
            strategies = []
            for pair in trading_pairs:
                crypto_symbol = pair.replace("USDT", "")

                # 获取当前价格（如果有）
                current_price = price_data.get(crypto_symbol, {}).get("current_price", 20000)
                if current_price == "Unknown":
                    current_price = 20000 if crypto_symbol == "BTC" else 1000

                # 模拟策略
                strategy = {
                    "daily_summary_id": daily_summary_id,
                    "crypto_symbol": crypto_symbol,
                    "trading_pair": pair,
                    "position_type": "NEUTRAL",
                    "entry_price_suggestion": float(current_price),
                    "stop_loss_price": float(current_price) * 0.95,
                    "take_profit_price": float(current_price) * 1.05,
                    "position_size_percentage": 10.0,
                    "leverage": 1.0,
                    "reasoning": f"这是一个模拟的交易策略（API响应解析失败后的备选方案），基于当前市场情况。建议观望{crypto_symbol}，等待更明确的市场信号。",
                    "ai_raw_response": json.dumps({"simulated": True, "reason": "API response parsing failed"})
                }
                strategies.append(strategy)

            # 继续执行，使用模拟策略

            # 生成模拟总结
            mock_summary = f"根据当前市场情况，建议对大多数加密货币保持谨慎态度。由于API响应解析失败，这是一个模拟的总结，建议等待更明确的市场信号。"
            store_strategy_summary(db_config, daily_summary_id, mock_summary)

    # 5. 存储策略到数据库
    if not strategies:
        logger.error("未能生成任何交易策略")
        return False

    success = store_trading_strategies(db_config, strategies)
    return success

def parse_ai_response(
    raw_response: str,
    trading_pairs: List[str],
    daily_summary_id: int,
    ai_result: Dict[str, Any]
) -> Tuple[List[Dict[str, Any]], str]:
    """
    解析AI响应，提取交易策略和总结

    Args:
        raw_response (str): AI原始响应文本
        trading_pairs (List[str]): 交易对列表
        daily_summary_id (int): 每日汇总数据ID
        ai_result (Dict[str, Any]): AI API完整响应

    Returns:
        Tuple[List[Dict[str, Any]], str]: 解析后的交易策略列表和总结内容
    """
    strategies = []
    summary = ""  # 用于存储总结内容

    # 将原始响应分割为每个交易对的部分
    sections = []

    # 尝试提取总结部分
    if "### 总结" in raw_response:
        summary_parts = raw_response.split("### 总结")
        if len(summary_parts) > 1:
            summary = summary_parts[1].strip()
            logger.info("成功提取总结部分")
            # 从原始响应中移除总结部分，以便更好地分割交易对部分
            raw_response = summary_parts[0]

    # 尝试不同的分割方法
    if "#### " in raw_response:
        # deepseek-chat模型的格式
        logger.info("检测到deepseek-chat格式的响应")
        crypto_sections = raw_response.split("#### ")
        # 跳过第一部分（通常是介绍性文本）
        for section in crypto_sections[1:]:
            if section.strip():
                sections.append(section)
    elif "1. 交易对:" in raw_response:
        # 原始格式
        sections = raw_response.split("1. 交易对:")[1:]
    elif "交易对:" in raw_response:
        # 备选格式
        sections = raw_response.split("交易对:")[1:]
    else:
        logger.warning("AI响应格式不符合预期，尝试其他分割方法")
        # 尝试按数字序号分割
        import re
        pattern = r'\d+\.\s+[A-Z]+'
        matches = re.finditer(pattern, raw_response)
        start_positions = [m.start() for m in matches]

        if start_positions:
            for i in range(len(start_positions)):
                start = start_positions[i]
                end = start_positions[i+1] if i+1 < len(start_positions) else len(raw_response)
                sections.append(raw_response[start:end])

    # 处理所有部分
    for section in sections:
        try:
            lines = section.strip().split("\n")

            # 初始化策略字典
            strategy = {
                "daily_summary_id": daily_summary_id,
                "crypto_symbol": "",
                "trading_pair": "",
                "position_type": "NEUTRAL",
                "entry_price_suggestion": 0.0,
                "stop_loss_price": 0.0,
                "take_profit_price": 0.0,
                "position_size_percentage": 0.0,
                "leverage": 1.0,
                "reasoning": "",
                "ai_raw_response": json.dumps(ai_result)
            }

            # 解析交易对
            first_line = lines[0].strip()

            # 处理deepseek-chat格式的响应
            if "(" in first_line and ")" in first_line:
                # 格式如 "1. BTC (BTCUSDT)"
                crypto_symbol = ""
                trading_pair = ""

                # 提取括号中的交易对
                import re
                match = re.search(r'\(([^)]+)\)', first_line)
                if match:
                    trading_pair = match.group(1)

                # 提取括号前的加密货币符号
                match = re.search(r'(\w+)\s*\(', first_line)
                if match:
                    crypto_symbol = match.group(1)

                if trading_pair in trading_pairs:
                    strategy["trading_pair"] = trading_pair
                    strategy["crypto_symbol"] = crypto_symbol
                elif crypto_symbol:
                    # 尝试根据加密货币符号匹配交易对
                    for pair in trading_pairs:
                        if crypto_symbol in pair:
                            strategy["trading_pair"] = pair
                            strategy["crypto_symbol"] = crypto_symbol
                            break
            else:
                # 原始格式
                trading_pair_line = first_line
                for pair in trading_pairs:
                    if pair in trading_pair_line or pair.replace("USDT", "") in trading_pair_line:
                        strategy["trading_pair"] = pair
                        strategy["crypto_symbol"] = pair.replace("USDT", "")
                        break

            if not strategy["trading_pair"]:
                logger.warning(f"无法识别交易对: {trading_pair_line}")
                continue

            # 解析其他字段
            for line in lines:
                line = line.strip()

                # 移除行首的数字编号（如 "2. 仓位类型:" 变为 "仓位类型:"）
                import re
                numbered_line_match = re.match(r'^\d+\.\s+(.*)', line)
                if numbered_line_match:
                    line_without_number = numbered_line_match.group(1)
                else:
                    line_without_number = line

                # 处理各种格式的仓位类型
                if any(pattern in line_without_number for pattern in ["仓位类型:", "Position Type:", "Position:"]):
                    try:
                        # 提取冒号后的内容
                        position_type = line.split(":", 1)[1].strip().upper() if ":" in line else ""

                        if "LONG" in position_type:
                            strategy["position_type"] = "LONG"
                        elif "SHORT" in position_type:
                            strategy["position_type"] = "SHORT"
                        else:
                            strategy["position_type"] = "NEUTRAL"
                    except (IndexError, AttributeError):
                        logger.warning(f"无法解析仓位类型: {line}")

                # 处理各种格式的入场价格
                elif any(pattern in line_without_number for pattern in ["入场价格:", "Entry Price:"]):
                    try:
                        if ":" in line:
                            price_str = line.split(":", 1)[1].strip()
                            # 处理 "N/A" 或空值情况
                            if price_str.upper() == "N/A" or not price_str:
                                logger.warning(f"无法解析入场价格: {line}")
                                continue

                            # 提取数字部分
                            import re
                            price_match = re.search(r'(\d+(?:\.\d+)?)', price_str)
                            if price_match:
                                price_str = price_match.group(1)
                                strategy["entry_price_suggestion"] = float(price_str)
                            else:
                                logger.warning(f"无法从字符串中提取价格: {price_str}")
                    except (ValueError, IndexError):
                        logger.warning(f"无法解析入场价格: {line}")

                # 处理各种格式的止损价格
                elif any(pattern in line_without_number for pattern in ["止损价格:", "Stop Loss:"]):
                    try:
                        if ":" in line:
                            price_str = line.split(":", 1)[1].strip()
                            # 处理 "N/A" 或空值情况
                            if price_str.upper() == "N/A" or not price_str:
                                logger.warning(f"无法解析止损价格: {line}")
                                continue

                            # 提取数字部分
                            import re
                            price_match = re.search(r'(\d+(?:\.\d+)?)', price_str)
                            if price_match:
                                price_str = price_match.group(1)
                                strategy["stop_loss_price"] = float(price_str)
                            else:
                                logger.warning(f"无法从字符串中提取价格: {price_str}")
                    except (ValueError, IndexError):
                        logger.warning(f"无法解析止损价格: {line}")

                # 处理各种格式的止盈价格
                elif any(pattern in line_without_number for pattern in ["止盈价格:", "Take Profit:"]):
                    try:
                        if ":" in line:
                            price_str = line.split(":", 1)[1].strip()
                            # 处理 "N/A" 或空值情况
                            if price_str.upper() == "N/A" or not price_str:
                                logger.warning(f"无法解析止盈价格: {line}")
                                continue

                            # 提取数字部分
                            import re
                            price_match = re.search(r'(\d+(?:\.\d+)?)', price_str)
                            if price_match:
                                price_str = price_match.group(1)
                                strategy["take_profit_price"] = float(price_str)
                            else:
                                logger.warning(f"无法从字符串中提取价格: {price_str}")
                    except (ValueError, IndexError):
                        logger.warning(f"无法解析止盈价格: {line}")

                # 处理各种格式的仓位大小
                elif any(pattern in line_without_number for pattern in ["仓位大小:", "Position Size:"]):
                    try:
                        if ":" in line:
                            size_str = line.split(":", 1)[1].strip()
                            # 提取百分比数字
                            import re
                            size_match = re.search(r'(\d+(?:\.\d+)?)\s*%?', size_str)
                            if size_match:
                                size_str = size_match.group(1)
                                strategy["position_size_percentage"] = float(size_str)
                            else:
                                logger.warning(f"无法从字符串中提取百分比: {size_str}")
                    except (ValueError, IndexError):
                        logger.warning(f"无法解析仓位大小: {line}")

                # 处理各种格式的杠杆倍数
                elif any(pattern in line_without_number for pattern in ["杠杆倍数:", "Leverage:"]):
                    try:
                        if ":" in line:
                            leverage_str = line.split(":", 1)[1].strip()
                            # 处理 "N/A" 或空值情况
                            if leverage_str.upper() == "N/A" or not leverage_str:
                                logger.warning(f"无法解析杠杆倍数: {line}")
                                continue

                            # 提取数字部分
                            import re
                            leverage_match = re.search(r'(\d+(?:\.\d+)?)\s*[xX]?', leverage_str)
                            if leverage_match:
                                leverage_str = leverage_match.group(1)
                                strategy["leverage"] = float(leverage_str)
                            else:
                                logger.warning(f"无法从字符串中提取杠杆倍数: {leverage_str}")
                    except (ValueError, IndexError):
                        logger.warning(f"无法解析杠杆倍数: {line}")

                # 处理各种格式的理由
                elif any(pattern in line_without_number for pattern in ["理由:", "Reasoning:"]):
                    try:
                        reasoning_parts = []
                        reasoning_index = lines.index(line)

                        # 提取冒号后的内容作为第一行
                        if ":" in line:
                            first_part = line.split(":", 1)[1].strip()
                            if first_part:  # 如果冒号后有内容
                                reasoning_parts.append(first_part)

                        # 收集理由的所有后续行，直到遇到分隔符或结束
                        for i in range(reasoning_index + 1, len(lines)):
                            next_line = lines[i].strip()
                            # 如果遇到分隔符或新的交易对，停止收集
                            if "---" in next_line or "###" in next_line:
                                break
                            reasoning_parts.append(next_line)

                        # 如果找到了理由内容
                        if reasoning_parts:
                            strategy["reasoning"] = " ".join(reasoning_parts)
                        else:
                            logger.warning(f"理由部分为空: {line}")
                    except (IndexError, ValueError):
                        logger.warning(f"无法解析理由: {line}")

            strategies.append(strategy)
            logger.info(f"成功解析{strategy['trading_pair']}的交易策略")

        except Exception as e:
            logger.error(f"解析策略部分时出错: {e}")
            continue

    return strategies, summary

def store_strategy_summary(db_config: Dict[str, Any], daily_summary_id: int, summary: str) -> bool:
    """
    将交易策略总结存储到数据库

    Args:
        db_config (Dict[str, Any]): 数据库配置
        daily_summary_id (int): 每日汇总数据ID
        summary (str): 总结内容

    Returns:
        bool: 操作是否成功
    """
    if not summary:
        logger.warning("没有总结内容可存储")
        return False

    db_manager = DatabaseManager(db_config)

    try:
        with db_manager.get_connection() as (connection, cursor):
            # 检查表是否存在
            check_table_sql = """
            SELECT COUNT(*)
            FROM information_schema.tables
            WHERE table_schema = %s
            AND table_name = 'trading_strategy_summaries'
            """
            cursor.execute(check_table_sql, (db_config["DB_NAME"],))
            table_exists = cursor.fetchone()[0] > 0

            # 如果表不存在，创建表
            if not table_exists:
                create_table_sql = """
                CREATE TABLE `trading_strategy_summaries` (
                  `id` INT NOT NULL AUTO_INCREMENT,
                  `decision_timestamp` DATETIME NOT NULL,
                  `daily_summary_id` INT NOT NULL,
                  `summary_content` TEXT NOT NULL,
                  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (`id`),
                  KEY `idx_daily_summary_id` (`daily_summary_id`),
                  KEY `idx_decision_timestamp` (`decision_timestamp`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                """
                cursor.execute(create_table_sql)
                logger.info("成功创建交易策略总结表")

            # 存储总结
            add_summary_sql = """
            INSERT INTO trading_strategy_summaries
            (decision_timestamp, daily_summary_id, summary_content)
            VALUES (NOW(), %s, %s)
            """
            cursor.execute(add_summary_sql, (daily_summary_id, summary))
            connection.commit()
            logger.info("成功存储交易策略总结")
            return True

    except Exception as err:
        logger.error(f"存储交易策略总结时出错: {err}")
        return False

def store_trading_strategies(db_config: Dict[str, Any], strategies: List[Dict[str, Any]]) -> bool:
    """
    将交易策略存储到数据库

    Args:
        db_config (Dict[str, Any]): 数据库配置
        strategies (List[Dict[str, Any]]): 交易策略列表

    Returns:
        bool: 操作是否成功
    """
    if not strategies:
        logger.warning("没有交易策略可存储")
        return False

    db_manager = DatabaseManager(db_config)
    stored_count = 0

    try:
        with db_manager.get_connection() as (connection, cursor):
            add_strategy_sql = ("""
            INSERT INTO trading_strategies
            (decision_timestamp, daily_summary_id, crypto_symbol, trading_pair, position_type,
             entry_price_suggestion, stop_loss_price, take_profit_price, position_size_percentage,
             leverage, reasoning, ai_raw_response)
            VALUES (NOW(), %(daily_summary_id)s, %(crypto_symbol)s, %(trading_pair)s, %(position_type)s,
                    %(entry_price_suggestion)s, %(stop_loss_price)s, %(take_profit_price)s,
                    %(position_size_percentage)s, %(leverage)s, %(reasoning)s, %(ai_raw_response)s)
            """)

            for strategy in strategies:
                try:
                    cursor.execute(add_strategy_sql, strategy)
                    stored_count += 1
                except Exception as err:
                    logger.error(f"数据库错误，无法存储{strategy.get('trading_pair')}的交易策略: {err}")

            connection.commit()
            logger.info(f"成功存储了{stored_count}个交易策略")
            return stored_count > 0

    except Exception as err:
        logger.error(f"连接数据库或执行查询时出错: {err}")
        return False

# 如果直接运行此脚本，执行测试
if __name__ == "__main__":
    print("执行trading_strategy_ai.py作为独立脚本（用于测试）")

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # 使用统一的配置加载方式
    try:
        from app.utils import load_config, get_db_config
        config = load_config()
        db_config = get_db_config(config)
        openai_api_key = config.OPENAI_API_KEY
        sealos_api_url = config.SEALOS_API_URL
        print("成功加载配置文件")
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        print("使用测试配置...")
        # 测试配置
        openai_api_key = "YOUR_OPENAI_API_KEY_HERE"
        sealos_api_url = "https://api.sealos.run/openai/v1/chat/completions"
        db_config = {
            "DB_HOST": "localhost",
            "DB_PORT": 3306,
            "DB_USER": "your_db_user",
            "DB_PASSWORD": "your_db_password",
            "DB_NAME": "crypto_trading"
        }

    if db_config["DB_USER"] == "your_db_user" or openai_api_key == "YOUR_OPENAI_API_KEY_HERE":
        print("警告: 使用占位符数据库凭据或OpenAI API密钥进行直接脚本执行")
        print("该过程将使用模拟的API调用运行，如果未配置，数据库操作可能会失败")

    # 确保数据库中存在当天的每日汇总数据
    print("在运行此测试之前，请确保数据库中存在目标日期的daily_summary记录")

    # 使用今天的日期进行测试
    success = generate_trading_strategy(
        db_config=db_config,
        openai_api_key=openai_api_key,
        sealos_api_url=sealos_api_url,
        trading_pairs=["BTCUSDT", "ETHUSDT", "SOLUSDT"]
    )

    # 使用特定日期进行测试
    # success = generate_trading_strategy(
    #     db_config=db_config,
    #     openai_api_key=openai_api_key,
    #     sealos_api_url=sealos_api_url,
    #     target_date_str="2023-05-13",
    #     trading_pairs=["BTCUSDT", "ETHUSDT"]
    # )

    if success:
        print("AI交易策略生成过程成功完成（来自测试调用）")
    else:
        print("AI交易策略生成过程失败或未生成/存储策略（来自测试调用）")
