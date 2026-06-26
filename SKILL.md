---
name: alpha-mom
description: >-
  宝妈反买指数（AlphaMom）。基于多维市场数据合成 MCI 宝妈拥挤度指数（0-100%），
  以"宝妈狂热度"拟人化播报反向交易信号。当用户提到"宝妈反买"、"宝妈指数"、
  "AlphaMom"、"MCI"、"散户反向指标"、"市场情绪"、"拥挤度"、"该不该卖/买"、
  "现在能不能上车"、"今日复盘"、"每日复盘"、"今日行情"、"持仓复盘"、
  "宝妈脱口秀"、"财经脱口秀"等关键词时触发。支持加密货币与A股，
  输出含五维拆解的情报简报或每日复盘脱口秀。兼顾趣味性与量化严谨性。
cn_name: AlphaMom 宝妈反买指数
cn_description: >-
  用多维真实市场数据（恐惧贪婪指数、搜索热度、衍生品杠杆、价格偏离、社区情绪）
  合成"宝妈拥挤度指数"，以拟人化播报给出反向交易信号。
  外行看个乐，内行看门道。
compatibility:
  - python>=3.8
  - requests
  - akshare
  - praw
  - vaderSentiment
  - pytrends
---

# AlphaMom — 宝妈反买指数

## 核心理念

"宝妈进场 = 该跑了"——这个流传十年的民间段子，背后是金融学严肃的**逆向投资理论**。
AlphaMom 不直接监控真实宝妈，而是用 5 个可量化的市场维度合成 **MCI (Mommy Crowding Index)**
宝妈拥挤度指数（0-100%），分数越高代表散户越拥挤，反向卖出信号越强。

**对外**：宝妈狂热度、宝妈情报简报
**对内**：多维市场数据交叉验证的量化情绪模型

## 工作流

### 1. 初始化（首次使用）

读取 `assets/config_template.json`，引导用户配置：
- 关注/持有的标的（加密货币 coin id 或 A股代码）
- 毒舌等级（温柔提醒 / 阴阳怪气 / 财经脱口秀）
- 保存到用户工作目录的 `alpha_mom_config.json`

### 2. 数据采集

执行 `scripts/fetch_crypto.py` 和/或 `scripts/fetch_astock.py`，采集五大维度数据：

| 维度 | 加密数据源 | A股数据源 | 权重 |
|------|-----------|----------|------|
| 恐惧贪婪指数 | Alternative.me API | AKShare funddb (沪深300) | 20% |
| 搜索热度异动 | Google Trends (PyTrends) | 换手率百分位 + 涨停板数量 (AKShare) | 20% |
| 杠杆拥挤度 | CoinGlass API (OI+费率+多空比) | 融资融券余额 + 北向资金 (AKShare) | 25% |
| 价格-趋势偏离 | CoinGecko API | AKShare stock_zh_a_hist | 20% |
| 社区情绪语义 | Reddit (PRAW+VADER) | 东财新闻情绪指数 (AKShare) | 15% |

### 3. MCI 计算

执行 `scripts/compute_mci.py`，对每个标的：
- 各维度独立归一化到 [0, 100]
- 自适应权重归一化（某维度不可用时权重按比例重分配）
- 加权求和得到 MCI

### 4. 信号分级与播报

执行 `scripts/report.py`，生成情报简报：

| MCI | 等级 | 宝妈状态 | 反向建议 |
|-----|------|---------|---------|
| 0-20 | 🧊 冰封区 | 宝妈早已割肉离场 | 🟢 买入信号 |
| 21-40 | ❄️ 寒冷区 | 宝妈观望中 | 🔵 建仓信号 |
| 41-60 | 😐 温和区 | 正常状态 | ⚪ 持有 |
| 61-80 | 🔥 升温区 | 宝妈开始打听 | 🟡 止盈信号 |
| 81-100 | 🌋 熔岩区 | 宝妈跑步进场 | 🔴 卖出信号 |

### 5. 输出格式

```
📋 AlphaMom 宝妈情报简报 · {date}

{标的名称}  MCI={分数}% {等级图标}
├─ 恐惧贪婪: {score}  {解读}
├─ 搜索热度: {score}  {解读}
├─ 杠杆拥挤: {score}  {解读}
├─ 趋势偏离: {score}  {解读}
└─ 社区情绪: {score}  {解读}

📢 宝妈播报: {拟人化文案}
🔔 反向信号: {操作建议}

⚠️ 免责声明: 本工具仅供娱乐与辅助参考，不构成任何投资建议。
```

## 执行方式

本技能有三种工作模式，根据用户触发词自动判断：

### 模式 A：信号快报（默认）

触发词："宝妈反买"、"MCI"、"该不该卖"、"能不能上车"、"市场情绪"等

1. 检查用户工作目录下是否有 `alpha_mom_config.json`
   - 没有 → 先走初始化流程
   - 有 → 读取配置
2. 根据配置中的标的类型，执行对应采集脚本
3. 执行 MCI 计算脚本
4. 执行播报脚本（默认文本模式），输出情报简报
5. 用户可要求输出 HTML 海报版（可选）

### 模式 B：今日复盘（每日收盘后使用）

触发词："今日复盘"、"每日复盘"、"今日行情"、"持仓复盘"、"宝妈脱口秀"、"财经脱口秀"等

这是为股民设计的每日情绪价值+决策辅助场景。与信号快报的区别：
- 信号快报 = 快速看一眼 MCI，给个买/卖信号
- 今日复盘 = 把今天持仓的每个标的全过一遍，讲今天发生了什么、为什么涨/跌、宝妈群什么反应、明天该不该动

**工作流**：

1. 读取配置，执行数据采集（同模式 A）
2. 执行 MCI 计算（同模式 A）
3. 执行播报脚本时传入 `--mode review` 参数：
   ```bash
   python scripts/report.py --mci data/mci_result.json --config alpha_mom_config.json --mode review
   ```
4. 复盘模式输出内容（比信号快报多出以下部分）：
   - **今日行情摘要**：每个标的今日涨跌幅、关键数据变化
   - **宝妈群生态**：用脱口秀口吻描述今天"宝妈群"的反应
   - **板块联动**：持仓标的中如果有联动关系的（如 BTC 和 ETH 同涨同跌），点出关联
   - **操作建议**：明天该不该动、关注什么信号
   - **宝妈金句**：每天一句点睛之笔的脱口秀台词
5. 可选输出 HTML 版复盘日报

### 模式 C：初始化配置

触发词："配置宝妈"、"AlphaMom 设置"、"改持仓"等

引导用户设置/修改持仓清单和毒舌等级。

### 脚本执行

```bash
# 加密标的
python scripts/fetch_crypto.py --config alpha_mom_config.json --output data/crypto_raw.json
# A股标的
python scripts/fetch_astock.py --config alpha_mom_config.json --output data/astock_raw.json
# MCI 计算
python scripts/compute_mci.py --crypto data/crypto_raw.json --astock data/astock_raw.json --output data/mci_result.json
# 生成播报
python scripts/report.py --mci data/mci_result.json --config alpha_mom_config.json
```

## 文件结构

```
alpha-mom/
├── SKILL.md
├── scripts/
│   ├── fetch_crypto.py    # 加密数据采集（Alternative.me + CoinGecko + CoinGlass + Reddit）
│   ├── fetch_astock.py    # A股数据采集（AKShare 恐惧贪婪 + 行情 + 融资融券 + 换手率）
│   ├── compute_mci.py     # MCI 计算引擎（五维归一化 + 自适应权重）
│   └── report.py          # 播报生成（拟人化文案 + HTML海报可选）
├── assets/
│   ├── config_template.json  # 配置模板
│   └── mama_quotes.json      # 宝妈语录库
└── data/                    # 运行时数据缓存（自动创建）
```

## 关键设计

- **自适应降级**：任一数据源失败，自动剔除该维度、重分配权重，MCI 始终能输出
- **历史缓存**：每次运行结果存入 `data/history.csv`，用于趋势对比
- **宝妈包装**：底层是硬数据，表浅是梗——语录库随机抽取，按毒舌等级切换语气
- **合规**：始终附带免责声明
