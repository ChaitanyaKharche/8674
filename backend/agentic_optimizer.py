"""
Agentic Curriculum Optimizer - Autonomous Graph Validator & Fixer
Detects missing courses, suggests replacements, and directly patches the graph.

Usage:
    python agentic_optimizer.py --graph neu_graph_clean6.pkl --validate
    python agentic_optimizer.py --graph neu_graph_clean6.pkl --fix --output neu_graph_fixed.pkl
"""
import pickle
import json
import re
import argparse
import networkx as nx
from typing import Dict, Set, List, Tuple, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

@dataclass
class CourseChange:
    """Detected change in course catalog"""
    old_code: str
    new_code: str = None
    status: str = "missing"  # missing, renamed, moved, deprecated
    replacement_suggestion: str = None
    confidence: float = 0.0
    evidence: str = ""

class AgenticOptimizer:
    """
    Autonomous agent that validates requirements AND fixes graph automatically
    """
    
    # Requirements synced with curriculum_optimizer.py
    CONCENTRATION_REQUIREMENTS = {
        "ai_ml": {
            "foundations": {
                "required": ["CS1800", "CS2500", "CS2510", "CS2800"],
            },
            "core": {
                "required": ["CS3000", "CS3500"],
                "pick_1_from": ["CS3200", "CS3650", "CS5700"]  # FIXED: CS3700 → CS5700
            },
            "concentration_specific": {
                "required": ["CS4100", "DS4400"],
                "pick_2_from": ["CS4120", "CS4180", "DS4420", "DS4440"],
                "pick_1_systems": ["CS4730", "CS4700"]  # REMOVED: CS4750 (doesn't exist)
            },
            "math": {
                "required": ["MATH1341", "MATH1342"],
                "pick_1_from": ["MATH2331", "MATH3081"]  # REMOVED: STAT3150
            }
        },
        "systems": {
            "foundations": {
                "required": ["CS1800", "CS2500", "CS2510", "CS2800"]
            },
            "core": {
                "required": ["CS3000", "CS3500", "CS3650"],
                "pick_1_from": ["CS5700", "CS3200"]  # FIXED: CS3700 → CS5700
            },
            "concentration_specific": {
                "required": ["CS4700"],
                "pick_2_from": ["CS4730"],  # REMOVED: CS4750, CS4770
                "pick_1_from": ["CS4400", "CS4500", "CS4520"]
            },
            "math": {
                "required": ["MATH1341", "MATH1342"]
            }
        },
        "security": {
            "foundations": {
                "required": ["CS1800", "CS2500", "CS2510", "CS2800"]
            },
            "core": {
                "required": ["CS3000", "CS3650", "CY2550"],
                "pick_1_from": ["CS5700", "CS3500"]  # FIXED: CS3700 → CS5700
            },
            "concentration_specific": {
                "required": ["CY3740"],
                "pick_2_from": ["CY4740", "CY4760", "CY4770"],  # CY4770 (moved from CS)
                "pick_1_from": ["CS4700", "CS4730"]
            },
            "math": {
                "required": ["MATH1342"],
                "pick_1_from": ["MATH3527", "MATH3081"]
            }
        }
    }
    
    # Known manual additions for courses that don't appear in scraper
    MANUAL_COURSES = {
        "CS5700": {
            "name": "Fundamentals of Networks",
            "subject": "CS",
            "classId": "5700",
            "description": "Networks and distributed systems (grad level, no prereqs)",
            "minCredits": 4,
            "maxCredits": 4,
            "prerequisites": []  # Open to undergrads
        },
        "CY4770": {
            "name": "Foundations of Cryptography",
            "subject": "CY",
            "classId": "4770",
            "description": "Mathematical cryptography (moved from CS dept)",
            "minCredits": 4,
            "maxCredits": 4,
            "prerequisites": ["CS3000"]  # Simplified prereq
        }
    }
    
    def __init__(self, graph_path: str, use_llm: bool = True):
        self.graph_path = graph_path
        self.use_llm = use_llm
        self.graph = None
        self.courses = {}
        self.changes = []
        
        # Load LLM if needed
        self.llm = None
        self.tokenizer = None
        if use_llm:
            self._load_llm()
    
    def _load_llm(self):
        """Load local LLM for intelligent validation"""
        print("🤖 Loading LLM for catalog analysis...")
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        if device.type == 'cuda':
            model_name = "meta-llama/Llama-3.1-8B-Instruct"
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )
            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.llm = AutoModelForCausalLM.from_pretrained(
                model_name,
                quantization_config=quant_config,
                device_map="auto"
            )
            print("✅ LLM loaded")
        else:
            print("⚠️  No GPU available, LLM disabled")
            self.use_llm = False
    
    def load_graph(self):
        """Load curriculum graph"""
        print(f"📚 Loading graph: {self.graph_path}")
        with open(self.graph_path, 'rb') as f:
            self.graph = pickle.load(f)
        self.courses = dict(self.graph.nodes(data=True))
        print(f"✅ Loaded {len(self.courses)} courses")
    
    def validate_requirements(self) -> Dict[str, List[CourseChange]]:
        """Check which required courses are missing from graph"""
        print("\n🔍 Validating CONCENTRATION_REQUIREMENTS against graph...")
        
        track_changes = {}
        
        for track, track_reqs in self.CONCENTRATION_REQUIREMENTS.items():
            print(f"\n📋 Checking {track} track:")
            track_changes[track] = []
            
            for category, reqs in track_reqs.items():
                if not isinstance(reqs, dict):
                    continue
                
                for key, courses in reqs.items():
                    if not isinstance(courses, list):
                        continue
                    
                    for course in courses:
                        if course not in self.courses:
                            change = CourseChange(
                                old_code=course,
                                status="missing",
                                evidence=f"Not found in scraped graph ({len(self.courses)} courses)"
                            )
                            track_changes[track].append(change)
                            print(f"  ❌ {course} - MISSING")
                        else:
                            print(f"  ✅ {course}")
        
        return track_changes
    
    def find_replacements(self, changes: Dict[str, List[CourseChange]]) -> Dict[str, List[CourseChange]]:
        """Use pattern matching + LLM to suggest replacements"""
        print("\n🤖 Analyzing missing courses...")
        
        for track, track_changes in changes.items():
            for change in track_changes:
                if change.status != "missing":
                    continue
                
                # Try pattern matching first (instant)
                replacement = self._pattern_match_replacement(change.old_code)
                if replacement:
                    change.new_code = replacement
                    change.status = "renamed"
                    change.confidence = 0.7
                    change.evidence = "Pattern matching"
                    print(f"  🔄 {change.old_code} → {replacement} (pattern)")
                    continue
                
                # Check manual course database
                if change.old_code in self.MANUAL_COURSES:
                    change.new_code = change.old_code  # Will be added to graph
                    change.status = "manual_add"
                    change.confidence = 1.0
                    change.evidence = "Manual course database"
                    print(f"  ➕ {change.old_code} - Will be added manually")
                    continue
                
                # Use LLM for ambiguous cases
                if self.use_llm and self.llm:
                    replacement = self._llm_suggest_replacement(change.old_code, track)
                    if replacement:
                        change.new_code = replacement
                        change.status = "renamed"
                        change.confidence = 0.9
                        change.evidence = "LLM analysis"
                        print(f"  🔄 {change.old_code} → {replacement} (LLM)")
                else:
                    print(f"  ⚠️  {change.old_code} - No replacement found")
        
        return changes
    
    def _pattern_match_replacement(self, course_code: str) -> Optional[str]:
        """Fast pattern-based replacement detection"""
        
        # Known replacements from manual verification
        known_replacements = {
            "CS3700": "CS5700",
            "CS4770": "CY4770",
            "STAT3150": "MATH3081",
        }
        
        if course_code in known_replacements:
            if known_replacements[course_code] in self.courses:
                return known_replacements[course_code]
        
        # Try subject swap (CS ↔ CY)
        if course_code.startswith("CS"):
            alt_code = "CY" + course_code[2:]
            if alt_code in self.courses:
                return alt_code
        elif course_code.startswith("CY"):
            alt_code = "CS" + course_code[2:]
            if alt_code in self.courses:
                return alt_code
        
        # Try grad-level version (3XXX/4XXX → 5XXX)
        match = re.match(r'([A-Z]+)(\d)(\d{3})', course_code)
        if match:
            subject, first_digit, rest = match.groups()
            if first_digit in ['3', '4']:
                grad_code = f"{subject}5{rest}"
                if grad_code in self.courses:
                    return grad_code
        
        return None
    
    def _llm_suggest_replacement(self, missing_course: str, track: str) -> Optional[str]:
        """Use LLM to intelligently suggest replacement"""
        
        subject = re.match(r'([A-Z]+)', missing_course).group(1)
        similar_courses = [
            (cid, data.get('name', ''))
            for cid, data in self.courses.items()
            if cid.startswith(subject) and cid != missing_course
        ][:10]
        
        course_list = "\n".join([f"- {cid}: {name}" for cid, name in similar_courses])
        
        prompt = f"""Course catalog expert analyzing NEU curriculum changes.

**Missing:** {missing_course}
**Track:** {track}

**Available courses:**
{course_list}

Which course replaced {missing_course}? Return ONLY the code or "NONE".

Rules:
- Networks: CS3700 → CS5700
- Crypto: CS → CY dept
- STAT → MATH
- Game courses often don't exist
"""
        
        try:
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to(self.llm.device)
            with torch.no_grad():
                outputs = self.llm.generate(
                    **inputs,
                    max_new_tokens=50,
                    temperature=0.1,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )
            response = self.tokenizer.decode(outputs[0][len(inputs['input_ids'][0]):], skip_special_tokens=True).strip()
            
            match = re.search(r'([A-Z]{2,4}\d{4})', response)
            if match:
                suggested = match.group(1)
                if suggested in self.courses:
                    return suggested
        
        except Exception as e:
            print(f"  ⚠️  LLM error: {e}")
        
        return None
    
    def fix_graph(self, changes: Dict[str, List[CourseChange]]) -> int:
        """Directly add missing courses to the graph"""
        print("\n🔧 Fixing graph by adding missing courses...")
        
        added_count = 0
        
        for track, track_changes in changes.items():
            for change in track_changes:
                if change.status == "manual_add" and change.old_code in self.MANUAL_COURSES:
                    course_data = self.MANUAL_COURSES[change.old_code]
                    cid = change.old_code
                    
                    # Add node
                    self.graph.add_node(cid, **course_data)
                    self.courses[cid] = course_data
                    
                    # Add prerequisite edges
                    for prereq in course_data.get("prerequisites", []):
                        if prereq in self.graph:
                            self.graph.add_edge(prereq, cid, relationship="prerequisite")
                        else:
                            print(f"    ⚠️  Prereq {prereq} for {cid} not in graph")
                    
                    print(f"  ✅ Added {cid}: {course_data['name']}")
                    added_count += 1
        
        return added_count
    
    def save_report(self, changes: Dict[str, List[CourseChange]], output_path: str = None):
        """Save validation report"""
        if not output_path:
            output_path = f"catalog_validation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        report = {
            "timestamp": datetime.now().isoformat(),
            "graph_file": self.graph_path,
            "total_courses_in_graph": len(self.courses),
            "changes": {
                track: [asdict(c) for c in track_changes]
                for track, track_changes in changes.items()
            }
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"\n💾 Report saved: {output_path}")
    
    def save_graph(self, output_path: str):
        """Save the fixed graph"""
        with open(output_path, 'wb') as f:
            pickle.dump(self.graph, f)
        print(f"💾 Fixed graph saved: {output_path}")
        print(f"📊 Final graph: {self.graph.number_of_nodes()} courses, {self.graph.number_of_edges()} edges")
    
    def run(self, fix: bool = False, output: str = None):
        """Main agent workflow"""
        print("="*70)
        print("AGENTIC OPTIMIZER - Autonomous Graph Validator & Fixer")
        print("="*70)
        
        # Step 1: Load data
        self.load_graph()
        
        # Step 2: Validate requirements
        changes = self.validate_requirements()
        
        # Count issues
        total_missing = sum(len(c) for c in changes.values())
        if total_missing == 0:
            print("\n✅ All requirements valid! No changes needed.")
            return
        
        print(f"\n⚠️  Found {total_missing} missing courses across all tracks")
        
        # Step 3: Find replacements
        changes = self.find_replacements(changes)
        
        # Step 4: Generate report
        self.save_report(changes)
        
        # Step 5: Fix graph if requested
        if fix:
            added = self.fix_graph(changes)
            
            if added > 0:
                print(f"\n✅ Added {added} courses to graph")
                
                if output:
                    self.save_graph(output)
                else:
                    # Default output name
                    default_output = self.graph_path.replace('.pkl', '_fixed.pkl')
                    self.save_graph(default_output)
            else:
                print("\n⚠️  No courses added (all issues are renamings, not missing)")
        
        print("\n✨ Optimization complete!")


def main():
    parser = argparse.ArgumentParser(description="Agentic Optimizer - Auto-validate & fix curriculum graph")
    parser.add_argument('--graph', required=True, help="Path to curriculum graph .pkl")
    parser.add_argument('--validate', action='store_true', help="Only validate, don't fix")
    parser.add_argument('--fix', action='store_true', help="Fix graph by adding missing courses")
    parser.add_argument('--output', help="Output path for fixed graph")
    parser.add_argument('--no-llm', action='store_true', help="Disable LLM (use pattern matching only)")
    
    args = parser.parse_args()
    
    agent = AgenticOptimizer(
        graph_path=args.graph,
        use_llm=not args.no_llm
    )
    
    agent.run(
        fix=args.fix,
        output=args.output
    )


if __name__ == "__main__":
    main()