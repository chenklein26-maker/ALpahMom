# AlphaMom - 宝妈反买指数

> 外行看个乐, 内行看门道.

AlphaMom 是一个基于多维市场数据的**散户拥挤度反向指标工具**. 它将"宝妈进场 = 该跑了"这个流传十年的民间段子, 用真实可获取的市场数据量化为 **MCI (Mommy Crowding Index) 宝妈拥挤度指数** (0-100%), 以拟人化播报给出反向交易信号.

## 核心理念

- **对外**: 宝妈狂热度, 宝妈情报简报, 财经脱口秀
- **对内**: 多维市场数据交叉验证的量化情绪模型

当 MCI 越高, 说明散户越拥挤, 反向卖出信号越强; MCI 越低, 说明市场冷清, 可能是底部区域.

## MCI 五维模型

| 维度 | 加密数据源 | A股数据源 | 权重 |
|------|-----------|----------|------|
| 恐惧贪婪指数 | Alternative.me API | AKShare funddb (沪深300) | 20% |
| 搜索热度异动 | Google Trends (PyTrends) | 换手率百分位 + 涨停板数量 | 20% |
| 杠杆拥挤度 | CoinGlass API | 融资融券余额 + 北向资金 | 25% |
| 价格-趋势偏离 | CoinGecko API | AKShare stock_zh_a_hist | 20% |
| 社区情绪语义 | Reddit (PRAW+VADER) | 东财新闻情绪指数 | 15% |

**自适应降级**: 任一数据源失败时, 自动剔除该维度并重新分配权重, MCI 始终能输出结果.

## 信号分级

| MCI | 等级 | 宝妈状态 | 反向建议 |
|-----|------|---------|---------|
| 0-20 | Ice Zone | 宝妈早已割肉离场 | Buy Signal |
| 21-40 | Cold Zone | 宝妈观望中 | Accumulate |
| 41-60 | Neutral | 正常状态 | Hold |
| 61-80 | Hot Zone | 宝妈开始打听 | Take Profit |
| 81-100 | Lava Zone | 宝妈跑步进场 | Sell Signal |

## 快速开始

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置

编辑 `assets/config_template.json`, 添加你关注的标的:

```json
{
  "crypto_assets": [
    {"coin_id": "bitcoin", "symbol": "BTC", "name": "Bitcoin", "weight": 1.0}
  ],
  "astock_assets": [
    {"symbol": "600519", "name": "贵州茅台", "weight": 1.0}
  ]
}
```

### 运行

```bash
# 1. 采集数据
python scripts/fetch_crypto.py --config assets/config_template.json --output data/crypto_raw.json
python scripts/fetch_astock.py --config assets/config_template.json --output data/astock_raw.json

# 2. 计算 MCI
python scripts/compute_mci.py --crypto data/crypto_raw.json --astock data/astock_raw.json --output data/mci_result.json

# 3a. 信号快报
python scripts/report.py --mci data/mci_result.json --config assets/config_template.json

# 3b. 今日复盘 (脱口秀模式)
python scripts/report.py --mci data/mci_result.json --config assets/config_template.json --mode review

# 3c. HTML 海报
python scripts/report.py --mci data/mci_result.json --config assets/config_template.json --html data/report.html
```

## 数据源可用性

| 维度 | 开箱即用 | 需额外配置 | 降级行为 |
|------|---------|-----------|---------|
| 恐惧贪婪 | Yes | - | - |
| 价格偏离 | Yes | - | - |
| 搜索热度 (A股) | Yes (AKShare) | - | - |
| 杠杆拥挤 (A股) | Yes (AKShare) | - | - |
| 社区情绪 (A股) | Yes (AKShare) | - | - |
| 搜索热度 (加密) | No | `pip install pytrends` | 降级为中性 |
| 杠杆拥挤 (加密) | No | CoinGlass API Key | 降级为中性 |
| 社区情绪 (加密) | No | Reddit API credentials | 降级为中性 |

## 文件结构

```
alpha-mom/
├── SKILL.md                  # Skill 触发词与工作流定义
├── README.md
├── LICENSE
├── requirements.txt
├── .gitignore
├── scripts/
│   ├── fetch_crypto.py       # 加密数据采集
│   ├── fetch_astock.py       # A股数据采集 (国内数据源)
│   ├── compute_mci.py        # MCI 计算引擎
│   └── report.py             # 播报生成 (信号快报 + 复盘 + HTML)
├── assets/
│   ├── config_template.json  # 配置模板
│   └── mama_quotes.json      # 宝妈语录库
└── data/                     # 运行时缓存 (gitignored)
```

## 免责声明

本工具仅供娱乐与辅助参考, 不构成任何投资建议. 市场有风险, 投资需谨慎. 宝妈反买, 盈亏自负.

## License

MIT
