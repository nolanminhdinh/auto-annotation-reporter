"""Unit tests cho module geometry (WBS 2.3)."""
from __future__ import annotations

import unittest
from src.processors.geometry import (
    ShapeGeometry,
    avg_area_frame_pct,
    avg_object_area,
    coco_scale,
    measure_shape,
    pct_small_objects,
    rectangle_area,
    shoelace_area,
    size_scale_counts,
)


class TestGeometry(unittest.TestCase):
    def test_rectangle_area_normal(self) -> None:
        self.assertEqual(rectangle_area([10, 20, 30, 60]), 800.0)
        self.assertEqual(rectangle_area([30, 60, 10, 20]), 800.0)

    def test_rectangle_area_invalid_points(self) -> None:
        with self.assertRaises(ValueError):
            rectangle_area([10, 20, 30])

    def test_shoelace_area_triangle(self) -> None:
        # Tam giác vuông: (0,0), (4,0), (0,3) -> area = 6
        points = [0.0, 0.0, 4.0, 0.0, 0.0, 3.0]
        self.assertAlmostEqual(shoelace_area(points), 6.0)

    def test_shoelace_area_invalid_points(self) -> None:
        with self.assertRaises(ValueError):
            shoelace_area([0, 0, 1, 1])

    def test_coco_scale(self) -> None:
        self.assertEqual(coco_scale(500), "Small")
        self.assertEqual(coco_scale(1023.9), "Small")
        self.assertEqual(coco_scale(1024), "Medium")
        self.assertEqual(coco_scale(5000), "Medium")
        self.assertEqual(coco_scale(9216), "Medium")
        self.assertEqual(coco_scale(9216.1), "Large")

    def test_measure_shape_rectangle(self) -> None:
        geo = measure_shape("rectangle", [0, 0, 20, 40], frame_width=100, frame_height=100)
        self.assertEqual(geo.shape_type, "rectangle")
        self.assertEqual(geo.area_pixels, 800.0)
        self.assertEqual(geo.size_scale, "Small")
        self.assertAlmostEqual(geo.frame_area_pct, 8.0)

    def test_measure_shape_unmeasurable(self) -> None:
        geo = measure_shape("points", [10, 20], frame_width=100, frame_height=100)
        self.assertIsNone(geo.area_pixels)
        self.assertIsNone(geo.size_scale)
        self.assertIsNone(geo.frame_area_pct)

    def test_aggregate_measures(self) -> None:
        g1 = ShapeGeometry("rectangle", 500.0, "Small", 5.0)
        g2 = ShapeGeometry("rectangle", 2000.0, "Medium", 20.0)
        g3 = ShapeGeometry("points", None, None, None)

        self.assertAlmostEqual(avg_object_area([g1, g2, g3]), 1250.0)
        self.assertAlmostEqual(avg_area_frame_pct([g1, g2, g3]), 12.5)
        self.assertAlmostEqual(pct_small_objects([g1, g2, g3]), 0.5)

        counts = size_scale_counts([g1, g2, g3])
        self.assertEqual(counts["Small"], 1)
        self.assertEqual(counts["Medium"], 1)
        self.assertEqual(counts["Large"], 0)
        self.assertEqual(counts["Unmeasured"], 1)


if __name__ == "__main__":
    unittest.main()
