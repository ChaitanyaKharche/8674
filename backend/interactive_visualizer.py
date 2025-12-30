"""
Interactive Curriculum Visualizer - FIXED VERSION
Creates CurricularAnalytics-style network graphs
"""
import streamlit as st
import networkx as nx
import plotly.graph_objects as go
import pickle
import json
from typing import Dict, List, Tuple, Set
import numpy as np

class CurriculumVisualizer:
    """
    Creates interactive curriculum dependency graphs
    Similar to CurricularAnalytics.org
    """
    
    def __init__(self, graph: nx.DiGraph):
        self.graph = graph
        self.courses = dict(graph.nodes(data=True))
        self.positions = None
        self.layers = None
        
    def calculate_metrics(self, course_id: str) -> Dict:
        """Calculate blocking factor, delay factor, centrality"""
        if course_id not in self.graph: return {}
            
        blocking = len(list(nx.descendants(self.graph, course_id)))
        
        delay = 0
        sinks = [n for n, d in self.graph.out_degree() if d == 0]
        max_len = 0
        for sink in sinks:
            try:
                paths = list(nx.all_simple_paths(self.graph, source=course_id, target=sink))
                if paths:
                    current_max = max(len(p) for p in paths)
                    if current_max > max_len:
                        max_len = current_max
            except (nx.NetworkXNoPath, nx.NodeNotFound):
                continue
        delay = max_len
        
        centrality_dict = nx.betweenness_centrality(self.graph)
        centrality = centrality_dict.get(course_id, 0) * 100
        complexity = self.courses.get(course_id, {}).get('complexity', 0)
        
        return {
            'blocking': blocking,
            'delay': delay,
            'centrality': round(centrality, 1),
            'complexity': complexity
        }
    
    def create_hierarchical_layout(self) -> Dict:
        """Create semester-based layout like CurricularAnalytics"""
        try:
            topo_order = list(nx.topological_sort(self.graph))
        except nx.NetworkXError:
            topo_order = list(nx.dfs_preorder_nodes(self.graph))
        
        depths = {}
        for node in topo_order:
            predecessors = list(self.graph.predecessors(node))
            if not predecessors:
                depths[node] = 0
            else:
                depths[node] = max(depths.get(p, 0) for p in predecessors) + 1
        
        layers = {}
        for node, depth in depths.items():
            layers.setdefault(depth, []).append(node)
        
        positions = {}
        for depth, nodes in layers.items():
            width = len(nodes)
            spacing = 2.0 / (width + 1) if width > 0 else 1
            for i, node in enumerate(nodes):
                positions[node] = ((i + 1) * spacing - 1, -depth * 2)
        
        self.positions = positions
        self.layers = layers
        return positions
    
    def create_interactive_plot(self, highlight_path: List[str] = None) -> go.Figure:
        """Create Plotly interactive network graph"""
        if not self.positions:
            self.create_hierarchical_layout()
        
        edge_traces = []
        for edge in self.graph.edges():
            if edge[0] in self.positions and edge[1] in self.positions:
                x0, y0 = self.positions[edge[0]]
                x1, y1 = self.positions[edge[1]]
                is_critical = False
                if highlight_path:
                    try: is_critical = highlight_path.index(edge[1]) == highlight_path.index(edge[0]) + 1
                    except ValueError: pass
                
                edge_traces.append(go.Scatter(
                    x=[x0, x1, None], y=[y0, y1, None], mode='lines',
                    line=dict(width=3 if is_critical else 1, color='red' if is_critical else '#888'),
                    hoverinfo='none'
                ))
        
        node_x, node_y, node_text, node_color, node_size = [], [], [], [], []
        for node in self.graph.nodes():
            if node in self.positions:
                x, y = self.positions[node]
                metrics = self.calculate_metrics(node)
                node_x.append(x)
                node_y.append(y)
                node_text.append(f"<b>{node}: {self.courses.get(node, {}).get('name', 'N/A')}</b><br>Complexity: {metrics.get('complexity', 0)}<br>Blocking: {metrics.get('blocking', 0)}")
                node_color.append(metrics.get('complexity', 0))
                node_size.append(15 + metrics.get('blocking', 0) * 2)
        
        node_trace = go.Scatter(
            x=node_x, y=node_y, mode='markers+text',
            text=[node for node in self.graph.nodes() if node in self.positions],
            textposition="top center", textfont=dict(size=9),
            hovertext=node_text, hoverinfo='text',
            marker=dict(
                showscale=True, colorscale='Viridis', size=node_size, color=node_color,
                # FIX: 'titleside' is invalid. Correct syntax is a nested 'title' dict.
                colorbar=dict(
                    thickness=15,
                    title=dict(text="Complexity", side="right"), 
                    xanchor="left"
                )
            )
        )
        
        fig = go.Figure(data=edge_traces + [node_trace])
        fig.update_layout(
            title_text='Interactive Curriculum Map', showlegend=False, hovermode='closest',
            margin=dict(b=0, l=0, r=0, t=40), plot_bgcolor='white', height=800,
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )
        return fig
    
    def find_critical_path(self) -> List[str]:
        """Find the longest path (critical path) in curriculum"""
        if not nx.is_directed_acyclic_graph(self.graph): return []
        return nx.dag_longest_path(self.graph)

    def export_to_curricular_analytics_format(self, plan: Dict) -> Dict:
        """Export plan in CurricularAnalytics JSON format"""
        ca_format = {"curriculum": {"courses": [], "dependencies": []}, "metrics": {}}
        for course_id in self.graph.nodes():
            metrics = self.calculate_metrics(course_id)
            ca_format["curriculum"]["courses"].append({
                "id": course_id, "name": self.courses.get(course_id, {}).get('name', ''), **metrics
            })
        for edge in self.graph.edges():
            ca_format["curriculum"]["dependencies"].append({"source": edge[0], "target": edge[1]})
        return ca_format


    def _is_required_course(self, course_id: str) -> bool:
        """Check if course is required in any concentration"""
        
        # This would check against your CONCENTRATION_REQUIREMENTS
        required_courses = {
            "CS1800", "CS2500", "CS2510", "CS2800",
            "CS3000", "CS3500", "CS3650", "CS3700",
            "CS4100", "DS4400", "DS3000", "CY2550",
            "CY3740", "CS4700", "MATH1341", "MATH1342"
        }
        return course_id in required_courses
    
    def _create_plan_subgraph(self, plan_courses: Set[str]) -> nx.DiGraph:
        """Creates a subgraph containing only the courses in the plan."""
        valid_plan_courses = [c for c in plan_courses if c in self.graph]
        return self.graph.subgraph(valid_plan_courses).copy()
    
    def _find_critical_path_in_subgraph(self, subgraph: nx.DiGraph) -> List[str]:
        """Finds the longest path in a given subgraph."""
        if not nx.is_directed_acyclic_graph(subgraph):
            return []
        
        sources = [n for n in subgraph.nodes() if subgraph.in_degree(n) == 0]
        sinks = [n for n in subgraph.nodes() if subgraph.out_degree(n) == 0]
        
        longest_path = []
        max_length = 0
        
        for source in sources:
            for sink in sinks:
                try:
                    paths = list(nx.all_simple_paths(subgraph, source, sink))
                    for path in paths:
                        if len(path) > max_length:
                            max_length = len(path)
                            longest_path = path
                except nx.NetworkXNoPath:
                    continue
        return longest_path
    
    def calculate_plan_specific_metrics(self, plan_courses: Set[str]) -> Dict[str, Dict]:
        """Calculate metrics using ONLY courses in the actual plan"""
        
        # Create subgraph of just the plan
        plan_graph = self._create_plan_subgraph(plan_courses)
        
        metrics = {}
        for course in plan_courses:
            if course not in plan_graph:
                continue
                
            # Blocking: only count courses IN THE PLAN that this blocks
            plan_descendants = set(nx.descendants(plan_graph, course)) & plan_courses
            blocking = len(plan_descendants)
            
            # Delay: longest path to end of plan
            delay = 0
            plan_sinks = [n for n in plan_graph.nodes() if plan_graph.out_degree(n) == 0]
            max_len = 0
            for sink in plan_sinks:
                if sink in plan_courses:  # Only consider plan endpoints
                    try:
                        paths = list(nx.all_simple_paths(plan_graph, source=course, target=sink))
                        if paths:
                           current_max = max(len(p) for p in paths)
                           if current_max > max_len:
                               max_len = current_max
                    except (nx.NetworkXNoPath, nx.NodeNotFound):
                        continue
            delay = max_len
    
            # Centrality within plan
            if len(plan_graph) > 2:
                centrality_dict = nx.betweenness_centrality(plan_graph)
                centrality = centrality_dict.get(course, 0) * 100
            else:
                centrality = 0
            
            metrics[course] = {
                'blocking_plan': blocking,
                'delay_plan': delay,
                'centrality_plan': round(centrality, 1),
                'is_required': self._is_required_course(course)
            }
        
        return metrics
    
    def compare_metric_systems(self, plan_courses: Set[str]) -> Dict:
        """Compare global vs plan-specific metrics"""
        
        global_metrics = {}
        plan_metrics = self.calculate_plan_specific_metrics(plan_courses)
        
        comparison = {
            'critical_path_match': False,
            'correlation': {},
            'major_differences': []
        }
        
        # Calculate global metrics for plan courses
        for course in plan_courses:
            if course in self.graph:
                global_metrics[course] = self.calculate_metrics(course)
        
        # Find critical paths in both systems
        global_critical = self.find_critical_path()
        plan_graph = self._create_plan_subgraph(plan_courses)
        plan_critical = self._find_critical_path_in_subgraph(plan_graph)
        
        comparison['critical_path_match'] = (global_critical == plan_critical)
        comparison['global_critical'] = global_critical[:5] if global_critical else []
        comparison['plan_critical'] = plan_critical[:5] if plan_critical else []
        
        # Find courses with major metric differences
        for course in plan_courses:
            if course in global_metrics and course in plan_metrics:
                global_blocking = global_metrics[course]['blocking']
                plan_blocking = plan_metrics[course]['blocking_plan']
                
                if global_blocking > 0:
                    diff_ratio = abs(global_blocking - plan_blocking) / global_blocking
                    if diff_ratio > 0.5:  # More than 50% difference
                        comparison['major_differences'].append({
                            'course': course,
                            'global_blocking': global_blocking,
                            'plan_blocking': plan_blocking,
                            'ratio': diff_ratio
                        })
        
        return comparison