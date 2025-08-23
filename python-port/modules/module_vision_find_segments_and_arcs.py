"""Advanced segment and arc detection module.

Specialized computer vision module for detecting and analyzing line segments
and circular arcs in images, with enhanced algorithms and OpenCV integration.
"""
from __future__ import annotations
import math
import numpy as np
from typing import Iterable, List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

try:
    import cv2
except Exception:  # pragma: no cover
    cv2 = None

from .module_base import ModuleBase
from vision.point_plus import PointPlus
from vision.geometry import Segment, Arc


@dataclass
class LineDetectionResult:
    """Result of line segment detection."""
    segments: List[Segment]
    total_length: float
    avg_length: float
    angles: List[float]
    
@dataclass 
class ArcDetectionResult:
    """Result of arc detection."""
    arcs: List[Arc]
    total_arc_length: float
    avg_radius: float
    centers: List[PointPlus]


class ModuleVisionFindSegmentsAndArcs(ModuleBase):
    """Advanced geometric primitive detection from edge points.
    
    Enhanced with:
    - Multiple detection algorithms
    - Parameter tuning capabilities
    - Statistical analysis of results
    - Integration with OpenCV methods
    - Robust error handling
    """

    def __init__(self, edges: Iterable[PointPlus] | None = None):
        super().__init__()
        self.edges: List[PointPlus] = list(edges) if edges else []
        self.segments: List[Segment] = []
        self.arcs: List[Arc] = []
        
        # Enhanced detection parameters
        self.segment_tolerance = 0.01
        self.min_segment_length = 5
        self.arc_tolerance = 1.0
        self.min_arc_points = 3
        self.max_arc_gap = 2.0
        self.merge_segments = True
        self.merge_threshold = 5.0
        
        # Results tracking
        self.detection_stats = {}
        self.last_detection_time = 0.0

    def set_edges(self, edges: Iterable[PointPlus]) -> None:
        self.edges = list(edges)

    # --------------------------------------------------------------
    def initialize(self) -> None:
        pass

    def fire(self) -> None:
        """Enhanced detection with statistics tracking."""
        import time
        start_time = time.time()
        
        # Clear previous results
        self.segments.clear()
        self.arcs.clear()
        
        if not self.edges:
            return
            
        # Enhanced segment detection
        segments, used_points = self._detect_segments_enhanced(self.edges)
        
        # Optional segment merging
        if self.merge_segments:
            segments = self._merge_similar_segments(segments)
            
        self.segments = segments
        
        # Detect arcs from remaining points
        remaining = [p for p in self.edges if p not in used_points]
        self.arcs = self._detect_arcs_enhanced(remaining)
        
        # Update statistics
        self.last_detection_time = time.time() - start_time
        self._update_detection_stats()

    # --------------------------------------------------------------
    def _detect_segments_enhanced(self, points: List[PointPlus]) -> Tuple[List[Segment], set[PointPlus]]:
        """Enhanced segment detection with multiple algorithms."""
        segments: List[Segment] = []
        used: set[PointPlus] = set()
        
        if len(points) < 2:
            return segments, used
            
        # Primary method: collinearity-based detection
        primary_segments, primary_used = self._detect_segments_collinear(
            points, self.segment_tolerance
        )
        segments.extend(primary_segments)
        used.update(primary_used)
        
        # Secondary method: RANSAC-like robust fitting for remaining points
        remaining = [p for p in points if p not in used]
        if len(remaining) >= 2 and cv2 is not None:
            ransac_segments, ransac_used = self._detect_segments_ransac(remaining)
            segments.extend(ransac_segments)
            used.update(ransac_used)
            
        # Filter by minimum length
        valid_segments = []
        final_used = set()
        
        for seg in segments:
            if seg.length >= self.min_segment_length:
                valid_segments.append(seg)
                # Add points that contribute to this segment
                for p in points:
                    if self._point_near_segment(p, seg, self.segment_tolerance * 2):
                        final_used.add(p)
                        
        return valid_segments, final_used
        
    def _detect_segments_collinear(self, points: List[PointPlus], tol: float) -> Tuple[List[Segment], set[PointPlus]]:
        """Original collinearity-based segment detection."""
        segments: List[Segment] = []
        used: set[PointPlus] = set()
        i = 0
        n = len(points)
        
        while i < n - 1:
            j = i + 1
            while j < n:
                if j - i < 2:
                    j += 1
                    continue
                if not self._collinear(points[i], points[j], points[i + 1:j], tol):
                    break
                j += 1
            if j - i >= 3:
                seg = Segment(points[i], points[j - 1])
                segments.append(seg)
                used.update(points[i:j])
            i = j
        return segments, used
        
    def _detect_segments_ransac(self, points: List[PointPlus]) -> Tuple[List[Segment], set[PointPlus]]:
        """RANSAC-based line fitting for robust segment detection."""
        segments: List[Segment] = []
        used: set[PointPlus] = set()
        
        if len(points) < 2:
            return segments, used
            
        # Convert to numpy array for OpenCV
        pts_array = np.array([[p.x, p.y] for p in points], dtype=np.float32)
        
        # Try to fit lines using RANSAC
        remaining_points = list(points)
        
        while len(remaining_points) >= self.min_segment_length:
            if len(remaining_points) < 2:
                break
                
            # Convert current remaining points
            curr_array = np.array([[p.x, p.y] for p in remaining_points], dtype=np.float32)
            
            # Fit line using fitLine with RANSAC-like method
            if len(curr_array) >= 2:
                try:
                    line_params = cv2.fitLine(curr_array, cv2.DIST_L2, 0, 0.01, 0.01)
                    vx, vy, x0, y0 = line_params.flatten()
                    
                    # Find inliers
                    inliers = []
                    for i, p in enumerate(remaining_points):
                        dist = self._point_to_line_distance(p, vx, vy, x0, y0)
                        if dist < self.segment_tolerance * 5:  # More tolerant for RANSAC
                            inliers.append(p)
                            
                    if len(inliers) >= self.min_segment_length:
                        # Create segment from extreme inliers
                        start_idx = 0
                        end_idx = len(inliers) - 1
                        
                        segment = Segment(inliers[start_idx], inliers[end_idx])
                        segments.append(segment)
                        used.update(inliers)
                        
                        # Remove inliers from remaining points
                        remaining_points = [p for p in remaining_points if p not in inliers]
                    else:
                        break
                        
                except Exception:
                    break
            else:
                break
                
        return segments, used
        
    def _point_to_line_distance(self, point: PointPlus, vx: float, vy: float, x0: float, y0: float) -> float:
        """Calculate distance from point to line defined by direction vector and point."""
        # Line: (x0, y0) + t*(vx, vy)
        # Distance = |((point.x - x0) * vy - (point.y - y0) * vx)| / sqrt(vx^2 + vy^2)
        numerator = abs((point.x - x0) * vy - (point.y - y0) * vx)
        denominator = math.sqrt(vx*vx + vy*vy)
        return numerator / denominator if denominator > 1e-10 else float('inf')
        
    def _point_near_segment(self, point: PointPlus, segment: Segment, tolerance: float) -> bool:
        """Check if a point is near a line segment."""
        # Vector from segment start to end
        seg_vec = PointPlus(segment.end.x - segment.start.x, segment.end.y - segment.start.y)
        # Vector from segment start to point
        point_vec = PointPlus(point.x - segment.start.x, point.y - segment.start.y)
        
        seg_length_sq = seg_vec.x**2 + seg_vec.y**2
        if seg_length_sq == 0:
            return point.distance_to(segment.start) < tolerance
            
        # Project point onto segment line
        t = (point_vec.x * seg_vec.x + point_vec.y * seg_vec.y) / seg_length_sq
        t = max(0, min(1, t))  # Clamp to segment
        
        # Find closest point on segment
        closest = PointPlus(
            segment.start.x + t * seg_vec.x,
            segment.start.y + t * seg_vec.y
        )
        
        return point.distance_to(closest) < tolerance

    def _collinear(self, p1: PointPlus, p2: PointPlus, pts: Iterable[PointPlus], tol: float) -> bool:
        """Enhanced collinearity test with better numerical stability."""
        for p in pts:
            # Calculate area of triangle formed by three points
            area = abs(p1.x * (p2.y - p.y) + p2.x * (p.y - p1.y) + p.x * (p1.y - p2.y))
            # Normalize by distance to handle varying scales
            base_dist = p1.distance_to(p2)
            if base_dist > 0:
                normalized_area = area / base_dist
                if normalized_area > tol:
                    return False
            elif area > tol:  # Fallback for degenerate case
                return False
        return True

    # --------------------------------------------------------------
    def _circle_from_points(self, p1: PointPlus, p2: PointPlus, p3: PointPlus) -> Optional[Tuple[PointPlus, float]]:
        """Enhanced circle fitting with better numerical stability."""
        try:
            # Check for collinear points first
            area = abs(p1.x * (p2.y - p3.y) + p2.x * (p3.y - p1.y) + p3.x * (p1.y - p2.y))
            if area < 1e-10:  # Points are collinear
                return None
                
            temp = p2.x ** 2 + p2.y ** 2
            bc = (p1.x ** 2 + p1.y ** 2 - temp) / 2.0
            cd = (temp - p3.x ** 2 - p3.y ** 2) / 2.0
            det = (p1.x - p2.x) * (p2.y - p3.y) - (p2.x - p3.x) * (p1.y - p2.y)
            
            if abs(det) < 1e-10:
                return None
                
            cx = (bc * (p2.y - p3.y) - cd * (p1.y - p2.y)) / det
            cy = ((p1.x - p2.x) * cd - (p2.x - p3.x) * bc) / det
            center = PointPlus(cx, cy)
            
            # Verify all three points are equidistant from center
            r1 = center.distance_to(p1)
            r2 = center.distance_to(p2)
            r3 = center.distance_to(p3)
            
            # Check if radii are consistent
            if abs(r1 - r2) > self.arc_tolerance or abs(r1 - r3) > self.arc_tolerance:
                return None
                
            return center, r1
        except (ZeroDivisionError, ValueError, OverflowError):
            return None

    def _detect_arcs_enhanced(self, points: List[PointPlus]) -> List[Arc]:
        """Enhanced arc detection with multiple methods and validation."""
        if len(points) < self.min_arc_points:
            return []
            
        arcs: List[Arc] = []
        
        # Method 1: Sliding window circle fitting
        arcs.extend(self._detect_arcs_sliding_window(points))
        
        # Method 2: RANSAC-based circle fitting for remaining points
        if cv2 is not None:
            used_points = set()
            for arc in arcs:
                # Mark points as used if they're close to existing arcs
                for p in points:
                    dist_to_arc = abs(arc.center.distance_to(p) - arc.radius)
                    if dist_to_arc < self.arc_tolerance:
                        used_points.add(p)
                        
            remaining = [p for p in points if p not in used_points]
            ransac_arcs = self._detect_arcs_ransac(remaining)
            arcs.extend(ransac_arcs)
            
        return self._validate_arcs(arcs)
        
    def _detect_arcs_sliding_window(self, points: List[PointPlus]) -> List[Arc]:
        """Detect arcs using sliding window approach."""
        arcs: List[Arc] = []
        n = len(points)
        
        if n < self.min_arc_points:
            return arcs
            
        # Try different window sizes
        for window_size in range(self.min_arc_points, min(n + 1, 20)):
            for i in range(n - window_size + 1):
                window_points = points[i:i + window_size]
                
                # Try to fit circle to first three points
                if len(window_points) >= 3:
                    circle_result = self._circle_from_points(
                        window_points[0], 
                        window_points[len(window_points)//2], 
                        window_points[-1]
                    )
                    
                    if circle_result:
                        center, radius = circle_result
                        
                        # Check how many points fit this circle
                        fitting_points = []
                        for p in window_points:
                            if abs(center.distance_to(p) - radius) < self.arc_tolerance:
                                fitting_points.append(p)
                                
                        # If enough points fit, create arc
                        if len(fitting_points) >= self.min_arc_points:
                            start_angle = math.atan2(
                                fitting_points[0].y - center.y, 
                                fitting_points[0].x - center.x
                            )
                            end_angle = math.atan2(
                                fitting_points[-1].y - center.y, 
                                fitting_points[-1].x - center.x
                            )
                            
                            arc = Arc(center, radius, start_angle, end_angle)
                            
                            # Check if this arc is significantly different from existing ones
                            if not self._is_duplicate_arc(arc, arcs):
                                arcs.append(arc)
                                
        return arcs
        
    def _detect_arcs_ransac(self, points: List[PointPlus]) -> List[Arc]:
        """RANSAC-based arc detection."""
        arcs: List[Arc] = []
        remaining_points = list(points)
        
        max_iterations = 100
        
        while len(remaining_points) >= self.min_arc_points and max_iterations > 0:
            max_iterations -= 1
            
            if len(remaining_points) < 3:
                break
                
            # Randomly sample three points
            import random
            sample_indices = random.sample(range(len(remaining_points)), 3)
            p1 = remaining_points[sample_indices[0]]
            p2 = remaining_points[sample_indices[1]] 
            p3 = remaining_points[sample_indices[2]]
            
            circle_result = self._circle_from_points(p1, p2, p3)
            if not circle_result:
                continue
                
            center, radius = circle_result
            
            # Find inliers
            inliers = []
            for p in remaining_points:
                if abs(center.distance_to(p) - radius) < self.arc_tolerance:
                    inliers.append(p)
                    
            if len(inliers) >= self.min_arc_points:
                # Create arc from inliers
                angles = []
                for p in inliers:
                    angle = math.atan2(p.y - center.y, p.x - center.x)
                    angles.append(angle)
                    
                angles.sort()
                start_angle = angles[0]
                end_angle = angles[-1]
                
                arc = Arc(center, radius, start_angle, end_angle)
                arcs.append(arc)
                
                # Remove inliers from remaining points
                remaining_points = [p for p in remaining_points if p not in inliers]
                
        return arcs
        
    def _is_duplicate_arc(self, new_arc: Arc, existing_arcs: List[Arc]) -> bool:
        """Check if an arc is similar to existing ones."""
        for existing in existing_arcs:
            center_dist = new_arc.center.distance_to(existing.center)
            radius_diff = abs(new_arc.radius - existing.radius)
            
            if center_dist < self.merge_threshold and radius_diff < self.arc_tolerance:
                return True
        return False
        
    def _validate_arcs(self, arcs: List[Arc]) -> List[Arc]:
        """Validate and filter detected arcs."""
        valid_arcs = []
        
        for arc in arcs:
            # Check minimum radius
            if arc.radius < 3.0:
                continue
                
            # Check reasonable angle span
            angle_span = abs(arc.end_angle - arc.start_angle)
            if angle_span < math.pi / 12:  # Less than 15 degrees
                continue
                
            # Check if arc is not too large compared to the point cloud
            if arc.radius > 1000:  # Reasonable upper bound
                continue
                
            valid_arcs.append(arc)
            
        return valid_arcs
        
    def _merge_similar_segments(self, segments: List[Segment]) -> List[Segment]:
        """Merge segments that are close and have similar orientations."""
        if not segments:
            return segments
            
        merged = []
        used = set()
        
        for i, seg1 in enumerate(segments):
            if i in used:
                continue
                
            # Find segments to merge with this one
            to_merge = [seg1]
            used.add(i)
            
            for j, seg2 in enumerate(segments[i+1:], i+1):
                if j in used:
                    continue
                    
                if self._should_merge_segments(seg1, seg2):
                    to_merge.append(seg2)
                    used.add(j)
                    
            # Create merged segment
            merged_segment = self._create_merged_segment(to_merge)
            merged.append(merged_segment)
            
        return merged
        
    def _should_merge_segments(self, seg1: Segment, seg2: Segment) -> bool:
        """Check if two segments should be merged."""
        # Check angle similarity
        angle1 = math.atan2(seg1.end.y - seg1.start.y, seg1.end.x - seg1.start.x)
        angle2 = math.atan2(seg2.end.y - seg2.start.y, seg2.end.x - seg2.start.x)
        angle_diff = abs(angle1 - angle2)
        
        if angle_diff > math.pi:
            angle_diff = 2 * math.pi - angle_diff
            
        if angle_diff > math.pi / 12:  # 15 degrees
            return False
            
        # Check distance between segments
        distances = [
            seg1.start.distance_to(seg2.start),
            seg1.start.distance_to(seg2.end),
            seg1.end.distance_to(seg2.start),
            seg1.end.distance_to(seg2.end)
        ]
        
        min_distance = min(distances)
        return min_distance < self.merge_threshold
        
    def _create_merged_segment(self, segments: List[Segment]) -> Segment:
        """Create a single segment from multiple segments."""
        if len(segments) == 1:
            return segments[0]
            
        # Find the two points that are furthest apart
        all_points = []
        for seg in segments:
            all_points.extend([seg.start, seg.end])
            
        max_dist = 0
        best_start, best_end = all_points[0], all_points[1]
        
        for i, p1 in enumerate(all_points):
            for j, p2 in enumerate(all_points[i+1:], i+1):
                dist = p1.distance_to(p2)
                if dist > max_dist:
                    max_dist = dist
                    best_start, best_end = p1, p2
                    
        return Segment(best_start, best_end)
        
    def _update_detection_stats(self) -> None:
        """Update detection statistics."""
        self.detection_stats = {
            'segments': len(self.segments),
            'arcs': len(self.arcs),
            'total_length': sum(s.length for s in self.segments),
            'avg_segment_length': np.mean([s.length for s in self.segments]) if self.segments else 0,
            'avg_arc_radius': np.mean([a.radius for a in self.arcs]) if self.arcs else 0,
            'detection_time': self.last_detection_time
        }
        
    def get_line_detection_result(self) -> LineDetectionResult:
        """Get structured line detection results."""
        if not self.segments:
            return LineDetectionResult([], 0, 0, [])
            
        total_length = sum(s.length for s in self.segments)
        avg_length = total_length / len(self.segments)
        angles = [math.atan2(s.end.y - s.start.y, s.end.x - s.start.x) for s in self.segments]
        
        return LineDetectionResult(self.segments, total_length, avg_length, angles)
        
    def get_arc_detection_result(self) -> ArcDetectionResult:
        """Get structured arc detection results."""
        if not self.arcs:
            return ArcDetectionResult([], 0, 0, [])
            
        total_arc_length = sum(a.radius * abs(a.end_angle - a.start_angle) for a in self.arcs)
        avg_radius = sum(a.radius for a in self.arcs) / len(self.arcs)
        centers = [a.center for a in self.arcs]
        
        return ArcDetectionResult(self.arcs, total_arc_length, avg_radius, centers)
        
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Set detection parameters."""
        for key, value in params.items():
            if hasattr(self, key):
                setattr(self, key, value)
                
    def get_parameters(self) -> Dict[str, Any]:
        """Get current parameters."""
        return {
            'segment_tolerance': self.segment_tolerance,
            'min_segment_length': self.min_segment_length,
            'arc_tolerance': self.arc_tolerance,
            'min_arc_points': self.min_arc_points,
            'max_arc_gap': self.max_arc_gap,
            'merge_segments': self.merge_segments,
            'merge_threshold': self.merge_threshold
        }
        
    def get_detection_summary(self) -> Dict[str, Any]:
        """Get comprehensive detection summary."""
        line_result = self.get_line_detection_result()
        arc_result = self.get_arc_detection_result()
        
        return {
            'input_points': len(self.edges),
            'segments_detected': len(self.segments),
            'arcs_detected': len(self.arcs),
            'total_segment_length': line_result.total_length,
            'total_arc_length': arc_result.total_arc_length,
            'avg_segment_length': line_result.avg_length,
            'avg_arc_radius': arc_result.avg_radius,
            'detection_time_ms': self.last_detection_time * 1000,
            'stats': self.detection_stats
        }
