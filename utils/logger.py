from database.db import SessionLocal
from database.models import SystemLog

class Logger:
    COLORS = {
        'INFO': '\033[94m',
        'SUCCESS': '\033[92m',
        'WARNING': '\033[93m',
        'ERROR': '\033[91m',
        'RESET': '\033[0m'
    }

    def __init__(self, module="system"):
        self.module = module
    
    def _log(self, level, message):
        session = SessionLocal()
        try:
            log = SystemLog(module=self.module, level=level, message=message)
            session.add(log)
            session.commit()
        except Exception:
            pass # Prevent DB errors from crashing the app
        finally:
            session.close()
            
        color = self.COLORS.get(level, self.COLORS['RESET'])
        print(f"{color}[{level}] [{self.module}] {message}{self.COLORS['RESET']}")
    
    def info(self, message):
        self._log('INFO', message)
    
    def success(self, message):
        self._log('SUCCESS', message)
    
    def warning(self, message):
        self._log('WARNING', message)
    
    def error(self, message):
        self._log('ERROR', message)
