# build_dashboard.py
# Injects the real extracted results into dashboard.html

import json
from pathlib import Path

def build_dashboard():
    with open('results/dashboard_data.json') as f:
        data = json.load(f)

    json_str = json.dumps(data)

    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Microgrid RL Energy Dashboard — Trained Results</title>
  <meta name="description" content="Interactive 3D visualization of reinforcement learning microgrid energy management wired to actual trained models." />

  <!-- Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com" />
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;600;700&display=swap" rel="stylesheet" />

  <!-- Three.js & Chart.js -->
  <script src="https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js"></script>
  <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>

  <style>
    :root {{
      --bg: #050a18;
      --surface: #0b1629;
      --surface2: #0f1e38;
      --border: rgba(100,160,255,0.12);
      --accent: #3b82f6;
      --accent2: #8b5cf6;
      --solar: #f59e0b;
      --load: #ef4444;
      --battery: #10b981;
      --grid: #6366f1;
      --text: #e2e8f0;
      --muted: #64748b;
      --glow: 0 0 30px rgba(59,130,246,0.25);
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Inter', sans-serif; background: var(--bg); color: var(--text); overflow-x: hidden; min-height: 100vh; }}

    header {{
      padding: 14px 28px;
      display: flex; align-items: center; justify-content: space-between;
      background: linear-gradient(90deg, rgba(11,22,41,0.98), rgba(15,30,56,0.92));
      border-bottom: 1px solid var(--border);
      backdrop-filter: blur(12px);
      position: sticky; top: 0; z-index: 100;
    }}
    .logo {{ display: flex; align-items: center; gap: 12px; }}
    .logo-icon {{ width: 38px; height: 38px; background: linear-gradient(135deg, var(--accent), var(--accent2)); border-radius: 9px; display: flex; align-items: center; justify-content: center; font-size: 20px; box-shadow: var(--glow); }}
    .logo-text {{ font-size: 1.15rem; font-weight: 700; letter-spacing: -0.02em; }}
    .logo-sub {{ font-size: 0.72rem; color: var(--muted); letter-spacing: 0.05em; text-transform: uppercase; }}
    .header-controls {{ display: flex; gap: 10px; align-items: center; }}
    .badge {{ padding: 5px 12px; border-radius: 999px; font-size: 0.72rem; font-weight: 600; letter-spacing: 0.05em; text-transform: uppercase; border: 1px solid; }}
    .badge-blue {{ background: rgba(59,130,246,0.12); color: #60a5fa; border-color: rgba(59,130,246,0.3); }}
    .badge-green {{ background: rgba(16,185,129,0.12); color: #34d399; border-color: rgba(16,185,129,0.3); }}
    .badge-purple {{ background: rgba(139,92,246,0.12); color: #c4b5fd; border-color: rgba(139,92,246,0.3); }}
    .badge-amber {{ background: rgba(245,158,11,0.12); color: #fbbf24; border-color: rgba(245,158,11,0.3); }}

    .main-grid {{
      display: grid;
      grid-template-columns: 1fr 410px;
      grid-template-rows: 460px auto auto;
      gap: 16px;
      padding: 16px 22px;
      max-width: 1650px; margin: 0 auto;
    }}

    .three-panel {{
      grid-row: 1; grid-column: 1;
      border-radius: 16px; border: 1px solid var(--border);
      background: var(--surface); position: relative; overflow: hidden;
      box-shadow: var(--glow);
    }}
    #three-canvas {{ width: 100%; height: 100%; display: block; }}
    .scene-overlay {{ position: absolute; top: 0; left: 0; right: 0; bottom: 0; pointer-events: none; }}
    .scene-label {{ position: absolute; top: 14px; left: 16px; font-size: 0.74rem; font-weight: 600; color: #94a3b8; letter-spacing: 0.08em; text-transform: uppercase; background: rgba(5,10,24,0.7); padding: 4px 10px; border-radius: 6px; border: 1px solid var(--border); }}
    .energy-flows {{ position: absolute; bottom: 14px; left: 14px; right: 14px; display: flex; gap: 8px; }}
    .flow-pill {{ background: rgba(5,10,24,0.88); border: 1px solid var(--border); border-radius: 8px; padding: 7px 12px; font-size: 0.74rem; backdrop-filter: blur(8px); display: flex; align-items: center; gap: 7px; flex: 1; justify-content: center; }}
    .flow-dot {{ width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }}

    .control-panel {{
      grid-row: 1; grid-column: 2;
      border-radius: 16px; border: 1px solid var(--border);
      background: var(--surface); padding: 18px;
      display: flex; flex-direction: column; gap: 13px;
      overflow-y: auto;
    }}
    .panel-title {{ font-size: 0.68rem; font-weight: 700; color: var(--muted); letter-spacing: 0.1em; text-transform: uppercase; margin-bottom: 2px; display: flex; justify-content: space-between; align-items: center; }}
    .time-display {{ font-family: 'JetBrains Mono', monospace; font-size: 2.2rem; font-weight: 700; color: #fff; letter-spacing: -0.02em; line-height: 1; }}
    .time-sub {{ font-size: 0.78rem; color: var(--muted); margin-top: 4px; }}
    .scrubber {{ -webkit-appearance: none; appearance: none; width: 100%; height: 5px; background: linear-gradient(90deg, var(--accent) var(--pct, 0%), rgba(100,116,139,0.3) var(--pct, 0%)); border-radius: 4px; outline: none; cursor: pointer; margin-top: 10px; }}
    .scrubber::-webkit-slider-thumb {{ -webkit-appearance: none; width: 16px; height: 16px; border-radius: 50%; background: var(--accent); box-shadow: 0 0 0 3px rgba(59,130,246,0.3); cursor: pointer; }}
    .playback-controls {{ display: flex; gap: 8px; margin-top: 8px; }}
    .ctrl-btn {{ flex: 1; padding: 7px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface2); color: var(--text); font-size: 0.78rem; font-weight: 600; cursor: pointer; transition: all 0.2s; }}
    .ctrl-btn:hover {{ background: var(--accent); border-color: var(--accent); color: #fff; }}
    .ctrl-btn.active {{ background: var(--accent); border-color: var(--accent); color: #fff; }}

    .agent-selector {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 6px; }}
    .agent-btn {{ padding: 7px 6px; border-radius: 8px; border: 1px solid var(--border); background: var(--surface2); color: var(--muted); font-size: 0.74rem; font-weight: 600; cursor: pointer; transition: all 0.2s; text-align: center; }}
    .agent-btn:hover {{ color: #fff; border-color: rgba(100,160,255,0.3); }}
    .agent-btn.selected {{ border-color: var(--accent2); background: rgba(139,92,246,0.18); color: #c4b5fd; box-shadow: 0 0 12px rgba(139,92,246,0.25); }}

    .agent-status-card {{ background: rgba(139,92,246,0.08); border: 1px solid rgba(139,92,246,0.25); border-radius: 8px; padding: 8px 10px; font-size: 0.72rem; line-height: 1.4; }}
    .agent-status-title {{ font-weight: 700; color: #c4b5fd; display: flex; justify-content: space-between; }}

    .kpi-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }}
    .kpi-card {{ background: var(--surface2); border: 1px solid var(--border); border-radius: 10px; padding: 10px; }}
    .kpi-label {{ font-size: 0.65rem; color: var(--muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; }}
    .kpi-value {{ font-family: 'JetBrains Mono', monospace; font-size: 1.2rem; font-weight: 700; margin-top: 3px; line-height: 1; }}
    .kpi-unit {{ font-size: 0.67rem; color: var(--muted); margin-top: 2px; }}

    .soc-bar-outer {{ height: 12px; border-radius: 6px; background: rgba(100,116,139,0.2); overflow: hidden; margin-top: 8px; }}
    .soc-bar-inner {{ height: 100%; border-radius: 6px; background: linear-gradient(90deg, var(--battery), #6ee7b7); transition: width 0.3s ease; box-shadow: 0 0 10px rgba(16,185,129,0.4); }}
    .soc-labels {{ display: flex; justify-content: space-between; font-size: 0.66rem; color: var(--muted); margin-top: 3px; }}
    .divider {{ height: 1px; background: var(--border); }}
    .info-row {{ display: flex; justify-content: space-between; align-items: center; padding: 4px 0; font-size: 0.76rem; }}
    .info-row-label {{ color: var(--muted); }}
    .info-row-val {{ font-family: 'JetBrains Mono', monospace; font-weight: 600; }}

    .charts-row {{ grid-column: 1 / -1; display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 16px; }}
    .chart-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 16px; }}
    .chart-title {{ font-size: 0.74rem; font-weight: 700; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; justify-content: space-between; }}
    .chart-title-left {{ display: flex; align-items: center; gap: 8px; }}
    .chart-dot {{ width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }}
    .chart-canvas-wrap {{ height: 180px; position: relative; }}

    .table-section {{ grid-column: 1 / -1; background: var(--surface); border: 1px solid var(--border); border-radius: 16px; padding: 18px; margin-bottom: 30px; }}
    .table-title {{ font-size: 0.85rem; font-weight: 700; color: #fff; margin-bottom: 12px; display: flex; align-items: center; gap: 8px; }}
    .leaderboard {{ width: 100%; border-collapse: collapse; font-size: 0.8rem; text-align: left; }}
    .leaderboard th {{ padding: 10px 14px; background: var(--surface2); color: #94a3b8; font-weight: 600; text-transform: uppercase; font-size: 0.68rem; letter-spacing: 0.05em; border-bottom: 1px solid var(--border); }}
    .leaderboard td {{ padding: 11px 14px; border-bottom: 1px solid rgba(100,160,255,0.06); font-family: 'JetBrains Mono', monospace; }}
    .leaderboard tr:hover td {{ background: rgba(59,130,246,0.04); }}
    .tag {{ padding: 3px 8px; border-radius: 4px; font-size: 0.68rem; font-weight: 700; display: inline-block; }}
    .tag-rank1 {{ background: rgba(16,185,129,0.2); color: #34d399; border: 1px solid rgba(16,185,129,0.4); }}
    .tag-rank2 {{ background: rgba(139,92,246,0.2); color: #c4b5fd; border: 1px solid rgba(139,92,246,0.4); }}
    .tag-rank3 {{ background: rgba(59,130,246,0.2); color: #60a5fa; border: 1px solid rgba(59,130,246,0.4); }}

    #particle-canvas {{ position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; opacity: 0.25; }}

    @keyframes pulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
    .pulse {{ animation: pulse 2s infinite; }}
  </style>
</head>
<body>

<canvas id="particle-canvas"></canvas>

<header>
  <div class="logo">
    <div class="logo-icon">⚡</div>
    <div>
      <div class="logo-text">MicroGrid RL</div>
      <div class="logo-sub">Reinforcement Learning Energy Management</div>
    </div>
  </div>
  <div class="header-controls">
    <span class="badge badge-green pulse">● Trained Models Wired</span>
    <span class="badge badge-purple">100-Episode Benchmark</span>
    <span class="badge badge-blue">SAC · R-SAC · PPO · LP</span>
    <span class="badge badge-amber">Tesla Powerwall 13.5 kWh</span>
  </div>
</header>

<div class="main-grid">

  <!-- 3D Scene Panel -->
  <div class="three-panel" id="three-panel">
    <canvas id="three-canvas"></canvas>
    <div class="scene-overlay">
      <div class="scene-label">Microgrid 3D Twin — Interactive (drag to orbit)</div>
      <div class="energy-flows">
        <div class="flow-pill">
          <div class="flow-dot" style="background:#f59e0b;box-shadow:0 0 6px #f59e0b"></div>
          Solar: <strong id="flow-solar">0.00</strong> kW
        </div>
        <div class="flow-pill">
          <div class="flow-dot" style="background:#ef4444;box-shadow:0 0 6px #ef4444"></div>
          Load: <strong id="flow-load">0.00</strong> kW
        </div>
        <div class="flow-pill">
          <div class="flow-dot" style="background:#10b981;box-shadow:0 0 6px #10b981"></div>
          Battery: <strong id="flow-battery">0.00</strong> kW
        </div>
        <div class="flow-pill">
          <div class="flow-dot" style="background:#6366f1;box-shadow:0 0 6px #6366f1"></div>
          Grid Net: <strong id="flow-grid">0.00</strong> kW
        </div>
      </div>
    </div>
  </div>

  <!-- Control Panel -->
  <div class="control-panel">
    <div>
      <div class="panel-title">
        <span>Simulation Time</span>
        <span id="price-tariff-badge" class="tag" style="background:rgba(245,158,11,0.15);color:#fbbf24;border:1px solid rgba(245,158,11,0.3)">Off-Peak</span>
      </div>
      <div class="time-display" id="time-display">00:00</div>
      <div class="time-sub">Hour <span id="hour-num">0</span> of 24 — <span id="period-label">Night</span></div>
      <input type="range" min="0" max="23" value="0" id="time-scrubber" class="scrubber" />
      <div class="playback-controls">
        <button class="ctrl-btn" onclick="stepTime(-1)">◀ Prev</button>
        <button class="ctrl-btn active" id="btn-play" onclick="togglePlay()">⏸ Pause</button>
        <button class="ctrl-btn" onclick="stepTime(1)">Next ▶</button>
        <button class="ctrl-btn" id="btn-speed" onclick="cycleSpeed()">1×</button>
      </div>
    </div>

    <div class="divider"></div>

    <div>
      <div class="panel-title">Select Agent Policy</div>
      <div class="agent-selector">
        <button class="agent-btn" id="agent-LP" onclick="selectAgent('LP')">LP Optimal</button>
        <button class="agent-btn selected" id="agent-RSAC" onclick="selectAgent('R-SAC')">R-SAC ★</button>
        <button class="agent-btn" id="agent-SAC" onclick="selectAgent('SAC')">SAC</button>
        <button class="agent-btn" id="agent-PPO" onclick="selectAgent('PPO')">PPO</button>
        <button class="agent-btn" id="agent-Rule" onclick="selectAgent('Rule-Based')">Rule-Based</button>
        <button class="agent-btn" id="agent-NoOp" onclick="selectAgent('NoOp')">NoOp</button>
      </div>
    </div>

    <div class="agent-status-card" id="agent-status-card">
      <div class="agent-status-title">
        <span id="agent-card-name">R-SAC (Robust Soft Actor-Critic)</span>
        <span id="agent-card-rank" class="tag tag-rank2">Rank #1 RL</span>
      </div>
      <div style="color:var(--muted);margin-top:4px" id="agent-card-desc">
        Trained with AR(1) domain randomization up to 30% forecast noise. Highest performing RL policy.
      </div>
    </div>

    <div class="divider"></div>

    <div>
      <div class="panel-title">Battery State of Charge (SoC)</div>
      <div style="display:flex;justify-content:space-between;align-items:baseline;margin-top:4px">
        <div style="font-size:1.6rem;font-weight:700;font-family:'JetBrains Mono',monospace" id="soc-pct">50%</div>
        <div style="font-size:0.76rem;color:var(--muted)" id="soc-kwh">6.75 / 13.5 kWh</div>
      </div>
      <div class="soc-bar-outer"><div class="soc-bar-inner" id="soc-bar" style="width:50%"></div></div>
      <div class="soc-labels"><span>10% min limit</span><span>50%</span><span>100% full</span></div>
    </div>

    <div class="divider"></div>

    <div>
      <div class="panel-title">Real-Time Step Metrics</div>
      <div class="kpi-grid">
        <div class="kpi-card">
          <div class="kpi-label">Cumulative Profit</div>
          <div class="kpi-value" id="kpi-profit" style="color:#60a5fa">-$0.199</div>
          <div class="kpi-unit">Total at this hour</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Hourly Cost</div>
          <div class="kpi-value" id="kpi-step-cost" style="color:#f87171">$0.199</div>
          <div class="kpi-unit">Step grid + deg cost</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">Battery Power</div>
          <div class="kpi-value" id="kpi-bat" style="color:#34d399">+0.24 kW</div>
          <div class="kpi-unit" id="bat-flow-dir">Charging</div>
        </div>
        <div class="kpi-card">
          <div class="kpi-label">TOU Price</div>
          <div class="kpi-value" id="kpi-price" style="color:#fbbf24">$0.08</div>
          <div class="kpi-unit">/kWh rate</div>
        </div>
      </div>
    </div>

    <div class="divider"></div>

    <div>
      <div class="panel-title">Grid & Physical Exchange</div>
      <div class="info-row"><span class="info-row-label">Net grid exchange</span><span class="info-row-val" id="info-grid">+3.16 kW (Import)</span></div>
      <div class="info-row"><span class="info-row-label">Solar PV generation</span><span class="info-row-val" id="info-solar" style="color:#fbbf24">0.00 kW</span></div>
      <div class="info-row"><span class="info-row-label">Household demand</span><span class="info-row-val" id="info-load" style="color:#f87171">3.02 kW</span></div>
      <div class="info-row"><span class="info-row-label">Gap vs LP Benchmark</span><span class="info-row-val" id="info-gap" style="color:#c4b5fd">20.6%</span></div>
    </div>

  </div>

  <!-- Charts Row -->
  <div class="charts-row">
    <div class="chart-card">
      <div class="chart-title">
        <div class="chart-title-left"><div class="chart-dot" style="background:var(--battery)"></div>State of Charge (SOC) — 24h</div>
        <span style="font-size:0.68rem;color:var(--muted)">All Trained Agents</span>
      </div>
      <div class="chart-canvas-wrap"><canvas id="chart-soc"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">
        <div class="chart-title-left"><div class="chart-dot" style="background:var(--solar)"></div>Power Profiles — <span id="power-chart-agent">R-SAC</span></div>
        <span style="font-size:0.68rem;color:var(--muted)">kW / Hour</span>
      </div>
      <div class="chart-canvas-wrap"><canvas id="chart-power"></canvas></div>
    </div>
    <div class="chart-card">
      <div class="chart-title">
        <div class="chart-title-left"><div class="chart-dot" style="background:var(--accent)"></div>100-Episode Mean Profit Benchmark</div>
        <span style="font-size:0.68rem;color:var(--muted)">LP Gap Comparison</span>
      </div>
      <div class="chart-canvas-wrap"><canvas id="chart-compare"></canvas></div>
    </div>
  </div>

  <!-- Leaderboard Table -->
  <div class="table-section">
    <div class="table-title">
      <span>🏆 100-Episode Evaluation Leaderboard & Performance Summary</span>
    </div>
    <table class="leaderboard">
      <thead>
        <tr>
          <th>Agent</th>
          <th>Mean Profit ($)</th>
          <th>Profit Std Dev</th>
          <th>Gap vs LP (%)</th>
          <th>Energy Profit ($)</th>
          <th>Peak Penalty ($)</th>
          <th>Throughput (kWh)</th>
          <th>Final SoC</th>
          <th>Eval Time (s)</th>
        </tr>
      </thead>
      <tbody id="leaderboard-body">
        <!-- populated dynamically -->
      </tbody>
    </table>
  </div>

</div>

<script>
// =============================================
// WIRED REAL RESULTS DATASET
// =============================================
const DATA = {json_str};

const HOURS = DATA.hours;
const LABELS = DATA.labels;
const solar = DATA.solar;
const load = DATA.load;
const prices = DATA.prices;
const agents = DATA.agents;
const summary = DATA.summary;

const AGENT_COLORS = {{
  'LP': '#2ecc71',
  'R-SAC': '#8b5cf6',
  'SAC': '#3b82f6',
  'PPO': '#ef4444',
  'NoOp': '#64748b',
  'Rule-Based': '#f59e0b'
}};

const AGENT_DESCRIPTIONS = {{
  'LP': {{ name: 'LP Benchmark (Linear Programming)', rank: 'Benchmark (0% Gap)', desc: 'Deterministic optimal upper bound computed using linear programming. Zero peak penalties and exact degradation minimization.' }},
  'R-SAC': {{ name: 'R-SAC (Robust Soft Actor-Critic)', rank: 'Rank #1 RL (+20.6%)', desc: 'Trained with AR(1) correlated forecast noise and domain randomization. Closest to LP optimal with highest mean profit among all RL models.' }},
  'SAC': {{ name: 'SAC (Soft Actor-Critic)', rank: 'Rank #2 RL (+33.1%)', desc: 'Maximum entropy off-policy RL agent. Learns robust arbitrage under clean forecasts with minimal peak violations.' }},
  'PPO': {{ name: 'PPO (Proximal Policy Optimization)', rank: 'Rank #3 RL (+164.8%)', desc: 'On-policy policy gradient agent. Requires observation & reward normalization, exhibits higher cycling throughput.' }},
  'Rule-Based': {{ name: 'Rule-Based Baseline', rank: 'Heuristic (+1036.6%)', desc: 'Rule-based threshold dispatch: charges when solar > load, discharges when price is high. Incurs heavy terminal SoC degradation penalties.' }},
  'NoOp': {{ name: 'No-Op (Zero Battery Dispatch)', rank: 'Passive (+460.4%)', desc: 'Zero battery action (throughput = 0 kWh). Represents purely passive grid exchange without energy storage.' }}
}};

// State
let currentHour = 0;
let selectedAgent = 'R-SAC';
let playing = true;
let speedIdx = 1;
const SPEEDS = [0.5, 1, 2, 4];

// =============================================
// THREE.JS 3D TWIN
// =============================================
const canvas3d = document.getElementById('three-canvas');
const panel3d = document.getElementById('three-panel');
const renderer = new THREE.WebGLRenderer({{ canvas: canvas3d, antialias: true, alpha: true }});
renderer.setPixelRatio(window.devicePixelRatio);
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;

const scene = new THREE.Scene();
scene.fog = new THREE.Fog(0x050a18, 22, 55);

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100);
camera.position.set(16, 10, 18);
camera.lookAt(0, 1.2, 0);

function resize3D() {{
  const w = panel3d.clientWidth, h = panel3d.clientHeight;
  renderer.setSize(w, h);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
}}
resize3D();
window.addEventListener('resize', resize3D);

// Lights
scene.add(new THREE.AmbientLight(0x16243b, 3));
const dirLight = new THREE.DirectionalLight(0x6699ff, 2.5);
dirLight.position.set(8, 14, 6);
dirLight.castShadow = true;
scene.add(dirLight);

const fillLight = new THREE.PointLight(0xfcd34d, 1.5, 30);
fillLight.position.set(-5, 6, 5);
scene.add(fillLight);

// Ground
const gnd = new THREE.Mesh(
  new THREE.PlaneGeometry(50, 50),
  new THREE.MeshStandardMaterial({{ color: 0x0a1628, roughness: 0.95 }})
);
gnd.rotation.x = -Math.PI / 2;
gnd.receiveShadow = true;
scene.add(gnd);
scene.add(new THREE.GridHelper(30, 20, 0x0d1828, 0x0d1828));

function makeBox(w, h, d, c, m=0.3, r=0.6) {{
  return new THREE.Mesh(
    new THREE.BoxGeometry(w, h, d),
    new THREE.MeshStandardMaterial({{ color: c, metalness: m, roughness: r }})
  );
}}

// === SOLAR ARRAY ===
const solarG = new THREE.Group();
solarG.position.set(-7, 0, -4);
const panBase = makeBox(6, 0.14, 4, 0x1a2545, 0.4, 0.5);
panBase.position.y = 1.3;
panBase.rotation.x = -0.28;
solarG.add(panBase);

for (let r = 0; r < 3; r++) {{
  for (let c = 0; c < 6; c++) {{
    const cell = makeBox(0.85, 0.05, 0.56, 0x1e3a6e, 0.6, 0.2);
    cell.position.set(-2.3 + c * 0.96, 1.38, -0.84 + r * 0.96);
    cell.rotation.x = -0.28;
    solarG.add(cell);
    const edge = new THREE.Mesh(
      new THREE.BoxGeometry(0.83, 0.015, 0.54),
      new THREE.MeshBasicMaterial({{ color: 0x60a5fa }})
    );
    edge.position.set(-2.3 + c * 0.96, 1.42, -0.84 + r * 0.96);
    edge.rotation.x = -0.28;
    solarG.add(edge);
  }}
}}
[-2, 2].forEach(x => {{
  const leg = makeBox(0.12, 1.5, 0.12, 0x334155, 0.7, 0.3);
  leg.position.set(x, 0.72, 0);
  solarG.add(leg);
}});
scene.add(solarG);

// === BATTERY TOWER (Powerwall) ===
const battG = new THREE.Group();
battG.position.set(0, 0, 0);
battG.add(makeBox(2, 0.2, 1.5, 0x1e293b, 0.5, 0.4));
const bBody = makeBox(1.8, 4, 1.3, 0x0f2a1f, 0.4, 0.5);
bBody.position.y = 2.2;
bBody.castShadow = true;
battG.add(bBody);

const bSegs = [];
for (let i = 0; i < 8; i++) {{
  const seg = makeBox(1.4, 0.32, 0.06, 0x10b981, 0.2, 0.5);
  seg.position.set(0, 0.38 + i * 0.44, 0.68);
  battG.add(seg);
  bSegs.push(seg);
}}
const battGlowL = new THREE.PointLight(0x10b981, 1.2, 6);
battGlowL.position.set(0, 2.2, 1.2);
battG.add(battGlowL);

const screen = makeBox(1.2, 0.6, 0.04, 0x0a2a1a, 0.1, 0.5);
screen.position.set(0, 3.6, 0.68);
battG.add(screen);
scene.add(battG);

// === HOUSE ===
const houseG = new THREE.Group();
houseG.position.set(6, 0, -1);
const hBody = makeBox(2.8, 2.4, 2.4, 0x1e1b4b, 0.2, 0.8);
hBody.position.y = 1.2;
hBody.castShadow = true;
houseG.add(hBody);

const roofMesh = new THREE.Mesh(
  new THREE.ConeGeometry(2.15, 1.4, 4),
  new THREE.MeshStandardMaterial({{ color: 0x3730a3, metalness: 0.3, roughness: 0.6 }})
);
roofMesh.position.y = 3.1;
roofMesh.rotation.y = Math.PI / 4;
roofMesh.castShadow = true;
houseG.add(roofMesh);

const windowLights = [];
[[-0.7, 1.2], [0.7, 1.2]].forEach(([x, y]) => {{
  const win = makeBox(0.65, 0.65, 0.05, 0xfef3c7, 0.1, 0.1);
  win.position.set(x, y, 1.22);
  houseG.add(win);
  const wg = new THREE.PointLight(0xfef3c7, 0.35, 2.5);
  wg.position.set(x, y, 1.5);
  houseG.add(wg);
  windowLights.push(wg);
}});
const door = makeBox(0.6, 0.9, 0.04, 0x2d1b4e, 0.2, 0.9);
door.position.set(0, 0.45, 1.22);
houseG.add(door);
scene.add(houseG);

// === GRID PYLON ===
const gridG = new THREE.Group();
gridG.position.set(-2, 0, 6);
gridG.add(makeBox(1.2, 0.2, 1.2, 0x334155, 0.6, 0.4));
const pole = makeBox(0.18, 5.5, 0.18, 0x475569, 0.6, 0.4);
pole.position.y = 2.85;
gridG.add(pole);

[[-0.3, 0], [0.3, 0]].forEach(([dx, dy]) => {{
  const arm = makeBox(3, 0.1, 0.1, 0x475569, 0.6, 0.4);
  arm.position.set(0, 5 + dx, 0);
  gridG.add(arm);
  [-1.2, 1.2].forEach(x => {{
    const ins = makeBox(0.1, 0.28, 0.1, 0xfef3c7, 0.1, 0.9);
    ins.position.set(x, 4.85 + dx, 0);
    gridG.add(ins);
  }});
}});
const gridGlowL = new THREE.PointLight(0x818cf8, 1.4, 10);
gridGlowL.position.set(0, 3.5, 0);
gridG.add(gridGlowL);
scene.add(gridG);

// === CONNECTING POWER WIRES ===
function makeLine(from, to, color) {{
  const geo = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(...from), new THREE.Vector3(...to)]);
  const mat = new THREE.LineBasicMaterial({{ color, transparent: true, opacity: 0.6 }});
  const l = new THREE.Line(geo, mat);
  scene.add(l);
  return l;
}}

const lines = {{
  solar_to_bat: makeLine([-7, 1.3, -4], [0, 2.2, 0], 0xf59e0b),
  bat_to_house: makeLine([0.9, 2.2, 0], [6, 2, -1], 0x10b981),
  grid_to_house: makeLine([-2, 2, 6], [6, 2, -1], 0x6366f1),
}};

// === ANIMATED PARTICLES ===
function makeParticles(from, to, color, n=12) {{
  const pos = new Float32Array(n * 3);
  const geo = new THREE.BufferGeometry();
  geo.setAttribute('position', new THREE.BufferAttribute(pos, 3));
  const mat = new THREE.PointsMaterial({{ color, size: 0.2, transparent: true, opacity: 0.9 }});
  const ps = new THREE.Points(geo, mat);
  scene.add(ps);
  return {{ from, to, geo, mat, offset: Math.random(), n, dir: 1 }};
}}

const particles = [
  makeParticles([-7, 1.3, -4], [0, 2.2, 0], 0xfcd34d, 12),  // solar -> battery
  makeParticles([0.9, 2.2, 0], [6, 2, -1], 0x6ee7b7, 12),   // battery <-> house
  makeParticles([-2, 2, 6], [6, 2, -1], 0x818cf8, 12),      // grid <-> house
];

// =============================================
// CHART.JS CONFIGURATION
// =============================================
const CD = {{
  responsive: true, maintainAspectRatio: false,
  plugins: {{
    legend: {{ labels: {{ color: '#94a3b8', font: {{ family: 'Inter', size: 10 }}, boxWidth: 10, padding: 8 }} }},
    tooltip: {{ backgroundColor: 'rgba(11,22,41,0.95)', borderColor: 'rgba(100,160,255,0.2)', borderWidth: 1, titleColor: '#e2e8f0', bodyColor: '#94a3b8', padding: 10 }}
  }},
  scales: {{
    x: {{ ticks: {{ color: '#475569', font: {{ size: 9 }}, maxTicksLimit: 7 }}, grid: {{ color: 'rgba(100,160,255,0.05)' }}, border: {{ color: 'rgba(100,160,255,0.08)' }} }},
    y: {{ ticks: {{ color: '#475569', font: {{ size: 9 }} }}, grid: {{ color: 'rgba(100,160,255,0.05)' }}, border: {{ color: 'rgba(100,160,255,0.08)' }} }}
  }}
}};

// 1. SOC Trajectory Chart
const socDatasets = Object.keys(agents).map(name => ({{
  label: name,
  data: agents[name].soc,
  borderColor: AGENT_COLORS[name],
  backgroundColor: 'transparent',
  borderWidth: name === selectedAgent ? 2.8 : 1.2,
  pointRadius: 0,
  tension: 0.3
}}));

const socChart = new Chart(document.getElementById('chart-soc'), {{
  type: 'line',
  data: {{ labels: LABELS, datasets: socDatasets }},
  options: {{
    ...CD,
    plugins: {{
      ...CD.plugins,
      legend: {{ position: 'top', labels: {{ boxWidth: 8, padding: 6, font: {{ size: 9 }} }} }}
    }},
    scales: {{
      ...CD.scales,
      y: {{ ...CD.scales.y, min: 0, max: 1.05, ticks: {{ ...CD.scales.y.ticks, callback: v => (v * 100).toFixed(0) + '%' }} }}
    }}
  }},
  plugins: [{{
    afterDraw: (chart) => {{
      const {{ ctx, chartArea: {{ top, bottom }}, scales: {{ x }} }} = chart;
      const xp = x.getPixelForValue(currentHour);
      ctx.save();
      ctx.strokeStyle = 'rgba(251,191,36,0.85)';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      ctx.moveTo(xp, top); ctx.lineTo(xp, bottom);
      ctx.stroke();
      ctx.restore();
    }}
  }}]
}});

// 2. Power Profiles Chart
const powerChart = new Chart(document.getElementById('chart-power'), {{
  type: 'line',
  data: {{
    labels: LABELS,
    datasets: [
      {{ label: 'Solar PV', data: solar, borderColor: '#f59e0b', backgroundColor: 'rgba(245,158,11,0.08)', fill: true, tension: 0.3, borderWidth: 2, pointRadius: 0 }},
      {{ label: 'Load', data: load, borderColor: '#ef4444', backgroundColor: 'rgba(239,68,68,0.08)', fill: true, tension: 0.3, borderWidth: 2, pointRadius: 0 }},
      {{ label: 'Net Grid', data: agents[selectedAgent].grid, borderColor: '#6366f1', borderDash: [4, 4], tension: 0.3, borderWidth: 1.6, pointRadius: 0 }},
      {{ label: 'Battery Dispatch', data: agents[selectedAgent].bat, borderColor: '#10b981', tension: 0.3, borderWidth: 1.8, pointRadius: 0 }}
    ]
  }},
  options: {{
    ...CD,
    scales: {{
      ...CD.scales,
      y: {{ ...CD.scales.y, ticks: {{ ...CD.scales.y.ticks, callback: v => v + ' kW' }} }}
    }}
  }}
}});

// 3. 100-Episode Mean Profit Comparison
const compAgents = ['LP', 'R-SAC', 'SAC', 'PPO', 'Rule-Based', 'NoOp'];
const compChart = new Chart(document.getElementById('chart-compare'), {{
  type: 'bar',
  data: {{
    labels: compAgents,
    datasets: [{{
      label: 'Mean Profit ($/day)',
      data: compAgents.map(a => summary[a]?.meanProfit ?? 0),
      backgroundColor: compAgents.map(a => AGENT_COLORS[a] + 'cc'),
      borderColor: compAgents.map(a => AGENT_COLORS[a]),
      borderWidth: 1.5,
      borderRadius: 6
    }}]
  }},
  options: {{
    ...CD,
    plugins: {{
      ...CD.plugins,
      legend: {{ display: false }},
      tooltip: {{
        callbacks: {{
          label: ctx => `Mean Profit: $${{ctx.raw.toFixed(2)}} (Gap: ${{summary[ctx.label]?.gapVsLp?.toFixed(1) ?? 0}}%)`
        }}
      }}
    }},
    scales: {{
      ...CD.scales,
      y: {{ ...CD.scales.y, ticks: {{ ...CD.scales.y.ticks, callback: v => '$' + v.toFixed(2) }} }}
    }}
  }}
}});

// =============================================
// POPULATE LEADERBOARD TABLE
// =============================================
const lbBody = document.getElementById('leaderboard-body');
const sortedAgents = Object.keys(summary).sort((a, b) => summary[b].meanProfit - summary[a].meanProfit);

sortedAgents.forEach((name, idx) => {{
  const s = summary[name];
  const tr = document.createElement('tr');
  const rankTag = idx === 0 ? '<span class="tag tag-rank1">Benchmark</span>' :
                  idx === 1 ? '<span class="tag tag-rank2">Rank #1 RL</span>' :
                  idx === 2 ? '<span class="tag tag-rank3">Rank #2 RL</span>' :
                  `<span class="tag" style="background:rgba(100,116,139,0.15);color:#94a3b8">#${{idx+1}}</span>`;

  tr.innerHTML = `
    <td><strong>${{name}}</strong> &nbsp;${{rankTag}}</td>
    <td style="color:${{s.meanProfit >= -2.0 ? '#34d399' : s.meanProfit >= -3.0 ? '#60a5fa' : '#f87171'}}">$${{s.meanProfit.toFixed(2)}}</td>
    <td>±$${{s.stdProfit.toFixed(2)}}</td>
    <td style="color:${{s.gapVsLp === 0 ? '#34d399' : s.gapVsLp <= 25 ? '#c4b5fd' : '#f87171'}}">${{s.gapVsLp.toFixed(1)}}%</td>
    <td>$${{s.energyProfit.toFixed(2)}}</td>
    <td>$${{s.peakPenalty.toFixed(2)}}</td>
    <td>${{s.throughput.toFixed(2)}}</td>
    <td>${{s.finalSoc.toFixed(1)}}%</td>
    <td>${{s.evalTime.toFixed(2)}}s</td>
  `;
  lbBody.appendChild(tr);
}});

// =============================================
// UI UPDATES
// =============================================
const PERIODS = {{
  0: 'Night (Off-Peak)', 1: 'Night (Off-Peak)', 2: 'Night (Off-Peak)', 3: 'Night (Off-Peak)', 4: 'Night (Off-Peak)', 5: 'Dawn (Off-Peak)',
  6: 'Morning (Mid-Peak)', 7: 'Morning (Mid-Peak)', 8: 'Morning (Mid-Peak)', 9: 'Morning (Mid-Peak)', 10: 'Morning (Mid-Peak)', 11: 'Midday (Mid-Peak)', 12: 'Noon (Mid-Peak)', 13: 'Early Afternoon',
  14: '⚡ On-Peak (High Cost)', 15: '⚡ On-Peak (High Cost)', 16: '⚡ On-Peak (High Cost)', 17: '⚡ On-Peak (High Cost)', 18: '⚡ On-Peak (High Cost)', 19: '⚡ On-Peak (High Cost)', 20: '⚡ On-Peak (High Cost)',
  21: 'Evening (Mid-Peak)', 22: 'Late Evening', 23: 'Night (Off-Peak)'
}};

function updateUI() {{
  const h = currentHour;
  const ag = agents[selectedAgent];
  if (!ag) return;

  // Time & Scrubber
  document.getElementById('time-display').textContent = `${{String(h).padStart(2, '0')}}:00`;
  document.getElementById('hour-num').textContent = h;
  document.getElementById('period-label').textContent = PERIODS[h] || '';
  const scrub = document.getElementById('time-scrubber');
  scrub.value = h;
  scrub.style.setProperty('--pct', (h / 23 * 100) + '%');

  const tariff = h >= 14 && h <= 20 ? 'On-Peak' : (h < 6 ? 'Off-Peak' : 'Mid-Peak');
  const badge = document.getElementById('price-tariff-badge');
  badge.textContent = tariff;
  badge.style.color = tariff === 'On-Peak' ? '#f87171' : (tariff === 'Off-Peak' ? '#34d399' : '#fbbf24');
  badge.style.borderColor = tariff === 'On-Peak' ? 'rgba(239,68,68,0.4)' : (tariff === 'Off-Peak' ? 'rgba(16,185,129,0.4)' : 'rgba(245,158,11,0.4)');

  // Battery SoC
  const soc = ag.soc[h] ?? 0.5;
  const socPct = Math.round(soc * 100);
  const sc = soc < 0.2 ? '#f87171' : soc < 0.45 ? '#fbbf24' : '#34d399';
  document.getElementById('soc-pct').textContent = socPct + '%';
  document.getElementById('soc-kwh').textContent = `${{(soc * 13.5).toFixed(2)}} / 13.5 kWh`;
  const sb = document.getElementById('soc-bar');
  sb.style.width = socPct + '%';
  sb.style.background = `linear-gradient(90deg, ${{sc}}, ${{sc}}aa)`;
  sb.style.boxShadow = `0 0 12px ${{sc}}88`;

  // 3D Battery Segment LEDs
  bSegs.forEach((seg, i) => {{
    const lit = soc >= (i + 1) / 8;
    seg.material.color.setHex(lit ? 0x10b981 : 0x162c20);
  }});
  battGlowL.intensity = 0.5 + soc * 1.4;
  battGlowL.color.setHex(soc < 0.25 ? 0xef4444 : 0x10b981);

  // Flows
  const solVal = solar[h] ?? 0;
  const loadVal = load[h] ?? 0;
  const batVal = ag.bat[h] ?? 0;
  const gridVal = ag.grid[h] ?? 0;

  document.getElementById('flow-solar').textContent = solVal.toFixed(2);
  document.getElementById('flow-load').textContent = loadVal.toFixed(2);
  document.getElementById('flow-battery').textContent = (batVal >= 0 ? '+' : '') + batVal.toFixed(2);
  document.getElementById('flow-grid').textContent = (gridVal >= 0 ? '+' : '') + gridVal.toFixed(2);

  // KPIs
  const cumProf = ag.cumProfit[h] ?? 0;
  const stepCost = ag.cost[h] ?? 0;
  document.getElementById('kpi-profit').textContent = (cumProf >= 0 ? '+$' : '-$') + Math.abs(cumProf).toFixed(3);
  document.getElementById('kpi-profit').style.color = cumProf >= 0 ? '#34d399' : (cumProf >= -1.0 ? '#60a5fa' : '#f87171');
  document.getElementById('kpi-step-cost').textContent = '$' + stepCost.toFixed(3);
  document.getElementById('kpi-bat').textContent = (batVal >= 0 ? '+' : '') + batVal.toFixed(2) + ' kW';
  document.getElementById('kpi-bat').style.color = batVal > 0.05 ? '#34d399' : (batVal < -0.05 ? '#f59e0b' : '#94a3b8');
  document.getElementById('bat-flow-dir').textContent = batVal > 0.05 ? 'Charging' : (batVal < -0.05 ? 'Discharging' : 'Idle');
  document.getElementById('kpi-price').textContent = '$' + prices[h].toFixed(2);

  // Grid details
  document.getElementById('info-grid').textContent = `${{gridVal >= 0 ? '+' : ''}}${{gridVal.toFixed(2)}} kW (${{gridVal >= 0 ? 'Import' : 'Export'}})`;
  document.getElementById('info-solar').textContent = solVal.toFixed(2) + ' kW';
  document.getElementById('info-load').textContent = loadVal.toFixed(2) + ' kW';
  document.getElementById('info-gap').textContent = (ag.gapVsLp ?? 0).toFixed(1) + '%';

  // Particle flow updates
  // 1. Solar -> Battery/House
  particles[0].mat.opacity = solVal > 0.1 ? 0.9 : 0.05;
  // 2. Battery <-> House
  particles[1].mat.opacity = Math.abs(batVal) > 0.05 ? 0.9 : 0.05;
  particles[1].dir = batVal >= 0 ? 1 : -1;
  // 3. Grid <-> House
  particles[2].mat.opacity = Math.abs(gridVal) > 0.05 ? 0.85 : 0.05;
  particles[2].dir = gridVal >= 0 ? 1 : -1;

  // Window & Solar Lighting
  fillLight.intensity = 0.4 + solVal * 0.45;
  fillLight.color.setHex(h >= 6 && h <= 18 ? 0xfcd34d : 0x1e3a8a);
  windowLights.forEach(wl => {{ wl.intensity = 0.2 + (loadVal / 4.0) * 0.5; }});

  socChart.update('none');
}}

function selectAgent(name) {{
  selectedAgent = name;
  document.querySelectorAll('.agent-btn').forEach(b => b.classList.remove('selected'));
  const btnMap = {{ 'LP': 'agent-LP', 'R-SAC': 'agent-RSAC', 'SAC': 'agent-SAC', 'PPO': 'agent-PPO', 'Rule-Based': 'agent-Rule', 'NoOp': 'agent-NoOp' }};
  document.getElementById(btnMap[name])?.classList.add('selected');

  // Update Status Card
  const desc = AGENT_DESCRIPTIONS[name] || {{ name, rank: '', desc: '' }};
  document.getElementById('agent-card-name').textContent = desc.name;
  document.getElementById('agent-card-rank').textContent = desc.rank;
  document.getElementById('agent-card-desc').textContent = desc.desc;

  document.getElementById('power-chart-agent').textContent = name;

  // Update SOC chart styling
  socChart.data.datasets.forEach(ds => {{
    ds.borderWidth = ds.label === name ? 3.0 : 1.0;
    ds.borderColor = ds.label === name ? AGENT_COLORS[ds.label] : AGENT_COLORS[ds.label] + '55';
  }});
  socChart.update();

  // Update Power Chart
  powerChart.data.datasets[2].data = agents[name].grid;
  powerChart.data.datasets[3].data = agents[name].bat;
  powerChart.update();

  updateUI();
}}

function togglePlay() {{
  playing = !playing;
  const b = document.getElementById('btn-play');
  b.textContent = playing ? '⏸ Pause' : '▶ Play';
  b.classList.toggle('active', playing);
}}

function stepTime(d) {{
  currentHour = Math.max(0, Math.min(23, currentHour + d));
  updateUI();
}}

function cycleSpeed() {{
  speedIdx = (speedIdx + 1) % SPEEDS.length;
  document.getElementById('btn-speed').textContent = SPEEDS[speedIdx] + '×';
}}

document.getElementById('time-scrubber').addEventListener('input', e => {{
  currentHour = +e.target.value;
  updateUI();
}});

// =============================================
// PARTICLE CANVAS BACKGROUND
// =============================================
const pCanvas = document.getElementById('particle-canvas');
const pCtx = pCanvas.getContext('2d');
let bgParticles = [];
function initBG() {{
  pCanvas.width = window.innerWidth;
  pCanvas.height = window.innerHeight;
  bgParticles = Array.from({{ length: 45 }}, () => ({{
    x: Math.random() * pCanvas.width,
    y: Math.random() * pCanvas.height,
    r: Math.random() * 1.5 + 0.4,
    vx: (Math.random() - 0.5) * 0.25,
    vy: (Math.random() - 0.5) * 0.25,
    a: Math.random() * 0.5 + 0.2
  }}));
}}
initBG();
window.addEventListener('resize', initBG);

function drawBG() {{
  pCtx.clearRect(0, 0, pCanvas.width, pCanvas.height);
  bgParticles.forEach(p => {{
    p.x += p.vx; p.y += p.vy;
    if (p.x < 0 || p.x > pCanvas.width) p.vx *= -1;
    if (p.y < 0 || p.y > pCanvas.height) p.vy *= -1;
    pCtx.beginPath();
    pCtx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
    pCtx.fillStyle = `rgba(96,165,250,${{p.a}})`;
    pCtx.fill();
  }});
}}

// =============================================
// ANIMATION LOOP
// =============================================
let tSec = 0, lastAutoStep = 0;
let isDragging = false, prevMX = 0, camAngle = 0.35;

panel3d.addEventListener('mousedown', e => {{ isDragging = true; prevMX = e.clientX; }});
window.addEventListener('mouseup', () => {{ isDragging = false; }});
window.addEventListener('mousemove', e => {{
  if (!isDragging) return;
  camAngle += (e.clientX - prevMX) * 0.01;
  prevMX = e.clientX;
}});

function animate(ts) {{
  requestAnimationFrame(animate);
  tSec = ts * 0.001;

  if (playing && ts - lastAutoStep > 1300 / SPEEDS[speedIdx]) {{
    currentHour = (currentHour + 1) % 24;
    updateUI();
    lastAutoStep = ts;
  }}

  if (!isDragging) {{
    camAngle += 0.0035;
  }}
  const CR = 23;
  camera.position.x = CR * Math.sin(camAngle);
  camera.position.z = CR * Math.cos(camAngle);
  camera.position.y = 10 + Math.sin(tSec * 0.04) * 1.1;
  camera.lookAt(0, 1.4, 0);

  // Particles
  particles.forEach((ps) => {{
    const {{ from, to, geo, n, dir }} = ps;
    const pa = geo.attributes.position;
    for (let i = 0; i < n; i++) {{
      const tv = ((i / n + tSec * 0.6 * dir + ps.offset) % 1 + 1) % 1;
      pa.setXYZ(
        i,
        from[0] + (to[0] - from[0]) * tv,
        from[1] + (to[1] - from[1]) * tv,
        from[2] + (to[2] - from[2]) * tv
      );
    }}
    pa.needsUpdate = true;
  }});

  // Battery Pulse
  const curSoc = agents[selectedAgent]?.soc[currentHour] ?? 0.5;
  battGlowL.intensity = (0.7 + curSoc * 0.8) * (0.92 + 0.08 * Math.sin(tSec * 3));

  drawBG();
  renderer.render(scene, camera);
}}

// Initialize
selectAgent('R-SAC');
updateUI();
animate(0);
</script>
</body>
</html>
'''

    with open('dashboard.html', 'w', encoding='utf-8') as f:
        f.write(html_content)
    print("[OK] dashboard.html successfully updated and wired to real trained results!")

if __name__ == '__main__':
    build_dashboard()
