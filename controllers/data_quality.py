from dataclasses import dataclass
from typing import Dict

@dataclass
class DataQualityMetrics:
    """Metrics for data quality assessment"""
    completeness: float = 0.0  # Percentage of non-null values
    accuracy: float = 0.0      # Percentage of values within expected range
    consistency: float = 0.0   # Percentage of values following expected patterns
    timeliness: float = 0.0    # Percentage of up-to-date values
    volume_quality: float = 0.0 # Quality of volume data
    price_quality: float = 0.0  # Quality of price data
    
    def __post_init__(self):
        """Validate metrics after initialization"""
        for field, value in self.__dict__.items():
            if not 0 <= value <= 1:
                raise ValueError(f"Invalid {field} value: {value}. Must be between 0 and 1.")
                
    @property
    def overall_quality(self) -> float:
        """Calculate overall data quality score"""
        weights = {
            'completeness': 0.2,
            'accuracy': 0.3,
            'consistency': 0.2,
            'timeliness': 0.1,
            'volume_quality': 0.1,
            'price_quality': 0.1
        }
        return sum(getattr(self, metric) * weight for metric, weight in weights.items())
        
    def to_dict(self) -> Dict[str, float]:
        """Convert metrics to dictionary"""
        return {
            'completeness': self.completeness,
            'accuracy': self.accuracy,
            'consistency': self.consistency,
            'timeliness': self.timeliness,
            'volume_quality': self.volume_quality,
            'price_quality': self.price_quality,
            'overall_quality': self.overall_quality
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, float]) -> 'DataQualityMetrics':
        """Create metrics from dictionary"""
        return cls(
            completeness=data.get('completeness', 0.0),
            accuracy=data.get('accuracy', 0.0),
            consistency=data.get('consistency', 0.0),
            timeliness=data.get('timeliness', 0.0),
            volume_quality=data.get('volume_quality', 0.0),
            price_quality=data.get('price_quality', 0.0)
        ) 