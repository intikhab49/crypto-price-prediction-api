class EarlyStopping:
    """Early stopping to prevent overfitting with comprehensive metric tracking"""
    def __init__(self, patience=10, min_delta=0):
        self.patience = patience
        self.min_delta = min_delta
        self.counter = 0
        self.best_loss = float('inf')
        self.best_epoch = None
        self.best_metrics = None
        self.early_stop = False
        self.best_model_state = None
        
    def step(self, val_loss, epoch, metrics=None, model_state=None):
        """
        Returns True if training should stop. Always saves the model with the absolute
        minimum validation loss seen during training.
        
        Args:
            val_loss (float): Current validation loss
            epoch (int): Current epoch number
            metrics (dict, optional): Additional metrics to track (e.g., MAPE, R2)
            model_state (dict, optional): Current model state dict
        """
        import logging
        logger = logging.getLogger(__name__)
        
        # Get current R2 score and MAPE from metrics
        current_r2 = metrics.get('val_r2', float('-inf')) if metrics else float('-inf')
        current_mape = metrics.get('val_mape', float('inf')) if metrics else float('inf')
        
        # Check if validation loss improved (strictly less than best_loss)
        if val_loss < self.best_loss:
            improvement = self.best_loss - val_loss
            # Update all best tracking variables together
            self.best_loss = val_loss
            self.best_epoch = epoch
            self.best_metrics = metrics.copy() if metrics else None
            self.best_model_state = model_state.copy() if model_state else None  # Ensure we make a copy
            self.counter = 0
            
            logger.info(f"New absolute best validation loss: {val_loss:.6f} at epoch {epoch} "
                       f"(improvement: {improvement:.6f}, MAPE: {current_mape:.2f}%, "
                       f"R2: {current_r2:.4f}, Combined Score: {current_r2 - current_mape/100:.4f})")
            return False
        else:
            self.counter += 1
            if self.counter >= self.patience:
                logger.info(f"Early stopping triggered at epoch {epoch}. "
                          f"Best model was from epoch {self.best_epoch} with "
                          f"Val Loss: {self.best_loss:.6f}, "
                          f"MAPE: {self.best_metrics.get('val_mape', float('inf')):.2f}%, "
                          f"R2: {self.best_metrics.get('val_r2', float('-inf')):.4f}")
                self.early_stop = True
                return True
            return False
        
    def get_best_state(self):
        """Returns the best state information"""
        return {
            'epoch': self.best_epoch,
            'metrics': self.best_metrics,
            'model_state': self.best_model_state
        } 