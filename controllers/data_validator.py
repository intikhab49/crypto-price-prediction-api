import logging
import time
from datetime import datetime, timedelta
import pytz
import pandas as pd
import numpy as np
from typing import Dict, Optional, List, Tuple
from dataclasses import dataclass
from collections import defaultdict
import threading
from functools import wraps
from config import settings, FEATURE_LIST, TIMEFRAME_MAP
from controllers.data_quality import DataQualityMetrics

logger = logging.getLogger(__name__)

class APIRateLimiter:
    """Rate limiter for API calls"""
    
    def __init__(self):
        self.rate_limits = {
            'coingecko': {'calls': 30, 'period': 60},  # Changed from 50 to 30 calls per minute
            'yfinance': {'calls': 2000, 'period': 3600},  # 2000 calls per hour
            'default': {'calls': 100, 'period': 60}  # Default limit
        }
        self.call_history = defaultdict(list)
        self.locks = defaultdict(threading.Lock)
        
    def check_rate_limit(self, api_name: str) -> Tuple[bool, float]:
        """Check if we're within rate limits"""
        with self.locks[api_name]:
            now = time.time()
            limit = self.rate_limits.get(api_name, self.rate_limits['default'])
            
            # Remove old calls
            self.call_history[api_name] = [
                t for t in self.call_history[api_name]
                if now - t < limit['period']
            ]
            
            # Check if we're within limits
            if len(self.call_history[api_name]) >= limit['calls']:
                oldest_call = self.call_history[api_name][0]
                wait_time = limit['period'] - (now - oldest_call)
                return False, max(0, wait_time)
                
            # Add new call
            self.call_history[api_name].append(now)
            return True, 0
            
    def wait_if_needed(self, api_name: str):
        """Wait if we're over rate limit"""
        while True:
            can_proceed, wait_time = self.check_rate_limit(api_name)
            if can_proceed:
                break
            logger.warning(f"Rate limit reached for {api_name}, waiting {wait_time:.1f}s")
            time.sleep(wait_time)

def rate_limit(api_name: Optional[str] = None, max_per_minute: int = settings.MAX_REQUESTS_PER_MINUTE):
    """Rate limiting decorator"""
    limiter_instance = APIRateLimiter()

    def decorator(func):
        last_called_generic = {} # For generic rate limiting when api_name is None

        # Calculate min_interval only for the generic case
        min_interval_generic = 60.0 / max_per_minute if max_per_minute > 0 else float('inf')

        @wraps(func)
        def wrapper(*args, **kwargs):
            if api_name:
                # Use APIRateLimiter for specific API
                limiter_instance.wait_if_needed(api_name)
                # The APIRateLimiter's check_rate_limit and wait_if_needed already record the call
                # So no need to update last_called for API-specific limits here
            else:
                # Use provided max_per_minute for generic rate limiting
                now = time.time()
                if func.__name__ in last_called_generic:
                    time_since_last = now - last_called_generic[func.__name__]
                    if time_since_last < min_interval_generic:
                        sleep_time = min_interval_generic - time_since_last
                        logger.debug(f"Generic rate limit for {func.__name__}: sleeping for {sleep_time:.2f}s")
                        time.sleep(sleep_time)
                last_called_generic[func.__name__] = time.time()
            
            result = func(*args, **kwargs)
            return result
        return wrapper
    return decorator

class DataValidator:
    """Validates cryptocurrency data quality and consistency"""
    
    def __init__(self, timeframe: str):
        self.timeframe = timeframe
        self.required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
        self.feature_weights = FEATURE_LIST  # Use the feature weights from config
        self.time_windows = {
            '1h': {'min_points': 500, 'gap_threshold': timedelta(hours=2)},
            '4h': {'min_points': 250, 'gap_threshold': timedelta(hours=8)},
            '24h': {'min_points': 200, 'gap_threshold': timedelta(days=2)}
        }
        
    def _validate_data_quality(self, df: pd.DataFrame) -> Tuple[bool, Dict]:
        """Validate data quality and calculate metrics"""
        try:
            metrics = {
                'original_rows': len(df),
                'missing_values': {},
                'outliers': {},
                'feature_stats': {},
                'gaps': [],
                'quality_scores': {}
            }
            
            # 1. Check minimum required samples with reduced requirements for demo API
            min_samples = TIMEFRAME_MAP[self.timeframe].get('min_samples', settings.MIN_DATA_POINTS)
            if self.timeframe == "1h":
                min_samples = min(min_samples, 500)  # Reduced requirement for hourly data
            elif self.timeframe == "4h":
                min_samples = min(min_samples, 250)  # Reduced requirement for 4h data
            elif self.timeframe == "24h":
                min_samples = min(min_samples, 200)  # Reduced requirement for daily data
            
            if len(df) < min_samples:
                logger.error(f"Insufficient data points: {len(df)} < {min_samples}")
                return False, metrics
            
            # 2. Check for time series gaps with more lenient criteria
            time_diffs = df.index.to_series().diff()
            expected_diff = pd.Timedelta(minutes={
                "1h": 60, "4h": 240, "24h": 1440
            }[self.timeframe])
            
            gaps = time_diffs[time_diffs > expected_diff * 3.0]  # Even more lenient gap detection
            if not gaps.empty:
                metrics['gaps'] = [
                    {'start': str(idx), 'duration_minutes': diff.total_seconds() / 60}
                    for idx, diff in gaps.items()
                ]
                # Only fail if there are extremely large gaps
                if any(gap['duration_minutes'] > settings.MAX_GAP_MINUTES * 3 for gap in metrics['gaps']):
                    logger.error(f"Found gaps larger than {settings.MAX_GAP_MINUTES * 3} minutes in the data")
                    return False, metrics
            
            # 3. Check required features and data points with greatly reduced requirements
            min_required = min(settings.MIN_PRICE_POINTS // 2, min_samples)  # Halved the requirement
            price_points = df[['Open', 'High', 'Low', 'Close']].count().min()
            volume_points = df['Volume'].count()
            
            if price_points < min_required:
                logger.error(f"Insufficient price data points: {price_points} < {min_required}")
                return False, metrics
                
            if volume_points < min_required:
                logger.error(f"Insufficient volume data points: {volume_points} < {min_required}")
                return False, metrics
            
            # 4. Calculate missing values metrics with very lenient threshold
            max_missing = settings.MAX_MISSING_PERCENTAGE * 3  # Triple the allowed missing percentage
            for column in df.columns:
                missing_count = df[column].isnull().sum()
                missing_percentage = missing_count / len(df)
                metrics['missing_values'][column] = {
                    'count': int(missing_count),
                    'percentage': float(missing_percentage)
                }
                
                if missing_percentage > max_missing:
                    logger.warning(f"High missing values in {column}: {missing_percentage:.2%}")
                    if column in self.required_columns:  # Only check essential columns
                        return False, metrics
            
            # 5. Calculate outlier metrics with feature-specific thresholds
            for column in df.columns:
                if column in self.required_columns:
                    mean = df[column].mean()
                    std = df[column].std()
                    threshold = settings.OUTLIER_STD_THRESHOLD * std
                    outliers = df[abs(df[column] - mean) > threshold]
                    
                    metrics['outliers'][column] = {
                        'count': len(outliers),
                        'percentage': len(outliers) / len(df),
                        'threshold': float(threshold)
                    }
            
            # 6. Calculate feature statistics with enhanced metrics
            for column in df.columns:
                metrics['feature_stats'][column] = {
                    'mean': float(df[column].mean()),
                    'std': float(df[column].std()),
                    'min': float(df[column].min()),
                    'max': float(df[column].max()),
                    'median': float(df[column].median()),
                    'skew': float(df[column].skew()),
                    'kurtosis': float(df[column].kurtosis()),
                    'importance': float(self.feature_weights.get(column, 0.5))
                }
            
            # 7. Calculate quality scores for each aspect
            quality_scores = {
                'completeness': 1 - df.isnull().mean().mean(),
                'timeliness': 1 - (len(metrics['gaps']) / len(df)) if metrics['gaps'] else 1.0,
                'outliers': 1 - sum(m['percentage'] for m in metrics['outliers'].values()) / len(metrics['outliers']) if metrics['outliers'] else 1.0,
                'consistency': self._calculate_consistency_score(df),
                'accuracy': self._calculate_accuracy_score(df),
                'volume_quality': self._calculate_volume_quality(df),
                'price_quality': self._calculate_price_quality(df)
            }
            
            metrics['quality_scores'] = quality_scores
            return True, metrics
            
        except Exception as e:
            logger.error(f"Error in data validation: {str(e)}")
            return False, metrics
    
    def validate_data(self, df: pd.DataFrame) -> Tuple[bool, Dict, pd.DataFrame]:
        """
        Validate and clean the input data
        Returns: (is_valid, metrics, cleaned_df)
        """
        try:
            # 1. Basic data validation
            if df is None or df.empty:
                raise ValueError("Input data is None or empty")
            
            # 2. Check required columns
            required_base_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
            missing_base_columns = [col for col in required_base_columns if col not in df.columns]
            if missing_base_columns:
                raise ValueError(f"Missing base columns: {missing_base_columns}")
            
            # 3. Clean data
            cleaned_df = df.copy()
            
            # Remove rows with zero volume
            cleaned_df = cleaned_df[cleaned_df['Volume'] > 0]
            
            # Forward fill missing values
            cleaned_df = cleaned_df.ffill()
            
            # Remove duplicate indices
            cleaned_df = cleaned_df[~cleaned_df.index.duplicated(keep='first')]
            
            # Sort by timestamp
            cleaned_df = cleaned_df.sort_index()
            
            # 4. Validate data quality
            is_valid, metrics = self._validate_data_quality(cleaned_df)
            
            return is_valid, metrics, cleaned_df
            
        except Exception as e:
            logger.error(f"Data validation failed: {str(e)}")
            return False, {}, df
    
    def prepare_training_data(self, df: pd.DataFrame) -> Tuple[Dict, pd.DataFrame]:
        """
        Prepare data for training by normalizing and splitting
        Returns: (data_info, prepared_df)
        """
        try:
            data_info = {
                'normalization': {},
                'split_info': {}
            }
            
            # 1. Calculate train/validation/test splits
            total_samples = len(df)
            test_size = int(total_samples * settings.TEST_SPLIT)
            val_size = int(total_samples * settings.VALIDATION_SPLIT)
            train_size = total_samples - test_size - val_size
            
            data_info['split_info'] = {
                'total_samples': total_samples,
                'train_size': train_size,
                'validation_size': val_size,
                'test_size': test_size
            }
            
            # 2. Normalize features
            prepared_df = df.copy()
            for column in df.columns:
                if column in self.required_columns:
                    # Store normalization parameters
                    mean = df[column].mean()
                    std = df[column].std()
                    data_info['normalization'][column] = {
                        'mean': float(mean),
                        'std': float(std)
                    }
                    
                    # Normalize the data
                    if std > 0:
                        prepared_df[column] = (df[column] - mean) / std
                    
            return data_info, prepared_df
            
        except Exception as e:
            logger.error(f"Data preparation failed: {str(e)}")
            return {}, df

    def validate_data_freshness(self, data: pd.DataFrame) -> bool:
        """Check if data is fresh enough"""
        if data.empty:
            return False
            
        latest_time = pd.to_datetime(data.index[-1])
        if latest_time.tzinfo is None:
            latest_time = latest_time.tz_localize('UTC')
            
        now = datetime.now(pytz.UTC)

        time_window_config = self.time_windows.get(self.timeframe)
        
        # Default to a sensible timedelta if config or key is missing
        actual_max_delay_timedelta = timedelta(days=1) # Default
        
        if time_window_config and isinstance(time_window_config, dict) and 'gap_threshold' in time_window_config:
            if isinstance(time_window_config['gap_threshold'], timedelta):
                actual_max_delay_timedelta = time_window_config['gap_threshold']
            else:
                logger.warning(f"Invalid 'gap_threshold' type for timeframe {self.timeframe} in time_windows. Using default timedelta(days=1).")
        else:
            logger.warning(f"No 'gap_threshold' found for timeframe {self.timeframe} in time_windows. Using default max_delay timedelta(days=1).")
            
        if now - latest_time > actual_max_delay_timedelta * 2: # Now actual_max_delay_timedelta is a timedelta
            logger.warning(f"Data is too old. Latest: {latest_time}, Now: {now}, Max allowed age (2*gap_threshold): {actual_max_delay_timedelta * 2}")
            return False
            
        return True
        
    def validate_data_continuity(self, data: pd.DataFrame) -> bool:
        """Check for gaps in time series"""
        if data.empty:
            return False
            
        time_window_config = self.time_windows.get(self.timeframe)
        
        # Default to a sensible timedelta if config or key is missing
        expected_interval_timedelta = None
        if time_window_config and isinstance(time_window_config, dict) and 'gap_threshold' in time_window_config:
            if isinstance(time_window_config['gap_threshold'], timedelta):
                 # Assuming gap_threshold is related to expected interval, or we need a different config value for expected_interval
                 # For now, let's assume gap_threshold can be used as a base for the expected interval check.
                 # This logic might need refinement if 'gap_threshold' is not the direct 'expected_interval'.
                 # A common approach is expected_interval = TIMEFRAME_MAP[self.timeframe]["interval"] (converted to timedelta)
                expected_interval_timedelta = time_window_config['gap_threshold'] 
            else:
                logger.warning(f"Invalid 'gap_threshold' type for timeframe {self.timeframe} in time_windows. Cannot determine expected interval.")
        else:
            logger.warning(f"No 'gap_threshold' configuration found for timeframe {self.timeframe} in time_windows. Cannot determine expected interval.")

        if not expected_interval_timedelta: # If we couldn't determine it, can't proceed with this check
            logger.warning("Could not determine expected_interval_timedelta for continuity check.")
            return True # Or False, depending on strictness. Let's be lenient for now.
            
        time_diffs = pd.Series(data.index[1:]) - pd.Series(data.index[:-1])
        # Use the extracted timedelta for comparison
        gaps = time_diffs > expected_interval_timedelta * 1.5 
        
        if gaps.any():
            gap_starts = data.index[:-1][gaps]
            logger.warning(f"Found {len(gap_starts)} time gaps. First gap at: {gap_starts[0]}")
            return False
            
        return True
        
    def validate_price_consistency(self, data: pd.DataFrame) -> bool:
        """Check price data consistency"""
        if data.empty:
            return False
            
        # Check OHLC relationships
        valid_ohlc = (
            (data['High'] >= data['Low']).all() and
            (data['High'] >= data['Open']).all() and
            (data['High'] >= data['Close']).all() and
            (data['Low'] <= data['Open']).all() and
            (data['Low'] <= data['Close']).all()
        )
        
        if not valid_ohlc:
            logger.warning("Invalid OHLC relationships found")
            return False
            
        # Check for extreme price changes
        returns = data['Close'].pct_change()
        std_dev = returns.std()
        extreme_returns = abs(returns) > std_dev * 4  # More than 4 standard deviations
        
        if extreme_returns.sum() > len(data) * 0.01:  # More than 1% extreme moves
            logger.warning(f"Found {extreme_returns.sum()} extreme price changes")
            return False
            
        return True
        
    def validate_volume_data(self, data: pd.DataFrame) -> bool:
        """Check volume data validity"""
        if data.empty or 'Volume' not in data.columns:
            return False
            
        # Check for negative volumes
        if (data['Volume'] < 0).any():
            logger.warning("Negative volumes found")
            return False
            
        # Check for suspiciously high volumes
        volume_std = data['Volume'].std()
        extreme_volumes = data['Volume'] > volume_std * 5
        
        if extreme_volumes.sum() > len(data) * 0.01:
            logger.warning(f"Found {extreme_volumes.sum()} suspicious volume spikes")
            return False
            
        # Check for too many zero volumes
        zero_volumes = (data['Volume'] == 0).sum()
        if zero_volumes > len(data) * 0.1:  # More than 10% zeros
            logger.warning(f"Too many zero volumes: {zero_volumes}")
            return False
            
        return True
        
    def calculate_quality_metrics(self, data: pd.DataFrame) -> DataQualityMetrics:
        """Calculate data quality metrics"""
        try:
            # Calculate completeness
            completeness = 1 - (data[self.required_columns].isnull().sum().sum() / 
                              (len(data) * len(self.required_columns)))
            
            # Calculate accuracy (using feature weights)
            accuracy_scores = []
            for col in data.columns:
                if col in self.feature_weights:
                    weight = self.feature_weights[col]
                    # Calculate accuracy for this feature (e.g., based on non-null values)
                    feature_accuracy = 1 - (data[col].isnull().sum() / len(data))
                    accuracy_scores.append(feature_accuracy * weight)
            
            accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.5
            
            # Calculate consistency
            consistency = self._calculate_consistency_score(data)
            
            # Calculate timeliness
            now = datetime.now(pytz.UTC)
            latest_data = data.index[-1]
            time_diff = (now - latest_data).total_seconds() / 3600  # Convert to hours
            max_delay = 24  # Maximum acceptable delay in hours
            timeliness = max(0, 1 - (time_diff / max_delay))
            
            # Calculate volume quality
            volume_quality = self._calculate_volume_quality(data)
            
            # Calculate price quality
            price_quality = self._calculate_price_quality(data)
            
            return DataQualityMetrics(
                completeness=completeness,
                accuracy=accuracy,
                consistency=consistency,
                timeliness=timeliness,
                volume_quality=volume_quality,
                price_quality=price_quality
            )
            
        except Exception as e:
            logger.error(f"Error calculating quality metrics: {str(e)}")
            raise

    def validate_and_clean_data(self, data: pd.DataFrame) -> Tuple[pd.DataFrame, DataQualityMetrics]:
        """Validate and clean the data"""
        try:
            # Calculate quality metrics
            metrics = self.calculate_quality_metrics(data)
            
            # Basic data cleaning
            data = data.copy()
            
            # Forward fill, then backward fill to handle NaNs at the beginning and end
            data = data.ffill()
            data = data.bfill()
            
            return data, metrics
            
        except Exception as e:
            logger.error(f"Error in data validation and cleaning: {str(e)}")
            raise

    def _calculate_consistency_score(self, df: pd.DataFrame) -> float:
        """Calculate data consistency score"""
        try:
            # Check if required columns exist
            missing_cols = [col for col in self.required_columns if col not in df.columns]
            if missing_cols:
                logger.warning(f"Missing required columns: {missing_cols}")
                return 0.0
                
            # Check for price consistency
            price_consistent = (df['High'] >= df['Close']).all() and \
                             (df['High'] >= df['Open']).all() and \
                             (df['Low'] <= df['Close']).all() and \
                             (df['Low'] <= df['Open']).all()
                             
            # Check for volume consistency
            volume_consistent = (df['Volume'] >= 0).all()
            
            # Weight the scores
            return 0.7 * float(price_consistent) + 0.3 * float(volume_consistent)
            
        except Exception as e:
            logger.error(f"Error calculating consistency score: {str(e)}")
            return 0.0

    def _calculate_volume_quality(self, df: pd.DataFrame) -> float:
        """Calculate volume data quality score"""
        try:
            if 'Volume' not in df.columns:
                return 0.0
                
            # Check for zero volumes
            zero_volumes = (df['Volume'] == 0).sum()
            zero_volume_score = 1 - (zero_volumes / len(df))
            
            # Check for volume spikes
            volume_mean = df['Volume'].mean()
            volume_std = df['Volume'].std()
            spikes = (df['Volume'] > volume_mean + 3 * volume_std).sum()
            spike_score = 1 - (spikes / len(df))
            
            # Combine scores with weights
            return 0.6 * zero_volume_score + 0.4 * spike_score
            
        except Exception as e:
            logger.error(f"Error calculating volume quality: {str(e)}")
            return 0.0

    def _calculate_price_quality(self, df: pd.DataFrame) -> float:
        """Calculate price data quality score"""
        try:
            # Check for required columns
            if not all(col in df.columns for col in ['Open', 'High', 'Low', 'Close']):
                return 0.0
                
            # Check price relationships
            valid_relationships = (
                (df['High'] >= df['Low']).all() and
                (df['High'] >= df['Open']).all() and
                (df['High'] >= df['Close']).all() and
                (df['Low'] <= df['Open']).all() and
                (df['Low'] <= df['Close']).all()
            )
            
            # Check for extreme price movements
            returns = df['Close'].pct_change()
            extreme_moves = (abs(returns) > 0.2).sum()  # 20% moves
            extreme_score = 1 - (extreme_moves / len(df))
            
            # Combine scores
            return 0.7 * float(valid_relationships) + 0.3 * extreme_score
            
        except Exception as e:
            logger.error(f"Error calculating price quality: {str(e)}")
            return 0.0 