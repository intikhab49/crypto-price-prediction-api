#!/usr/bin/env python3
import os
import sys
import logging
import argparse
from datetime import datetime
import pytz
from typing import List, Dict
import json
import numpy as np
from train import train_all_models
from evaluate import evaluate_all_models
from controllers.prediction import predict_next_price, ensemble_prediction
from controllers.data_validator import DataValidator
from controllers.data_fetcher import DataFetcher
from config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def setup_environment():
    """Setup required directories and environment"""
    try:
        # Create required directories
        directories = [
            settings.MODEL_PATH,
            settings.CACHE_DIR,
            'plots',
            'logs',
            'results',
            'data/raw',
            'data/processed',
            'data/validated'
        ]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
            
        # Verify environment variables
        required_vars = [
            'COINGECKO_API_KEY',
            'DATABASE_URL',
            'MODEL_PATH',
            'CACHE_DIR'
        ]
        
        missing_vars = [var for var in required_vars if not os.getenv(var)]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
        return True
        
    except Exception as e:
        logger.error(f"Environment setup failed: {str(e)}")
        return False

def validate_and_prepare_data(symbol: str, timeframe: str) -> Dict:
    """Fetch, validate, and prepare data for a symbol and timeframe"""
    try:
        data_fetcher = DataFetcher()
        data_validator = DataValidator()
        
        # 1. Fetch data
        df = data_fetcher.get_merged_data(symbol, timeframe)
        if df is None or df.empty:
            raise ValueError(f"No data available for {symbol} ({timeframe})")
            
        # Save raw data
        raw_file = f"data/raw/{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d')}.csv"
        df.to_csv(raw_file)
        logger.info(f"Raw data saved to {raw_file}")
        
        # 2. Validate data
        is_valid, metrics, cleaned_df = data_validator.validate_data(df, timeframe)
        if not is_valid:
            raise ValueError(f"Data validation failed for {symbol} ({timeframe})")
            
        # Save validation metrics
        metrics_file = f"data/validated/{symbol}_{timeframe}_metrics_{datetime.now().strftime('%Y%m%d')}.json"
        with open(metrics_file, 'w') as f:
            json.dump(metrics, f, indent=2)
        logger.info(f"Validation metrics saved to {metrics_file}")
        
        # 3. Prepare data for training
        data_info, prepared_df = data_validator.prepare_training_data(cleaned_df)
        
        # Save processed data
        processed_file = f"data/processed/{symbol}_{timeframe}_{datetime.now().strftime('%Y%m%d')}.csv"
        prepared_df.to_csv(processed_file)
        logger.info(f"Processed data saved to {processed_file}")
        
        return {
            'status': 'success',
            'data': prepared_df,
            'metrics': metrics,
            'data_info': data_info,
            'files': {
                'raw': raw_file,
                'processed': processed_file,
                'metrics': metrics_file
            }
        }
        
    except Exception as e:
        logger.error(f"Data preparation failed for {symbol} ({timeframe}): {str(e)}")
        return {
            'status': 'error',
            'error': str(e)
        }

def run_pipeline(symbols: List[str] = None, timeframes: List[str] = None, 
                skip_training: bool = False, skip_evaluation: bool = False) -> Dict:
    """Run the complete prediction pipeline"""
    try:
        # Setup environment
        if not setup_environment():
            raise RuntimeError("Environment setup failed")
            
        pipeline_start = datetime.now(pytz.UTC)
        results = {
            'start_time': pipeline_start.isoformat(),
            'symbols': symbols,
            'timeframes': timeframes,
            'data_validation': {},
            'training': None,
            'evaluation': None,
            'predictions': {}
        }
        
        # Validate and prepare data
        for symbol in symbols or ["BTC", "ETH", "BNB", "XRP", "ADA", "DOGE", "SOL"]:
            results['data_validation'][symbol] = {}
            for timeframe in timeframes or settings.TIMEFRAME_OPTIONS:
                logger.info(f"Preparing data for {symbol} ({timeframe})")
                data_result = validate_and_prepare_data(symbol, timeframe)
                results['data_validation'][symbol][timeframe] = data_result
                
                if data_result['status'] == 'error':
                    logger.error(f"Skipping {symbol} ({timeframe}) due to data preparation failure")
                    continue
        
        # Train models
        if not skip_training:
            logger.info("Starting model training")
            training_results = train_all_models(symbols, timeframes)
            results['training'] = {
                'total': len(training_results),
                'successful': sum(1 for r in training_results if r['result']['status'] == 'success'),
                'results': training_results
            }
        
        # Evaluate models
        if not skip_evaluation:
            logger.info("Starting model evaluation")
            evaluation_results = evaluate_all_models(symbols, timeframes)
            results['evaluation'] = {
                'total': len(evaluation_results),
                'successful': sum(1 for r in evaluation_results if 'metrics' in r),
                'results': evaluation_results
            }
        
        # Make predictions
        logger.info("Making predictions")
        for symbol in symbols or ["BTC", "ETH", "BNB", "XRP", "ADA", "DOGE", "SOL"]:
            if symbol not in results['data_validation'] or all(r['status'] == 'error' for r in results['data_validation'][symbol].values()):
                logger.warning(f"Skipping predictions for {symbol} due to data validation failures")
                continue
                
            symbol_predictions = {}
            for timeframe in timeframes or settings.TIMEFRAME_OPTIONS:
                if results['data_validation'][symbol][timeframe]['status'] == 'success':
                    try:
                        prediction = predict_next_price(symbol, timeframe)
                        symbol_predictions[timeframe] = prediction
                    except Exception as e:
                        logger.error(f"Prediction failed for {symbol} ({timeframe}): {str(e)}")
                        symbol_predictions[timeframe] = {'error': str(e)}
            
            # Ensemble prediction
            try:
                ensemble = ensemble_prediction(symbol)
                symbol_predictions['ensemble'] = ensemble
            except Exception as e:
                logger.error(f"Ensemble prediction failed for {symbol}: {str(e)}")
                symbol_predictions['ensemble'] = {'error': str(e)}
            
            results['predictions'][symbol] = symbol_predictions
        
        # Save results
        pipeline_end = datetime.now(pytz.UTC)
        results['end_time'] = pipeline_end.isoformat()
        results['duration'] = str(pipeline_end - pipeline_start)
        
        output_file = f"results/pipeline_results_{pipeline_start.strftime('%Y%m%d_%H%M%S')}.json"
        with open(output_file, 'w') as f:
            json.dump(results, f, indent=2)
        
        logger.info(f"Pipeline completed. Results saved to {output_file}")
        return results
        
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        return {
            'status': 'error',
            'error': str(e),
            'timestamp': datetime.now(pytz.UTC).isoformat()
        }

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='Run cryptocurrency prediction pipeline')
    parser.add_argument('--symbols', nargs='+', help='Symbols to process (default: all)')
    parser.add_argument('--timeframes', nargs='+', choices=settings.TIMEFRAME_OPTIONS,
                      help='Timeframes to process (default: all)')
    parser.add_argument('--skip-training', action='store_true',
                      help='Skip model training phase')
    parser.add_argument('--skip-evaluation', action='store_true',
                      help='Skip model evaluation phase')
    args = parser.parse_args()
    
    try:
        results = run_pipeline(
            symbols=args.symbols,
            timeframes=args.timeframes,
            skip_training=args.skip_training,
            skip_evaluation=args.skip_evaluation
        )
        
        if results.get('status') == 'error':
            logger.error(f"Pipeline failed: {results['error']}")
            sys.exit(1)
            
        # Print summary
        logger.info("\nPipeline Summary:")
        logger.info(f"Start Time: {results['start_time']}")
        logger.info(f"End Time: {results['end_time']}")
        logger.info(f"Duration: {results['duration']}")
        
        logger.info("\nData Validation Summary:")
        for symbol in results['data_validation']:
            logger.info(f"\n{symbol}:")
            for timeframe, result in results['data_validation'][symbol].items():
                if result['status'] == 'success':
                    metrics = result['metrics']
                    logger.info(f"  {timeframe}: Success - Quality Score: {metrics['data_quality_score']:.2f}")
                else:
                    logger.info(f"  {timeframe}: Failed - {result['error']}")
        
        if results.get('training'):
            logger.info(f"\nTraining Results:")
            logger.info(f"Total Models: {results['training']['total']}")
            logger.info(f"Successful: {results['training']['successful']}")
            
        if results.get('evaluation'):
            logger.info(f"\nEvaluation Results:")
            logger.info(f"Total Models: {results['evaluation']['total']}")
            logger.info(f"Successful: {results['evaluation']['successful']}")
            
        logger.info("\nPredictions Summary:")
        for symbol in results['predictions']:
            logger.info(f"\n{symbol}:")
            for timeframe, prediction in results['predictions'][symbol].items():
                if isinstance(prediction, dict) and 'error' in prediction:
                    logger.info(f"  {timeframe}: Failed - {prediction['error']}")
                else:
                    logger.info(f"  {timeframe}: {prediction.get('predicted_price', 'N/A')} "
                              f"(confidence: {prediction.get('confidence', 0):.2f})")
        
    except Exception as e:
        logger.error(f"Pipeline execution failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 