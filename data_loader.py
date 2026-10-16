# data_loader.py
# Load and process energy data for microgrid simulation
# Supports Pecan Street dataset and generic electricity CSV files

import pandas as pd
import numpy as np
import os


class PecanStreetDataLoader:
    """Loads Pecan Street 1-min data and converts to hourly profiles."""
    
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.raw_data = None
        self.processed_data = None
        self.daily_profiles = None
        
    def load_raw_data(self):
        print("Loading data from %s..." % self.csv_path)
        self.raw_data = pd.read_csv(self.csv_path)
        self.raw_data['Datetime (UTC)'] = pd.to_datetime(self.raw_data['Datetime (UTC)'])
        print("Loaded %d rows" % len(self.raw_data))
        print("Homes: %s" % str(self.raw_data['Home ID'].unique()))
        print("Circuits: %s" % str(self.raw_data['Circuit'].unique()))
        print("Date range: %s to %s" % (self.raw_data['Datetime (UTC)'].min(),
                                         self.raw_data['Datetime (UTC)'].max()))
        return self.raw_data
    
    def extract_circuit_data(self, circuit_name):
        """Pull data for one circuit (e.g. 'Solar', 'Main Panel')."""
        if self.raw_data is None:
            self.load_raw_data()
            
        circuit_data = self.raw_data[self.raw_data['Circuit'] == circuit_name].copy()
        circuit_data = circuit_data[['Datetime (UTC)', 'Home ID', 'Value']]
        circuit_data.columns = ['datetime', 'home_id', 'power_kw']
        return circuit_data
    
    def aggregate_to_hourly(self, df):
        """Resample 1-min data to hourly means."""
        df = df.copy()
        df['hour'] = df['datetime'].dt.floor('H')
        df['date'] = df['datetime'].dt.date
        hourly = df.groupby(['date', 'hour', 'home_id'])['power_kw'].mean().reset_index()
        return hourly
    
    def process_data(self):
        """Process raw data -> hourly solar and load profiles."""
        if self.raw_data is None:
            self.load_raw_data()
            
        print("\nProcessing solar generation data...")
        solar_raw = self.extract_circuit_data('Solar')
        solar_raw['power_kw'] = solar_raw['power_kw'].abs()  # make positive
        solar_hourly = self.aggregate_to_hourly(solar_raw)
        
        print("Processing main panel (load) data...")
        load_raw = self.extract_circuit_data('Main Panel')
        load_hourly = self.aggregate_to_hourly(load_raw)
        
        self.processed_data = {
            'solar': solar_hourly,
            'load': load_hourly
        }
        
        print("\nProcessed %d hourly solar records" % len(solar_hourly))
        print("Processed %d hourly load records" % len(load_hourly))
        
        return self.processed_data
    
    def create_daily_profiles(self, home_ids=None):
        """Build list of complete 24h profiles for simulation."""
        if self.processed_data is None:
            self.process_data()
            
        solar_df = self.processed_data['solar']
        load_df = self.processed_data['load']
        
        if home_ids is None:
            home_ids = solar_df['home_id'].unique()
            
        daily_profiles = []
        
        for home_id in home_ids:
            home_solar = solar_df[solar_df['home_id'] == home_id]
            home_load = load_df[load_df['home_id'] == home_id]
            
            dates = home_solar['date'].unique()
            
            for date in dates:
                day_solar = home_solar[home_solar['date'] == date].sort_values('hour')
                day_load = home_load[home_load['date'] == date].sort_values('hour')
                
                if len(day_solar) == 24 and len(day_load) == 24:
                    solar_vals = day_solar['power_kw'].values.astype(np.float32)
                    # zero out nighttime solar
                    for h in range(24):
                        if h < 6 or h >= 20:
                            solar_vals[h] = 0.0
                    
                    daily_profiles.append({
                        'home_id': home_id,
                        'date': date,
                        'solar_kw': solar_vals,
                        'load_kw': day_load['power_kw'].values.astype(np.float32)
                    })
        
        self.daily_profiles = daily_profiles
        print("\nCreated %d complete daily profiles" % len(daily_profiles))
        return daily_profiles
    
    def get_episode_data(self, episode_idx=None):
        if self.daily_profiles is None:
            self.create_daily_profiles()
        if episode_idx is None:
            episode_idx = np.random.randint(0, len(self.daily_profiles))
        else:
            episode_idx = episode_idx % len(self.daily_profiles)
        return self.daily_profiles[episode_idx]
    
    def get_num_episodes(self):
        if self.daily_profiles is None:
            self.create_daily_profiles()
        return len(self.daily_profiles)


class ElectricityDataLoader:
    """Loader for generic electricity consumption/production CSV."""
    
    def __init__(self, csv_path):
        self.csv_path = csv_path
        self.raw_data = None
        self.daily_profiles = None
        
    def load_raw_data(self):
        print("Loading data from %s..." % self.csv_path)
        self.raw_data = pd.read_csv(self.csv_path)
        self.raw_data['DateTime'] = pd.to_datetime(self.raw_data['DateTime'])
        print("Loaded %d rows" % len(self.raw_data))
        print("Date range: %s to %s" % (self.raw_data['DateTime'].min(),
                                         self.raw_data['DateTime'].max()))
        print("Consumption range: %.0f - %.0f W" % (self.raw_data['Consumption'].min(),
                                                      self.raw_data['Consumption'].max()))
        print("Solar range: %.0f - %.0f W" % (self.raw_data['Solar'].min(),
                                                self.raw_data['Solar'].max()))
        return self.raw_data
    
    def process_data(self):
        if self.raw_data is None:
            self.load_raw_data()
        
        self.raw_data['date'] = self.raw_data['DateTime'].dt.date
        self.raw_data['hour'] = self.raw_data['DateTime'].dt.hour
        
        # W -> kW
        self.raw_data['consumption_kw'] = self.raw_data['Consumption'] / 1000.0
        self.raw_data['solar_kw'] = self.raw_data['Solar'] / 1000.0
        
        print("Converted to kW - Consumption: %.2f avg, Solar: %.2f avg" %
              (self.raw_data['consumption_kw'].mean(), self.raw_data['solar_kw'].mean()))
        return self.raw_data
    
    def create_daily_profiles(self):
        if self.raw_data is None or 'consumption_kw' not in self.raw_data.columns:
            self.process_data()
            
        daily_profiles = []
        dates = self.raw_data['date'].unique()
        
        for date in dates:
            day_data = self.raw_data[self.raw_data['date'] == date].sort_values('hour')
            
            if len(day_data) == 24:
                daily_profiles.append({
                    'home_id': 'aggregate',
                    'date': date,
                    'solar_kw': day_data['solar_kw'].values.astype(np.float32),
                    'load_kw': day_data['consumption_kw'].values.astype(np.float32)
                })
        
        self.daily_profiles = daily_profiles
        print("\nCreated %d complete daily profiles" % len(daily_profiles))
        return daily_profiles
    
    def get_episode_data(self, episode_idx=None):
        if self.daily_profiles is None:
            self.create_daily_profiles()
        if episode_idx is None:
            episode_idx = np.random.randint(0, len(self.daily_profiles))
        else:
            episode_idx = episode_idx % len(self.daily_profiles)
        return self.daily_profiles[episode_idx]
    
    def get_num_episodes(self):
        if self.daily_profiles is None:
            self.create_daily_profiles()
        return len(self.daily_profiles)


def get_tou_prices(hours=24):
    """
    Time-of-Use pricing schedule ($/kWh):
      Off-peak  (00-06): 0.08
      Mid-peak  (06-14): 0.15
      On-peak   (14-21): 0.28
      Mid-peak  (21-24): 0.15
    """
    prices = np.zeros(hours, dtype=np.float32)
    
    for h in range(hours):
        if 0 <= h < 6:
            prices[h] = 0.08
        elif 6 <= h < 14:
            prices[h] = 0.15
        elif 14 <= h < 21:
            prices[h] = 0.28
        else:
            prices[h] = 0.15
            
    return prices


def get_feed_in_tariff(hours=24):
    """Feed-in tariff = 40% of retail price."""
    return get_tou_prices(hours) * 0.4


if __name__ == "__main__":
    loader = PecanStreetDataLoader("PecanStreet_10_Homes_1Min_Data.csv")
    loader.load_raw_data()
    loader.process_data()
    profiles = loader.create_daily_profiles()
    
    if profiles:
        sample = profiles[0]
        print("\nSample - Home %s, Date: %s" % (sample['home_id'], sample['date']))
        print("Solar (first 6h): %s" % str(sample['solar_kw'][:6]))
        print("Load (first 6h): %s" % str(sample['load_kw'][:6]))
        
    prices = get_tou_prices()
    print("\nTOU Prices: %s" % str(prices))
