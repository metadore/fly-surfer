"""Generate Figures 9-14 (Y1-Y6): real YOLO11n dataset and prediction visuals.

Every pixel shown comes from the project's own artifacts:

* image panels are the original Roboflow v15 files (byte-identical copies in the
  curated export), selected from the curated group-held-out split;
* ground-truth boxes are read from the original YOLO label files;
* prediction panels are produced by the deployed, SHA-pinned ONNX model through
  the repository's own ``OnnxRuntimeDetector`` at the deployment thresholds.

Nothing is retrained, fine-tuned, calibrated or synthesised. No aggregate
performance metric is computed: the inference pool exists only to choose
illustrative examples, and every statement in a figure footer is a statement
about the selected sample.

Outputs (all inside ``research_paper/``):

    figures/yolo11_visuals/Y01_training_samples.png        -> Figure 9
    figures/yolo11_visuals/Y02_ground_truth.png            -> Figure 10
    figures/yolo11_visuals/Y03_class_diversity.png         -> Figure 11
    figures/yolo11_visuals/Y04_predictions.png             -> Figure 12
    figures/yolo11_visuals/Y05_gt_vs_prediction.png        -> Figure 13
    figures/yolo11_visuals/Y06_detection_examples.png      -> Figure 14
    figures/yolo11_visuals/FIGURE_INDEX.md
    figures/yolo11_visuals/FIGURE_INDEX.csv
    figures/yolo11_visuals/PROVENANCE.json
    figures/FIGURE_INDEX.csv  (Y rows merged into the existing index)

Run after ``make_figures.py`` so the merged index keeps its rows.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
import textwrap
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.lines import Line2D
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from perception.config import load_perception_config  # noqa: E402
from perception.detector_config import load_detector_config  # noqa: E402
from perception.image import ImagePreprocessor  # noqa: E402
from perception.inference import OnnxRuntimeDetector  # noqa: E402

PAPER = ROOT / "research_paper"
OUTDIR = PAPER / "figures" / "yolo11_visuals"
EXPORT = ROOT / "datasets" / "exports" / "phase_3b2b1_yolo11n"
ORIG = (
    ROOT
    / "datasets"
    / "external"
    / "subway surfers"
    / "roboflow_v15_yolov8"
    / "subway surfers object dataset.v15-added.yolov8"
)
MANIFEST = ROOT / "reports" / "PHASE_3B1_SPLIT_MANIFEST.json"
DETECTOR_CFG = ROOT / "configs" / "detector_config.yaml"
PERCEPTION_CFG = ROOT / "configs" / "perception_config.yaml"

GT_COLOR = "#1b7f3b"
PRED_COLOR = "#c0392b"
MISS_COLOR = "#d68910"
FOCUS_COLOR = "#1565c0"
MUTED = "#8a8a8a"
INK = "#1a1a1a"
LOW_CONF = 0.526

# Distinct, print-safe colours; index = class id (0-13).
PALETTE = [
    "#1f77b4", "#e07000", "#2ca02c", "#c62828", "#7b4fa0", "#8c564b",
    "#d94f9a", "#5f5f5f", "#9aa800", "#0d8fa8", "#393b79", "#637939",
    "#8c6d31", "#843c39",
]

plt.rcParams.update(
    {
        "font.size": 7.6,
        "axes.titlesize": 7.8,
        "savefig.dpi": 200,
        "figure.dpi": 200,
        "axes.unicode_minus": False,
    }
)

NAME_RE = re.compile(r"^(?P<rec>.+?)-(?P<frame>\d+)_jpg\.rf\.[0-9a-f]+\.jpg$")

INDEX: list[dict] = []
PROVENANCE: dict = {
    "task": "YOLO11n visual documentation figures (Figures 9-14)",
    "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "figures": {},
    "datasets": {},
    "model": {},
    "matching_rule": (
        "greedy one-to-one matching by descending IoU among same-class pairs, "
        "IoU >= 0.5; unmatched ground-truth boxes are counted as misses, "
        "unmatched predictions as extra detections"
    ),
}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def wrap(text: str, width: int) -> str:
    return "\n".join(textwrap.wrap(" ".join(text.split()), width))


def short_name(name: str) -> str:
    match = NAME_RE.match(name)
    if not match:
        return name
    return f"{match.group('rec').replace('_mp4', '')} f{int(match.group('frame'))}"


@dataclass(frozen=True)
class Box:
    cls: int
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def w(self) -> float:
        return self.x2 - self.x1

    @property
    def h(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.w * self.h

    def as_list(self) -> list[float]:
        return [round(v, 3) for v in (self.x1, self.y1, self.x2, self.y2)]


@dataclass(frozen=True)
class Detection:
    cls: int
    conf: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def box(self) -> Box:
        return Box(self.cls, self.x1, self.y1, self.x2, self.y2)

    def as_dict(self) -> dict:
        return {
            "class_id": self.cls,
            "confidence": round(self.conf, 6),
            "box": self.box.as_list(),
        }


@dataclass
class Record:
    split: str
    name: str
    image_path: Path
    label_path: Path
    orig_rel: str
    width: int
    height: int
    boxes: tuple[Box, ...]
    dhash: int = 0

    @property
    def label(self) -> str:
        return short_name(self.name)

    @property
    def recording(self) -> str:
        match = NAME_RE.match(self.name)
        return match.group("rec").replace("_mp4", "") if match else self.name

    @property
    def frame(self) -> int:
        match = NAME_RE.match(self.name)
        return int(match.group("frame")) if match else -1

    def boxes_of(self, cls: int) -> tuple[Box, ...]:
        return tuple(box for box in self.boxes if box.cls == cls)


def dhash(path: Path) -> int:
    with Image.open(path) as opened:
        grey = opened.convert("L").resize((9, 8), Image.LANCZOS)
        values = np.asarray(grey, dtype=np.int16)
    bits = (values[:, 1:] > values[:, :-1]).ravel()
    value = 0
    for bit in bits:
        value = (value << 1) | int(bit)
    return value


def hamming(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def load_split(split: str, class_names: list[str], assignments: dict) -> list[Record]:
    records = []
    for image_path in sorted((EXPORT / split / "images").glob("*.jpg")):
        label_path = EXPORT / split / "labels" / (image_path.stem + ".txt")
        if not label_path.is_file():
            raise SystemExit(f"missing label file for {image_path.name}")
        orig_rel = assignments.get(image_path.name)
        if orig_rel is None:
            hits = list(ORIG.glob(f"*/images/{image_path.name}"))
            if not hits:
                raise SystemExit(f"image not in the source release: {image_path}")
            orig_rel = hits[0].relative_to(ORIG).as_posix()
        with Image.open(image_path) as opened:
            width, height = opened.size
        boxes = []
        for line in label_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            fields = line.split()
            if len(fields) != 5:
                raise SystemExit(f"bad label row in {label_path.name}: {line!r}")
            cls = int(fields[0])
            cx, cy, bw, bh = (float(v) for v in fields[1:])
            if not 0 <= cls < len(class_names):
                raise SystemExit(f"class id {cls} outside the 14-class map")
            boxes.append(
                Box(
                    cls,
                    (cx - bw / 2) * width,
                    (cy - bh / 2) * height,
                    (cx + bw / 2) * width,
                    (cy + bh / 2) * height,
                )
            )
        records.append(
            Record(
                split=split,
                name=image_path.name,
                image_path=image_path,
                label_path=label_path,
                orig_rel=orig_rel,
                width=width,
                height=height,
                boxes=tuple(boxes),
                dhash=dhash(image_path),
            )
        )
    return records


def draw_class_boxes(
    ax,
    boxes,
    class_names: list[str],
    *,
    confs: list[float] | None = None,
    linewidth: float = 1.0,
    legend: bool = True,
    fontsize: float = 4.7,
    ncol: int = 2,
    bbox_y: float = -0.012,
) -> None:
    """Outline boxes in the class colour and list classes (and confidences) in a legend.

    A per-class legend replaces per-box text tags: clustered boxes from distant
    frames would otherwise stack unreadable tags on top of each other.
    """
    for box in boxes:
        for edge, width, alpha in (("#ffffff", linewidth + 1.9, 0.65), (PALETTE[box.cls], linewidth, 1.0)):
            ax.add_patch(
                mpatches.Rectangle(
                    (box.x1, box.y1),
                    box.w,
                    box.h,
                    fill=False,
                    edgecolor=edge,
                    linewidth=width,
                    alpha=alpha,
                    joinstyle="miter",
                )
            )
    if not legend or not boxes:
        return
    grouped: dict[int, list[float | None]] = {}
    for index, box in enumerate(boxes):
        grouped.setdefault(box.cls, []).append(None if confs is None else confs[index])
    handles, labels = [], []
    for cls, values in grouped.items():
        if confs is None:
            labels.append(f"{class_names[cls]} ({len(values)})")
        else:
            scores = ", ".join(f"{value:.2f}" for value in sorted(values, reverse=True))
            labels.append(f"{class_names[cls]} {scores}")
        handles.append(Line2D([0], [0], color=PALETTE[cls], linewidth=1.6))
    ax.legend(
        handles,
        labels,
        loc="upper left",
        bbox_to_anchor=(0.0, bbox_y),
        ncol=ncol,
        fontsize=fontsize,
        frameon=False,
        handlelength=1.0,
        handletextpad=0.35,
        columnspacing=0.7,
        labelspacing=0.12,
        borderaxespad=0.0,
    )


def draw_boxes(
    ax,
    boxes,
    *,
    color: str,
    numbered: bool = True,
    offset: tuple[float, float] = (0.0, 0.0),
    linewidth: float = 1.0,
    linestyle="solid",
    alpha: float = 1.0,
    confs: list[float] | None = None,
    halo: bool = False,
) -> None:
    dx, dy = offset
    for index, box in enumerate(boxes, 1):
        x1, y1 = box.x1 - dx, box.y1 - dy
        if halo:
            ax.add_patch(
                mpatches.Rectangle(
                    (x1, y1), box.w, box.h, fill=False, edgecolor="#ffffff",
                    linewidth=linewidth + 1.9, linestyle=linestyle, alpha=0.65,
                )
            )
        ax.add_patch(
            mpatches.Rectangle(
                (x1, y1),
                box.w,
                box.h,
                fill=False,
                edgecolor=color,
                linewidth=linewidth,
                linestyle=linestyle,
                alpha=alpha,
                joinstyle="miter",
            )
        )
        if numbered:
            tag = f"{index}" if confs is None else f"{index} {confs[index - 1]:.2f}"
            ax.annotate(
                tag,
                xy=(x1, y1),
                xytext=(0, 2),
                textcoords="offset points",
                fontsize=5.4,
                color="white",
                ha="left",
                va="bottom",
                annotation_clip=False,
                bbox=dict(boxstyle="round,pad=0.12", facecolor=color, edgecolor="none", alpha=0.92),
            )


def footer(fig, lines: list[str], *, y: float = 0.002, fontsize: float = 5.4) -> None:
    fig.text(
        0.004,
        y,
        "\n".join(lines),
        ha="left",
        va="bottom",
        fontsize=fontsize,
        color="#333333",
        linespacing=1.28,
    )


def title(fig, text: str, y: float = 0.988) -> None:
    fig.text(0.004, y, text, ha="left", va="top", fontsize=9.2, weight="bold", color=INK)


def save(fig, fid: str, number: int, name: str, fig_title: str, sources: str, note: str, caption: str) -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)
    path = OUTDIR / f"{fid}_{name}.png"
    fig.savefig(path, bbox_inches="tight", pad_inches=0.04, facecolor="white")
    plt.close(fig)
    with Image.open(path) as opened:
        width, height = opened.size
    padding = f"W={width}px H={height}px ratio={height / width:.3f}"
    print(f"wrote {path.name} ({padding})")
    if height / width > 1.31:
        print(f"  WARNING: {path.name} is taller than the 1.31 page-fit guideline")
    INDEX.append(
        {
            "figure_id": fid,
            "number": number,
            "title": fig_title,
            "file": path.relative_to(PAPER).as_posix(),
            "sources": sources,
            "note": note,
        }
    )
    PROVENANCE["figures"][str(number)] = {
        "file": path.relative_to(PAPER).as_posix(),
        "pixel_size": [width, height],
        "caption": caption,
        "data_source": sources,
        "note": note,
    }


def crop_square(record: Record, box: Box, factor: float = 2.2, minimum: int = 250):
    side = int(max(box.w, box.h) * factor)
    side = min(max(side, minimum), record.width, record.height)
    cx, cy = (box.x1 + box.x2) / 2, (box.y1 + box.y2) / 2
    x0 = max(0, min(int(round(cx - side / 2)), record.width - side))
    y0 = max(0, min(int(round(cy - side / 2)), record.height - side))
    return x0, y0, x0 + side, y0 + side


def load_rgb(record: Record) -> np.ndarray:
    with Image.open(record.image_path) as opened:
        return np.asarray(opened.convert("RGB"))


def iou(a: Box, b: Box) -> float:
    x1, y1 = max(a.x1, b.x1), max(a.y1, b.y1)
    x2, y2 = min(a.x2, b.x2), min(a.y2, b.y2)
    inter = max(0.0, x2 - x1) * max(0.0, y2 - y1)
    return 0.0 if inter <= 0 else inter / (a.area + b.area - inter)


def match(gt: list[Box], preds: list[Detection], threshold: float = 0.5):
    pairs = []
    for gi, gbox in enumerate(gt):
        for pi, pred in enumerate(preds):
            if pred.cls != gbox.cls:
                continue
            value = iou(gbox, pred.box)
            if value >= threshold:
                pairs.append((value, gi, pi))
    pairs.sort(key=lambda row: (-row[0], row[1], row[2]))
    used_gt, used_pred, matched = set(), set(), []
    for value, gi, pi in pairs:
        if gi in used_gt or pi in used_pred:
            continue
        used_gt.add(gi)
        used_pred.add(pi)
        matched.append((gi, pi, value))
    missed = [i for i in range(len(gt)) if i not in used_gt]
    extra = [i for i in range(len(preds)) if i not in used_pred]
    return matched, missed, extra


def distinct(candidate: Record, chosen: list[Record], min_hash: int, min_gap: int) -> bool:
    for other in chosen:
        if other is None:
            continue
        if hamming(candidate.dhash, other.dhash) < min_hash:
            return False
        if candidate.recording == other.recording and abs(candidate.frame - other.frame) < min_gap:
            return False
    return True


# ---------------------------------------------------------------------------
# selection
# ---------------------------------------------------------------------------
TRAIN_CLASSES = ["train", "boxtrain", "ramp", "wall", "jump-roll-barrier", "jump-barrier"]


def select_training_examples(train: list[Record], class_names: list[str]) -> list[Record]:
    chosen: list[Record] = []
    relaxations = []
    rules = [(0, 12, 40), (1, 8, 20), (2, 4, 6), (3, 0, 0)]
    for class_name in TRAIN_CLASSES:
        cls = class_names.index(class_name)
        candidates = sorted(
            (rec for rec in train if rec.boxes_of(cls)),
            key=lambda rec: (-max(box.area for box in rec.boxes_of(cls)), rec.name),
        )
        picked = None
        for relax, min_hash, min_gap in rules:
            for candidate in candidates:
                if any(candidate is other for other in chosen):
                    continue
                if distinct(candidate, chosen, min_hash, min_gap):
                    picked = candidate
                    relaxations.append([class_name, relax, min_hash, min_gap])
                    break
            if picked is not None:
                break
        if picked is None:
            raise SystemExit(f"no training example available for {class_name}")
        chosen.append(picked)
    PROVENANCE["selection_relaxations"] = relaxations
    return chosen


def select_class_panels(train: list[Record], class_names: list[str]):
    panels = []
    for cls, class_name in enumerate(class_names):
        candidates = [rec for rec in train if rec.boxes_of(cls)]
        support_images = len(candidates)
        support_boxes = sum(len(rec.boxes_of(cls)) for rec in candidates)
        if not candidates:
            panels.append((class_name, None, None, 0, 0))
            continue
        ordered = sorted(
            candidates, key=lambda rec: (-max(box.area for box in rec.boxes_of(cls)), rec.name)
        )
        already = [panel[1] for panel in panels if panel[1] is not None]
        picked = None
        for min_hash in (8, 4, 0):
            for candidate in ordered:
                if distinct(candidate, already, min_hash, 4):
                    picked = candidate
                    break
            if picked is not None:
                break
        target = max(picked.boxes_of(cls), key=lambda box: box.area)
        panels.append((class_name, picked, target, support_images, support_boxes))
    return panels


# ---------------------------------------------------------------------------
# figures
# ---------------------------------------------------------------------------
def figure_samples(records: list[Record], selected: list[str], class_names: list[str], number: int) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(10.2, 12.2))
    fig.subplots_adjust(left=0.012, right=0.988, top=0.932, bottom=0.075, wspace=0.05, hspace=0.10)
    title(fig, f"Figure {number}. Curated training images: unmodified dataset samples")
    for ax, record, chosen_class in zip(axes.ravel(), records, selected):
        ax.imshow(load_rgb(record))
        ax.set_axis_off()
        counts: dict[str, int] = {}
        for box in record.boxes:
            counts[class_names[box.cls]] = counts.get(class_names[box.cls], 0) + 1
        others = len(counts) - 1
        suffix = f" + {others} other class" + ("es" if others != 1 else "") if others else ""
        ax.set_title(
            f"{record.label} - {chosen_class} x{counts[chosen_class]}{suffix}", fontsize=6.4, pad=2.5
        )
    footer(
        fig,
        [
            wrap(
                "Data source: Roboflow 'subway surfers object dataset' v15, curated training split "
                "(1,188 images, 4,704 boxes; groups subwayavitomp4, subwayedited2, subwayedtied). "
                "Images are the original files displayed unmodified and unstretched, with no "
                "annotation overlay. One image is shown for each of six high-frequency classes ("
                + ", ".join(selected)
                + "), choosing the largest labelled instance of that class, with 64-bit dHash distance "
                ">= 12 and >= 40 frames within a recording. This is group-held-out development data, "
                "not an independent test set.",
                178,
            ),
            "Files: " + "; ".join(record.name for record in records),
        ],
    )
    save(
        fig,
        "Y01",
        number,
        "training_samples",
        f"Figure {number}. Curated training images: unmodified dataset samples",
        "datasets/exports/phase_3b2b1_yolo11n/train/images (originals under datasets/external/.../v15)",
        "Six unmodified curated training images, one per high-frequency class.",
        caption=(
            "Six unmodified curated training images, one for each of six high-frequency classes, "
            f"shown without annotation. Their ground truth is drawn in Figure {number + 1}."
        ),
    )
    PROVENANCE["figures"][str(number)]["images"] = [
        {
            "name": record.name,
            "export_path": record.image_path.relative_to(ROOT).as_posix(),
            "original_path": (ORIG / record.orig_rel).relative_to(ROOT).as_posix(),
            "sha256": sha256(record.image_path),
            "label_sha256": sha256(record.label_path),
            "boxes": len(record.boxes),
        }
        for record in records
    ]


def figure_ground_truth(records: list[Record], class_names: list[str], number: int) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(10.2, 13.0))
    fig.subplots_adjust(left=0.012, right=0.988, top=0.935, bottom=0.115, wspace=0.05, hspace=0.30)
    title(fig, f"Figure {number}. Ground-truth annotations from the original YOLO label files")
    for ax, record in zip(axes.ravel(), records):
        ax.imshow(load_rgb(record))
        ax.set_axis_off()
        ax.set_title(f"{record.label} - {len(record.boxes)} ground-truth boxes", fontsize=6.4, pad=2.5)
        draw_class_boxes(ax, list(record.boxes), class_names, linewidth=1.4, ncol=2, fontsize=4.8)
    footer(
        fig,
        [
            wrap(
                "Data source: the six curated training images of the preceding figure and their "
                "original YOLO label files. Each row of the normalized label file (class cx cy w h) "
                "is converted to pixels with the 606 x 1050 image size; every colour-coded box is one "
                "label row and no box is inferred or added. Colours identify classes, as listed in "
                "the legend beneath each image. There is no player class and no coin class in "
                "this schema.",
                178,
            ),
            "Files: " + "; ".join(record.name for record in records),
        ],
    )
    save(
        fig,
        "Y02",
        number,
        "ground_truth",
        f"Figure {number}. Ground-truth annotations from the original YOLO label files",
        "the six Figure 9 images; labels in datasets/exports/phase_3b2b1_yolo11n/train/labels",
        "Ground-truth boxes for the six Figure 9 images.",
        caption=(
            "Ground-truth annotations for the six curated training images of Figure 9, drawn from "
            "the original label files at the original image scale."
        ),
    )


def figure_class_diversity(panels, number: int) -> None:
    fig, axes = plt.subplots(4, 4, figsize=(10.2, 11.8))
    fig.subplots_adjust(left=0.012, right=0.988, top=0.937, bottom=0.10, wspace=0.04, hspace=0.30)
    title(fig, f"Figure {number}. Class diversity in the curated training split: one instance per class")
    for ax in axes.ravel():
        ax.set_axis_off()
    low_support = []
    for ax, (class_name, record, target, support_images, support_boxes) in zip(axes.ravel(), panels):
        if record is None:
            ax.text(0.5, 0.5, f"{class_name}\nno labelled example", ha="center", va="center", fontsize=7)
            low_support.append(class_name)
            continue
        x0, y0, x1, y1 = crop_square(record, target)
        ax.imshow(load_rgb(record)[y0:y1, x0:x1])
        draw_boxes(ax, [b for b in record.boxes if b is not target], color=MUTED, numbered=False,
                   offset=(x0, y0), linewidth=0.5, alpha=0.75)
        draw_boxes(ax, [target], color=FOCUS_COLOR, numbered=False, offset=(x0, y0), linewidth=1.8,
                   halo=True)
        ax.set_axis_off()
        ax.set_title(class_name, fontsize=7.0, pad=2.0)
        marker = " *" if support_images < 40 else ""
        ax.text(0.5, -0.03, f"{short_name(record.name)} - {support_images} images / {support_boxes} boxes{marker}",
                transform=ax.transAxes, ha="center", va="top", fontsize=5.0, color=INK)
        if support_images < 40:
            low_support.append(class_name)
    footer(
        fig,
        [
            wrap(
                "Data source: curated training split (1,188 images, 4,704 boxes). Each panel is a "
                "square crop centred on the largest labelled instance of that class; the blue box is "
                "that instance and thin grey boxes are other annotations in the same frame. Beneath "
                "each panel: source image and class support in the split (images containing the "
                "class / boxes). * low support (fewer than 40 images) - shown, but not well sampled. "
                "The curated validation split has no boots-powerup and no jump-electric annotations, "
                "so those classes cannot be evaluated there.",
                178,
            ),
        ],
    )
    save(
        fig,
        "Y03",
        number,
        "class_diversity",
        f"Figure {number}. Class diversity in the curated training split",
        "datasets/exports/phase_3b2b1_yolo11n/train (images and labels)",
        "One labelled instance for each of the 14 classes; low-support classes marked.",
        caption=(
            "One labelled instance for each of the 14 classes from the curated training split, with "
            "the per-class support in that split. Classes with fewer than 40 images are marked, and "
            "the two classes absent from the validation split are named."
        ),
    )
    PROVENANCE["figures"][str(number)]["images"] = [
        {
            "class": class_name,
            "name": record.name if record else None,
            "export_path": record.image_path.relative_to(ROOT).as_posix() if record else None,
            "sha256": sha256(record.image_path) if record else None,
            "label_sha256": sha256(record.label_path) if record else None,
            "target_box": target.as_list() if target else None,
            "support_images": support_images,
            "support_boxes": support_boxes,
        }
        for class_name, record, target, support_images, support_boxes in panels
    ]


def figure_predictions(rows, class_names: list[str], number: int) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(10.2, 13.2))
    fig.subplots_adjust(left=0.012, right=0.988, top=0.935, bottom=0.135, wspace=0.05, hspace=0.30)
    title(
        fig,
        f"Figure {number}. Deployed YOLO11n detections on curated validation images "
        "(confidence >= 0.426, NMS IoU 0.70)",
    )
    for ax, row in zip(axes.ravel(), rows):
        record, preds = row["record"], row["preds"]
        ax.imshow(load_rgb(record))
        ax.set_axis_off()
        ax.set_title(
            f"{record.label} - curated validation - {len(preds)} "
            f"{'detection' if len(preds) == 1 else 'detections'}",
            fontsize=6.4,
            pad=2.5,
        )
        draw_class_boxes(
            ax,
            [pred.box for pred in preds],
            class_names,
            confs=[pred.conf for pred in preds],
            linewidth=1.4,
            ncol=1,
            fontsize=4.6,
        )
    footer(
        fig,
        [
            wrap(
                "Model: YOLO11n ONNX deployment best.onnx, SHA-256 e6ad18f9...6aa77, 10,636,871 "
                "bytes, executed locally through the repository OnnxRuntimeDetector (CPU, one "
                "thread); letterbox 640 x 640, pad 114, RGB, output 1x18x8400, per-class confidence "
                "0.426, NMS IoU 0.70, identity 14-class map. The model was not retrained, "
                "fine-tuned or calibrated for this figure. Split: curated validation (1,128 images; "
                "groups datasetfootage, subwayy1_1), group-held-out development data and not an "
                "independent test set.",
                178,
            ),
            "Files: " + "; ".join(row["record"].name for row in rows),
            "The class and confidence of each detection are listed beneath its image; the values "
            "in this footer are deployment settings, not a re-estimate of accuracy.",
        ],
    )
    save(
        fig,
        "Y04",
        number,
        "predictions",
        f"Figure {number}. Deployed YOLO11n detections on curated validation images",
        "curated validation images + deployment best.onnx (SHA-256 e6ad18f9...6aa77)",
        "Six curated validation images with actual ONNX detections at the deployment thresholds.",
        caption=(
            "Actual predictions of the deployed YOLO11n ONNX model on curated validation images at "
            "the deployment confidence and NMS settings, with predicted class and confidence. No "
            "accuracy metric is re-estimated."
        ),
    )
    PROVENANCE["figures"][str(number)]["images"] = [
        {
            "name": row["record"].name,
            "export_path": row["record"].image_path.relative_to(ROOT).as_posix(),
            "sha256": sha256(row["record"].image_path),
            "label_sha256": sha256(row["record"].label_path),
            "gt_boxes": [box.as_list() for box in row["record"].boxes],
            "predictions": [pred.as_dict() for pred in row["preds"]],
        }
        for row in rows
    ]


def figure_comparison(rows, class_names: list[str], number: int) -> None:
    fig, axes = plt.subplots(2, 4, figsize=(10.2, 10.0))
    fig.subplots_adjust(left=0.008, right=0.992, top=0.918, bottom=0.155, wspace=0.04, hspace=0.34)
    title(
        fig,
        f"Figure {number}. Ground truth (left) versus deployed YOLO11n detection (right), "
        "same image and scale",
    )
    slots = [(0, 0), (0, 1), (1, 0), (1, 1)]
    for slot, row in enumerate(rows):
        row_index, pair_index = slots[slot]
        ax_gt = axes[row_index][pair_index * 2]
        ax_pred = axes[row_index][pair_index * 2 + 1]
        record, preds = row["record"], row["preds"]
        for ax in (ax_gt, ax_pred):
            ax.imshow(load_rgb(record))
            ax.set_axis_off()
        draw_class_boxes(ax_gt, list(record.boxes), class_names, linewidth=1.25, ncol=1, fontsize=4.1)
        draw_class_boxes(
            ax_pred,
            [pred.box for pred in preds],
            class_names,
            confs=[pred.conf for pred in preds],
            linewidth=1.25,
            ncol=1,
            fontsize=4.1,
        )
        ax_gt.set_title(
            f"E{slot + 1} {record.label} - ground truth ({len(record.boxes)}), "
            f"missed {len(row['missed'])}",
            fontsize=5.9,
            pad=2.0,
        )
        ax_pred.set_title(
            f"E{slot + 1} {record.label} - detection ({len(preds)}), extra {len(row['extra'])}",
            fontsize=5.9,
            pad=2.0,
        )
    footer(
        fig,
        [
            wrap(
                "Model and thresholds as in the preceding figure. Left panel of each pair: original "
                "label-file annotations. Right panel: deployed YOLO11n detections. Boxes are colour-"
                "coded by class and the class/confidence legend sits beneath each panel; the left "
                "panel has no confidence values because ground truth carries none. Both panels use "
                "the same source image and the same display scale. Matching: greedy one-to-one "
                "same-class matching at IoU >= 0.5; "
                "'missed' counts unmatched ground-truth boxes and 'extra' counts unmatched "
                "detections. Pairs were chosen to include exact and imperfect outcomes, not only "
                "successes.",
                178,
            ),
            "Files: " + "; ".join(f"E{i + 1} {row['record'].name}" for i, row in enumerate(rows)),
        ],
    )
    save(
        fig,
        "Y05",
        number,
        "gt_vs_prediction",
        f"Figure {number}. Ground truth versus deployed YOLO11n detection",
        "curated validation labels + deployment best.onnx",
        "Four paired ground-truth/detection comparisons on identical images and scale.",
        caption=(
            "Paired ground-truth and detection panels for four curated validation images at identical "
            "scale, with unmatched boxes counted under the stated matching rule."
        ),
    )
    PROVENANCE["figures"][str(number)]["images"] = [
        {
            "name": row["record"].name,
            "sha256": sha256(row["record"].image_path),
            "label_sha256": sha256(row["record"].label_path),
            "gt_boxes": [box.as_list() for box in row["record"].boxes],
            "predictions": [pred.as_dict() for pred in row["preds"]],
            "matched": [{"gt_index": gi, "pred_index": pi, "iou": round(value, 4)} for gi, pi, value in row["matched"]],
            "missed_gt": row["missed"],
            "extra_pred": row["extra"],
        }
        for row in rows
    ]


def figure_examples(rows, class_names: list[str], number: int, observed: dict) -> None:
    fig, axes = plt.subplots(2, 3, figsize=(10.2, 13.4))
    fig.subplots_adjust(left=0.012, right=0.988, top=0.935, bottom=0.155, wspace=0.05, hspace=0.30)
    title(fig, f"Figure {number}. Detection examples and limitations on curated validation images")
    for ax, row in zip(axes.ravel(), rows):
        record, preds = row["record"], row["preds"]
        ax.imshow(load_rgb(record))
        for box in record.boxes:
            ax.add_patch(
                mpatches.Rectangle((box.x1, box.y1), box.w, box.h, fill=False,
                                   edgecolor="#ffffff", linewidth=2.4, linestyle=(0, (2, 1.6)), alpha=0.65)
            )
            ax.add_patch(
                mpatches.Rectangle((box.x1, box.y1), box.w, box.h, fill=False,
                                   edgecolor="#2b2b2b", linewidth=0.8, linestyle=(0, (2, 1.6)))
            )
        for gi in row["missed"]:
            box = record.boxes[gi]
            ax.add_patch(
                mpatches.Rectangle((box.x1, box.y1), box.w, box.h, fill=False,
                                   edgecolor="#ffffff", linewidth=3.9, linestyle=(0, (3, 2)), alpha=0.7)
            )
            ax.add_patch(
                mpatches.Rectangle((box.x1, box.y1), box.w, box.h, fill=False,
                                   edgecolor=MISS_COLOR, linewidth=2.2, linestyle=(0, (3, 2)))
            )
        draw_class_boxes(
            ax,
            [pred.box for pred in preds],
            class_names,
            confs=[pred.conf for pred in preds],
            linewidth=1.4,
            legend=False,
        )
        ax.set_axis_off()
        ax.set_title(f"{record.label} - {row['badge']}", fontsize=6.4, pad=2.5,
                     color=PRED_COLOR if row["category"] != "clean" else INK)
        grouped: dict[int, list[float]] = {}
        for pred in preds:
            grouped.setdefault(pred.cls, []).append(pred.conf)
        handles, labels = [], []
        for cls, values in grouped.items():
            handles.append(Line2D([0], [0], color=PALETTE[cls], linewidth=1.6))
            labels.append(f"{class_names[cls]} {', '.join(f'{value:.2f}' for value in sorted(values, reverse=True))}")
        handles.append(Line2D([0], [0], color="#2b2b2b", linewidth=0.9, linestyle=(0, (2, 1.6))))
        labels.append(f"ground truth ({len(record.boxes)})")
        if row["missed"]:
            missed_classes: dict[str, int] = {}
            for gi in row["missed"]:
                name = class_names[record.boxes[gi].cls]
                missed_classes[name] = missed_classes.get(name, 0) + 1
            detail = ", ".join(f"{name} ({count})" for name, count in missed_classes.items())
            handles.append(Line2D([0], [0], color=MISS_COLOR, linewidth=2.0, linestyle=(0, (3, 2))))
            labels.append(f"missed: {detail}")
        ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(0.0, -0.012), ncol=1,
                  fontsize=4.6, frameon=False, handlelength=1.0, handletextpad=0.35,
                  columnspacing=0.7, labelspacing=0.12, borderaxespad=0.0)
    absent = [name for name, count in observed.items() if count == 0]
    present = ", ".join(f"{name} {count}" for name, count in observed.items() if count)
    footer(
        fig,
        [
            wrap(
                "Dashed dark grey with a white halo: ground truth from the label files. Solid "
                "class-coloured: deployed YOLO11n detection, with confidence listed in the per-panel "
                "legend. Dashed amber: ground-truth box with no matching detection (missed, IoU < "
                "0.5 with every same-class prediction); its true class is named in the legend. "
                "Matching rule as in the preceding figure. Category counts over the six selected "
                "panels (a panel can count in more than one category): " + present + "."
                + (" Categories not observed in this selection: " + ", ".join(absent) + "." if absent else "")
                + " Absence in this sample is not evidence that the model never makes that error.",
                178,
            ),
            "Files: " + "; ".join(row["record"].name for row in rows),
        ],
    )
    save(
        fig,
        "Y06",
        number,
        "detection_examples",
        f"Figure {number}. Detection examples and limitations",
        "curated validation labels + deployment best.onnx",
        "Correct, missed, extra and low-confidence cases, with observed-category disclosure.",
        caption=(
            "Detection examples and limitations: correct detections, missed ground-truth objects, "
            "extra detections and low-confidence matches, with explicit disclosure of which error "
            "categories were observed in the selected panels."
        ),
    )
    PROVENANCE["figures"][str(number)]["images"] = [
        {
            "name": row["record"].name,
            "sha256": sha256(row["record"].image_path),
            "label_sha256": sha256(row["record"].label_path),
            "gt_boxes": [box.as_list() for box in row["record"].boxes],
            "predictions": [pred.as_dict() for pred in row["preds"]],
            "matched": [{"gt_index": gi, "pred_index": pi, "iou": round(value, 4)} for gi, pi, value in row["matched"]],
            "missed_gt": row["missed"],
            "extra_pred": row["extra"],
            "low_conf_matched": row["low_conf"],
            "badge": row["badge"],
        }
        for row in rows
    ]
    PROVENANCE["observed_categories"] = observed


# ---------------------------------------------------------------------------
# index files
# ---------------------------------------------------------------------------
def write_indexes() -> None:
    rows = sorted(INDEX, key=lambda row: row["number"])
    header = "figure_id,title,file,sources,note"
    lines = [
        header,
        *[
            ",".join('"' + str(row[key]).replace('"', '""') + '"'
                     for key in ("figure_id", "title", "file", "sources", "note"))
            for row in rows
        ],
    ]
    (OUTDIR / "FIGURE_INDEX.csv").write_text("\n".join(lines) + "\n", encoding="utf-8")

    merged_path = PAPER / "figures" / "FIGURE_INDEX.csv"
    existing = []
    if merged_path.is_file():
        existing = [line for line in merged_path.read_text(encoding="utf-8").splitlines()[1:] if line.strip()]
    new_ids = {row["figure_id"] for row in rows}
    kept = [line for line in existing if line.split(",", 1)[0].strip('"') not in new_ids]
    merged_path.write_text("\n".join([header] + kept + lines[1:]) + "\n", encoding="utf-8")

    detail = []
    for row in rows:
        number = str(row["number"])
        spec = PROVENANCE["figures"][number]
        detail.append(f"### Figure {number} - {spec['caption'].split('.')[0]}\n")
        detail.append(f"- File: `{row['file']}` ({spec['pixel_size'][0]} x {spec['pixel_size'][1]} px)")
        detail.append(f"- Caption: {spec['caption']}")
        detail.append(f"- Data source: {row['sources']}")
        detail.append(f"- Note: {row['note']}")
        if "images" in spec:
            detail.append("- Images shown:")
            for item in spec["images"]:
                if item.get("class"):
                    detail.append(
                        f"  - `{item['class']}`: `{item['name']}`"
                        f" (support {item['support_images']} images / {item['support_boxes']} boxes)"
                    )
                else:
                    detail.append(f"  - `{item['name']}` (SHA-256 `{item['sha256'][:16]}...`)")
        detail.append("")

    doc = [
        "# YOLO11n visual documentation figures (Figures 9-14)",
        "",
        "Generated by `research_paper/scripts/make_yolo_figures.py`. Every image is a project",
        "artifact; predictions come from the deployment ONNX model at the deployment thresholds.",
        "See `PROVENANCE.json` for per-image hashes, ground-truth boxes, predictions and matches.",
        "",
        "Dataset: Roboflow 'subway surfers object dataset' v15, curated group-held-out split",
        "(train 1,188 images / 4,704 boxes; validation 1,128 images / 3,962 boxes; no test split).",
        "",
        "Model: `models/YOLO11/deployment/yolo11n_v1_deployment/best.onnx`",
        "(SHA-256 `e6ad18f90cd0be8c71237556f0922d83a6dca4ac54184ddde6536896b6b6aa77`),",
        "confidence 0.426, NMS IoU 0.70, input 640x640 letterbox, identity 14-class map.",
        "The model was not retrained, fine-tuned or calibrated during this task.",
        "",
        "| Figure | File | Content |",
        "|---|---|---|",
        *[f"| {row['number']} | `{row['file']}` | {row['note']} |" for row in rows],
        "",
        "## Figure details",
        "",
        *detail,
    ]
    (OUTDIR / "FIGURE_INDEX.md").write_text("\n".join(doc) + "\n", encoding="utf-8")
    (OUTDIR / "PROVENANCE.json").write_text(
        json.dumps(PROVENANCE, indent=2) + "\n", encoding="utf-8"
    )
    print("wrote FIGURE_INDEX.md, FIGURE_INDEX.csv, PROVENANCE.json")


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------
def main() -> None:
    OUTDIR.mkdir(parents=True, exist_ok=True)

    perception = load_perception_config(PERCEPTION_CFG)
    detector_cfg = load_detector_config(DETECTOR_CFG)
    class_names = [definition.name for definition in perception.schema.classes]
    if len(class_names) != 14:
        raise SystemExit("expected 14 classes")
    detector = OnnxRuntimeDetector(detector_cfg, perception.schema)
    preprocessor = ImagePreprocessor(perception.preprocess)

    assignments = json.loads(MANIFEST.read_text(encoding="utf-8"))["fixed_split"]["assignments"]
    by_basename = {Path(key).name: key for key in assignments}

    PROVENANCE["model"] = {
        "path": detector.model_path.relative_to(ROOT).as_posix(),
        "sha256": detector.model_sha256,
        "input_size": list(detector_cfg.input_size),
        "output_layout": detector_cfg.output_layout,
        "has_objectness": detector_cfg.has_objectness,
        "class_activation": detector_cfg.class_activation,
        "confidence_threshold": detector_cfg.confidence_threshold,
        "nms_iou_threshold": detector_cfg.nms_iou_threshold,
        "max_detections": detector_cfg.max_detections,
        "class_id_map": list(detector_cfg.class_id_map),
        "providers": list(detector_cfg.providers),
        "detector_config": DETECTOR_CFG.relative_to(ROOT).as_posix(),
        "detector_config_sha256": sha256(DETECTOR_CFG),
        "perception_config": PERCEPTION_CFG.relative_to(ROOT).as_posix(),
        "perception_config_sha256": sha256(PERCEPTION_CFG),
        "weights_trained_in_this_task": False,
    }

    train = load_split("train", class_names, by_basename)
    valid = load_split("valid", class_names, by_basename)
    PROVENANCE["datasets"] = {
        "export_root": EXPORT.relative_to(ROOT).as_posix(),
        "original_root": ORIG.relative_to(ROOT).as_posix(),
        "split_manifest": MANIFEST.relative_to(ROOT).as_posix(),
        "split_manifest_sha256": sha256(MANIFEST),
        "class_names": class_names,
        "train_images": len(train),
        "valid_images": len(valid),
        "train_boxes": sum(len(rec.boxes) for rec in train),
        "valid_boxes": sum(len(rec.boxes) for rec in valid),
    }
    if (len(train), len(valid)) != (1188, 1128):
        raise SystemExit(f"unexpected curated split sizes: {len(train)}, {len(valid)}")

    # Y1 / Y2
    samples = select_training_examples(train, class_names)
    figure_samples(samples, TRAIN_CLASSES, class_names, 9)
    figure_ground_truth(samples, class_names, 10)

    # Y3
    figure_class_diversity(select_class_panels(train, class_names), 11)

    # inference pool (selection only)
    pool = []
    for index in range(len(valid)):
        if index % 9 != 4:
            continue
        record = valid[index]
        frame = preprocessor.load(record.image_path)
        detections = detector.detect(frame)
        preds = sorted(
            (
                Detection(
                    det.class_id,
                    float(det.confidence),
                    min(max(det.x1, 0.0), record.width),
                    min(max(det.y1, 0.0), record.height),
                    min(max(det.x2, 0.0), record.width),
                    min(max(det.y2, 0.0), record.height),
                )
                for det in detections
            ),
            key=lambda det: -det.conf,
        )
        matched, missed, extra = match(list(record.boxes), preds)
        low_conf = [pi for _, pi, _ in matched if preds[pi].conf < LOW_CONF]
        if missed and extra:
            category = "missed_extra"
        elif missed:
            category = "missed"
        elif extra:
            category = "extra"
        else:
            category = "clean"
        pool.append(
            {
                "record": record,
                "preds": preds,
                "matched": matched,
                "missed": missed,
                "extra": extra,
                "low_conf": low_conf,
                "category": category,
            }
        )
    PROVENANCE["inference_pool"] = {
        "selection": "every ninth curated-validation image in sorted filename order (index % 9 == 4)",
        "size": len(pool),
        "purpose": "example selection only; no aggregate metric is computed or reported",
        "category_counts": {key: sum(1 for row in pool if row["category"] == key)
                            for key in ("clean", "missed", "extra", "missed_extra")},
        "low_confidence_band": [0.426, LOW_CONF],
        "images": [
            {
                "name": row["record"].name,
                "predictions": len(row["preds"]),
                "matched": len(row["matched"]),
                "missed": len(row["missed"]),
                "extra": len(row["extra"]),
                "low_conf": len(row["low_conf"]),
                "category": row["category"],
            }
            for row in pool
        ],
    }
    print("pool categories:", PROVENANCE["inference_pool"]["category_counts"])

    # Y4
    chosen = []
    for row in pool:
        if row["category"] != "clean":
            continue
        if distinct(row["record"], [c["record"] for c in chosen], 12, 40):
            chosen.append(row)
        if len(chosen) == 6:
            break
    if len(chosen) < 6:
        raise SystemExit(f"only {len(chosen)} clean examples in the pool")
    figure_predictions(chosen, class_names, 12)

    # Y5
    def pick(category: str, avoid: list, min_hash: int, min_gap: int, limit: int = 1):
        found = []
        for row in pool:
            if row["category"] != category or any(row is other for other in avoid):
                continue
            if distinct(row["record"], [c["record"] for c in avoid + found], min_hash, min_gap):
                found.append(row)
            if len(found) == limit:
                break
        return found

    comparison = pick("clean", [], 12, 40, 2)
    comparison += pick("missed_extra", comparison, 8, 12, 1)
    comparison += pick("missed", comparison, 8, 12, 1)
    if len(comparison) < 4:
        comparison += pick("extra", comparison, 8, 12, 4 - len(comparison))
    if len(comparison) < 4:
        comparison += pick("clean", comparison, 4, 6, 4 - len(comparison))
    if len(comparison) != 4:
        raise SystemExit("could not build four comparison pairs")
    figure_comparison(comparison, class_names, 13)

    # Y6
    observed = {
        "correct (no miss, no extra)": 0,
        "missed ground truth": 0,
        "extra detection": 0,
        "low-confidence match": 0,
    }
    chosen6 = []
    used = list(comparison)
    for category, count in (("clean", 2), ("missed", 1), ("extra", 1), ("missed_extra", 1)):
        chosen6 += pick(category, used + chosen6, 10, 30, count)
    chosen6 += [
        row for row in pool
        if row["low_conf"] and row not in chosen6 and row not in used
        and distinct(row["record"], [c["record"] for c in used + chosen6], 10, 30)
    ][:1]
    for row in pool:
        if len(chosen6) >= 6:
            break
        if any(row is other for other in chosen6 + used):
            continue
        if distinct(row["record"], [c["record"] for c in used + chosen6], 6, 12):
            chosen6.append(row)
    chosen6 = chosen6[:6]
    if len(chosen6) < 6:
        raise SystemExit("could not build six example panels")
    for row in chosen6:
        if row["category"] == "clean":
            observed["correct (no miss, no extra)"] += 1
        if row["missed"]:
            observed["missed ground truth"] += 1
        if row["extra"]:
            observed["extra detection"] += 1
        if row["low_conf"]:
            observed["low-confidence match"] += 1
        row["badge"] = (
            f"correct {len(row['matched'])}/{len(row['record'].boxes)}"
            if row["category"] == "clean"
            else f"missed {len(row['missed'])}, extra {len(row['extra'])}"
            + (f", low-conf {len(row['low_conf'])}" if row["low_conf"] else "")
        )
    figure_examples(chosen6, class_names, 14, observed)

    write_indexes()
    print("done")


if __name__ == "__main__":
    main()
