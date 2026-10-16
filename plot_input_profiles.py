# plot_input_profiles.py
# Generate thesis-quality PV and load profile plots

import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import pandas as pd
import os
from main import setup_environment

def set_style():
    sns.set_style("ticks")
    sns.set_context("paper", font_scale=1.5)
    
    plt.rcParams.update({
        'font.family': 'sans-serif',
        'font.size': 12,
        'axes.titlesize': 16,
        'axes.labelsize': 14,
        'xtick.labelsize': 12,
        'ytick.labelsize': 12,
        'legend.fontsize': 12,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'lines.linewidth': 2.5,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'grid.linestyle': '--',
        'grid.alpha': 0.6,
    })

def plot_pv_profile(solar_profile, save_path="pv_profile.pdf"):
    fig, ax = plt.subplots(figsize=(10, 6))
    hours = np.arange(24)
    
    ax.fill_between(hours, 0, solar_profile, color='#f39c12', alpha=0.3)
    ax.plot(hours, solar_profile, color='#e67e22', label='Solar Generation')
    
    peak_h = np.argmax(solar_profile)
    peak_v = solar_profile[peak_h]
    ax.annotate('Peak: %.2f kW' % peak_v, 
                xy=(peak_h, peak_v), xytext=(peak_h, peak_v + 1),
                ha='center', va='bottom',
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5),
                fontweight='bold')

    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Power (kW)')
    ax.set_title('Daily Solar (PV) Generation Profile', fontweight='bold', pad=15)
    ax.set_xlim(0, 23)
    ax.set_ylim(0, max(solar_profile) * 1.2)
    ax.set_xticks(np.arange(0, 25, 4))
    ax.grid(True, axis='y')
    
    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    print("Saved: %s" % save_path)
    plt.close()

def plot_load_profile(load_profile, save_path="load_profile.pdf"):
    fig, ax = plt.subplots(figsize=(10, 6))
    hours = np.arange(24)
    
    ax.fill_between(hours, 0, load_profile, color='#3498db', alpha=0.3)
    ax.plot(hours, load_profile, color='#2980b9', label='Load Consumption')
    
    peak_h = np.argmax(load_profile)
    peak_v = load_profile[peak_h]
    ax.annotate('Peak: %.2f kW' % peak_v, 
                xy=(peak_h, peak_v), xytext=(peak_h, peak_v + 1),
                ha='center', va='bottom',
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5),
                fontweight='bold')

    mean_v = np.mean(load_profile)
    ax.axhline(y=mean_v, color='gray', linestyle='--', alpha=0.8, label='Mean: %.2f kW' % mean_v)

    ax.set_xlabel('Hour of Day')
    ax.set_ylabel('Power (kW)')
    ax.set_title('Daily Load Consumption Profile', fontweight='bold', pad=15)
    ax.set_xlim(0, 23)
    ax.set_ylim(0, max(load_profile) * 1.3)
    ax.set_xticks(np.arange(0, 25, 4))
    ax.legend(loc='upper left')
    ax.grid(True, axis='y')
    
    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    print("Saved: %s" % save_path)
    plt.close()

def plot_combined_profiles(solar_profile, load_profile, save_path="combined_profiles.pdf"):
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 10), sharex=True)
    hours = np.arange(24)
    
    # solar
    ax1.fill_between(hours, 0, solar_profile, color='#f39c12', alpha=0.3)
    ax1.plot(hours, solar_profile, color='#e67e22', label='Solar Generation')
    peak_h = np.argmax(solar_profile)
    peak_v = solar_profile[peak_h]
    ax1.annotate('Peak: %.2f kW' % peak_v, 
                xy=(peak_h, peak_v), xytext=(peak_h, peak_v + 1),
                ha='center', va='bottom',
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5),
                fontweight='bold')
    ax1.set_ylabel('Power (kW)')
    ax1.set_title('Solar (PV) Generation Profile', fontweight='bold')
    ax1.set_ylim(0, max(solar_profile) * 1.2)
    ax1.grid(True, axis='y')
    ax1.legend(loc='upper right')
    
    # load
    ax2.fill_between(hours, 0, load_profile, color='#3498db', alpha=0.3)
    ax2.plot(hours, load_profile, color='#2980b9', label='Load Consumption')
    peak_h = np.argmax(load_profile)
    peak_v = load_profile[peak_h]
    ax2.annotate('Peak: %.2f kW' % peak_v, 
                xy=(peak_h, peak_v), xytext=(peak_h, peak_v + 1),
                ha='center', va='bottom',
                arrowprops=dict(arrowstyle='->', color='black', lw=1.5),
                fontweight='bold')
    mean_v = np.mean(load_profile)
    ax2.axhline(y=mean_v, color='gray', linestyle='--', alpha=0.8, label='Mean: %.2f kW' % mean_v)
    ax2.set_xlabel('Hour of Day')
    ax2.set_ylabel('Power (kW)')
    ax2.set_title('Load Consumption Profile', fontweight='bold')
    ax2.set_xlim(0, 23)
    ax2.set_ylim(0, max(load_profile) * 1.3)
    ax2.set_xticks(np.arange(0, 25, 4))
    ax2.legend(loc='upper left')
    ax2.grid(True, axis='y')
    
    plt.tight_layout()
    plt.savefig(save_path, bbox_inches='tight')
    print("Saved: %s" % save_path)
    plt.close()

def main():
    print("Generating PV and Load Profile Plots...")
    set_style()
    
    DATA_PATH = "electricityConsumptionAndProductioction.csv"
    FALLBACK_DATA_PATH = "PecanStreet_10_Homes_1Min_Data.csv"
    OUTPUT_DIR = "results"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    solar, load, prices, config = setup_environment(DATA_PATH, FALLBACK_DATA_PATH)
    
    plot_pv_profile(solar, "%s/pv_profile.pdf" % OUTPUT_DIR)
    plot_load_profile(load, "%s/load_profile.pdf" % OUTPUT_DIR)
    plot_combined_profiles(solar, load, "%s/input_profiles_combined.pdf" % OUTPUT_DIR)
    
    print("\nDONE.")

if __name__ == "__main__":
    main()
