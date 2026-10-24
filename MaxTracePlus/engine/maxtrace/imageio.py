"""Image loading with predictable colour and alpha handling."""

from __future__ import annotations

import hashlib
import os

import cv2
import numpy as np

SUPPORTED_EXT = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".exr", ".webp"}


class ImageLoadError(RuntimeError):
    pass


def file_digest(path: str, chunk: int = 1 << 20) -> str:
    h = hashlib.sha1()
    with open(path, "rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def load_rgb(path: str) -> np.ndarray:
    """Load an image as float32 RGB in [0, 1] (alpha composited if present).

    Transparent areas are composited over the median colour of the opaque
    area, which keeps line/background contrast intact regardless of whether
    the producer (e.g. a Fusion Saver) wrote straight or premultiplied alpha.
    """
    if not os.path.isfile(path):
        raise ImageLoadError(f"Image file not found: {path}")
    ext = os.path.splitext(path)[1].lower()
    if ext not in SUPPORTED_EXT:
        raise ImageLoadError(f"Unsupported image format '{ext}'. Use PNG, JPG or TIFF.")
    if ext == ".exr":
        os.environ.setdefault("OPENCV_IO_ENABLE_OPENEXR", "1")
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ImageLoadError(f"Could not decode image: {os.path.basename(path)}")
    if img.dtype == np.uint8:
        f = img.astype(np.float32) / 255.0
    elif img.dtype == np.uint16:
        f = img.astype(np.float32) / 65535.0
    else:
        f = np.clip(img.astype(np.float32), 0.0, 1.0)
    if f.ndim == 2:
        f = cv2.cvtColor(f, cv2.COLOR_GRAY2BGR)
    if f.shape[2] == 4:
        bgr = f[:, :, :3]
        a = f[:, :, 3:4]
        opaque = a[:, :, 0] > 0.98
        if opaque.any():
            base = np.median(bgr[opaque], axis=0)
        else:
            base = np.array([1.0, 1.0, 1.0], np.float32)
        if not opaque.all():
            # Detect premultiplied data: colour never exceeds alpha.
            premult = bool(np.all(bgr <= a + 1.5 / 255.0))
            fg = bgr if premult else bgr * a
            bgr = fg + base[None, None, :] * (1.0 - a)
        f = bgr
    elif f.shape[2] != 3:
        raise ImageLoadError("Unsupported channel layout")
    rgb = cv2.cvtColor(np.ascontiguousarray(f, dtype=np.float32), cv2.COLOR_BGR2RGB)
    if rgb.shape[0] < 16 or rgb.shape[1] < 16:
        raise ImageLoadError("Image is too small to analyse")
    return rgb


def load_alpha(path: str) -> np.ndarray:
    """Load the alpha channel (float32 0..1); opaque images return ones."""
    data = np.fromfile(path, dtype=np.uint8)
    img = cv2.imdecode(data, cv2.IMREAD_UNCHANGED)
    if img is None:
        raise ImageLoadError(f"Could not decode image: {os.path.basename(path)}")
    scale = 65535.0 if img.dtype == np.uint16 else (255.0 if img.dtype == np.uint8 else 1.0)
    if img.ndim == 3 and img.shape[2] == 4:
        return img[:, :, 3].astype(np.float32) / scale
    return np.ones(img.shape[:2], np.float32)


def rgb_to_lab(rgb: np.ndarray) -> np.ndarray:
    """float RGB [0,1] -> CIE Lab (L 0..100). Input treated as sRGB."""
    return cv2.cvtColor(np.ascontiguousarray(rgb, dtype=np.float32), cv2.COLOR_RGB2LAB)


def lab_to_rgb(lab: np.ndarray) -> np.ndarray:
    lab = np.asarray(lab, np.float32).reshape(1, -1, 3)
    return np.clip(cv2.cvtColor(lab, cv2.COLOR_LAB2RGB).reshape(-1, 3), 0, 1)


def hex_to_rgb(value: str) -> tuple[float, float, float]:
    v = value.strip().lstrip("#")
    if len(v) == 3:
        v = "".join(c * 2 for c in v)
    if len(v) != 6:
        raise ValueError(f"Invalid hex colour '{value}'")
    return tuple(int(v[i : i + 2], 16) / 255.0 for i in (0, 2, 4))  # type: ignore[return-value]


def rgb_to_hex(rgb) -> str:
    r, g, b = (int(round(float(c) * 255)) for c in rgb)
    return "#{:02X}{:02X}{:02X}".format(max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b)))
