# Microgrid Energy Management with Reinforcement Learning

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.18859278.svg)](https://doi.org/10.5281/zenodo.18859278)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

A reinforcement learning framework for optimal energy management in residential microgrids with battery energy storage systems (BESS). This project implements and compares multiple RL agents against a Linear Programming (LP) benchmark under various forecast uncertainty conditions.

## Features

- **RL Agents**: Soft Actor-Critic (SAC), Proximal Policy Optimization (PPO), Robust SAC (R-SAC with domain randomization)
- **LP Benchmark**: Optimal deterministic solution via linear programming for baseline comparison
- **Custom Gymnasium Environment**: Realistic microgrid simulation with battery constraints, ramping limits, degradation costs, and time-of-use pricing
- **Robustness Analysis**: Systematic evaluation under varying forecast uncertainty levels (0–30% noise)
- **Comprehensive Visualization**: 13 publication-ready plots (SOC comparison, profit analysis, pricing strategy, robustness, etc.)
- **Real-World Data Support**: Compatible with Pecan Street Dataport and generic electricity consumption/production datasets

## Installation

```bash
# Clone the repository
git clone https://github.com/kerberker/microgrid-rl-energy-management.git
cd microgrid-rl-energy-management

# Create a virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Full Simulation Pipeline

Runs the complete pipeline: environment setup → agent training (SAC, PPO, R-SAC) → evaluation → visualization → robustness testing.

```bash
python main.py
```

### Quick Demo

Runs a reduced version with minimal training steps to quickly test the pipeline.

```bash
python main.py --demo
```

### Robustness Analysis Only

If you have trained models in `results/`, you can run standalone robustness tests:

```bash
python run_robustness_check.py
```

## Project Structure

```
├── main.py                     # Main pipeline (train → evaluate → visualize)
├── microgrid_env.py            # Gymnasium environment (MicrogridEnv, DynamicMicrogridEnv)
├── rl_agents.py                # RL agent wrappers (SAC, PPO, R-SAC, Rule-Based, NoOp)
├── lp_solver.py                # Linear programming benchmark solver
├── data_loader.py              # Data loading (Pecan Street, generic CSV)
├── evaluation.py               # Multi-episode evaluation framework
├── visualization.py            # Publication-ready plot generation
├── robustness_test.py          # Robustness testing under forecast uncertainty
├── run_robustness_check.py     # Standalone robustness test runner
├── plot_results.py             # Additional result plotting utilities
├── plot_input_profiles.py      # Input profile visualization
├── plot_environment_diagram.py # Environment architecture diagram
├── create_duck_curve.py        # Duck curve visualization
├── create_multipanel_plot.py   # Multi-panel comparison plots
├── visualize_forecast_behavior.py  # Forecast error visualization
├── regenerate_plots.py         # Regenerate plots from saved models
├── report_results.py           # Summary report generation
├── extract_profiles.py         # Profile extraction utility
├── requirements.txt            # Python dependencies
├── CITATION.cff                # Citation metadata (Zenodo DOI)
├── .zenodo.json                # Zenodo metadata
├── LICENSE                     # MIT License
├── Pages/                      # LaTeX thesis chapters and figures
└── results/                    # Output directory (generated)
    ├── *.pdf                   # Visualization plots
    ├── *.csv                   # Evaluation results
    └── *.zip / *.pkl           # Trained models (not tracked by Git)
```

## Data

This project supports two data sources:

1. **Pecan Street Dataport** (`PecanStreet_10_Homes_1Min_Data.csv`): 1-minute resolution residential solar and load data
2. **Generic electricity data** (`electricityConsumptionAndProductioction.csv`): Consumption and production profiles

> **Note:** Data files are not included in the repository due to size constraints. Place your data files in the project root directory. If no data is found, the system will use synthetic profiles.

## Environment Configuration

The microgrid is configured with a Tesla Powerwall-like battery system:

| Parameter | Value | Description |
|-----------|-------|-------------|
| Battery Capacity | 13.5 kWh | Maximum energy storage |
| Max Power | 5.0 kW | Charge/discharge rate |
| Efficiency | 95% | Round-trip charge/discharge |
| Ramp Rate | 2.5 kW/h | Maximum power change rate |
| Peak Threshold | 10.0 kW | Grid demand threshold |
| Forecast Horizon | 24 h | Look-ahead window |

## Citation

If you use this software in your research, please cite it:

```bibtex
@software{microgrid_rl_2026,
  author       = {Cetinkaya, Berker},
  title        = {Microgrid Energy Management with Reinforcement Learning},
  year         = {2026},
  publisher    = {Zenodo},
  doi          = {10.5281/zenodo.18859278},
  url          = {https://doi.org/10.5281/zenodo.18859278}
}
```

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
