"""
Worker Interface - Base protocol for all worker types.

This module defines the minimal interface that all workers must implement.
"""

from typing import Protocol


class IWorker(Protocol):
    """
    Base protocol for all worker types.
    
    This is a minimal interface that defines the contract all workers
    must fulfill. Specific worker types (OpportunityWorker, ContextWorker, etc.)
    will extend this with additional methods.
    """
    
    @property
    def name(self) -> str:
        """
        Get the worker's name/identifier.
        
        Returns:
            Worker name (typically from manifest or configuration)
        """
        ...
