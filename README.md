# 🚀 加密货币智能交易系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Status](https://img.shields.io/badge/Status-Active-brightgreen.svg)

## 📋 项目概述

一个功能完整的加密货币自动交易系统，集成了数据收集、AI策略生成、自动交易执行、风险管理和实时监控等功能。

### ✨ 核心特性

- 🔄 **自动化交易**: 完整的交易执行、价格监控和仓位管理
- 🤖 **AI策略生成**: 基于市场数据和新闻情感的智能策略
- 📊 **实时监控**: WebSocket价格监控和自动止盈止损
- ⚡ **高性能**: 支持多交易对并发处理
- 🛡️ **风险管理**: 完善的仓位控制和风险管理机制
- 📈 **数据分析**: 市场数据收集和技术指标分析

## 🏗️ 系统架构

```text
crypto_trading/
├── 📁 app/                     # 核心应用模块
│   ├── 📊 data_collectors/     # 数据收集
│   │   ├── binance_data_collector.py
│   │   └── crypto_news_collector.py
│   ├── 🔄 data_processors/     # 数据处理
│   │   └── daily_summary_processor.py
│   ├── 🤖 decision_makers/     # AI决策
│   │   └── trading_strategy_ai.py
│   ├── 💾 database/            # 数据库管理
│   │   └── db_manager.py
│   ├── 🔄 trading/             # 交易模块
│   │   ├── trading_executor.py     # 交易执行
│   │   ├── price_monitor.py        # 价格监控
│   │   ├── position_manager.py     # 仓位管理
│   │   └── trading_manager.py      # 交易管理器
│   ├── ⏰ scheduler/           # 定时任务
│   │   ├── scheduler.py
│   │   ├── tasks.py
│   │   └── trading_tasks.py
│   └── 📈 reporting/           # 报告生成
│       └── profit_loss_calculator.py
├── ⚙️ config/                  # 配置文件
├── 📊 models/                  # 数据库模型
├── 🔧 scripts/                 # 工具脚本
├── 🧪 test/                    # 测试文件
└── 📖 examples/                # 使用示例
```

### 🔧 核心模块

| 模块 | 功能 | 主要特性 |
|------|------|----------|
| 🔄 **交易执行** | 自动化交易操作 | 市价单、限价单、止损止盈 |
| 📊 **价格监控** | 实时价格跟踪 | WebSocket监控、自动触发 |
| 💼 **仓位管理** | 投资组合管理 | 风险控制、盈亏计算 |
| 🤖 **AI策略** | 智能决策生成 | 基于数据的策略建议 |
| 📈 **数据收集** | 市场数据获取 | 实时价格、新闻、K线数据 |

## 🚀 快速开始

### 📋 系统要求

- **Python**: 3.11+
- **数据库**: MySQL 8.0+
- **操作系统**: Windows/Linux/macOS
- **内存**: 建议4GB+
- **网络**: 稳定的互联网连接

### ⚡ 一键安装

```bash
# 1. 克隆项目
git clone <repository-url>
cd crypto_trading

# 2. 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 3. 安装依赖
pip install -r requirements.txt

# 4. 配置数据库
mysql -u root -p -e "CREATE DATABASE crypto_trading;"
mysql -u root -p crypto_trading < models/database_schema.sql

# 5. 配置系统
cp config/config.py.template config/config.py
# 编辑 config/config.py 填入API密钥
```

### ⚙️ 配置说明

编辑 `config/config.py` 文件，配置以下关键参数：

```python
# API配置
BINANCE_API_KEY = "your_binance_api_key"
BINANCE_API_SECRET = "your_binance_secret"
BINANCE_TESTNET = True  # 建议先使用测试网

# 交易对配置
TRADING_PAIRS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT"  # 自定义交易币种
]

# 风险管理
ENABLE_AUTO_TRADING = False  # 自动交易开关
DEFAULT_RISK_PERCENTAGE = 2.0  # 风险百分比
```

### ✅ 配置验证

```bash
# 验证配置是否正确
python scripts/validate_config.py

# 清理重复配置（如果需要）
python scripts/cleanup_config.py
```

## 🎮 使用方式

### 🔄 自动化运行（推荐）

```bash
# 启动完整的自动化交易系统
python crypto_run.py --run scheduler
```

系统将自动执行：
- 📊 每小时收集市场数据和新闻
- 🤖 每日生成AI交易策略
- 💰 自动执行交易（如果启用）
- 📈 实时监控价格和仓位

### 🎯 手动执行任务

```bash
# 运行单个任务
python crypto_run.py --run task --task <task_name>

# 示例：收集今日数据
python crypto_run.py --run task --task collect_hourly_data

# 示例：生成交易策略
python crypto_run.py --run task --task generate_crypto_trading_strategy
```

**可用任务列表：**

| 任务 | 功能 | 频率建议 |
|------|------|----------|
| `collect_crypto_news` | 收集加密货币新闻 | 每小时 |
| `collect_crypto_market_data` | 收集市场数据 | 每小时 |
| `generate_crypto_trading_strategy` | 生成交易策略 | 每日 |
| `full_workflow` | 完整工作流程 | 按需 |

### 🧪 测试和示例

```bash
# 运行交易模块测试
python test/trading/test_trading_modules.py

# 运行完整示例
python examples/trading_example.py

# 验证配置
python scripts/validate_config.py
```

### 🖥️ 系统服务（可选）

```bash
# Windows服务安装
python scripts/install_service.py --install

# 启动/停止服务
net start CryptoTradingService
net stop CryptoTradingService
```

## 🌟 核心功能

### 📊 数据收集与分析
- **实时市场数据**: Binance API集成，获取价格、K线、资金费率
- **新闻情感分析**: CryptoPanic/CoinMarketCal新闻收集和NLP分析
- **多时间框架**: 支持1分钟到1天的多种K线周期
- **市场情绪**: 自动计算市场情绪指标和热度

### 🤖 AI智能决策
- **策略生成**: 基于Sealos AI Proxy的智能交易策略
- **风险评估**: 自动计算入场价格、止损止盈位置
- **多币种支持**: 同时处理多个交易对的策略分析
- **参数优化**: 动态调整仓位大小和风险参数

### 💰 自动化交易
- **交易执行**: 支持市价单、限价单、止损止盈单
- **实时监控**: WebSocket价格监控和自动触发
- **仓位管理**: 完整的投资组合管理和风险控制
- **盈亏跟踪**: 实时计算未实现和已实现盈亏

### ⚡ 系统特性
- **24/7运行**: 适应加密货币市场的全天候特性
- **高可用性**: 自动重连和异常恢复机制
- **模块化设计**: 易于扩展和维护
- **配置灵活**: 支持自定义交易对和参数

## ⚠️ 重要提醒

### 🔐 安全配置
- **API密钥**: 确保Binance API密钥权限最小化，建议只开启现货交易权限
- **测试优先**: 强烈建议先在测试网络上验证所有功能
- **密钥安全**: 不要将API密钥提交到版本控制系统

### 🛡️ 风险管理
- **资金控制**: 建议单笔交易风险不超过总资金的2-5%
- **止损设置**: 务必为每个仓位设置合理的止损价格
- **分散投资**: 避免将所有资金投入单一币种

### 📋 使用须知
- **策略参考**: 生成的交易策略仅供参考，不构成投资建议
- **自动交易**: 默认禁用自动交易，启用前请充分测试
- **数据依赖**: 系统依赖外部API，可能受网络和服务商影响

## 📞 技术支持

### 🔧 故障排除
```bash
# 检查系统状态
python scripts/validate_config.py

# 查看日志
tail -f logs/crypto_trading.log

# 测试连接
python test/trading/test_trading_modules.py
```

### 📚 文档和示例
- 配置验证工具: `scripts/validate_config.py`
- 使用示例: `examples/trading_example.py`
- 测试脚本: `test/trading/`

## ⚖️ 免责声明

**本软件仅用于教育和研究目的，不构成任何形式的投资建议。**

- 🚨 加密货币交易具有极高风险，可能导致全部资金损失
- 📈 过往表现不代表未来收益，市场波动不可预测
- 🤖 AI生成的策略可能存在错误，用户需自行判断
- 💼 用户对所有交易决策和结果承担全部责任
- 🔒 开发者不对任何直接或间接损失承担责任

**请在充分了解风险的前提下谨慎使用本系统。**
