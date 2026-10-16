# run_robustness_check.py
# Standalone robustness evaluation on saved models

import os
import numpy as np
import matplotlib.pyplot as plt
from stable_baselines3 import SAC, PPO

from microgrid_env import MicrogridEnv, MicrogridConfig
from data_loader import get_tou_prices
from rl_agents import create_robust_sac_agent, NoopAgent, RuleBasedAgent
from robustness_test import run_robustness_test, plot_robustness_comparison, create_robustness_summary, RobustnessConfig

def main():
    print("Running Robustness Test on Saved Models...")
    
    DATA_PATH = "electricityConsumptionAndProductioction.csv"
    try:
        from data_loader import ElectricityDataLoader
        data_loader = ElectricityDataLoader(DATA_PATH)
        data_loader.load_raw_data()
        data_loader.process_data()
        daily_profiles = data_loader.create_daily_profiles()
        best_idx = 0
        best_solar = 0
        for idx, profile in enumerate(daily_profiles):
            total_solar = profile['solar_kw'].sum()
            if total_solar > best_solar:
                best_solar = total_solar
                best_idx = idx
        profile = daily_profiles[best_idx]
        solar = profile['solar_kw'] * 5 
        load = profile['load_kw']
        print("Loaded real data profiles")
    except:
        print("Using synthetic profiles")
        np.random.seed(42)
        solar = np.maximum(0, 5 * np.sin(np.linspace(0, np.pi, 24)) + np.random.normal(0, 0.5, 24))
        load = 3 + 2 * np.sin(np.linspace(0, 2*np.pi, 24) + np.pi/4) + np.random.normal(0, 0.3, 24)
        solar = np.clip(solar, 0, 10)
        load = np.clip(load, 1, 10)
        
    prices = get_tou_prices()
    
    config = MicrogridConfig(
        e_max=13.5, e_min_ratio=0.1, p_bat_max=5.0,
        eta_charge=0.95, eta_discharge=0.95, ramp_rate=2.5,
        p_grid_peak=10.0, peak_penalty_rate=0.50,
        degradation_cost_per_kwh=0.02, forecast_horizon=12
    )
    
    env = MicrogridEnv(solar, load, prices, config=config)
    
    agents = {}
    agents['LP'] = None
    agents['NoOp'] = NoopAgent()
    agents['Rule-Based'] = RuleBasedAgent()
    
    try:
        agents['SAC'] = SAC.load("results/sac_model", env=env)
        print("Loaded SAC")
    except: print("Failed to load SAC")
        
    try:
        agents['R-SAC'] = SAC.load("results/rsac_model", env=env)
        print("Loaded R-SAC")
    except: print("Failed to load R-SAC")
        
    try:
        agents['PPO'] = PPO.load("results/ppo_model", env=env)
        print("Loaded PPO")
    except: print("Failed to load PPO")
    
    robustness_config = RobustnessConfig(
        noise_levels=[0.0, 0.05, 0.10, 0.20, 0.30],
        n_scenarios=20
    )
    
    results = run_robustness_test(
        agents=agents, solar_profile=solar, load_profile=load,
        price_profile=prices, config=robustness_config,
        env_config=config, verbose=True
    )
    
    summary = create_robustness_summary(results)
    print("\nROBUSTNESS SUMMARY")
    print(summary.to_string(index=False))
    
    fig = plot_robustness_comparison(results, save_path="results/robustness_forecast_enhanced.png")

if __name__ == "__main__":
    main()
