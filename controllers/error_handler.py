import logging
import traceback
from datetime import datetime, timedelta
import pytz
from typing import Dict, Optional, Any
import json
import os
from dataclasses import dataclass, asdict
from enum import Enum
import uuid

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('error_tracking.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ErrorSeverity(Enum):
    """Error severity levels"""
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"

class ErrorCategory(Enum):
    """Categories of errors"""
    DATA_FETCH = "DATA_FETCH"
    DATA_QUALITY = "DATA_QUALITY"
    MODEL = "MODEL"
    API = "API"
    DATABASE = "DATABASE"
    SYSTEM = "SYSTEM"

@dataclass
class ErrorContext:
    """Context information for errors"""
    timestamp: str
    error_type: str
    error_message: str
    stack_trace: str
    severity: ErrorSeverity
    category: ErrorCategory
    component: str
    additional_info: Dict[str, Any]

class ErrorTracker:
    """Centralized error tracking and handling"""
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ErrorTracker, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self.errors = {}
            self._initialized = True
        
    def track_error(
        self,
        error: Exception,
        severity: ErrorSeverity,
        category: ErrorCategory,
        source: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Track an error with detailed information
        Returns: error_id for reference
        """
        error_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()
        
        error_info = {
            'error_id': error_id,
            'timestamp': timestamp,
            'error_type': type(error).__name__,
            'error_message': str(error),
            'severity': severity.value,
            'category': category.value,
            'source': source,
            'stack_trace': traceback.format_exc(),
            'metadata': metadata or {}
        }
        
        # Store error
        self.errors[error_id] = error_info
        
        # Log error
        log_message = (
            f"Error tracked - ID: {error_id}\n"
            f"Type: {error_info['error_type']}\n"
            f"Message: {error_info['error_message']}\n"
            f"Severity: {severity.value}\n"
            f"Category: {category.value}\n"
            f"Source: {source}"
        )
        
        if metadata:
            log_message += f"\nMetadata: {json.dumps(metadata, indent=2)}"
        
        if severity in (ErrorSeverity.ERROR, ErrorSeverity.CRITICAL):
            logger.error(log_message)
        elif severity == ErrorSeverity.WARNING:
            logger.warning(log_message)
        else:
            logger.info(log_message)
        
        return error_id
    
    def get_error(self, error_id: str) -> Optional[Dict]:
        """Retrieve error information by ID"""
        return self.errors.get(error_id)
    
    def get_errors_by_category(self, category: ErrorCategory) -> Dict[str, Dict]:
        """Get all errors of a specific category"""
        return {
            error_id: error_info
            for error_id, error_info in self.errors.items()
            if error_info['category'] == category.value
        }
    
    def get_errors_by_severity(self, severity: ErrorSeverity) -> Dict[str, Dict]:
        """Get all errors of a specific severity"""
        return {
            error_id: error_info
            for error_id, error_info in self.errors.items()
            if error_info['severity'] == severity.value
        }
    
    def clear_errors(self):
        """Clear all tracked errors"""
        self.errors.clear()

# Initialize global error tracker instance
error_tracker = ErrorTracker()

class DataValidationError(Exception):
    """Custom exception for data validation errors"""
    pass

class ModelError(Exception):
    """Custom exception for model-related errors"""
    pass

class APIError(Exception):
    """Custom exception for API-related errors"""
    pass

def handle_api_error(error: Exception, source: str) -> Dict[str, Any]:
    """Handle API errors and return appropriate response"""
    error_id = error_tracker.track_error(
        error=error,
        severity=ErrorSeverity.ERROR,
        category=ErrorCategory.API,
        source=source
    )
    
    return {
        'error': True,
        'error_id': error_id,
        'message': str(error),
        'type': type(error).__name__
    }

def rate_limit(source: str):
    """Decorator for rate limiting API calls"""
    from functools import wraps
    import time
    from collections import defaultdict
    
    # Store last call timestamps
    last_calls = defaultdict(lambda: 0)
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_time = time.time()
            elapsed = current_time - last_calls[source]
            
            if elapsed < 1.0:  # Minimum 1 second between calls
                time.sleep(1.0 - elapsed)
            
            try:
                result = func(*args, **kwargs)
                last_calls[source] = time.time()
                return result
            except Exception as e:
                raise APIError(f"Rate limited API call failed: {str(e)}")
        
        return wrapper
    return decorator

def get_recent_errors(hours: int = 24) -> Dict:
    """Get errors from the last N hours"""
    try:
        cutoff = datetime.now(pytz.UTC) - timedelta(hours=hours)
        recent_errors = {}
        
        for category, errors in error_tracker.errors.items():
            recent = {
                error_id: details
                for error_id, details in errors.items()
                if datetime.fromisoformat(details['timestamp']) > cutoff
            }
            if recent:
                recent_errors[category] = recent
                
        return recent_errors
        
    except Exception as e:
        logger.error(f"Error retrieving recent errors: {str(e)}")
        return {}

def analyze_error_patterns() -> Dict:
    """Analyze patterns in recent errors"""
    try:
        recent_errors = get_recent_errors(24)
        analysis = {
            'total_errors': 0,
            'errors_by_category': {},
            'errors_by_severity': {},
            'most_common_components': {},
            'error_trend': {}
        }
        
        for category, errors in recent_errors.items():
            # Count by category
            analysis['errors_by_category'][category] = len(errors)
            analysis['total_errors'] += len(errors)
            
            # Analyze each error
            for error in errors.values():
                # Count by severity
                severity = error['severity']
                analysis['errors_by_severity'][severity] = \
                    analysis['errors_by_severity'].get(severity, 0) + 1
                
                # Count by component
                component = error['component']
                analysis['most_common_components'][component] = \
                    analysis['most_common_components'].get(component, 0) + 1
                
                # Track hourly trend
                hour = datetime.fromisoformat(error['timestamp']).strftime('%Y-%m-%d %H:00')
                analysis['error_trend'][hour] = \
                    analysis['error_trend'].get(hour, 0) + 1
        
        return analysis
        
    except Exception as e:
        logger.error(f"Error analyzing error patterns: {str(e)}")
        return {}

# Ensure error_tracker is properly exported
__all__ = ['error_tracker', 'ErrorSeverity', 'ErrorCategory', 'ErrorTracker',
           'DataValidationError', 'ModelError', 'APIError', 'handle_api_error',
           'rate_limit', 'get_recent_errors', 'analyze_error_patterns'] 