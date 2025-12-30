"""
Curriculum Optimizer - PRODUCTION VERSION
All redundant code removed, all critical issues fixed
"""
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from sentence_transformers import SentenceTransformer, util
import networkx as nx
import numpy as np
from typing import Dict, List, Set, Optional
from dataclasses import dataclass
import re
from datetime import datetime
import itertools
import collections


@dataclass
class StudentProfile:
    completed_courses: List[str]
    time_commitment: int
    preferred_difficulty: str
    career_goals: str
    interests: List[str]
    current_gpa: float = 3.5
    learning_style: str = "Visual"

class HybridOptimizer:
    
    EQUIVALENCY_GROUPS = [
        {"MATH1341", "MATH1241", "MATH1231"},
        {"MATH1342", "MATH1242"},
        {"PHYS1151", "PHYS1161", "PHYS1145"},
        {"PHYS1155", "PHYS1165", "PHYS1147"},
    ]
    
    COURSE_TRACKS = {
        "physics": {
            "engineering": ["PHYS1151", "PHYS1155"],
            "science": ["PHYS1161", "PHYS1165"], 
            "life_sciences": ["PHYS1145", "PHYS1147"]
        },
        "calculus": {
            "standard": ["MATH1341", "MATH1342"],
            "computational": ["MATH156", "MATH256"]
        }
    }
    
    CONCENTRATION_REQUIREMENTS = {
        "general": {
            "foundations": {
                "required": ["CS1800", "CS2500", "CS2510", "CS2800"],
            },
            "core": {
                "required": ["CS3000", "CS3500"],
                # Moved Systems/Database to choices
                "pick_2_core": ["CS3650", "CS3200", "CS5700", "CS5010"] 
            },
            "concentration_specific": {
                "required": ["CS4100"], 
                # HUGE POOL of electives so it doesn't run out of courses
                "pick_5_electives": [
                    "CS4550", "CS4530", "CS4400", "CS4700", "CS4730", 
                    "CS4120", "CS4180", "DS3000", "DS4400", "IS4200", 
                    "IS4300", "CS3540", "CS4520", "CY3740", "DS4200"
                ]
            },
            "math": {
                "required": ["MATH1341", "MATH1342"],
                "pick_1_from": ["MATH2331", "MATH3081"]
            }
        },
        # --- NEW GAME DEV TRACK DEFINITION (based on your AI/ML base) ---
        "game_dev": {
            "foundations": {
                "required": ["CS1800", "CS2500", "CS2510", "CS2800"],
            },
            "core": {
                "required": ["CS3000", "CS3500"],
                "pick_1_from": ["CS3200", "CS3650", "CS5700"]
            },
            "concentration_specific": {
                "required": ["CS3540"], # Game Programming
                "pick_2_from": ["CS4100", "CS4520", "CS4300", "CS4700"], # AI, Graphics, HCI, Systems
                "pick_1_electives": ["CS4180", "CS4550"] # Related topics
            },
            "math": {
                "required": ["MATH1341", "MATH1342"],
                "pick_1_from": ["MATH2331", "MATH3081"]
            }
        },
        "ai_ml": {
            "foundations": {
                "required": ["CS1800", "CS2500", "CS2510", "CS2800"],
                "sequence": True
            },
            "core": {
                "required": ["CS3000", "CS3500"],
                "pick_1_from": ["CS3200", "CS3650", "CS5700"]
            },
            "concentration_specific": {
                "required": ["CS4100", "DS4400"],
                "pick_2_from": ["CS4120", "CS4180", "DS4420", "DS4440"],
                "pick_1_systems": ["CS4730", "CS4700"]
            },
            "math": {
                "required": ["MATH1341", "MATH1342"],
                "pick_1_from": ["MATH2331", "MATH3081"]
            }
        },
        "systems": {
            "foundations": {"required": ["CS1800", "CS2500", "CS2510", "CS2800"]},
            "core": {"required": ["CS3000", "CS3500", "CS3650"], "pick_1_from": ["CS5700", "CS3200"]},
            "concentration_specific": {"required": ["CS4700"], "pick_2_from": ["CS4730"], "pick_1_from": ["CS4400", "CS4500", "CS4520"]},
            "math": {"required": ["MATH1341", "MATH1342"]}
        },
        "security": {
            "foundations": {"required": ["CS1800", "CS2500", "CS2510", "CS2800"]},
            "core": {"required": ["CS3000", "CS3650", "CY2550"], "pick_1_from": ["CS5700", "CS3500"]},
            "concentration_specific": {"required": ["CY3740"], "pick_2_from": ["CY4740", "CY4760", "CY4770"], "pick_1_from": ["CS4700", "CS4730"]},
            "math": {"required": ["MATH1342"], "pick_1_from": ["MATH3527", "MATH3081"]}
        }
    }
    
    def __init__(self):
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_name = "meta-llama/Llama-3.1-8B-Instruct"
        self.embedding_model_name = 'BAAI/bge-large-en-v1.5'
        self.llm = None
        self.tokenizer = None
        self.embedding_model = None
        self.curriculum_graph = None
        self.courses = {}
        self.current_student = None
        self.rmp_service = None
    def load_models(self):
        print("Loading embedding model...")
        self.embedding_model = SentenceTransformer(self.embedding_model_name, device=self.device)
        
    def load_llm(self):
        if self.device.type == 'cuda' and self.llm is None:
            print("Loading LLM for intelligent planning...")
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_compute_dtype=torch.bfloat16
            )
            self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
            self.tokenizer.pad_token = self.tokenizer.eos_token
            self.llm = AutoModelForCausalLM.from_pretrained(
                self.model_name,
                quantization_config=quant_config,
                device_map="auto"
            )
            
    def load_data(self, graph: nx.DiGraph):
        self.curriculum_graph = graph
        self.courses = dict(graph.nodes(data=True))
        UNDERGRAD_ACCESSIBLE_GRAD = {"CS5700", "CY5700", "DS5110", "CS5010"}
        self.valid_courses = []
        try:
            from rmp_service import RateMyProfService
            self.rmp_service = RateMyProfService()
            print("✓ RMP service initialized for professor difficulty ratings")
        except ImportError:
            print("⚠ RMP service not available - using base difficulty scoring")
            self.rmp_service = None
        course_texts = []
        
        concentration_courses = set()
        for track_reqs in self.CONCENTRATION_REQUIREMENTS.values():
            for category, reqs in track_reqs.items():
                if isinstance(reqs, dict):
                    for key, courses in reqs.items():
                        if isinstance(courses, list):
                            concentration_courses.update(courses)
        
        for cid, data in self.courses.items():
            name = data.get('name', '')
            if not name or 'lab' in name.lower() or 'recitation' in name.lower():
                continue
            
            course_level = self._get_level(cid)
            if course_level >= 5000 and cid not in UNDERGRAD_ACCESSIBLE_GRAD:
                continue
                
            self.valid_courses.append(cid)
            course_texts.append(f"{name} {data.get('description', '')}")
        
        missing_required = concentration_courses - set(self.valid_courses)
        if missing_required:
            print(f"\n⚠️ WARNING: {len(missing_required)} required courses missing from graph: {sorted(missing_required)}\n")

        print(f"Computing embeddings for {len(self.valid_courses)} courses...")
        self.course_embeddings = self.embedding_model.encode(course_texts, convert_to_tensor=True, show_progress_bar=True)
        print(f"\nTotal valid courses: {len(self.valid_courses)}")

    def _get_level(self, course_id: str) -> int:
        match = re.search(r'\d+', course_id)
        return int(match.group()) if match else 9999

    def _get_completed_with_equivalents(self, completed: Set[str]) -> Set[str]:
        expanded_completed = completed.copy()
        for course in completed:
            for group in self.EQUIVALENCY_GROUPS:
                if course in group:
                    expanded_completed.update(group)
        return expanded_completed

    def _can_take_course(self, course_id: str, completed: Set[str]) -> bool:
        effective_completed = self._get_completed_with_equivalents(completed)
        if course_id not in self.curriculum_graph:
            return True
        prereqs = set(self.curriculum_graph.predecessors(course_id))
        return prereqs.issubset(effective_completed)

    def _validate_sequence(self, selected: List[str], candidate: str) -> bool:
        for track_type, tracks in self.COURSE_TRACKS.items():
            for track_name, sequence in tracks.items():
                if candidate in sequence:
                    for other_track, other_seq in tracks.items():
                        if other_track != track_name and any(c in selected for c in other_seq):
                            return False
        return True
        
        
    
    def _get_course_difficulty_score(self, course_id: str) -> float:
        if course_id not in self.courses:
            return 50
        
        course = self.courses[course_id]
        
        # Base complexity from scraping (default 50)
        base_complexity = course.get("complexity", 50)
        
        # Heuristic adjustment:
        # 1. 1000-level courses are easier (subtract 20)
        # 2. 4000/5000+ level courses are harder (add 20)
        # 3. Higher credits = harder
        
        level = 0
        import re
        match = re.search(r'(\d)', course_id) # Find first digit
        if match:
            level = int(match.group(1)) * 1000
            
        heuristic_score = 50
        if level < 2000: heuristic_score = 30
        elif level >= 5000: heuristic_score = 80
        elif level >= 4000: heuristic_score = 70
        
        # Adjust by credits (standard is 4)
        credits = course.get("maxCredits", 4)
        if credits > 4: heuristic_score += 10
        if credits < 4: heuristic_score -= 10
        
        return heuristic_score

    
    
    def _score_course(self, course_id: str, semantic_scores: Dict[str, float], required_set: Set[str], picklist_set: Set[str], year: int, track: str) -> float:
        if course_id not in self.courses: return -10000.0
        
        course_data = self.courses[course_id]
        subject = course_data.get('subject', '').strip().upper() 
        name = course_data.get('name', '').lower()
        level = self._get_level(course_id)
        
        score = 0.0
        
        # --- 1. BASE SCORES ---
        score += semantic_scores.get(course_id, 0.0) * 5.0
        
        if course_id in required_set: score += 20000.0
        if course_id in picklist_set: score += 10000.0

        # --- 2. COMMON SENSE RULES (The Fix) ---
        
        # RULE: No Intro/Freshman courses in Year 3 or 4
        # (Fixes the CS1100 / ENGW1102 in Year 4 bug)
        if year >= 3:
            if level < 2000: score -= 50000.0
            if subject == "ENGW": score -= 50000.0
            
        # RULE: No CS1100 for CS Majors (It's for non-majors)
        if course_id == "CS1100": score -= 50000.0

        # --- 3. DIFFICULTY TUNING ---
        diff_pref = self.current_student.preferred_difficulty.lower() if self.current_student else "moderate"

        # === EASY MODE ===
        if diff_pref == "easy":
            # BAN Graduate Courses (5000+)
            if level >= 5000: score -= 20000.0
            
            # PREFER Web/Game/Social electives (known easier)
            if any(k in name for k in ['web', 'game', 'social', 'human']):
                score += 5000.0
                
            # PREFER Lower Level Electives (3000s over 4000s)
            if 3000 <= level < 4000: score += 2000.0

        # === HARD MODE ===
        elif diff_pref == "challenging":
            # BOOST Graduate Courses
            if level >= 5000 and subject in ["CS", "DS"]: score += 15000.0
            
            # PENALIZE "Fluff"
            if any(k in name for k in ['social', 'intro', 'fundamental']):
                score -= 2000.0

        # --- 4. DATA DRIVEN RMP (Keep this) ---
        if hasattr(self, 'rmp_service') and self.rmp_service:
            try:
                profs = course_data.get('professors', [])
                if profs:
                    diffs = [self.rmp_service.get_professor_difficulty(p)['difficulty'] for p in profs]
                    avg_diff = sum(diffs) / len(diffs)
                    
                    if diff_pref == "easy":
                        if avg_diff > 3.8: score -= 5000.0
                        elif avg_diff < 2.5: score += 5000.0
                    elif diff_pref == "challenging":
                        if avg_diff > 3.5: score += 5000.0
            except: pass

        # Level progression (Standard)
        score -= (level / 100.0)
        
        return score



    def generate_simple_plan(self, student: StudentProfile, track_override: Optional[str] = None) -> Dict:
        print("--- Generating Enhanced Rule-Based Plan ---")
        self.current_student = student
        return self.generate_enhanced_rule_plan(student, track_override)
        
    def generate_enhanced_rule_plan(self, student: StudentProfile, track_override: Optional[str] = None) -> Dict:
        self.current_student = student
        
        # --- FIX: Logic corrected to respect "general" override ---
        if track_override:
            track = track_override
            print(f"--- Using user-selected track: {track} ---")
        else:
            track = self._identify_track(student)
            print(f"--- Auto-identified track: {track} ---")
            if not track:
                track = "general"
        
        plan = self._build_structured_plan(student, track, None)
        validation = self.validate_plan(plan, student)
        
        if validation["errors"]:
            plan = self._fix_plan_errors(plan, validation, student)
            validation = self.validate_plan(plan, student)
        
        difficulty_level = self._map_difficulty(student.preferred_difficulty)
        courses_per_semester = self._calculate_course_load(student.time_commitment)
        
        track_name = track.replace("_", " ").title()
        explanation = f"Personalized {track_name} track ({difficulty_level} difficulty, {courses_per_semester} courses/semester)"
        
        return self._finalize_plan(plan, explanation, validation)

    def generate_llm_plan(self, student: StudentProfile, track_override: Optional[str] = None) -> Dict:
        print("--- Generating AI-Optimized Plan ---")
        self.current_student = student
        self.load_llm()
        if not self.llm:
            return self.generate_enhanced_rule_plan(student, track_override) # Pass override
        
        # --- FIX: Use override if provided, otherwise identify ---
        if track_override and track_override != "general":
            track = track_override
            print(f"--- Using user-selected track: {track} ---")
        else:
            track = self._identify_track(student)
            print(f"--- Auto-identified track: {track} ---")
            if not track:
                track = "general"
        
        llm_suggestions = self._get_llm_course_suggestions(student, track)
        plan = self._build_structured_plan(student, track, llm_suggestions)
        validation = self.validate_plan(plan, student)
        if validation["errors"]:
            plan = self._fix_plan_errors(plan, validation, student)
            validation = self.validate_plan(plan, student)
        
        track_name = track.replace("_", " ").title()
        explanation = self._generate_explanation(student, plan, track, f"AI-optimized {track_name}")
        return self._finalize_plan(plan, explanation, validation)

    
    def generate_all_valid_plans(self, track: str) -> List[Set[str]]:
        """
        Generates all valid course-set combinations for a given track.
        """
        if track not in self.CONCENTRATION_REQUIREMENTS:
            print(f"Warning: Track '{track}' not found. Defaulting to 'general'.")
            track = "general"
            
        track_reqs = self.CONCENTRATION_REQUIREMENTS[track]
        
        base_required = set()
        choice_blocks = [] # This will be a list of lists of sets

        # 1. Parse all requirements
        for category, reqs in track_reqs.items():
            if not isinstance(reqs, dict): continue
            
            for key, courses in reqs.items():
                if not isinstance(courses, list): continue
                
                # Filter courses to only those in the graph
                valid_options = [c for c in courses if c in self.courses]
                
                if key == "required":
                    base_required.update(valid_options)
                
                elif key.startswith("pick_"):
                    try:
                        num_to_pick = int(key.split('_')[1])
                    except ValueError:
                        print(f"Warning: Could not parse pick number from '{key}'")
                        num_to_pick = 1
                    
                    if len(valid_options) < num_to_pick:
                        print(f"Warning: Not enough options for {track} {key}. Need {num_to_pick}, found {len(valid_options)}")
                        # Add all available options as the only choice
                        choice_blocks.append([set(valid_options)])
                    else:
                        # Get all combinations (e.g., pick 2 from 4)
                        combinations_for_block = [
                            set(combo) for combo in itertools.combinations(valid_options, num_to_pick)
                        ]
                        if combinations_for_block:
                            choice_blocks.append(combinations_for_block)

        # 2. Calculate the Cartesian product of all choice blocks
        all_combinations = []
        if not choice_blocks:
            # This track has no electives (only required courses)
            return [base_required]

        product_of_choices = itertools.product(*choice_blocks)
        
        # 3. Combine product with base requirements
        for choice_tuple in product_of_choices:
            # choice_tuple looks like: ({'CS3200'}, {'CS4120', 'CS4180'}, ...)
            new_plan_set = base_required.copy()
            for choice_set in choice_tuple:
                new_plan_set.update(choice_set)
            all_combinations.append(new_plan_set)
            
        return all_combinations
        
    def calculate_choice_scores(self, all_plans: List[Set[str]], track: str) -> Dict[str, float]:
        """
        Calculates the inclusion frequency for all non-required courses.
        Returns a dict: {course_id: frequency (0.0 to 1.0)}
        """
        # Find the set of purely required courses to exclude them
        track_reqs = self.CONCENTRATION_REQUIREMENTS.get(track, {})
        base_required = set()
        for reqs in track_reqs.values():
            if "required" in reqs:
                base_required.update(reqs["required"])

        course_counts = collections.defaultdict(int)
        total_plans = len(all_plans)
        if total_plans == 0:
            return {}

        for plan in all_plans:
            for course in plan:
                if course not in base_required:
                    course_counts[course] += 1
        
        # Calculate frequency
        choice_scores = {
            course: (count / total_plans)
            for course, count in course_counts.items()
        }
        
        # Sort by frequency, descending
        return dict(sorted(choice_scores.items(), key=lambda item: item[1], reverse=True))

    def calculate_plan_set_metrics(self, all_plans: List[Set[str]]) -> Dict:
        """
        Calculates aggregate metrics (complexity, blocking factor)
        across all possible plan combinations.
        """
        plan_total_complexities = []
        plan_median_blocking_factors = []
        
        if not all_plans:
            return {}

        for plan in all_plans:
            complexities_in_plan = []
            blocking_factors_in_plan = []
            
            for course in plan:
                if course in self.courses:
                    complexities_in_plan.append(self.courses[course].get('complexity', 0))
                if course in self.curriculum_graph:
                    # Use out_degree as the "blocking factor"
                    blocking_factors_in_plan.append(self.curriculum_graph.out_degree(course))

            if complexities_in_plan:
                plan_total_complexities.append(np.sum(complexities_in_plan))
            
            if blocking_factors_in_plan:
                plan_median_blocking_factors.append(np.median(blocking_factors_in_plan))
        
        if not plan_total_complexities:
             return {"error": "No complexity data found for courses in plans."}

        return {
            "median_total_complexity": np.median(plan_total_complexities),
            "min_total_complexity": np.min(plan_total_complexities),
            "max_total_complexity": np.max(plan_total_complexities),
            "median_blocking_factor": np.median(plan_median_blocking_factors) if plan_median_blocking_factors else 0
        }    
        
    def analyze_track_flexibility(self, track: str) -> Dict:
        """
        Runs a full analysis on a track, generating all combinations
        and calculating choice scores and plan metrics.
        """
        print(f"--- Analyzing all combinations for {track} track ---")
        
        # 1. Generate all plan sets
        all_plans = self.generate_all_valid_plans(track)
        
        if not all_plans:
            return {"error": "No valid plan combinations found for this track."}
        
        total_combinations = len(all_plans)
        
        # 2. Calculate choice scores
        choice_scores = self.calculate_choice_scores(all_plans, track)
        
        # 3. Calculate aggregate metrics
        plan_set_metrics = self.calculate_plan_set_metrics(all_plans)
        
        print(f"--- Analysis complete: Found {total_combinations} combinations ---")
        
        return {
            "track": track,
            "total_combinations": total_combinations,
            "choice_scores": choice_scores,
            "plan_set_metrics": plan_set_metrics
        }    
        
        
    def _build_structured_plan(self, student: StudentProfile, track: str, llm_suggestions: Optional[List[str]] = None) -> Dict:
        """
        PRODUCTION PLANNER - NOW FULLY TRACK-AWARE
        Uses different priority lists based on the selected track.
        """
        completed = set(student.completed_courses)
        plan = {}
        
        requirements = self.CONCENTRATION_REQUIREMENTS.get(track, self.CONCENTRATION_REQUIREMENTS["ai_ml"])
        print(f"--- Using requirements for: {track} ---")
        print(f"--- Difficulty preference: {student.preferred_difficulty} ---")  # DEBUG
        
        courses_per_semester = self._calculate_course_load(student.time_commitment)
        
        # Build required and pick sets
        required_set = set()
        picklist_set = set()
        for category, reqs in requirements.items():
            if "required" in reqs:
                required_set.update(reqs["required"])
            for key, courses in reqs.items():
                if key.startswith("pick_"):
                    picklist_set.update(courses)
        
        semantic_scores = self._compute_semantic_scores(student)
        
        # --- TRACK-AWARE PRIORITIES ---
        TRACK_YEAR_PRIORITIES = {
            "general": {
                2: ["CS3000", "CS3500", "CS3650", "MATH2331", "MATH3081", "CS3200"],
                3: ["CS4700", "CS4400", "CS4500", "CS4100"],
                4: ["CS5700", "CS4730", "CS4530", "CS4550", "CS4410"]
            },
            "ai_ml": {
                2: ["CS3000", "CS3500", "DS2500", "DS3000", "DS3500", "MATH2331", "MATH3081", "CS3650"],
                3: ["CS4100", "DS4400", "CS4120", "DS4420", "DS4440", "CS4180"],
                4: ["CS4730", "CS4700", "CS5700", "DS4300", "CS4400", "CS4500"]
            },
            "security": {
                2: ["CS3000", "CS3650", "CY2550", "MATH2331", "MATH3081", "CS3500"],
                3: ["CY3740", "CS4700", "CS5700", "CS4730"],
                4: ["CY4740", "CY4760", "CS4400"]
            },
            "systems": {
                2: ["CS3000", "CS3500", "CS3650", "MATH2331", "CS3200"],
                3: ["CS4700", "CS5700", "CS4730", "CS4500", "CS4400"],
                4: ["CS4520", "CS4410"]
            },
            "game_dev": {
                2: ["CS3000", "CS3500", "CS3540", "MATH2331", "MATH3081", "CS3650"],
                3: ["CS4520", "CS4300", "CS4100", "CS4700"],
                4: ["CS4550", "CS4410", "CS4180"]
            }
        }
        
        for sem_num in range(1, 9):
            year = ((sem_num - 1) // 2) + 1
            
            available_courses = self._get_available_courses(completed, year, sem_num, track)
            
            schedulable = [
                c for c in available_courses
                if c not in completed and self._can_take_course(c, completed)
            ]
            
            # Use track-specific priorities
            current_year_priorities = TRACK_YEAR_PRIORITIES.get(track, TRACK_YEAR_PRIORITIES["general"]).get(year)
            
            if current_year_priorities:
                priority_courses = [c for c in current_year_priorities if c in schedulable]
                other_courses = [c for c in schedulable if c not in current_year_priorities]
                
                scored_priority = sorted(
                    priority_courses,
                    key=lambda c: self._score_course(c, semantic_scores, required_set, picklist_set, year, track),
                    reverse=True
                )
                scored_others = sorted(
                    other_courses,
                    key=lambda c: self._score_course(c, semantic_scores, required_set, picklist_set, year, track),
                    reverse=True
                )
                
                scored_courses = scored_priority + scored_others
            else:
                scored_courses = sorted(
                    schedulable,
                    key=lambda c: self._score_course(c, semantic_scores, required_set, picklist_set, year, track),
                    reverse=True
                )
            
            # === DIFFICULTY FILTER BEFORE SELECTION ===
            if self.current_student and self.current_student.preferred_difficulty:
                diff_pref = self.current_student.preferred_difficulty.lower()
                
                if diff_pref == "easy":
                    # Try progressively higher thresholds
                    thresholds = [6.0, 7.0, 8.0, 100.0]  # Last = no filter
                    easy_courses = []
                    
                    for threshold in thresholds:
                        easy_courses = [
                            c for c in scored_courses 
                            if self._get_course_difficulty_score(c) < threshold
                        ]
                        if len(easy_courses) >= courses_per_semester:
                            print(f"  [Year {year}] Easy: {len(easy_courses)} courses (threshold={threshold})")
                            break
                    
                    scored_courses = easy_courses
                
                elif diff_pref == "challenging":
                    # Sort by difficulty DESC (hardest first)
                    scored_courses = sorted(
                        scored_courses,
                        key=lambda c: self._get_course_difficulty_score(c),
                        reverse=True
                    )
                    print(f"  [Year {year}] Challenging: sorted by difficulty")

            
            # Select top N courses (NOW with filtered list)
            selected = []
            for course in scored_courses:
                if len(selected) >= courses_per_semester:
                    break
                if self._validate_sequence(selected, course):
                    selected.append(course)
            
            if selected:
                year_key = f"year_{year}"
                if year_key not in plan:
                    plan[year_key] = {}
                
                sem_type = 'fall' if (sem_num % 2) == 1 else 'spring'
                plan[year_key][sem_type] = selected
                completed.update(selected)
        
        return plan


    def _get_available_courses(self, completed: Set[str], year: int, sem_num: int = None, track: str = "ai_ml") -> List[str]:
        """
        AGENTIC COURSE FILTER - Relies on Graph Attributes
        """
        # --- Year 1: Foundation (Keep this structure) ---
        if year == 1:
            if not completed or len(completed) < 2:
                return [c for c in ["CS1800", "CS2500", "MATH1341", "ENGW1111"] if c in self.valid_courses]
            else:
                next_courses = []
                prereq_map = [
                    ("CS2800", "CS1800"), 
                    ("CS2510", "CS2500"), 
                    ("MATH1342", "MATH1341"), 
                    ("DS2000", None),
                    ("DS2500", "DS2000")
                ]
                for course, prereq in prereq_map:
                    if course in self.valid_courses and course not in completed:
                        if prereq is None or prereq in completed:
                            next_courses.append(course)
                return next_courses
        
        # --- Years 2-4: Dynamic Graph Query ---
        available = []
        
        for cid in self.valid_courses:
            # 1. CRITICAL: Don't suggest courses already taken
            if cid in completed:
                continue
            
            # 2. Agentic Check: Trust the Graph's data
            # The Analyzer must have tagged these nodes previously!
            if self.courses[cid].get('undergrad_accessible', False):
                available.append(cid)
                
        return available

    def _fix_plan_errors(self, plan: Dict, validation: Dict, student: StudentProfile) -> Dict:
        if any("Mixed" in error for error in validation["errors"]):
            return self._build_structured_plan(student, self._identify_track(student), None)
        return plan
        
    def _get_llm_course_suggestions(self, student: StudentProfile, track: str) -> List[str]:
        requirements = self.CONCENTRATION_REQUIREMENTS.get(track, {})
        all_options = set()
        for reqs in requirements.values():
            for key, courses in reqs.items():
                if key.startswith("pick_"):
                    all_options.update(courses)
        
        course_options_text = [
            f"{cid}: {self.courses[cid].get('name', cid)} - {self.courses[cid].get('description', '')[:100].strip()}"
            for cid in list(all_options)[:15] if cid in self.courses
        ]
        
        prompt = f"""Expert curriculum advisor ranking courses for student.

Student Profile:
- Career Goal: {student.career_goals}
- Interests: {', '.join(student.interests)}
- Difficulty: {student.preferred_difficulty}

Available Courses:
{chr(10).join(course_options_text)}

Return ONLY top 5 course IDs, one per line."""

        try:
            inputs = self.tokenizer(prompt, return_tensors="pt", truncation=True, max_length=4096).to(self.device)
            with torch.no_grad():
                outputs = self.llm.generate(
                    **inputs, 
                    max_new_tokens=100, 
                    temperature=0.2, 
                    do_sample=True, 
                    pad_token_id=self.tokenizer.eos_token_id
                )
            response = self.tokenizer.decode(outputs[0][len(inputs['input_ids'][0]):], skip_special_tokens=True)
            suggested_courses = re.findall(r'([A-Z]{2,4}\d{4})', response)
            return suggested_courses[:5]
        except Exception as e:
            print(f"LLM suggestion failed: {e}")
            return list(all_options)[:5]

    def _map_difficulty(self, preferred_difficulty: str) -> str:
        return {"easy": "easy", "moderate": "medium", "challenging": "hard"}.get(preferred_difficulty.lower(), "medium")
        
    def _calculate_course_load(self, time_commitment: int) -> int:
        if time_commitment <= 20:
            return 3
        if time_commitment <= 40:
            return 4
        return 5
        
    def _identify_track(self, student: StudentProfile) -> str:
        if not hasattr(self, 'embedding_model') or self.embedding_model is None:
            combined = f"{student.career_goals.lower()} {' '.join(student.interests).lower()}"
            if any(word in combined for word in ['ai', 'ml', 'machine learning', 'data']):
                return "ai_ml"
            if any(word in combined for word in ['systems', 'distributed', 'backend']):
                return "systems"
            if any(word in combined for word in ['security', 'cyber']):
                return "security"
            return "ai_ml"
        
        profile_text = f"{student.career_goals} {' '.join(student.interests)}"
        profile_emb = self.embedding_model.encode(profile_text, convert_to_tensor=True)
        
        track_descriptions = {
            "ai_ml": "artificial intelligence machine learning deep learning neural networks data science",
            "systems": "operating systems distributed systems networks compilers databases performance backend",
            "security": "cybersecurity cryptography network security ethical hacking vulnerabilities"
        }
        
        best_track, best_score = "ai_ml", -1.0
        for track, description in track_descriptions.items():
            track_emb = self.embedding_model.encode(description, convert_to_tensor=True)
            score = float(util.cos_sim(profile_emb, track_emb))
            if score > best_score:
                best_score, best_track = score, track
        
        return best_track
        
    def _compute_semantic_scores(self, student: StudentProfile) -> Dict[str, float]:
        query_text = f"{student.career_goals} {' '.join(student.interests)}"
        query_emb = self.embedding_model.encode(query_text, convert_to_tensor=True)
        similarities = util.cos_sim(query_emb, self.course_embeddings)[0]
        return {cid: float(similarities[idx]) for idx, cid in enumerate(self.valid_courses)}
        
    def _generate_explanation(self, student: StudentProfile, plan: Dict, track: str, plan_type: str) -> str:
        return f"{plan_type.title()} plan for the {track} track, tailored to your goal of becoming a {student.career_goals}."

    def validate_plan(self, plan: Dict, student: StudentProfile = None) -> Dict[str, List[str]]:
        issues = {"errors": [], "warnings": [], "info": []}
        all_courses = [course for year in plan.values() for sem in year.values() for course in sem if isinstance(sem, list)]
        
        # Check for mixed tracks
        for track_type, tracks in self.COURSE_TRACKS.items():
            tracks_used = {name for name, courses in tracks.items() if any(c in all_courses for c in courses)}
            if len(tracks_used) > 1:
                issues["errors"].append(f"Mixed {track_type} tracks: {', '.join(tracks_used)}. Choose one sequence.")

        # Validate prerequisites
        completed_for_validation = set(student.completed_courses) if student else set()
        for year in range(1, 5):
            for sem in ["fall", "spring"]:
                year_key = f"year_{year}"
                sem_courses = plan.get(year_key, {}).get(sem, [])
                for course in sem_courses:
                    if course in self.curriculum_graph:
                        prereqs = set(self.curriculum_graph.predecessors(course))
                        if not prereqs.issubset(self._get_completed_with_equivalents(completed_for_validation)):
                            missing = prereqs - completed_for_validation
                            issues["errors"].append(f"{course} in Year {year} {sem} is missing prereqs: {', '.join(missing)}")
                completed_for_validation.update(sem_courses)
        
        return issues

    def _finalize_plan(self, plan: Dict, explanation: str, validation: Dict = None) -> Dict:
        structured_plan = {
            "reasoning": explanation, 
            "validation": validation or {"errors": [], "warnings": [], "info": []}
        }
        
        complexities = []
        for year in range(1, 5):
            year_key = f"year_{year}"
            structured_plan[year_key] = {
                "fall": plan.get(year_key, {}).get("fall", []),
                "spring": plan.get(year_key, {}).get("spring", []),
                "summer": "co-op" if year in [2, 3] else []
            }
            
            for sem in ["fall", "spring"]:
                courses = structured_plan[year_key][sem]
                if courses:
                    sem_complexity = sum(self.courses.get(c, {}).get('complexity', 50) for c in courses)
                    complexities.append(sem_complexity)
        
        structured_plan["complexity_analysis"] = {
            "average_semester_complexity": float(np.mean(complexities)) if complexities else 0,
            "peak_semester_complexity": float(np.max(complexities)) if complexities else 0,
            "total_complexity": float(np.sum(complexities)) if complexities else 0,
            "balance_score (std_dev)": float(np.std(complexities)) if complexities else 0
        }
        
        structured_plan["metadata"] = {
            "generated": datetime.now().isoformat(),
            "valid": len(validation.get("errors", [])) == 0 if validation else True,
        }
        
        return {"pathway": structured_plan}

class CurriculumOptimizer(HybridOptimizer):
    """Compatibility wrapper"""
    def __init__(self):
        super().__init__()
    
    def generate_plan(self, student: StudentProfile, track_override: Optional[str] = None) -> Dict:
        return self.generate_enhanced_rule_plan(student, track_override)