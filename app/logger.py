# app/logger.py
import logging
import json
import re
from datetime import datetime

class PIIFormatter(logging.Formatter):
    """Custom logging formatter that scrubs sensitive PII patterns and formats output as JSON."""
    
    def format(self, record: logging.LogRecord) -> str:
        log_message = super().format(record)
        
        # Comprehensive PII scrubbing regex patterns
        # 1. PAN Card
        log_message = re.sub(r'\b[A-Z]{5}[0-9]{4}[A-Z]{1}\b', 'XXXXX[PAN]X', log_message, flags=re.IGNORECASE)
        # 2. Aadhaar Number
        log_message = re.sub(r'\b\d{4}\s?\d{4}\s?\d{4}\b', 'XXXX-XXXX-XXXX', log_message)
        # 3. Email Address
        log_message = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED_EMAIL]', log_message)
        # 4. Mobile Phone Number (10 digit Indian formats)
        log_message = re.sub(r'\b(?:\+91[\-\s]?)?[6-9]\d{9}\b', '[REDACTED_PHONE]', log_message)
        # 5. Bank Account / Credit Card numbers (9-16 digits)
        log_message = re.sub(r'\b\d{9,16}\b', lambda m: 'X' * (len(m.group(0)) - 4) + m.group(0)[-4:], log_message)

        # Structure as JSON object
        structured_log = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": log_message
        }
        return json.dumps(structured_log)

def get_structured_logger(name: str = "cred_agent") -> logging.Logger:
    """Configures and returns a structured logger with PII scrubbing enabled."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler()
        handler.setFormatter(PIIFormatter())
        logger.addHandler(handler)
    return logger

# Global logger instance
logger = get_structured_logger()