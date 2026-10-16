# create_multipanel_plot.py
# Multi-panel comparison figure + energy balance plot

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os

from microgrid_env import MicrogridEnv, MicrogridConfig
from stable_baselines3 import SAC, PPO
from rl_agents import RuleBasedAgent, NoopAgent
from data_loader import get_tou_prices
from evaluation import run_comprehensive_evaluation
import visualization

def create_multipanel_comparison():
    print("Generating Multi-Panel Comparison + Energy Balance Plots...")
    
    from main import setup_environment
    DATA_PATH = "electricityConsumptionAndProductioction.csv"
    FALLBACK_DATA_PATH = "PecanStreet_10_Homes_1Min_Data.csv"
    
    solar_profile, load_profile, prices, config = setup_environment(DATA_PATH, FALLBACK_DATA_PATH)
    
    agents = {}
    
    if os.path.exists("results/rsac_model.zip"):
        print("Loading R-SAC...")
        env = MicrogridEnv(solar_profile, load_profile, prices, config=config)
        agents['R-SAC'] = SAC.load("results/rsac_model", env=env)
    
    if os.path.exists("results/sac_model.zip"):
        print("Loading SAC...")
        env = MicrogridEnv(solar_profile, load_profile, prices, config=config)
        agents['SAC'] = SAC.load("results/sac_model", env=env)
        
    if os.path.exists("results/ppo_model.zip"):
        print("Loading PPO...")
        env = MicrogridEnv(solar_profile, load_profile, prices, config=config)
        agents['PPO'] = PPO.load("results/ppo_model", env=env)
         
    agents['Rule-Based'] = RuleBasedAgent()
    agents['NoOp'] = NoopAgent()

    if not agents:
        print("ERROR: No agents found!")
        return
        
    print("Running evaluation for %s..." % str(list(agents.keys())))
    results = run_comprehensive_evaluation(
        agents, solar_profile, load_profile, prices, 
        n_episodes=1, config=config, verbose=True
    )
    
    # energy balance plot
    target = 'R-SAC' if 'R-SAC' in agents else 'SAC'
    print("Generating Energy Balance Plot for %s..." % target)
    visualization.plot_energy_balance(
        results, agent_name=target, episode_idx=0, 
        save_path="results/energy_balance_plot.pdf"
    )
    
    # multi-panel figure
    print("Generating Multi-Panel Comparison Plot...")
    
    fig, axes = plt.subplots(4, 1, figsize=(10, 14), sharex=True)
    hours = np.arange(24)
    
    first_agent = list(results['all_results'].keys())[0]
    ep = results['all_results'][first_agent]['episodes'][0]
    solar = ep['solar_profile']
    load = ep['load_profile']
    price = ep['price_profile']
    
    ax1 = axes[0]
    ax1.plot(hours, solar, label='PV Generation', color='#f1c40f', linewidth=2)
    ax1.plot(hours, load, label='Load Demand', color='#e74c3c', linewidth=2)
    ax1.set_ylabel('Power (kW)')
    ax1.set_title('(a) PV Generation and Load Demand', fontweight='bold', loc='left')
    ax1.legend(loc='upper right')
    ax1.grid(True, alpha=0.3)
    
    ax2 = axes[1]
    ax2.step(hours, price, where='post', label='TOU Price', color='#2c3e50', linewidth=2)
    ax2.set_ylabel('Price ($/kWh)')
    ax2.set_title('(b) Electricity Price', fontweight='bold', loc='left')
    visualization.add_background_shading(ax2, label=False)
    ax2.grid(True, alpha=0.3)

    ax3 = axes[2]
    ax3.set_ylabel('SoC (0-1)')
    ax3.set_title('(c) State of Charge Tracking', fontweight='bold', loc='left')
    
    for name, res in results['all_results'].items():
        ep = res['episodes'][0]
        soc = np.concatenate(([0.5], ep['soc_trajectory']))
        c = visualization.get_agent_color(name)
        lw = 2.5 if 'SAC' in name else 1.5
        ls = '-' if 'SAC' in name else '--'
        n_pts = min(len(soc), 25)
        ax3.plot(np.arange(n_pts), soc[:n_pts], label=name, color=c, linewidth=lw, linestyle=ls)
        
    ax3.set_ylim(0, 1.05)
    visualization.add_background_shading(ax3, label=False)
    ax3.legend(loc='upper center', bbox_to_anchor=(0.5, -0.15), ncol=3, fontsize=9)
    ax3.grid(True, alpha=0.3)
    
    ax4 = axes[3]
    ax4.set_ylabel('Grid Power (kW)')
    ax4.set_title('(d) Grid Power Exchange (+Buy / -Sell)', fontweight='bold', loc='left')
    
    for name, res in results['all_results'].items():
        ep = res['episodes'][0]
        grid = ep['grid_power']
        c = visualization.get_agent_color(name)
        lw = 2.5 if 'SAC' in name else 1.5
        al = 0.9 if 'SAC' in name else 0.6
        ax4.plot(hours, grid, label=name, color=c, linewidth=lw, alpha=al)
        
    ax4.axhline(0, color='black', linewidth=0.5)
    visualization.add_background_shading(ax4, label=False)
    ax4.grid(True, alpha=0.3)
    ax4.set_xlabel('Hour of Day')
    
    plt.tight_layout()
    plt.subplots_adjust(hspace=0.3)
    
    fig.savefig('results/thesis_comparison_plot.pdf')
    print("Saved results/thesis_comparison_plot.pdf")

if __name__ == "__main__":
    create_multipanel_comparison()
