# robustness_test.py
# Compare LP vs RL agents under forecast uncertainty

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os

from microgrid_env import MicrogridEnv, MicrogridConfig, ScenarioGenerator
from lp_solver import solve_lp_benchmark, LPConfig


class RobustnessConfig:
    """Settings for robustness testing."""
    def __init__(self, noise_levels=None, n_scenarios=10, seed=42):
        if noise_levels is None:
            noise_levels = [0.0, 0.05, 0.10, 0.20, 0.30]
        self.noise_levels = noise_levels
        self.n_scenarios = n_scenarios
        self.seed = seed


def evaluate_lp_with_forecast_error(forecast_solar, forecast_load,
                                     actual_solar, actual_load,
                                     price_profile, initial_soc=0.5, config=None):
    """LP plans on forecast but executes on actual (noisy) data."""
    lp_plan = solve_lp_benchmark(forecast_solar, forecast_load, price_profile, initial_soc)
    
    env_config = config or MicrogridConfig()
    env = MicrogridEnv(actual_solar, actual_load, price_profile, config=env_config)
    
    obs, _ = env.reset(options={'initial_soc': initial_soc})
    
    total_reward = 0
    for t in range(24):
        planned = lp_plan['battery_power'][t] if t < len(lp_plan['battery_power']) else 0
        action = np.clip(np.array([planned / env_config.p_bat_max]), -1, 1)
        
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        if terminated or truncated:
            break
    
    results = env.get_episode_results()
    results['planned_vs_actual'] = {
        'forecast_solar': forecast_solar,
        'actual_solar': actual_solar,
        'forecast_load': forecast_load,
        'actual_load': actual_load
    }
    return results


def evaluate_agent_with_noise(agent, forecast_solar, forecast_load,
                               actual_solar, actual_load, price_profile,
                               initial_soc=0.5, config=None):
    """
    Evaluate RL agent under mismatch between forecast and reality.
    Agent sees forecast in obs, but physics uses actual.
    """
    env_config = config or MicrogridConfig()
    
    env = MicrogridEnv(
        solar_profile=forecast_solar,
        load_profile=forecast_load,
        price_profile=price_profile,
        actual_solar_profile=actual_solar,
        actual_load_profile=actual_load,
        actual_price_profile=price_profile,
        config=env_config
    )
    
    obs, _ = env.reset(options={'initial_soc': initial_soc})
    
    total_reward = 0
    for t in range(24):
        action, _ = agent.predict(obs, deterministic=True)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        if terminated or truncated:
            break
    
    return env.get_episode_results()


def run_robustness_test(agents, solar_profile, load_profile, price_profile,
                         config=None, env_config=None, verbose=True):
    """Run robustness test across noise levels. Returns results dict."""
    config = config or RobustnessConfig()
    generator = ScenarioGenerator(seed=config.seed)
    
    results = {
        'noise_levels': config.noise_levels,
        'agents': {},
        'raw_results': {}
    }
    
    for agent_name in agents.keys():
        results['agents'][agent_name] = {
            'mean_profits': [],
            'std_profits': [],
            'all_profits': []
        }
        results['raw_results'][agent_name] = {}
    
    if verbose:
        print("\n" + "="*60)
        print("ROBUSTNESS TEST: LP vs RL Agents Under Uncertainty")
        print("="*60)
    
    for noise_level in config.noise_levels:
        if verbose:
            print("\n--- Noise Level: %.0f%% ---" % (noise_level*100))
        
        scenarios = generator.generate_scenarios(
            solar_profile, load_profile, price_profile,
            noise_level, config.n_scenarios
        )
        
        for agent_name, agent in agents.items():
            profits = []
            
            for sc in scenarios:
                init_soc = np.random.uniform(0.2, 0.8)
                
                if agent_name == 'LP':
                    result = evaluate_lp_with_forecast_error(
                        solar_profile, load_profile,
                        sc['solar'], sc['load'],
                        price_profile, init_soc, env_config
                    )
                else:
                    result = evaluate_agent_with_noise(
                        agent,
                        solar_profile, load_profile,
                        sc['solar'], sc['load'],
                        price_profile, init_soc, env_config
                    )
                
                profits.append(-result['total_cost'])
            
            mean_p = np.mean(profits)
            std_p = np.std(profits)
            
            results['agents'][agent_name]['mean_profits'].append(mean_p)
            results['agents'][agent_name]['std_profits'].append(std_p)
            results['agents'][agent_name]['all_profits'].append(profits)
            results['raw_results'][agent_name][noise_level] = profits
            
            if verbose:
                print("  %-12s: $%.2f +/- $%.2f" % (agent_name, mean_p, std_p))
    
    return results


def plot_robustness_comparison(results, save_path=None):
    """Plot profit vs noise level for all agents."""
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 5))
    
    noise_pct = np.array(results['noise_levels']) * 100
    
    colors = {
        'LP': '#2ecc71', 'SAC': '#3498db', 'R-SAC': '#9b59b6',
        'PPO': '#e74c3c', 'NoOp': '#95a5a6', 'Rule-Based': '#f39c12'
    }
    
    for name, agt_res in results['agents'].items():
        c = colors.get(name, '#333333')
        means = agt_res['mean_profits']
        stds = agt_res['std_profits']
        
        ax1.plot(noise_pct, means, 'o-', label=name, color=c, linewidth=2, markersize=8)
        ax1.fill_between(noise_pct,
                         np.array(means) - np.array(stds),
                         np.array(means) + np.array(stds),
                         alpha=0.2, color=c)
    
    ax1.set_xlabel('Forecast Error (%)')
    ax1.set_ylabel('Mean Profit ($)')
    ax1.set_title('Profit vs Forecast Uncertainty', fontweight='bold')
    ax1.legend(loc='best')
    ax1.grid(True, alpha=0.3)
    ax1.axhline(y=0, color='black', linestyle='--', alpha=0.3)
    
    # relative performance
    for name, agt_res in results['agents'].items():
        c = colors.get(name, '#333333')
        means = np.array(agt_res['mean_profits'])
        if abs(means[0]) > 0.01:
            rel = means / means[0] * 100
        else:
            rel = np.ones_like(means) * 100
        ax2.plot(noise_pct, rel, 'o-', label=name, color=c, linewidth=2, markersize=8)
    
    ax2.set_xlabel('Forecast Error (%)')
    ax2.set_ylabel('Relative Performance (%)')
    ax2.set_title('Performance Degradation Under Uncertainty', fontweight='bold')
    ax2.legend(loc='best')
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=100, color='black', linestyle='--', alpha=0.3)
    
    plt.tight_layout()
    
    if save_path:
        fig.savefig(save_path, dpi=150, bbox_inches='tight')
        print("Saved: %s" % save_path)
    
    return fig


def create_robustness_summary(results):
    """Summary table: baseline vs worst-case profit & degradation."""
    rows = []
    for name, agt_res in results['agents'].items():
        baseline = agt_res['mean_profits'][0]
        worst = agt_res['mean_profits'][-1]
        
        if abs(baseline) > 0.01:
            deg = (baseline - worst) / abs(baseline) * 100
        else:
            deg = 0.0
        
        rows.append({
            'Agent': name,
            'Profit @ 0% Noise': baseline,
            'Profit @ 30% Noise': worst,
            'Degradation (%)': deg,
            'Robustness Score': 100 - abs(deg)
        })
    
    df = pd.DataFrame(rows)
    df = df.sort_values('Robustness Score', ascending=False)
    return df


def save_robustness_results(results, output_path):
    """Save summary + detailed per-scenario results."""
    summary = create_robustness_summary(results)
    summary.to_csv(output_path, index=False)
    print("Robustness summary saved to %s" % output_path)
    
    detailed_rows = []
    for agent_name, agent_data in results['raw_results'].items():
        for noise_level, profits in agent_data.items():
            for i, profit in enumerate(profits):
                detailed_rows.append({
                    'Agent': agent_name,
                    'Noise Level': noise_level,
                    'Scenario': i + 1,
                    'Profit ($)': profit
                })
                
    detailed_df = pd.DataFrame(detailed_rows)
    base = os.path.dirname(output_path)
    detailed_path = os.path.join(base, "robustness_detailed.csv")
    detailed_df.to_csv(detailed_path, index=False)
    print("Detailed results saved to %s" % detailed_path)


if __name__ == "__main__":
    from data_loader import get_tou_prices
    from rl_agents import NoopAgent, RuleBasedAgent
    from stable_baselines3 import SAC, PPO

    print("Testing Robustness Module...")
    
    np.random.seed(42)
    solar = np.maximum(0, 5 * np.sin(np.linspace(0, np.pi, 24)))
    load = 3 + 2 * np.sin(np.linspace(0, 2*np.pi, 24) + np.pi/4)
    prices = get_tou_prices()
    
    env_config = MicrogridConfig()
    env = MicrogridEnv(solar, load, prices, config=env_config)
    
    agents = {
        'LP': None,
        'NoOp': NoopAgent(),
        'Rule-Based': RuleBasedAgent()
    }
    
    model_dir = "results"
    
    if os.path.exists(os.path.join(model_dir, "sac_model.zip")):
        try:
            print("Loading SAC agent...")
            agents['SAC'] = SAC.load(os.path.join(model_dir, "sac_model"), env=env)
        except Exception as e:
            print("Failed to load SAC: %s" % e)

    if os.path.exists(os.path.join(model_dir, "ppo_model.zip")):
        try:
            print("Loading PPO agent...")
            agents['PPO'] = PPO.load(os.path.join(model_dir, "ppo_model"), env=env)
        except Exception as e:
            print("Failed to load PPO: %s" % e)
            
    if os.path.exists(os.path.join(model_dir, "rsac_model.zip")):
        try:
            print("Loading RSAC agent...")
            agents['R-SAC'] = SAC.load(os.path.join(model_dir, "rsac_model"), env=env)
        except Exception as e:
            print("Failed to load RSAC: %s" % e)
    
    test_config = RobustnessConfig(
        noise_levels=[0.0, 0.1, 0.2, 0.3],
        n_scenarios=5
    )
    
    results = run_robustness_test(agents, solar, load, prices,
                                  config=test_config, verbose=True)
    
    print("\n" + "="*60)
    print("ROBUSTNESS SUMMARY")
    print("="*60)
    summary = create_robustness_summary(results)
    print(summary.to_string(index=False))
    
    fig = plot_robustness_comparison(results, save_path="test_robustness.pdf")
    print("\nSaved test plot")
    plt.close(fig)
