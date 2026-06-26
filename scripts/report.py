#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AlphaMom — 赛博情绪广播电台版播报生成器
将 MCI 结果转化为荒诞、讽刺的“大盘避险简报”
支持终端文本输出 + HTML 海报输出
"""

import argparse
import json
import os
import sys
import random
from datetime import datetime, timedelta

# Windows encoding support
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

# ─── 赛博讽刺广播语录 ───────────────────────────────────────────────
MAMA_QUOTES = {
    "freeze": [
        "早上好，天台VIP们！昨天的“天台乐透”全员爆满！在这个连韭菜都懒得看盘的冰封期，讨论区凉得像医院的太平间。想抄底？先买好你的速效救心丸吧，韭菜们！",
        "电台频道里已经没人在提这个垃圾了。讨论菜价都比这大盘有生气。连救护车都懒得去清扫那些因爆仓而从写字楼天台跳下来的投机者尸体。",
        "公共频道里安静得像被拔了网线。上次在群里发持仓截图的倒霉蛋，他的账号已经被债主强行清算，正骑着电动车在风雨里送外卖。"
    ],
    "cold": [
        "哦，你居然还在坚守那堆废铜烂铁？连街边收废品的大爷都不屑于用它结算尾款。大家都去抢购特价大米 and 打折鸡蛋了。至于这大盘？那是什么，能当房租交吗？",
        "偶尔有些不怕死的韭菜在群里问一句‘还能接盘吗’，结果是被无情地踢出群聊。别做梦了，在这个市场里，没有人会同情你的电子钱包，它们比你的命还薄。"
    ],
    "neutral": [
        "大盘一切照旧。写字楼里的白领在加班猝死，外卖员在街头狂奔。这个标的正在温和的泥潭里打滚，没人在乎，保持你们那可怜的理智吧，接盘侠们。",
        "不温不火的一天. 本地新闻刚刚播报了三起电动车起火案，而我们的大盘指数和天台乐透一样平静。暂时死不了，但也别想翻身，祝你们好运吧。"
    ],
    "hot": [
        "早上好，未来的金融巨鳄们！快看窗外，那些平时只买得起打折方便面的底层打工人，居然开始在早餐摊上兴致勃勃地讨论公司股票的K线了！傻子们正在兴奋地擦亮眼睛，准备跑步进场。我打赌，机构的高层现在嘴都笑歪了。",
        "广播里的理财广告已经铺天盖地。连足疗店的小妹都在向你兜售‘稳赚不赔的翻倍股票’。天才交易员们开始疯狂抵押车子去加杠杆。听我一句劝：风暴要来了！"
    ],
    "lava": [
        "警告！警告！全城的贪婪值已经突破临界点！连你二姑、小区保安、甚至街角卖煎饼果子的大叔，都红着眼求你帮他开户！交易所顶楼正在放用散户骨灰做的烟花！如果你不想成为明天的天台名单，火速逃命吧，天才交易员们！",
        "熔岩爆发！朋友圈里十条有八条在晒他们的豪华SUV和度假照片。每个人都觉得自己是下一个股神巴菲特，能把庄家踩在脚下。清醒点！收尸车已经停在街角了，只要你敢进场，收尸人明天就会把你剥个精光！"
    ]
}

# ─── 维度解读 ─────────────────────────────────────────────────
DIM_INTERPRETATIONS = {
    "fear_greed": {
        "name": "合意态度",
        "high": "市场极度贪婪,韭菜亢奋想飞天",
        "mid": "情绪中性,大盘在磨洋工",
        "low": "极度绝望恐惧,韭菜们正绝望割肉"
    },
    "search_interest": {
        "name": "破圈热度",
        "high": "圈外大妈搜索暴增,新韭菜跑步接盘",
        "mid": "热度正常,无异动",
        "low": "死水微澜,根本没人搜"
    },
    "derivatives": {
        "name": "杠杆拥挤",
        "high": "高倍杠杆拥挤,资金费率过高,爆仓炸弹已拉弦",
        "mid": "杠杆水平处于安全常态",
        "low": "去杠杆彻底,市场极度冷静"
    },
    "price_trend": {
        "name": "趋势偏离",
        "high": "价格远远偏离均线,高位泡沫随时爆",
        "mid": "价格贴近MA均线,趋势正常",
        "low": "大幅低于MA均线,极度超卖"
    },
    "social_sentiment": {
        "name": "社区舆论",
        "high": "舆论狂热吹嘘,全是暴富假象",
        "mid": "讨论不温不火",
        "low": "讨论冷清,舆论偏向极度悲观"
    }
}

LEVEL_KEYS = ["freeze", "cold", "neutral", "hot", "lava"]

def get_level_key(mci):
    if mci is None: return "neutral"
    if mci <= 20: return "freeze"
    elif mci <= 40: return "cold"
    elif mci <= 60: return "neutral"
    elif mci <= 80: return "hot"
    else: return "lava"

def interpret_dim(dim_name, score):
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
    key = get_level_key(mci)
    quotes = MAMA_QUOTES.get(key, MAMA_QUOTES["neutral"])
    quote = random.choice(quotes)
    return quote

def generate_text_report(mci_data, config, report_texts):
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    lines = []
    lines.append(f"\n{'='*65}")
    lines.append(f"  🎙️ 赛博情绪广播电台 · AlphaMom 避险简报 · {date_str}")
    lines.append(f"{'='*65}")

    portfolio = mci_data.get("portfolio")
    if portfolio:
        p_mci = portfolio["mci"]
        p_level = portfolio["level"]
        mci_str = f"{p_mci}%" if p_mci is not None else "N/A"
        lines.append(f"\n  📊 组合总拥挤度: {mci_str} {p_level['icon']} {p_level['level']}")
        
        quote = report_texts["portfolio_quote"]
                
        lines.append(f"  📢 电台主播播报: {quote}")
        lines.append(f"  🔔 避险信号: {p_level['signal_icon']} {p_level['signal']}")
        lines.append(f"  👨 散户生存状态: {p_level['mama_status']}")

    lines.append(f"\n  {'─'*55}")
    lines.append(f"  📌 核心标的诊断明细:")
    for asset in mci_data.get("assets", []):
        mci = asset["mci"]
        level = asset["level"]
        sym = asset["symbol"]
        mci_str = f"{mci}%" if mci is not None else "N/A"
        market_tag = "🔐" if asset.get("market") == "crypto" else "📈"
        lines.append(f"\n  {market_tag} {asset['name']} ({asset['symbol']})")
        lines.append(f"     MCI = {mci_str} {level['icon']} {level['level']}")
        lines.append(f"     避险信号: {level['signal_icon']} {level.get('signal', '')}")
        
        asset_texts = report_texts.get("assets", {}).get(sym, {})
        advice = asset_texts.get("advice", "")
        lines.append(f"     逆向指导: {advice}")

        lines.append(f"     ┌─ 维度数据:")
        for dim_name in ["fear_greed", "search_interest", "derivatives", "price_trend", "social_sentiment"]:
            dim = asset["dimensions"].get(dim_name, {})
            score = dim.get("score")
            avail = dim.get("available", False)
            interp = interpret_dim(dim_name, score) if avail else f"{DIM_INTERPRETATIONS.get(dim_name, {}).get('name', dim_name)}: 维度数据断裂"
            lines.append(f"     │  {interp}")

        unavailable = asset.get("unavailable_dimensions", [])
        if unavailable:
            names = [DIM_INTERPRETATIONS.get(d, {}).get("name", d) for d in unavailable]
            lines.append(f"     └─ ⚠️ 降级维度: {', '.join(names)} (已动态调整权重)")
        else:
            lines.append(f"     └─ 五维空间数据完整")

    lines.append(f"\n  {'─'*55}")
    lines.append(f"  ⚠️ 免责声明: 本节目仅供广大股民娱乐参考,不构成任何投资建议.")
    lines.append(f"  股市有风险,理财有排异.跟风梭哈,后果自负.")
    lines.append(f"{'='*65}\n")

    return "\n".join(lines)


REVIEW_GOLDEN_QUOTES = [
    "Welcome to Wall Street, where the premium class buys the dip, and the retail crowd buys the peak.",
    "The market is like an expensive gadget: looks cool, until it glitches and fries your bank account.",
    "Rule number one: never trust institutional analysts. Rule number two: never buy what your taxi driver recommends.",
    "History does not repeat, but institutional greed always does.",
    "To get rich, you don't need a degree. You just need to sell when the crowd is shouting 'To the moon!'",
    "Good luck out there, genius traders. Keep your money close, and your emergency savings closer."
]

def get_asset_daily_summary(asset):
    dims = asset.get("dimensions", {})
    price_dim = dims.get("price_trend", {})
    fg_dim = dims.get("fear_greed", {})
    price_info = price_dim.get("details", price_dim) if price_dim else {}
    fg_info = fg_dim.get("details", fg_dim) if fg_dim else {}
    return {
        "name": asset.get("name", ""),
        "symbol": asset.get("symbol", ""),
        "market": asset.get("market", ""),
        "mci": asset.get("mci", 0),
        "level": asset.get("level", {}),
        "price_today": price_info.get("price_today") if price_dim and price_dim.get("available") else None,
        "ret_14d": price_info.get("ret_14d") if price_dim and price_dim.get("available") else None,
        "deviation": price_info.get("deviation") if price_dim and price_dim.get("available") else None,
        "fear_greed": fg_info.get("score") if fg_dim and fg_dim.get("available") else None,
        "fg_classification": fg_info.get("classification", "") if fg_dim and fg_dim.get("available") else None,
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
            "Today the public channel is as quiet as a graveyard. Nobody mentions anything.",
            "Coroners are busy scraping the jumpers off the pavement near the financial district, zero bid in sight.",
        ],
        "cold": [
            "Someone asked in the group chat if it's cheap enough - no response. Even the most aggressive leverage traders are offline.",
            "Retail traders are busy checking job boards or delivering food; they don't care about corporate paper right now."
        ],
        "neutral": [
            "Just another gray afternoon in the office district. Normal corporate grind, normal market flatline.",
            "Uneventful. Corporate white-collars working themselves to death, index moves sideways."
        ],
        "hot": [
            "The social media feed is getting loud. Uber drivers are bragging about their paper gains.",
            "Foot massage therapists are selling insider stock tips. The radio host says: get ready for a crash."
        ],
        "lava": [
            "Lava explosion! Everyone is trying to lease luxury sports cars. The institutions are preparing to harvest.",
            "Your aunt withdrew her pension to buy in. Radio warning: the slaughter is tonight!"
        ]
    }
    pool = reactions.get(key, reactions["neutral"])
    return random.choice(pool)

def detect_correlation(assets):
    if len(assets) < 2:
        return None
    crypto_assets = [a for a in assets if a.get("market") == "crypto" and a.get("mci") is not None]
    correlations = []
    if len(crypto_assets) >= 2:
        names = [a["name"] for a in crypto_assets]
        mcis = [a["mci"] for a in crypto_assets]
        mci_range = max(mcis) - min(mcis)
        if mci_range < 10:
            joined = " and ".join(names)
            correlations.append(joined + " move in lockstep. MCI spread only " + str(round(mci_range, 1)))
    has_crypto = any(a.get("market") == "crypto" for a in assets)
    has_astock = any(a.get("market") == "astock" for a in assets)
    if has_crypto and has_astock:
        correlations.append("You cross both corporate shares and crypto. Capital rotates between them like a seesaw.")
    return " ".join(correlations) if correlations else None

def call_deepseek_api(mci_data, config):
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    llm_conf = config.get("llm_config", {})
    if not api_key:
        api_key = llm_conf.get("deepseek_api_key")
    if not api_key:
        raise ValueError("DEEPSEEK_API_KEY not found in environment or config.")
    if not llm_conf.get("enabled", True):
        raise ValueError("LLM generation is disabled in config.")
        
    model_name = llm_conf.get("model_name", "deepseek-chat")
    api_base = llm_conf.get("api_base", "https://api.deepseek.com/v1")
    api_base = api_base.rstrip("/")
    url = f"{api_base}/chat/completions"
    
    # Prepare prompt
    import json
    input_str = json.dumps(mci_data, ensure_ascii=False, indent=2)
    
    system_prompt = """你是一个辛辣讽刺、充满幽默感的财经电台主播。你的任务是根据给定的量化情绪指标数据（宝妈反买量化指标 MCI，价格偏离，衍生品杠杆等），生成一份今日大盘避险播报。
你的称呼对象是一群狂热而又盲目的散户，请使用“天台VIP们”、“接盘侠们”、“天才交易员们”、“金融巨鳄们”或“韭菜们”等戏谑称呼。不要提到任何与游戏《赛博朋克2077》相关的名词（如夜之城、荒坂、NCPD、欧金等），纯粹对齐现实中真实的金融与理财市场（A股、加密货币、黄金、白酒等）。

你必须返回一个符合以下 JSON 结构的有效 JSON 字符串：
{
  "portfolio_quote": "今日大盘广播大白话点评",
  "assets": {
    "SYMBOL": {
      "quote": "该资产的戏谑点评",
      "advice": "该资产的逆向操作避险建议"
    }
  },
  "tomorrow_watch": [
    "明日警告关注点 1",
    "明日警告关注点 2"
  ],
  "golden_quote": "今日电台金句"
}
"""

    user_prompt = f"""这是今日的量化数据，请分析并生成避险播报：
{input_str}
"""

    import requests
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "response_format": {
            "type": "json_object"
        },
        "temperature": 0.7
    }
    
    response = requests.post(url, headers=headers, json=payload, timeout=20)
    response.raise_for_status()
    
    res_json = response.json()
    text_content = res_json["choices"][0]["message"]["content"]
    
    # Parse the text response as JSON robustly stripping markdown blocks
    content = text_content.strip()
    if content.startswith("```json"):
        content = content[7:]
    if content.startswith("```"):
        content = content[3:]
    if content.endswith("```"):
        content = content[:-3]
    parsed = json.loads(content.strip())
    return parsed

def get_fallback_report_texts(mci_data, config, quotes_json=None):
    portfolio = mci_data.get("portfolio", {})
    p_mci = portfolio.get("mci")
    
    portfolio_quote = get_mama_quote(p_mci, config.get("sass_level", "medium"))
    if quotes_json:
        key = get_level_key(p_mci)
        if key in quotes_json:
            portfolio_quote = random.choice(quotes_json[key])
            
    assets = {}
    for asset in mci_data.get("assets", []):
        mci = asset["mci"]
        sym = asset["symbol"]
        quote = describe_mama_reaction(mci, quotes_json)
        
        sym_upper = sym.upper()
        if mci is None:
            advice = "Data node offline. Diagnostic unavailable."
        else:
            if "518880" in sym_upper or "黄金" in asset.get("name", ""):
                if mci >= 81:
                    advice = "黄金暴涨！街头疯传金条比房产证还保值，接盘侠们甚至连夜去金店排队抢购，狂热度彻底炸裂！强烈建议逢高分批抛售，把本金落袋为安，快逃！"
                elif mci >= 61:
                    advice = "金价新高让写字楼里的投机狗们蠢蠢欲动，午餐时间全在讨论是买实物金还是开通加倍杠杆。风暴将至，建议分批止盈，降低仓位。"
                elif mci >= 41:
                    advice = "避险金属在箱体正常调整，庄家和投机客都对它反应平平。"
                elif mci >= 21:
                    advice = "金价低位盘整，天才交易员们嫌弃黄金没有垃圾题材股刺激，兴趣寥寥。逆向来看，这反而是绝佳的避险防御配置期。"
                else:
                    advice = "黄金冷门无人问津，金店专柜冷清得只有流浪汉在捡垃圾，大伙直呼黄金是旧时代遗产。逆向思考：这正是分批低吸的黄金底！"
            elif "161725" in sym_upper or "白酒" in asset.get("name", ""):
                if mci >= 81:
                    advice = "白酒基金净值狂飙，讨论区纷纷直呼‘股神万岁’，社畜把买房的私房钱全梭哈了。贪婪爆表！强烈建议立刻分批套现离场，别等庄家拔插头！"
                elif mci >= 61:
                    advice = "白酒异动，隔壁的游资大佬都在打听要不要上车。拉响高位警报，别做机构的垫脚石，建议开始逢高分批减仓。"
                elif mci >= 41:
                    advice = "白酒板块正常盘整，散户们反应中性，无异常追加或割肉。建议暂时保持底仓，静观其变。"
                elif mci >= 21:
                    advice = "白酒阴跌不断，大伙直叹气表示‘年轻人不喝白酒了，只喝气泡水和咖啡了’。情绪偏冷，中线布局的筹码正在变得便宜。"
                else:
                    advice = "白酒板块崩盘跌破红线，讨论区一片尸骨无存的哀嚎，都在痛骂‘基金经理下课’。情绪极寒，主力筹码出清，正是中线分批捡漏的黄金大坑！"
            elif "600519" in sym_upper or "茅台" in asset.get("name", ""):
                if mci >= 81:
                    advice = "核心资产被炒到了天上，炒家和白领都在疯狂囤货，扬言它能涨到云端。泡沫明显，强烈建议逢高分批套现退场，天才交易员们！"
                elif mci >= 61:
                    advice = "股价反弹，朋友圈里的微商和炒客都在吹嘘资产金融属性。注意保护好你的核心利润，防范机构高位收网，建议考虑减仓。"
                elif mci >= 41:
                    advice = "茅台在平稳波动，街头没有任何异常的买卖动静。建议继续保持仓位不动，吃瓜看戏。"
                elif mci >= 21:
                    advice = "低迷横盘，大伙表示‘传统股已经没有成长性了’。大盘情绪偏冷，适合中长线分批逐步建仓。"
                else:
                    advice = "直线下跌，大伙惊呼‘信仰已死，以后不碰实体股了’。逆向思维：高端消费资产被极度超卖，正是左侧大举分批买入的良机！"
            else: # Crypto (BTC/ETH) or general
                if mci >= 81:
                    advice = "市场彻底疯了！每个人都自以为是下一个暴富股神，狂晒千倍神话收益，连办公楼底下的快餐阿姨都在问你怎么开户！狂热度炸裂！快火速抛售退场！"
                elif mci >= 61:
                    advice = "韭菜们开始打听如何注册去中心化钱包，热度正在上升。空气里满是危险的本金炮灰味，建议提高警惕，保护利润，分批高抛。"
                elif mci >= 41:
                    advice = "市场处于正常盘整区间，大伙都在各自按部就班生活。建议继续持有，静观其变。"
                elif mci >= 21:
                    advice = "筹码无人问津，甚至有人为了生活费把交易账户清算注销了。逆向而言，这往往是中线分批建仓的宁静良机。"
                else:
                    advice = "大伙已割肉离场，频道里死寂一片，上次提到这名字的家伙已经被交易所清算归零。极度深寒正是主力的吸筹坑，买入信号极为强烈！"
        assets[sym] = {"quote": quote, "advice": advice}
        
    tomorrow_watch = []
    if p_mci is None:
        tomorrow_watch.append("暂无足够数据评估明日方向。")
    elif p_mci >= 61:
        tomorrow_watch.append("当前贪婪度过热。明天重点关注社交媒体是否出现新的散户跑步开户、甚至抵押家当梭哈的信号。")
        tomorrow_watch.append("如果组合 MCI 突破 80%，需坚决执行止盈减仓计划，保住你可怜的本金。")
    elif p_mci <= 40:
        tomorrow_watch.append("韭菜退潮。指数进入深度超卖的恐慌底部，密切关注主力低吸企稳信号。")
        tomorrow_watch.append("若组合 MCI 跌破 20%，这是散户与游资逆袭重仓的绝佳黄金坑。")
    else:
        tomorrow_watch.append("当前市场情绪中性。以静制动，捂紧你的钱包，切忌盲目追高或割肉。")
        
    golden_quote = random.choice(REVIEW_GOLDEN_QUOTES)
    
    return {
        "portfolio_quote": portfolio_quote,
        "assets": assets,
        "tomorrow_watch": tomorrow_watch,
        "golden_quote": golden_quote
    }

def get_report_texts(mci_data, config, quotes_json=None):
    try:
        print("[INFO] 尝试使用 DeepSeek 大模型生成今日动态播报...", file=sys.stderr)
        return call_deepseek_api(mci_data, config)
    except Exception as e:
        print(f"[WARN] DeepSeek 生成失败，自动启用本地静态模板降级: {e}", file=sys.stderr)
        return get_fallback_report_texts(mci_data, config, quotes_json)

def generate_review_report(mci_data, config, report_texts):
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = []
    lines.append("")
    lines.append("=" * 60)
    lines.append("  🎙️ Cyber Sentiment Radio Daily Review - " + date_str)
    lines.append("=" * 60)
    portfolio = mci_data.get("portfolio", {})
    p_mci = portfolio.get("mci")
    p_level = portfolio.get("level", {})
    p_mci_str = f"{p_mci}%" if p_mci is not None else "N/A"
    lines.append("")
    lines.append("  Today's city state in one sentence:")
    lines.append("  Portfolio Crowd Intensity: " + p_mci_str + " " + str(p_level.get("icon", "")) + " " + str(p_level.get("level", "")))
    lines.append("  " + str(p_level.get("mama_status", "")))
    
    quote = report_texts["portfolio_quote"]
    lines.append("  " + quote)
    lines.append("")
    lines.append("=" * 56)
    lines.append("  Diagnostic Breakdown:")
    for asset in mci_data.get("assets", []):
        summary = get_asset_daily_summary(asset)
        mci = summary["mci"]
        sym = summary["symbol"]
        mci_str = f"{mci}%" if mci is not None else "N/A"
        level = summary["level"]
        market_tag = "[C]" if summary["market"] == "crypto" else "[A]"
        lines.append("")
        lines.append("  " + market_tag + " " + summary["name"] + " (" + summary["symbol"] + ")")
        lines.append("     MCI: " + mci_str + " " + str(level.get("icon", "")) + " " + str(level.get("level", "")))
        
        lines.append("     Signal: " + str(level.get("signal_icon", "")) + " " + str(level.get("signal", "")))
        
        asset_texts = report_texts.get("assets", {}).get(sym, {})
        advice = asset_texts.get("advice", "")
        asset_quote = asset_texts.get("quote", "")
        
        lines.append("     Advice: " + advice)
        lines.append("     Price action: " + describe_price_action(summary))
        if summary["fear_greed"] is not None:
            fg = summary["fear_greed"]
            fg_cls = summary["fg_classification"]
            if not fg_cls:
                if fg <= 20:
                    fg_cls = "Extreme Fear"
                elif fg <= 40:
                    fg_cls = "Fear"
                elif fg <= 60:
                    fg_cls = "Neutral"
                elif fg <= 80:
                    fg_cls = "Greed"
                else:
                    fg_cls = "Extreme Greed"
            lines.append("     Fear/Greed: " + str(fg) + " (" + fg_cls + ")")
        lines.append("     City Pulse: " + asset_quote)
        
    correlation = detect_correlation(mci_data.get("assets", []))
    if correlation:
        lines.append("")
        lines.append("=" * 56)
        lines.append("  Sector correlation:")
        lines.append("  " + correlation)
    lines.append("")
    lines.append("=" * 56)
    lines.append("  Tomorrow's Watch:")
    for watch_item in report_texts.get("tomorrow_watch", []):
        lines.append("  - " + watch_item)
    lines.append("")
    lines.append("=" * 56)
    lines.append("  City Golden Quote:")
    lines.append('  "' + report_texts.get("golden_quote", "") + '"')
    lines.append("")
    lines.append("-" * 56)
    lines.append("  Disclaimer: For entertainment only. Keep your hard-earned money safe.")
    lines.append("=" * 60)
    lines.append("")
    return "\n".join(lines)

def generate_html_report(mci_data, config, report_texts):
    date_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    portfolio = mci_data.get("portfolio", {})
    p_mci = portfolio.get("mci", 0)
    p_level = portfolio.get("level", {})
    
    color_map = {"🧊": "#3b82f6", "❄️": "#06b6d4", "😐": "#10b981", "🔥": "#f59e0b", "🌋": "#ef4444"}
    level_icon = p_level.get("icon", "😐")
    bg_color = color_map.get(level_icon, "#10b981")
    
    asset_cards = ""
    for asset in mci_data.get("assets", []):
        mci = asset["mci"]
        level = asset["level"]
        sym = asset["symbol"]
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
        asset_texts = report_texts.get("assets", {}).get(sym, {})
        advice = asset_texts.get("advice", level.get("signal", ""))
        
        asset_cards += f'''
        <div class="asset-card" style="border-left-color:{asset_color}">
            <div class="asset-header">
                <span class="asset-icon">{market_tag}</span>
                <span class="asset-name">{asset['name']}</span>
                <span class="asset-symbol">{asset['symbol']}</span>
                <span class="asset-mci" style="color:{asset_color}">{mci}%</span>
                <span class="asset-level">{level.get('icon','')} {level.get('level','')}</span>
            </div>
            <div class="asset-signal">{level.get('signal_icon','')} {advice}</div>
            <div class="dims">{dims_html}</div>
        </div>'''

    quote = report_texts["portfolio_quote"]

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>AlphaMom 赛博情绪广播 · {date_str}</title>
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
    <h1>🎙️ 赛博情绪广播电台 · AlphaMom</h1>
    <div class="date">{date_str}</div>
</div>
<div class="portfolio">
    <div class="mci-value">{p_mci}%</div>
    <div class="mci-label">{level_icon} {p_level.get('level','')} · 组合拥挤度</div>
    <div class="mama-quote">📢 {quote}</div>
    <div class="signal">{p_level.get('signal_icon','')} {p_level.get('signal','')}</div>
</div>
{asset_cards}
<div class="disclaimer">
    ⚠️ 免责声明: 本简报仅供娱乐参考，不构成投资建议。市场有风险，投资需谨慎，盈亏自负。<br>
    AlphaMom — 外行看个乐，内行看门道。
</div>
</body>
</html>'''

    return html

def update_history(mci_data):
    history_file = "data/history.json"
    history = []
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
        except:
            history = []
            
    if not history:
        base_date = datetime.now() - timedelta(days=15)
        mock_btc_price = 55000.0
        mock_eth_price = 1400.0
        for i in range(15):
            date_str = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
            mock_btc_price += random.randint(-1500, 1800)
            mock_eth_price += random.randint(-50, 70)
            mock_mci = 30.0 + random.randint(-15, 20)
            history.append({
                "date": date_str,
                "portfolio_mci": round(mock_mci, 1),
                "btc_price": round(mock_btc_price, 2),
                "btc_mci": round(mock_mci * 0.9 + random.randint(-5, 5), 1),
                "eth_price": round(mock_eth_price, 2),
                "eth_mci": round(mock_mci * 1.1 + random.randint(-5, 5), 1),
                "maotai_price": None,
                "maotai_mci": None
            })
            
    today_str = datetime.now().strftime("%Y-%m-%d")
    history = [h for h in history if h["date"] != today_str]
    
    portfolio = mci_data.get("portfolio", {})
    p_mci = portfolio.get("mci")
    
    today_entry = {
        "date": today_str,
        "portfolio_mci": p_mci
    }
    
    for asset in mci_data.get("assets", []):
        sym = asset["symbol"].lower()
        mci = asset["mci"]
        today_entry[f"{sym}_mci"] = mci
        
        dims = asset.get("dimensions", {})
        price_dim = dims.get("price_trend", {})
        price_info = price_dim.get("details", price_dim) if price_dim else {}
        price = price_info.get("price_today")
        today_entry[f"{sym}_price"] = price
        
    history.append(today_entry)
    
    os.makedirs(os.path.dirname(history_file), exist_ok=True)
    with open(history_file, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

def generate_web_report(mci_data, config, report_texts):
    web_report_file = "data/web_report.json"
    
    portfolio = mci_data.get("portfolio", {})
    p_mci = portfolio.get("mci")
    p_level = portfolio.get("level", {})
    
    quote = report_texts["portfolio_quote"]
            
    assets_list = []
    for asset in mci_data.get("assets", []):
        summary = get_asset_daily_summary(asset)
        mci = summary["mci"]
        level = summary["level"]
        sym = summary["symbol"]
        
        asset_texts = report_texts.get("assets", {}).get(sym, {})
        advice = asset_texts.get("advice", level.get("signal", ""))
        mama_reaction = asset_texts.get("quote", "")
        
        dims_data = {}
        for dname in ["fear_greed", "search_interest", "derivatives", "price_trend", "social_sentiment"]:
            dim = asset["dimensions"].get(dname, {})
            dims_data[dname] = {
                "score": dim.get("score"),
                "available": dim.get("available", False),
                "name": DIM_INTERPRETATIONS.get(dname, {}).get("name", dname)
            }
            
        assets_list.append({
            "symbol": summary["symbol"],
            "name": summary["name"],
            "market": summary["market"],
            "mci": mci,
            "level": level,
            "price": summary["price_today"],
            "price_change_14d": summary["ret_14d"],
            "deviation": summary["deviation"],
            "fear_greed": summary["fear_greed"],
            "fear_greed_classification": summary["fg_classification"],
            "quote": mama_reaction,
            "advice": advice,
            "dimensions": dims_data,
            "unavailable_dimensions": asset.get("unavailable_dimensions", [])
        })
        
    correlation = detect_correlation(mci_data.get("assets", []))
    tomorrow_watch = report_texts.get("tomorrow_watch", [])
    golden_quote = report_texts.get("golden_quote", "")
    
    web_data = {
        "timestamp": datetime.now().isoformat(),
        "portfolio": {
            "mci": p_mci,
            "level": p_level,
            "quote": quote
        },
        "assets": assets_list,
        "correlation": correlation,
        "tomorrow_watch": tomorrow_watch,
        "golden_quote": golden_quote
    }
    
    os.makedirs(os.path.dirname(web_report_file), exist_ok=True)
    with open(web_report_file, 'w', encoding='utf-8') as f:
        json.dump(web_data, f, ensure_ascii=False, indent=2)
    print(f"[OK] Web 报告数据已保存到 {web_report_file}", file=sys.stderr)

def main():
    parser = argparse.ArgumentParser(description="AlphaMom Financial Radio Generator")
    parser.add_argument("--mci", required=True, help="MCI 结果文件路径")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--mode", default="signal", choices=["signal", "review"], help="Report mode")
    parser.add_argument("--html", help="HTML 海报输出路径(可选)")
    args = parser.parse_args()

    with open(args.mci, 'r', encoding='utf-8') as f:
        mci_data = json.load(f)
    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    quotes_json = None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    default_quotes = os.path.join(script_dir, "..", "assets", "mama_quotes.json")
    if os.path.exists(default_quotes):
        try:
            with open(default_quotes, "r", encoding="utf-8-sig") as f:
                quotes_json = json.load(f)
        except:
            pass

    # Fetch report texts (via DeepSeek LLM or fallback)
    report_texts = get_report_texts(mci_data, config, quotes_json)

    if args.mode == "review":
        report = generate_review_report(mci_data, config, report_texts)
    else:
        report = generate_text_report(mci_data, config, report_texts)
    print(report)

    try:
        update_history(mci_data)
        generate_web_report(mci_data, config, report_texts)
    except Exception as e:
        print(f"[WARN] 自动更新 Web 报表失败: {e}", file=sys.stderr)

    if args.html:
        html = generate_html_report(mci_data, config, report_texts)
        os.makedirs(os.path.dirname(args.html), exist_ok=True)
        with open(args.html, 'w', encoding='utf-8') as f:
            f.write(html)
        print(f"[OK] HTML 海报已保存到 {args.html}", file=sys.stderr)

if __name__ == "__main__":
    main()
