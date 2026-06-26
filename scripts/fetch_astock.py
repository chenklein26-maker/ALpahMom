#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AlphaMom - A-Stock Data Fetcher v2 (Domestic Sources)
All data from AKShare. Dimensions:
  1. Fear & Greed: index_fear_greed_funddb
  2. Search proxy: market turnover percentile + limit-up count
  3. Leverage: margin balance + northbound capital flow
  4. Price-Trend: stock_zh_a_hist
  5. Social proxy: news sentiment index (fallback: neutral)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timedelta


def safe_akshare():
    try:
        import akshare as ak
        return ak
    except ImportError:
        print("[WARN] akshare not installed", file=sys.stderr)
        return None


def fetch_fear_greed(ak):
    if not ak:
        return {"available": False, "error": "akshare not installed"}
    try:
        df = ak.index_fear_greed_funddb(symbol="沪深300")
        if df is None or df.empty:
            return {"available": False, "error": "empty data"}
        latest = df.iloc[-1]
        col = "index" if "index" in df.columns else "fear"
        score = float(latest.get(col, 50))
        recent_7d = df.tail(7)
        avg_7d = float(recent_7d[col].mean())
        return {"score": round(score, 1), "avg_7d": round(avg_7d, 1), "available": True}
    except Exception as e:
        print(f"[WARN] F&G failed: {e}", file=sys.stderr)
        return {"available": False, "error": str(e)}


def fetch_turnover_rate(ak):
    if not ak:
        return {"available": False, "error": "akshare not installed"}
    try:
        df = ak.stock_zh_index_daily(symbol="sh000001")
        if df is None or df.empty:
            return {"available": False, "error": "empty index data"}
        df = df.tail(252)
        vol_col = None
        for c in ["成交量", "volume"]:
            if c in df.columns:
                vol_col = c
                break
        if not vol_col:
            return {"available": False, "error": "no volume column"}
        volumes = df[vol_col].astype(float).tolist()
        recent_7d_avg = sum(volumes[-7:]) / 7
        rank = sum(1 for v in volumes if v <= recent_7d_avg) / len(volumes)
        return {"score": round(rank * 100, 1), "recent_7d_avg_vol": round(recent_7d_avg, 0), "source": "market_turnover_proxy", "available": True}
    except Exception as e:
        print(f"[WARN] Turnover failed: {e}", file=sys.stderr)
        return {"available": False, "error": str(e)}


def fetch_limit_up_count(ak):
    if not ak:
        return {"available": False, "error": "akshare not installed"}
    try:
        today = datetime.now().strftime("%Y%m%d")
        df = ak.stock_zt_pool_em(date=today)
        if df is None or df.empty:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y%m%d")
            df = ak.stock_zt_pool_em(date=yesterday)
        if df is None or df.empty:
            return {"available": False, "error": "no limit-up data"}
        count = len(df)
        score = min(100, count * 0.8)
        return {"score": round(score, 1), "limit_up_count": count, "source": "stock_zt_pool_em", "available": True}
    except Exception as e:
        print(f"[WARN] Limit-up count failed: {e}", file=sys.stderr)
        return {"available": False, "error": str(e)}


def fetch_search_interest(ak):
    turnover = fetch_turnover_rate(ak)
    limit_up = fetch_limit_up_count(ak)
    if turnover.get("available") and limit_up.get("available"):
        combined = 0.5 * turnover["score"] + 0.5 * limit_up["score"]
        return {"score": round(combined, 1), "turnover_score": turnover["score"], "limit_up_score": limit_up["score"], "limit_up_count": limit_up.get("limit_up_count", 0), "source": "turnover_and_limitup", "available": True}
    elif turnover.get("available"):
        return {**turnover, "source": "turnover_only"}
    elif limit_up.get("available"):
        return {**limit_up, "source": "limitup_only"}
    else:
        return {"available": False, "error": "both failed"}


def fetch_margin_balance(ak):
    if not ak:
        return {"available": False, "error": "akshare not installed"}
    try:
        df = ak.stock_margin_sse(start_date=(datetime.now() - timedelta(days=30)).strftime("%Y%m%d"), end_date=datetime.now().strftime("%Y%m%d"))
        if df is None or df.empty:
            return {"available": False, "error": "empty margin data"}
        col = None
        for c in df.columns:
            if "融资" in c and "余额" in c:
                col = c
                break
        if not col:
            return {"available": False, "error": "no margin balance column"}
        values = df[col].astype(float).tolist()
        if len(values) < 2:
            return {"available": False, "error": "insufficient data"}
        current = values[-1]
        prev_7d = values[-8] if len(values) >= 8 else values[0]
        change_pct = (current / prev_7d - 1) * 100 if prev_7d > 0 else 0
        score = max(0, min(100, 50 + change_pct * 10))
        return {"score": round(score, 1), "margin_balance": current, "change_7d_pct": round(change_pct, 2), "source": "stock_margin_sse", "available": True}
    except Exception as e:
        print(f"[WARN] Margin balance failed: {e}", file=sys.stderr)
        return {"available": False, "error": str(e)}


def fetch_northbound_flow(ak):
    if not ak:
        return {"available": False, "error": "akshare not installed"}
    try:
        df = ak.stock_hsgt_hist_em(symbol="北向资金")
        if df is None or df.empty:
            return {"available": False, "error": "empty northbound data"}
        recent = df.tail(5)
        flow_col = None
        for c in recent.columns:
            if "净流" in c or "资金" in c:
                flow_col = c
                break
        if not flow_col:
            return {"available": False, "error": "no flow column"}
        net_flows = recent[flow_col].astype(float).tolist()
        total_5d = sum(net_flows)
        if total_5d > 0:
            score = min(100, 50 + min(abs(total_5d) / 10, 50))
        else:
            score = max(0, 50 - min(abs(total_5d) / 10, 50))
        return {"score": round(score, 1), "net_flow_5d": round(total_5d, 2), "source": "stock_hsgt_hist_em", "available": True}
    except Exception as e:
        print(f"[WARN] Northbound flow failed: {e}", file=sys.stderr)
        return {"available": False, "error": str(e)}


def fetch_derivatives(ak):
    margin = fetch_margin_balance(ak)
    northbound = fetch_northbound_flow(ak)
    if margin.get("available") and northbound.get("available"):
        combined = 0.6 * margin["score"] + 0.4 * northbound["score"]
        return {"score": round(combined, 1), "margin_score": margin["score"], "northbound_score": northbound["score"], "margin_change_7d": margin.get("change_7d_pct"), "northbound_5d_flow": northbound.get("net_flow_5d"), "source": "margin_and_northbound", "available": True}
    elif margin.get("available"):
        return {**margin, "source": "margin_only"}
    elif northbound.get("available"):
        return {**northbound, "source": "northbound_only"}
    else:
        return {"available": False, "error": "both failed"}


def fetch_price_data(ak, symbol):
    if not ak:
        return {"available": False, "error": "akshare not installed"}
    try:
        end_date = datetime.now().strftime("%Y%m%d")
        start_date = (datetime.now() - timedelta(days=400)).strftime("%Y%m%d")
        df = ak.stock_zh_a_hist(symbol=symbol, period="daily", start_date=start_date, end_date=end_date, adjust="qfq")
        if df is None or df.empty:
            return {"available": False, "error": "empty price data"}
        prices = df["收盘"].astype(float).tolist()
        if len(prices) < 30:
            return {"available": False, "error": "insufficient data"}
        price_today = prices[-1]
        price_14d_ago = prices[-15] if len(prices) >= 15 else prices[0]
        ma_period = min(200, len(prices))
        ma_value = sum(prices[-ma_period:]) / ma_period
        deviation = (price_today - ma_value) / ma_value if ma_value > 0 else 0
        trend_score = max(0, min(100, 50 + deviation * 200))
        ret_14d = (price_today / price_14d_ago - 1) if price_14d_ago > 0 else 0
        lookback = min(252, len(prices) - 14)
        if lookback > 10:
            rolling_returns = []
            for i in range(lookback):
                if i + 14 < len(prices) and prices[i] > 0:
                    r = prices[i + 14] / prices[i] - 1
                    rolling_returns.append(r)
            if rolling_returns:
                rank = sum(1 for r in rolling_returns if r <= ret_14d) / len(rolling_returns)
                momentum_score = rank * 100
            else:
                momentum_score = 50
        else:
            momentum_score = 50
        price_score = 0.5 * trend_score + 0.5 * momentum_score
        return {"score": round(price_score, 1), "price_today": price_today, "price_14d_ago": price_14d_ago, "ma_value": round(ma_value, 2), "ma_period": ma_period, "deviation": round(deviation * 100, 2), "ret_14d": round(ret_14d * 100, 2), "available": True}
    except Exception as e:
        print(f"[WARN] Price data failed({symbol}): {e}", file=sys.stderr)
        return {"available": False, "error": str(e)}


def fetch_news_sentiment(ak):
    if not ak:
        return {"available": False, "error": "akshare not installed"}
    try:
        df = ak.index_news_sentiment_scope()
        if df is None or df.empty:
            return {"available": False, "error": "empty news sentiment data"}
        latest = df.iloc[-1]
        score_col = None
        for c in df.columns:
            if "情绪" in c or "sentiment" in c.lower() or "score" in c.lower():
                score_col = c
                break
        if not score_col:
            score_col = df.columns[-1]
        raw_score = float(latest.get(score_col, 50))
        score = max(0, min(100, raw_score))
        return {"score": round(score, 1), "raw_score": raw_score, "source": "index_news_sentiment_scope", "available": True}
    except Exception as e:
        print(f"[WARN] News sentiment failed: {e}", file=sys.stderr)
        return {"available": False, "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="AlphaMom A-Stock Data Fetcher v2")
    parser.add_argument("--config", required=True, help="Config file path")
    parser.add_argument("--output", required=True, help="Output file path")
    args = parser.parse_args()
    with open(args.config, 'r', encoding='utf-8-sig') as f:
        config = json.load(f)
    astock_assets = config.get("astock_assets", [])
    if not astock_assets:
        print("[INFO] No A-stock assets configured, skipping", file=sys.stderr)
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump({"assets": []}, f, ensure_ascii=False, indent=2)
        return
    ak = safe_akshare()
    print("[1/5] Fetching A-stock Fear & Greed...", file=sys.stderr)
    fear_greed = fetch_fear_greed(ak)
    time.sleep(1)
    print("[2/5] Fetching turnover + limit-up (search proxy)...", file=sys.stderr)
    search_interest = fetch_search_interest(ak)
    time.sleep(1)
    print("[3/5] Fetching margin + northbound (leverage proxy)...", file=sys.stderr)
    derivatives = fetch_derivatives(ak)
    time.sleep(1)
    results = []
    for asset in astock_assets:
        symbol = asset.get("symbol", "000001")
        name = asset.get("name", symbol)
        print(f"\n=== Processing {name} ({symbol}) ===", file=sys.stderr)
        print(f"[4/5] Fetching {name} price data...", file=sys.stderr)
        price_data = fetch_price_data(ak, symbol)
        time.sleep(1)
        print(f"[5/5] Fetching news sentiment...", file=sys.stderr)
        social = fetch_news_sentiment(ak)
        results.append({
            "symbol": symbol,
            "name": name,
            "weight": asset.get("weight", 1.0),
            "dimensions": {
                "fear_greed": fear_greed,
                "search_interest": search_interest,
                "derivatives": derivatives,
                "price_trend": price_data,
                "social_sentiment": social
            }
        })
    output = {"timestamp": datetime.now().isoformat(), "market": "astock", "assets": results}
    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] A-stock data saved to {args.output}", file=sys.stderr)

if __name__ == "__main__":
    main()
