#!/usr/bin/env python3
"""
Enhanced Curriculum Analyzer - Production Version
Fixes: Robust file loading, Tagging logic, Prereq fixes.
"""
import pickle
import argparse
import networkx as nx
import re
import json
import logging
from typing import Set, Dict, Optional
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def get_course_level(cid: str) -> int:
    match = re.search(r'\d+', cid)
    return int(match.group(0)) if match else 9999

class CurriculumAnalyzer:
    KEEP_SUBJECTS = {"CS", "DS", "CY", "MATH", "PHYS", "ENGW"}
    UNDERGRAD_ACCESSIBLE_GRAD = {
        "CS5010", "CS5100", "CS5200", "CS5340", "CS5400", "CS5500", "CS5520", 
        "CS5600", "CS5610", "CS5700", "CS5800", "CS6120", "CS6140", "CS6200", 
        "DS5110", "DS5220", "DS5230", "CY5700", "CY5770"
    }

    def __init__(self, input_path):
        """
        Robustly loads graph from ANY format (Graph object, Dict, or Combined Dict).
        """
        logger.info(f"📚 Loading from {input_path}...")
        try:
            with open(input_path, 'rb') as f:
                data = pickle.load(f)
            
            # Case 1: Direct Graph Object
            if isinstance(data, (nx.Graph, nx.DiGraph)):
                self.graph = data
                logger.info("   Detected 'Direct Graph' format.")
                
            # Case 2: Dictionary containing Graph
            elif isinstance(data, dict):
                if "graph" in data:
                    self.graph = data["graph"]
                    logger.info("   Detected 'Combined' format (Graph found).")
                else:
                    # Fallback: Try to build graph if only courses dict exists
                    logger.warning("   No 'graph' key found. Attempting to build from course list...")
                    self.graph = nx.DiGraph()
                    courses = data.get("courses", data) # Assume it's a course dict
                    for cid, cdata in courses.items():
                        self.graph.add_node(cid, **cdata)
            else:
                raise ValueError(f"Unknown pickle format: {type(data)}")

            # Ensure we have a graph now
            if self.graph is None:
                raise ValueError("Could not extract a graph from the file.")

            # Load Course Details (Metadata merging)
            # If the input was a dict with "courses", merge those details into the graph nodes
            if isinstance(data, dict) and "courses" in data:
                count = 0
                for cid, cdata in data["courses"].items():
                    if self.graph.has_node(cid):
                        self.graph.nodes[cid].update(cdata)
                        count += 1
                logger.info(f"   Merged metadata for {count} courses.")

        except Exception as e:
            logger.error(f"CRITICAL LOAD ERROR: {e}")
            exit(1)
            
        self.original_node_count = self.graph.number_of_nodes()
        logger.info(f"✅ Loaded {self.original_node_count} nodes.")

    def run_pipeline(self, output_path):
        # 1. Filter Subjects (But keep Grad courses!)
        logger.info("\n🧹 Pre-filtering graph...")
        nodes_to_remove = []
        for n, d in self.graph.nodes(data=True):
            subject = d.get('subject', '')
            name = d.get('name', '').lower()
            
            if subject not in self.KEEP_SUBJECTS:
                nodes_to_remove.append(n)
            elif any(skip in name for skip in ['lab', 'recitation', 'seminar', 'co-op']):
                nodes_to_remove.append(n)
        
        self.graph.remove_nodes_from(nodes_to_remove)
        logger.info(f"   Filtered to {self.graph.number_of_nodes()} relevant nodes.")

        # 2. Strict Prereqs (Fixes CS2800 circular logic)
        self._enforce_prereqs()

        # 3. Tag Accessibility (Critical for Hard Mode)
        self._tag_accessibility()

        # 4. Save
        logger.info(f"\n💾 Saving to {output_path}...")
        with open(output_path, 'wb') as f:
            pickle.dump(self.graph, f)
        logger.info("   Done.")

    def _enforce_prereqs(self):
        logger.info("\n🔒 Enforcing strict prerequisite rules...")
        CORRECT = {
            "CS2800": ["CS1800"], 
            "CS3000": ["CS2510", "CS2800"],
            "CS3500": ["CS2510"],
            "CS3650": ["CS2510", "CS3000"],
            "CS4100": ["CS3000", "CS3500"],
            "DS4400": ["DS3000", "DS3500", "CS3500"]
        }
        for course, prereqs in CORRECT.items():
            if course in self.graph:
                # Clear existing
                current = list(self.graph.predecessors(course))
                for p in current: self.graph.remove_edge(p, course)
                # Add correct
                for p in prereqs:
                    if p in self.graph: self.graph.add_edge(p, course)
        
        # General Fixes (Add if missing)
        chains = [("CS1800", "CS2800"), ("CS2500", "CS2510"), ("MATH1341", "MATH1342"), ("DS2000", "DS2500")]
        for u, v in chains:
            if u in self.graph and v in self.graph and not self.graph.has_edge(u, v):
                self.graph.add_edge(u, v)

    def _tag_accessibility(self):
        logger.info("\n🏷️  Tagging undergrad accessibility...")
        count = 0
        for n, d in self.graph.nodes(data=True):
            lvl = get_course_level(n)
            is_acc = False
            
            # Rule 1: Undergrad
            if lvl < 5000: is_acc = True
            # Rule 2: Whitelist
            elif n in self.UNDERGRAD_ACCESSIBLE_GRAD: is_acc = True
            # Rule 3: Text Analysis
            elif "undergraduate" in d.get('description', '').lower(): is_acc = True
            
            self.graph.nodes[n]['undergrad_accessible'] = is_acc
            
            # Calculate Complexity while we are here
            in_d = self.graph.in_degree(n)
            out_d = self.graph.out_degree(n)
            score = (in_d * 10) + (out_d * 5) + 50
            if lvl >= 5000: score += 20
            elif lvl < 2000: score -= 10
            self.graph.nodes[n]['complexity'] = score
            
            if is_acc: count += 1
            
        logger.info(f"   Tagged {count} courses as Accessible.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True, help="Input pickle file")
    parser.add_argument('--output', default='neu_graph_clean.pkl')
    args = parser.parse_args()
    
    analyzer = CurriculumAnalyzer(args.input)
    analyzer.run_pipeline(args.output)