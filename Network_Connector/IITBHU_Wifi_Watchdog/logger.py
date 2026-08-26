import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logger(diagnostic_mode=False):
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    logger = logging.getLogger("wifi_watchdog")
    
    if logger.hasHandlers():
        logger.handlers.clear()
        
    level = logging.DEBUG if diagnostic_mode else logging.INFO
    logger.setLevel(level)
    
    formatter = logging.Formatter('[%(asctime)s] %(message)s', datefmt='%H:%M:%S')
    
    file_handler = RotatingFileHandler(
        os.path.join(log_dir, "wifi_watchdog.log"),
        maxBytes=5*1024*1024, # 5 MB
        backupCount=3
    )
    file_handler.setFormatter(formatter)
    
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger
