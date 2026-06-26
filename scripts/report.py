#!/usr/bin/env python3
"""
AlphaMom — 播报生成器
将 MCI 结果转化为拟人化"宝妈情报简报"
支持终端文本输出 + HTML 海报输出
"""

import argparse
import json
import os
import sys
import random
from datetime import datetime

# ─── 宝妈语录库 ───────────────────────────────────────────────
MAMA_QUOTES = {
    "freeze": [
        "群里鸦雀无声,上次提到这个标的的人已经被踢了.",
        "宝妈们纷纷表示'再也不碰了',连讨论的力气都没了.",
        "小区群里在聊明天的菜价,没人在聊行情.",
    ],
    "cold": [
        "偶尔有人在群里问一句'还能买吗',然后被已读不回.",
        "宝妈们的注意力在别的地方,这个标的已经不在她们的视野里了.",
        "提起来最多换来一句'哦,那个啊'.",
    ],
    "neutral": [
        "宝妈们正常生活,没人特别关注这个标的.",
        "群里偶尔有人提起,但没什么水花.",
        "不温不火,宝妈们还在观望.",
    ],
    "hot": [
        "你王阿姨今早在小区群问'这个是不是还能上车'.",
        "群里开始有人晒收益截图了,附带'姐妹们冲'.",
        "宝妈们开始打听怎么开户了,朋友圈出现了相关转发.",
    ],
    "lava": [
        "连你三姑都在群里推荐这个标的了,还说'稳赚不赔'.",
        "宝妈群已经刷屏,每个人都在问'现在买还来得及吗'.",
        "小区保安都在讨论这个标的,你妈打电话问你要不要买.",
        "朋友圈十条有八条在晒收益,剩两条在问怎么开户.",
    ]
}

# ─── 维度解读 ─────────────────────────────────────────────────
DIM_INTERPRETATIONS = {
    "fear_greed": {
        "name": "恐惧贪婪",
        "high": "市场情绪极度贪婪,散户亢奋",
        "mid": "市场情绪中性",
        "low": "市场情绪极度恐惧,散户恐慌"
    },
    "search_interest": {
        "name": "搜索热度",
        "high": "圈外人搜索量飙升,新资金蠢蠢欲动",
        "mid": "搜索热度正常",
        "low": "搜索冷淡,无人问津"
    },
    "derivatives": {
        "name": "杠杆拥挤",
        "high": "杠杆多头拥挤,资金费率偏高",
        "mid": "杠杆水平正常",
        "low": "杠杆偏低,市场去杠杆中"
    },
    "price_trend": {
        "name": "趋势偏离",
        "high": "价格严重偏离均线,泡沫风险高",
        "mid": "价格在均线附近,趋势正常",
        "low": "价格大幅低于均线,超卖"
    },
    "social_sentiment": {
        "name": "社区情绪",
        "high": "社区讨论火爆,情绪极度乐观",
        "mid": "社区讨论热度一般",
        "low": "社区冷清,情绪偏悲观"
    }
}

LEVEL_KEYS = ["freeze", "cold", "neutral", "hot", "lava"]

def get_level_key(mci):
    if mci <= 20: return "freeze"
    elif mci <= 40: return "cold"
    elif mci <= 60: return "neutral"
    elif mci <= 80: return "hot"
    else: return "lava"

def interpret_dim(dim_name, score):
    """维度分数解读"""
    info = DIM_INTERPRETATIONS.get(dim_name, {"name": dim_name, "high": "", "mid": "", "low": ""})
    if score is None:
        return f"{info['name']}: 数据不可用"
    if score >= 70:
        return f"{info['name']}: {score} — {info['high']}"
    elif score >= 40:
        return f"{info['name']}: {score} — {info['mid']}"
    else:
        return f"{info['name']}: {score} — {info['low']}"

def get_mama_quote(mci, sass_level="medium"):
    """根据 MCI 和毒舌等级获取宝妈语录"""
    key = get_level_key(mci)
    quotes = MAMA_QUOTES.get(key, MAMA_QUOTES["neutral"])
    quote = random.choice(quotes)
    return quote

def generate_text_report(mci_data, config):
    """生成终端文本情报简报"""
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    sass = config.get("sass_level", "medium")
    sass_prefix = {"gentle": "", "medium": "", "comedy": ""}.get(sass, "")

    lines = []
    lines.append(f"\n{'='*55}")
    lines.append(f"  📋 AlphaMom 宝妈情报简报 · {date_str}")
    lines.append(f"{'='*55}")

    # 组合 MCI
    portfolio = mci_data.get("portfolio")
    if portfolio:
        p_mci = portfolio["mci"]
        p_level = portfolio["level"]
        lines.append(f"\n  📊 组合宝妈狂热度: {p_mci}% {p_level['icon']} {p_level['level']}")
        lines.append(f"  📢 宝妈播报: {get_mama_quote(p_mci, sass)}")
        lines.append(f"  🔔 反向信号: {p_level['signal_icon']} {p_level['signal']}")
        lines.append(f"  👩 宝妈状态: {p_level['mama_status']}")

    # 各标的明细
    lines.append(f"\n  {'─'*50}")
    lines.append(f"  📌 各标的明细:")
    for asset in mci_data.get("assets", []):
        mci = asset["mci"]
        level = asset["level"]
        market_tag = "🔐" if asset.get("market") == "crypto" else "📈"
        lines.append(f"\n  {market_tag} {asset['name']} ({asset['symbol']})")
        lines.append(f"     MCI = {mci}% {level['icon']} {level['level']}")
        lines.append(f"     反向信号: {level['signal_icon']} {level['signal']}")

        # 维度拆解
        lines.append(f"     ┌─ 维度拆解:")
        for dim_name in ["fear_greed", "search_interest", "derivatives", "price_trend", "social_sentiment"]:
            dim = asset["dimensions"].get(dim_name, {})
            score = dim.get("score")
            avail = dim.get("available", False)
            interp = interpret_dim(dim_name, score) if avail else f"{DIM_INTERPRETATIONS.get(dim_name, {}).get('name', dim_name)}: 数据不可用"
            lines.append(f"     │  {interp}")

        # 不可用维度
        unavailable = asset.get("unavailable_dimensions", [])
        if unavailable:
            names = [DIM_INTERPRETATIONS.get(d, {}).get("name", d) for d in unavailable]
            lines.append(f"     └─ ⚠️ 降级维度: {', '.join(names)} (权重已重分配)")
        else:
            lines.append(f"     └─ 五维数据完整")

    # 免责声明
    lines.append(f"\n  {'─'*50}")
    lines.append(f"  ⚠️ 免责声明: 本工具仅供娱乐与辅助参考,不构成任何投资建议.")
    lines.append(f"  市场有风险,投资需谨慎.宝妈反买,盈亏自负.")
    lines.append(f"{'='*55}\n")

    return "\n".join(lines)


REVIEW_GOLDEN_QUOTES = [
    "Be greedy when others are fearful, run when others are greedy - but mamas never check charts, they only check the group chat.",
    "The market is like square dance: when the music stops at peak excitement, you are still standing in the middle.",
    "The hardest part of investing is not buying low and selling high - it is resisting the urge to say RUN when a mama asks should I buy.",
    "History does not repeat, but mamas do - at the end of every bull market stands a freshly-registered mama.",
    "True contrarian investing: on the day everyone is posting profits, quietly open the trading app and hit sell.",
]

def get_asset_daily_summary(asset):
    dims = asset.get("dimensions", {})
    price_dim = dims.get("price_trend", {})
    fg_dim = dims.get("fear_greed", {})
    # Data is nested under "details" in MCI result
    price_info = price_dim.get("details", price_dim)
    fg_info = fg_dim.get("details", fg_dim)
    return {
        "name": asset.get("name", ""),
        "symbol": asset.get("symbol", ""),
        "market": asset.get("market", ""),
        "mci": asset.get("mci", 0),
        "level": asset.get("level", {}),
        "price_today": price_info.get("price_today") if price_dim.get("available") else None,
        "ret_14d": price_info.get("ret_14d") if price_dim.get("available") else None,
        "deviation": price_info.get("deviation") if price_dim.get("available") else None,
        "fear_greed": fg_info.get("score") if fg_dim.get("available") else None,
        "fg_classification": fg_info.get("classification", "") if fg_dim.get("available") else None,
    }

def describe_price_action(summary):
    ret = summary.get("ret_14d")
    dev = summary.get("deviation")
    price = summary.get("price_today")
    parts = []
    if price is not None:
        if summary["market"] == "crypto":
            parts.append("Current price $" + format(price, ",.0f"))
        else:
            parts.append("Current price " + format(price, ",.2f"))
    if ret is not None:
        if ret > 10:
            parts.append("14d surge +" + str(ret) + "%")
        elif ret > 0:
            parts.append("14d up +" + str(ret) + "%")
        elif ret > -10:
            parts.append("14d down " + str(ret) + "%")
        else:
            parts.append("14d plunge " + str(ret) + "%")
    if dev is not None:
        if dev > 20:
            parts.append("deviation +" + str(dev) + "% above MA, high bubble risk")
        elif dev > 0:
            parts.append("above MA by " + str(dev) + "%")
        elif dev > -20:
            parts.append("below MA by " + str(dev) + "%")
        else:
            parts.append("far below MA by " + str(dev) + "%, oversold zone")
    return ", ".join(parts) + "." if parts else "Price data incomplete."

def describe_mama_reaction(mci, quotes_json=None):
    key = get_level_key(mci)
    if quotes_json and key in quotes_json:
        return random.choice(quotes_json[key])
    reactions = {
        "freeze": [
            "Today the mama group is as quiet as a library. Nobody mentions any asset.",
            "Today the mamas are mainly discussing what to wear for the school sports day.",
            "A newcomer asked can I buy the dip - three minutes of silence, then she deleted it.",
        ],
        "cold": [
            "Someone forwarded a market news link today, replies were all just oh.",
            "Someone posted a portfolio screenshot - all red. The only reply: a hug emoji.",
            "The mamas attention today is on bargain hunting. The market is not on their radar.",
        ],
        "neutral": [
            "The mama group is chatting normally today. Someone mentions the market occasionally.",
            "A mama asked how is it looking - another replied not bad - end of conversation.",
            "An uneventful day. The mamas are picking up kids and cooking dinner as usual.",
        ],
        "hot": [
            "The mama group suddenly lit up! Someone posted a profit screenshot and 20 messages asked how to buy.",
            "Your cousin asked is it too late to get on board and your mom messaged you asking is this reliable.",
            "Someone in the mama group posted an account-opening tutorial, marked beginner friendly.",
        ],
        "lava": [
            "The mama group EXPLODED. Everyone is posting profit screenshots.",
            "Your mom called you TWICE today. First: how to buy. Second: when does it double.",
            "The neighborhood group is now organizing group account openings. Leader: supermarket cashier.",
        ]
    }
    pool = reactions.get(key, reactions["neutral"])
    return random.choice(pool)

def detect_correlation(assets):
    if len(assets) < 2:
        return None
    crypto_assets = [a for a in assets if a.get("market") == "crypto"]
    correlations = []
    if len(crypto_assets) >= 2:
        names = [a["name"] for a in crypto_assets]
        mcis = [a["mci"] for a in crypto_assets]
        mci_range = max(mcis) - min(mcis)
        if mci_range < 10:
            joined = " and ".join(names)
            correlations.append(joined + " are highly correlated, MCI spread only " + str(round(mci_range, 1)) + " - they move in lockstep.")
    has_crypto = any(a.get("market") == "crypto" for a in assets)
    has_astock = any(a.get("market") == "astock" for a in assets)
    if has_crypto and has_astock:
        correlations.append("Your portfolio spans both crypto and A-stocks. Watch for capital flow between markets - a seesaw effect.")
    return " ".join(correlations) if correlations else None

def generate_review_report(mci_data, config, quotes_json=None):
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("  AlphaMom Daily Review - " + date_str)
    lines.append("=" * 60)
    portfolio = mci_data.get("portfolio", {})
    p_mci = portfolio.get("mci", 0)
    p_level = portfolio.get("level", {})
    lines.append("")
    lines.append("  Today mama market in one sentence:")
    lines.append("  Portfolio Mama Frenzy: " + str(p_mci) + "% " + str(p_level.get("icon", "")) + " " + str(p_level.get("level", "")))
    lines.append("  " + str(p_level.get("mama_status", "")))
    mama_quote = get_mama_quote(p_mci)
    if quotes_json:
        key = get_level_key(p_mci)
        if key in quotes_json:
            mama_quote = random.choice(quotes_json[key])
    lines.append("  " + mama_quote)
    lines.append("")
    lines.append("=" * 56)
    lines.append("  Portfolio breakdown:")
    for asset in mci_data.get("assets", []):
        summary = get_asset_daily_summary(asset)
        mci = summary["mci"]
        level = summary["level"]
        market_tag = "[C]" if summary["market"] == "crypto" else "[A]"
        lines.append("")
        lines.append("  " + market_tag + " " + summary["name"] + " (" + summary["symbol"] + ")")
        lines.append("     MCI: " + str(mci) + "% " + str(level.get("icon", "")) + " " + str(level.get("level", "")))
        lines.append("     Signal: " + str(level.get("signal_icon", "")) + " " + str(level.get("signal", "")))
        lines.append("     Price action: " + describe_price_action(summary))
        if summary["fear_greed"] is not None:
            fg = summary["fear_greed"]
            fg_cls = summary["fg_classification"] or ""
            lines.append("     Fear/Greed: " + str(fg) + " (" + fg_cls + ")")
        lines.append("     Mama group: " + describe_mama_reaction(mci, quotes_json))
        if mci >= 81:
            lines.append("     Advice: Mamas rushing in - consider scaling out. Do not wait for Third Aunt to call.")
        elif mci >= 61:
            lines.append("     Advice: Mamas getting interested - raise alert. Consider trimming position.")
        elif mci >= 41:
            lines.append("     Advice: Calm waters. Hold and enjoy the quiet.")
        elif mci >= 21:
            lines.append("     Advice: Mamas do not care - might be a good time to slowly accumulate.")
        else:
            lines.append("     Advice: Mamas dead silent, extreme fear - Buffett said: be greedy when others are fearful.")
    correlation = detect_correlation(mci_data.get("assets", []))
    if correlation:
        lines.append("")
        lines.append("=" * 56)
        lines.append("  Correlation watch:")
        lines.append("  " + correlation)
    lines.append("")
    lines.append("=" * 56)
    lines.append("  Tomorrow watch:")
    if p_mci >= 61:
        lines.append("  - Mama frenzy elevated, watch for more new account signals tomorrow")
        lines.append("  - If MCI breaks above 80%, execute take-profit plan decisively")
    elif p_mci <= 40:
        lines.append("  - Mamas quiet, market in fear zone, watch for stabilization signals")
        lines.append("  - If MCI drops below 20%, could be the final golden pit")
    else:
        lines.append("  - Market sentiment neutral, maintain status quo, no chasing or panic selling")
        lines.append("  - Watch for unexpected events that could break the balance")
    lines.append("")
    lines.append("=" * 56)
    lines.append("  Today golden quote:")
    lines.append('  "' + random.choice(REVIEW_GOLDEN_QUOTES) + '"')
    lines.append("")
    lines.append("-" * 56)
    lines.append("  Disclaimer: For entertainment and reference only, not investment advice.")
    lines.append("  Markets carry risk, invest with caution.")
    lines.append("=" * 60)
    lines.append("")
    return "\n".join(lines)

def generate_html_report(mci_data, config):
    """生成 HTML 海报版情报简报"""
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    portfolio = mci_data.get("portfolio", {})
    p_mci = portfolio.get("mci", 0)
    p_level = portfolio.get("level", {})
    
    # 颜色映射
    color_map = {"🧊": "#3b82f6", "❄️": "#06b6d4", "😐": "#10b981", "🔥": "#f59e0b", "🌋": "#ef4444"}
    level_icon = p_level.get("icon", "😐")
    bg_color = color_map.get(level_icon, "#10b981")
    
    # 各标的卡片
    asset_cards = ""
    for asset in mci_data.get("assets", []):
        mci = asset["mci"]
        level = asset["level"]
        market_tag = "🔐" if asset.get("market") == "crypto" else "📈"
        
        dims_html = ""
        for dim_name in ["fear_greed", "search_interest", "derivatives", "price_trend", "social_sentiment"]:
            dim = asset["dimensions"].get(dim_name, {})
            score = dim.get("score")
            avail = dim.get("available", False)
            name = DIM_INTERPRETATIONS.get(dim_name, {}).get("name", dim_name)
            if avail and score is not None:
                bar_width = score
                bar_color = "#ef4444" if score >= 70 else ("#f59e0b" if score >= 40 else "#3b82f6")
                dims_html += f'<div class="dim-row"><span class="dim-name">{name}</span><div class="dim-bar"><div class="dim-fill" style="width:{bar_width}%;background:{bar_color}"></div></div><span class="dim-score">{score}</span></div>'
            else:
                dims_html += f'<div class="dim-row"><span class="dim-name">{name}</span><div class="dim-bar"><div class="dim-fill" style="width:0%"></div></div><span class="dim-score dim-na">N/A</span></div>'

        asset_color = color_map.get(level.get("icon", ""), "#10b981")
        asset_cards += f'''
        <div class="asset-card" style="border-left-color:{asset_color}">
            <div class="asset-header">
                <span class="asset-icon">{market_tag}</span>
                <span class="asset-name">{asset['name']}</span>
                <span class="asset-symbol">{asset['symbol']}</span>
                <span class="asset-mci" style="color:{asset_color}">{mci}%</span>
                <span class="asset-level">{level.get('icon','')} {level.get('level','')}</span>
            </div>
            <div class="asset-signal">{level.get('signal_icon','')} {level.get('signal','')}</div>
            <div class="dims">{dims_html}</div>
        </div>'''

    quote = get_mama_quote(p_mci)

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AlphaMom 宝妈情报简报 · {date_str}</title>
<style>
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{ font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif; background:#0f172a; color:#e2e8f0; padding:20px; max-width:680px; margin:0 auto; }}
.header {{ text-align:center; padding:30px 20px; background:linear-gradient(135deg,#1e293b,#334155); border-radius:16px; margin-bottom:20px; }}
.header h1 {{ font-size:28px; margin-bottom:8px; }}
.header .date {{ color:#94a3b8; font-size:14px; }}
.portfolio {{ background:linear-gradient(135deg,{bg_color}22,{bg_color}11); border:2px solid {bg_color}; border-radius:16px; padding:24px; margin-bottom:20px; text-align:center; }}
.portfolio .mci-value {{ font-size:56px; font-weight:800; color:{bg_color}; line-height:1; }}
.portfolio .mci-label {{ color:#94a3b8; font-size:14px; margin-top:4px; }}
.portfolio .mama-quote {{ margin-top:16px; padding:12px 20px; background:#1e293b; border-radius:12px; font-size:15px; color:#cbd5e1; }}
.portfolio .signal {{ margin-top:12px; font-size:18px; font-weight:600; }}
.asset-card {{ background:#1e293b; border-radius:12px; padding:20px; margin-bottom:16px; border-left:4px solid #10b981; }}
.asset-header {{ display:flex; align-items:center; gap:8px; flex-wrap:wrap; margin-bottom:8px; }}
.asset-name {{ font-size:18px; font-weight:600; }}
.asset-symbol {{ color:#64748b; font-size:14px; }}
.asset-mci {{ margin-left:auto; font-size:24px; font-weight:800; }}
.asset-level {{ font-size:14px; color:#94a3b8; }}
.asset-signal {{ font-size:14px; margin-bottom:12px; color:#94a3b8; }}
.dim-row {{ display:flex; align-items:center; gap:8px; margin:6px 0; }}
.dim-name {{ width:70px; font-size:12px; color:#94a3b8; flex-shrink:0; }}
.dim-bar {{ flex:1; height:8px; background:#334155; border-radius:4px; overflow:hidden; }}
.dim-fill {{ height:100%; border-radius:4px; transition:width .3s; }}
.dim-score {{ width:36px; text-align:right; font-size:12px; color:#cbd5e1; }}
.dim-na {{ color:#475569; }}
.disclaimer {{ text-align:center; color:#475569; font-size:12px; padding:20px; margin-top:10px; }}
</style>
</head>
<body>
<div class="header">
    <h1>📋 AlphaMom 宝妈情报简报</h1>
    <div class="date">{date_str}</div>
</div>
<div class="portfolio">
    <div class="mci-value">{p_mci}%</div>
    <div class="mci-label">{level_icon} {p_level.get('level','')} · 组合宝妈狂热度</div>
    <div class="mama-quote">📢 {quote}</div>
    <div class="signal">{p_level.get('signal_icon','')} {p_level.get('signal','')}</div>
</div>
{asset_cards}
<div class="disclaimer">
    ⚠️ 本工具仅供娱乐与辅助参考,不构成任何投资建议.市场有风险,投资需谨慎.<br>
    AlphaMom — 外行看个乐,内行看门道.
</div>
</body>
</html>'''

    return html

# ─── 主流程 ───────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AlphaMom 播报生成器")
    parser.add_argument("--mci", required=True, help="MCI 结果文件路径")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--mode", default="signal", choices=["signal", "review"], help="Report mode")
    parser.add_argument("--html", help="HTML 海报输出路径(可选)")
    args = parser.parse_args()

    with open(args.mci, 'r', encoding='utf-8') as f:
        mci_data = json.load(f)
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    # 终端文本报告

    quotes_json = None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_quotes = os.path.join(script_dir, "..", "assets", "mama_quotes.json")
    if os.path.exists(default_quotes):
        try:
            with open(default_quotes, "r", encoding="utf-8-sig") as f:
                quotes_json = json.load(f)
        except:
            pass

    if args.mode == "review":
        report = generate_review_report(mci_data, config, quotes_json)
    else:
        report = generate_text_report(mci_data, config, quotes_json)
    print(report)

    # HTML 海报(可选)
    if args.html:
        html = generate_html_report(mci_data, config)
        os.makedirs(os.path.dirname(args.html), exist_ok=True)
        with open(args.html, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"[OK] HTML 海报已保存到 {args.html}", file=sys.stderr)

if __name__ == "__main__":
    main()
