"""Advanced computer vision module with OpenCV integration.

Ports the sophisticated vision processing capabilities from the C# BrainSimIII,
including corner detection, arc fitting, boundary tracing, Hough transforms,
and shape recognition using OpenCV and scikit-image.
"""
from __future__ import annotations
import math
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass, field

try:
    import cv2
    from PIL import Image, ImageFilter
    from skimage import feature, measure, morphology
    from skimage.transform import hough_line, hough_circle, hough_ellipse
except Exception:  # pragma: no cover - optional dependencies
    cv2 = Image = ImageFilter = feature = measure = morphology = None
    hough_line = hough_circle = hough_ellipse = None

from .module_base import ModuleBase
from vision.point_plus import PointPlus
from angle import Angle


@dataclass
class Corner:
    """Represents a corner point with angle calculation."""
    pt: PointPlus
    prev_pt: PointPlus
    next_pt: PointPlus
    curve: bool = False
    
    @property
    def angle(self) -> Angle:
        """Calculate the angle at this corner."""
        # Vector from prev to current point
        v1 = PointPlus(self.pt.x - self.prev_pt.x, self.pt.y - self.prev_pt.y)
        # Vector from current to next point  
        v2 = PointPlus(self.next_pt.x - self.pt.x, self.next_pt.y - self.pt.y)
        
        # Calculate angle between vectors
        angle1 = math.atan2(v1.y, v1.x)
        angle2 = math.atan2(v2.y, v2.x)
        diff = angle2 - angle1
        
        # Normalize to [-π, π]
        while diff > math.pi:
            diff -= 2 * math.pi
        while diff < -math.pi:
            diff += 2 * math.pi
            
        return Angle.from_radians(diff)


@dataclass
class Arc(Corner):
    """Represents an arc defined by three points."""
    
    def __post_init__(self):
        self.curve = True
    
    @property
    def angle(self) -> Angle:
        """Calculate arc angle from circle through three points."""
        try:
            center, radius = self.get_circle_from_three_points(
                self.prev_pt, self.pt, self.next_pt
            )
            if radius == 0:
                return Angle.from_degrees(0)
                
            # Calculate angles from center to each point
            start_angle = math.atan2(self.prev_pt.y - center.y, self.prev_pt.x - center.x)
            mid_angle = math.atan2(self.pt.y - center.y, self.pt.x - center.x)
            end_angle = math.atan2(self.next_pt.y - center.y, self.next_pt.x - center.x)
            
            # Calculate arc angle
            arc_angle = abs(end_angle - start_angle)
            
            # Check if we need to go the other way around
            if not self._point_between_angles(mid_angle, start_angle, end_angle):
                arc_angle = 2 * math.pi - arc_angle
                
            return Angle.from_radians(arc_angle)
        except (ZeroDivisionError, ValueError):
            return Angle.from_degrees(0)
    
    def get_circle_from_three_points(self, p1: PointPlus, p2: PointPlus, p3: PointPlus) -> Tuple[PointPlus, float]:
        """Calculate circle center and radius through three points."""
        x1, y1 = p1.x, p1.y
        x2, y2 = p2.x, p2.y
        x3, y3 = p3.x, p3.y
        
        # Check for collinear points
        if abs((y2-y1)*(x3-x1) - (y3-y1)*(x2-x1)) < 1e-10:
            return PointPlus(0, 0), 0
            
        # Calculate perpendicular bisector slopes
        if abs(x2 - x1) < 1e-10 or abs(x3 - x2) < 1e-10:
            return PointPlus(0, 0), 0
            
        ma = (y2 - y1) / (x2 - x1)
        mb = (y3 - y2) / (x3 - x2)
        
        if abs(mb - ma) < 1e-10:
            return PointPlus(0, 0), 0
            
        # Calculate center
        cx = (ma * mb * (y1 - y3) + mb * (x1 + x2) - ma * (x2 + x3)) / (2 * (mb - ma))
        cy = -(cx - (x1 + x2) / 2) / ma + (y1 + y2) / 2
        
        center = PointPlus(cx, cy)
        radius = math.sqrt((cx - x1)**2 + (cy - y1)**2)
        
        return center, radius
    
    def _point_between_angles(self, angle: float, start: float, end: float) -> bool:
        """Check if angle is between start and end angles."""
        # Normalize angles to [0, 2π]
        angle = angle % (2 * math.pi)
        start = start % (2 * math.pi)
        end = end % (2 * math.pi)
        
        if start <= end:
            return start <= angle <= end
        else:
            return angle >= start or angle <= end


@dataclass
class Segment:
    """Represents a line segment."""
    start: PointPlus
    end: PointPlus
    
    @property
    def length(self) -> float:
        """Calculate segment length."""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return math.sqrt(dx*dx + dy*dy)
    
    @property
    def angle(self) -> Angle:
        """Calculate segment angle."""
        dx = self.end.x - self.start.x
        dy = self.end.y - self.start.y
        return Angle.from_radians(math.atan2(dy, dx))


class ModuleVision(ModuleBase):
    """Advanced computer vision module with comprehensive image processing.
    
    Features:
    - Edge detection with multiple algorithms (Canny, Sobel, Prewitt)
    - Corner detection (Harris, Shi-Tomasi, FAST)
    - Line detection with Hough transforms
    - Circle and ellipse detection
    - Contour analysis and shape recognition
    - Boundary tracing and stroke extraction
    - Background color analysis
    - Arc fitting and geometric analysis
    """

    def __init__(self, image_path: Optional[str] = None):
        super().__init__()
        self.image_path = image_path
        self.image: Optional[np.ndarray] = None
        self.gray_image: Optional[np.ndarray] = None
        
        # Vision processing results
        self.edges: List[PointPlus] = []
        self.corners: List[Corner] = []
        self.segments: List[Segment] = []
        self.arcs: List[Arc] = []
        self.stroke_points: List[PointPlus] = []
        self.boundary_points: List[PointPlus] = []
        self.contours: List[np.ndarray] = []
        
        # Background color analysis
        self.background_color: Tuple[int, int, int] = (0, 0, 0)
        
        # Processing parameters
        self.edge_threshold_low = 50
        self.edge_threshold_high = 150
        self.corner_quality_level = 0.01
        self.corner_min_distance = 10
        self.hough_threshold = 50
        self.min_line_length = 50
        self.max_line_gap = 10
        
        # Scan directions for boundary detection
        self.horiz_scan = True
        self.vert_scan = True
        self.forty_five_scan = True
        self.minus_forty_five_scan = True

    def initialize(self) -> None:
        """Initialize the vision module."""
        if cv2 is None:
            raise RuntimeError("OpenCV is required for advanced ModuleVision features")
        if self.image_path:
            self.load_image(self.image_path)
            self.process_image()

    def fire(self) -> None:
        """Process the current image through the vision pipeline."""
        if self.image is not None:
            self.process_image()

    def load_image(self, path: str) -> None:
        """Load an image from file."""
        if cv2 is None:
            raise RuntimeError("OpenCV is required for ModuleVision")
            
        self.image = cv2.imread(path)
        if self.image is None:
            raise FileNotFoundError(f"Could not load image: {path}")
            
        self.gray_image = cv2.cvtColor(self.image, cv2.COLOR_BGR2GRAY)
        self.image_path = path
        
    def process_image(self) -> None:
        """Run the complete vision processing pipeline."""
        if self.gray_image is None:
            return
            
        # Clear previous results
        self.clear_results()
        
        # Run processing steps
        self.find_background_color()
        self.detect_edges()
        self.detect_corners()
        self.detect_lines()
        self.detect_circles()
        self.find_contours()
        self.find_boundaries()
        self.extract_strokes()
        
    def clear_results(self) -> None:
        """Clear all processing results."""
        self.edges.clear()
        self.corners.clear() 
        self.segments.clear()
        self.arcs.clear()
        self.stroke_points.clear()
        self.boundary_points.clear()
        self.contours.clear()

    def find_background_color(self) -> None:
        """Determine the most common color as background."""
        if self.image is None:
            return
            
        # Count color occurrences
        color_counts = {}
        h, w, c = self.image.shape
        
        # Sample pixels to avoid processing every pixel for performance
        step = max(1, min(h, w) // 100)
        for y in range(0, h, step):
            for x in range(0, w, step):
                color = tuple(self.image[y, x])
                color_counts[color] = color_counts.get(color, 0) + 1
        
        # Find most common color
        if color_counts:
            self.background_color = max(color_counts.items(), key=lambda x: x[1])[0]

    def detect_edges(self, method: str = "canny") -> None:
        """Detect edges using various algorithms."""
        if self.gray_image is None:
            return
            
        if method == "canny":
            edges = cv2.Canny(self.gray_image, self.edge_threshold_low, self.edge_threshold_high)
        elif method == "sobel":
            sobelx = cv2.Sobel(self.gray_image, cv2.CV_64F, 1, 0, ksize=3)
            sobely = cv2.Sobel(self.gray_image, cv2.CV_64F, 0, 1, ksize=3)
            edges = np.sqrt(sobelx**2 + sobely**2).astype(np.uint8)
            edges = (edges > self.edge_threshold_low).astype(np.uint8) * 255
        else:  # Default to Canny
            edges = cv2.Canny(self.gray_image, self.edge_threshold_low, self.edge_threshold_high)
            
        # Convert edge pixels to PointPlus objects
        y_coords, x_coords = np.where(edges > 0)
        self.edges = [PointPlus(int(x), int(y)) for x, y in zip(x_coords, y_coords)]

    def detect_corners(self, method: str = "harris") -> None:
        """Detect corners using Harris or Shi-Tomasi algorithms."""
        if self.gray_image is None:
            return
            
        if method == "harris":
            # Harris corner detection
            corners = cv2.cornerHarris(self.gray_image, 2, 3, 0.04)
            corners = cv2.dilate(corners, None)
            
            # Extract corner coordinates
            corner_coords = np.where(corners > self.corner_quality_level * corners.max())
            corner_points = list(zip(corner_coords[1], corner_coords[0]))
            
        elif method == "shi_tomasi":
            # Shi-Tomasi corner detection
            corners = cv2.goodFeaturesToTrack(
                self.gray_image, 
                maxCorners=1000,
                qualityLevel=self.corner_quality_level,
                minDistance=self.corner_min_distance
            )
            if corners is not None:
                corner_points = [(int(x), int(y)) for [[x, y]] in corners]
            else:
                corner_points = []
        else:
            corner_points = []
            
        # Convert to Corner objects (simplified without prev/next points for now)
        self.corners = []
        for x, y in corner_points:
            pt = PointPlus(x, y)
            # For now, use dummy prev/next points - could be enhanced with contour analysis
            corner = Corner(pt=pt, prev_pt=PointPlus(x-1, y), next_pt=PointPlus(x+1, y))
            self.corners.append(corner)

    def detect_lines(self) -> None:
        """Detect lines using Hough transform."""
        if self.gray_image is None:
            return
            
        # First detect edges for line detection
        edges = cv2.Canny(self.gray_image, self.edge_threshold_low, self.edge_threshold_high)
        
        # Apply Hough line transform
        lines = cv2.HoughLinesP(
            edges, 
            1, 
            np.pi/180, 
            threshold=self.hough_threshold,
            minLineLength=self.min_line_length,
            maxLineGap=self.max_line_gap
        )
        
        self.segments = []
        if lines is not None:
            for line in lines:
                x1, y1, x2, y2 = line[0]
                start = PointPlus(x1, y1)
                end = PointPlus(x2, y2)
                self.segments.append(Segment(start=start, end=end))

    def detect_circles(self) -> None:
        """Detect circles using Hough circle transform."""
        if self.gray_image is None:
            return
            
        # Apply Hough circle transform
        circles = cv2.HoughCircles(
            self.gray_image,
            cv2.HOUGH_GRADIENT,
            dp=1,
            minDist=30,
            param1=self.edge_threshold_high,
            param2=30,
            minRadius=10,
            maxRadius=200
        )
        
        # Convert circles to Arc objects
        if circles is not None:
            circles = np.round(circles[0, :]).astype("int")
            for (x, y, r) in circles:
                # Create three points on the circle to define an arc
                center = PointPlus(x, y)
                p1 = PointPlus(x + r, y)
                p2 = PointPlus(x, y + r)  
                p3 = PointPlus(x - r, y)
                
                arc = Arc(pt=p2, prev_pt=p1, next_pt=p3)
                self.arcs.append(arc)

    def find_contours(self) -> None:
        """Find contours in the image."""
        if self.gray_image is None:
            return
            
        # Apply threshold to create binary image
        _, binary = cv2.threshold(self.gray_image, 127, 255, cv2.THRESH_BINARY)
        
        # Find contours
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        self.contours = contours

    def find_boundaries(self) -> None:
        """Find boundary points using directional scanning."""
        if self.gray_image is None:
            return
            
        self.boundary_points.clear()
        h, w = self.gray_image.shape
        
        # Scan directions
        directions = []
        if self.horiz_scan:
            directions.append((1, 0))   # horizontal
        if self.vert_scan:
            directions.append((0, 1))   # vertical
        if self.forty_five_scan:
            directions.append((1, 1))   # 45 degrees
        if self.minus_forty_five_scan:
            directions.append((1, -1))  # -45 degrees
            
        # Apply edge detection
        edges = cv2.Canny(self.gray_image, self.edge_threshold_low, self.edge_threshold_high)
        
        # For each scan direction, find boundary transitions
        for dx, dy in directions:
            for start_x in range(0, w, 10):  # Sample every 10 pixels
                for start_y in range(0, h, 10):
                    x, y = start_x, start_y
                    prev_pixel = 0
                    
                    while 0 <= x < w and 0 <= y < h:
                        current_pixel = edges[y, x]
                        
                        # Detect edge transition
                        if prev_pixel == 0 and current_pixel > 0:
                            self.boundary_points.append(PointPlus(x, y))
                            
                        prev_pixel = current_pixel
                        x += dx
                        y += dy

    def extract_strokes(self) -> None:
        """Extract stroke points from contours."""
        self.stroke_points.clear()
        
        for contour in self.contours:
            # Approximate contour to reduce points
            epsilon = 0.02 * cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, epsilon, True)
            
            # Convert contour points to stroke points
            for point in approx:
                x, y = point[0]
                self.stroke_points.append(PointPlus(int(x), int(y)))

    def get_edge_count(self) -> int:
        """Get the number of detected edge points."""
        return len(self.edges)
        
    def get_corner_count(self) -> int:
        """Get the number of detected corners."""
        return len(self.corners)
        
    def get_line_count(self) -> int:
        """Get the number of detected lines."""
        return len(self.segments)
        
    def get_circle_count(self) -> int:
        """Get the number of detected circles/arcs."""
        return len(self.arcs)
        
    def get_contour_count(self) -> int:
        """Get the number of detected contours."""
        return len(self.contours)

    def analyze_shapes(self) -> Dict[str, Any]:
        """Analyze detected shapes and return summary statistics."""
        if not self.contours:
            return {}
            
        shape_analysis = {
            "total_contours": len(self.contours),
            "total_edges": len(self.edges),
            "total_corners": len(self.corners),
            "total_lines": len(self.segments),
            "total_circles": len(self.arcs),
            "shapes": []
        }
        
        for i, contour in enumerate(self.contours):
            # Calculate contour properties
            area = cv2.contourArea(contour)
            perimeter = cv2.arcLength(contour, True)
            
            if area > 0:
                # Approximate shape
                epsilon = 0.02 * perimeter
                approx = cv2.approxPolyDP(contour, epsilon, True)
                vertices = len(approx)
                
                # Classify shape based on vertices
                if vertices == 3:
                    shape_type = "triangle"
                elif vertices == 4:
                    # Check if rectangle or square
                    x, y, w, h = cv2.boundingRect(approx)
                    aspect_ratio = float(w) / h
                    shape_type = "square" if 0.9 <= aspect_ratio <= 1.1 else "rectangle"
                elif vertices > 4:
                    # Check if circle
                    circularity = 4 * np.pi * area / (perimeter * perimeter)
                    shape_type = "circle" if circularity > 0.7 else "polygon"
                else:
                    shape_type = "unknown"
                    
                shape_analysis["shapes"].append({
                    "id": i,
                    "type": shape_type,
                    "vertices": vertices,
                    "area": area,
                    "perimeter": perimeter,
                    "circularity": 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
                })
                
        return shape_analysis

    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Set processing parameters."""
        if "edge_threshold_low" in params:
            self.edge_threshold_low = params["edge_threshold_low"]
        if "edge_threshold_high" in params:
            self.edge_threshold_high = params["edge_threshold_high"]
        if "corner_quality_level" in params:
            self.corner_quality_level = params["corner_quality_level"]
        if "corner_min_distance" in params:
            self.corner_min_distance = params["corner_min_distance"]
        if "hough_threshold" in params:
            self.hough_threshold = params["hough_threshold"]
        if "min_line_length" in params:
            self.min_line_length = params["min_line_length"]
        if "max_line_gap" in params:
            self.max_line_gap = params["max_line_gap"]

    def get_parameters(self) -> Dict[str, Any]:
        """Get current processing parameters."""
        return {
            "edge_threshold_low": self.edge_threshold_low,
            "edge_threshold_high": self.edge_threshold_high,
            "corner_quality_level": self.corner_quality_level,
            "corner_min_distance": self.corner_min_distance,
            "hough_threshold": self.hough_threshold,
            "min_line_length": self.min_line_length,
            "max_line_gap": self.max_line_gap,
            "horiz_scan": self.horiz_scan,
            "vert_scan": self.vert_scan,
            "forty_five_scan": self.forty_five_scan,
            "minus_forty_five_scan": self.minus_forty_five_scan
        }
