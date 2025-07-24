import logging
import sys
from datetime import datetime
from typing import Optional

class ColoredFormatter(logging.Formatter):
    """Colored log formatter for better readability"""
    
    COLORS = {
        'DEBUG': '\033[36m',    # Cyan
        'INFO': '\033[32m',     # Green
        'WARNING': '\033[33m',  # Yellow
        'ERROR': '\033[31m',    # Red
        'CRITICAL': '\033[35m', # Magenta
        'RESET': '\033[0m'      # Reset
    }
    
    def format(self, record):
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        record.levelname = f"{color}{record.levelname}{self.COLORS['RESET']}"
        return super().format(record)

def setup_logger(name: str, level: str = "INFO") -> logging.Logger:
    """Setup logger with colored output"""
    
    logger = logging.getLogger(name)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Set level
    logger.setLevel(getattr(logging, level.upper()))
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(getattr(logging, level.upper()))
    
    # Create formatter
    formatter = ColoredFormatter(
        fmt='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # Prevent duplicate logs
    logger.propagate = False
    
    return logger

def log_agent_action(logger: logging.Logger, agent_name: str, action: str, details: Optional[str] = None):
    """Log agent actions with consistent format"""
    message = f"🤖 {agent_name} | {action}"
    if details:
        message += f" | {details}"
    logger.info(message)

def log_pebblo_action(logger: logging.Logger, action: str, details: Optional[str] = None):
    """Log Pebblo MCP actions with consistent format"""
    message = f"🛡️ Pebblo MCP | {action}"
    if details:
        message += f" | {details}"
    logger.info(message)

def log_security_event(logger: logging.Logger, event_type: str, details: str, severity: str = "WARNING"):
    """Log security events"""
    message = f"🚨 SECURITY | {event_type} | {details}"
    if severity.upper() == "ERROR":
        logger.error(message)
    elif severity.upper() == "CRITICAL":
        logger.critical(message)
    else:
        logger.warning(message)