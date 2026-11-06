"""Authoritative curation-manifest lookup for inference inputs.

The split of an image is taken from ``reports/PHASE_3B1_SPLIT_MANIFEST.json``
by filename group. It is never inferred from the Roboflow ``train``/``valid``
folder the image happens to sit in, and an unknown group is an error rather
than a fallback.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class ManifestError(ValueError):
    """Raised when the manifest is missing, invalid or cannot resolve a path."""


@dataclass(frozen=True)
class SplitAssignment:
    """Curation-derived identity of one dataset image."""

    path: str
    group: str
    split: str | None
    excluded: bool
    exclusion_reason: str | None
    split_source: str = "curation_manifest_fixed_split"

    def as_dict(self) -> dict:
        return {
            "path": self.path,
            "group": self.group,
            "split": self.split,
            "excluded": self.excluded,
            "exclusion_reason": self.exclusion_reason,
            "split_source": self.split_source,
        }


def _normalize(value: str) -> str:
    text = value.replace("\\", "/")
    while text.startswith("./"):
        text = text[2:]
    return text


class SplitManifest:
    """Loaded Phase 3B.1 manifest with exact filename-group lookup."""

    def __init__(self, payload: dict, *, repo_root: Path, source_path: Path) -> None:
        if not isinstance(payload, dict):
            raise ManifestError("split manifest must be a JSON object")
        for key in ("groups", "fixed_split", "exclusions", "dataset"):
            if key not in payload:
                raise ManifestError(f"split manifest is missing {key!r}")
        dataset = payload["dataset"]
        if not isinstance(dataset, dict) or not dataset.get("discovered_root"):
            raise ManifestError("split manifest has no dataset.discovered_root")
        groups = payload["groups"]
        fixed_split = payload["fixed_split"]
        if not isinstance(groups, dict) or not groups:
            raise ManifestError("split manifest groups must be a non-empty object")
        if not isinstance(fixed_split, dict):
            raise ManifestError("split manifest fixed_split must be an object")
        train_groups = fixed_split.get("train_groups", fixed_split.get("train"))
        valid_groups = fixed_split.get("valid_groups", fixed_split.get("valid"))
        if not isinstance(train_groups, list) or not isinstance(valid_groups, list):
            raise ManifestError("fixed_split must list train and valid groups")
        overlap = set(train_groups) & set(valid_groups)
        if overlap:
            raise ManifestError(
                f"groups appear in both splits: {sorted(overlap)}"
            )
        for group in list(train_groups) + list(valid_groups):
            if group not in groups:
                raise ManifestError(f"fixed_split references unknown group {group!r}")

        self.payload = payload
        self.repo_root = Path(repo_root)
        self.source_path = Path(source_path)
        self.dataset_root = _normalize(str(dataset["discovered_root"]))
        self.class_names = tuple(str(name) for name in dataset.get("class_names", ()))
        self.groups: dict[str, dict[str, Any]] = groups
        self._split_by_group = {
            **{group: "train" for group in train_groups},
            **{group: "valid" for group in valid_groups},
        }
        self._prefixes: list[tuple[str, str]] = sorted(
            (
                (str(prefix), group)
                for group, payload_group in groups.items()
                for prefix in payload_group.get("prefixes", (group,))
            ),
            key=lambda item: len(item[0]),
            reverse=True,
        )
        exclusions = payload["exclusions"]
        if not isinstance(exclusions, list):
            raise ManifestError("split manifest exclusions must be a list")
        self._exclusions_by_path: dict[str, str] = {}
        self._exclusions_by_name: dict[str, str] = {}
        for entry in exclusions:
            if not isinstance(entry, dict) or "path" not in entry:
                raise ManifestError("each exclusion must contain a path")
            path = _normalize(str(entry["path"]))
            reason = str(entry.get("reason", "excluded"))
            self._exclusions_by_path[path] = reason
            self._exclusions_by_name[Path(path).name] = reason

    @classmethod
    def load(
        cls,
        path: str | Path | None = None,
        *,
        repo_root: str | Path | None = None,
    ) -> "SplitManifest":
        root = (
            Path(repo_root)
            if repo_root is not None
            else Path(__file__).resolve().parents[1]
        )
        source = (
            Path(path)
            if path is not None
            else root / "reports" / "PHASE_3B1_SPLIT_MANIFEST.json"
        )
        if not source.is_file():
            raise ManifestError(f"split manifest not found: {source}")
        try:
            payload = json.loads(source.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ManifestError(f"cannot read split manifest {source}: {exc}") from exc
        return cls(payload, repo_root=root, source_path=source)

    @property
    def train_groups(self) -> tuple[str, ...]:
        fixed_split = self.payload["fixed_split"]
        return tuple(fixed_split.get("train_groups", fixed_split.get("train", ())))

    @property
    def valid_groups(self) -> tuple[str, ...]:
        fixed_split = self.payload["fixed_split"]
        return tuple(fixed_split.get("valid_groups", fixed_split.get("valid", ())))

    @property
    def dataset_root_path(self) -> Path:
        return (self.repo_root / self.dataset_root).resolve()

    def _relative_to_dataset(self, path: str | Path) -> tuple[str, str]:
        """Return (path relative to the dataset root, basename)."""
        candidate = Path(path)
        inside_dataset = False
        if candidate.is_absolute():
            try:
                relative = candidate.resolve().relative_to(
                    self.dataset_root_path
                )
                inside_dataset = True
            except ValueError:
                # Also allow a repo-relative absolute path under the repo.
                try:
                    relative = candidate.resolve().relative_to(
                        self.repo_root.resolve()
                    )
                except ValueError as exc:
                    raise ManifestError(
                        f"image is outside the curated dataset: {path}"
                    ) from exc
            normalized = _normalize(str(relative))
        else:
            normalized = _normalize(str(path))
        if not normalized:
            raise ManifestError("empty image path")
        if normalized.startswith(self.dataset_root + "/"):
            normalized = normalized[len(self.dataset_root) + 1 :]
        elif "/" in normalized and not inside_dataset:
            raise ManifestError(
                "image path is not inside the manifest dataset root: "
                f"{normalized!r}"
            )
        basename = Path(normalized).name
        if not basename:
            raise ManifestError(f"image path has no filename: {path!r}")
        return normalized, basename

    def group_for(self, basename: str) -> str:
        for prefix, group in self._prefixes:
            if basename == prefix or basename.startswith(prefix + "_"):
                return group
            if basename.startswith(prefix + "."):
                return group
        raise ManifestError(
            f"filename {basename!r} does not match any manifest group; "
            "refusing to guess a split"
        )

    def resolve(self, path: str | Path) -> SplitAssignment:
        """Resolve group and curated split for a dataset image.

        The ``split`` comes only from the manifest's filename groups. It does
        not depend on the image's current ``train``/``valid`` folder.
        """
        normalized, basename = self._relative_to_dataset(path)
        group = self.group_for(basename)
        reason = self._exclusions_by_path.get(normalized)
        if reason is None:
            reason = self._exclusions_by_name.get(basename)
        if reason is not None:
            return SplitAssignment(
                path=normalized,
                group=group,
                split=self._split_by_group.get(group),
                excluded=True,
                exclusion_reason=reason,
            )
        if group not in self._split_by_group:
            raise ManifestError(
                f"group {group!r} is not assigned to any split and is not excluded"
            )
        split = self._split_by_group[group]
        return SplitAssignment(
            path=normalized,
            group=group,
            split=split,
            excluded=False,
            exclusion_reason=None,
        )

    def describe(self) -> dict:
        return {
            "source": str(self.source_path),
            "dataset_root": self.dataset_root,
            "class_names": list(self.class_names),
            "train_groups": list(self.train_groups),
            "valid_groups": list(self.valid_groups),
            "n_exclusions": len(self._exclusions_by_path),
            "split_source": "curation_manifest_fixed_split",
        }
