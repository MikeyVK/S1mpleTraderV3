# mcp_server/managers/dependency_graph_validator.py
"""
Dependency graph validator for project initialization.

Validates dependency graphs are acyclic (DAG) using topological sort algorithm.
Used by ProjectManager to ensure phase dependencies don't create cycles.

@layer: Manager
@dependencies: [mcp_server.state.project]
@responsibilities: [cycle detection, topological sort, dependency validation]
"""
# Standard library
from collections import defaultdict, deque

# Project modules
from mcp_server.state.project import PhaseSpec


class DependencyGraphValidator:
    """
    Validates dependency graphs for project initialization.

    Uses Kahn's algorithm for topological sort to detect cycles.
    """

    def validate_acyclic(
        self,
        phases: list[PhaseSpec]
    ) -> tuple[bool, list[str] | None]:
        """
        Check if dependency graph is acyclic (DAG).

        Args:
            phases: List of phase specifications to validate

        Returns:
            Tuple of (is_valid, cycle_path)
            - is_valid: True if graph is acyclic, False if cycle detected
            - cycle_path: List of phase IDs forming cycle, or None if valid

        Examples:
            >>> validator = DependencyGraphValidator()
            >>> phases = [
            ...     PhaseSpec(phase_id="A", title="Phase A", depends_on=[]),
            ...     PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"])
            ... ]
            >>> is_valid, cycle = validator.validate_acyclic(phases)
            >>> assert is_valid is True
            >>> assert cycle is None
        """
        try:
            self.topological_sort(phases)
            return (True, None)
        except ValueError as e:
            # Extract cycle from error message
            error_msg = str(e)
            if "Circular dependency detected" in error_msg:
                # Parse cycle from error message (format: "cycle: A -> B -> C -> A")
                if "cycle:" in error_msg:
                    cycle_str = error_msg.split("cycle:")[1].strip()
                    cycle_path = [p.strip() for p in cycle_str.split("->")]
                    return (False, cycle_path)
            return (False, None)

    def topological_sort(self, phases: list[PhaseSpec]) -> list[str]:
        """
        Perform topological sort on phases using Kahn's algorithm.

        Args:
            phases: List of phase specifications to sort

        Returns:
            List of phase IDs in topologically sorted order

        Raises:
            ValueError: If cycle detected in dependency graph

        Examples:
            >>> validator = DependencyGraphValidator()
            >>> phases = [
            ...     PhaseSpec(phase_id="B", title="Phase B", depends_on=["A"]),
            ...     PhaseSpec(phase_id="A", title="Phase A", depends_on=[])
            ... ]
            >>> sorted_ids = validator.topological_sort(phases)
            >>> assert sorted_ids == ["A", "B"]
        """
        # Build adjacency list and in-degree map
        graph: dict[str, list[str]] = defaultdict(list)
        in_degree: dict[str, int] = {phase.phase_id: 0 for phase in phases}

        for phase in phases:
            for dep in phase.depends_on:
                graph[dep].append(phase.phase_id)
                in_degree[phase.phase_id] += 1

        # Initialize queue with nodes that have no dependencies
        queue: deque[str] = deque(
            [phase_id for phase_id, degree in in_degree.items() if not degree]
        )
        sorted_order: list[str] = []

        while queue:
            current = queue.popleft()
            sorted_order.append(current)

            # Reduce in-degree for neighbors
            for neighbor in graph[current]:
                in_degree[neighbor] -= 1
                if not in_degree[neighbor]:
                    queue.append(neighbor)

        # Check if all nodes were processed
        if len(sorted_order) != len(phases):
            # Find cycle for better error message
            unprocessed = [
                pid for pid in in_degree if pid not in sorted_order
            ]
            cycle = self._find_cycle(phases, unprocessed[0])
            cycle_str = " -> ".join(cycle)
            raise ValueError(
                f"Circular dependency detected in project phases, cycle: {cycle_str}"
            )

        return sorted_order

    def _find_cycle(self, phases: list[PhaseSpec], start: str) -> list[str]:
        """
        Find and return a cycle starting from given phase.

        Args:
            phases: List of phase specifications
            start: Phase ID to start cycle detection from

        Returns:
            List of phase IDs forming a cycle

        Note:
            Uses DFS with path tracking to find cycle.
        """
        # Build dependency map
        deps_map = {phase.phase_id: phase.depends_on for phase in phases}

        visited: set[str] = set()
        path: list[str] = []

        def dfs(node: str) -> list[str] | None:
            if node in path:
                # Found cycle - return cycle portion
                cycle_start = path.index(node)
                return path[cycle_start:] + [node]

            if node in visited:
                return None

            visited.add(node)
            path.append(node)

            for dep in deps_map.get(node, []):
                result = dfs(dep)
                if result:
                    return result

            path.pop()
            return None

        cycle = dfs(start)
        return cycle if cycle else [start]
