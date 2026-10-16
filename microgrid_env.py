# microgrid_env.py
# Gymnasium environment for battery energy management in a microgrid

import gymnasium as gym
from gymnasium import spaces
import numpy as np
from dataclasses import dataclass


class ScenarioGenerator:
    """Generates perturbed scenarios with correlated forecast errors."""
    
    def __init__(self, seed=42):
        self.rng = np.random.RandomState(seed)
    
    def add_noise(self, profile, noise_level, correlation=0.8, clip_min=0.0, clip_max=None):
        # AR(1) correlated noise process
        n = len(profile)
        noise = np.zeros(n)
        
        if abs(correlation) < 1e-5:
            noise = self.rng.normal(0, noise_level, n)
        else:
            noise[0] = self.rng.normal(0, noise_level)
            innov_scale = noise_level * np.sqrt(1 - correlation**2)
            for t in range(1, n):
                noise[t] = correlation * noise[t-1] + self.rng.normal(0, innov_scale)
            
        noisy = profile * (1 + noise)
        
        if clip_max is None:
            clip_max = profile.max() * 2
        
        return np.clip(noisy, clip_min, clip_max).astype(np.float32)
    
    def generate_scenarios(self, solar_profile, load_profile, price_profile,
                           noise_level, n_scenarios, correlation=0.8):
        """Generate multiple noisy scenarios for robustness testing."""
        scenarios = []
        for _ in range(n_scenarios):
            sc = {
                'solar': self.add_noise(solar_profile, noise_level, correlation, clip_min=0.0),
                'load': self.add_noise(load_profile, noise_level, correlation, clip_min=0.1),
                'price': self.add_noise(price_profile, noise_level * 0.5, correlation, clip_min=0.01),
                'noise_level': noise_level
            }
            scenarios.append(sc)
        return scenarios


class MicrogridConfig:
    """Configuration for the microgrid environment."""
    def __init__(self, e_max=13.5, e_min_ratio=0.1, p_bat_max=5.0,
                 eta_charge=0.95, eta_discharge=0.95, ramp_rate=2.5,
                 p_grid_peak=10.0, peak_penalty_rate=0.50,
                 degradation_cost_per_kwh=0.02,
                 target_final_soc=0.5, terminal_soc_penalty=5.0,
                 hours_per_day=24, history_length=4, forecast_horizon=24):
        self.e_max = e_max
        self.e_min_ratio = e_min_ratio
        self.p_bat_max = p_bat_max
        self.eta_charge = eta_charge
        self.eta_discharge = eta_discharge
        self.ramp_rate = ramp_rate
        self.p_grid_peak = p_grid_peak
        self.peak_penalty_rate = peak_penalty_rate
        self.degradation_cost_per_kwh = degradation_cost_per_kwh
        self.target_final_soc = target_final_soc
        self.terminal_soc_penalty = terminal_soc_penalty
        self.hours_per_day = hours_per_day
        self.history_length = history_length
        self.forecast_horizon = forecast_horizon
    
    @property
    def e_min(self):
        return self.e_max * self.e_min_ratio


class MicrogridEnv(gym.Env):
    """
    Microgrid energy management environment.
    
    Agent controls battery charge/discharge to minimize cost over 24h.
    State includes a look-ahead forecast window of PV, load and price.
    """
    
    metadata = {"render_modes": ["human", "ansi"]}
    
    def __init__(self, solar_profile, load_profile, price_profile,
                 actual_solar_profile=None, actual_load_profile=None,
                 actual_price_profile=None, config=None, render_mode=None,
                 randomize_env=False, noise_level=0.1, variable_noise_level=False,
                 correlation=0.8, seed=42):
        super().__init__()
        
        self.config = config or MicrogridConfig()
        self.render_mode = render_mode
        self.randomize_env = randomize_env
        self.noise_level = noise_level
        self.variable_noise_level = variable_noise_level
        self.correlation = correlation
        self.current_noise_level = noise_level
        self.scenario_generator = ScenarioGenerator(seed=seed) if randomize_env else None

        # forecast profiles (what the agent sees)
        self.solar_profile = np.array(solar_profile, dtype=np.float32)
        self.load_profile = np.array(load_profile, dtype=np.float32)
        self.price_profile = np.array(price_profile, dtype=np.float32)
        
        # actual profiles (physics) - defaults to forecast if not given
        self.actual_solar_profile = np.array(actual_solar_profile if actual_solar_profile is not None else solar_profile, dtype=np.float32)
        self.actual_load_profile = np.array(actual_load_profile if actual_load_profile is not None else load_profile, dtype=np.float32)
        self.actual_price_profile = np.array(actual_price_profile if actual_price_profile is not None else price_profile, dtype=np.float32)
        
        assert len(self.solar_profile) == self.config.hours_per_day
        assert len(self.load_profile) == self.config.hours_per_day
        assert len(self.price_profile) == self.config.hours_per_day
        
        # normalization
        self.max_net_power = max(abs(self.load_profile - self.solar_profile).max(), 1.0)
        self.max_price = max(self.price_profile.max(), 0.01)
        
        # observation space dimensions
        # base: SOC, net_power, price, sin_hour, cos_hour, prev_action, last_error = 7
        base_obs = 7
        hist_dim = self.config.history_length
        fc_dim = self.config.forecast_horizon * 5  # net, price, solar, sin, cos per step
        
        obs_dim = base_obs + hist_dim + fc_dim
        
        self.observation_space = spaces.Box(
            low=-1.0, high=1.0, shape=(obs_dim,), dtype=np.float32
        )
        
        # action: battery power [-1, 1] mapped to [-P_BAT_MAX, P_BAT_MAX]
        self.action_space = spaces.Box(
            low=-1.0, high=1.0, shape=(1,), dtype=np.float32
        )
        
        self._reset_state()
        
    def _reset_state(self):
        self.current_step = 0
        self.soc = 0.5
        self.prev_battery_power = 0.0
        self.total_cost = 0.0
        self.total_energy_cost = 0.0
        self.total_peak_penalty = 0.0
        self.total_degradation_cost = 0.0
        self.total_terminal_soc_penalty = 0.0
        self.total_throughput = 0.0
        self.peak_violations = 0
        self.last_forecast_error = 0.0
        self.history = np.zeros(self.config.history_length, dtype=np.float32)
        
        self.soc_history = []
        self.battery_power_history = []
        self.grid_power_history = []
        self.cost_history = []
        
    def _get_obs(self):
        hour = self.current_step
        
        solar = self.solar_profile[hour] if hour < self.config.hours_per_day else 0
        load = self.load_profile[hour] if hour < self.config.hours_per_day else 0
        price = self.price_profile[hour] if hour < self.config.hours_per_day else 0
        net_power = load - solar
        
        sin_h = np.sin(2 * np.pi * hour / 24.0)
        cos_h = np.cos(2 * np.pi * hour / 24.0)
        
        # build forecast features
        fc_features = []
        for i in range(1, self.config.forecast_horizon + 1):
            t = (hour + i) % 24
            
            f_solar = self.solar_profile[t]
            f_load = self.load_profile[t]
            f_price = self.price_profile[t]
            f_net = f_load - f_solar
            
            f_sin = np.sin(2 * np.pi * t / 24.0)
            f_cos = np.cos(2 * np.pi * t / 24.0)
            
            fc_features.extend([
                np.clip(f_net / self.max_net_power, -1, 1),
                f_price / self.max_price - 0.5,
                f_solar / self.max_net_power,
                f_sin,
                f_cos
            ])

        obs = np.array([
            (self.soc - 0.5) * 2,
            np.clip(net_power / self.max_net_power, -1, 1),
            price / self.max_price - 0.5,
            sin_h, cos_h,
            self.prev_battery_power / self.config.p_bat_max,
            np.clip(self.last_forecast_error / self.max_net_power, -1, 1),
            *self.history,
            *fc_features
        ], dtype=np.float32)
        
        return obs
    
    def _get_info(self):
        return {
            'step': self.current_step,
            'soc': self.soc,
            'total_cost': self.total_cost,
            'energy_cost': self.total_energy_cost,
            'peak_penalty': self.total_peak_penalty,
            'degradation_cost': self.total_degradation_cost,
            'throughput': self.total_throughput,
            'peak_violations': self.peak_violations
        }
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        # domain randomization for training
        if self.randomize_env:
            if self.variable_noise_level:
                self.current_noise_level = self.np_random.uniform(0.0, self.noise_level)
            else:
                self.current_noise_level = self.noise_level

            self.actual_solar_profile = self.scenario_generator.add_noise(self.solar_profile, self.current_noise_level, self.correlation, clip_min=0.0)
            self.actual_load_profile = self.scenario_generator.add_noise(self.load_profile, self.current_noise_level, self.correlation, clip_min=0.1)
            self.actual_price_profile = self.scenario_generator.add_noise(self.price_profile, self.current_noise_level * 0.2, self.correlation, clip_min=0.01)
            
            self.max_net_power = max(abs(self.load_profile - self.solar_profile).max(), 1.0)
        
        self._reset_state()
        
        if options and 'initial_soc' in options:
            self.soc = np.clip(options['initial_soc'], self.config.e_min_ratio, 1.0)
        else:
            self.soc = self.np_random.uniform(0.2, 0.8)
            
        return self._get_obs(), self._get_info()
    
    def step(self, action):
        # scale action
        action_val = float(action[0]) if hasattr(action, '__len__') else float(action)
        bat_power_req = np.clip(action_val, -1, 1) * self.config.p_bat_max
        
        # ramping constraint
        power_change = bat_power_req - self.prev_battery_power
        if abs(power_change) > self.config.ramp_rate:
            power_change = np.sign(power_change) * self.config.ramp_rate
        battery_power = self.prev_battery_power + power_change
        
        # current actual profiles
        hour = self.current_step
        solar = self.actual_solar_profile[hour]
        load = self.actual_load_profile[hour]
        price = self.actual_price_profile[hour]
        net_demand = load - solar
        
        # battery constraints
        current_energy = self.soc * self.config.e_max
        
        if battery_power > 0:  # charging
            max_charge_energy = (1.0 - self.soc) * self.config.e_max
            max_charge_power = max_charge_energy / 1.0
            battery_power = min(battery_power, max_charge_power, self.config.p_bat_max)
            energy_to_bat = battery_power * self.config.eta_charge
        else:  # discharging
            avail_energy = (self.soc - self.config.e_min_ratio) * self.config.e_max
            max_discharge = avail_energy / 1.0
            battery_power = max(battery_power, -max_discharge, -self.config.p_bat_max)
            energy_to_bat = battery_power / self.config.eta_discharge
        
        # update SOC
        new_soc = self.soc + energy_to_bat / self.config.e_max
        new_soc = np.clip(new_soc, self.config.e_min_ratio, 1.0)
        
        actual_energy_change = (new_soc - self.soc) * self.config.e_max
        
        # grid power
        grid_power = net_demand + battery_power
        
        # costs
        if grid_power >= 0:
            energy_cost = grid_power * price
        else:
            feed_in_tariff = price * 0.4  # sell at 40% of retail
            energy_cost = grid_power * feed_in_tariff
        
        peak_violation = max(0, grid_power - self.config.p_grid_peak)
        peak_penalty = peak_violation * self.config.peak_penalty_rate
        if peak_violation > 0:
            self.peak_violations += 1
        
        throughput = abs(actual_energy_change)
        degradation_cost = throughput * self.config.degradation_cost_per_kwh
        
        step_cost = energy_cost + peak_penalty + degradation_cost
        
        # update state
        self.soc = new_soc
        self.prev_battery_power = battery_power
        self.current_step += 1
        
        # forecast error tracking
        f_solar = self.solar_profile[hour]
        f_load = self.load_profile[hour]
        f_net = f_load - f_solar
        self.last_forecast_error = net_demand - f_net
        
        # update history buffer
        self.history = np.roll(self.history, -1)
        self.history[-1] = np.clip(net_demand / self.max_net_power, -1, 1)
        
        # accumulate totals
        self.total_cost += step_cost
        self.total_energy_cost += energy_cost
        self.total_peak_penalty += peak_penalty
        self.total_degradation_cost += degradation_cost
        self.total_throughput += throughput
        
        self.soc_history.append(self.soc)
        self.battery_power_history.append(battery_power)
        self.grid_power_history.append(grid_power)
        self.cost_history.append(step_cost)
        
        terminated = self.current_step >= self.config.hours_per_day
        truncated = False
        
        reward = -step_cost
        
        # terminal SOC penalty
        if terminated:
            soc_dev = abs(self.soc - self.config.target_final_soc)
            terminal_pen = soc_dev * self.config.terminal_soc_penalty * 10
            self.total_terminal_soc_penalty = terminal_pen
            self.total_cost += terminal_pen
            reward -= terminal_pen
        
        if self.render_mode == "human":
            self.render()
            
        return self._get_obs(), reward, terminated, truncated, self._get_info()
    
    def render(self):
        if self.render_mode in ("human", "ansi"):
            hour = self.current_step - 1 if self.current_step > 0 else 0
            grid_p = self.grid_power_history[-1] if self.grid_power_history else 0
            bat_p = self.battery_power_history[-1] if self.battery_power_history else 0
            print("Hour %2d: SOC=%.2f%%, Grid=%.2fkW, Bat=%.2fkW, Cost=$%.2f" %
                  (hour, self.soc*100, grid_p, bat_p, self.total_cost))
    
    def get_episode_results(self):
        return {
            'soc_trajectory': np.array(self.soc_history),
            'battery_power': np.array(self.battery_power_history),
            'grid_power': np.array(self.grid_power_history),
            'cost_per_step': np.array(self.cost_history),
            'cumulative_cost': np.cumsum(self.cost_history),
            'total_cost': self.total_cost,
            'energy_cost': self.total_energy_cost,
            'peak_penalty': self.total_peak_penalty,
            'degradation_cost': self.total_degradation_cost,
            'throughput': self.total_throughput,
            'peak_violations': self.peak_violations,
            'final_soc': self.soc,
            'solar_profile': self.actual_solar_profile,
            'load_profile': self.actual_load_profile,
            'price_profile': self.actual_price_profile,
            'forecast_solar': self.solar_profile,
            'forecast_load': self.load_profile
        }


class DynamicMicrogridEnv(MicrogridEnv):
    """Microgrid env that samples new profiles from a data loader each episode."""
    
    def __init__(self, data_loader, price_profile, config=None, render_mode=None):
        self.data_loader = data_loader
        self.stored_price_profile = price_profile
        
        ep_data = data_loader.get_episode_data(0)
        
        super().__init__(
            solar_profile=ep_data['solar_kw'],
            load_profile=ep_data['load_kw'],
            price_profile=price_profile,
            config=config,
            render_mode=render_mode
        )
    
    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        
        ep_data = self.data_loader.get_episode_data()
        self.solar_profile = ep_data['solar_kw']
        self.load_profile = ep_data['load_kw']
        
        self.max_net_power = max(abs(self.load_profile - self.solar_profile).max(), 1.0)
        
        self._reset_state()
        
        if options and 'initial_soc' in options:
            self.soc = np.clip(options['initial_soc'], self.config.e_min_ratio, 1.0)
        else:
            self.soc = self.np_random.uniform(0.2, 0.8)
            
        return self._get_obs(), self._get_info()


if __name__ == "__main__":
    from data_loader import get_tou_prices
    
    np.random.seed(42)
    solar = np.maximum(0, 5 * np.sin(np.linspace(0, np.pi, 24)))
    load = 3 + 2 * np.sin(np.linspace(0, 2*np.pi, 24) + np.pi/4)
    prices = get_tou_prices()
    
    env = MicrogridEnv(solar, load, prices, render_mode="human")
    
    obs, info = env.reset(seed=42)
    print("Observation shape: %s" % str(obs.shape))
    print("Initial SOC: %.2f%%" % (info['soc']*100))
    
    total_reward = 0
    for step in range(24):
        action = env.action_space.sample()
        obs, reward, terminated, truncated, info = env.step(action)
        total_reward += reward
        if terminated:
            break
    
    print("\nEpisode finished:")
    print("Total reward: %.2f" % total_reward)
    print("Total cost: $%.2f" % info['total_cost'])
    print("Final SOC: %.2f%%" % (info['soc']*100))
    print("Peak violations: %d" % info['peak_violations'])
