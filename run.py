#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AlphaMom — 宝妈反买量化指数一键运行脚本
按顺序执行抓取、计算、报告生成的端到端流水线
"""

import os
import sys
import subprocess
import argparse
import shutil

# Ensure output encoding is UTF-8
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

def run_command(cmd, step_name):
    print(f"\n[运行步骤] {step_name}...")
    print(f"执行命令: {' '.join(cmd)}")
    print("-" * 50)
    
    try:
        # Run process and let it write directly to stdout/stderr of the parent process
        result = subprocess.run(cmd)
        print("-" * 50)
        
        if result.returncode != 0:
            print(f"[错误] {step_name} 失败，退出码: {result.returncode}", file=sys.stderr)
            return False
        return True
    except FileNotFoundError:
        print(f"[错误] 未找到 Python 解释器或脚本文件，请确认当前工作目录正确。", file=sys.stderr)
        return False
    except Exception as e:
        print(f"[错误] 执行 {step_name} 时发生异常: {e}", file=sys.stderr)
        return False

def main():
    parser = argparse.ArgumentParser(description="AlphaMom 一键运行流水线")
    parser.add_argument(
        "--config", 
        default="alpha_mom_config.json", 
        help="配置文件路径 (默认: alpha_mom_config.json，不存在时自动使用 assets/config_template.json)"
    )
    parser.add_argument(
        "--mode", 
        default="review", 
        choices=["review", "signal"], 
        help="报告生成模式 (review: 今日复盘模式，适合终端阅读；signal: 简短避险信号模式)"
    )
    parser.add_argument(
        "--html", 
        help="HTML 视觉海报输出路径 (可选，如: output/report.html)"
    )
    args = parser.parse_args()

    # 1. 检查/初始化配置文件
    config_path = args.config
    if not os.path.exists(config_path):
        template_path = os.path.join("assets", "config_template.json")
        if os.path.exists(template_path):
            print(f"[提示] 未找到配置文件 '{config_path}'，正在自动从模板 '{template_path}' 复制...")
            try:
                shutil.copy(template_path, config_path)
                print(f"[OK] 已生成默认配置文件 '{config_path}'，如果需要接入 DeepSeek API，请在其中填写您的 api_key。")
            except Exception as e:
                print(f"[警告] 无法复制配置文件模板: {e}，将直接使用模板文件。")
                config_path = template_path
        else:
            print(f"[错误] 未找到任何配置文件或配置模板，请检查项目完整性。", file=sys.stderr)
            sys.exit(1)

    # 2. 创建必要的数据与输出文件夹
    os.makedirs("data", exist_ok=True)
    os.makedirs("output", exist_ok=True)

    # 3. 准备执行步骤
    python_exe = sys.executable
    
    steps = [
        {
            "name": "抓取加密货币情绪与市场数据",
            "cmd": [python_exe, os.path.join("scripts", "fetch_crypto.py"), "--config", config_path, "--output", os.path.join("data", "crypto_raw.json")]
        },
        {
            "name": "抓取 A 股情绪与市场数据",
            "cmd": [python_exe, os.path.join("scripts", "fetch_astock.py"), "--config", config_path, "--output", os.path.join("data", "astock_raw.json")]
        },
        {
            "name": "计算宝妈拥挤度指数 (MCI)",
            "cmd": [python_exe, os.path.join("scripts", "compute_mci.py"), "--crypto", os.path.join("data", "crypto_raw.json"), "--astock", os.path.join("data", "astock_raw.json"), "--output", os.path.join("data", "mci_result.json")]
        }
    ]

    # 添加报告生成步骤
    report_cmd = [
        python_exe, 
        os.path.join("scripts", "report.py"), 
        "--mci", os.path.join("data", "mci_result.json"), 
        "--config", config_path, 
        "--mode", args.mode
    ]
    if args.html:
        report_cmd.extend(["--html", args.html])
        
    steps.append({
        "name": "生成讽刺广播避险报告",
        "cmd": report_cmd
    })

    # 4. 顺序执行
    print("=" * 60)
    print("           AlphaMom 宝妈反买量化指数一键运行流水线           ")
    print("=" * 60)
    
    for i, step in enumerate(steps, 1):
        step_name_formatted = f"[{i}/{len(steps)}] {step['name']}"
        success = run_command(step['cmd'], step_name_formatted)
        if not success:
            print(f"\n[错误] 流水线在第 {i} 步中断。如果因缺少依赖模块报错，请先运行: pip install -r requirements.txt", file=sys.stderr)
            sys.exit(1)

    print("\n" + "=" * 60)
    print("[OK] 流水线全部执行完毕！")
    print("  - Web 报告数据保存在: data/web_report.json")
    if args.html:
        print(f"  - HTML 视觉海报保存在: {args.html}")
    print("\n你可以运行以下命令启动本地网页服务器查看 macOS 质感的双模仪表盘：")
    print("  python -m http.server 8000")
    print("然后在浏览器中访问: http://127.0.0.1:8000")
    print("=" * 60)

if __name__ == "__main__":
    main()
