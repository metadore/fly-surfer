# Phase 8 — GPU Readiness Checklist

**Prepared:** 2026-11-20
**Scope:** Measurement and checklist only. No Pilot 1 episode was run, no training
run was started, no campaign was executed, no package was installed, and no
configuration, protocol or Git state was changed.
**Snapshot verdict:** **GPU present and compatible; current Phase 8 runtime is
CPU-only; no GPU is required by Pilot 1.**

This document is a waiting-period artifact. It records what the machine can do
today and what must be re-checked immediately before any run. It is not an
execution authorisation; B7 and every other gate are unchanged (§9).

---

## 1. Why the GPU matters here — and where it does not

| Phase 8 work | Substrate | GPU needed? |
|---|---|---|
| Pilot 1 (condition A only, 3 seeds × 3 episodes) | Biological graph, `LiveBancStepper`, controlled environment via `environment/live_loop.py` | **No.** CPU, single process; the binding resource is system RAM (4.0 GiB gate) |
| Condition families A/B/C/D/F … | Same neural closed loop | **No** declared GPU dependency |
| Training artifacts (F, Fβ, F_init; E/E_full conventional) | `torch` tensors in `experiments/phase_8/training/` and `readout/` | **Not today.** The installed `torch` is a CPU build and no stage selects a CUDA device |
| Perception (YOLO11n detector) | `perception/inference.py` via `onnxruntime` | **Currently CPU.** `perception/detector_config.py` defaults `providers=("CPUExecutionProvider",)`; no Phase 8 stage uses the detector |

No file under `experiments/phase_8/` references `cuda`, `torch.device` or a device
selection, so the declared Phase 8 pipeline does not consume VRAM. Installing a
CUDA-enabled stack would be an environment change with no current Phase 8
consumer, and is therefore not required to unblock Pilot 1.

---

## 2. Measured snapshot (2026-11-20 15:43 local)

| Item | Measured value | Source |
|---|---|---|
| GPU | NVIDIA GeForce RTX 3050 Laptop GPU (WDDM) | `nvidia-smi` |
| Driver / KMD | 610.91 | `nvidia-smi` |
| CUDA UMD version | 13.3 | `nvidia-smi` |
| Compute capability | 8.6 | `nvidia-smi --query-gpu=compute_cap` |
| VRAM total | 4096 MiB (4.000 GiB) | `nvidia-smi` |
| VRAM used / free | 0 MiB / 3962 MiB | `nvidia-smi` |
| GPU utilisation | 0 %, P8, 3 W / 30 W cap | `nvidia-smi` |
| Temperature | 52 °C | `nvidia-smi` |
| ECC | N/A (consumer GPU) | `nvidia-smi` |
| System RAM total | 15.342 GiB | `psutil.virtual_memory()` |
| System RAM available | 5.494 GiB | `psutil.virtual_memory()` |
| System RAM used | 64.2 % | `psutil.virtual_memory()` |
| OS | Windows 11 10.0.26200 | `platform.platform()` |
| Python | 3.13.14 (CPython) | `sys.version` |
| torch | 2.10.0 **+cpu** (`torch.cuda.is_available()` → `False`) | import |
| onnxruntime | 1.29.0; providers `AzureExecutionProvider`, `CPUExecutionProvider` | import |
| CUDA toolkit (`nvcc`) | absent | `nvcc --version` |
| `cupy` / `cuda` Python packages | absent | `importlib.util.find_spec` |
| numpy / scipy / pandas / matplotlib / numba / tensorflow | 2.3.4 / 1.16.3 / 2.3.3 / 3.10.7 / 0.65.1 / 2.21.0 | `importlib.metadata` |

---

## 3. Available VRAM — PASS (not currently needed)

- **Total 4.000 GiB, free 3.962 GiB at snapshot.** The GPU is a mobile part on a
  shared-memory laptop, so free VRAM is a floor, not a guarantee: display,
  browser and other applications can reclaim it between checks.
- **No Phase 8 stage allocates VRAM today**, so this figure does not gate Pilot 1.
- **If GPU offload is adopted later**, the pass criterion is at least 1.0 GiB of
  free VRAM *after* the model, input buffers and cuDNN workspace are allocated,
  measured on the same driver and the same session as the run. A 4 GiB laptop
  GPU leaves little headroom for a YOLO11n session plus a neural simulator; run
  it as a measured pilot, not an assumption.

## 4. Available system RAM — PASS at snapshot against the 4.0 GiB gate

- Gate: `psutil.virtual_memory().available / 1024**3 >= 4.0`
  (`configs/phase_8/campaign.yaml`, `memory_gate_gb: 4.0`; enforced by the
  campaign preflight and by `stages/common.py`).
- Measured: **5.494 GiB available**, i.e. a **1.494 GiB margin** at this instant.
  That is the same instrument and the same gate that produced the G3/B7
  deviation, which observed a **1.628 GiB minimum free** during BANC-scale work.
  A laptop with 15.342 GiB total and 64.2 % already in use can cross the gate
  under ordinary background load.
- Therefore: **the gate passes now, and it must be re-measured immediately
  before any run.** A PASS here does not resolve B7 (§9).

## 5. GPU compatibility — PASS for the hardware, unverified for a GPU stack

- RTX 3050 Laptop, compute capability **8.6**, is supported by current CUDA
  toolkits and by CUDA-enabled ONNX Runtime / PyTorch builds.
- Driver 610.91 reports **CUDA UMD 13.3**, so a CUDA 12.x/13.x runtime is within
  the driver's capability. Exact runtime selection must be checked against the
  build actually installed, not assumed.
- ECC is not available on this consumer GPU; bit-for-bit reproducibility must
  therefore come from the code path (seeded CPU execution, recorded hashes), not
  from ECC-protected device memory.
- No GPU stack is currently installed (§6), so hardware compatibility is
  satisfied but *software* compatibility with the GPU is **not yet exercised**.

## 6. Required software/runtime — FAIL for GPU execution, PASS for the declared pipeline

| Component | Required for GPU execution | Installed | Status |
|---|---|---|---|
| NVIDIA driver | present | 610.91, CUDA UMD 13.3 | PASS |
| CUDA toolkit (`nvcc`) | needed only to build custom kernels | absent | not required for prebuilt wheels |
| PyTorch CUDA build | `torch` with CUDA | **2.10.0+cpu** | **FAIL** — `torch.cuda.is_available()` is `False` |
| ONNX Runtime GPU | `onnxruntime-gpu` with `CUDAExecutionProvider` | `onnxruntime` 1.29.0, CPU/Azure only | **FAIL** for detector GPU offload |
| YOLO11n ONNX artifact | present | `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx`, 10,636,871 bytes, SHA-256 `e6ad18f9…6aa77` | PASS (artifact), CPU execution only |
| YOLO11n `best.pt` | present | 5,491,034 bytes, SHA-256 `1b47a433…bdef8` | PASS (artifact), not loaded |
| Detectron/other accelerated backends | not used | — | — |

**Interpretation:** the declared Phase 8 pipeline runs correctly on the installed
CPU stack (torch CPU build and CPU ONNX Runtime are both present and importable).
GPU execution is *not currently possible* without replacing the installed builds
with CUDA variants. Doing so would modify the Python environment; no install was
performed, and none is required for Pilot 1.

## 7. Model execution compatibility — PASS on CPU, GPU path not built

- The detector artifact loads and exposes the contract recorded in
  `model_config.json`: input `images` `[1, 3, 640, 640]` float32 (NCHW, RGB),
  output `output0` `[1, 18, 8400]` float32, 14 classes, NMS applied by the
  caller. A CPU `InferenceSession` was created successfully during this
  measurement; no image was inferred and no evaluation was run.
- Input/output shapes match the recorded deployment contract, so the CPU path is
  structurally compatible. The GPU path cannot be assessed until
  `onnxruntime-gpu` (or the CUDA torch build for training artifacts) is present.
- The Phase 8 training modules (`experiments/phase_8/training/state.py`,
  `readout/linear.py`, `readout/trainer.py`) import `torch`; they construct no
  CUDA tensors, so the CPU build is the supported configuration today.
- Nothing here shows that a 4 GiB mobile GPU can host the simulator *and* a
  detector *and* training at once. That combination has not been tested and
  should not be assumed.

## 8. Final resource preflight — procedure to run immediately before any run

Execute in this order, on the same machine state that will run the experiment,
and attach the output to the run manifest. **A PASS in every row is necessary,
not sufficient**: authorization gates (§9) are checked separately by the code.

1. **Free RAM against the gate**
   `python -c "import psutil;v=psutil.virtual_memory();print(round(v.available/1024**3,3))"`
   PASS if the printed value is ≥ 4.0 GiB with the intended workload already
   open. Snapshot: 5.494 GiB → PASS.
2. **Free VRAM (only if a GPU path is being used)**
   `nvidia-smi --query-gpu=memory.total,memory.free --format=csv,noheader`
   PASS if free VRAM stays ≥ 1.0 GiB after the full session (model + workspace)
   is allocated. Snapshot: 3962 MiB free, no GPU consumer → not applicable.
3. **GPU visibility (only if a GPU path is being used)**
   `python -c "import torch;print(torch.cuda.is_available(), torch.version.cuda)"`
   PASS requires `True` and a CUDA runtime. Snapshot: `False`/`None` → **FAIL
   for GPU execution, PASS for the CPU-only declared pipeline**.
4. **ONNX providers (only if the detector is being run)**
   `python -c "import onnxruntime as o;print(o.get_available_providers())"`
   PASS requires the provider the config requests. Snapshot: CPU/Azure only.
5. **Artifact digests**
   Re-hash the frozen inputs listed in `configs/phase_8/campaign.yaml` and the
   detector files against `SHA256SUMS.json`; any mismatch is a stop.
6. **Authorization gates**
   `approval_status()` must report D1 approved against the on-disk REV4 hash,
   and `assert_campaign_authorized()` must return cleanly. Snapshot: D1 approved,
   **B7 still refuses**, so step 6 **FAILS by design** (§9).
7. **Record the preflight JSON in the run manifest** (`memory_preflight` block);
   a refused run writes a manifest saying so, never a "complete" one.

## 9. What this checklist does not change

- **B7 / G3 remains open.** `randomization_deviation().status` is still
  `deviation_recorded` (gate_weakened False, min observed free 1.628 GiB,
  16 certified seeds). No graph was regenerated and no deviation was accepted.
  `assert_campaign_authorized()` still refuses real execution.
- **D2 is still the owner's.** D1 approved REV4 §12 and U1–U18 as written; it
  did not resolve G3 applicability or authorise any deviation.
- **Other blockers are untouched:** B2 (design/U7 `n_seeds_selected` null),
  B3–B6 (training-operation inputs), B8 (run-time memory gate).
- **No execution occurred while preparing this checklist**: no Pilot 1 episode,
  no training, no campaign, no detector inference, no protected-artifact write.
- **No environment change was made:** nothing was installed, upgraded or
  removed; the GPU stack is exactly as measured in §6.

## 10. Decision needed before GPU-dependent work (not before Pilot 1)

If GPU-accelerated detector inference or training is ever wanted on this
machine, the owner must first decide whether to replace the installed CPU builds
(`torch 2.10.0+cpu` → CUDA build; `onnxruntime` → `onnxruntime-gpu`). That is an
environment change with reproducibility consequences: it alters `torch` and
`onnxruntime` versions recorded in manifests, and it would need its own measured
compatibility pilot. It is **not** a prerequisite for Pilot 1, which needs none
of it.
