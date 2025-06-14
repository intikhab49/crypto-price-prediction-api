import os
import shutil
import json
from datetime import datetime
import pytz
import logging
from typing import Dict, Optional
import torch
import hashlib

logger = logging.getLogger(__name__)

class ModelManager:
    """Manages model versioning, backups, and performance tracking"""
    
    def __init__(self, base_path: str = "models"):
        self.base_path = base_path
        self.version_file = os.path.join(base_path, "versions.json")
        self.backup_dir = os.path.join(base_path, "backups")
        self.metrics_file = os.path.join(base_path, "metrics.json")
        
        # Create necessary directories
        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(self.backup_dir, exist_ok=True)
        
        # Initialize or load version tracking
        self.versions = self._load_versions()
        self.metrics = self._load_metrics()
        
    def _load_versions(self) -> Dict:
        """Load version information from file"""
        if os.path.exists(self.version_file):
            try:
                with open(self.version_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading version file: {str(e)}")
                return {}
        return {}
        
    def _save_versions(self):
        """Save version information to file"""
        try:
            with open(self.version_file, 'w') as f:
                json.dump(self.versions, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving version file: {str(e)}")
            
    def _load_metrics(self) -> Dict:
        """Load metrics history from file"""
        if os.path.exists(self.metrics_file):
            try:
                with open(self.metrics_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading metrics file: {str(e)}")
                return {}
        return {}
        
    def _save_metrics(self):
        """Save metrics history to file"""
        try:
            with open(self.metrics_file, 'w') as f:
                json.dump(self.metrics, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving metrics file: {str(e)}")
            
    def _calculate_model_hash(self, model_path: str) -> str:
        """Calculate SHA-256 hash of model file"""
        try:
            with open(model_path, 'rb') as f:
                return hashlib.sha256(f.read()).hexdigest()
        except Exception as e:
            logger.error(f"Error calculating model hash: {str(e)}")
            return ""
            
    def save_model(self, model: torch.nn.Module, symbol: str, timeframe: str, 
                  metrics: Dict, model_path: str) -> str:
        """Save model with version control"""
        try:
            # Generate version info
            version = {
                'timestamp': datetime.now(pytz.UTC).isoformat(),
                'metrics': metrics,
                'hash': None
            }
            
            # Save model
            torch.save({
                'model_state_dict': model.state_dict(),
                'version_info': version,
                'metrics': metrics
            }, model_path)
            
            # Calculate hash
            version['hash'] = self._calculate_model_hash(model_path)
            
            # Update version tracking
            model_key = f"{symbol}_{timeframe}"
            if model_key not in self.versions:
                self.versions[model_key] = []
            self.versions[model_key].append(version)
            
            # Keep only last 5 versions
            if len(self.versions[model_key]) > 5:
                self.versions[model_key] = self.versions[model_key][-5:]
                
            self._save_versions()
            
            # Create backup
            backup_path = os.path.join(
                self.backup_dir, 
                f"{symbol}_{timeframe}_{version['timestamp']}.pth"
            )
            shutil.copy2(model_path, backup_path)
            
            # Update metrics history
            if model_key not in self.metrics:
                self.metrics[model_key] = []
            self.metrics[model_key].append({
                'timestamp': version['timestamp'],
                'metrics': metrics
            })
            self._save_metrics()
            
            return version['hash']
            
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            raise
            
    def load_model(self, symbol: str, timeframe: str, version_hash: Optional[str] = None) -> str:
        """Load specific model version"""
        try:
            model_key = f"{symbol}_{timeframe}"
            model_path = os.path.join(self.base_path, f"{model_key}.pth")
            
            if version_hash:
                # Look for specific version in backups
                versions = self.versions.get(model_key, [])
                version_info = next(
                    (v for v in versions if v['hash'] == version_hash),
                    None
                )
                
                if version_info:
                    backup_path = os.path.join(
                        self.backup_dir,
                        f"{symbol}_{timeframe}_{version_info['timestamp']}.pth"
                    )
                    if os.path.exists(backup_path):
                        return backup_path
                        
                logger.warning(f"Version {version_hash} not found, using latest")
                
            return model_path
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            raise
            
    def get_model_history(self, symbol: str, timeframe: str) -> Dict:
        """Get model version history and performance metrics"""
        try:
            model_key = f"{symbol}_{timeframe}"
            return {
                'versions': self.versions.get(model_key, []),
                'metrics_history': self.metrics.get(model_key, [])
            }
        except Exception as e:
            logger.error(f"Error getting model history: {str(e)}")
            return {'versions': [], 'metrics_history': []}
            
    def should_retrain(self, symbol: str, timeframe: str, current_metrics: Dict) -> bool:
        """Determine if model should be retrained based on performance degradation"""
        try:
            model_key = f"{symbol}_{timeframe}"
            history = self.metrics.get(model_key, [])
            
            if not history:
                return True
                
            # Get average metrics from last 3 versions
            recent_metrics = history[-3:]
            avg_metrics = {
                'mae': sum(m['metrics']['mae'] for m in recent_metrics) / len(recent_metrics),
                'rmse': sum(m['metrics']['rmse'] for m in recent_metrics) / len(recent_metrics),
                'r2': sum(m['metrics']['r2'] for m in recent_metrics) / len(recent_metrics)
            }
            
            # Check for significant degradation (20% worse than average)
            degraded = (
                current_metrics['mae'] > avg_metrics['mae'] * 1.2 or
                current_metrics['rmse'] > avg_metrics['rmse'] * 1.2 or
                current_metrics['r2'] < avg_metrics['r2'] * 0.8
            )
            
            if degraded:
                logger.warning(f"Model performance degraded for {symbol}_{timeframe}")
                return True
                
            return False
            
        except Exception as e:
            logger.error(f"Error checking retrain condition: {str(e)}")
            return True  # Retrain on error to be safe 