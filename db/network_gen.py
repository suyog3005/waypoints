"""Procedural network generator for realistic railway topology.

Generates a large, organically-random railway network with:
- Backbone + branches topology (not grid-like)
- Curved edges using waypoint deflection (not straight lines)
- Deterministic reproducibility via seed

Usage:
    from db.network_gen import NetworkGenerator
    
    gen = NetworkGenerator(seed=12345)
    gen.generate(num_nodes=500, num_edges=800)
    nodes, edges = gen.nodes, gen.edges
    
    # Or via CLI:
    python -m db.network_gen --nodes=500 --edges=800 --seed=12345 --randomize
"""

import random
import math
import hashlib
from dataclasses import dataclass
from typing import Optional, Tuple, List


@dataclass
class Node:
    """Railway network node (station, junction, or signal point)."""
    id: str
    x: float  # meters
    y: float  # meters
    node_type: str  # 'station', 'junction', 'signal'
    name: Optional[str] = None


@dataclass
class Waypoint:
    """Intermediate waypoint on a curved track edge."""
    x: float  # meters
    y: float  # meters


@dataclass
class Edge:
    """Railway network edge (track segment) with optional waypoints for curved geometry."""
    id: str
    from_id: str
    to_id: str
    waypoints: List[Waypoint]  # Empty for straight edges, populated for curved edges
    track_id: Optional[str] = None
    name: Optional[str] = None


class NetworkGenerator:
    """Procedural railway network generator."""
    
    def __init__(
        self,
        seed: int = 12345,
        deflection_pct: float = 0.08,  # ±8% deflection magnitude
        segment_length: float = 5000.0,  # Max segment length before adding waypoint
    ):
        """Initialize the generator.
        
        Args:
            seed: RNG seed for reproducibility.
            deflection_pct: Perpendicular deflection as fraction of edge length (e.g., 0.08 = ±8%).
            segment_length: Maximum segment length before inserting a waypoint.
        """
        self.seed = seed
        self.deflection_pct = deflection_pct
        self.segment_length = segment_length
        self.nodes: List[Node] = []
        self.edges: List[Edge] = []
        self.rng = random.Random(seed)
        self.node_id_counter = 0
        self.edge_id_counter = 0
    
    def _next_node_id(self) -> str:
        """Generate a unique node ID."""
        node_id = f"n-{self.node_id_counter:04d}"
        self.node_id_counter += 1
        return node_id
    
    def _next_edge_id(self) -> str:
        """Generate a unique edge ID."""
        edge_id = f"e-{self.edge_id_counter:04d}"
        self.edge_id_counter += 1
        return edge_id
    
    def _distance(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Euclidean distance between two points (meters)."""
        return math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    
    def _bearing(self, x1: float, y1: float, x2: float, y2: float) -> float:
        """Bearing from (x1, y1) to (x2, y2) in radians."""
        return math.atan2(y2 - y1, x2 - x1)
    
    def _perpendicular_deflection(
        self,
        midpoint_x: float,
        midpoint_y: float,
        bearing: float,
        deflection_magnitude: float,
    ) -> Tuple[float, float]:
        """Apply perpendicular deflection to a midpoint.
        
        Returns new (x, y) position offset perpendicular to bearing.
        """
        # Perpendicular direction (90° from bearing)
        perp_bearing = bearing + math.pi / 2
        
        # Apply deflection
        new_x = midpoint_x + deflection_magnitude * math.cos(perp_bearing)
        new_y = midpoint_y + deflection_magnitude * math.sin(perp_bearing)
        
        return new_x, new_y
    
    def _generate_curved_waypoints(
        self,
        from_node: Node,
        to_node: Node,
        edge_id: str,
    ) -> List[Waypoint]:
        """Generate intermediate waypoints for a curved edge.
        
        Uses deflection-based interpolation to create smooth organic curves.
        Waypoints are deterministic given the edge ID and master seed.
        
        Returns list of waypoints (empty list if edge is short enough to be straight).
        """
        distance = self._distance(from_node.x, from_node.y, to_node.x, to_node.y)
        bearing = self._bearing(from_node.x, from_node.y, to_node.x, to_node.y)
        
        # Determine number of segments (each up to segment_length)
        num_segments = max(2, math.ceil(distance / self.segment_length))
        
        if num_segments <= 2:
            # Very short edge: keep straight (no waypoints)
            return []
        
        # Seed the RNG for this specific edge (deterministic per edge, varied per master seed)
        edge_hash = int(hashlib.md5(f"{edge_id}-{self.seed}".encode()).hexdigest(), 16)
        edge_rng = random.Random(edge_hash % (2**31))
        
        waypoints: List[Waypoint] = []
        
        # Generate waypoints for each segment
        for i in range(1, num_segments):
            t = i / num_segments  # Parameter [0, 1]
            
            # Linear interpolation along the straight line
            midpoint_x = from_node.x + t * (to_node.x - from_node.x)
            midpoint_y = from_node.y + t * (to_node.y - from_node.y)
            
            # Random deflection: ±deflection_pct * distance
            deflection_magnitude = edge_rng.uniform(
                -self.deflection_pct * distance,
                self.deflection_pct * distance,
            )
            
            # Apply perpendicular deflection
            wp_x, wp_y = self._perpendicular_deflection(
                midpoint_x,
                midpoint_y,
                bearing,
                deflection_magnitude,
            )
            
            waypoints.append(Waypoint(x=wp_x, y=wp_y))
        
        return waypoints
    
    def _add_edge(
        self,
        from_node: Node,
        to_node: Node,
        curved: bool = True,
    ) -> Edge:
        """Add an edge between two nodes, optionally with curved waypoints."""
        edge_id = self._next_edge_id()
        track_id = f"T-{edge_id}"
        
        waypoints = self._generate_curved_waypoints(from_node, to_node, edge_id) if curved else []
        
        edge = Edge(
            id=edge_id,
            from_id=from_node.id,
            to_id=to_node.id,
            waypoints=waypoints,
            track_id=track_id,
            name=f"{from_node.name} → {to_node.name}" if from_node.name and to_node.name else None,
        )
        self.edges.append(edge)
        return edge
    
    def generate(
        self,
        num_nodes: int = 500,
        num_edges: int = 800,
    ) -> Tuple[List[Node], List[Edge]]:
        """Generate a procedural railway network.
        
        Algorithm:
        1. Generate backbone: randomized walk of trunk stations
        2. Attach branch lines: 3-6 branches per trunk with random lengths
        3. Add cross-links: 2-4 loop connections between branches
        4. Curve all edges with waypoint deflection
        
        Args:
            num_nodes: Target number of nodes (approximate).
            num_edges: Target number of edges (approximate).
        
        Returns:
            Tuple of (nodes list, edges list).
        """
        self.nodes.clear()
        self.edges.clear()
        self.node_id_counter = 0
        self.edge_id_counter = 0
        
        # Estimate backbone length and branching factor
        # Backbone: ~20-30% of total nodes
        backbone_nodes = max(10, int(num_nodes * 0.25))
        
        # ── 1. Generate backbone ───────────────────────────────────────────
        
        # Random walk with jittered distances (8-25 km apart)
        backbone: List[Node] = []
        current_x, current_y = 0.0, 0.0
        
        for i in range(backbone_nodes):
            node_id = self._next_node_id()
            node_type = "station" if i == 0 or i == backbone_nodes - 1 else "junction"
            node = Node(
                id=node_id,
                x=current_x,
                y=current_y,
                node_type=node_type,
                name=f"{node_type.title()} {i}",
            )
            backbone.append(node)
            self.nodes.append(node)
            
            # Random bearing for next segment (±30° from current if not first)
            if i == 0:
                bearing = self.rng.uniform(0, 2 * math.pi)
            else:
                current_bearing = self._bearing(backbone[-2].x, backbone[-2].y, current_x, current_y)
                bearing = current_bearing + self.rng.uniform(-math.pi / 6, math.pi / 6)
            
            # Random distance (8-25 km)
            distance = self.rng.uniform(8_000, 25_000)
            current_x += distance * math.cos(bearing)
            current_y += distance * math.sin(bearing)
        
        # Connect backbone stations with curved edges
        for i in range(len(backbone) - 1):
            self._add_edge(backbone[i], backbone[i + 1], curved=True)
        
        # ── 2. Attach branches ─────────────────────────────────────────────
        
        remaining_nodes = num_nodes - len(self.nodes)
        num_branches = max(3, min(6, int(remaining_nodes / 15)))  # 3-6 branches
        branch_nodes_each = remaining_nodes // num_branches
        
        branches: List[List[Node]] = []
        
        for branch_idx in range(num_branches):
            # Pick random backbone station as root
            root = self.rng.choice(backbone)
            branch: List[Node] = [root]
            
            # Random initial bearing (±35° spread)
            branch_bearing = self.rng.uniform(0, 2 * math.pi)
            branch_x, branch_y = root.x, root.y
            
            # Generate branch line with branch_nodes_each nodes
            for node_idx in range(branch_nodes_each):
                node_id = self._next_node_id()
                node_type = "junction" if node_idx < branch_nodes_each - 1 else "station"
                node = Node(
                    id=node_id,
                    x=branch_x,
                    y=branch_y,
                    node_type=node_type,
                    name=f"Branch {branch_idx} {node_idx}",
                )
                branch.append(node)
                self.nodes.append(node)
                
                # Jitter the branch bearing (±35° per segment)
                branch_bearing += self.rng.uniform(-math.pi / 5, math.pi / 5)
                
                # Random distance (5-15 km)
                distance = self.rng.uniform(5_000, 15_000)
                branch_x += distance * math.cos(branch_bearing)
                branch_y += distance * math.sin(branch_bearing)
            
            branches.append(branch)
            
            # Connect branch nodes with curved edges
            for i in range(len(branch) - 1):
                self._add_edge(branch[i], branch[i + 1], curved=True)
        
        # ── 3. Add cross-links (loop connections) ──────────────────────────
        
        num_crosslinks = self.rng.randint(2, 4)
        for _ in range(num_crosslinks):
            if len(branches) < 2:
                break
            
            # Pick two random branches
            branch_a = self.rng.choice(branches)
            branch_b = self.rng.choice(branches)
            
            if branch_a is branch_b or len(branch_a) < 2 or len(branch_b) < 2:
                continue
            
            # Pick random nodes from each branch
            node_a = self.rng.choice(branch_a[1:])  # Skip root
            node_b = self.rng.choice(branch_b[1:])  # Skip root
            
            # Add cross-link with curved edge
            self._add_edge(node_a, node_b, curved=True)
        
        # ── 4. Validate network ────────────────────────────────────────────
        
        # Ensure all edges reference valid nodes
        node_ids = {n.id for n in self.nodes}
        valid_edges = [e for e in self.edges if e.from_id in node_ids and e.to_id in node_ids]
        self.edges = valid_edges
        
        return self.nodes, self.edges


def generate_network(
    num_nodes: int = 500,
    num_edges: int = 800,
    seed: Optional[int] = None,
    deflection_pct: float = 0.08,
) -> Tuple[List[Node], List[Edge]]:
    """Convenience function to generate a network."""
    if seed is None:
        seed = random.randint(0, 2**31 - 1)
    
    gen = NetworkGenerator(seed=seed, deflection_pct=deflection_pct)
    return gen.generate(num_nodes=num_nodes, num_edges=num_edges)


if __name__ == "__main__":
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description="Generate a procedural railway network.")
    parser.add_argument("--nodes", type=int, default=500, help="Target number of nodes.")
    parser.add_argument("--edges", type=int, default=800, help="Target number of edges.")
    parser.add_argument("--seed", type=int, default=12345, help="RNG seed for reproducibility.")
    parser.add_argument("--randomize", action="store_true", help="Use a random seed instead.")
    parser.add_argument("--deflection", type=float, default=0.08, help="Deflection magnitude as fraction (0.08 = ±8 percent).")
    
    args = parser.parse_args()
    
    seed = random.randint(0, 2**31 - 1) if args.randomize else args.seed
    
    print(f"Generating network with seed={seed}, nodes≈{args.nodes}, edges≈{args.edges}...")
    nodes, edges = generate_network(
        num_nodes=args.nodes,
        num_edges=args.edges,
        seed=seed,
        deflection_pct=args.deflection,
    )
    
    # Output as JSON for inspection
    output = {
        "seed": seed,
        "num_nodes": len(nodes),
        "num_edges": len(edges),
        "nodes": [
            {
                "id": n.id,
                "x": n.x,
                "y": n.y,
                "type": n.node_type,
                "name": n.name,
            }
            for n in nodes
        ],
        "edges": [
            {
                "id": e.id,
                "from": e.from_id,
                "to": e.to_id,
                "trackId": e.track_id,
                "waypoints": [{"x": w.x, "y": w.y} for w in e.waypoints],
                "name": e.name,
            }
            for e in edges
        ],
    }
    
    print(json.dumps(output, indent=2))
