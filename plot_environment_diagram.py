# plot_environment_diagram.py
# Generate the microgrid system architecture diagram

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import os

def draw_diagram(save_path="results/environment_architecture.pdf"):
    fig, ax = plt.subplots(figsize=(12, 7))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 7)
    ax.axis('off')
    
    # background layers
    cyber = patches.Rectangle((0, 4.5), 10, 2.5, facecolor='#d6eaf8', edgecolor='#3498db', alpha=0.5, zorder=0)
    ax.add_patch(cyber)
    ax.text(1.5, 6, "CYBER LAYER\n(Control/Agent)", ha='center', va='center', fontsize=14, fontweight='bold')
    
    phys = patches.Rectangle((0, 0), 10, 4.2, facecolor='#d5f5e3', edgecolor='#27ae60', alpha=0.5, zorder=0)
    ax.add_patch(phys)
    ax.text(1.5, 3.5, "PHYSICAL LAYER\n(Microgrid)", ha='center', va='center', fontsize=14, fontweight='bold')
    
    def draw_box(x, y, w, h, text, color, ec='black'):
        r = patches.Rectangle((x, y), w, h, facecolor=color, edgecolor=ec, linewidth=1.5, zorder=2)
        ax.add_patch(r)
        ax.text(x + w/2, y + h/2, text, ha='center', va='center', fontsize=12, fontweight='bold', zorder=3)
        return (x + w/2, y + h/2)
        
    # components
    agent_x, agent_y = 4.0, 5.0
    agent_w, agent_h = 3.0, 1.2
    agent_ctr = draw_box(agent_x, agent_y, agent_w, agent_h, "RL Agent\n(EMS)", '#a9cce3')
    
    cw, ch = 1.8, 1.0
    
    grid_x, grid_y = 2.5, 2.5
    grid_ctr = draw_box(grid_x, grid_y, cw, ch, "Grid\nConnection", '#d7dbdd')
    
    solar_x, solar_y = 6.5, 2.5
    solar_ctr = draw_box(solar_x, solar_y, cw, ch, "Solar PV", '#f9e79f', '#f1c40f')
    
    load_x, load_y = 2.5, 0.5
    load_ctr = draw_box(load_x, load_y, cw, ch, "House Load", '#fadbd8', '#e74c3c')
    
    batt_x, batt_y = 6.5, 0.5
    batt_ctr = draw_box(batt_x, batt_y, cw, ch, "Battery Storage\n(ESS)", '#d2b4de', '#8e44ad')
    
    # DC/AC bus
    bus = patches.Circle((5.5, 1.75), 0.6, facecolor='#fAD7A0', edgecolor='#F39C12', linewidth=1.5, zorder=2)
    ax.add_patch(bus)
    ax.text(5.5, 1.75, "DC/AC\nBus", ha='center', va='center', fontsize=11, fontweight='bold', zorder=3)
    bus_ctr = (5.5, 1.75)
    
    # arrows
    pwr = dict(arrowstyle='<->', linewidth=3, color='black', shrinkA=0, shrinkB=0)
    pwr_dir = dict(arrowstyle='->', linewidth=3, color='black', shrinkA=0, shrinkB=0)
    info = dict(arrowstyle='->', linewidth=1.5, color='#0055aa', linestyle='--', shrinkA=0, shrinkB=0)
    
    # power flows
    ax.annotate("", xy=bus_ctr, xytext=(grid_x+cw, grid_y+ch/2), arrowprops=pwr, zorder=1)
    ax.plot([solar_x, 5.5], [solar_y+ch/2, solar_y+ch/2], lw=3, color='black', zorder=1)
    ax.plot([5.5, 5.5], [solar_y+ch/2, 1.75], lw=3, color='black', zorder=1)
    ax.annotate("", xy=bus_ctr, xytext=(5.5, 3.0), arrowprops=pwr_dir, zorder=1)
    ax.annotate("", xy=(batt_x, batt_y+ch/2), xytext=bus_ctr, arrowprops=pwr, zorder=1)
    ax.annotate("", xy=(load_x+cw, load_y+ch/2), xytext=bus_ctr, arrowprops=pwr_dir, zorder=1)
    ax.text(4.5, 2.0, "Power Flow", fontsize=10, rotation=35, ha='center')

    # info flows
    ax.plot([grid_x+cw/2, grid_x+cw/2], [grid_y+ch, agent_y+0.6], lw=1.5, color='#0055aa', linestyle='--', zorder=1)
    ax.plot([grid_x+cw/2, agent_x], [agent_y+0.6, agent_y+0.6], lw=1.5, color='#0055aa', linestyle='--', zorder=1)
    ax.annotate("", xy=(agent_x, agent_y+0.6), xytext=(agent_x-0.1, agent_y+0.6), arrowprops=info)
    ax.text(3.1, 4.3, "Price", fontsize=10, bbox=dict(facecolor='white', edgecolor='none', alpha=0.7))

    ax.plot([solar_x+cw/2, solar_x+cw/2], [solar_y+ch, agent_y], lw=1.5, color='#0055aa', linestyle='--', zorder=1)
    ax.annotate("", xy=(solar_x+cw/2, agent_y), xytext=(solar_x+cw/2, agent_y-0.1), arrowprops=info)
    ax.text(7.0, 4.0, "Generation", fontsize=10, ha='center', bbox=dict(facecolor='white', edgecolor='none', alpha=0.7))
    
    px = [batt_x+cw*0.8, batt_x+cw*0.8, 9.5, 9.5, agent_x+agent_w]
    py = [batt_y+ch, 4.0, 4.0, agent_y+0.4, agent_y+0.4]
    ax.plot(px, py, lw=1.5, color='#0055aa', linestyle='--', zorder=1)
    ax.annotate("", xy=(agent_x+agent_w, agent_y+0.4), xytext=(agent_x+agent_w+0.1, agent_y+0.4), arrowprops=info)
    ax.text(9.0, 4.2, "SOC", fontsize=10, ha='center')
    
    px2 = [agent_x+agent_w, 9.8, 9.8, batt_x+cw/2]
    py2 = [agent_y+0.8, agent_y+0.8, 1.8, batt_y+ch]
    ax.plot(px2, py2, lw=1.5, color='#0055aa', linestyle='--', zorder=1)
    ax.annotate("", xy=(batt_x+cw/2, batt_y+ch), xytext=(batt_x+cw/2, batt_y+ch+0.1), arrowprops=info)
    ax.text(8.5, 6.0, "Charge/Discharge Cmd", fontsize=10, ha='center', bbox=dict(facecolor='white', edgecolor='none', alpha=0.7))

    plt.tight_layout()
    
    d = os.path.dirname(save_path)
    if d and not os.path.exists(d):
        os.makedirs(d)
        
    plt.savefig(save_path, bbox_inches='tight', dpi=300)
    print("Diagram saved to %s" % save_path)
    plt.close()

if __name__ == "__main__":
    draw_diagram()
