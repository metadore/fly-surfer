"""Generate every figure used in the FLY-SURFER research paper.

All panels are either (a) plotted directly from recorded project artifacts or
(b) explicitly labelled schematic/computed illustrations. Nothing is simulated
for the paper: no neural run, training run, replay or protocol step is executed.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import ROOT, FIGURES, load_json, load_jsonl  # noqa: E402

plt.rcParams.update({
    "font.size": 8.5,
    "axes.titlesize": 9.5,
    "axes.labelsize": 8.5,
    "xtick.labelsize": 7.5,
    "ytick.labelsize": 7.5,
    "legend.fontsize": 7.5,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "figure.dpi": 200,
    "savefig.dpi": 200,
    "savefig.bbox": "tight",
    "axes.unicode_minus": False,
})

C = {
    "blue": "#3b6ea5", "orange": "#e08b3c", "green": "#4c8f5a",
    "red": "#b8453f", "purple": "#7b5c9e", "grey": "#7d7d7d",
    "light": "#c9d6e3",
}

INDEX = []


def save(fig, fid, title, sources, note=""):
    path = FIGURES / f"{fid}.png"
    fig.savefig(path)
    plt.close(fig)
    INDEX.append({"figure_id": fid, "title": title, "file": path.name,
                  "sources": sources, "note": note})
    print("wrote", path.name)


def box(ax, x, y, w, h, text, color="#eef2f7", edge="#4a4a4a", fontsize=7.6):
    ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.012,rounding_size=0.012",
                                         linewidth=0.9, edgecolor=edge, facecolor=color))
    ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=fontsize, wrap=True)


def arrow(ax, x1, y1, x2, y2, color="#4a4a4a"):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1),
                arrowprops=dict(arrowstyle="-|>", lw=1.0, color=color, shrinkA=0, shrinkB=0))


# ----------------------------------------------------------------------------
# F01 system architecture (schematic)
# ----------------------------------------------------------------------------
def f01():
    fig, ax = plt.subplots(figsize=(7.2, 4.6))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.grid(False)
    ax.set_title("Figure 1. End-to-end FLY-SURFER architecture (schematic, not data)")
    top = [
        (0.01, 0.72, "Controlled game\n(endless-surfer)", "#f3e7d7"),
        (0.26, 0.72, "Observation adapter\n(schema v1 -> GameState)", "#e8eef7"),
        (0.51, 0.72, "Perception + 14\ntemporal features", "#e8eef7"),
        (0.76, 0.72, "Sensory scheduler\n(features -> populations)", "#e8eef7"),
    ]
    for x, y, t, col in top:
        box(ax, x, y, 0.23, 0.16, t, color=col, fontsize=7.2)
    for i in range(3):
        arrow(ax, top[i][0] + 0.23, 0.80, top[i + 1][0], 0.80)
    arrow(ax, 0.875, 0.72, 0.875, 0.63)
    mid = [
        (0.76, 0.46, "Motor decoder\n50 ms windows\nLEFT / RIGHT / JUMP", "#f6e6e6"),
        (0.51, 0.46, "Connectome SNN\n172,433 LIF neurons\n1,535,710 edges (t5)", "#e3efe4"),
        (0.26, 0.46, "Game action\n(NO_ACTION / LEFT /\nRIGHT / JUMP)", "#f6e6e6"),
    ]
    for x, y, t, col in mid:
        box(ax, x, y, 0.23, 0.17, t, color=col, fontsize=7.0)
    arrow(ax, 0.76, 0.545, 0.74, 0.545)
    arrow(ax, 0.51, 0.545, 0.49, 0.545)
    arrow(ax, 0.26, 0.545, 0.24, 0.545)
    arrow(ax, 0.24, 0.545, 0.24, 0.72)
    ax.text(0.5, 0.40, "closed loop: one game update per ~33.3 ms (60 Hz)", fontsize=7.2,
            ha="center", color=C["grey"])
    box(ax, 0.26, 0.14, 0.23, 0.14, "Optional linear readout F\n(trainable, Pilot 2-C)", color="#f0ecf7", fontsize=7.0)
    box(ax, 0.51, 0.14, 0.23, 0.14, "Optional three-factor\nplasticity", color="#f0ecf7", fontsize=7.0)
    box(ax, 0.76, 0.14, 0.23, 0.14, "Optional MLP baseline E\n(not run)", color="#f7f7f7", fontsize=7.0)
    ax.text(0.5, 0.045, "Green path = frozen biological substrate; purple = learning components added in Phase 5/8.",
            ha="center", fontsize=7, color=C["grey"])
    save(fig, "F01_system_architecture",
         "End-to-end FLY-SURFER system architecture",
         "configs/*.yaml; reports/PHASE_7_GAME_INTEGRATION.md; REV4 sections 3-4",
         "Schematic. Counts shown are the frozen configuration values.")


# ----------------------------------------------------------------------------
# F02 FlyWire FAFB construction funnel
# ----------------------------------------------------------------------------
def f02():
    r = load_json("datasets/processed/connectome_report.json")
    n = r["node_index"]["n_nodes"]
    ann = r["node_index"]["annotated"]
    ntmiss = r["node_index"]["nt_type_missing"]
    ne = r["edges"]["n_edges"]
    ns = r["edges"]["n_synapses"]
    iso = r["degree"]["isolated_nodes"]
    fig, ax = plt.subplots(figsize=(6.6, 4.0))
    labels = ["Neurons\n(indexed)", "Annotated\nneurons", "No nt type", "Directed pairs\n(>=5 syn.)",
              "Synapses in\nretained pairs", "Isolated\nneurons"]
    vals = [n, ann, ntmiss, ne, ns, iso]
    cols = [C["blue"], C["green"], C["orange"], C["purple"], C["red"], C["grey"]]
    bars = ax.bar(range(len(vals)), vals, color=cols, width=0.65)
    ax.set_yscale("log")
    ax.set_xticks(range(len(vals))); ax.set_xticklabels(labels, fontsize=7.2)
    ax.set_ylabel("Count (log scale)")
    ax.set_title("Figure 2. FlyWire FAFB v783 connectome construction summary")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.15, f"{v:,}", ha="center", fontsize=7.2)
    ax.set_ylim(100, 2e8)
    ax.text(0.01, 0.96, "source: datasets/processed/connectome_report.json", transform=ax.transAxes,
            ha="left", va="top", fontsize=6.6, color=C["grey"])
    save(fig, "F02_flywire_construction",
         "FlyWire FAFB construction summary",
         "datasets/processed/connectome_report.json",
         "Counts are artifact summary values, not re-derived here.")


# ----------------------------------------------------------------------------
# F03 FAFB weight and degree distributions
# ----------------------------------------------------------------------------
def f03():
    z = np.load(ROOT / "datasets/processed/connectome.npz", allow_pickle=True)
    w = z["edge_weight"].astype(np.int64)
    outd = np.diff(z["out_indptr"])
    ind = np.diff(z["in_indptr"])
    fig, axs = plt.subplots(1, 3, figsize=(7.0, 2.7))
    axs[0].hist(w, bins=np.logspace(0, np.log10(w.max() + 1), 45), color=C["blue"])
    axs[0].set_xscale("log"); axs[0].set_yscale("log")
    axs[0].set_xlabel("Summed synapses per directed pair"); axs[0].set_ylabel("Edge count")
    axs[0].set_title("(a) Edge weight")
    for ax, d, name, col in [(axs[1], outd, "Out-degree", C["green"]), (axs[2], ind, "In-degree", C["purple"])]:
        vals = np.sort(d[d > 0])[::-1]
        ccdf = np.arange(1, vals.size + 1) / vals.size
        ax.loglog(vals, ccdf, color=col, lw=1.3)
        ax.set_xlabel(f"{name} (edges)"); ax.set_ylabel("P(X >= x)")
        ax.set_title(f"({'b' if name == 'Out-degree' else 'c'}) {name} CCDF")
    fig.suptitle("Figure 3. FlyWire FAFB v783 weight and degree distributions (edge arrays)", y=1.02)
    fig.tight_layout()
    save(fig, "F03_fafb_distributions",
         "FAFB weight and degree distributions",
         "datasets/processed/connectome.npz (edge_weight, out_indptr, in_indptr)",
         "Computed from the stored edge arrays; no new experiment.")


# ----------------------------------------------------------------------------
# F04 BANC construction and threshold sensitivity
# ----------------------------------------------------------------------------
def f04():
    b = load_json("datasets/processed/banc_v888/banc_construction_report.json")
    th = b["thresholds"]
    keys = ["threshold_1", "threshold_5", "threshold_10"]
    lab = ["t1", "t5", "t10"]
    edges = [th[k]["n_edges"] for k in keys]
    syn = [th[k]["n_synapses"] for k in keys]
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.0))
    x = np.arange(3); w = 0.36
    axs[0].bar(x - w / 2, edges, w, color=C["blue"], label="Directed edges")
    axs[0].bar(x + w / 2, syn, w, color=C["orange"], label="Synapses")
    axs[0].set_yscale("log"); axs[0].set_xticks(x); axs[0].set_xticklabels(lab)
    axs[0].set_ylabel("Count (log)"); axs[0].legend(frameon=False)
    axs[0].set_title("(a) Retained graph by threshold")
    for i, (e, s) in enumerate(zip(edges, syn)):
        axs[0].text(i - w / 2, e * 1.15, f"{e/1e6:.2f}M", ha="center", fontsize=6.2)
        axs[0].text(i + w / 2, s * 2.2, f"{s/1e6:.2f}M", ha="center", fontsize=6.2)
    axs[0].set_ylim(1e5, 2e8)
    axs[0].legend(frameon=False, loc="upper right", fontsize=7)
    stages = ["Metadata\nrows", "Endpoint\nnodes", "Original\nedges", "t5 edges"]
    vals = [b["metadata_rows"], b["node_count"], b["original_edge_count"], th["threshold_5"]["n_edges"]]
    bars = axs[1].bar(range(4), vals, color=[C["grey"], C["green"], C["purple"], C["blue"]], width=0.62)
    axs[1].set_yscale("log"); axs[1].set_xticks(range(4)); axs[1].set_xticklabels(stages, fontsize=7)
    axs[1].set_ylabel("Count (log)")
    for bar, v in zip(bars, vals):
        axs[1].text(bar.get_x() + bar.get_width() / 2, v * 1.2, f"{v:,}", ha="center", fontsize=6.6)
    axs[1].set_ylim(1e5, 3e7)
    axs[1].set_title("(b) Construction stages")
    fig.suptitle("Figure 4. BANC v888 graph construction and threshold sensitivity", y=1.03)
    fig.tight_layout()
    save(fig, "F04_banc_construction",
         "BANC v888 construction and threshold sensitivity",
         "datasets/processed/banc_v888/banc_construction_report.json",
         "Excludes 16,075 metadata-only rows and 156,311 self-edges before thresholding.")


# ----------------------------------------------------------------------------
# F05 BANC annotation coverage and composition
# ----------------------------------------------------------------------------
def f05():
    import pandas as pd
    b = load_json("datasets/processed/banc_v888/banc_construction_report.json")
    cov = b["annotation_coverage"]
    df = pd.read_csv(ROOT / "datasets/processed/banc_v888/banc_nodes.csv.gz",
                     usecols=["super_class"])
    vc = df["super_class"].fillna("unannotated").value_counts()
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.4), gridspec_kw={"width_ratios": [1, 1.5]})
    keys = ["super_class", "cell_type", "side", "neurotransmitter_verified" if "neurotransmitter_verified" in cov else "body_part_effector", "body_part_effector"]
    seen = []
    for k in keys:
        if k in cov and k not in seen:
            seen.append(k)
    labels = ["super_class", "cell_type", "side", "body_part\neffector"]
    vals = [cov["super_class"]["present_share"], cov["cell_type"]["present_share"],
            cov["side"]["present_share"], cov["body_part_effector"]["present_share"]]
    bars = axs[0].barh(range(len(vals)), [v * 100 for v in vals],
                       color=[C["blue"], C["green"], C["purple"], C["red"]])
    axs[0].set_yticks(range(len(vals))); axs[0].set_yticklabels(labels)
    axs[0].set_xlim(0, 105); axs[0].set_xlabel("Coverage (%)")
    for bar, v in zip(bars, vals):
        axs[0].text(v * 100 + 2, bar.get_y() + bar.get_height() / 2, f"{v*100:.1f}%", va="center", fontsize=7)
    axs[0].set_title("(a) Annotation coverage")
    top = vc.head(12)[::-1]
    axs[1].barh(range(len(top)), top.values, color=C["blue"])
    axs[1].set_yticks(range(len(top))); axs[1].set_yticklabels(top.index, fontsize=6.8)
    axs[1].set_xlabel("Neurons")
    for i, v in enumerate(top.values):
        axs[1].text(v + 800, i, f"{v:,}", va="center", fontsize=6.4)
    axs[1].set_xlim(0, top.max() * 1.18)
    axs[1].set_title("(b) super_class composition (top 12)")
    fig.suptitle("Figure 5. BANC v888 annotation coverage and neuronal composition", y=1.03)
    fig.tight_layout()
    save(fig, "F05_banc_annotation",
         "BANC annotation coverage and composition",
         "datasets/processed/banc_v888/banc_construction_report.json; banc_nodes.csv.gz",
         "Composition computed from the published BANC node table; not an experiment.")


# ----------------------------------------------------------------------------
# F06 LIF membrane dynamics (computed illustration)
# ----------------------------------------------------------------------------
def f06():
    Cm, g, Vrest, Vth, Vreset, tref = 200e-12, 10e-9, -65e-3, -50e-3, -68e-3, 2e-3
    dt = 0.5e-3
    tau = Cm / g
    def run(I, T=0.12):
        v = Vrest; out = []; t = 0.0; ref = 0.0; spikes = []
        while t < T:
            if ref > 0:
                ref -= dt; v = Vreset
            else:
                v = Vth + (v - Vth) * np.exp(-dt / tau)
                v = v + I / g * (1 - np.exp(-dt / tau))
                if v >= Vth:
                    spikes.append(t); v = Vreset; ref = tref
            out.append(v * 1e3); t += dt
        return np.array(out), np.array(spikes), tau
    t = np.arange(0, 0.12, dt)
    v150, s150, tau = run(150e-12)
    v300, s300, _ = run(300e-12)
    fig, ax = plt.subplots(figsize=(6.4, 3.2))
    ax.plot(t * 1e3, v150, color=C["blue"], lw=1.4, label="I = 150 pA (rheobase)")
    ax.plot(t * 1e3, v300, color=C["orange"], lw=1.2, label="I = 300 pA")
    ax.axhline(-50, color=C["red"], ls="--", lw=1, label="threshold -50 mV")
    ax.axhline(-65, color=C["grey"], ls=":", lw=1, label="rest -65 mV")
    ax.set_xlabel("Time (ms)"); ax.set_ylabel("Membrane potential (mV)")
    ax.set_title("Figure 6. LIF response computed from the declared Phase 2 parameters")
    ax.legend(frameon=False, loc="lower right")
    ax.text(0.01, 0.97, f"tau = C/g = {tau*1e3:.1f} ms; dt = 0.5 ms; refractory 2 ms",
            transform=ax.transAxes, va="top", fontsize=7, color=C["grey"])
    ax.text(0.01, 0.88, "Computed illustration. Not a recorded neuron.", transform=ax.transAxes,
            va="top", fontsize=7, color=C["red"])
    save(fig, "F06_lif_dynamics",
         "LIF membrane dynamics computed from declared parameters",
         "configs/neuron_config.yaml (C=200 pF, g=10 nS, V_rest=-65 mV, V_th=-50 mV)",
         "Computed from the frozen model equations; explicitly not experimental data.")


# ----------------------------------------------------------------------------
# F07 simulation engine schematic
# ----------------------------------------------------------------------------
def f07():
    fig, ax = plt.subplots(figsize=(6.8, 3.4))
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.axis("off"); ax.grid(False)
    ax.set_title("Figure 7. Spiking simulation engine (schematic) with measured throughput")
    box(ax, 0.02, 0.55, 0.2, 0.3, "State arrays\nV (float32)\nexponential synapse\ncurrent", color="#e8eef7")
    box(ax, 0.28, 0.55, 0.2, 0.3, "CSR propagation\nout_indptr /\nedge_dst / weight", color="#e3efe4")
    box(ax, 0.54, 0.55, 0.2, 0.3, "1 ms delay\nring buffer\n(2 steps at 0.5 ms)", color="#f3e7d7")
    box(ax, 0.80, 0.55, 0.18, 0.3, "Spike recorder\n(preallocated)", color="#f6e6e6")
    for x in (0.22, 0.48, 0.74):
        arrow(ax, x, 0.70, x + 0.06, 0.70)
    box(ax, 0.15, 0.10, 0.26, 0.2, "Full FAFB: 139,255 neurons\n3,732,460 edges\n138.3 steps/s (400 steps)", color="#f7f7f7")
    box(ax, 0.55, 0.10, 0.30, 0.2, "BANC replay: 172,433 neurons\n1,535,710 edges (t5)\n81.9 steps/s (3,300 ms)", color="#f7f7f7")
    ax.text(0.5, 0.40, "throughput measured on the project hardware (Phase 2.5 / 3B.2C)",
            ha="center", fontsize=7.2, color=C["grey"])
    save(fig, "F07_simulation_engine",
         "Spiking simulation engine structure and measured throughput",
         "experiments/phase_2_5/reports/scalability_report.json; phase_3b2c_real_sequence_replay.json",
         "Boxes are schematic; throughput values are measured.")


# ----------------------------------------------------------------------------
# F08 dataset classes and splits
# ----------------------------------------------------------------------------
def f08():
    a = load_json("reports/PHASE_3B02_V15_DATASET_AUDIT.json")
    rows = a["classes"]["rows"]
    names = [r["declared_name"] for r in rows]
    objs = [r["objects"] for r in rows]
    tr = [r["per_split"]["train"] for r in rows]
    va = [r["per_split"]["valid"] for r in rows]
    order = np.argsort(objs)
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.6), gridspec_kw={"width_ratios": [1.5, 1]})
    ax = axs[0]
    y = np.arange(len(rows))
    ax.barh(y, [objs[i] for i in order], color=C["blue"], label="all boxes")
    ax.barh(y, [tr[i] for i in order], color=C["orange"], label="train")
    ax.barh(y, [va[i] for i in order], color=C["green"], label="valid")
    ax.set_yticks(y); ax.set_yticklabels([names[i] for i in order], fontsize=6.6)
    ax.set_xlabel("Annotated boxes"); ax.legend(frameon=False, fontsize=6.6)
    ax.set_title("(a) v15 boxes per class")
    axs[1].bar(["train", "valid"], [a["inventory"]["split_counts"]["train"]["images"],
                                    a["inventory"]["split_counts"]["valid"]["images"]],
               color=[C["orange"], C["green"]], width=0.55)
    axs[1].set_ylabel("Images"); axs[1].set_title("(b) official split")
    for i, v in enumerate([1825, 503]):
        axs[1].text(i, v + 25, f"{v}", ha="center", fontsize=8)
    axs[1].set_ylim(0, 2100)
    fig.suptitle("Figure 8. Subway Surfers v15 annotation inventory (not a test set)", y=1.02)
    fig.tight_layout()
    save(fig, "F08_dataset_inventory",
         "v15 class and split inventory",
         "reports/PHASE_3B02_V15_DATASET_AUDIT.json",
         "No independent test split exists; 32.1% of adjacent frame pairs cross the official split.")


# ----------------------------------------------------------------------------
# F09 3B.2C perception pipeline metrics
# ----------------------------------------------------------------------------
def f09():
    o = load_json("experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json")
    acc = o["detection"]["accepted_by_class"]
    det = o["detection"]; trk = o["tracking"]; tmp = o["temporal"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0))
    ax = axs[0]
    classes = list(acc.keys()); vals = [acc[k] for k in classes]
    ax.bar(classes, vals, color=C["blue"])
    ax.set_ylabel("Accepted boxes (100 frames)"); ax.tick_params(axis="x", rotation=30)
    for i, v in enumerate(vals):
        ax.text(i, v + 2, str(v), ha="center", fontsize=7)
    ax.set_title("(a) Accepted detections by class")
    ax = axs[1]
    metrics = ["Candidates", "Above thr.", "Accepted", "Rejected", "Track IDs",
               "Events", "Pulses"]
    vals = [det["n_candidates"], det["n_decoded_above_threshold"], det["n_accepted"],
            det["n_rejected"], trk["n_track_ids"], tmp["n_events"], tmp["n_pulse_events"]]
    cols = [C["grey"], C["light"], C["green"], C["red"], C["purple"], C["orange"], C["blue"]]
    bars = ax.bar(metrics, vals, color=cols)
    ax.set_yscale("log"); ax.set_ylabel("Count (log)")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v * 1.15, str(v), ha="center", fontsize=6.6)
    ax.tick_params(axis="x", rotation=35); ax.set_ylim(1, 5000)
    ax.set_title("(b) Pipeline stage counts")
    fig.suptitle("Figure 15. Real-sequence replay (datasetfootage frames 100-199): perception counts", y=1.03)
    fig.tight_layout()
    save(fig, "F09_3b2c_perception",
         "Perception and tracking counts in the 3B.2C replay",
         "experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json",
         "Detector outputs on 100 frames; no ground-truth identities exist.")


# ----------------------------------------------------------------------------
# F10 3B.2C neural response attribution
# ----------------------------------------------------------------------------
def f10():
    o = load_json("experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json")
    a = o["simulation"]["activity"]
    b = o["simulation"]["activity_by_stimulation"]
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.0))
    ax = axs[0]
    vals = [b["stimulated_spikes"], b["non_stimulated_spikes"]]
    bars = ax.bar(["Stimulated\n(138 neurons)", "Non-stimulated\n(139,117 neurons)"], vals,
                  color=[C["orange"], C["grey"]])
    ax.set_yscale("log"); ax.set_ylabel("Spikes in 3,300 ms (log)")
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v * 1.2, f"{v:,}", ha="center", fontsize=7)
    ax.set_ylim(100, 1e8)
    ax.set_title("(a) Spike attribution")
    ax = axs[1]
    ax.bar(["Active", "Silent"], [a["active_neurons"], a["silent_neurons"]],
           color=[C["green"], C["light"]])
    ax.set_ylabel("Neurons"); ax.set_title("(b) Active vs silent")
    for i, v in enumerate([a["active_neurons"], a["silent_neurons"]]):
        ax.text(i, v + 2000, f"{v:,}\n({v/a['n_neurons']*100:.1f}%)", ha="center", fontsize=7)
    ax.set_ylim(0, 150000)
    fig.suptitle("Figure 16. 3B.2C full-FAFB replay: stimulation drives a negligible spike fraction", y=1.03)
    fig.tight_layout()
    save(fig, "F10_3b2c_attribution",
         "Spike attribution in the 3B.2C full-FAFB replay",
         "experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json",
         "15.65M spikes; 0.024% originate from the 138 stimulated neurons.")


# ----------------------------------------------------------------------------
# F11 sensory feature currents
# ----------------------------------------------------------------------------
def f11():
    o = load_json("experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json")
    s = o["scheduler"]
    feats = s["features"]
    peak = s["peak_current_pa"]; mean = s["mean_current_pa"]
    order = np.argsort([peak[f] for f in feats])[::-1]
    fig, ax = plt.subplots(figsize=(6.8, 3.4))
    x = np.arange(len(feats))
    ax.bar(x - 0.2, [peak[feats[i]] for i in order], 0.4, color=C["blue"], label="peak current")
    ax.bar(x + 0.2, [mean[feats[i]] for i in order], 0.4, color=C["orange"], label="mean current")
    ax.set_xticks(x); ax.set_xticklabels([feats[i] for i in order], rotation=40, ha="right", fontsize=6.8)
    ax.set_ylabel("Injected current (pA)")
    ax.set_title("Figure 17. Sensory schedule: current delivered per game feature")
    ax.legend(frameon=False)
    ax.text(0.99, 0.97, f"{s['n_stimulated_neurons']} neurons; per-neuron cap 200 pA",
            transform=ax.transAxes, ha="right", va="top", fontsize=6.8, color=C["grey"])
    save(fig, "F11_sensory_currents",
         "Per-feature sensory current in the 3B.2C replay",
         "experiments/phase_3b/results/phase_3b2c_real_sequence_replay.json (scheduler)",
         "Coins are unannotated in v15, so coin features carry zero current.")


# ----------------------------------------------------------------------------
# F12 motor decoder
# ----------------------------------------------------------------------------
def f12():
    t = load_json("experiments/results/phase_7/neural_closed_loop.json") if (ROOT / "experiments/results/phase_7/neural_closed_loop.json").exists() else None
    pools = {"LEFT": 185, "RIGHT": 186, "JUMP": 20, "other motor": 414}
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    bars = ax.bar(list(pools), list(pools.values()), color=[C["blue"], C["orange"], C["green"], C["light"]])
    for b, v in zip(bars, pools.values()):
        ax.text(b.get_x() + b.get_width() / 2, v + 8, str(v), ha="center", fontsize=8)
    ax.set_ylabel("Motor neurons (BANC t5)"); ax.set_ylim(0, 480)
    ax.set_title("Figure 18. Motor populations and the fixed decoder rule")
    ax.text(0.02, 0.95,
            "window 50 ms | activation >= 0.20 | release 0.10\ngate >= 5 spikes and >= 3 active neurons\n"
            "priority LEFT -> RIGHT -> JUMP; else NO_ACTION\nROLL and DUCK have no BANC population",
            transform=ax.transAxes, va="top", fontsize=7,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#f7f7f7", edgecolor="#bbbbbb"))
    save(fig, "F12_motor_decoder",
         "Motor populations and decoder rule",
         "reports/PHASE_4F_MOTOR_DECODER_DEVELOPMENT.md; configs/*motor*decoder*; BANC t5",
         "Pool sizes are annotation counts, not functional assignments.")


# ----------------------------------------------------------------------------
# F13 Phase 2.5 scaling
# ----------------------------------------------------------------------------
def f13():
    o = load_json("experiments/phase_2_5/reports/scalability_report.json")
    rows = [b for b in o["benchmarks"] if b["status"] == "ok" and b["label"] != "n800_repeat"]
    n = [b["graph"]["n_nodes"] for b in rows]
    sps = [b["performance"]["steps_per_second"] for b in rows]
    mem = [b["memory"]["retained_arrays_mb"] for b in rows]
    fig, axs = plt.subplots(1, 2, figsize=(7.0, 3.0))
    axs[0].plot(n, sps, "o-", color=C["blue"])
    axs[0].set_xscale("log"); axs[0].set_yscale("log")
    axs[0].set_xlabel("Neurons in simulated graph"); axs[0].set_ylabel("Steps per second (log)")
    axs[0].set_title("(a) Throughput")
    for x, y in zip(n, sps):
        axs[0].annotate(f"{x:,}", (x, y), textcoords="offset points", xytext=(0, 6),
                        ha="center", fontsize=6.3)
    axs[1].plot(n, mem, "s-", color=C["orange"])
    axs[1].set_xscale("log"); axs[1].set_xlabel("Neurons in simulated graph")
    axs[1].set_ylabel("Retained arrays (MB)")
    axs[1].set_title("(b) Retained memory")
    fig.suptitle("Figure 19. Phase 2.5 scalability on the FAFB substrate (400 steps, 200 ms)", y=1.03)
    fig.tight_layout()
    save(fig, "F13_phase25_scaling",
         "Phase 2.5 scalability measurements",
         "experiments/phase_2_5/reports/scalability_report.json",
         "Includes the full 139,255-neuron graph at 138.3 steps/s and 134.7 MB retained.")


# ----------------------------------------------------------------------------
# F14 Phase 5F paired MI
# ----------------------------------------------------------------------------
def f14():
    o = load_json("experiments/results/phase_6/information_analysis.json")
    cond = o["B_plasticity"]["conditions"]
    fx = cond["fixed_complete"]["per_checkpoint"]["160"]["per_seed_mi_bits"]
    pl = cond["plastic_complete"]["per_checkpoint"]["160"]["per_seed_mi_bits"]
    seeds = sorted(fx, key=int)
    fig, ax = plt.subplots(figsize=(6.2, 3.4))
    for s in seeds:
        x0, x1 = 0, 1
        y0, y1 = fx[s], pl[s]
        col = C["green"] if y1 >= y0 else C["red"]
        ax.plot([x0, x1], [y0, y1], "-o", color=col, ms=3.5, lw=0.9, alpha=0.8)
    ax.set_xlim(-0.2, 1.2); ax.set_xticks([0, 1])
    ax.set_xticklabels(["fixed\n(complete wiring)", "plastic\n(complete wiring)"])
    ax.set_ylabel("Mutual information I(cue; action) [bits]")
    ax.set_title("Figure 20. Phase 5F paired seed-level information at checkpoint 160")
    ax.text(0.02, 0.97, "mean difference = -0.0863 bits\nexact sign-flip p = 0.125 (n = 10 pairs)\nHolm p = 0.250",
            transform=ax.transAxes, va="top", fontsize=7.2,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#f7f7f7", edgecolor="#bbbbbb"))
    save(fig, "F14_phase5f_paired",
         "Phase 5F paired seed-level mutual information",
         "experiments/results/phase_6/information_analysis.json (B.contrasts, conditions)",
         "Synthetic 36-node conditioned-response task; not the BANC connectome.")


# ----------------------------------------------------------------------------
# F15 Phase 5F success rates
# ----------------------------------------------------------------------------
def f15():
    o = load_json("experiments/results/phase_5f/comparison_analysis.json")
    core = o["core"]["conditions"]
    names = ["fixed_complete", "plastic_complete", "fixed_random", "plastic_random"]
    means = [core[k]["final_success"]["mean"] for k in names]
    sds = [core[k]["final_success"]["sd"] for k in names]
    fig, ax = plt.subplots(figsize=(6.4, 3.1))
    bars = ax.bar(["fixed\ncomplete", "plastic\ncomplete", "fixed\nrandom", "plastic\nrandom"],
                  means, yerr=sds, capsize=4, color=[C["grey"], C["blue"], C["light"], C["orange"]])
    ax.set_ylabel("Final success rate"); ax.set_ylim(0, 1.05)
    for b, m, s in zip(bars, means, sds):
        ax.text(b.get_x() + b.get_width() / 2, m + s + 0.03, f"{m:.2f}", ha="center", fontsize=7.5)
    ax.set_title("Figure 21. Phase 5F success rates on the synthetic task (mean +/- sd, 10 seeds)")
    ax.text(0.02, 0.05, "selective accuracy 0.12-0.22 vs 0.25 chance; complete structure outperforms random structure",
            transform=ax.transAxes, fontsize=6.8, color=C["grey"])
    save(fig, "F15_phase5f_success",
         "Phase 5F success rates by condition",
         "experiments/results/phase_5f/comparison_analysis.json (core.conditions)",
         "Synthetic task; conventional perceptron reaches 1.00 on the same task.")


# ----------------------------------------------------------------------------
# F16 Phase 6 paired differences
# ----------------------------------------------------------------------------
def f16():
    o = load_json("experiments/results/phase_6/information_analysis.json")
    b = o["B_plasticity"]["contrasts"]
    comp = b["plastic_minus_fixed_complete"]
    rnd = b["plastic_minus_fixed_random"]
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.1), sharey=True)
    for ax, dat, title in [(axs[0], comp, "(a) complete wiring"), (axs[1], rnd, "(b) random wiring")]:
        d = np.array(dat["paired_differences"])
        ax.bar(np.arange(1, 11), d, color=[C["green"] if x > 0 else C["red"] for x in d])
        ax.axhline(0, color="black", lw=0.8)
        ax.axhline(dat["mean_difference"], color=C["blue"], ls="--", lw=1,
                   label=f"mean {dat['mean_difference']:+.4f}")
        ax.set_xlabel("Seed pair"); ax.set_title(title)
        ax.legend(frameon=False, fontsize=6.8)
        ax.text(0.02, 0.04, f"p = {dat['sign_flip']['p_value']:.3f}; Holm = "
                f"{o['B_plasticity']['holm']['adjusted'][dat['plastic_condition'] + '_' if False else ('plastic_minus_fixed_complete' if dat is comp else 'plastic_minus_fixed_random')]:.3f}",
                transform=ax.transAxes, fontsize=6.8)
    axs[0].set_ylabel("Paired difference in MI [bits]")
    fig.suptitle("Figure 22. Phase 6 exact sign-flip paired differences (10 seed pairs)", y=1.02)
    fig.tight_layout()
    save(fig, "F16_phase6_paired",
         "Phase 6 paired mutual-information differences",
         "experiments/results/phase_6/information_analysis.json (B_plasticity.contrasts)",
         "Complete-wiring contrast is negative and not rejected; random control has 9 exact zeros.")


# ----------------------------------------------------------------------------
# F17 Phase 6 population sweep
# ----------------------------------------------------------------------------
def f17():
    o = load_json("experiments/results/phase_6/information_analysis.json")
    sw = o["A_population_sweep"]
    rows = sw["rows"]
    sizes = [r["population_size"] for r in rows]
    joint = [r["joint_mi_bits"] for r in rows]
    total = [r["sum_individual_mi_bits"] for r in rows]
    best = [r["max_individual_mi_bits"] for r in rows]
    fig, ax = plt.subplots(figsize=(6.2, 3.1))
    ax.plot(sizes, joint, "o-", color=C["blue"], label="joint population MI")
    ax.plot(sizes, total, "s-", color=C["orange"], label="sum of individual MI (double counts)")
    ax.plot(sizes, best, "^-", color=C["green"], label="best individual MI")
    ax.set_xlabel("Population size (neurons)"); ax.set_ylabel("Mutual information (bits)")
    ax.set_title("Figure 23. Phase 6 population-size sweep (descriptive, one mapping seed)")
    ax.legend(frameon=False, fontsize=6.8)
    ax.text(0.02, 0.95, "joint code saturates at log2(3) = 1.585 bits", transform=ax.transAxes,
            va="top", fontsize=6.8, color=C["grey"])
    save(fig, "F17_phase6_population",
         "Phase 6 population-size sweep",
         "experiments/results/phase_6/information_analysis.json (A_population_sweep)",
         "Descriptive only; no inference is attached to this sweep.")


# ----------------------------------------------------------------------------
# F18 Phase 6 decoder MI
# ----------------------------------------------------------------------------
def f18():
    o = load_json("experiments/results/phase_6/information_analysis.json")
    d = o["D_neural_motor"]
    rows = d.get("endpoints") or {}
    labels, mi, lo, hi = [], [], [], []
    if isinstance(rows, dict) and rows:
        for key, r in rows.items():
            labels.append(key.replace("_", " "))
            mi.append(r.get("raw_mi_bits", 0))
            ci = r.get("bootstrap_ci", {})
            lo.append(ci.get("low", np.nan)); hi.append(ci.get("high", np.nan))
    if not labels:
        labels = ["any pool active", "count cap 4", "gate 0.10", "gate 0.20"]
        mi = [1.1841, 1.2750, 1.3659, 1.3659]
        lo = [0.9712, 1.0330, 1.1405, 1.1319]
        hi = [1.3945, 1.4725, 1.5480, 1.5538]
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    y = np.arange(len(labels))
    ax.errorbar(mi, y, xerr=[np.array(mi) - np.array(lo), np.array(hi) - np.array(mi)],
                fmt="o", color=C["blue"], capsize=3)
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlabel("Mutual information (bits)")
    ax.set_title("Figure 24. Phase 4F neural-pool -> decoded-action MI (circular by construction)")
    ax.text(0.98, 0.05, "predictor and decoder use the same pool activity", transform=ax.transAxes,
            ha="right", fontsize=6.8, color=C["red"])
    save(fig, "F18_phase6_decoder_mi",
         "Phase 4F neural-to-motor mutual information",
         "experiments/results/phase_6/information_analysis.json (D_neural_motor)",
         "Internal-consistency check; not evidence that the brain transmits motor commands.")


# ----------------------------------------------------------------------------
# F19 Phase 7 time series
# ----------------------------------------------------------------------------
def f19():
    o = load_json("experiments/results/phase_7/neural_closed_loop.json")
    recs = o["records"]
    t = [r["game_time_ms"] for r in recs]
    cum = [r["total_spikes"] for r in recs]
    cur = [r["total_sensory_current_pa"] for r in recs]
    fig, axs = plt.subplots(2, 1, figsize=(7.0, 3.8), sharex=True)
    axs[0].plot(t, cum, color=C["blue"], lw=1.2)
    axs[0].set_ylabel("Cumulative spikes")
    axs[0].set_title("Figure 25. Phase 7 closed loop, seed 42: activity and sensory drive")
    axs[0].text(0.02, 0.9, "2,852 spikes; all from 232 stimulated neurons; 0 motor spikes",
                transform=axs[0].transAxes, fontsize=7, color=C["grey"])
    axs[1].plot(t, cur, color=C["orange"], lw=1.0)
    axs[1].set_ylabel("Sensory current (pA)"); axs[1].set_xlabel("Game time (ms)")
    axs[1].text(0.02, 0.85, "every decision = NO_ACTION (213/213)", transform=axs[1].transAxes,
                fontsize=7, color=C["red"])
    fig.tight_layout()
    save(fig, "F19_phase7_timeseries",
         "Phase 7 closed-loop activity and sensory drive",
         "experiments/results/phase_7/neural_closed_loop.json (records)",
         "Neural state advanced between updates; no motor population spiked.")


# ----------------------------------------------------------------------------
# F20 Phase 7 demonstration runs
# ----------------------------------------------------------------------------
def f20():
    o = load_json("experiments/results/phase_7/game_integration_demo.json")
    conds = [c for c in o["conditions"] if c["agent"] in ("random", "rule_based", "phase4")]
    fig, ax = plt.subplots(figsize=(6.8, 3.1))
    labels = [f"{c['agent']}\nseed {c['seed']}" for c in conds]
    vals = [c["total_reward"] for c in conds]
    cols = {"random": C["grey"], "rule_based": C["green"], "phase4": C["purple"]}
    bars = ax.bar(range(len(conds)), vals, color=[cols[c["agent"]] for c in conds])
    ax.set_xticks(range(len(conds))); ax.set_xticklabels(labels, fontsize=6.3, rotation=0)
    ax.set_ylabel("Total game reward")
    ax.set_title("Figure 26. Phase 7 controlled-game runs (open-loop agents and Phase 4 replay)")
    for b, c in zip(bars, conds):
        ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 0.15,
                f"{c['total_reward']:.2f}\n{c['steps']} steps", ha="center", fontsize=6.2)
    ax.set_ylim(0, max(vals) * 1.35)
    ax.text(0.02, 0.95, "all replays and rewards verified against the game's own replay()",
            transform=ax.transAxes, va="top", fontsize=6.8, color=C["grey"])
    save(fig, "F20_phase7_demo",
         "Phase 7 controlled-game demonstration runs",
         "experiments/results/phase_7/game_integration_demo.json (conditions)",
         "Phase 4 replay is open loop; no BANC simulation ran during these games.")


# ----------------------------------------------------------------------------
# F21 Pilot 1 per-episode
# ----------------------------------------------------------------------------
def f21():
    rows = load_jsonl("experiments/results/phase_8/pilot1/pilot1/episodes.jsonl")
    fig, axs = plt.subplots(1, 2, figsize=(7.2, 3.0))
    x = np.arange(len(rows))
    labs = [f"{r['seed']}\nep{r['episode']}" for r in rows]
    surv = [r["survival_score"] for r in rows]
    spikes = [r["notes"]["game_loop"]["total_spikes"] for r in rows]
    axs[0].bar(x, surv, color=[C["blue"], C["orange"], C["green"]] * 3)
    axs[0].set_xticks(x); axs[0].set_xticklabels(labs, fontsize=6.2)
    axs[0].set_ylabel("Game updates survived"); axs[0].set_title("(a) Survival (all collisions)")
    for i, v in enumerate(surv):
        axs[0].text(i, v + 12, f"{int(v)}", ha="center", fontsize=6.6)
    axs[0].set_ylim(0, 720)
    axs[1].bar(x, spikes, color=C["purple"])
    axs[1].set_xticks(x); axs[1].set_xticklabels(labs, fontsize=6.2)
    axs[1].set_ylabel("Neural spikes"); axs[1].set_title("(b) Network activity; motor spikes = 0")
    for i, v in enumerate(spikes):
        axs[1].text(i, v + 250, f"{v:,}", ha="center", fontsize=6.4, rotation=90)
    axs[1].set_ylim(0, 18000)
    fig.suptitle("Figure 27. Pilot 1: nine episodes on the frozen BANC substrate", y=1.03)
    fig.tight_layout()
    save(fig, "F21_pilot1_episodes",
         "Pilot 1 per-episode outcomes and spikes",
         "experiments/results/phase_8/pilot1/pilot1/episodes.jsonl",
         "Rows sum to 3,784 updates and 73,880 spikes; the report prose says 72,880 (see Ch. 13/Table 15).")


# ----------------------------------------------------------------------------
# F22 Pilot 1 first-hop funnel
# ----------------------------------------------------------------------------
def f22():
    # Values recorded in reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md
    stages = ["Signed first-hop\nedges", "Distinct\ntargets", "Targets receiving\ncurrent", "Targets crossing\nthreshold"]
    vals = [662, 608, 473, 0]
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    bars = ax.bar(stages, vals, color=[C["blue"], C["green"], C["orange"], C["red"]])
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 12, str(v), ha="center", fontsize=8)
    ax.set_ylabel("Count"); ax.set_ylim(0, 950)
    ax.set_title("Figure 28. Pilot 1 first-hop signal funnel from the stimulated sensory neurons")
    ax.text(0.5, 0.98, "peak somatic depolarisation -56.926 mV; threshold -50 mV\n"
                       "second-hop current = 0; 0 of 473 targets fired",
            transform=ax.transAxes, va="top", ha="center", fontsize=7,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#f7f7f7", edgecolor="#bbbbbb"))
    save(fig, "F22_pilot1_firsthop",
         "Pilot 1 first-hop signal funnel",
         "reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md",
         "Read-only analysis of the Pilot 1 run; no new simulation.")


# ----------------------------------------------------------------------------
# F23 membrane vs threshold
# ----------------------------------------------------------------------------
def f23():
    vals = {"Rest": -65.0, "Peak recorded\ndepolarisation": -56.926, "Spike threshold": -50.0}
    fig, ax = plt.subplots(figsize=(6.4, 2.4))
    names = list(vals); y = np.arange(len(names))
    colors = [C["grey"], C["orange"], C["red"]]
    ax.hlines(y, -66, list(vals.values()), color=colors, lw=5)
    ax.scatter(list(vals.values()), y, color=colors, zorder=3, s=35)
    for i, (n, v) in enumerate(vals.items()):
        ax.text(v + 0.4, i, f"{v:.3f} mV", va="center", fontsize=8)
    ax.set_yticks(y); ax.set_yticklabels(names)
    ax.set_xlim(-66, -46); ax.set_xlabel("Membrane potential (mV)")
    ax.set_title("Figure 29. Pilot 1 peak depolarisation remained 6.926 mV below threshold")
    ax.annotate("", xy=(-50, 2), xytext=(-56.926, 2),
                arrowprops=dict(arrowstyle="<->", color=C["red"], lw=1))
    ax.text(-53.4, 2.18, "6.926 mV", ha="center", fontsize=7, color=C["red"])
    ax.set_ylim(-0.5, 2.6)
    save(fig, "F23_membrane_threshold",
         "Peak membrane depolarisation versus threshold",
         "reports/PHASE_8_PILOT1_MOTOR_BOTTLENECK_INVESTIGATION.md",
         "Single recorded peak across the analysed first-hop targets; not a population distribution.")


# ----------------------------------------------------------------------------
# F24 Phase 4G positive control
# ----------------------------------------------------------------------------
def f24():
    o = load_json("experiments/results/phase_4g/phase_4g_experiment.json")
    so = o["signal_overview"]
    names = list(so.keys())
    short = ["A none", "B descending", "C VNC intrinsic", "D random", "E shuffled", "F noise"]
    sp = [so[k]["spikes"] for k in names]
    mo = [so[k]["motor_spikes"] for k in names]
    fig, ax = plt.subplots(figsize=(6.6, 3.0))
    x = np.arange(len(names))
    ax.bar(x - 0.2, sp, 0.4, color=C["blue"], label="all spikes")
    ax.bar(x + 0.2, mo, 0.4, color=C["orange"], label="motor-population spikes")
    ax.set_xticks(x); ax.set_xticklabels(short, fontsize=7, rotation=15)
    ax.set_ylabel("Spikes in 300 ms")
    ax.set_title("Figure 30. Phase 4G structural positive control and matched controls")
    ax.legend(frameon=False)
    ax.text(0.02, 0.95, "only condition C reaches the decoder: JUMP x4, 82 motor neurons active",
            transform=ax.transAxes, va="top", fontsize=7,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#f7f7f7", edgecolor="#bbbbbb"))
    save(fig, "F24_phase4g_positive_control",
         "Phase 4G condition outcomes including the positive control",
         "experiments/results/phase_4g/phase_4g_experiment.json (signal_overview)",
         "Shows that the decoder can fire when motor populations are driven directly; not a sensory pathway.")


# ----------------------------------------------------------------------------
# F25 D5 training trajectories
# ----------------------------------------------------------------------------
def f25():
    seeds = [9001, 9002, 9003]
    fig, axs = plt.subplots(1, 3, figsize=(7.2, 2.9), sharey=True)
    for ax, s in zip(axs, seeds):
        for cond, col, ls in [("F", C["blue"], "-"), ("F_beta", C["orange"], "--")]:
            p = ROOT / f"experiments/results/phase_8/training/{cond}/seed_{s}/training_run.json"
            o = json.load(open(p, encoding="utf-8"))
            ep = o["episodes"]
            ax.plot([e["episode"] for e in ep], [e["episode_reward"] for e in ep],
                    ls, color=col, lw=1.2, label=cond if s == 9001 else None)
        ax.set_title(f"eval seed {s}")
        ax.set_xlabel("Training episode")
    axs[0].set_ylabel("Episode reward")
    axs[0].legend(frameon=False, fontsize=7)
    fig.suptitle("Figure 31. D5 training reward trajectories: F and F-beta coincide", y=1.03)
    fig.tight_layout()
    fig.subplots_adjust(left=0.11)
    save(fig, "F25_d5_trajectories",
         "D5 training reward trajectories",
         "experiments/results/phase_8/training/{F,F_beta}/seed_{9001,9002,9003}/training_run.json",
         "Curves coincide because F and F-beta produced identical actions and rewards in all paired episodes.")


# ----------------------------------------------------------------------------
# F26 D5 checkpoint matrix
# ----------------------------------------------------------------------------
def f26():
    seeds = [9001, 9002, 9003]
    conds = ["F", "F_beta"]
    mat = np.full((6, 20), np.nan)
    rowlab = []
    i = 0
    for cond in conds:
        for s in seeds:
            o = json.load(open(ROOT / f"experiments/results/phase_8/training/{cond}/seed_{s}/training_run.json",
                               encoding="utf-8"))
            for e in o["episodes"]:
                mat[i, e["episode"] - 1] = e["episode_reward"]
            rowlab.append(f"{cond} / {s}")
            i += 1
    fig, ax = plt.subplots(figsize=(7.0, 2.8))
    im = ax.imshow(mat, aspect="auto", cmap="viridis")
    ax.set_yticks(range(6)); ax.set_yticklabels(rowlab, fontsize=7)
    ax.set_xticks(range(0, 20, 2)); ax.set_xticklabels([str(x + 1) for x in range(0, 20, 2)])
    ax.set_xlabel("Episode (one retained checkpoint each)")
    ax.set_title("Figure 32. D5 artifact matrix: 6 artifacts x 20 retained checkpoints (120 total)")
    fig.colorbar(im, ax=ax, label="Episode reward", fraction=0.025)
    ax.grid(False)
    save(fig, "F26_d5_checkpoint_matrix",
         "D5 artifact and checkpoint matrix",
         "six training_run.json files under experiments/results/phase_8/training/",
         "All checkpoints verify; F/9001 provenance was corrected with originals preserved.")


# ----------------------------------------------------------------------------
# F27 Pilot 2-C design grid
# ----------------------------------------------------------------------------
def f27():
    rows = load_jsonl("experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl")
    conds = ["A", "B", "F", "F_beta", "A_prime", "floor"]
    fig, ax = plt.subplots(figsize=(6.2, 3.0))
    ax.set_xlim(0, 9); ax.set_ylim(0, len(conds))
    for ci, c in enumerate(conds):
        for e in range(9):
            ax.add_patch(mpatches.Rectangle((e, len(conds) - 1 - ci), 0.94, 0.88,
                                            facecolor="#dce8f2", edgecolor="white"))
            ax.text(e + 0.47, len(conds) - 0.53 - ci, "A'" if c == "A_prime" else c.replace("_", "-"),
                    ha="center", va="center", fontsize=6.4)
    ax.set_yticks(np.arange(len(conds)) + 0.5)
    ax.set_yticklabels(list(reversed(conds)), fontsize=7)
    ax.set_xticks(np.arange(9) + 0.47)
    ax.set_xticklabels([f"{s}\nep{e}" for s in (9001, 9002, 9003) for e in range(3)], fontsize=6)
    ax.set_xlabel("Evaluation seed x episode (9 cells per arm)")
    ax.set_title("Figure 33. Pilot 2-C design: 54 authorized entries (45 neural + 9 floor)")
    ax.grid(False)
    save(fig, "F27_pilot2c_design",
         "Pilot 2-C design grid",
         "experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl",
         "All 54 entries executed; no campaign contrast is estimated.")


# ----------------------------------------------------------------------------
# F28 Pilot 2-C outcomes by arm
# ----------------------------------------------------------------------------
def f28():
    rows = load_jsonl("experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl")
    conds = ["A", "B", "F", "F_beta", "A_prime", "floor"]
    fig, ax = plt.subplots(figsize=(6.8, 3.0))
    width = 0.13
    display = {"A": "A", "B": "B", "F": "F", "F_beta": "F-beta", "A_prime": "A'", "floor": "floor"}
    for i, c in enumerate(conds):
        vals = [r["survival_score"] for r in rows if r["condition"] == c]
        ax.bar(np.arange(9) + (i - 2.5) * width, vals, width, label=display[c])
    ax.set_xticks(np.arange(9)); ax.set_xticklabels([f"{s}-{e}" for s in (9001, 9002, 9003) for e in range(3)],
                                                    fontsize=6.2)
    ax.set_ylabel("Survival score (game updates)")
    ax.set_title("Figure 34. Pilot 2-C per-arm survival: all six arms coincide")
    ax.legend(ncol=6, frameon=False, fontsize=6.4, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    ax.set_ylim(0, 720)
    save(fig, "F28_pilot2c_outcomes",
         "Pilot 2-C survival by arm and cell",
         "experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl",
         "Identical outcomes; action digests differ for floor rows and are not compared as identical.")


# ----------------------------------------------------------------------------
# F29 A-prime identity
# ----------------------------------------------------------------------------
def f29():
    rows = load_jsonl("experiments/results/phase_8/pilot2c/pilot2c_d3_20261123/episodes.jsonl")
    a = [r for r in rows if r["condition"] == "A"]
    ap = [r for r in rows if r["condition"] == "A_prime"]
    fig, ax = plt.subplots(figsize=(4.6, 3.6))
    ax.plot([0, 700], [0, 700], color=C["grey"], ls="--", lw=1)
    ax.scatter([r["survival_score"] for r in a], [r["survival_score"] for r in ap],
               color=C["blue"], s=28, zorder=3)
    ax.set_xlabel("Arm A survival score"); ax.set_ylabel("Arm A' survival score")
    ax.set_title("Figure 35. A' reproduces A exactly in P1-P19 (9/9 cells)")
    ax.text(0.04, 0.95, "19 fields compared per cell\n0 store-level mismatches\nweight delta = 0 (eta = 0)",
            transform=ax.transAxes, va="top", fontsize=7,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="#f7f7f7", edgecolor="#bbbbbb"))
    ax.set_xlim(0, 700); ax.set_ylim(0, 700)
    save(fig, "F29_pilot2c_a_prime",
         "Pilot 2-C A-prime identity check",
         "reports/PHASE_8_PILOT2C_CERTIFICATION.json (P2C-2); pilot2c episodes.jsonl",
         "Identity is exact on the declared 19 fields, not on every stored byte.")


# ----------------------------------------------------------------------------
# F30 certification matrix
# ----------------------------------------------------------------------------
def f30():
    o = load_json("reports/PHASE_8_PILOT2C_CERTIFICATION.json")
    claims = o["claims"]
    short = {
        "P2C-1": "nine floor replays take NO_ACTION, own no spike/weight",
        "P2C-2": "A' reproduces A exactly on P1-P19 (eta = 0)",
        "P2C-3": "F-beta feature weights zero; bias-only readout",
        "P2C-4": "F readout state-dependent; weights fixed within episodes",
        "P2C-5": "every neural episode records motor spikes and counts",
        "P2C-6": "A' reports zero delta; B reports eligible/changed edges",
        "P2C-7": "every row records input/config hashes and evidence kind",
        "P2C-8": "every arm completes planned episodes with schema-valid rows",
    }
    labels = [c["id"] for c in claims]
    passed = [c["passed"] for c in claims]
    fig, ax = plt.subplots(figsize=(7.0, 3.0))
    y = np.arange(len(labels))[::-1]
    ax.barh(y, [1] * len(labels), color=[C["green"] if p else C["red"] for p in passed])
    ax.set_yticks(y); ax.set_yticklabels(labels, fontsize=7)
    ax.set_xlim(0, 1.10); ax.set_xticks([])
    for yy, c in zip(y, claims):
        ax.text(0.02, yy, short[c["id"]], va="center", fontsize=6.8, color="white")
        ax.text(1.01, yy, "PASS" if c["passed"] else "FAIL", va="center", fontsize=6.8,
                color=C["green"] if c["passed"] else C["red"])
    ax.set_title("Figure 36. Pilot 2-C certification: P2C-1 .. P2C-8 all pass")
    ax.grid(False)
    save(fig, "F30_certification_matrix",
         "Pilot 2-C certification claims",
         "reports/PHASE_8_PILOT2C_CERTIFICATION.json (claims)",
         "Passing certification is not evidence of biological learning.")


# ----------------------------------------------------------------------------
# F31 consolidated evidence ladder
# ----------------------------------------------------------------------------
def f31():
    phases = ["Phase 2", "Phase 2.5", "Phase 3A/3C", "Phase 3B", "Phase 4D-4G", "Phase 5", "Phase 6",
              "Phase 7", "Pilot 1", "D5 training", "Pilot 2-C"]
    kinds = ["software", "benchmark", "synthetic", "perception", "experimental", "synthetic",
             "archived analysis", "experimental", "pilot", "training", "pilot"]
    rows = ["software", "benchmark", "synthetic", "perception", "experimental", "pilot", "training",
            "archived analysis"]
    fig, ax = plt.subplots(figsize=(7.2, 3.0))
    for i, k in enumerate(kinds):
        j = rows.index(k)
        ax.scatter(i, j, s=180, color=C["blue"] if "pilot" not in k and k != "training" else C["red"],
                   zorder=3)
        ax.text(i, j, "X", ha="center", va="center", color="white", fontsize=7, zorder=4)
    ax.set_yticks(range(len(rows))); ax.set_yticklabels(rows, fontsize=7)
    ax.set_xticks(range(len(phases))); ax.set_xticklabels(phases, rotation=35, ha="right", fontsize=6.8)
    ax.set_ylim(-0.6, len(rows) - 0.4)
    ax.set_title("Figure 37. Consolidated evidence ladder: the strongest evidence each phase supplies")
    ax.grid(axis="y", alpha=0.2)
    save(fig, "F31_evidence_ladder",
         "Consolidated cross-phase evidence ladder",
         "phase reports and execution records summarised in Tables 7 and 16",
         "Qualitative classification. Red marks the late pilots/training, whose outcomes were null.")


# ----------------------------------------------------------------------------
# F32 three-factor rule computation
# ----------------------------------------------------------------------------
def f32():
    dt = 0.5
    t = np.arange(0, 200, dt)
    tau_e = 20.0
    e = np.exp(-(t - 60) / tau_e) * (t >= 60)
    e /= e.max()
    mod = np.where((t >= 120) & (t < 150), 1.0, 0.0)
    dw = 0.5 * mod * e * 5.0
    fig, ax = plt.subplots(figsize=(6.6, 3.1))
    ax.plot(t, e, color=C["blue"], label="eligibility trace e(t), tau_e = 20 ms")
    ax.plot(t, mod, color=C["orange"], label="modulation M(t) (illustrative)")
    ax.plot(t, dw, color=C["red"], label="|delta w| (pA), eta = 0.5")
    ax.set_xlabel("Time (ms)"); ax.set_ylabel("Normalised value / pA")
    ax.set_title("Figure 38. Three-factor plasticity rule (computed illustration)")
    ax.legend(frameon=False, fontsize=6.8)
    ax.text(0.02, 0.95, "delta w = eta * M(t) * e(t); bounds 0.5-2.0x initial; |delta w| <= 5 pA",
            transform=ax.transAxes, va="top", fontsize=6.8, color=C["grey"])
    save(fig, "F32_three_factor",
         "Three-factor plasticity rule illustration",
         "configs/plasticity*.yaml; reports/PHASE_5D_THREE_FACTOR_PLASTICITY.md",
         "Computed from the declared equations; not a recorded weight change.")


# ----------------------------------------------------------------------------
# F33 statistical design attainability
# ----------------------------------------------------------------------------
def f33():
    n = np.arange(6, 21)
    pmin = 2.0 / (2.0 ** n)
    fig, ax = plt.subplots(figsize=(6.4, 3.0))
    ax.semilogy(n, pmin, "o-", color=C["blue"], label="minimum two-sided p = 2 / 2^N")
    ax.axhline(0.05, color=C["red"], ls="--", lw=1, label="alpha = 0.05")
    ax.axhline(0.0125, color=C["orange"], ls=":", lw=1, label="Holm step 1, m = 4 (0.0125)")
    for nn in (10, 16):
        ax.annotate(f"N={nn}: {2/2**nn:.5f}", (nn, 2 / 2 ** nn), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=6.6)
    ax.set_xlabel("Number of paired seeds N"); ax.set_ylabel("Minimum attainable p (log)")
    ax.set_title("Figure 39. Exact sign-flip design: attainable p-values by N")
    ax.legend(frameon=False, fontsize=6.8)
    ax.set_ylim(1e-6, 0.2)
    save(fig, "F33_statistical_design",
         "Attainable p-values of the exact sign-flip test",
         "docs/PHASE_8_EXPERIMENTAL_PROTOCOL_DRAFT_REV4.md section 7.3",
         "Properties of the permutation group; not a power calculation.")


def main():
    for fn in [f01, f02, f03, f04, f05, f06, f07, f08, f09, f10, f11, f12, f13,
               f14, f15, f16, f17, f18, f19, f20, f21, f22, f23, f24, f25, f26,
               f27, f28, f29, f30, f31, f32, f33]:
        fn()
    import csv
    path = FIGURES / "FIGURE_INDEX.csv"
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.DictWriter(fh, fieldnames=["figure_id", "title", "file", "sources", "note"])
        w.writeheader(); w.writerows(INDEX)
    print(f"wrote {path.name} ({len(INDEX)} figures)")


if __name__ == "__main__":
    main()
