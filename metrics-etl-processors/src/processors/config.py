"""Toàn bộ ngưỡng nghiệp vụ dùng chung trong tầng processors.

Thay đổi ngưỡng tại đây để ảnh hưởng đồng bộ lên velocity, quality, geometry
và segmentation. Mỗi thay đổi cần được Lead (Đinh Công Minh) chấp thuận
(xem PROJECT_MANAGEMENT_PLAN.md mục 4.5 – giả định #1 đến #8).
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Thresholds:
    # --- Lọc idle (WBS 4.4) ---
    idle_gap_seconds: int = 300          # khoảng lặng dài hơn này coi là treo máy

    # --- Cửa sổ dự báo ETA (WBS 4.2) ---
    eta_window_days: int = 7             # lấy số frame hoàn thành trong N ngày gần nhất

    # --- Phân khúc vận tốc (mục 4.1) – đơn vị frames/giờ ---
    velocity_super_fast: float = 60.0   # >= siêu nhanh
    velocity_on_target: float = 40.0    # >= đạt chuẩn
    velocity_average: float = 20.0      # >= trung bình; dưới ngưỡng này là chậm

    # --- Phân khúc chất lượng (mục 4.2) ---
    ftpr_risk_threshold: float = 0.80   # FTPR < ngưỡng này là rủi ro
    rejection_risk_threshold: float = 0.20  # rejection_rate >= ngưỡng này là rủi ro
    f1_risk_threshold: float = 0.85     # F1 < ngưỡng này là rủi ro (ISNULL → 1.0)

    # --- Phân khúc Onboarding (mục 4.4 nhóm 5) ---
    onboarding_days: int = 14            # thâm niên <= N ngày
    onboarding_max_jobs: int = 10        # jobs completed <= N

    # --- Phân khúc Inactive (mục 4.4 nhóm 6) ---
    inactive_window_days: int = 7        # không có giờ hoạt động trong N ngày

    # --- COCO scale (mục 4.3) – đơn vị px² ---
    coco_small_max: float = 1024.0       # < ngưỡng này là Small (32×32)
    coco_medium_max: float = 9216.0      # <= ngưỡng này là Medium (96×96); lớn hơn là Large

    # --- Đơn vị xuất CSV ---
    # Tài liệu ghi avg_velocity_fps là frames/phút (giả định #6)
    # Code tính theo frames/giờ; dùng hằng này để quy đổi khi export
    frames_per_hour_to_per_minute: float = 1.0 / 60.0


# Singleton dùng trong toàn bộ processors
THRESHOLDS = Thresholds()
