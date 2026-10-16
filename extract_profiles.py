# extract_profiles.py
# Helper to dump the exact solar/load/price profiles from the simulation

import numpy as np
import sys
from main import setup_environment

def extract():
    def print_arr(name, arr):
        vals = ["%.2f" % x for x in arr]
        print("'%s': [%s]," % (name, ', '.join(vals)))

    try:
        solar, load, prices, config = setup_environment(
            "electricityConsumptionAndProductioction.csv", 
            "PecanStreet_10_Homes_1Min_Data.csv"
        )
        
        print("PROFILES = {")
        print_arr('solar', solar)
        print_arr('load', load)
        print_arr('price', prices)
        print("}")
        
    except Exception as e:
        print("Error: %s" % e)

if __name__ == "__main__":
    extract()
