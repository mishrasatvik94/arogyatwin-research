"""
ArogyaTwin Figure Generator
===========================
Generates publication figures 7-12 from simulation results:
- Fig 7: Valid-alert delivery latency CDF (seeds 8000-8009)
- Fig 8: Stale-packet transmission vs. proactive suppression (N=30 trials from results.json)
- Fig 9: Bandwidth consumption by configuration (N=30 trials from results.json)
- Fig 10: Queue occupancy over time (seeds 8500-8509, separate 10-trial experiment)
- Fig 11: Regional verification precision and recall ablation (N=30 trials from results.json)
- Fig 12: Adaptive trust calibration under chronically degraded node (seeds 8600-8609, 10 trials)
"""
import os
import json
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from sim.engine import run_trial, CONFIGS
from sim.metrics import compute_metrics
from sim.core import (
    DEGRADED_VILLAGE, TRUST_WEIGHTS, H_PRIOR, H_ALPHA,
    generate_ground_truth, village_drift, clip, HOURS,
    N_VILLAGES, SOURCES_PER_VILLAGE, VERIFICATION_DELAY,
)

plt.rcParams.update({
    "font.size": 11, "axes.spines.top": False, "axes.spines.right": False,
    "figure.facecolor": "white", "axes.facecolor": "white",
    "font.family": "DejaVu Sans",
})

OUT = "."   # save figures to current directory
RESULTS_FILE = "results.json"

COLORS = dict(full="#1b6ca8", raw="#c0392b", fixed_ttl="#e67e22", fixed_trust="#8e44ad",
              no_diversity="#16a085", no_expiry="#c0392b", no_signature="#7f8c8d")


# ---------- Figure 7: valid-alert delivery-latency CDF ----------
def fig7():
    fig, ax = plt.subplots(figsize=(7.5, 4.6))
    for cfg, color, label in [("full", "#1b6ca8", "Full ArogyaTwin"),
                               ("fixed_ttl", "#e67e22", "Fixed-TTL"),
                               ("centralized_raw", "#c0392b", "Centralized/raw forwarding")]:
        all_lat = []
        for seed in range(10):
            r = run_trial("long_outage", cfg, seed=8000 + seed)
            all_lat.extend(p["latency"] for p in r["packets"] if not p["stale"])
        all_lat = np.sort(all_lat)
        y = np.arange(1, len(all_lat) + 1) / len(all_lat)
        ax.plot(all_lat, y, label=label, color=color, linewidth=2.2)
    ax.set_xlabel("Valid-alert delivery latency (hours)")
    ax.set_ylabel("Cumulative fraction of delivered valid packets")
    ax.set_title("Figure 7. Valid-alert delivery latency (long-outage scenario)")
    ax.set_xlim(0, 150)
    ax.legend(frameon=False, loc="lower right")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig7_latency_cdf.png", dpi=200)
    plt.close(fig)
    print("  fig7 saved")


# ---------- Figure 8: stale-packet handling ----------
def fig8():
    d = json.load(open(RESULTS_FILE))
    scen = "long_outage"
    e1 = d["exp1_main_comparison"][scen]
    configs = ["centralized_raw", "no_expiry", "fixed_ttl", "fixed_trust", "no_diversity", "full"]
    labels = ["Centralized/\nraw", "No expiry\nsuppression (D)", "Fixed-TTL", "Fixed-trust",
              "No diversity\ncheck (E)", "Full\nArogyaTwin"]
    stale_rate = [e1[c]["stale_rate"]["mean"] * 100 for c in configs]
    disc = [e1[c]["proactive_discards"]["mean"] for c in configs]
    n_gen = [e1[c]["n_generated"]["mean"] for c in configs]
    suppressed_pct = [100 * d_ / n for d_, n in zip(disc, n_gen)]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    x = np.arange(len(configs))
    w = 0.36
    b1 = ax.bar(x - w / 2, stale_rate, w, label="Stale packets transmitted (%)", color="#c0392b")
    b2 = ax.bar(x + w / 2, suppressed_pct, w, label="Stale packets proactively suppressed (%)", color="#1b6ca8")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylabel("% of generated candidate packets")
    ax.set_title("Figure 8. Stale-packet transmission vs. proactive suppression\n(long-outage scenario, N=30 trials)")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig8_stale_handling.png", dpi=200)
    plt.close(fig)
    print("  fig8 saved")


# ---------- Figure 9: bandwidth consumption ----------
def fig9():
    d = json.load(open(RESULTS_FILE))
    scen = "long_outage"
    e1 = d["exp1_main_comparison"][scen]
    configs = ["centralized_raw", "no_signature", "fixed_ttl", "fixed_trust", "no_diversity", "full"]
    labels = ["Centralized/\nraw", "(A) No compact\nsignature", "Fixed-TTL", "Fixed-trust",
              "(E) No diversity\ncheck", "(F) Full\nArogyaTwin"]
    bpe = [e1[c]["bytes_per_event"]["mean"] for c in configs]
    ci = [e1[c]["bytes_per_event"]["ci95"] for c in configs]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    colors = ["#c0392b", "#8e44ad", "#e67e22", "#e67e22", "#16a085", "#1b6ca8"]
    bars = ax.bar(labels, bpe, yerr=ci, capsize=4, color=colors)
    ax.set_ylabel("Bytes transmitted per generated candidate event")
    ax.set_yscale("log")
    ax.set_title("Figure 9. Communication overhead by configuration\n(long-outage scenario, N=30 trials, log scale)")
    for b, v in zip(bars, bpe):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.15, f"{v:.0f} B", ha="center", fontsize=9)
    ax.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig9_bandwidth.png", dpi=200)
    plt.close(fig)
    print("  fig9 saved")


# ---------- Figure 10: queue occupancy over time ----------
def fig10():
    fig, ax = plt.subplots(figsize=(8, 4.6))
    for cfg, color, label in [("centralized_raw", "#c0392b", "Centralized/raw forwarding"),
                               ("fixed_ttl", "#e67e22", "Fixed-TTL"),
                               ("full", "#1b6ca8", "Full ArogyaTwin")]:
        traces = []
        for seed in range(10):
            r = run_trial("long_outage", cfg, seed=8500 + seed)
            qt = np.zeros(720)
            for (t, v, q) in r["queue_trace"]:
                qt[t] += q
            traces.append(qt / 6.0)  # mean across villages
        mean_trace = np.mean(traces, axis=0)
        ax.plot(mean_trace, color=color, label=label, linewidth=1.8)
    ax.axvspan(288, 384, color="gray", alpha=0.18, label="Induced 96h outage")
    ax.axvspan(300, 450, color="orange", alpha=0.10, label="Outbreak-1 window")
    ax.set_xlabel("Simulation time (hours)")
    ax.set_ylabel("Mean queued packets per village")
    ax.set_title("Figure 10. Queue occupancy over the 30-day evaluation horizon\n(long-outage scenario, mean of 10 trials)")
    ax.legend(frameon=False, fontsize=9, loc="upper left")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig10_queue_occupancy.png", dpi=200)
    plt.close(fig)
    print("  fig10 saved")


# ---------- Figure 11: ablation comparison (precision) ----------
def fig11():
    d = json.load(open(RESULTS_FILE))
    scen = "long_outage"
    e1 = d["exp1_main_comparison"][scen]
    order = ["centralized_raw", "no_signature", "fixed_trust", "fixed_ttl", "no_diversity", "full"]
    labels = ["Centralized/\nraw", "(A) No compact\nsignature", "(B) Fixed\ntrust",
              "(C) Fixed\nTTL", "(E) No diversity\ncheck", "(F) Full\nArogyaTwin"]
    prec = [e1[c]["precision"]["mean"] for c in order]
    ci = [e1[c]["precision"]["ci95"] for c in order]
    rec = [e1[c]["recall"]["mean"] for c in order]

    fig, ax = plt.subplots(figsize=(8, 4.8))
    x = np.arange(len(order))
    w = 0.36
    ax.bar(x - w / 2, prec, w, yerr=ci, capsize=3, label="Regional verification precision", color="#1b6ca8")
    ax.bar(x + w / 2, rec, w, label="Recall (both outbreaks)", color="#95a5a6")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9.5)
    ax.set_ylim(0, 1.15)
    ax.set_title("Figure 11. Ablation comparison: regional verification precision/recall\n(long-outage scenario, N=30 trials, mean \u00b1 95% CI)")
    ax.legend(frameon=False)
    ax.grid(alpha=0.25, axis="y")
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig11_ablation_precision.png", dpi=200)
    plt.close(fig)
    print("  fig11 saved")


# ---------- Figure 12: trust calibration under degraded nodes ----------
def fig12():
    fig, ax = plt.subplots(figsize=(8, 4.6))
    seeds = range(10)
    reliable_v = 0
    traces_deg, traces_rel = [], []
    for seed in seeds:
        rng = np.random.default_rng(8600 + seed)
        fire, true_label, conf, accurate = generate_ground_truth(rng)
        H = np.full(N_VILLAGES, H_PRIOR)
        pending = [[] for _ in range(N_VILLAGES)]
        trust_trace = np.zeros((N_VILLAGES, HOURS))
        for t in range(HOURS):
            drift_t = village_drift(t)
            for v in range(N_VILLAGES):
                s0, s1 = v * SOURCES_PER_VILLAGE, (v + 1) * SOURCES_PER_VILLAGE
                firing_idx = [s for s in range(s0, s1) if fire[s, t]]
                if firing_idx:
                    c_val = float(np.mean([conf[s, t] for s in firing_idx]))
                    a_val = (len(firing_idx) - 1) / (SOURCES_PER_VILLAGE - 1)
                    d_val = float(clip(drift_t[v] + rng.normal(0, 0.03), 0, 1))
                    w = TRUST_WEIGHTS
                    trust = clip(w["w_H"] * H[v] + w["w_C"] * c_val + w["w_A"] * a_val - w["w_D"] * d_val, 0, 1)
                    trust_trace[v, t] = trust
                    acc = all(accurate[s, t] for s in firing_idx)
                    pending[v].append((t + VERIFICATION_DELAY, acc))
                else:
                    trust_trace[v, t] = trust_trace[v, t - 1] if t > 0 else H_PRIOR
                still = []
                for (rt, lab) in pending[v]:
                    if rt <= t:
                        H[v] = (1 - H_ALPHA) * H[v] + H_ALPHA * (1.0 if lab else 0.0)
                    else:
                        still.append((rt, lab))
                pending[v] = still
        traces_deg.append(trust_trace[DEGRADED_VILLAGE])
        traces_rel.append(trust_trace[reliable_v])
    mean_deg = np.mean(traces_deg, axis=0)
    mean_rel = np.mean(traces_rel, axis=0)
    ax.plot(mean_rel, color="#1b6ca8", label="Reliable village (V0)", linewidth=1.8)
    ax.plot(mean_deg, color="#c0392b", label="Chronically degraded village (V5)", linewidth=1.8)
    ax.set_xlabel("Simulation time (hours)")
    ax.set_ylabel("Adaptive trust value T(t)")
    ax.set_title("Figure 12. Adaptive trust calibration under a chronically degraded node\n(mean of 10 trials)")
    ax.set_ylim(0, 1)
    ax.legend(frameon=False)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(f"{OUT}/fig12_trust_calibration.png", dpi=200)
    plt.close(fig)
    print("  fig12 saved")


if __name__ == "__main__":
    print("Generating figures from simulation results...")
    fig7(); print("fig7 done")
    fig8(); print("fig8 done")
    fig9(); print("fig9 done")
    fig10(); print("fig10 done")
    fig11(); print("fig11 done")
    fig12(); print("fig12 done")
    print("\nAll figures generated successfully.")
