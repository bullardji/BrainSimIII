"""Enhanced mental model module for spatial and conceptual reasoning.

This module creates and maintains mental representations of spatial layouts,
object relationships, and conceptual structures based on sensory input.
"""
from __future__ import annotations
from typing import Iterable, List, Dict, Optional, Any, Tuple
from datetime import datetime, timedelta
import math

from .module_base import ModuleBase
from vision.point_plus import PointPlus


class SpatialRelationship:
    """Represents a spatial relationship between objects."""
    
    def __init__(self, obj1: str, obj2: str, relation_type: str, confidence: float = 1.0):
        self.object1 = obj1
        self.object2 = obj2
        self.relation_type = relation_type  # 'above', 'below', 'left', 'right', 'near', 'far'
        self.confidence = confidence
        self.created_time = datetime.now()
        
    def __str__(self) -> str:
        return f"{self.object1} {self.relation_type} {self.object2} (conf: {self.confidence:.2f})"


class MentalModelObject:
    """Represents an object in the mental model with properties and relationships."""
    
    def __init__(self, name: str, object_type: str = "unknown"):
        self.name = name
        self.object_type = object_type
        self.position: Optional[PointPlus] = None
        self.properties: Dict[str, Any] = {}
        self.relationships: List[SpatialRelationship] = []
        self.confidence = 1.0
        self.last_updated = datetime.now()
        
    def add_property(self, key: str, value: Any) -> None:
        """Add or update a property."""
        self.properties[key] = value
        self.last_updated = datetime.now()
        
    def add_relationship(self, relationship: SpatialRelationship) -> None:
        """Add a spatial relationship."""
        self.relationships.append(relationship)
        self.last_updated = datetime.now()


class ModuleMentalModel(ModuleBase):
    """Enhanced mental model for spatial and conceptual reasoning.
    
    Maintains internal representations of:
    - Spatial layouts and object relationships
    - Shape classifications and properties
    - Temporal sequences and changes
    - Abstract conceptual structures
    """

    def __init__(self, label: Optional[str] = None):
        super().__init__(label)
        
        # Enhanced mental model storage
        self.shapes: List[Dict] = []  # Legacy shape storage
        self.objects: Dict[str, MentalModelObject] = {}  # Enhanced object tracking
        self.spatial_relationships: List[SpatialRelationship] = []
        
        # Processing parameters
        self.spatial_threshold = 50.0  # Distance threshold for "near" relationships
        self.confidence_decay = 0.95   # Confidence decay factor over time
        self.max_objects = 100         # Maximum objects to track
        
        # Temporal tracking
        self.last_scan_time = datetime.now()
        self.processing_interval = timedelta(seconds=1.0)
        
        # Statistics
        self.stats = {
            'objects_processed': 0,
            'relationships_created': 0,
            'shapes_classified': 0
        }

    def initialize(self) -> None:
        """Initialize the mental model module."""
        if self.the_uks:
            # Create basic conceptual hierarchy
            self.the_uks.get_or_add_thing("Sense", "Thing")
            self.the_uks.get_or_add_thing("Visual", "Sense")
            self.the_uks.get_or_add_thing("Spatial", "Visual")
            self.the_uks.get_or_add_thing("Shape", "Visual")
            self.the_uks.get_or_add_thing("Object", "Visual")
            
            # Create spatial relationship concepts
            spatial_concepts = ['above', 'below', 'left', 'right', 'near', 'far', 'inside', 'contains']
            for concept in spatial_concepts:
                self.the_uks.get_or_add_thing(concept, "Spatial")

    def fire(self) -> None:
        """Main processing cycle for mental model updates."""
        current_time = datetime.now()
        
        # Check if enough time has passed since last processing
        if current_time - self.last_scan_time < self.processing_interval:
            return
            
        self.last_scan_time = current_time
        
        # Process sensory input and update mental model
        self._update_from_sensory_input()
        
        # Update spatial relationships
        self._update_spatial_relationships()
        
        # Perform reasoning and inference
        self._perform_spatial_reasoning()
        
        # Decay old information
        self._decay_old_information()
        
        # Update UKS with current state
        self._update_uks_representations()
    
    def _update_from_sensory_input(self) -> None:
        """Update mental model from current sensory input."""
        if not self.the_uks:
            return
            
        try:
            # Process corners from vision system
            corners_thing = self.the_uks.get_thing("corner")
            if corners_thing and hasattr(corners_thing, 'children'):
                for corner in corners_thing.children:
                    if hasattr(corner, 'lastFiredTime') and corner.lastFiredTime > self.last_scan_time:
                        self._process_corner(corner)
            
            # Process detected shapes
            current_shape_thing = self.the_uks.get_thing("currentShape")
            if current_shape_thing and hasattr(current_shape_thing, 'children'):
                for shape in current_shape_thing.children:
                    self._process_shape(shape)
                    
        except Exception:
            # Handle UKS access errors gracefully
            pass
    
    def _process_corner(self, corner) -> None:
        """Process a corner from the vision system."""
        corner_id = f"corner_{id(corner)}"
        
        if corner_id not in self.objects:
            corner_obj = MentalModelObject(corner_id, "corner")
            self.objects[corner_id] = corner_obj
        else:
            corner_obj = self.objects[corner_id]
            
        # Update properties
        if hasattr(corner, 'position'):
            corner_obj.position = corner.position
        if hasattr(corner, 'angle'):
            corner_obj.add_property('angle', corner.angle)
            
        self.stats['objects_processed'] += 1
    
    def _process_shape(self, shape) -> None:
        """Process a shape from the vision system."""
        shape_id = f"shape_{id(shape)}"
        
        if shape_id not in self.objects:
            shape_obj = MentalModelObject(shape_id, "shape")
            self.objects[shape_id] = shape_obj
        else:
            shape_obj = self.objects[shape_id]
            
        # Update shape properties
        if hasattr(shape, 'area'):
            shape_obj.add_property('area', shape.area)
        if hasattr(shape, 'perimeter'):
            shape_obj.add_property('perimeter', shape.perimeter)
        if hasattr(shape, 'center'):
            shape_obj.position = PointPlus(shape.center.x, shape.center.y)
            
        # Classify shape type
        shape_type = self._classify_shape(shape_obj)
        if shape_type:
            shape_obj.add_property('shape_type', shape_type)
            
        self.stats['shapes_classified'] += 1
    
    def _classify_shape(self, shape_obj: MentalModelObject) -> Optional[str]:
        """Classify a shape based on its properties."""
        area = shape_obj.properties.get('area', 0)
        perimeter = shape_obj.properties.get('perimeter', 0)
        
        if area <= 0 or perimeter <= 0:
            return None
            
        # Calculate circularity
        circularity = 4 * math.pi * area / (perimeter * perimeter)
        
        if circularity > 0.8:
            return "circle"
        elif circularity > 0.6:
            return "ellipse"
        elif area / (perimeter / 4) ** 2 > 0.8:  # Rough square test
            return "square"
        else:
            return "polygon"
    
    def _update_spatial_relationships(self) -> None:
        """Update spatial relationships between objects."""
        objects_list = list(self.objects.values())
        
        for i, obj1 in enumerate(objects_list):
            for obj2 in objects_list[i+1:]:
                if obj1.position and obj2.position:
                    relationship = self._determine_spatial_relationship(obj1, obj2)
                    if relationship:
                        self.spatial_relationships.append(relationship)
                        obj1.add_relationship(relationship)
                        self.stats['relationships_created'] += 1
    
    def _determine_spatial_relationship(self, obj1: MentalModelObject, obj2: MentalModelObject) -> Optional[SpatialRelationship]:
        """Determine spatial relationship between two objects."""
        if not (obj1.position and obj2.position):
            return None
            
        dx = obj2.position.x - obj1.position.x
        dy = obj2.position.y - obj1.position.y
        distance = math.sqrt(dx*dx + dy*dy)
        
        # Determine relationship type
        if distance < self.spatial_threshold:
            relation_type = "near"
        else:
            # Determine directional relationship
            if abs(dx) > abs(dy):
                relation_type = "right" if dx > 0 else "left"
            else:
                relation_type = "below" if dy > 0 else "above"
                
        return SpatialRelationship(obj1.name, obj2.name, relation_type, 1.0)
    
    def _perform_spatial_reasoning(self) -> None:
        """Perform spatial reasoning and inference."""
        # Simple transitive reasoning: if A left-of B and B left-of C, then A left-of C
        for obj_name in self.objects:
            left_objects = self.query_spatial_relations(obj_name, "left")
            for left_obj in left_objects:
                far_left_objects = self.query_spatial_relations(left_obj, "left")
                for far_left_obj in far_left_objects:
                    # Add inferred relationship with lower confidence
                    inferred_rel = SpatialRelationship(obj_name, far_left_obj, "left", 0.7)
                    self.spatial_relationships.append(inferred_rel)
    
    def _decay_old_information(self) -> None:
        """Apply confidence decay to old information."""
        cutoff_time = datetime.now() - timedelta(minutes=5)
        
        # Decay object confidence
        for obj in self.objects.values():
            if obj.last_updated < cutoff_time:
                obj.confidence *= self.confidence_decay
                
        # Remove very low confidence objects
        to_remove = [name for name, obj in self.objects.items() if obj.confidence < 0.1]
        for name in to_remove:
            del self.objects[name]
            
        # Limit total object count
        if len(self.objects) > self.max_objects:
            # Remove oldest objects
            sorted_objects = sorted(self.objects.items(), key=lambda x: x[1].last_updated)
            for name, _ in sorted_objects[:len(self.objects) - self.max_objects]:
                del self.objects[name]
    
    def _update_uks_representations(self) -> None:
        """Update UKS with current mental model state."""
        if not self.the_uks:
            return
            
        try:
            # Add objects to UKS
            for obj in self.objects.values():
                obj_thing = self.the_uks.get_or_add_thing(obj.name, obj.object_type)
                
                # Add properties as relationships
                for prop_name, prop_value in obj.properties.items():
                    prop_thing = self.the_uks.get_or_add_thing(str(prop_value), prop_name)
                    self.the_uks.add_relationship(obj_thing, prop_name, prop_thing)
                    
            # Add spatial relationships
            for rel in self.spatial_relationships[-10:]:  # Only recent relationships
                obj1_thing = self.the_uks.get_thing(rel.object1)
                obj2_thing = self.the_uks.get_thing(rel.object2)
                if obj1_thing and obj2_thing:
                    self.the_uks.add_relationship(obj1_thing, rel.relation_type, obj2_thing)
                    
        except Exception:
            # Handle UKS errors gracefully
            pass
    
    def query_spatial_relations(self, obj_name: str, relation_type: str) -> List[str]:
        """Query objects that have a specific spatial relationship with the given object."""
        results = []
        
        # Check spatial relationships
        for rel in self.spatial_relationships:
            if rel.object1 == obj_name and rel.relation_type == relation_type:
                results.append(rel.object2)
            elif rel.object2 == obj_name and self._inverse_relation(rel.relation_type) == relation_type:
                results.append(rel.object1)
                
        return list(set(results))  # Remove duplicates
    
    def _inverse_relation(self, relation: str) -> str:
        """Get the inverse of a spatial relationship."""
        inverse_map = {
            'above': 'below', 'below': 'above',
            'left': 'right', 'right': 'left',
            'near': 'near', 'far': 'far',
            'inside': 'contains', 'contains': 'inside'
        }
        return inverse_map.get(relation, relation)
    
    # Legacy methods for compatibility
    def ingest_shapes(self, shapes: Iterable[Dict]) -> None:
        """Legacy method: ingest shapes (maintained for compatibility)."""
        self.shapes.extend(shapes)
        
        # Convert to new object format
        for i, shape in enumerate(shapes):
            shape_id = f"legacy_shape_{len(self.objects) + i}"
            shape_obj = MentalModelObject(shape_id, "shape")
            
            for key, value in shape.items():
                shape_obj.add_property(key, value)
                
            self.objects[shape_id] = shape_obj

    def get_shape_count(self, shape_type: str | None = None) -> int:
        """Get count of shapes, optionally filtered by type."""
        if shape_type is None:
            return len(self.shapes) + len([obj for obj in self.objects.values() if obj.object_type == "shape"])
        
        legacy_count = sum(1 for s in self.shapes if s.get("type") == shape_type)
        object_count = sum(1 for obj in self.objects.values() 
                          if obj.object_type == "shape" and obj.properties.get("shape_type") == shape_type)
        
        return legacy_count + object_count
    
    def get_mental_model_summary(self) -> Dict[str, Any]:
        """Get a comprehensive summary of the mental model state."""
        return {
            'total_objects': len(self.objects),
            'object_types': list(set(obj.object_type for obj in self.objects.values())),
            'spatial_relationships': len(self.spatial_relationships),
            'legacy_shapes': len(self.shapes),
            'processing_stats': self.stats.copy(),
            'parameters': {
                'spatial_threshold': self.spatial_threshold,
                'confidence_decay': self.confidence_decay,
                'max_objects': self.max_objects
            }
        }
    
    def set_parameters(self, params: Dict[str, Any]) -> None:
        """Set processing parameters."""
        if 'spatial_threshold' in params:
            self.spatial_threshold = params['spatial_threshold']
        if 'confidence_decay' in params:
            self.confidence_decay = params['confidence_decay']
        if 'max_objects' in params:
            self.max_objects = params['max_objects']
    
    def get_parameters(self) -> Dict[str, Any]:
        """Get current parameters."""
        return {
            'spatial_threshold': self.spatial_threshold,
            'confidence_decay': self.confidence_decay,
            'max_objects': self.max_objects,
            'processing_interval_ms': self.processing_interval.total_seconds() * 1000
        }
