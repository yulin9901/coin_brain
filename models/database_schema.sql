-- 数据库整体设计：用于存储加密货币市场数据、热点资讯、市场流向、每日汇总、交易策略和盈亏等数据。

-- 1. 热点资讯表 (hot_topics)
CREATE TABLE IF NOT EXISTS hot_topics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '资讯发布时间或抓取时间',
    source VARCHAR(255) COMMENT '资讯来源, 例如：CoinDesk、Cointelegraph、Twitter等',
    title TEXT NOT NULL COMMENT '资讯标题',
    url VARCHAR(255) UNIQUE COMMENT '资讯原始链接',
    content_summary TEXT COMMENT '资讯内容摘要',
    sentiment ENUM('positive', 'negative', 'neutral') COMMENT '情感分析结果',
    retrieved_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据入库时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储获取的加密货币热点资讯';

-- 2. 市场资金流向表 (market_fund_flows)
CREATE TABLE IF NOT EXISTS market_fund_flows (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据观测时间点',
    crypto_symbol VARCHAR(20) COMMENT '加密货币符号，例如：BTC、ETH',
    inflow_amount DECIMAL(20, 8) COMMENT '资金净流入金额（USDT），可为负数表示流出',
    change_rate DECIMAL(10, 4) COMMENT '24小时涨跌幅',
    volume_24h DECIMAL(30, 8) COMMENT '24小时交易量',
    funding_rate DECIMAL(10, 6) COMMENT '合约资金费率',
    open_interest DECIMAL(30, 8) COMMENT '合约未平仓量',
    liquidations_24h DECIMAL(30, 8) COMMENT '24小时爆仓量',
    data_source VARCHAR(255) COMMENT '数据来源平台',
    retrieved_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据入库时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储加密货币市场资金流向数据';

-- 3. 每日数据汇总表 (daily_summary)
CREATE TABLE IF NOT EXISTS daily_summary (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE UNIQUE NOT NULL COMMENT '汇总数据的日期',
    aggregated_hot_topics_summary TEXT COMMENT '当日热点资讯汇总摘要',
    aggregated_market_summary TEXT COMMENT '当日市场概况汇总摘要',
    market_sentiment_indicator VARCHAR(100) COMMENT '市场情绪指标（例如：看涨、看跌、中性）',
    key_market_indicators TEXT COMMENT '当日关键市场指标 (JSON格式存储)',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '汇总数据创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储每日汇总后的数据';

-- 4. 交易策略决策表 (trading_strategies)
CREATE TABLE IF NOT EXISTS trading_strategies (
    id INT AUTO_INCREMENT PRIMARY KEY,
    decision_timestamp DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '决策生成时间',
    daily_summary_id INT COMMENT '关联的每日数据汇总ID',
    crypto_symbol VARCHAR(20) NOT NULL COMMENT '加密货币符号，例如：BTC、ETH',
    trading_pair VARCHAR(20) NOT NULL COMMENT '交易对，例如：BTCUSDT',
    position_type ENUM('LONG', 'SHORT', 'NEUTRAL') NOT NULL COMMENT '仓位类型：做多、做空或观望',
    entry_price_suggestion DECIMAL(20, 8) COMMENT '建议入场价格',
    stop_loss_price DECIMAL(20, 8) COMMENT '止损价格',
    take_profit_price DECIMAL(20, 8) COMMENT '止盈价格',
    position_size_percentage DECIMAL(5, 2) COMMENT '建议仓位大小（占总资金百分比）',
    leverage DECIMAL(5, 2) DEFAULT 1.00 COMMENT '杠杆倍数，默认为1（现货）',
    reasoning TEXT COMMENT 'AI给出的交易理由',
    ai_raw_response TEXT COMMENT 'AI原始回复内容',
    is_executed BOOLEAN DEFAULT FALSE COMMENT '是否已执行交易',
    executed_entry_price DECIMAL(20, 8) COMMENT '实际执行入场价格',
    executed_position_size DECIMAL(20, 8) COMMENT '实际执行仓位大小',
    executed_timestamp DATETIME COMMENT '实际执行入场时间',
    FOREIGN KEY (daily_summary_id) REFERENCES daily_summary(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储AI生成的交易策略信息';

-- 5. K线图数据表 (kline_data)
CREATE TABLE IF NOT EXISTS kline_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trading_pair VARCHAR(20) NOT NULL COMMENT '交易对，例如：BTCUSDT',
    interval_type VARCHAR(10) NOT NULL COMMENT 'K线间隔类型（1m, 5m, 1h, 1d等）',
    timestamp DATETIME NOT NULL COMMENT 'K线时间点',
    open_price DECIMAL(20, 8) NOT NULL COMMENT '开盘价',
    high_price DECIMAL(20, 8) NOT NULL COMMENT '最高价',
    low_price DECIMAL(20, 8) NOT NULL COMMENT '最低价',
    close_price DECIMAL(20, 8) NOT NULL COMMENT '收盘价',
    volume DECIMAL(30, 8) COMMENT '成交量',
    quote_asset_volume DECIMAL(30, 8) COMMENT '报价资产成交量',
    number_of_trades INT COMMENT '交易笔数',
    taker_buy_base_volume DECIMAL(30, 8) COMMENT 'Taker买入基础资产成交量',
    taker_buy_quote_volume DECIMAL(30, 8) COMMENT 'Taker买入报价资产成交量',
    retrieved_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '数据入库时间',
    UNIQUE KEY `idx_pair_interval_time` (`trading_pair`, `interval_type`, `timestamp`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储获取的加密货币K线图数据';

-- 6. 交易记录表 (trades)
CREATE TABLE IF NOT EXISTS trades (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trading_pair VARCHAR(20) NOT NULL COMMENT '交易对，例如：BTCUSDT',
    position_type ENUM('LONG', 'SHORT') NOT NULL COMMENT '仓位类型：做多或做空',
    transaction_type ENUM('OPEN', 'CLOSE') NOT NULL COMMENT '交易类型：开仓或平仓',
    transaction_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '交易执行时间',
    quantity DECIMAL(20, 8) NOT NULL COMMENT '成交数量',
    price DECIMAL(20, 8) NOT NULL COMMENT '成交价格',
    leverage DECIMAL(5, 2) DEFAULT 1.00 COMMENT '杠杆倍数',
    commission_fee DECIMAL(20, 8) DEFAULT 0.00 COMMENT '手续费',
    funding_fee DECIMAL(20, 8) DEFAULT 0.00 COMMENT '资金费用（合约）',
    other_fees DECIMAL(20, 8) DEFAULT 0.00 COMMENT '其他费用',
    total_amount DECIMAL(30, 8) COMMENT '总金额（已扣除费用）',
    pnl DECIMAL(30, 8) COMMENT '平仓时的盈亏（仅平仓交易）',
    related_strategy_id INT COMMENT '关联的交易策略ID',
    related_open_trade_id INT COMMENT '关联的开仓交易ID（如果是平仓交易）',
    close_reason TEXT COMMENT '平仓原因（如果是平仓交易）',
    FOREIGN KEY (related_strategy_id) REFERENCES trading_strategies(id) ON DELETE SET NULL,
    FOREIGN KEY (related_open_trade_id) REFERENCES trades(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='记录实际的加密货币交易操作';

-- 7. 每日盈亏统计表 (daily_profit_loss)
CREATE TABLE IF NOT EXISTS daily_profit_loss (
    id INT AUTO_INCREMENT PRIMARY KEY,
    date DATE UNIQUE NOT NULL COMMENT '统计日期',
    total_realized_profit_loss DECIMAL(30, 8) DEFAULT 0.00 COMMENT '当日已实现总盈亏',
    total_unrealized_profit_loss DECIMAL(30, 8) DEFAULT 0.00 COMMENT '当日持仓未实现总盈亏',
    total_fees_paid DECIMAL(20, 8) DEFAULT 0.00 COMMENT '当日总支付费用（手续费+资金费等）',
    portfolio_value DECIMAL(30, 8) COMMENT '当日收盘时组合总价值',
    calculation_details TEXT COMMENT '盈亏计算的简要说明或涉及的交易ID列表',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '统计数据创建时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储每日的盈亏情况';

-- 8. 回测结果表 (backtest_results)
CREATE TABLE IF NOT EXISTS backtest_results (
    id INT AUTO_INCREMENT PRIMARY KEY,
    backtest_name VARCHAR(100) NOT NULL COMMENT '回测名称',
    start_date DATE NOT NULL COMMENT '回测开始日期',
    end_date DATE NOT NULL COMMENT '回测结束日期',
    trading_pairs TEXT NOT NULL COMMENT '回测交易对（JSON格式）',
    initial_capital DECIMAL(20, 8) NOT NULL COMMENT '初始资金',
    final_capital DECIMAL(20, 8) NOT NULL COMMENT '最终资金',
    total_return_percentage DECIMAL(10, 4) COMMENT '总回报率（%）',
    annualized_return DECIMAL(10, 4) COMMENT '年化回报率（%）',
    max_drawdown DECIMAL(10, 4) COMMENT '最大回撤（%）',
    sharpe_ratio DECIMAL(10, 4) COMMENT '夏普比率',
    win_rate DECIMAL(5, 2) COMMENT '胜率（%）',
    profit_factor DECIMAL(10, 4) COMMENT '盈亏比',
    total_trades INT COMMENT '总交易次数',
    strategy_parameters TEXT COMMENT '策略参数（JSON格式）',
    trade_history TEXT COMMENT '交易历史（JSON格式）',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '回测时间'
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='存储策略回测结果';

-- 9. 创建交易策略总结表 (trading_strategy_summaries)
CREATE TABLE IF NOT EXISTS `trading_strategy_summaries` (
  `id` INT NOT NULL AUTO_INCREMENT COMMENT '主键ID',
  `decision_timestamp` DATETIME NOT NULL COMMENT '策略决策时间',
  `daily_summary_id` INT NOT NULL COMMENT '关联的每日汇总ID',
  `summary_content` TEXT NOT NULL COMMENT '策略总结内容',
  `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '记录创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_daily_summary_id` (`daily_summary_id`),
  KEY `idx_decision_timestamp` (`decision_timestamp`),
  CONSTRAINT `fk_summary_daily_summary` FOREIGN KEY (`daily_summary_id`) REFERENCES `daily_summary` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='存储交易策略的总结信息';

-- 10. 当前持仓表 (positions)
CREATE TABLE IF NOT EXISTS positions (
    id INT AUTO_INCREMENT PRIMARY KEY,
    trading_pair VARCHAR(20) NOT NULL COMMENT '交易对，例如：BTCUSDT',
    position_type ENUM('LONG', 'SHORT') NOT NULL COMMENT '仓位类型：做多或做空',
    quantity DECIMAL(20, 8) NOT NULL COMMENT '持仓数量',
    entry_price DECIMAL(20, 8) NOT NULL COMMENT '平均入场价格',
    current_price DECIMAL(20, 8) COMMENT '当前价格',
    unrealized_pnl DECIMAL(30, 8) DEFAULT 0.00 COMMENT '未实现盈亏',
    stop_loss_price DECIMAL(20, 8) COMMENT '止损价格',
    take_profit_price DECIMAL(20, 8) COMMENT '止盈价格',
    leverage DECIMAL(5, 2) DEFAULT 1.00 COMMENT '杠杆倍数',
    margin_used DECIMAL(30, 8) DEFAULT 0.00 COMMENT '已用保证金',
    open_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '开仓时间',
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    status ENUM('OPEN', 'CLOSED', 'LIQUIDATED') DEFAULT 'OPEN' COMMENT '仓位状态',
    related_strategy_id INT COMMENT '关联的交易策略ID',
    FOREIGN KEY (related_strategy_id) REFERENCES trading_strategies(id) ON DELETE SET NULL,
    UNIQUE KEY unique_position (trading_pair, position_type, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='当前持仓信息';

-- 11. 账户余额表 (account_balance)
CREATE TABLE IF NOT EXISTS account_balance (
    id INT AUTO_INCREMENT PRIMARY KEY,
    asset VARCHAR(20) NOT NULL COMMENT '资产符号，例如：USDT、BTC',
    free_balance DECIMAL(30, 8) NOT NULL DEFAULT 0.00 COMMENT '可用余额',
    locked_balance DECIMAL(30, 8) NOT NULL DEFAULT 0.00 COMMENT '冻结余额',
    total_balance DECIMAL(30, 8) NOT NULL DEFAULT 0.00 COMMENT '总余额',
    last_updated DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '最后更新时间',
    UNIQUE KEY unique_asset (asset)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='账户余额信息';

-- 12. 订单表 (orders)
CREATE TABLE IF NOT EXISTS orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    binance_order_id BIGINT UNIQUE NOT NULL COMMENT 'Binance订单ID',
    trading_pair VARCHAR(20) NOT NULL COMMENT '交易对，例如：BTCUSDT',
    order_type ENUM('MARKET', 'LIMIT', 'STOP_LOSS', 'TAKE_PROFIT', 'STOP_LOSS_LIMIT', 'TAKE_PROFIT_LIMIT') NOT NULL COMMENT '订单类型',
    side ENUM('BUY', 'SELL') NOT NULL COMMENT '买卖方向',
    quantity DECIMAL(20, 8) NOT NULL COMMENT '订单数量',
    price DECIMAL(20, 8) COMMENT '订单价格（限价单）',
    stop_price DECIMAL(20, 8) COMMENT '触发价格（止损/止盈单）',
    executed_quantity DECIMAL(20, 8) DEFAULT 0.00 COMMENT '已成交数量',
    executed_price DECIMAL(20, 8) COMMENT '成交价格',
    status ENUM('NEW', 'PARTIALLY_FILLED', 'FILLED', 'CANCELED', 'REJECTED', 'EXPIRED') NOT NULL COMMENT '订单状态',
    time_in_force ENUM('GTC', 'IOC', 'FOK') DEFAULT 'GTC' COMMENT '订单有效期',
    commission_fee DECIMAL(20, 8) DEFAULT 0.00 COMMENT '手续费',
    commission_asset VARCHAR(20) COMMENT '手续费资产',
    order_time DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '下单时间',
    update_time DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    related_strategy_id INT COMMENT '关联的交易策略ID',
    related_position_id INT COMMENT '关联的仓位ID',
    FOREIGN KEY (related_strategy_id) REFERENCES trading_strategies(id) ON DELETE SET NULL,
    FOREIGN KEY (related_position_id) REFERENCES positions(id) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='订单信息';
