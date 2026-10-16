# evaluation.py
# Multi-episode evaluation framework and metrics

import numpy as np
import pandas as pd
import os
import time

from microgrid_env import MicrogridEnv, MicrogridConfig
from lp_solver import solve_lp_benchmark, LPConfig
from data_loader import get_tou_prices

from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize


class EvaluationMetrics:
    """Holds aggregated evaluation metrics."""
    def __init__(self, mean_profit, std_profit, min_profit, max_profit,
                 mean_energy_profit, mean_peak_penalty, mean_throughput,
                 mean_final_soc, mean_peak_violations, gap_vs_lp=0.0, gap_std=0.0):
        self.mean_profit = mean_profit
        self.std_profit = std_profit
        self.min_profit = min_profit
        self.max_profit = max_profit
        self.mean_energy_profit = mean_energy_profit
        self.mean_peak_penalty = mean_peak_penalty
        self.mean_throughput = mean_throughput
        self.mean_final_soc = mean_final_soc
        self.mean_peak_violations = mean_peak_violations
        self.gap_vs_lp = gap_vs_lp
        self.gap_std = gap_std


def evaluate_agent_single_episode(agent, env, deterministic=True, initial_soc=None):
    """Run one episode and return results."""
    options = {'initial_soc': initial_soc} if initial_soc else None
    obs, info = env.reset(options=options)
    
    total_reward = 0
    done = False
    
    while not done:
        action, _ = agent.predict(obs, deterministic=deterministic)
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        done = terminated or truncated
    
    results = env.get_episode_results()
    results['total_reward'] = total_reward
    results['initial_soc'] = initial_soc
    return results


def evaluate_agent_multi_episode(agent, env, n_episodes=10, deterministic=True,
                                  initial_socs=None, verbose=True):
    """Evaluate over multiple episodes, return (results_list, metrics)."""
    if initial_socs is None:
        initial_socs = np.linspace(0.2, 0.8, n_episodes)
    
    all_results = []
    
    for i, init_soc in enumerate(initial_socs):
        if verbose and (i + 1) % 5 == 0:
            print("  Episode %d/%d" % (i+1, n_episodes))
        
        results = evaluate_agent_single_episode(agent, env, deterministic, init_soc)
        all_results.append(results)
    
    # aggregate (cost -> profit by negating)
    profits = [-r['total_cost'] for r in all_results]
    energy_profits = [-r['energy_cost'] for r in all_results]
    peak_pens = [r['peak_penalty'] for r in all_results]
    thruputs = [r['throughput'] for r in all_results]
    final_socs = [r['final_soc'] for r in all_results]
    peak_viols = [r['peak_violations'] for r in all_results]
    
    metrics = EvaluationMetrics(
        mean_profit=np.mean(profits),
        std_profit=np.std(profits),
        min_profit=np.min(profits),
        max_profit=np.max(profits),
        mean_energy_profit=np.mean(energy_profits),
        mean_peak_penalty=np.mean(peak_pens),
        mean_throughput=np.mean(thruputs),
        mean_final_soc=np.mean(final_socs),
        mean_peak_violations=np.mean(peak_viols),
    )
    
    return all_results, metrics


def calculate_lp_benchmark(solar_profile, load_profile, price_profile, initial_socs):
    """Run LP for each initial SOC."""
    lp_results = []
    for init_soc in initial_socs:
        result = solve_lp_benchmark(solar_profile, load_profile, price_profile, init_soc)
        result['initial_soc'] = init_soc
        lp_results.append(result)
    return lp_results


def calculate_optimality_gap(agent_profits, lp_profits):
    """Gap = (LP - Agent) / |LP| * 100. Returns (mean, std, list)."""
    gaps = []
    for ap, lp in zip(agent_profits, lp_profits):
        if abs(lp) > 0.01:
            gap = (lp - ap) / abs(lp) * 100
        else:
            gap = 0.0
        gaps.append(gap)
    return np.mean(gaps), np.std(gaps), gaps


def run_comprehensive_evaluation(agents, solar_profile, load_profile, price_profile,
                                  n_episodes=10, config=None, verbose=True):
    """Evaluate all agents + LP benchmark. Returns comprehensive results dict."""
    env_config = config or MicrogridConfig()
    initial_socs = list(np.linspace(0.2, 0.8, n_episodes))
    
    results = {}
    
    # LP benchmark first
    if verbose:
        print("\n" + "="*60)
        print("Evaluating LP Benchmark...")
        print("="*60)
    
    t0 = time.time()
    lp_results = calculate_lp_benchmark(solar_profile, load_profile, price_profile, initial_socs)
    lp_time = time.time() - t0
    
    lp_costs = [r['total_cost'] for r in lp_results]
    lp_profits = [-c for c in lp_costs]
    
    results['LP'] = {
        'episodes': lp_results,
        'mean_profit': np.mean(lp_profits),
        'std_profit': np.std(lp_profits),
        'mean_gap': 0.0,
        'evaluation_time': lp_time
    }
    
    if verbose:
        print("  Mean profit: $%.2f +/- $%.2f" % (np.mean(lp_profits), np.std(lp_profits)))
    
    # wrapper for PPO obs normalization
    import gymnasium as gym
    class ManualNormalizeWrapper(gym.Wrapper):
        def __init__(self, env, obs_rms):
            super().__init__(env)
            self.obs_rms = obs_rms
            self.epsilon = 1e-8
        def normalize(self, obs):
            return np.clip((obs - self.obs_rms.mean) / np.sqrt(self.obs_rms.var + self.epsilon), -10, 10)
        def step(self, action):
            obs, r, term, trunc, info = self.env.step(action)
            return self.normalize(obs), r, term, trunc, info
        def reset(self, **kwargs):
            obs, info = self.env.reset(**kwargs)
            return self.normalize(obs), info
        def get_episode_results(self):
            return self.env.get_episode_results()

    # evaluate each agent
    for agent_name, agent in agents.items():
        if verbose:
            print("\n" + "="*60)
            print("Evaluating %s..." % agent_name)
            print("="*60)
        
        env = MicrogridEnv(solar_profile, load_profile, price_profile, config=env_config)
        
        # PPO needs normalized observations
        if agent_name == 'PPO':
            stats_path = "results/ppo_vec_normalize.pkl"
            if os.path.exists(stats_path):
                print("  Loading PPO normalization stats...")
                dummy = DummyVecEnv([lambda: MicrogridEnv(solar_profile, load_profile, price_profile, config=env_config)])
                vec_norm = VecNormalize.load(stats_path, dummy)
                env = ManualNormalizeWrapper(env, vec_norm.obs_rms)
            else:
                print("  WARNING: PPO normalization stats not found!")
        
        t0 = time.time()
        agent_results, metrics = evaluate_agent_multi_episode(
            agent, env, n_episodes,
            deterministic=True, initial_socs=initial_socs, verbose=verbose
        )
        eval_time = time.time() - t0
        
        agent_profits = [-r['total_cost'] for r in agent_results]
        mean_gap, std_gap, gaps = calculate_optimality_gap(agent_profits, lp_profits)
        
        results[agent_name] = {
            'episodes': agent_results,
            'metrics': metrics,
            'mean_profit': metrics.mean_profit,
            'std_profit': metrics.std_profit,
            'mean_gap': mean_gap,
            'std_gap': std_gap,
            'gaps': gaps,
            'evaluation_time': eval_time
        }
        
        if verbose:
            print("  Mean profit: $%.2f +/- $%.2f" % (metrics.mean_profit, metrics.std_profit))
            print("  Gap vs LP: %.1f%% +/- %.1f%%" % (mean_gap, std_gap))
    
    return {
        'all_results': results,
        'solar_profile': solar_profile,
        'load_profile': load_profile,
        'price_profile': price_profile,
        'initial_socs': initial_socs,
        'n_episodes': n_episodes
    }


def create_summary_table(evaluation_results):
    """Build a pandas DataFrame summarizing all agent results."""
    all_results = evaluation_results['all_results']
    
    rows = []
    for name, res in all_results.items():
        if name == 'LP':
            row = {
                'Agent': name,
                'Mean Profit ($)': res['mean_profit'],
                'Std Profit ($)': res['std_profit'],
                'Gap vs LP (%)': 0.0,
                'Gap Std (%)': 0.0,
                'Mean Energy Profit ($)': -np.mean([e['energy_cost'] for e in res['episodes']]),
                'Mean Peak Penalty ($)': np.mean([e['peak_penalty'] for e in res['episodes']]),
                'Mean Throughput (kWh)': np.mean([e['throughput'] for e in res['episodes']]),
                'Mean Final SOC': np.mean([e['final_soc'] for e in res['episodes']]),
                'Eval Time (s)': res['evaluation_time']
            }
        else:
            m = res['metrics']
            row = {
                'Agent': name,
                'Mean Profit ($)': res['mean_profit'],
                'Std Profit ($)': res['std_profit'],
                'Gap vs LP (%)': res['mean_gap'],
                'Gap Std (%)': res.get('std_gap', 0),
                'Mean Energy Profit ($)': m.mean_energy_profit,
                'Mean Peak Penalty ($)': m.mean_peak_penalty,
                'Mean Throughput (kWh)': m.mean_throughput,
                'Mean Final SOC': m.mean_final_soc,
                'Eval Time (s)': res['evaluation_time']
            }
        rows.append(row)
    
    df = pd.DataFrame(rows)
    df = df.sort_values('Mean Profit ($)', ascending=False)
    return df


def save_evaluation_results(evaluation_results, output_path):
    """Save summary + detailed episode results to CSV."""
    summary = create_summary_table(evaluation_results)
    summary.to_csv(output_path, index=False)
    print("Summary saved to %s" % output_path)
    
    all_results = evaluation_results['all_results']
    detailed_rows = []
    
    for agent_name, agent_data in all_results.items():
        for i, ep in enumerate(agent_data['episodes']):
            row = {
                'Agent': agent_name,
                'Episode': i + 1,
                'Initial SOC': ep.get('initial_soc', np.nan),
                'Final SOC': ep.get('final_soc', np.nan),
                'Total Cost ($)': ep['total_cost'],
                'Profit ($)': -ep['total_cost'],
                'Energy Cost ($)': ep['energy_cost'],
                'Peak Penalty ($)': ep['peak_penalty'],
                'Degradation Cost ($)': ep['degradation_cost'],
                'Throughput (kWh)': ep['throughput'],
                'Peak Violations': ep['peak_violations'],
                'Total Solar (kWh)': np.sum(ep.get('actual_solar_profile', ep.get('solar_profile', []))),
                'Total Load (kWh)': np.sum(ep.get('actual_load_profile', ep.get('load_profile', []))),
                'Net Grid Energy (kWh)': np.sum(ep['grid_power']),
            }
            detailed_rows.append(row)
            
    detailed_df = pd.DataFrame(detailed_rows)
    
    base = os.path.dirname(output_path)
    detailed_path = os.path.join(base, "evaluation_episodes.csv")
    detailed_df.to_csv(detailed_path, index=False)
    print("Detailed results saved to %s" % detailed_path)


if __name__ == "__main__":
    from rl_agents import RuleBasedAgent, NoopAgent, RandomAgent
    
    np.random.seed(42)
    
    solar = np.maximum(0, 5 * np.sin(np.linspace(0, np.pi, 24)))
    load = 3 + 2 * np.sin(np.linspace(0, 2*np.pi, 24) + np.pi/4)
    prices = get_tou_prices()
    
    agents = {
        'NoOp': NoopAgent(),
        'Rule-Based': RuleBasedAgent()
    }
    
    print("Running quick evaluation test...")
    results = run_comprehensive_evaluation(agents, solar, load, prices,
                                            n_episodes=3, verbose=True)
    
    print("\n" + "="*60)
    print("Summary Table:")
    print("="*60)
    summary = create_summary_table(results)
    print(summary.to_string(index=False))
