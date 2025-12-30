import pickle
import networkx as nx
import os
import glob
import sys
from tabulate import tabulate

def load_graph_safe(path):
    """Robust loader that handles Dicts, Graphs, and Combined formats."""
    try:
        with open(path, 'rb') as f:
            data = pickle.load(f)
            
        # Case A: It's already a Graph
        if isinstance(data, (nx.Graph, nx.DiGraph)):
            return data, "Direct Graph"
            
        # Case B: It's a Dictionary containing a graph
        if isinstance(data, dict):
            if 'graph' in data and isinstance(data['graph'], (nx.Graph, nx.DiGraph)):
                return data['graph'], "Dict['graph']"
            # Case C: It's just a course dictionary (Not a graph)
            return None, "Raw Dict (Not a Graph)"
            
        return None, f"Unknown Type: {type(data)}"
        
    except Exception as e:
        return None, f"Error: {str(e)[:50]}..."

def scan_directory(dir_path):
    print(f"🕵️  Scanning directory: {dir_path}/*.pkl\n")
    
    files = glob.glob(os.path.join(dir_path, "*.pkl"))
    results = []
    
    for file_path in files:
        filename = os.path.basename(file_path)
        G, type_desc = load_graph_safe(file_path)
        
        # --- FIX: Ensure skipped files have all keys ---
        if G is None:
            results.append({
                "File": filename,
                "Status": "❌ Skipped",
                "Nodes": 0,
                "Edges": 0,           # Was missing
                "Accessible": 0,      # Was missing
                "Access%": "N/A",
                "GradTargets": "N/A", # Was missing
                "Score": -1,
                "Object": type_desc
            })
            continue
            
        # Analyze the Graph
        total_nodes = G.number_of_nodes()
        total_edges = G.number_of_edges()
        
        # Count tags
        accessible = sum(1 for n, d in G.nodes(data=True) if d.get('undergrad_accessible') is True)
        
        # Check Hard Mode Targets
        targets = ["CS5010", "CS5700", "DS5110", "CS6120"]
        targets_found = sum(1 for t in targets if t in G and G.nodes[t].get('undergrad_accessible'))
        
        # Calculate score (simple heuristic)
        score = accessible if total_nodes > 0 else 0
        
        results.append({
            "File": filename,
            "Status": "✅ Valid",
            "Nodes": total_nodes,
            "Edges": total_edges,
            "Accessible": accessible,
            "Access%": f"{(accessible/total_nodes)*100:.1f}%" if total_nodes else "0%",
            "GradTargets": f"{targets_found}/{len(targets)}",
            "Score": score,
            "Object": type_desc
        })

    # Sort by Score descending
    results.sort(key=lambda x: x.get("Score", 0), reverse=True)
    
    return results

def print_results(results):
    headers = ["File", "Nodes", "Edges", "Accessible", "Access%", "GradTargets", "Status"]
    # Safe accessor using .get() just in case
    rows = [[r.get(h, "N/A") for h in headers] for r in results]
    
    print(tabulate(rows, headers=headers, tablefmt="github"))

    print("\n" + "="*60)
    best = next((r for r in results if r["Status"] == "✅ Valid"), None)
    
    if best:
        print(f"🏆 RECOMMENDATION: Use '{best['File']}'")
        print(f"   Reason: It has {best['Nodes']} nodes and {best['Accessible']} are accessible to the Agent.")
        
        if best["Accessible"] < 10:
            print("\n⚠️  WARNING: Even the best file has almost zero accessible courses.")
            print("   ACTION: You MUST run 'curriculum_analyzer.py' on the RAW data again.")
    else:
        print("❌ No valid graph files found.")

if __name__ == "__main__":
    scan_results = scan_directory("utils")
    print_results(scan_results)