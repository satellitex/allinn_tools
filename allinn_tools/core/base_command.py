"""Base command class for extensible CLI commands."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseCommand(ABC):
    """Base class for all CLI commands."""
    
    def __init__(self):
        self.logger = self._setup_logger()
    
    def _setup_logger(self) -> logging.Logger:
        """Set up logger for the command."""
        logger = logging.getLogger(self.__class__.__name__)
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Command name for CLI."""
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        """Command description for help text."""
        pass
    
    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """Main command execution logic."""
        pass
    
    def validate_args(self, **kwargs) -> Dict[str, Any]:
        """Validate command arguments. Override if needed."""
        return kwargs