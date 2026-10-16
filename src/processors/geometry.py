"""Tính toán hình học vật thể – diện tích Shoelace, bbox, COCO scale (WBS 2.3).

Ánh xạ sang DAX Measures:
    #15 Avg_Object_Area_Pixels   → avg_object_area
    #16 Avg_Area_Frame_Pct       → avg_area_frame_pct
    #17 Pct_Small_Objects        → pct_small_objects

Các hàm bổ sung: shoelace_area, rectangle_area, coco_scale, measure_shape,
size_scale_counts.

Quy ước (readmereport.md mục 4.5):
    - Tọa độ hỏng (rectangle < 4 số, polygon < 3 đỉnh) → ValueError.
    - Loại shape không đo được ('points', 'cuboid', ...) → các trường đo là None.
    - frame_area_pct là % (0–100), không phải tỷ số 0–1.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List, Optional, Sequence

from ._math import mean_or_none, safe_div
from .config import THRESHOLDS


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass
class ShapeGeometry:
    """Kết quả đo hình học của một đối tượng đã vẽ."""
    shape_type: str
    area_pixels: Optional[float]         # px²; None nếu không đo được
    size_scale: Optional[str]            # 'Small' | 'Medium' | 'Large' | None
    frame_area_pct: Optional[float]      # % chiếm dụng khung hình (0–100); None nếu thiếu frame_size


# ---------------------------------------------------------------------------
# Primitive area functions
# ---------------------------------------------------------------------------

def rectangle_area(points: Sequence[float]) -> float:
    """Diện tích bbox từ [x1, y1, x2, y2].

    Raises ValueError nếu ít hơn 4 số.
    """
    if len(points) < 4:
        raise ValueError(f"Rectangle cần ít nhất 4 số tọa độ, nhận được {len(points)}")
    x1, y1, x2, y2 = points[0], points[1], points[2], points[3]
    return abs(x2 - x1) * abs(y2 - y1)


def shoelace_area(points: Sequence[float]) -> float:
    """Diện tích polygon bằng công thức Shoelace (Gauss).

    points: [x0, y0, x1, y1, ..., xn, yn] – tối thiểu 3 đỉnh (6 số).

    Raises ValueError nếu số điểm < 3 đỉnh.
    """
    n_coords = len(points)
    if n_coords < 6 or n_coords % 2 != 0:
        raise ValueError(
            f"Polygon cần ít nhất 3 đỉnh (6 số tọa độ), nhận được {n_coords}"
        )
    xs = points[0::2]
    ys = points[1::2]
    n = len(xs)
    area = 0.0
    for i in range(n):
        j = (i + 1) % n
        area += xs[i] * ys[j]
        area -= xs[j] * ys[i]
    return abs(area) / 2.0


# ---------------------------------------------------------------------------
# COCO scale classifier
# ---------------------------------------------------------------------------

def coco_scale(area_pixels: float) -> str:
    """Phân loại kích thước vật thể theo chuẩn COCO (mục 4.3).

    | Diện tích (px²) | Nhãn   |
    |-----------------|--------|
    | < 1024          | Small  |
    | 1024 – 9216     | Medium |
    | > 9216          | Large  |
    """
    if area_pixels < THRESHOLDS.coco_small_max:
        return "Small"
    if area_pixels <= THRESHOLDS.coco_medium_max:
        return "Medium"
    return "Large"


# ---------------------------------------------------------------------------
# Main measurement entry point
# ---------------------------------------------------------------------------

def measure_shape(
    shape_type: str,
    points: Sequence[float],
    frame_width: float,
    frame_height: float,
) -> ShapeGeometry:
    """Đo diện tích và phân loại kích thước cho một đối tượng.

    shape_type: 'rectangle' | 'polygon' | 'polyline' | 'points' | 'cuboid' | ...
    frame_width, frame_height: kích thước ảnh (pixel). Dùng 0 nếu không biết.
    """
    area: Optional[float] = None
    scale: Optional[str] = None
    frame_pct: Optional[float] = None

    try:
        if shape_type == "rectangle":
            area = rectangle_area(points)
        elif shape_type in ("polygon", "polyline"):
            area = shoelace_area(points)
        # Các loại không đo được: points, cuboid, ellipse, ...
    except ValueError:
        raise

    if area is not None:
        scale = coco_scale(area)
        frame_area = frame_width * frame_height
        if frame_area > 0:
            frame_pct = (area / frame_area) * 100.0

    return ShapeGeometry(
        shape_type=shape_type,
        area_pixels=area,
        size_scale=scale,
        frame_area_pct=frame_pct,
    )


# ---------------------------------------------------------------------------
# Aggregate geometry measures
# ---------------------------------------------------------------------------

def avg_object_area(geometries: Sequence[ShapeGeometry]) -> Optional[float]:
    """DAX #15 – diện tích pixel trung bình của các đối tượng có thể đo."""
    return mean_or_none(g.area_pixels for g in geometries)


def avg_area_frame_pct(geometries: Sequence[ShapeGeometry]) -> Optional[float]:
    """DAX #16 – tỷ lệ chiếm dụng khung hình trung bình (%)."""
    return mean_or_none(g.frame_area_pct for g in geometries)


def pct_small_objects(geometries: Sequence[ShapeGeometry]) -> Optional[float]:
    """DAX #17 – tỷ lệ vật thể nhỏ (< 1024 px²) trong toàn bộ đối tượng có scale."""
    measurable = [g for g in geometries if g.size_scale is not None]
    if not measurable:
        return None
    small = sum(1 for g in measurable if g.size_scale == "Small")
    return safe_div(small, len(measurable))


def size_scale_counts(geometries: Sequence[ShapeGeometry]) -> dict:
    """Đếm số lượng theo từng nhóm kích thước COCO."""
    counts = {"Small": 0, "Medium": 0, "Large": 0, "Unmeasured": 0}
    for g in geometries:
        if g.size_scale in counts:
            counts[g.size_scale] += 1
        else:
            counts["Unmeasured"] += 1
    return counts
