"""A minimal worker with no custom logic or dependencies."""
from typing import Dict, Any
from mcp_server.workers.base_worker import BaseWorker
from mcp_server.core.exceptions import ExecutionError
class MinimalWorkerWorker:
    """A minimal worker with no custom logic or dependencies.
    
    @layer: Backend (Workers)
    """
    def __init__(self):
        """Initialize MinimalWorkerWorker."""
        pass
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute MinimalWorker worker logic.
        
        Args:
            context: Execution context with input data
            
        Returns:
            Dict with execution results
            
        Raises:
            ExecutionError: If execution fails
        """
        # TODO: Implement worker logic
        raise NotImplementedError("Worker logic not implemented")