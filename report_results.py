# report_results.py
# Quick script to display saved simulation results

import pandas as pd
import matplotlib.pyplot as plt

def report():
    print("RECOVERING SIMULATION RESULTS...")
    
    try:
        df = pd.read_csv("results/evaluation_results.csv")
        print("\n=== EVALUATION SUMMARY ===")
        print(df.to_string(index=False))
    except Exception as e:
        print("Could not load evaluation results: %s" % e)

if __name__ == "__main__":
    report()
