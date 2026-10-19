# export_web_data.py
# Exports evaluation curves and metrics from results into dashboard_data.json
# and wires it directly into dashboard.html.

import os
import re
import json
import zlib
from pathlib import Path

def extract_pdf_streams(pdf_path):
    with open(pdf_path, 'rb') as f:
        data = f.read()
    streams = re.findall(rb'stream[\r\n]+(.*?)[\r\n]+endstream', data, re.DOTALL)
    decomp = zlib.decompress(streams[0]).decode('latin1')
    return decomp

def parse_all_results(results_dir='results_new'):
    res_path = Path(results_dir)
    if not res_path.exists():
        res_path = Path('results')

    print(f"Loading results from {res_path}...")

    # 1. Profiles (11_profiles.pdf)
    prof_decomp = extract_pdf_streams(res_path / '11_profiles.pdf')
    prof_matches = re.findall(r'([0-9\.]+\s+[0-9\.]+\s+[0-9\.]+\s+RG[\s\S]*?S\b)', prof_decomp)
    y_zero = 402.718438
    y_step = 24.34365

    pts_load = re.findall(r'([0-9\.]+)\s+([0-9\.]+)\s+[ml]', prof_matches[1])
    load_profile = [round((float(y) - y_zero) / y_step, 3) for _, y in pts_load]

    pts_net = re.findall(r'([0-9\.]+)\s+([0-9\.]+)\s+[ml]', prof_matches[2])
    net_profile = [round((float(y) - y_zero) / y_step, 3) for _, y in pts_net]

    solar_profile = [round(max(0.0, l - n), 3) for l, n in zip(load_profile, net_profile)]

    # TOU Prices
    prices = []
    for h in range(24):
        if 0 <= h < 6:
            prices.append(0.08)
        elif 6 <= h < 14 or 21 <= h <= 23:
            prices.append(0.15)
        else: # 14 to 20
            prices.append(0.28)

    # 2. SOC (01_soc_comparison.pdf)
    soc_decomp = extract_pdf_streams(res_path / '01_soc_comparison.pdf')
    soc_matches = re.findall(r'([0-9\.]+\s+[0-9\.]+\s+[0-9\.]+\s+RG[\s\S]*?S\b)', soc_decomp)
    y0_soc, y1_soc = 101.225475, 390.249475

    def parse_soc_block(match_block, skip=0):
        pts = re.findall(r'([0-9\.]+)\s+([0-9\.]+)\s+[ml]', match_block)[skip:]
        vals = [round(max(0.1, min(1.0, (float(y) - y0_soc) / (y1_soc - y0_soc) * 1.1)), 3) for _, y in pts]
        # Return 24 hourly steps (after initial soc=0.5)
        if len(vals) == 25:
            return vals[1:]
        return vals[:24]

    lp_soc = parse_soc_block(soc_matches[0], skip=8)
    sac_soc = parse_soc_block(soc_matches[1])
    rsac_soc = parse_soc_block(soc_matches[2])
    ppo_soc = parse_soc_block(soc_matches[3])
    noop_soc = parse_soc_block(soc_matches[4])
    rule_soc = parse_soc_block(soc_matches[5])

    # 3. Battery Power (06_battery_power.pdf)
    bat_decomp = extract_pdf_streams(res_path / '06_battery_power.pdf')
    bat_matches = re.findall(r'([0-9\.]+\s+[0-9\.]+\s+[0-9\.]+\s+RG[\s\S]*?S\b)', bat_decomp)
    y_zero_bat = 213.418125
    scale_bat = 33.0709

    def parse_bat_block(match_block, skip=0):
        pts = re.findall(r'([0-9\.]+)\s+([0-9\.]+)\s+[ml]', match_block)[skip:]
        return [round((float(y) - y_zero_bat) / scale_bat, 3) for _, y in pts][:24]

    lp_bat = parse_bat_block(bat_matches[0], skip=8)
    sac_bat = parse_bat_block(bat_matches[1])
    rsac_bat = parse_bat_block(bat_matches[2])
    ppo_bat = parse_bat_block(bat_matches[3])
    noop_bat = [0.0] * 24
    rule_bat = parse_bat_block(bat_matches[5])

    # 4. Net Grid Power (05_net_grid_power.pdf)
    grid_decomp = extract_pdf_streams(res_path / '05_net_grid_power.pdf')
    grid_matches = re.findall(r'([0-9\.]+\s+[0-9\.]+\s+[0-9\.]+\s+RG[\s\S]*?S\b)', grid_decomp)
    y_zero_grid = 224.524228
    scale_grid = 23.0415

    def parse_grid_block(match_block, skip=0):
        pts = re.findall(r'([0-9\.]+)\s+([0-9\.]+)\s+[ml]', match_block)[skip:]
        return [round((float(y) - y_zero_grid) / scale_grid, 3) for _, y in pts][:24]

    lp_grid = parse_grid_block(grid_matches[0], skip=8)
    sac_grid = parse_grid_block(grid_matches[1])
    rsac_grid = parse_grid_block(grid_matches[2])
    ppo_grid = parse_grid_block(grid_matches[3])
    noop_grid = parse_grid_block(grid_matches[4])
    rule_grid = parse_grid_block(grid_matches[5])

    # 5. Cumulative Profit (02_cumulative_profit.pdf)
    profit_decomp = extract_pdf_streams(res_path / '02_cumulative_profit.pdf')
    profit_matches = re.findall(r'([0-9\.]+\s+[0-9\.]+\s+[0-9\.]+\s+RG[\s\S]*?S\b)', profit_decomp)
    y_zero_profit = 390.909373
    scale_profit = 81.57878

    def parse_profit_block(match_block, skip=0):
        pts = re.findall(r'([0-9\.]+)\s+([0-9\.]+)\s+[ml]', match_block)[skip:]
        return [round((float(y) - y_zero_profit) / scale_profit, 3) for _, y in pts][:24]

    lp_cum_prof = parse_profit_block(profit_matches[0], skip=8)
    sac_cum_prof = parse_profit_block(profit_matches[1])
    rsac_cum_prof = parse_profit_block(profit_matches[2])
    ppo_cum_prof = parse_profit_block(profit_matches[3])
    noop_cum_prof = parse_profit_block(profit_matches[4])
    rule_cum_prof = parse_profit_block(profit_matches[5])

    # Build Agent Map
    # Real 100-episode Evaluation Summary Metrics (from 12_summary_table.pdf)
    metrics = {
        'LP': {
            'meanProfit': -1.94, 'stdProfit': 0.17, 'gapVsLp': 0.0,
            'energyProfit': -1.78, 'peakPenalty': 0.00, 'throughput': 8.17,
            'finalSoc': 50.0, 'evalTime': 0.24, 'rank': 1
        },
        'R-SAC': {
            'meanProfit': -2.35, 'stdProfit': 0.25, 'gapVsLp': 20.6,
            'energyProfit': -2.02, 'peakPenalty': 0.00, 'throughput': 15.68,
            'finalSoc': 50.0, 'evalTime': 2.31, 'rank': 2
        },
        'SAC': {
            'meanProfit': -2.59, 'stdProfit': 0.22, 'gapVsLp': 33.1,
            'energyProfit': -2.22, 'peakPenalty': 0.00, 'throughput': 16.61,
            'finalSoc': 49.9, 'evalTime': 2.00, 'rank': 3
        },
        'PPO': {
            'meanProfit': -5.11, 'stdProfit': 0.14, 'gapVsLp': 164.8,
            'energyProfit': -2.97, 'peakPenalty': 0.00, 'throughput': 25.52,
            'finalSoc': 48.0, 'evalTime': 2.01, 'rank': 4
        },
        'NoOp': {
            'meanProfit': -10.78, 'stdProfit': 4.37, 'gapVsLp': 460.4,
            'energyProfit': -3.20, 'peakPenalty': 0.00, 'throughput': 0.00,
            'finalSoc': 50.0, 'evalTime': 0.34, 'rank': 5
        },
        'Rule-Based': {
            'meanProfit': -21.94, 'stdProfit': 0.29, 'gapVsLp': 1036.6,
            'energyProfit': -1.57, 'peakPenalty': 0.00, 'throughput': 18.61,
            'finalSoc': 10.0, 'evalTime': 0.35, 'rank': 6
        }
    }

    agent_data = {
        'LP': {'soc': lp_soc, 'bat': lp_bat, 'grid': lp_grid, 'cumProfit': lp_cum_prof},
        'R-SAC': {'soc': rsac_soc, 'bat': rsac_bat, 'grid': rsac_grid, 'cumProfit': rsac_cum_prof},
        'SAC': {'soc': sac_soc, 'bat': sac_bat, 'grid': sac_grid, 'cumProfit': sac_cum_prof},
        'PPO': {'soc': ppo_soc, 'bat': ppo_bat, 'grid': ppo_grid, 'cumProfit': ppo_cum_prof},
        'NoOp': {'soc': noop_soc, 'bat': noop_bat, 'grid': noop_grid, 'cumProfit': noop_cum_prof},
        'Rule-Based': {'soc': rule_soc, 'bat': rule_bat, 'grid': rule_grid, 'cumProfit': rule_cum_prof}
    }

    # Derive hourly costs and attach metrics
    for name, d in agent_data.items():
        cum = d['cumProfit']
        # Cost is negative profit
        cumCost = [-round(v, 3) for v in cum]
        cost = []
        prev = 0.0
        for c in cumCost:
            cost.append(round(c - prev, 3))
            prev = c
        d['cost'] = cost
        d['cumCost'] = cumCost
        d['totalCost'] = cumCost[-1] if cumCost else 0.0
        d.update(metrics[name])

    dataset = {
        'hours': list(range(24)),
        'labels': [f"{h:02d}:00" for h in range(24)],
        'solar': solar_profile,
        'load': load_profile,
        'prices': prices,
        'agents': agent_data,
        'summary': metrics
    }

    out_file = Path('results') / 'dashboard_data.json'
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, 'w') as f:
        json.dump(dataset, f, indent=2)
    print(f"[OK] Saved dashboard dataset to {out_file}")

    return dataset

if __name__ == '__main__':
    parse_all_results('results_new')
    from build_dashboard import build_dashboard
    build_dashboard()
