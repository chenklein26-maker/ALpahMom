#!/usr/bin/env python3
"""
AlphaMom — MCI 计算引擎
五维归一化 + 自适应权重 + 加权求和
"""

import argparse
import json
import os
import sys
from datetime import datetime

# ─── 权重配置 ─────────────────────────────────────────────────
DEFAULT_WEIGHTS = {
    "fear_greed": 0.20,
    "search_interest": 0.20,
    "derivatives": 0.25,
    "price_trend": 0.20,
    "social_sentiment": 0.15
}

# ─── 信号分级 ─────────────────────────────────────────────────
SIGNAL_LEVELS = [
    {"min": 0,  "max": 20,  "level": "冰封区", "icon": "🧊", "mama_status": "宝妈早已割肉离场,群里鸦雀无声",  "signal": "买入信号",  "signal_icon": "🟢"},
    {"min": 21, "max": 40,  "level": "寒冷区", "icon": "❄️", "mama_status": "宝妈偶尔提起但兴趣寥寥",          "signal": "建仓信号",  "signal_icon": "🔵"},
    {"min": 41, "max": 60,  "level": "温和区", "icon": "😐", "mama_status": "正常市场状态,宝妈无异常举动",      "signal": "持有",      "signal_icon": "⚪"},
    {"min": 61, "max": 80,  "level": "升温区", "icon": "🔥", "mama_status": "宝妈开始打听,群里有人晒单",        "signal": "止盈信号",  "signal_icon": "🟡"},
    {"min": 81, "max": 100, "level": "熔岩区", "icon": "🌋", "mama_status": "宝妈跑步进场,连你三姑都在推荐",    "signal": "卖出信号",  "signal_icon": "🔴"},
]

def get_signal_level(mci):
    """根据 MCI 获取信号等级"""
    for level in SIGNAL_LEVELS:
        if level["min"] <= mci <= level["max"]:
            return level
    return SIGNAL_LEVELS[2]  # 默认温和区

# ─── 自适应权重归一化 ─────────────────────────────────────────
def normalize_weights(dimensions):
    """维度不可用时,权重按比例重新分配"""
    available = {}
    unavailable = []
    total_weight = 0

    for dim_name, dim_data in dimensions.items():
        if dim_data.get("available", False):
            w = DEFAULT_WEIGHTS.get(dim_name, 0)
            available[dim_name] = w
            total_weight += w
        else:
            unavailable.append(dim_name)

    if total_weight == 0:
        # 全部不可用,等权
        for dim_name in dimensions:
            available[dim_name] = 1.0 / len(dimensions)
        total_weight = 1.0

    # 归一化
    normalized = {k: v / total_weight for k, v in available.items()}
    return normalized, unavailable

# ─── MCI 计算 ─────────────────────────────────────────────────
def compute_mci_for_asset(asset_data):
    """为单个标的计算 MCI"""
    dims = asset_data.get("dimensions", {})
    
    # 获取各维度分数
    dim_scores = {}
    for dim_name, dim_data in dims.items():
        if dim_data.get("available", False):
            score = dim_data.get("score", 50)
            dim_scores[dim_name] = {
                "score": score,
                "weight": DEFAULT_WEIGHTS.get(dim_name, 0),
                "available": True,
                "details": dim_data
            }
        else:
            dim_scores[dim_name] = {
                "score": None,
                "weight": DEFAULT_WEIGHTS.get(dim_name, 0),
                "available": False,
                "details": dim_data
            }

    # 自适应权重归一化
    norm_weights, unavailable = normalize_weights(dims)

    # 加权求和
    mci = 0
    for dim_name, w in norm_weights.items():
        s = dim_scores[dim_name]["score"]
        if s is not None:
            mci += w * s

    mci = round(max(0, min(100, mci)), 1)

    # 信号等级
    level = get_signal_level(mci)

    return {
        "symbol": asset_data.get("symbol", ""),
        "name": asset_data.get("name", ""),
        "weight": asset_data.get("weight", 1.0),
        "mci": mci,
        "level": level,
        "dimensions": dim_scores,
        "normalized_weights": norm_weights,
        "unavailable_dimensions": unavailable
    }

# ─── 组合 MCI ─────────────────────────────────────────────────
def compute_portfolio_mci(asset_results):
    """多标的加权组合 MCI"""
    if not asset_results:
        return None
    total_weight = sum(a["weight"] for a in asset_results)
    if total_weight == 0:
        total_weight = 1
    portfolio_mci = sum(a["mci"] * a["weight"] for a in asset_results) / total_weight
    portfolio_mci = round(portfolio_mci, 1)
    level = get_signal_level(portfolio_mci)
    return {
        "mci": portfolio_mci,
        "level": level
    }

# ─── 主流程 ───────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="AlphaMom MCI 计算引擎")
    parser.add_argument("--crypto", help="加密数据文件路径")
    parser.add_argument("--astock", help="A股数据文件路径")
    parser.add_argument("--output", required=True, help="输出文件路径")
    args = parser.parse_args()

    all_assets = []

    # 读取加密数据
    if args.crypto and os.path.exists(args.crypto):
        with open(args.crypto, 'r', encoding='utf-8') as f:
            crypto_data = json.load(f)
        for asset in crypto_data.get("assets", []):
            result = compute_mci_for_asset(asset)
            result["market"] = "crypto"
            all_assets.append(result)

    # 读取A股数据
    if args.astock and os.path.exists(args.astock):
        with open(args.astock, 'r', encoding='utf-8') as f:
            astock_data = json.load(f)
        for asset in astock_data.get("assets", []):
            result = compute_mci_for_asset(asset)
            result["market"] = "astock"
            all_assets.append(result)

    if not all_assets:
        print("[ERROR] 无可用数据", file=sys.stderr)
        sys.exit(1)

    # 组合 MCI
    portfolio = compute_portfolio_mci(all_assets)

    output = {
        "timestamp": datetime.now().isoformat(),
        "assets": all_assets,
        "portfolio": portfolio
    }

    os.makedirs(os.path.dirname(args.output), exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    print(f"[OK] MCI 计算完成,结果已保存到 {args.output}", file=sys.stderr)

    # 终端摘要
    print("\n" + "=" * 50, file=sys.stderr)
    if portfolio:
        print(f"组合 MCI: {portfolio['mci']}% {portfolio['level']['icon']} {portfolio['level']['level']}", file=sys.stderr)
    for a in all_assets:
        print(f"  {a['name']:12s}  MCI={a['mci']:5.1f}%  {a['level']['icon']} {a['level']['signal']}", file=sys.stderr)
    print("=" * 50, file=sys.stderr)

if __name__ == "__main__":
    main()
