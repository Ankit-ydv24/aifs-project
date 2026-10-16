# main.py - Microgrid Energy Management System
# Complete simulation pipeline: train RL agents, run LP benchmark, compare

import os
import sys
import numpy as np
import pandas as pd
from pathlib import Path
import warnings
import time

warnings.filterwarnings('ignore')
os.environ['TF_CPP_MIN_LOG_LEVEL'] = '3'

from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize

from data_loader import PecanStreetDataLoader, ElectricityDataLoader, get_tou_prices
from microgrid_env import MicrogridEnv, MicrogridConfig, DynamicMicrogridEnv
from rl_agents import (
    create_sac_agent, create_ppo_agent, create_robust_sac_agent,
    train_agent, save_agent, evaluate_agent,
    NoopAgent, RuleBasedAgent, TrainingCallback
)
from lp_solver import solve_lp_benchmark, LPConfig
from evaluation import run_comprehensive_evaluation, create_summary_table, save_evaluation_results
from visualization import generate_all_plots
from robustness_test import run_robustness_test, plot_robustness_comparison, save_robustness_results, create_robustness_summary, RobustnessConfig

import matplotlib.pyplot as plt


def print_header(text):
    print("\n" + "="*70)
    print("  %s" % text)
    print("="*70 + "\n")


def setup_environment(data_path, fallback_path):
    """Setup microgrid environment and load data."""
    print_header("Setting Up Environment")
    
    daily_profiles = None
    
    # try loading electricity consumption/production data first
    try:
        data_loader = ElectricityDataLoader(data_path)
        data_loader.load_raw_data()
        data_loader.process_data()
        data_loader.create_daily_profiles()
        print("\n[OK] Using %s" % data_path)
        daily_profiles = data_loader.daily_profiles
    except FileNotFoundError:
        print("Warning: %s not found. Trying Pecan Street data..." % data_path)
        try:
            data_loader = PecanStreetDataLoader(fallback_path)
            data_loader.load_raw_data()
            data_loader.process_data()
            daily_profiles = data_loader.create_daily_profiles()
            print("\n[OK] Using %s" % fallback_path)
        except FileNotFoundError:
            print("Warning: %s not found. Using synthetic data." % fallback_path)
    
    prices = get_tou_prices()
    
    if daily_profiles and len(daily_profiles) > 0:
        # find day with highest solar generation
        best_idx = 0
        best_solar = 0
        for idx, profile in enumerate(daily_profiles):
            total_solar = profile['solar_kw'].sum()
            if total_solar > best_solar:
                best_solar = total_solar
                best_idx = idx
        
        profile = daily_profiles[best_idx]
        solar = profile['solar_kw'] * 5  # scale up for realistic residential system
        load = profile['load_kw']
        print("\nUsing profile from Date: %s (highest solar day)" % profile['date'])
        print("Solar scaled 5x for realistic residential microgrid")
    else:
        print("\nUsing synthetic solar and load profiles")
        np.random.seed(42)
        solar = np.maximum(0, 5 * np.sin(np.linspace(0, np.pi, 24)) + np.random.normal(0, 0.5, 24))
        load = 3 + 2 * np.sin(np.linspace(0, 2*np.pi, 24) + np.pi/4) + np.random.normal(0, 0.3, 24)
        solar = np.clip(solar, 0, 10)
        load = np.clip(load, 1, 10)
    
    print("Solar generation: min=%.2f, max=%.2f, mean=%.2f kW" % (solar.min(), solar.max(), solar.mean()))
    print("Load consumption: min=%.2f, max=%.2f, mean=%.2f kW" % (load.min(), load.max(), load.mean()))
    
    config = MicrogridConfig(
        e_max=13.5,          # Tesla Powerwall
        e_min_ratio=0.1,
        p_bat_max=5.0,
        eta_charge=0.95,
        eta_discharge=0.95,
        ramp_rate=2.5,
        p_grid_peak=10.0,
        peak_penalty_rate=0.50,
        degradation_cost_per_kwh=0.02,
        forecast_horizon=24,
    )
    
    return solar, load, prices, config


def main():
    """Run the complete microgrid simulation."""
    print_header("MICROGRID ENERGY MANAGEMENT SYSTEM WITH RL")
    print("Starting simulation pipeline...")
    print("Time: %s" % pd.Timestamp.now())
    
    # paths
    DATA_PATH = "electricityConsumptionAndProductioction.csv"
    FALLBACK_DATA_PATH = "PecanStreet_10_Homes_1Min_Data.csv"
    OUTPUT_DIR = "results"
    
    # training params
    SAC_TIMESTEPS = 200000
    PPO_TIMESTEPS = 200000
    N_EVAL_EPISODES = 100
    
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    
    # --- STEP 1 & 2: Environment Setup ---
    solar, load, prices, config = setup_environment(DATA_PATH, FALLBACK_DATA_PATH)
    
    train_env = MicrogridEnv(solar, load, prices, config=config)
    
    print("Environment created with:")
    print("  - Observation space: %s" % str(train_env.observation_space.shape))
    print("  - Action space: %s" % str(train_env.action_space.shape))
    print("  - Battery capacity: %.1f kWh" % config.e_max)
    print("  - Max charge/discharge: %.1f kW" % config.p_bat_max)
    
    # --- STEP 3: Train RL Agents ---
    print_header("STEP 3: Training RL Agents")
    
    trained_agents = {}
    
    # Train SAC
    print("\n[1/3] Training SAC Agent...")
    sac_env = MicrogridEnv(solar, load, prices, config=config)
    sac_agent = create_sac_agent(sac_env, verbose=0)
    sac_callback = TrainingCallback(log_interval=2000)
    
    start_time = time.time()
    train_agent(sac_agent, SAC_TIMESTEPS, callback=sac_callback, progress_bar=True)
    sac_train_time = time.time() - start_time
    
    save_agent(sac_agent, "%s/sac_model" % OUTPUT_DIR)
    trained_agents['SAC'] = sac_agent
    print("  SAC training completed in %.1fs" % sac_train_time)
    
    # from rl_agents import load_agent
    # sac_env_dummy = MicrogridEnv(solar, load, prices, config=config)
    # sac_agent = load_agent(type(create_sac_agent(sac_env_dummy)), "%s/sac_model" % OUTPUT_DIR, sac_env_dummy)
    # trained_agents['SAC'] = sac_agent
    # sac_train_time = 0
    
    # Train Robust SAC
    print("\n[2/3] Training Robust SAC Agent...")
    rsac_env = MicrogridEnv(
        solar, load, prices,
        config=config, 
        randomize_env=True, 
        noise_level=0.30,
        variable_noise_level=True,
        correlation=0.9
    )
    rsac_agent, rsac_wrapped_env = create_robust_sac_agent(rsac_env, verbose=0)
    rsac_callback = TrainingCallback(log_interval=2000)
    
    start_time = time.time()
    train_agent(rsac_agent, SAC_TIMESTEPS, callback=rsac_callback, progress_bar=True)
    rsac_train_time = time.time() - start_time
    
    save_agent(rsac_agent, "%s/rsac_model" % OUTPUT_DIR)
    trained_agents['R-SAC'] = rsac_agent
    print("  R-SAC training completed in %.1fs" % rsac_train_time)
    
    # Train PPO (needs normalized env)
    print("\n[3/3] Training PPO Agent...")
    ppo_env = DummyVecEnv([lambda: MicrogridEnv(solar, load, prices, config=config)])
    ppo_env = VecNormalize(ppo_env, norm_obs=True, norm_reward=True, clip_obs=10.)
    
    ppo_agent = create_ppo_agent(ppo_env, verbose=0)
    ppo_callback = TrainingCallback(log_interval=3000)
    
    start_time = time.time()
    train_agent(ppo_agent, PPO_TIMESTEPS, callback=ppo_callback, progress_bar=True)
    ppo_train_time = time.time() - start_time
    
    save_agent(ppo_agent, "%s/ppo_model" % OUTPUT_DIR)
    ppo_env.save("%s/ppo_vec_normalize.pkl" % OUTPUT_DIR)
    trained_agents['PPO'] = ppo_agent
    print("  PPO training completed in %.1fs" % ppo_train_time)
    
    # baselines
    trained_agents['NoOp'] = NoopAgent()
    trained_agents['Rule-Based'] = RuleBasedAgent()
    
    print("\nTotal training time: %.1fs" % (sac_train_time + rsac_train_time + ppo_train_time))
    
    # --- STEP 4: Evaluation ---
    print_header("STEP 4: Evaluating All Agents")
    
    eval_results = run_comprehensive_evaluation(
        agents=trained_agents,
        solar_profile=solar,
        load_profile=load,
        price_profile=prices,
        n_episodes=N_EVAL_EPISODES,
        config=config,
        verbose=True
    )
    
    save_evaluation_results(eval_results, "%s/evaluation_results.csv" % OUTPUT_DIR)
    
    # --- STEP 5: Visualizations ---
    print_header("STEP 5: Generating Visualizations")
    
    figures = generate_all_plots(eval_results, output_dir=OUTPUT_DIR, episode_idx=0)
    
    # --- STEP 6: Robustness Testing ---
    print_header("STEP 6: Robustness Testing (LP vs RL Under Uncertainty)")
    
    robustness_agents = {
        'LP': None,  # handled separately
        'SAC': trained_agents['SAC'],
        'R-SAC': trained_agents['R-SAC'],
        'PPO': trained_agents['PPO']
    }
    
    rob_config = RobustnessConfig(
        noise_levels=[0.0, 0.05, 0.10, 0.20, 0.30],
        n_scenarios=10
    )
    
    rob_results = run_robustness_test(
        agents=robustness_agents,
        solar_profile=solar,
        load_profile=load,
        price_profile=prices,
        config=rob_config,
        env_config=config,
        verbose=True
    )
    
    rob_fig = plot_robustness_comparison(rob_results, save_path="%s/13_robustness_comparison.pdf" % OUTPUT_DIR)
    plt.close(rob_fig)
    
    save_robustness_results(rob_results, output_path="%s/robustness_summary.csv" % OUTPUT_DIR)
    
    # print summary
    print("\n" + "="*60)
    print("ROBUSTNESS SUMMARY")
    print("="*60)
    rob_summary = create_robustness_summary(rob_results)
    print(rob_summary.to_string(index=False))
    
    # --- STEP 7: Final Summary ---
    print_header("SIMULATION COMPLETE - SUMMARY")
    
    summary_df = create_summary_table(eval_results)
    print(summary_df.to_string(index=False))
    
    print("\nResults saved to: %s/" % OUTPUT_DIR)
    print("   - 13 visualization plots (PNG)")
    print("   - evaluation_results.csv")
    print("   - Trained models (SAC, R-SAC, PPO)")
    
    # key findings
    print("\nKey Findings:")
    all_results = eval_results['all_results']
    
    lp_profit = all_results['LP']['mean_profit']
    print("   - LP Benchmark profit: $%.2f" % lp_profit)
    
    best_rl = max(
        [(name, res['mean_profit']) for name, res in all_results.items() if name not in ['LP', 'NoOp', 'Rule-Based']],
        key=lambda x: x[1]
    )
    print("   - Best RL agent: %s ($%.2f)" % (best_rl[0], best_rl[1]))
    
    if abs(lp_profit) > 0.01:
        gap = (lp_profit - best_rl[1]) / abs(lp_profit) * 100
        print("   - Gap vs LP: %.1f%%" % gap)
    
    print("\nRobustness Findings:")
    most_robust = rob_summary.iloc[0]['Agent']
    print("   - Most robust agent: %s" % most_robust)
    
    plt.close('all')
    
    return eval_results, rob_results


def run_quick_demo():
    """Quick demo with reduced training for testing."""
    print_header("QUICK DEMO MODE")
    
    np.random.seed(42)
    
    solar = np.maximum(0, 5 * np.sin(np.linspace(0, np.pi, 24)))
    load = 3 + 2 * np.sin(np.linspace(0, 2*np.pi, 24) + np.pi/4)
    prices = get_tou_prices()
    
    config = MicrogridConfig()
    env = MicrogridEnv(solar, load, prices, config=config)
    
    print("Training SAC (500 steps)...")
    sac_agent = create_sac_agent(env, verbose=0)
    train_agent(sac_agent, 500, progress_bar=False)
    
    agents = {
        'SAC': sac_agent,
        'Rule-Based': RuleBasedAgent()
    }
    
    print("\nEvaluating...")
    results = run_comprehensive_evaluation(
        agents, solar, load, prices,
        n_episodes=3, config=config, verbose=False
    )
    
    print("\nSummary:")
    summary = create_summary_table(results)
    print(summary.to_string(index=False))
    
    from visualization import plot_soc_comparison
    fig = plot_soc_comparison(results, save_path="demo_soc.png")
    print("\nSaved demo plot: demo_soc.png")
    plt.close(fig)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--demo":
        run_quick_demo()
    else:
        results = main()
