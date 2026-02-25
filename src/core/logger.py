import logging
import json
import os
from datetime import datetime
from pathlib import Path

# Configurar directorio de logs
LOGS_DIR = Path("logs")
LOGS_DIR.mkdir(exist_ok=True)

class JSONFormatter(logging.Formatter):
    """Formatter to outputs JSON strings."""
    def format(self, record):
        log_record = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "module": record.module,
            "message": record.getMessage()
        }
        
        # Add custom fields if passed directly via extra parameter
        if hasattr(record, "extra_data"):
             log_record.update(record.extra_data)
             
        # Catch and encode exception info if present
        if record.exc_info:
            log_record["exception"] = self.formatException(record.exc_info)
            
        return json.dumps(log_record)

def setup_logger(name: str, log_file: str, level=logging.INFO):
    """Function to setup as many loggers as you want"""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Evitamos que se agreguen duplicados si se llama de nuevo
    if not logger.handlers:
        file_handler = logging.FileHandler(LOGS_DIR / log_file, encoding='utf-8')
        file_handler.setFormatter(JSONFormatter())
        logger.addHandler(file_handler)
        
        # Add console handler for easy debugging in terminal
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(module)s: %(message)s'))
        logger.addHandler(console_handler)

    return logger

# Inicialización de Loggers dedicados
app_logger = setup_logger('app', 'app.log', logging.INFO)
error_logger = setup_logger('errors', 'errors.log', logging.ERROR)
ingestion_logger = setup_logger('ingestion', 'ingestion.log', logging.INFO)
ai_logger = setup_logger('ai_calls', 'ai_calls.log', logging.INFO)

def log_ingestion_event(event: str, **kwargs):
    """Helper for structured ingestion logging."""
    extra_data = {"event": event}
    extra_data.update(kwargs)
    ingestion_logger.info(f"Ingestion event: {event}", extra={"extra_data": extra_data})
    
def log_ai_call(prompt_hash: str, model: str, success: bool, tokens_est: int, latency_ms: float, pathway: str="direct_answer"):
    """Helper for documenting AI calls."""
    extra = {
        "event": "ai_call",
        "prompt_hash": prompt_hash,
        "model": model,
        "success": success,
        "tokens_est": tokens_est,
        "latency_ms": latency_ms,
        "pathway": pathway
    }
    ai_logger.info("AI call executed", extra={"extra_data": extra})

def log_error(module_name: str, message: str, error_obj: Exception = None):
    """Helper to log errors cleanly."""
    extra = {"event": "error", "error_type": type(error_obj).__name__ if error_obj else "Unknown"}
    error_logger.error(message, exc_info=error_obj, extra={"extra_data": extra})
