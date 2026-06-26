#!/usr/bin/env python3
"""
AlphaMom — 加密货币数据采集模块
采集五大维度中的加密相关数据:
  1. 恐惧贪婪指数 (Alternative.me API)
  2. 搜索热度 (Google Trends / 降级: Alternative.me 社交子项)
  3. 衍生品杠杆拥挤度 (CoinGlass API)
  4. 价格-趋势偏离 (CoinGecko API)
  5. 社区情绪语义 (Reddit PRAW + VADER)
"""

import argparse
import json
import os
import sys
import time
import math
import statistics
from datetime import datetime, timedelta
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

def fetch_json(url, headers=None, timeout=15):
    """通用 JSON 获取"""
    req = Request(url)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)
    resp = urlopen(req, timeout=timeout)
    return json.loads(resp.read().decode('utf-8'))

# ─── 维度1: 恐惧贪婪指数 ──────────────────────────────────────
def fetch_fear_greed():
    """从 Alternative.me 获取恐惧贪婪指数(免费、无key)"""
    try:
        url = "https://api.alternative.me/fng/?limit=30"
        data = fetch_json(url)
        values = data.get("data", [])
        if not values:
            return None
        current = int(values[0]["value"])
        classification = values[0].get("value_classification", "")
        # 最近7天均值
        recent_7d = [int(v["value"]) for v in values[:7]]
        avg_7d = sum(recent_7d) / len(recent_7d)
        return {
            "score": current,
            "classification": classification,
            "avg_7d": round(avg_7d, 1),
            "history_30d": [int(v["value"]) for v in values],
            "available": True
        }
    except Exception as e:
        print(f"[WARN] 恐惧贪婪指数获取失败: {e}", file=sys.stderr)
        return {"available": False, "error": str(e)}

# ─── 维度2: 搜索热度 ──────────────────────────────────────────
def fetch_search_interest(keyword="bitcoin"):
    """Google Trends 搜索热度(降级: Alternative.me 社交子项)"""
    # 尝试 PyTrends
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl='en-US', tz=360, timeout=10, retries=1, backoff_factor=0.5)
        pytrends.build_payload([keyword], timeframe='today 3-m', geo='')
        df = pytrends.interest_over_time()
        if df.empty:
            raise ValueError("empty dataframe")
        current = df[keyword].tail(7).mean()
        peak_90d = df[keyword].max()
        score = min(current / peak_90d * 100, 100) if peak_90d > 0 else 50
        return {
            "score": round(score, 1),
            "current_7d_avg": round(current, 1),
            "peak_90d": int(peak_90d),
            "source": "google_trends",
            "available": True
        }
    except Exception as e:
        print(f"[INFO] PyTrends 不可用({e}),降级到 Alternative.me 社交子项", file=sys.stderr)
        # 降级: 用 Alternative.me 的数据(无法拆子项时用 F&G 本身近似)
        return {
            "score": 50,
            "source": "fallback_neutral",
            "available": False,
            "error": str(e)
        }

# ─── 维度3: 衍生品杠杆拥挤度 ──────────────────────────────────
def fetch_derivatives(symbol="BTC"):
    """CoinGlass 衍生品数据(持仓量、资金费率、多空比)"""
    result = {"available": False, "error": None}
    
    # 尝试 CoinGlass 公开端点
    try:
        # Open Interest
        oi_url = f"https://open-api-v3.coinglass.com/api/futures/openInterest?symbol={symbol}&interval=0&exchange=Binance"
        oi_data = fetch_json(oi_url, timeout=10)
        oi_list = oi_data.get("data", [])
        if oi_list:
            oi_current = float(oi_list[0].get("openInterest", 0))
            oi_amount = float(oi_list[0].get("amount", 0))
        else:
            oi_current = 0
            oi_amount = 0
    except Exception as e:
        print(f"[WARN] CoinGlass OI 获取失败: {e}", file=sys.stderr)
        oi_current = 0
        oi_amount = 0

    # 尝试 Funding Rate (公开页面 API)
    try:
        fr_url = f"https://open-api-v3.coinglass.com/api/futures/fundingRate?symbol={symbol}&exchange=Binance"
        fr_data = fetch_json(fr_url, timeout=10)
        fr_list = fr_data.get("data", [])
        funding_rate = float(fr_list[0].get("rate", 0)) if fr_list else 0
    except Exception as e:
        print(f"[WARN] CoinGlass Funding Rate 获取失败: {e}", file=sys.stderr)
        funding_rate = 0

    # 尝试 Long/Short Ratio
    try:
        ls_url = f"https://open-api-v3.coinglass.com/api/futures/longShortRatio?symbol={symbol}&interval=1h&exchange=Binance"
        ls_data = fetch_json(ls_url, timeout=10)
        ls_list = ls_data.get("data", [])
        if ls_list:
            long_ratio = float(ls_list[0].get("longRate", 0.5))
            short_ratio = float(ls_list[0].get("shortRate", 0.5))
        else:
            long_ratio = 0.5
            short_ratio = 0.5
    except Exception as e:
        print(f"[WARN] CoinGlass Long/Short 获取失败: {e}", file=sys.stderr)
        long_ratio = 0.5
        short_ratio = 0.5

    # 如果所有子项都是0,标记不可用
    if oi_current == 0 and funding_rate == 0:
        return result

    # 计算子分
    # OI Score: 需要历史对比,这里用绝对值近似(OI越高越拥挤)
    # 降级:没有历史时用 50 作为基准
    oi_score = 50  # 默认中性,有历史数据时替换
    
    # Funding Rate Score: >0 = 多头拥挤
    funding_score = max(0, min(100, 50 + funding_rate * 5000))
    
    # Long/Short Ratio Score: long > short = 多头拥挤
    ls_ratio_score = max(0, min(100, 50 + (long_ratio - 0.5) * 100))

    composite = (oi_score + funding_score + ls_ratio_score) / 3

    return {
        "score": round(composite, 1),
        "oi": oi_current,
        "oi_amount": oi_amount,
        "funding_rate": funding_rate,
        "long_ratio": long_ratio,
        "short_ratio": short_ratio,
        "sub_scores": {
            "oi_score": oi_score,
            "funding_score": round(funding_score, 1),
            "ls_ratio_score": round(ls_ratio_score, 1)
        },
        "available": True
    }

# ─── 维度4: 价格-趋势偏离 ─────────────────────────────────────
def fetch_price_data(coin_id="bitcoin"):
    """CoinGecko 获取价格历史(免费、无key)"""
    try:
        # 获取365天日线数据
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart?vs_currency=usd&days=365&interval=daily"
        data = fetch_json(url, timeout=20)
        prices = [p[1] for p in data.get("prices", [])]
        if len(prices) < 30:
            return {"available": False, "error": "insufficient price data"}

        price_today = prices[-1]
        price_14d_ago = prices[-15] if len(prices) >= 15 else prices[0]

        # 200日均线(如果数据不足200天,用全部数据的均值)
        ma_period = min(200, len(prices))
        ma_value = sum(prices[-ma_period:]) / ma_period

        # 偏离率
        deviation = (price_today - ma_value) / ma_value if ma_value > 0 else 0
        trend_score = max(0, min(100, 50 + deviation * 200))

        # 14日动量
        ret_14d = (price_today / price_14d_ago - 1) if price_14d_ago > 0 else 0
        
        # 动量百分位:用过去252天(或可用数据)的14日收益率排序
        lookback = min(252, len(prices) - 14)
        if lookback > 10:
            rolling_returns = []
            for i in range(lookback, 0, -1):
                if len(prices) > i + 14 and prices[i] > 0:
                    r = prices[-(i+14)] / prices[-(i)] - 1 if i + 14 < len(prices) else 0
                    if prices[-(i)] > 0:
                        r = (prices[-(i)] / prices[-(i+14)] - 1)
                        rolling_returns.append(r)
            if rolling_returns:
                rank = sum(1 for r in rolling_returns if r <= ret_14d) / len(rolling_returns)
                momentum_score = rank * 100
            else:
                momentum_score = 50
        else:
            momentum_score = 50

        price_score = 0.5 * trend_score + 0.5 * momentum_score

        return {
            "score": round(price_score, 1),
            "price_today": price_today,
            "price_14d_ago": price_14d_ago,
            "ma_value": round(ma_value, 2),
            "ma_period": ma_period,
            "deviation": round(deviation * 100, 2),
            "ret_14d": round(ret_14d * 100, 2),
            "sub_scores": {
                "trend_score": round(trend_score, 1),
                "momentum_score": round(momentum_score, 1)
            },
            "available": True
        }
    except Exception as e:
        print(f"[WARN] CoinGecko 价格数据获取失败: {e}", file=sys.stderr)
        return {"available": False, "error": str(e)}

# ─── 维度5: 社区情绪语义 ──────────────────────────────────────
def fetch_social_sentiment(keyword="bitcoin", subreddit="CryptoCurrency"):
    """Reddit 社区情绪分析(PRAW + VADER)"""
    # 尝试 PRAW
    try:
        import praw
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
        
        # 需要 Reddit API credentials(从环境变量读取)
        reddit = praw.Reddit(
            client_id=os.environ.get("REDDIT_CLIENT_ID", ""),
            client_secret=os.environ.get("REDDIT_CLIENT_SECRET", ""),
            user_agent="AlphaMom/1.0 by alphamom_bot",
            check_for_async=False
        )
        
        if not os.environ.get("REDDIT_CLIENT_ID"):
            raise ValueError("REDDIT_CLIENT_ID not set")
        
        analyzer = SentimentIntensityAnalyzer()
        sub = reddit.subreddit(subreddit)
        posts = list(sub.search(keyword, time_filter='week', limit=50))
        
        if not posts:
            return {"score": 50, "source": "reddit", "available": False, "error": "no posts found"}

        post_count = len(posts)
        avg_upvotes = sum(p.score for p in posts) / post_count
        sentiments = [analyzer.polarity_scores(p.title)['compound'] for p in posts]
        avg_sentiment = sum(sentiments) / len(sentiments)

        # 讨论量评分(需要历史基准,降级用绝对值近似)
        volume_score = min(100, post_count * 2)  # 50帖≈100分
        sentiment_score = max(0, min(100, 50 + avg_sentiment * 50))

        score = 0.6 * volume_score + 0.4 * sentiment_score

        return {
            "score": round(score, 1),
            "post_count": post_count,
            "avg_upvotes": round(avg_upvotes, 1),
            "avg_sentiment": round(avg_sentiment, 3),
            "source": "reddit_praw",
            "available": True
        }
    except Exception as e:
        print(f"[INFO] Reddit PRAW 不可用({e}),降级到中性", file=sys.stderr)
        return {"score": 50, "source": "fallback_neutral", "available": False, "error": str(e)}

# ─── 主流程 ───────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AlphaMom 加密数据采集")
    parser.add_argument("--config", required=True, help="配置文件路径")
    parser.add_argument("--output", required=True, help="输出文件路径")
    args = parser.parse_args()

    with open(args.config, 'r', encoding='utf-8') as f:
        config = json.load(f)

    crypto_assets = config.get("crypto_assets", [])
    if not crypto_assets:
        print("[INFO] 无加密标的配置,跳过", file=sys.stderr)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump({"assets": []}, f, ensure_ascii=False, indent=2)
        return

    # 全局数据(不分标的的维度)
    print("[1/5] 采集恐惧贪婪指数...", file=sys.stderr)
    fear_greed = fetch_fear_greed()
    time.sleep(1)

    print("[2/5] 采集搜索热度...", file=sys.stderr)
    search_keyword = crypto_assets[0].get("search_keyword", "bitcoin")
    search_interest = fetch_search_interest(search_keyword)
    time.sleep(1)

    results = []
    for asset in crypto_assets:
        coin_id = asset.get("coin_id", "bitcoin")
        symbol = asset.get("symbol", "BTC").upper()
        name = asset.get("name", symbol)

        print(f"\n=== 处理 {name} ({coin_id}) ===", file=sys.stderr)

        print(f"[3/5] 采集 {symbol} 衍生品数据...", file=sys.stderr)
        derivatives = fetch_derivatives(symbol)
        time.sleep(1)

        print(f"[4/5] 采集 {name} 价格数据...", file=sys.stderr)
        price_data = fetch_price_data(coin_id)
        time.sleep(1)

        print(f"[5/5] 采集 {name} 社区情绪...", file=sys.stderr)
        social = fetch_social_sentiment(keyword=name.lower())

        results.append({
            "symbol": symbol,
            "name": name,
            "coin_id": coin_id,
            "weight": asset.get("weight", 1.0),
            "dimensions": {
                "fear_greed": fear_greed,
                "search_interest": search_interest,
                "derivatives": derivatives,
                "price_trend": price_data,
                "social_sentiment": social
            }
        })

    output = {
        "timestamp": datetime.now().isoformat(),
        "market": "crypto",
        "assets": results
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] 加密数据已保存到 {args.output}", file=sys.stderr)

if __name__ == "__main__":
    main()
