# visualization.py
# Generate plots for the microgrid simulation results (12 + 1 plots)

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import pandas as pd
import os


# plot style
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams.update({
    'figure.figsize': (12, 8),
    'font.size': 11,
    'axes.titlesize': 14,
    'axes.labelsize': 12,
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'legend.fontsize': 10,
    'figure.dpi': 100
})

# agent colors
AGENT_COLORS = {
    'LP': '#2ecc71',
    'SAC': '#3498db',
    'R-SAC': '#9b59b6',
    'PPO': '#e74c3c',
    'NoOp': '#95a5a6',
    'Rule-Based': '#f39c12'
}


def get_agent_color(name):
    return AGENT_COLORS.get(name, '#333333')


def add_background_shading(ax, label=True):
    """Add TOU pricing period shading."""
    ax.axvspan(0, 6, alpha=0.1, color='green',
               label='Off-Peak Price' if label else None)
    ax.axvspan(14, 21, alpha=0.1, color='red',
               label='Peak Price (High Cost)' if label else None)
    ax.grid(True, linestyle='--', alpha=0.3)


def plot_soc_comparison(evaluation_results, episode_idx=0, save_path=None):
    """Plot 1: SOC trajectory comparison."""
    fig, ax = plt.subplots(figsize=(14, 6))
    add_background_shading(ax)
    
    all_results = evaluation_results['all_results']
    
    for name, res in all_results.items():
        eps = res['episodes']
        if episode_idx < len(eps):
            soc = eps[episode_idx]['soc_trajectory']
            soc = np.concatenate(([0.5], soc))
            hours = np.arange(len(soc))
            
            c = get_agent_color(name)
            lw = 3 if 'R-SAC' in name else 2
            ax.plot(hours, soc, label=name, color=c, linewidth=lw, marker='o', markersize=4)
    
    ax.axhline(y=0.1, color='black', linestyle='--', alpha=0.8, label='Min SOC (10%)')
    ax.axhline(y=1.0, color='black', linestyle=':', alpha=0.5)
    
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('State of Charge (SOC)')
    ax.set_title('Battery State of Charge Comparison', fontweight='bold')
    ax.set_xlim(0, 23)
    ax.set_ylim(0, 1.1)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=4, frameon=True)
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def plot_cumulative_profit(evaluation_results, episode_idx=0, save_path=None):
    """Plot 2: Cumulative profit over time."""
    fig, ax = plt.subplots(figsize=(14, 6))
    add_background_shading(ax, label=False)
    
    hours = np.arange(24)
    all_results = evaluation_results['all_results']
    
    for name, res in all_results.items():
        eps = res['episodes']
        if episode_idx < len(eps):
            cum_cost = eps[episode_idx]['cumulative_cost']
            cum_profit = -np.array(cum_cost)
            c = get_agent_color(name)
            lw = 3 if 'R-SAC' in name else 2
            ax.plot(hours, cum_profit, label=name, color=c, linewidth=lw, marker='s', markersize=4)
            
            final = cum_profit[-1]
            ax.text(23.2, final, "$%.2f" % final, color=c, va='center', fontweight='bold')
    
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Cumulative Profit ($)')
    ax.set_title('Cumulative Daily Profit Comparison', fontweight='bold')
    ax.set_xlim(0, 24.5)
    ax.legend(loc='upper left', frameon=True)
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def plot_total_profit_bar(evaluation_results, save_path=None):
    """Plot 3: Total profit bar chart with error bars."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    all_results = evaluation_results['all_results']
    names = list(all_results.keys())
    means = [all_results[n]['mean_profit'] for n in names]
    stds = [all_results[n]['std_profit'] for n in names]
    colors = [get_agent_color(n) for n in names]
    
    bars = ax.bar(names, means, yerr=stds, capsize=10,
                  color=colors, alpha=0.8, edgecolor='black', linewidth=1)
    
    for bar in bars:
        h = bar.get_height()
        ax.annotate('$%.2f' % h,
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3 if h >= 0 else -3),
                    textcoords="offset points",
                    ha='center', va='bottom' if h >= 0 else 'top',
                    fontweight='bold')
    
    ax.set_ylabel('Total Profit ($)')
    ax.set_title('Average Daily Total Profit Comparison', fontweight='bold')
    ax.axhline(y=0, color='black', linewidth=1)
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def plot_profit_breakdown(evaluation_results, save_path=None):
    """Plot 4: Profit component breakdown."""
    fig, ax = plt.subplots(figsize=(14, 6))
    
    all_results = evaluation_results['all_results']
    names = list(all_results.keys())
    
    energy_profits = []
    peak_pens = []
    deg_costs = []
    
    for n in names:
        eps = all_results[n]['episodes']
        energy_profits.append(np.mean([-e['energy_cost'] for e in eps]))
        peak_pens.append(np.mean([e['peak_penalty'] for e in eps]))
        deg_costs.append(np.mean([e['degradation_cost'] for e in eps]))
        
    x = np.arange(len(names))
    w = 0.25
    
    ax.bar(x - w, energy_profits, w, label='Energy Arbitrage Profit', color='#27ae60')
    ax.bar(x, [-p for p in peak_pens], w, label='Peak Demand Penalty', color='#e74c3c')
    ax.bar(x + w, [-d for d in deg_costs], w, label='Degradation Cost', color='#f39c12')
    
    ax.set_ylabel('Value ($)')
    ax.set_title('Profit Composition Breakdown', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(names)
    ax.axhline(y=0, color='black', linewidth=1)
    ax.legend(loc='upper right')
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    all_vals = energy_profits + [-p for p in peak_pens] + [-d for d in deg_costs]
    if all_vals:
        mn = min(all_vals)
        mx = max(all_vals)
        rng = mx - mn if mx != mn else 1.0
        ax.set_ylim(top=max(mx, 0) + 0.2 * rng)
    
    for i, n in enumerate(names):
        net = energy_profits[i] - peak_pens[i] - deg_costs[i]
        base_h = max(energy_profits[i], 0)
        ax.annotate("Net: $%.2f" % net,
                    xy=(i, base_h), xytext=(0, 5),
                    textcoords="offset points",
                    ha='center', va='bottom', fontweight='bold', fontsize=9)

    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def plot_net_grid_power(evaluation_results, episode_idx=0, save_path=None):
    """Plot 5: Net grid power profile."""
    fig, ax = plt.subplots(figsize=(14, 6))
    add_background_shading(ax, label=False)
    
    hours = np.arange(24)
    all_results = evaluation_results['all_results']
    
    for name, res in all_results.items():
        eps = res['episodes']
        if episode_idx < len(eps):
            gp = eps[episode_idx]['grid_power']
            c = get_agent_color(name)
            if name == 'R-SAC':
                ax.fill_between(hours, gp, 0, color=c, alpha=0.2)
                ax.plot(hours, gp, label=name, color=c, linewidth=3)
            else:
                ax.plot(hours, gp, label=name, color=c, linewidth=1.5, alpha=0.8)
    
    ax.axhline(y=0, color='black', linestyle='-', linewidth=2)
    
    ylim = ax.get_ylim()
    ax.text(1, ylim[1]*0.9, "BUYING FROM GRID", color='red', fontsize=12, fontweight='bold', alpha=0.3)
    ax.text(1, ylim[0]*0.9, "SELLING TO GRID", color='green', fontsize=12, fontweight='bold', alpha=0.3)

    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Net Grid Power (kW)')
    ax.set_title('Net Grid Power Profile', fontweight='bold')
    ax.set_xlim(0, 23)
    ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=4)
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def plot_battery_power(evaluation_results, episode_idx=0, save_path=None):
    """Plot 6: Battery charge/discharge power."""
    fig, ax = plt.subplots(figsize=(14, 6))
    add_background_shading(ax, label=False)
    
    hours = np.arange(24)
    all_results = evaluation_results['all_results']
    
    for name, res in all_results.items():
        eps = res['episodes']
        if episode_idx < len(eps):
            bp = eps[episode_idx]['battery_power']
            c = get_agent_color(name)
            if name == 'R-SAC':
                ax.plot(hours, bp, label=name, color=c, linewidth=3)
            else:
                ax.plot(hours, bp, label=name, color=c, linewidth=1.5, alpha=0.7)
    
    ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
    
    ylim = ax.get_ylim()
    ax.text(1, ylim[1]*0.8, "CHARGING", color='blue', fontsize=10, fontweight='bold', alpha=0.3)
    ax.text(1, ylim[0]*0.8, "DISCHARGING", color='purple', fontsize=10, fontweight='bold', alpha=0.3)
    
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Battery Power (kW)')
    ax.set_title('Battery Power Profile', fontweight='bold')
    ax.set_xlim(0, 23)
    ax.legend(loc='upper right')
    ax.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def plot_ramping_analysis(evaluation_results, episode_idx=0, save_path=None):
    """Plot 7: Battery power ramp rates."""
    fig, ax = plt.subplots(figsize=(14, 6))
    add_background_shading(ax, label=False)
    
    hours = np.arange(1, 24)
    all_results = evaluation_results['all_results']
    
    for name, res in all_results.items():
        eps = res['episodes']
        if episode_idx < len(eps):
            bp = eps[episode_idx]['battery_power']
            ramp = np.diff(bp)
            c = get_agent_color(name)
            ax.plot(hours, ramp, label=name, color=c, linewidth=1.5, marker='.')
            
    ax.axhline(y=2.5, color='red', linestyle='--', label='Max Ramp Up')
    ax.axhline(y=-2.5, color='red', linestyle='--', label='Max Ramp Down')
    ax.axhline(y=0, color='black', alpha=0.5)
    
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Power Change (kW/hour)')
    ax.set_title('Battery Power Ramp Rates', fontweight='bold')
    ax.set_xlim(1, 23)
    ax.legend(loc='upper right')
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def plot_pricing_strategy(evaluation_results, episode_idx=0, save_path=None):
    """Plot 8: Price profile + grid purchase strategy."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), sharex=True)
    
    hours = np.arange(24)
    prices = evaluation_results['price_profile']
    all_results = evaluation_results['all_results']
    
    ax1.fill_between(hours, 0, prices, alpha=0.3, color='gold')
    ax1.plot(hours, prices, color='orange', linewidth=2, marker='o', label='Electricity Price')
    ax1.set_ylabel('Price ($/kWh)')
    ax1.set_title('Electricity Price and Grid Purchase Strategy', fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.axvspan(0, 6, alpha=0.1, color='green', label='Off-Peak')
    ax1.axvspan(14, 21, alpha=0.1, color='red', label='On-Peak')
    
    for name, res in all_results.items():
        eps = res['episodes']
        if episode_idx < len(eps):
            gp = eps[episode_idx]['grid_power']
            buy = np.maximum(gp, 0)
            c = get_agent_color(name)
            offset = list(all_results.keys()).index(name) * 0.15 - 0.3
            ax2.bar(hours + offset, buy, width=0.15, label=name, color=c, alpha=0.7)
    
    ax2.set_xlabel('Hour of Day')
    ax2.set_ylabel('Grid Purchase (kW)')
    ax2.legend(loc='upper right', ncol=2)
    ax2.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def plot_multi_episode_gap(evaluation_results, save_path=None):
    """Plot 9: Gap vs LP across episodes."""
    fig, ax = plt.subplots(figsize=(12, 6))
    
    all_results = evaluation_results['all_results']
    n_ep = evaluation_results['n_episodes']
    ep_nums = np.arange(1, n_ep + 1)
    
    for name, res in all_results.items():
        if name == 'LP':
            continue
        if 'gaps' in res:
            c = get_agent_color(name)
            ax.plot(ep_nums, res['gaps'], label=name, color=c, linewidth=2, marker='o')
    
    ax.axhline(y=0, color='green', linestyle='--', alpha=0.7, label='LP Optimum')
    ax.set_xlabel('Episode')
    ax.set_ylabel('Gap vs LP (%)')
    ax.set_title('Optimality Gap vs LP Benchmark Across Episodes', fontweight='bold')
    ax.legend(loc='upper right')
    ax.set_xlim(0.5, n_ep + 0.5)
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def plot_efficiency_metrics(evaluation_results, save_path=None):
    """Plot 10: Throughput, SOC deviation, peak violations."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    
    all_results = evaluation_results['all_results']
    names = list(all_results.keys())
    colors = [get_agent_color(n) for n in names]
    
    # throughput
    tp = []
    for res in all_results.values():
        tp.append(np.mean([e['throughput'] for e in res['episodes']]))
    axes[0].bar(names, tp, color=colors, edgecolor='black')
    axes[0].set_ylabel('Energy Throughput (kWh)')
    axes[0].set_title('Battery Throughput', fontweight='bold')
    axes[0].tick_params(axis='x', rotation=45)
    
    # SOC deviation
    soc_dev = []
    for res in all_results.values():
        devs = []
        for e in res['episodes']:
            init = e.get('initial_soc', 0.5)
            devs.append(abs(e['final_soc'] - init))
        soc_dev.append(np.mean(devs))
    axes[1].bar(names, soc_dev, color=colors, edgecolor='black')
    axes[1].set_ylabel('SOC Deviation')
    axes[1].set_title('SOC Deviation (|Final - Initial|)', fontweight='bold')
    axes[1].tick_params(axis='x', rotation=45)
    
    # peak violations
    pv = []
    for res in all_results.values():
        pv.append(np.mean([e['peak_violations'] for e in res['episodes']]))
    axes[2].bar(names, pv, color=colors, edgecolor='black')
    axes[2].set_ylabel('Peak Violations')
    axes[2].set_title('Average Peak Violations', fontweight='bold')
    axes[2].tick_params(axis='x', rotation=45)
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def plot_profiles(evaluation_results, save_path=None):
    """Plot 11: Solar, Load, Price profiles."""
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 8), sharex=True)
    
    hours = np.arange(24)
    solar = evaluation_results['solar_profile']
    load = evaluation_results['load_profile']
    price = evaluation_results['price_profile']
    
    ax1.fill_between(hours, 0, solar, alpha=0.5, color='gold', label='Solar Generation')
    ax1.plot(hours, solar, color='orange', linewidth=2)
    ax1.plot(hours, load, color='red', linewidth=2, label='Load Consumption')
    ax1.fill_between(hours, 0, load, alpha=0.3, color='red')
    
    net = load - solar
    ax1.plot(hours, net, color='purple', linewidth=2, linestyle='--', label='Net Load')
    
    ax1.set_ylabel('Power (kW)')
    ax1.set_title('Solar Generation and Load Profiles', fontweight='bold')
    ax1.legend(loc='upper right')
    ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
    
    ax2.fill_between(hours, 0, price, alpha=0.3, color='green')
    ax2.step(hours, price, where='mid', color='darkgreen', linewidth=2, label='TOU Price')
    ax2.set_xlabel('Hour of Day')
    ax2.set_ylabel('Price ($/kWh)')
    ax2.set_title('Time-of-Use Electricity Price', fontweight='bold')
    ax2.legend(loc='upper right')
    ax2.set_xticks(range(0, 24, 2))
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def plot_summary_table(evaluation_results, save_path=None):
    """Plot 12: Summary table as image."""
    from evaluation import create_summary_table
    
    df = create_summary_table(evaluation_results)
    
    fig, ax = plt.subplots(figsize=(14, 4))
    ax.axis('off')
    
    df_disp = df.copy()
    df_disp['Mean Profit ($)'] = df_disp['Mean Profit ($)'].apply(lambda x: '$%.2f' % x)
    df_disp['Std Profit ($)'] = df_disp['Std Profit ($)'].apply(lambda x: '$%.2f' % x)
    df_disp['Gap vs LP (%)'] = df_disp['Gap vs LP (%)'].apply(lambda x: '%.1f%%' % x)
    df_disp['Gap Std (%)'] = df_disp['Gap Std (%)'].apply(lambda x: '%.1f%%' % x)
    df_disp['Mean Energy Profit ($)'] = df_disp['Mean Energy Profit ($)'].apply(lambda x: '$%.2f' % x)
    df_disp['Mean Peak Penalty ($)'] = df_disp['Mean Peak Penalty ($)'].apply(lambda x: '$%.2f' % x)
    df_disp['Mean Throughput (kWh)'] = df_disp['Mean Throughput (kWh)'].apply(lambda x: '%.2f' % x)
    df_disp['Mean Final SOC'] = df_disp['Mean Final SOC'].apply(lambda x: '%.1f%%' % (x*100))
    df_disp['Eval Time (s)'] = df_disp['Eval Time (s)'].apply(lambda x: '%.2f' % x)
    
    table = ax.table(
        cellText=df_disp.values,
        colLabels=df_disp.columns,
        cellLoc='center',
        loc='center',
        colColours=['#4a90d9'] * len(df_disp.columns)
    )
    
    table.auto_set_font_size(False)
    table.set_fontsize(9)
    table.scale(1.2, 1.5)
    
    for i in range(len(df_disp.columns)):
        table[(0, i)].set_text_props(weight='bold', color='white')
    
    ax.set_title('Evaluation Summary', fontsize=14, fontweight='bold', pad=20)
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def plot_energy_balance(evaluation_results, agent_name='SAC', episode_idx=0, save_path=None):
    """Plot 13: Energy balance / self-consumption analysis."""
    import matplotlib.colors as mcolors
    
    fig, ax = plt.subplots(figsize=(14, 7))
    
    if agent_name not in evaluation_results['all_results']:
        print("Agent %s not found" % agent_name)
        return fig
        
    ep = evaluation_results['all_results'][agent_name]['episodes'][episode_idx]
    
    solar = evaluation_results['solar_profile']
    load = evaluation_results['load_profile']
    hours = np.arange(24)
    
    grid_power = ep['grid_power']
    bat_power = ep['battery_power']
    
    grid_import = np.maximum(grid_power, 0)
    bat_discharge = np.maximum(-bat_power, 0)
    direct_solar = np.maximum(load - grid_import - bat_discharge, 0)
    
    grid_export = np.maximum(-grid_power, 0)
    bat_charge = np.maximum(bat_power, 0)
    
    ax.plot(hours, load, color='black', linewidth=2.5, linestyle='-', label='Load Demand', zorder=10)
    ax.plot(hours, solar, color='black', linewidth=2.5, linestyle='--', label='PV Generation', zorder=10)
    
    # load side stack
    ax.fill_between(hours, 0, direct_solar, color='#2980b9', alpha=0.9, label='Direct Solar Usage')
    
    layer2 = direct_solar + bat_discharge
    ax.fill_between(hours, direct_solar, layer2, color='#8e44ad', alpha=0.8, label='Battery Discharging')
    
    layer3 = layer2 + grid_import
    ax.fill_between(hours, layer2, layer3, color='#c0392b', alpha=0.8, label='Grid Import')
    
    # solar side stack
    layer2s = direct_solar + bat_charge
    ax.fill_between(hours, direct_solar, layer2s, color='#9b59b6', alpha=0.6, label='Battery Charging')
    
    layer3s = layer2s + grid_export
    ax.fill_between(hours, layer2s, layer3s, color='#27ae60', alpha=0.8, label='Grid Export')
    
    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Power (kW)')
    ax.set_title('Energy Balance Analysis - %s Agent' % agent_name, fontweight='bold', fontsize=14)
    ax.set_xlim(0, 23)
    ax.set_ylim(0, max(np.max(load), np.max(solar)) * 1.2)
    
    add_background_shading(ax, label=False)
    ax.legend(loc='upper right', ncol=2, frameon=True, fancybox=True, shadow=True)
    
    plt.tight_layout()
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    return fig


def generate_all_plots(evaluation_results, output_dir="results", episode_idx=0):
    """Generate all 12 plots."""
    os.makedirs(output_dir, exist_ok=True)
    
    print("\n" + "="*60)
    print("Generating Visualization Plots...")
    print("="*60)
    
    figures = []
    
    fig1 = plot_soc_comparison(evaluation_results, episode_idx,
                                "%s/01_soc_comparison.pdf" % output_dir)
    figures.append(fig1)
    
    fig2 = plot_cumulative_profit(evaluation_results, episode_idx,
                                  "%s/02_cumulative_profit.pdf" % output_dir)
    figures.append(fig2)
    
    fig3 = plot_total_profit_bar(evaluation_results,
                                 "%s/03_total_profit_bar.pdf" % output_dir)
    figures.append(fig3)
    
    fig4 = plot_profit_breakdown(evaluation_results,
                                 "%s/04_profit_breakdown.pdf" % output_dir)
    figures.append(fig4)
    
    fig5 = plot_net_grid_power(evaluation_results, episode_idx,
                                "%s/05_net_grid_power.pdf" % output_dir)
    figures.append(fig5)
    
    fig6 = plot_battery_power(evaluation_results, episode_idx,
                               "%s/06_battery_power.pdf" % output_dir)
    figures.append(fig6)
    
    fig7 = plot_ramping_analysis(evaluation_results, episode_idx,
                                  "%s/07_ramping_analysis.pdf" % output_dir)
    figures.append(fig7)
    
    fig8 = plot_pricing_strategy(evaluation_results, episode_idx,
                                  "%s/08_pricing_strategy.pdf" % output_dir)
    figures.append(fig8)
    
    fig9 = plot_multi_episode_gap(evaluation_results,
                                   "%s/09_multi_episode_gap.pdf" % output_dir)
    figures.append(fig9)
    
    fig10 = plot_efficiency_metrics(evaluation_results,
                                     "%s/10_efficiency_metrics.pdf" % output_dir)
    figures.append(fig10)
    
    fig11 = plot_profiles(evaluation_results,
                          "%s/11_profiles.pdf" % output_dir)
    figures.append(fig11)
    
    fig12 = plot_summary_table(evaluation_results,
                                "%s/12_summary_table.pdf" % output_dir)
    figures.append(fig12)
    
    print("\n[OK] Generated %d plots in %s/" % (len(figures), output_dir))
    return figures


if __name__ == "__main__":
    from data_loader import get_tou_prices
    
    np.random.seed(42)
    
    solar = np.maximum(0, 5 * np.sin(np.linspace(0, np.pi, 24)))
    load = 3 + 2 * np.sin(np.linspace(0, 2*np.pi, 24) + np.pi/4)
    prices = get_tou_prices()
    
    # print test data
    print("Test data created. Run main.py for full visualization.")
