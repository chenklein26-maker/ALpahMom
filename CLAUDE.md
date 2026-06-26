# CLAUDE.md — AlphaMom 开发者指南

本文档为开发智能 Agent（如 Antigravity / Claude Code）在本项目中的开发与执行提供指令指南和规范约束。

---

## 🚀 常用指令

### 1. 运行数据流水线 (一键端到端)
您可以使用以下单条命令运行整个数据流，包括数据抓取、MCI指数计算以及大模型播报生成：
```bash
# 一键运行整条流水线 (默认生成今日复盘报告)
python run.py

# 一键运行并生成 HTML 海报
python run.py --html output/report.html

# 一键运行生成简短避险信号模式
python run.py --mode signal
```

> [!TIP]
> 如果您是首次克隆此项目，运行 `python run.py` 会自动为您在根目录生成默认的 `alpha_mom_config.json` 配置文件。您可以直接在其中配置您的 `DEEPSEEK_API_KEY` 以启用大模型动态播报。

### 2. 高级用法 (分步执行)
如果您需要调试特定模块，亦可依序执行以下子脚本：
```bash
# 1. 抓取加密货币情绪与市场数据
python scripts/fetch_crypto.py --config alpha_mom_config.json --output data/crypto_raw.json

# 2. 抓取 A 股情绪与市场数据
python scripts/fetch_astock.py --config alpha_mom_config.json --output data/astock_raw.json

# 3. 计算宝妈拥挤度指数 (MCI)
python scripts/compute_mci.py --crypto data/crypto_raw.json --astock data/astock_raw.json --output data/mci_result.json

# 4. 生成讽刺广播避险报告 (今日复盘模式)
python scripts/report.py --mci data/mci_result.json --config alpha_mom_config.json --mode review
```

### 3. 预览 Web 端 macOS 仪表盘
启动本地轻量级 HTTP 服务以托管 macOS 质感的双模仪表盘：
```bash
python -m http.server 8000
```
在浏览器中打开 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**，以测试滑块交互、Z-Score 离散气泡及海报下载功能。

---

## 🎙️ 广播电台人设与语气规范

本项目所有面向用户的输出（控制台打印、网页文本、海报生成）必须严格遵守 **Cyber Sentiment Radio (赛博情绪电台)** 语气人设：
1. **辛辣讽刺的电台播报腔**：使用快节奏、黑色幽默、冷嘲热讽的美式电台主持人口吻。
2. **戏谑的用户称呼**：针对散户使用特定的理财讽刺代称，必须根据市场冷热动态使用以下称呼：
   - `天台VIP们` (针对冰封/极冷恐慌区)
   - `接盘侠们` (针对极热/泡沫过热区)
   - `天才交易员们` (反讽加杠杆的散户)
   - `金融巨鳄们` (调侃跑步进场的业余投资者)
   - `韭菜们` (泛指)
3. **去游戏化规范 (关键)**：**严禁**提到任何《赛博朋克2077》相关的特定虚构名词（如：*夜之城/Night City*、*荒坂/Arasaka*、*NCPD*、*欧金/Eurodollars*、*黑墙/Blackwall*、*歌舞伎町*、*斯坦利*等）。一切内容必须聚焦于现实中的真实理财市场（A股、加密货币、黄金、白酒、茅台等）及现实中的散户行为。
4. **LLM 提示词参考**：开发 Agent 在为大模型编写提示词时，可直接参考 [assets/mama_quotes.json](file:///c:/Users/v_clulcchen/Desktop/RYu/Coding/宝妈反买/assets/mama_quotes.json) 以对齐本地静态兜底模板的讽刺深度与文本句式。

---

## 🛠️ 技术规范与执行机制

1. **大模型动态播报与降级逻辑**：
   - 默认接入 **DeepSeek API (`deepseek-chat` 模型)**。
   - 环境变量 Key 为 `DEEPSEEK_API_KEY`，配置文件字段为 `llm_config.deepseek_api_key`。
   - **自愈式降级**：若未配置 Key 或接口调用异常（如网络超时、配额耗尽等），程序必须通过 `try...except` **无感回退降级**为本地静态模板加载（即 `mama_quotes.json`），绝不能中断报错导致 Agent 挂机。
2. **双模 Web 看板交互**：
   - 双模切换（Lite 模式与 Pro 模式）通过 CSS 类名优雅隐显过渡。
   - **性能约束**：为保证极致交互手感，在网页 Pro 模式中用户拖动滑块权重时，MCI 与评语重算**必须在前端 JS 本地内存中在毫秒级内瞬间完成**，严禁向后端或 LLM 发送同步请求，确保零延迟响应。
