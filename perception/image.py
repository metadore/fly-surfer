"""Image loading and preprocessing with explicit coordinate mapping.

The detector sees the processed image. Its boxes are converted back to screen
pixels and then to viewport fractions. That mapping is held by
``ImageFrame`` so resolution or crop changes cannot silently shift lanes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from PIL import Image, UnidentifiedImageError

from perception.config import PreprocessConfig
from perception.geometry import BoundingBox, NormalizedBox


class ImageLoadError(ValueError):
    """Raised when an input image cannot be opened or is unusable."""


def _positive_size(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


@dataclass(frozen=True)
class ImageFrame:
    """A loaded image plus the transform between detector and screen space."""

    pixels: Image.Image
    original_size: tuple[int, int]
    crop_box: tuple[int, int, int, int]
    processed_size: tuple[int, int]
    scale_x: float
    scale_y: float
    source_path: Path | None = None
    frame_id: str | None = None
    timestamp_ms: float | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.pixels, Image.Image):
            raise ValueError("pixels must be a PIL image")
        width, height = self.original_size
        _positive_size(width, "original width")
        _positive_size(height, "original height")
        left, top, right, bottom = self.crop_box
        if not (0 <= left < right <= width and 0 <= top < bottom <= height):
            raise ValueError("crop_box must lie inside the original image")
        processed_width, processed_height = self.processed_size
        _positive_size(processed_width, "processed width")
        _positive_size(processed_height, "processed height")
        if self.pixels.size != self.processed_size:
            raise ValueError("pixels size does not match processed_size")
        if not math.isfinite(self.scale_x) or self.scale_x <= 0:
            raise ValueError("scale_x must be finite and positive")
        if not math.isfinite(self.scale_y) or self.scale_y <= 0:
            raise ValueError("scale_y must be finite and positive")
        if self.timestamp_ms is not None:
            if isinstance(self.timestamp_ms, bool) or not isinstance(
                self.timestamp_ms, (int, float)
            ):
                raise ValueError("timestamp_ms must be a number or None")
            value = float(self.timestamp_ms)
            if not math.isfinite(value) or value < 0:
                raise ValueError("timestamp_ms must be finite and non-negative")
            object.__setattr__(self, "timestamp_ms", value)
        if self.frame_id is not None and not isinstance(self.frame_id, str):
            raise ValueError("frame_id must be a string or None")

    @property
    def viewport_size(self) -> tuple[int, int]:
        left, top, right, bottom = self.crop_box
        return (right - left, bottom - top)

    def processed_box_to_screen(self, x1: float, y1: float, x2: float, y2: float) -> BoundingBox:
        """Map a detector box (processed pixels) to original screen pixels."""
        left, top, _, _ = self.crop_box
        return BoundingBox(
            left + float(x1) / self.scale_x,
            top + float(y1) / self.scale_y,
            left + float(x2) / self.scale_x,
            top + float(y2) / self.scale_y,
        )

    def screen_box_to_normalized(self, box: BoundingBox) -> NormalizedBox:
        """Map a screen box to fractions of the processed viewport."""
        left, top, right, bottom = self.crop_box
        width = right - left
        height = bottom - top
        return NormalizedBox(
            (box.x1 - left) / width,
            (box.y1 - top) / height,
            (box.x2 - left) / width,
            (box.y2 - top) / height,
        )

    def as_array(self) -> np.ndarray:
        """Copy the processed pixels as an H x W x C uint8 array."""
        return np.array(self.pixels, dtype=np.uint8, copy=True)


class ImagePreprocessor:
    """Load, validate, optionally crop/resize, and retain the transform."""

    def __init__(self, config: PreprocessConfig) -> None:
        if not isinstance(config, PreprocessConfig):
            raise ValueError("config must be a PreprocessConfig")
        self.config = config

    @staticmethod
    def _read_image(path: Path, mode: str) -> Image.Image:
        if not path.is_file():
            raise ImageLoadError(f"image not found: {path}")
        try:
            with Image.open(path) as opened:
                opened.load()
                image = opened.copy()
        except (OSError, UnidentifiedImageError) as exc:
            raise ImageLoadError(f"cannot read image {path}: {exc}") from exc
        if image.mode != mode:
            try:
                image = image.convert(mode)
            except (ValueError, OSError) as exc:
                raise ImageLoadError(
                    f"cannot convert {path} to mode {mode!r}: {exc}"
                ) from exc
        return image

    def load(
        self,
        path: str | Path,
        *,
        frame_id: str | None = None,
        timestamp_ms: float | None = None,
    ) -> ImageFrame:
        path = Path(path)
        image = self._read_image(path, self.config.mode)
        return self.from_image(
            image,
            source_path=path,
            frame_id=path.stem if frame_id is None else frame_id,
            timestamp_ms=timestamp_ms,
        )

    def from_image(
        self,
        image: Image.Image,
        *,
        source_path: str | Path | None = None,
        frame_id: str | None = None,
        timestamp_ms: float | None = None,
    ) -> ImageFrame:
        if not isinstance(image, Image.Image):
            raise ImageLoadError("image must be a PIL image")
        width, height = image.size
        _positive_size(width, "image width")
        _positive_size(height, "image height")
        if image.mode != self.config.mode:
            try:
                image = image.convert(self.config.mode)
            except (ValueError, OSError) as exc:
                raise ImageLoadError(
                    f"cannot convert image to mode {self.config.mode!r}: {exc}"
                ) from exc

        left = int(round(width * self.config.crop_left_fraction))
        right = width - int(round(width * self.config.crop_right_fraction))
        top = int(round(height * self.config.crop_top_fraction))
        bottom = height - int(round(height * self.config.crop_bottom_fraction))
        if right - left < 1 or bottom - top < 1:
            raise ImageLoadError("crop leaves an empty viewport")

        cropped = image.crop((left, top, right, bottom))
        if self.config.resize is not None:
            resized = cropped.resize(
                self.config.resize, resample=Image.Resampling.BILINEAR
            )
        else:
            resized = cropped
        processed_width, processed_height = resized.size
        viewport_width = right - left
        viewport_height = bottom - top
        source = Path(source_path) if source_path is not None else None
        return ImageFrame(
            pixels=resized,
            original_size=(width, height),
            crop_box=(left, top, right, bottom),
            processed_size=(processed_width, processed_height),
            scale_x=processed_width / viewport_width,
            scale_y=processed_height / viewport_height,
            source_path=source,
            frame_id=frame_id,
            timestamp_ms=timestamp_ms,
        )
