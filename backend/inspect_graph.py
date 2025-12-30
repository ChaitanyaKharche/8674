#!/usr/bin/env python3
"""
Comprehensive Graph Data Inspector
Diagnoses all potential issues with the curriculum graph data
"""
import pickle
import networkx as nx
from collections import defaultdict
import sys

def inspect_graph_thoroughly(graph_file):
    """Complete inspection of curriculum graph data"""
    
    print("=" * 70)
    print("COMPREHENSIVE CURRICULUM GRAPH INSPECTION")
    print("=" * 70)
    
    # Load the graph
    try:
        with open(graph_file, 'rb') as f:
            graph = pickle.load(f)
    except Exception as e:
        print(f"❌ ERROR: Could not load graph: {e}")
        return
    
    print(f"\n📊 BASIC STATS:")
    print(f"  Total nodes: {graph.number_of_nodes()}")
    print(f"  Total edges: {graph.number_of_edges()}")
    
    # 1. CHECK SUBJECT DISTRIBUTION
    print("\n📚 SUBJECT ANALYSIS:")
    subject_counts = defaultdict(int)
    courses_by_subject = defaultdict(list)
    
    for node, data in graph.nodes(data=True):
        subject = data.get('subject', 'UNKNOWN')
        subject_counts[subject] += 1
        courses_by_subject[subject].append(node)
    
    # Categorize subjects
    CS_RELEVANT = {"CS", "DS", "IS", "CY", "MATH", "PHYS", "ENGW", "STAT", "EECE"}
    MAYBE_RELEVANT = {"CHEM", "BIOL", "PSYC", "PHIL", "ECON"}
    
    print("\n  Relevant CS Subjects:")
    for subj in sorted(CS_RELEVANT):
        count = subject_counts.get(subj, 0)
        if count > 0:
            sample = courses_by_subject[subj][:3]
            print(f"    ✅ {subj:8s}: {count:3d} courses (e.g., {', '.join(sample)})")
        else:
            print(f"    ❌ {subj:8s}: 0 courses - MISSING!")
    
    print("\n  Irrelevant Subjects (should be removed):")
    irrelevant_found = False
    for subj, count in sorted(subject_counts.items()):
        if subj not in CS_RELEVANT and subj not in MAYBE_RELEVANT and count > 0:
            irrelevant_found = True
            sample = courses_by_subject[subj][:3]
            print(f"    ❌ {subj:8s}: {count:3d} courses (e.g., {', '.join(sample)})")
    
    if not irrelevant_found:
        print("    ✅ None found - graph is clean!")
    
    # 2. CHECK CRITICAL COURSES EXISTENCE
    print("\n🎯 CRITICAL COURSES CHECK:")
    
    # Foundation courses
    foundation_courses = ["CS1800", "CS2500", "CS2510", "CS2800"]
    print("\n  Foundation Courses:")
    for course in foundation_courses:
        if course in graph:
            data = graph.nodes[course]
            print(f"    ✅ {course}: {data.get('name', 'Unknown')}")
        else:
            print(f"    ❌ {course}: MISSING!")
    
    # Core CS courses
    core_courses = ["CS3000", "CS3500", "CS3650", "CS3700", "CS3200"]
    print("\n  Core CS Courses:")
    for course in core_courses:
        if course in graph:
            data = graph.nodes[course]
            print(f"    ✅ {course}: {data.get('name', 'Unknown')}")
        else:
            print(f"    ❌ {course}: MISSING!")
    
    # AI/ML concentration courses
    ai_ml_courses = ["CS4100", "DS4400", "CS4120", "DS4420", "CS4180", "DS4440"]
    print("\n  AI/ML Concentration:")
    missing_concentration = []
    for course in ai_ml_courses:
        if course in graph:
            data = graph.nodes[course]
            print(f"    ✅ {course}: {data.get('name', 'Unknown')}")
        else:
            missing_concentration.append(course)
            print(f"    ❌ {course}: MISSING!")
    
    # 3. CHECK PREREQUISITE CHAINS
    print("\n🔗 PREREQUISITE CHAINS:")
    
    critical_chains = [
        ("CS1800", "CS2800", "Discrete Structures → Logic"),
        ("CS2500", "CS2510", "Fundies 1 → Fundies 2"),
        ("CS2510", "CS3500", "Fundies 2 → OOD"),
        ("CS2510", "CS3000", "Fundies 2 → Algorithms"),
        ("MATH1341", "MATH1342", "Calc 1 → Calc 2"),
        ("DS2000", "DS2500", "Prog w/ Data → Intermediate"),
        ("DS2500", "DS3500", "Intermediate → Advanced")
    ]
    
    broken_chains = []
    for prereq, course, desc in critical_chains:
        if prereq in graph and course in graph:
            if graph.has_edge(prereq, course):
                print(f"    ✅ {prereq} → {course} ({desc})")
            else:
                broken_chains.append((prereq, course))
                print(f"    ❌ {prereq} → {course} ({desc}) - EDGE MISSING!")
        else:
            if prereq not in graph:
                print(f"    ⚠️  {prereq} → {course} - {prereq} doesn't exist")
            if course not in graph:
                print(f"    ⚠️  {prereq} → {course} - {course} doesn't exist")
    
    # 4. CS2800 SPECIFIC DIAGNOSIS
    print("\n🔍 CS2800 DETAILED ANALYSIS:")
    
    if "CS2800" in graph:
        cs2800_data = graph.nodes["CS2800"]
        print(f"  ✅ CS2800 exists")
        print(f"     Name: {cs2800_data.get('name', 'Unknown')}")
        print(f"     Subject: {cs2800_data.get('subject', 'Unknown')}")
        print(f"     Credits: {cs2800_data.get('maxCredits', 'Unknown')}")
        
        # Check prerequisites
        prereqs = list(graph.predecessors("CS2800"))
        print(f"     Prerequisites: {prereqs if prereqs else 'NONE (this is wrong!)'}")
        
        # What it unlocks
        unlocks = list(graph.successors("CS2800"))[:5]
        print(f"     Unlocks: {unlocks if unlocks else 'Nothing (suspicious...)'}")
        
        # Specific CS1800 connection
        if "CS1800" in graph:
            if graph.has_edge("CS1800", "CS2800"):
                print(f"     ✅ CS1800 → CS2800 connection exists")
            else:
                print(f"     ❌ CS1800 → CS2800 connection MISSING!")
    else:
        print(f"  ❌ CS2800 is completely MISSING from the graph!")
    
    # 5. CHECK FOR DUPLICATE/REDUNDANT COURSES
    print("\n🔄 CHECKING FOR REDUNDANT COURSES:")
    
    calc_variants = ["MATH1341", "MATH1241", "MATH1231", "MATH1340"]
    physics_variants = ["PHYS1151", "PHYS1161", "PHYS1145"]
    
    print("\n  Calculus variants in graph:")
    calc_found = [c for c in calc_variants if c in graph]
    if len(calc_found) > 1:
        print(f"    ⚠️  Multiple calculus courses found: {calc_found}")
        print(f"       These satisfy the same requirement - graph needs deduplication")
    else:
        print(f"    ✅ Only one variant: {calc_found}")
    
    print("\n  Physics variants in graph:")
    phys_found = [c for c in physics_variants if c in graph]
    if len(phys_found) > 1:
        print(f"    ⚠️  Multiple physics courses found: {phys_found}")
    else:
        print(f"    ✅ Only one variant: {phys_found}")
    
    # 6. CHECK FOR LABS/RECITATIONS
    print("\n🧪 CHECKING FOR LABS/RECITATIONS (should be removed):")
    
    labs_found = []
    for node, data in graph.nodes(data=True):
        name = data.get('name', '').lower()
        if any(word in name for word in ['lab', 'recitation', 'seminar', 'practicum']):
            labs_found.append((node, data.get('name', node)))
    
    if labs_found:
        print(f"  ❌ Found {len(labs_found)} lab/recitation courses:")
        for course_id, name in labs_found[:5]:
            print(f"     - {course_id}: {name}")
    else:
        print(f"  ✅ No labs/recitations found")
    
    # 7. CHECK 4000-LEVEL COURSES
    print("\n🎓 4000-LEVEL COURSES:")
    
    cs4000_courses = [n for n in graph.nodes() if n.startswith("CS4")]
    ds4000_courses = [n for n in graph.nodes() if n.startswith("DS4")]
    
    print(f"  CS 4000-level: {len(cs4000_courses)} courses")
    if cs4000_courses:
        print(f"    Examples: {', '.join(cs4000_courses[:5])}")
    else:
        print(f"    ❌ NO CS 4000-level courses found!")
        
    print(f"  DS 4000-level: {len(ds4000_courses)} courses")
    if ds4000_courses:
        print(f"    Examples: {', '.join(ds4000_courses[:5])}")
    else:
        print(f"    ❌ NO DS 4000-level courses found!")
    
    # FINAL VERDICT
    print("\n" + "=" * 70)
    print("VERDICT:")
    print("=" * 70)
    
    issues = []
    
    if irrelevant_found:
        issues.append("Contains irrelevant subjects (ARTH, FRNH, etc.)")
    
    if missing_concentration:
        issues.append(f"Missing critical courses: {', '.join(missing_concentration)}")
    
    if broken_chains:
        issues.append(f"Broken prerequisite chains: {len(broken_chains)}")
    
    if not cs4000_courses or not ds4000_courses:
        issues.append("Missing 4000-level courses")
    
    if labs_found:
        issues.append(f"Contains {len(labs_found)} lab/recitation courses")
    
    if issues:
        print("❌ GRAPH HAS ISSUES:")
        for i, issue in enumerate(issues, 1):
            print(f"   {i}. {issue}")
        
        print("\n📋 RECOMMENDED ACTIONS:")
        print("1. Re-scrape with more subjects: CS DS IS CY MATH PHYS STAT EECE")
        print("2. Re-run analyzer with stricter filtering")
        print("3. Manually add missing prerequisite edges if needed")
    else:
        print("✅ Graph appears to be clean and complete!")

def suggest_fix_commands(graph_file):
    """Suggest specific commands to fix issues"""
    
    print("\n" + "=" * 70)
    print("FIX COMMANDS:")
    print("=" * 70)
    
    print("\n1️⃣ If courses are missing, re-scrape with expanded subjects:")
    print("   python neu_scraper.py --term 202510 --subjects CS DS IS CY MATH PHYS STAT EECE --prefix neu_complete")
    
    print("\n2️⃣ Clean the new data:")
    print("   python curriculum_analyzer.py --graph neu_complete_graph_*.pkl --courses neu_complete_courses_*.pkl --output-graph neu_graph_ultra_clean.pkl")
    
    print("\n3️⃣ Test the cleaned data:")
    print(f"   python {sys.argv[0]} neu_graph_ultra_clean.pkl")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python inspect_graph.py <graph.pkl>")
        print("Example: python inspect_graph.py neu_graph_clean3.pkl")
    else:
        graph_file = sys.argv[1]
        inspect_graph_thoroughly(graph_file)
        suggest_fix_commands(graph_file)