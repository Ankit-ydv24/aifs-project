# lp_solver.py
# Optimal battery scheduling via linear programming
# Provides theoretical lower bound (perfect foresight benchmark)

import numpy as np
from scipy.optimize import linprog


class LPConfig:
    """LP solver configuration (mirrors MicrogridConfig params)."""
    def __init__(self, e_max=13.5, e_min_ratio=0.1, p_bat_max=5.0,
                 eta_charge=0.95, eta_discharge=0.95, ramp_rate=2.5,
                 p_grid_peak=10.0, peak_penalty_rate=0.50,
                 degradation_cost=0.02, feed_in_ratio=0.4):
        self.e_max = e_max
        self.e_min_ratio = e_min_ratio
        self.p_bat_max = p_bat_max
        self.eta_charge = eta_charge
        self.eta_discharge = eta_discharge
        self.ramp_rate = ramp_rate
        self.p_grid_peak = p_grid_peak
        self.peak_penalty_rate = peak_penalty_rate
        self.degradation_cost = degradation_cost
        self.feed_in_ratio = feed_in_ratio
    
    @property
    def e_min(self):
        return self.e_max * self.e_min_ratio


class MicrogridLPSolver:
    """
    LP formulation for optimal battery scheduling.
    
    Minimizes: sum_t (energy_cost + peak_penalty + degradation)
    Subject to SOC dynamics, power bounds, ramping constraints.
    """
    
    def __init__(self, config=None):
        self.config = config or LPConfig()
        
    def solve(self, solar_profile, load_profile, price_profile,
              initial_soc=0.5, final_soc_penalty=0.0):
        """Solve optimal schedule. Returns dict with costs and trajectories."""
        T = len(solar_profile)
        net_load = load_profile - solar_profile
        
        # Decision vars: P_c[0:T], P_d[T:2T], P_peak[2T:3T],
        #                P_grid_pos[3T:4T], P_grid_neg[4T:5T]
        n_vars = 5 * T
        
        # objective coefficients
        c = np.zeros(n_vars)
        
        for t in range(T):
            c[3*T + t] = price_profile[t]                          # buy cost
            c[4*T + t] = -price_profile[t] * self.config.feed_in_ratio  # sell revenue
            c[2*T + t] = self.config.peak_penalty_rate              # peak penalty
            c[t]       += self.config.degradation_cost * self.config.eta_charge
            c[T + t]   += self.config.degradation_cost / self.config.eta_discharge
        
        A_eq = []
        b_eq = []
        A_ub = []
        b_ub = []
        
        soc_current = initial_soc * self.config.e_max
        
        # grid power balance
        for t in range(T):
            row = np.zeros(n_vars)
            row[3*T + t] = 1     # P_grid_pos
            row[4*T + t] = -1    # -P_grid_neg
            row[t] = -1          # -P_c
            row[T + t] = 1       # +P_d
            A_eq.append(row)
            b_eq.append(net_load[t])
        
        # peak violation: P_peak >= P_grid_pos - threshold
        for t in range(T):
            row = np.zeros(n_vars)
            row[2*T + t] = -1
            row[3*T + t] = 1
            A_ub.append(row)
            b_ub.append(self.config.p_grid_peak)
        
        # SOC bounds (cumulative formulation)
        for t in range(T):
            # upper: SOC_init + sum(eta*Pc - Pd/eta) <= E_max
            row_up = np.zeros(n_vars)
            for s in range(t + 1):
                row_up[s] = self.config.eta_charge
                row_up[T + s] = -1 / self.config.eta_discharge
            A_ub.append(row_up)
            b_ub.append(self.config.e_max - soc_current)
            
            # lower: -(sum) <= SOC_init - E_min
            row_lo = np.zeros(n_vars)
            for s in range(t + 1):
                row_lo[s] = -self.config.eta_charge
                row_lo[T + s] = 1 / self.config.eta_discharge
            A_ub.append(row_lo)
            b_ub.append(soc_current - self.config.e_min)
        
        # terminal SOC = 50%
        target_soc = 0.5 * self.config.e_max
        row_final = np.zeros(n_vars)
        for s in range(T):
            row_final[s] = self.config.eta_charge
            row_final[T + s] = -1 / self.config.eta_discharge
        A_eq.append(row_final)
        b_eq.append(target_soc - soc_current)
        
        # ramping constraints
        for t in range(1, T):
            # (Pc[t]-Pd[t]) - (Pc[t-1]-Pd[t-1]) <= ramp
            row1 = np.zeros(n_vars)
            row1[t] = 1;     row1[T+t] = -1
            row1[t-1] = -1;  row1[T+t-1] = 1
            A_ub.append(row1)
            b_ub.append(self.config.ramp_rate)
            
            # reverse direction
            row2 = np.zeros(n_vars)
            row2[t] = -1;    row2[T+t] = 1
            row2[t-1] = 1;   row2[T+t-1] = -1
            A_ub.append(row2)
            b_ub.append(self.config.ramp_rate)
        
        # variable bounds
        bounds = []
        for t in range(T): bounds.append((0, self.config.p_bat_max))  # P_c
        for t in range(T): bounds.append((0, self.config.p_bat_max))  # P_d
        for t in range(T): bounds.append((0, None))   # P_peak
        for t in range(T): bounds.append((0, None))   # P_grid_pos
        for t in range(T): bounds.append((0, None))   # P_grid_neg
        
        A_eq = np.array(A_eq) if A_eq else None
        b_eq = np.array(b_eq) if b_eq else None
        A_ub = np.array(A_ub) if A_ub else None
        b_ub = np.array(b_ub) if b_ub else None
        
        result = linprog(c, A_ub=A_ub, b_ub=b_ub,
                         A_eq=A_eq, b_eq=b_eq,
                         bounds=bounds, method='highs')
        
        if not result.success:
            print("LP warning: %s" % result.message)
            return self._get_fallback_solution(solar_profile, load_profile,
                                                price_profile, initial_soc)
        
        # extract solution
        x = result.x
        P_c = x[0:T]
        P_d = x[T:2*T]
        P_peak = x[2*T:3*T]
        P_grid_pos = x[3*T:4*T]
        P_grid_neg = x[4*T:5*T]
        
        # SOC trajectory
        soc_traj = [initial_soc]
        for t in range(T):
            dsoc = (P_c[t] * self.config.eta_charge - P_d[t] / self.config.eta_discharge) / self.config.e_max
            soc_traj.append(np.clip(soc_traj[-1] + dsoc, self.config.e_min_ratio, 1.0))
        soc_traj = np.array(soc_traj[1:])
        
        P_grid = P_grid_pos - P_grid_neg
        P_bat = P_c - P_d
        
        energy_cost = np.sum(P_grid_pos * price_profile - P_grid_neg * price_profile * self.config.feed_in_ratio)
        peak_pen = np.sum(P_peak * self.config.peak_penalty_rate)
        throughput = np.sum(np.abs(P_c * self.config.eta_charge) + np.abs(P_d / self.config.eta_discharge)) / 2
        deg_cost = throughput * self.config.degradation_cost
        total_cost = energy_cost + peak_pen + deg_cost
        
        return {
            'success': result.success,
            'total_cost': total_cost,
            'energy_cost': energy_cost,
            'peak_penalty': peak_pen,
            'degradation_cost': deg_cost,
            'battery_power': P_bat,
            'grid_power': P_grid,
            'soc_trajectory': soc_traj,
            'charging_power': P_c,
            'discharging_power': P_d,
            'peak_violations': P_peak,
            'throughput': throughput,
            'final_soc': soc_traj[-1],
            'cumulative_cost': np.cumsum(
                P_grid_pos * price_profile - P_grid_neg * price_profile * self.config.feed_in_ratio +
                P_peak * self.config.peak_penalty_rate
            ),
            'solar_profile': solar_profile,
            'load_profile': load_profile,
            'price_profile': price_profile
        }
    
    def _get_fallback_solution(self, solar_profile, load_profile,
                                price_profile, initial_soc):
        """Greedy heuristic fallback when LP fails."""
        T = len(solar_profile)
        net_load = load_profile - solar_profile
        
        soc = initial_soc
        soc_traj = []
        bat_power = []
        grid_power = []
        costs = []
        
        for t in range(T):
            if net_load[t] < 0 and soc < 0.9:
                p = min(-net_load[t], self.config.p_bat_max, (1 - soc) * self.config.e_max)
            elif net_load[t] > 0 and soc > 0.2 and price_profile[t] > 0.15:
                p = -min(net_load[t], self.config.p_bat_max, (soc - self.config.e_min_ratio) * self.config.e_max)
            else:
                p = 0
            
            if p > 0:
                dsoc = p * self.config.eta_charge / self.config.e_max
            else:
                dsoc = p / self.config.eta_discharge / self.config.e_max
            soc = np.clip(soc + dsoc, self.config.e_min_ratio, 1.0)
            
            pg = net_load[t] + p
            if pg >= 0:
                cost = pg * price_profile[t]
            else:
                cost = pg * price_profile[t] * self.config.feed_in_ratio
            cost += max(0, pg - self.config.p_grid_peak) * self.config.peak_penalty_rate
            
            soc_traj.append(soc)
            bat_power.append(p)
            grid_power.append(pg)
            costs.append(cost)
        
        return {
            'success': False,
            'total_cost': sum(costs),
            'energy_cost': sum(c for c, g in zip(costs, grid_power) if g >= 0),
            'peak_penalty': sum(max(0, g - self.config.p_grid_peak) * self.config.peak_penalty_rate for g in grid_power),
            'degradation_cost': 0,
            'battery_power': np.array(bat_power),
            'grid_power': np.array(grid_power),
            'soc_trajectory': np.array(soc_traj),
            'charging_power': np.maximum(bat_power, 0),
            'discharging_power': np.maximum(-np.array(bat_power), 0),
            'peak_violations': np.maximum(np.array(grid_power) - self.config.p_grid_peak, 0),
            'throughput': sum(abs(pp) for pp in bat_power),
            'final_soc': soc,
            'cumulative_cost': np.cumsum(costs),
            'solar_profile': solar_profile,
            'load_profile': load_profile,
            'price_profile': price_profile
        }


def solve_lp_benchmark(solar_profile, load_profile, price_profile,
                       initial_soc=0.5, config=None):
    """Convenience wrapper for LP solve."""
    solver = MicrogridLPSolver(config)
    return solver.solve(solar_profile, load_profile, price_profile, initial_soc)


if __name__ == "__main__":
    from data_loader import get_tou_prices
    
    np.random.seed(42)
    
    solar = np.maximum(0, 5 * np.sin(np.linspace(0, np.pi, 24)))
    load = 3 + 2 * np.sin(np.linspace(0, 2*np.pi, 24) + np.pi/4)
    prices = get_tou_prices()
    
    print("Testing LP Solver...")
    print("Solar: %s..." % str(solar[:6].round(2)))
    print("Load: %s..." % str(load[:6].round(2)))
    print("Prices: %s..." % str(prices[:6]))
    
    result = solve_lp_benchmark(solar, load, prices, initial_soc=0.5)
    
    print("\nLP Solution:")
    print("  Success: %s" % result['success'])
    print("  Total cost: $%.2f" % result['total_cost'])
    print("  Energy cost: $%.2f" % result['energy_cost'])
    print("  Peak penalty: $%.2f" % result['peak_penalty'])
    print("  Final SOC: %.1f%%" % (result['final_soc'] * 100))
    print("  Throughput: %.2f kWh" % result['throughput'])
