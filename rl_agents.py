# rl_agents.py
# RL agent creation, training, and baseline agents for microgrid

import os
import numpy as np
from pathlib import Path

from stable_baselines3 import SAC, PPO
from stable_baselines3.common.callbacks import BaseCallback, EvalCallback
from stable_baselines3.common.noise import NormalActionNoise
from stable_baselines3.common.vec_env import DummyVecEnv
from stable_baselines3.common.monitor import Monitor

import gymnasium as gym


class TrainingCallback(BaseCallback):
    """Callback for logging training progress."""
    
    def __init__(self, log_interval=1000, verbose=1):
        super().__init__(verbose)
        self.log_interval = log_interval
        self.episode_rewards = []
        self.episode_costs = []
        self.episode_lengths = []
        
    def _on_step(self):
        if self.n_calls % self.log_interval == 0 and self.verbose > 0:
            if len(self.episode_rewards) > 0:
                mean_rew = np.mean(self.episode_rewards[-10:])
                print("Step %d: Mean reward (last 10): %.2f" % (self.n_calls, mean_rew))
        return True
    
    def _on_rollout_end(self):
        if hasattr(self, 'locals') and 'infos' in self.locals:
            for info in self.locals['infos']:
                if 'episode' in info:
                    self.episode_rewards.append(info['episode']['r'])
                    self.episode_lengths.append(info['episode']['l'])


def create_sac_agent(env, learning_rate=3e-4, buffer_size=50000,
                     batch_size=256, gamma=0.99, tau=0.005,
                     policy_kwargs=None, verbose=1):
    """Create SAC agent with default hyperparams."""
    if policy_kwargs is None:
        policy_kwargs = {'net_arch': [256, 256]}
    
    agent = SAC(
        policy='MlpPolicy',
        env=env,
        learning_rate=learning_rate,
        buffer_size=buffer_size,
        batch_size=batch_size,
        gamma=gamma,
        tau=tau,
        policy_kwargs=policy_kwargs,
        verbose=verbose,
        tensorboard_log=None
    )
    return agent


def create_ppo_agent(env, learning_rate=3e-4, n_steps=4096,
                     batch_size=128, n_epochs=15, gamma=0.99,
                     gae_lambda=0.95, clip_range=0.2,
                     ent_coef=0.01, vf_coef=0.5, max_grad_norm=0.5,
                     policy_kwargs=None, verbose=1):
    """Create PPO agent. Uses SDE and deeper network."""
    if policy_kwargs is None:
        policy_kwargs = {
            'net_arch': dict(pi=[256, 256, 128], vf=[256, 256, 128]),
            'ortho_init': True,
        }
    
    agent = PPO(
        policy='MlpPolicy',
        env=env,
        learning_rate=learning_rate,
        n_steps=n_steps,
        batch_size=batch_size,
        n_epochs=n_epochs,
        gamma=gamma,
        gae_lambda=gae_lambda,
        clip_range=clip_range,
        ent_coef=ent_coef,
        vf_coef=vf_coef,
        max_grad_norm=max_grad_norm,
        use_sde=True,
        sde_sample_freq=4,
        normalize_advantage=True,
        policy_kwargs=policy_kwargs,
        verbose=verbose,
        tensorboard_log=None
    )
    return agent


def create_robust_sac_agent(env, learning_rate=1e-4, buffer_size=100000,
                            batch_size=512, gamma=0.99, tau=0.005,
                            train_freq=1, gradient_steps=2,
                            learning_starts=1000, policy_kwargs=None,
                            verbose=1, **sac_kwargs):
    """
    Create Robust SAC with domain randomization support.
    Lower LR + bigger buffer + deeper net for stable training under noise.
    """
    if policy_kwargs is None:
        policy_kwargs = {'net_arch': [256, 256, 128]}
    
    agent = SAC(
        policy='MlpPolicy',
        env=env,
        learning_rate=learning_rate,
        buffer_size=buffer_size,
        batch_size=batch_size,
        gamma=gamma,
        tau=tau,
        train_freq=train_freq,
        gradient_steps=gradient_steps,
        learning_starts=learning_starts,
        use_sde=True,
        use_sde_at_warmup=True,
        policy_kwargs=policy_kwargs,
        verbose=verbose,
        tensorboard_log=None,
        **sac_kwargs
    )
    return agent, env


def train_agent(agent, total_timesteps, callback=None, progress_bar=True):
    """Train the given RL agent."""
    print("\n" + "="*50)
    print("Training %s for %d timesteps..." % (type(agent).__name__, total_timesteps))
    print("="*50 + "\n")
    
    if callback is None:
        callback = TrainingCallback(log_interval=1000)
    
    agent.learn(
        total_timesteps=total_timesteps,
        callback=callback,
        progress_bar=progress_bar
    )
    
    return {
        'timesteps': total_timesteps,
        'episode_rewards': getattr(callback, 'episode_rewards', []),
        'episode_lengths': getattr(callback, 'episode_lengths', [])
    }


def save_agent(agent, path):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    agent.save(path)
    print("Agent saved to %s" % path)


def load_agent(agent_class, path, env):
    return agent_class.load(path, env=env)


def evaluate_agent(agent, env, n_episodes=10, deterministic=True):
    """Run evaluation episodes and collect stats."""
    all_rewards = []
    all_costs = []
    all_episodes = []
    
    for ep in range(n_episodes):
        obs, info = env.reset()
        ep_reward = 0
        done = False
        
        while not done:
            action, _ = agent.predict(obs, deterministic=deterministic)
            obs, reward, terminated, truncated, info = env.step(action)
            ep_reward += reward
            done = terminated or truncated
        
        all_rewards.append(ep_reward)
        all_costs.append(info['total_cost'])
        all_episodes.append(env.get_episode_results())
    
    return {
        'mean_reward': np.mean(all_rewards),
        'std_reward': np.std(all_rewards),
        'mean_cost': np.mean(all_costs),
        'std_cost': np.std(all_costs),
        'all_rewards': all_rewards,
        'all_costs': all_costs,
        'episodes': all_episodes
    }


class NoopAgent:
    """Does nothing - battery stays idle."""
    def predict(self, obs, deterministic=True):
        return np.array([0.0]), None


class RandomAgent:
    """Takes random actions."""
    def __init__(self, action_space):
        self.action_space = action_space
    def predict(self, obs, deterministic=True):
        return self.action_space.sample(), None


class RuleBasedAgent:
    """
    Simple heuristic:
    - charge when excess solar & SOC is low
    - discharge when price is high & SOC available
    """
    def predict(self, obs, deterministic=True):
        soc = (obs[0] + 1) / 2  # [-1,1] -> [0,1]
        net_power = obs[1]
        price = obs[2]
        
        action = 0.0
        
        if net_power < -0.2:  # excess solar
            if soc < 0.9:
                action = 0.8
        elif net_power > 0.2:  # need power
            if soc > 0.2:
                if price > 0.1:
                    action = -0.8
                    
        return np.array([action]), None


if __name__ == "__main__":
    from microgrid_env import MicrogridEnv
    from data_loader import get_tou_prices
    
    np.random.seed(42)
    solar = np.maximum(0, 5 * np.sin(np.linspace(0, np.pi, 24)))
    load = 3 + 2 * np.sin(np.linspace(0, 2*np.pi, 24) + np.pi/4)
    prices = get_tou_prices()
    
    env = MicrogridEnv(solar, load, prices)
    
    print("Creating SAC agent...")
    sac_agent = create_sac_agent(env, verbose=0)
    print("SAC: %s" % sac_agent)
    
    print("\nCreating PPO agent...")
    ppo_agent = create_ppo_agent(env, verbose=0)
    print("PPO: %s" % ppo_agent)
    
    print("\nCreating Robust SAC agent...")
    rsac_agent, rsac_env = create_robust_sac_agent(env, verbose=0)
    print("R-SAC: %s" % rsac_agent)
    
    print("\nQuick training test (100 steps)...")
    train_agent(sac_agent, 100, progress_bar=False)
    print("OK")
