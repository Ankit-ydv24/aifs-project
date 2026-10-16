# visualize_forecast_behavior.py
# Show forecast vs actual (noisy) profiles side by side

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
import os

from microgrid_env import MicrogridEnv, MicrogridConfig
from data_loader import ElectricityDataLoader, get_tou_prices

def visualize_forecast_behavior():
    print("Visualizing Forecast vs Actual Behavior using Real Data...")
    
    data_path = "electricityConsumptionAndProductioction.csv"
    if not os.path.exists(data_path):
        print("Error: Data file %s not found!" % data_path)
        return

    loader = ElectricityDataLoader(data_path)
    daily_profiles = loader.create_daily_profiles()
    
    if not daily_profiles:
        print("Error: No daily profiles created.")
        return
        
    sample = daily_profiles[0]
    forecast_solar = sample['solar_kw']
    forecast_load = sample['load_kw']
    prices = get_tou_prices()
    
    print("Loaded sample day: %s" % sample['date'])
    
    config = MicrogridConfig()
    noise_level = 0.30
    correlation = 0.8
    
    env = MicrogridEnv(
        solar_profile=forecast_solar,
        load_profile=forecast_load,
        price_profile=prices,
        config=config,
        randomize_env=True,
        noise_level=noise_level,
        correlation=correlation
    )
    
    obs, info = env.reset(seed=123)
    
    actual_solar = env.actual_solar_profile
    actual_load = env.actual_load_profile
    
    print("Generating plot...")
    
    plt.style.use('seaborn-v0_8-paper')
    
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8), sharex=True)
    hours = np.linspace(0, 23, 24)
    
    # solar
    ax1.plot(hours, forecast_solar, 'b--', linewidth=2, label='Forecast (Expected)')
    ax1.plot(hours, actual_solar, 'b-', linewidth=2, alpha=0.7, label='Actual (Realized)')
    ax1.fill_between(hours, forecast_solar, actual_solar, alpha=0.2, color='blue', label='Forecast Error')
    ax1.set_ylabel('Solar Generation (kW)', fontsize=12)
    ax1.set_title('Solar: Forecast vs Actual (Noise=%.0f%%)' % (noise_level*100), fontweight='bold', fontsize=14)
    ax1.legend(loc='upper right', frameon=True)
    ax1.grid(True, alpha=0.3)
    ax1.set_ylim(bottom=0)
    
    # load
    ax2.plot(hours, forecast_load, 'r--', linewidth=2, label='Forecast (Expected)')
    ax2.plot(hours, actual_load, 'r-', linewidth=2, alpha=0.7, label='Actual (Realized)')
    ax2.fill_between(hours, forecast_load, actual_load, alpha=0.2, color='red', label='Forecast Error')
    ax2.set_ylabel('Load Consumption (kW)', fontsize=12)
    ax2.set_title('Load: Forecast vs Actual', fontweight='bold', fontsize=14)
    ax2.set_xlabel('Hour of Day', fontsize=12)
    ax2.legend(loc='upper right', frameon=True)
    ax2.grid(True, alpha=0.3)
    ax2.set_xticks(hours)
    ax2.set_ylim(bottom=0)
    
    plt.tight_layout()
    
    os.makedirs("Pages/fig", exist_ok=True)
    save_path = "Pages/fig/forecast_vs_actual.pdf"
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print("Plot saved to %s" % save_path)
    plt.close()

if __name__ == "__main__":
    visualize_forecast_behavior()
