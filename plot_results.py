# plot_results.py
# Generate thesis-grade figures for simulation results

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D

# ---- DATA (from simulation runs) ----

AGENTS = ['LP', 'SAC', 'R-SAC', 'PPO', 'Rule-Based']

DATA = {
    'mean_profit':   [-14.22, -15.16, -14.94, -15.91, -34.12],
    'std_profit':    [0.22,   0.25,   0.23,   0.22,   0.27],
    'optimality_gap':[0.0,    6.60,   5.04,   11.93,  139.97],
    'energy_profit': [-13.82, -13.88, -14.20, -14.17, -13.74], 
    'peak_penalty':  [0.0,    0.0,    0.0,    0.0,    0.0],
    'degradation':   [-0.40,  -1.28,  -0.74,  -1.74,  -20.38],
    'throughput':    [19.91,  39.32,  31.30,  34.39,  18.59],
    'final_soc':     [0.50,   0.51,   0.50,   0.48,   0.10],
}

ROBUSTNESS_DATA = {
    '0% Noise':  [-14.70, -15.09, -14.91, -15.97],
    '30% Noise': [-16.98, -17.46, -17.14, -19.55],
    'Agents':    ['LP',   'SAC',  'R-SAC', 'PPO']
}

PROFILES = {
    'solar': [0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 0.00, 1.02, 3.53, 5.53, 7.10, 7.63, 7.76, 7.70, 7.04, 5.68, 4.13, 1.01, 0.09, 0.00, 0.00, 0.00, 0.00, 0.00],
    'load': [5.95, 5.87, 5.76, 5.72, 5.85, 6.11, 6.64, 7.20, 6.95, 6.50, 5.87, 5.52, 5.28, 5.34, 5.38, 5.62, 5.84, 6.85, 7.30, 7.82, 7.72, 7.39, 6.72, 6.22],
    'price': [0.08, 0.08, 0.08, 0.08, 0.08, 0.08, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.15, 0.28, 0.28, 0.28, 0.28, 0.28, 0.28, 0.28, 0.15, 0.15, 0.15]
}


# ---- STYLE ----

def set_style():
    sns.set_style("ticks")
    sns.set_context("paper", font_scale=1.4)
    
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.sans-serif': ['Arial', 'DejaVu Sans', 'Liberation Sans'],
        'font.size': 12,
        'axes.titlesize': 16,
        'axes.labelsize': 14,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'legend.fontsize': 12,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'lines.linewidth': 2,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'grid.linestyle': '--',
        'grid.alpha': 0.6,
    })

COLORS = {
    'LP': '#2c3e50',
    'SAC': '#2980b9',
    'R-SAC': '#e67e22',
    'PPO': '#27ae60',
    'Rule-Based': '#c0392b',
    'NoOp': '#7f8c8d'
}


# ---- PLOTS ----

def plot_performance_summary():
    """Fig 1: Cost bar + optimality gap line."""
    fig, ax1 = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(AGENTS))
    w = 0.6
    
    costs = [-p for p in DATA['mean_profit']]
    errors = DATA['std_profit']
    
    bars = ax1.bar(x, costs, w, yerr=errors, capsize=5, 
                   color=[COLORS.get(a, '#333') for a in AGENTS], 
                   alpha=0.9, edgecolor='black', linewidth=1)
    
    ax1.set_ylabel('Daily Operational Cost ($)', fontweight='bold')
    ax1.set_xlabel('Agent', fontweight='bold')
    ax1.set_xticks(x)
    ax1.set_xticklabels(AGENTS)
    ax1.set_ylim(0, max(costs) * 1.2)
    
    ax2 = ax1.twinx()
    gaps = DATA['optimality_gap']
    ax2.plot(x, gaps, color='#e74c3c', marker='o', linestyle='-', linewidth=3, markersize=8)
    ax2.set_ylabel('Optimality Gap (%)', fontweight='bold', color='#e74c3c')
    ax2.tick_params(axis='y', labelcolor='#e74c3c')
    ax2.set_ylim(-5, max(gaps) * 1.1)
    
    for i, v in enumerate(gaps):
        ax2.text(i, v + 2, "%.1f%%" % v, color='#e74c3c', ha='center', fontweight='bold')
        
    plt.title('Economic Performance Summary', fontsize=16, pad=20)
    plt.tight_layout()
    plt.savefig('fig1_performance.pdf', bbox_inches='tight')
    print("Saved fig1_performance.pdf")
    plt.close()


def plot_cost_breakdown():
    """Fig 2: Stacked cost breakdown."""
    fig, ax = plt.subplots(figsize=(10, 6))
    
    x = np.arange(len(AGENTS))
    w = 0.6
    
    energy = [-v for v in DATA['energy_profit']]
    peak = [-v for v in DATA['peak_penalty']]
    deg = [-v for v in DATA['degradation']]
    
    p1 = ax.bar(x, energy, w, label='Net Energy Cost', color='#3498db', edgecolor='black', alpha=0.9)
    p2 = ax.bar(x, peak, w, bottom=energy, label='Peak Penalty', color='#e74c3c', edgecolor='black', alpha=0.9)
    bottom_deg = [e + p for e, p in zip(energy, peak)]
    p3 = ax.bar(x, deg, w, bottom=bottom_deg, label='Degradation Cost', color='#f1c40f', edgecolor='black', alpha=0.9)
    
    ax.set_ylabel('Daily Cost breakdown ($)', fontweight='bold')
    ax.set_xticks(x)
    ax.set_xticklabels(AGENTS)
    ax.legend(loc='upper left', frameon=True)
    
    plt.title('Cost Component Analysis', fontsize=16, pad=20)
    plt.tight_layout()
    plt.savefig('fig2_breakdown.pdf', bbox_inches='tight')
    print("Saved fig2_breakdown.pdf")
    plt.close()


def plot_efficiency_frontier():
    """Fig 3: Profit vs throughput scatter."""
    fig, ax = plt.subplots(figsize=(8, 6))
    
    profits = DATA['mean_profit']
    throughput = DATA['throughput']
    
    for i, agent in enumerate(AGENTS):
        color = COLORS.get(agent, 'black')
        ax.scatter(throughput[i], profits[i], s=200, color=color, edgecolor='black', alpha=0.9, zorder=3)
        offset_y = 0.5 if i % 2 == 0 else -0.5
        ax.text(throughput[i] + 0.5, profits[i] + offset_y, agent, fontsize=12, fontweight='bold', color=color)
        
    ax.set_xlabel('Battery Throughput (kWh/day)', fontweight='bold')
    ax.set_ylabel('Mean Daily Profit ($)', fontweight='bold')
    ax.grid(True, linestyle='--', alpha=0.5)
    
    plt.title('Efficiency Frontier: Profit vs. Battery Wear', fontsize=16, pad=20)
    plt.tight_layout()
    plt.savefig('fig3_efficiency.pdf', bbox_inches='tight')
    print("Saved fig3_efficiency.pdf")
    plt.close()


def plot_robustness_slope():
    """Fig 4: Slope chart 0% vs 30% noise."""
    fig, ax = plt.subplots(figsize=(8, 8))
    
    agents = ROBUSTNESS_DATA['Agents']
    p0 = ROBUSTNESS_DATA['0% Noise']
    p30 = ROBUSTNESS_DATA['30% Noise']
    
    x_pos = [0, 1]
    
    for i, agent in enumerate(agents):
        y_vals = [p0[i], p30[i]]
        color = COLORS.get(agent, 'grey')
        
        is_hl = (agent == 'R-SAC')
        lw = 4 if is_hl else 2
        alpha = 1.0 if is_hl else 0.6
        
        ax.plot(x_pos, y_vals, color=color, linewidth=lw, alpha=alpha, marker='o', markersize=8)
        ax.text(-0.05, y_vals[0], "%s: $%.2f" % (agent, y_vals[0]), ha='right', va='center', color=color, fontweight='bold')
        ax.text(1.05, y_vals[1], "$%.2f" % y_vals[1], ha='left', va='center', color=color, fontweight='bold')
        
        deg_pct = (y_vals[1] - y_vals[0]) / abs(y_vals[0]) * 100
        mid_y = (y_vals[0] + y_vals[1]) / 2
        
        if is_hl:
           ax.text(0.5, mid_y + 0.5, "%s\n%.1f%% Drop" % (agent, deg_pct), ha='center', color=color, fontweight='bold', fontsize=10, backgroundcolor='white')

    ax.set_xticks([0, 1])
    ax.set_xticklabels(['Ideal (0% Noise)', 'Stochastic (30% Noise)'], fontweight='bold')
    ax.set_ylabel('Daily Profit ($)', fontweight='bold')
    ax.set_xlim(-0.5, 1.5)
    ax.spines['left'].set_visible(False)
    ax.yaxis.grid(True)
    
    plt.title('Robustness Analysis: Performance Under Uncertainty', fontsize=16, pad=20)
    plt.tight_layout()
    plt.savefig('fig4_robustness.pdf', bbox_inches='tight')
    print("Saved fig4_robustness.pdf")
    plt.close()


def plot_system_profiles():
    """Fig 5: Solar/Load/Price dual axis."""
    fig, ax1 = plt.subplots(figsize=(12, 6))
    
    hours = np.arange(24)
    
    ax1.plot(hours, PROFILES['load'], color='#2c3e50', linewidth=2, label='Load Demand', linestyle='--')
    ax1.fill_between(hours, PROFILES['load'], color='#2c3e50', alpha=0.1)
    ax1.plot(hours, PROFILES['solar'], color='#f39c12', linewidth=2, label='Solar Generation')
    ax1.fill_between(hours, PROFILES['solar'], color='#f39c12', alpha=0.2)
    
    ax1.set_xlabel('Hour of Day', fontweight='bold')
    ax1.set_ylabel('Power (kW)', fontweight='bold', color='#2c3e50')
    ax1.set_xlim(0, 23)
    ax1.set_xticks(hours)
    ax1.tick_params(axis='y', labelcolor='#2c3e50')
    
    ax2 = ax1.twinx()
    ax2.step(hours, PROFILES['price'], where='post', color='#27ae60', linewidth=2.5, label='ToU Price', zorder=0)
    ax2.set_ylabel('Price ($/kWh)', fontweight='bold', color='#27ae60')
    ax2.tick_params(axis='y', labelcolor='#27ae60')
    ax2.set_ylim(0, max(PROFILES['price']) * 1.5)
    
    lines1, labels1 = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper center', bbox_to_anchor=(0.5, 1.15), 
               ncol=3, frameon=False, fontsize=12)
    
    plt.title('Daily Microgrid Profiles & Pricing', fontsize=16, y=1.15)
    plt.tight_layout()
    plt.savefig('fig5_profiles.pdf', bbox_inches='tight')
    print("Saved fig5_profiles.pdf")
    plt.close()


def plot_robustness_scenarios():
    """Fig 6: Forecast uncertainty envelope."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
    
    hours = np.arange(24)
    n_scenarios = 20
    noise_level = 0.30
    
    base_solar = np.array(PROFILES['solar'])
    ax1.plot(hours, base_solar, color='black', linewidth=3, label='Forecast (Baseline)', zorder=5)
    
    np.random.seed(42)
    for _ in range(n_scenarios):
        noise = np.random.normal(0, noise_level, 24)
        noisy = base_solar * (1 + noise)
        noisy = np.clip(noisy, 0, None)
        ax1.plot(hours, noisy, color='#f39c12', linewidth=1, alpha=0.3)
        
    ax1.set_title('Solar Uncertainty (30% Noise)', fontweight='bold')
    ax1.set_xlabel('Hour')
    ax1.set_ylabel('Power (kW)')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    base_load = np.array(PROFILES['load'])
    ax2.plot(hours, base_load, color='black', linewidth=3, label='Forecast (Baseline)', zorder=5)
    
    for _ in range(n_scenarios):
        noise = np.random.normal(0, noise_level, 24)
        noisy = base_load * (1 + noise)
        noisy = np.maximum(noisy, base_load * 0.5)
        ax2.plot(hours, noisy, color='#2980b9', linewidth=1, alpha=0.3)
        
    ax2.set_title('Load Uncertainty (30% Noise)', fontweight='bold')
    ax2.set_xlabel('Hour')
    ax2.set_ylabel('Power (kW)')
    ax2.legend(loc='upper right')
    ax2.grid(True, alpha=0.3)
    
    plt.suptitle('Robustness Evaluation Scenarios', fontsize=16, y=1.05)
    plt.tight_layout()
    plt.savefig('fig6_robustness_scenarios.pdf', bbox_inches='tight')
    print("Saved fig6_robustness_scenarios.pdf")
    plt.close()


def main():
    print("Generating Thesis-Grade Figures...")
    set_style()
    
    plot_performance_summary()
    plot_cost_breakdown()
    plot_efficiency_frontier()
    plot_robustness_slope()
    plot_system_profiles()
    plot_robustness_scenarios()
    
    print("\nDONE. All figures saved.")

if __name__ == "__main__":
    main()
