"""
RateMyProfessors GraphQL Scraper - Direct & Exhaustive
Bypasses the need for RapidAPI by mimicking the browser's GraphQL calls.
"""
import requests
import json
import base64
import time
import pickle
import os
import random
import networkx as nx  # Added for graph handling
from typing import Dict, Optional

# --- CONFIGURATION ---
NEU_SCHOOL_ID = "U2Nob29sLTY5OA=="  # Base64 for "School-698" (Northeastern)
RMP_GRAPHQL_URL = "https://www.ratemyprofessors.com/graphql"
AUTH_HEADER = "Basic dGVzdDp0ZXN0" 

class RMPScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": AUTH_HEADER,
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Content-Type": "application/json",
            "Origin": "https://www.ratemyprofessors.com",
            "Referer": "https://www.ratemyprofessors.com/"
        })

    def search_professor(self, name: str) -> Optional[str]:
        """Search for a professor by name at NEU and return their Legacy ID."""
        query = """
        query NewSearchTeachersPS($query: TeacherSearchQuery!) {
          newSearch {
            teachers(query: $query) {
              edges {
                node {
                  id
                  legacyId
                  firstName
                  lastName
                  school {
                    id
                    name
                  }
                }
              }
            }
          }
        }
        """
        
        variables = {
            "query": {
                "text": name,
                "schoolID": NEU_SCHOOL_ID
            }
        }

        try:
            response = self.session.post(
                RMP_GRAPHQL_URL, 
                json={"query": query, "variables": variables},
                timeout=5
            )
            data = response.json()
            
            edges = data.get("data", {}).get("newSearch", {}).get("teachers", {}).get("edges", [])
            if not edges:
                return None
            
            return edges[0]["node"]["legacyId"]
            
        except Exception as e:
            print(f"❌ Search failed for {name}: {e}")
            return None

    def get_professor_details(self, legacy_id: int) -> Dict:
        """Fetch detailed ratings using the Legacy ID."""
        query = """
        query TeacherRatingsPageQuery($id: ID!) {
          node(id: $id) {
            ... on Teacher {
              id
              firstName
              lastName
              avgRating
              avgDifficulty
              numRatings
              wouldTakeAgainPercent
              department
            }
          }
        }
        """
        
        base64_id = base64.b64encode(f"Teacher-{legacy_id}".encode('utf-8')).decode('utf-8')
        variables = {"id": base64_id}

        try:
            response = self.session.post(
                RMP_GRAPHQL_URL, 
                json={"query": query, "variables": variables},
                timeout=5
            )
            data = response.json()
            node = data.get("data", {}).get("node", {})
            
            return {
                "id": legacy_id,
                "name": f"{node.get('firstName')} {node.get('lastName')}",
                "avgRating": node.get("avgRating"),
                "avgDifficulty": node.get("avgDifficulty"),
                "numRatings": node.get("numRatings"),
                "wouldTakeAgain": node.get("wouldTakeAgainPercent"),
                "department": node.get("department")
            }
        except Exception as e:
            print(f"❌ Details failed for ID {legacy_id}: {e}")
            return None

def scrape_all_professors(pickle_path: str, output_json: str):
    """Load your existing .pkl, extract prof names, scrape RMP, save JSON."""
    
    print(f"📂 Loading courses from {pickle_path}...")
    with open(pickle_path, 'rb') as f:
        data = pickle.load(f)
    
    courses = {}

    # --- FIX: Handle NetworkX Graph vs Dict ---
    if isinstance(data, nx.Graph) or isinstance(data, nx.DiGraph):
        print("ℹ️  Detected NetworkX Graph object.")
        # NetworkX nodes store attributes in a dict, so we convert nodes to a dict
        courses = dict(data.nodes(data=True))
    elif isinstance(data, dict):
        if "courses" in data:
            courses = data["courses"]
        else:
            courses = data
    else:
        print(f"❌ Unknown pickle format: {type(data)}")
        return
    # ------------------------------------------

    # Extract unique professors
    unique_profs = set()
    for cdata in courses.values():
        # Handle cases where 'professors' might be missing or None
        profs = cdata.get("professors", [])
        if profs:
            for prof in profs:
                if prof: # Ensure prof string is not empty
                    unique_profs.add(prof)
    
    print(f"🔍 Found {len(unique_profs)} unique professors to check.")
    
    scraper = RMPScraper()
    results = {}
    
    if os.path.exists(output_json):
        with open(output_json, 'r') as f:
            results = json.load(f)
        print(f"♻️  Resuming from cache ({len(results)} already scraped).")

    for i, prof_name in enumerate(unique_profs):
        if prof_name in results:
            continue
            
        print(f"[{i+1}/{len(unique_profs)}] Searching: {prof_name}...", end=" ", flush=True)
        
        time.sleep(random.uniform(0.5, 1.5))
        
        legacy_id = scraper.search_professor(prof_name)
        
        if legacy_id:
            details = scraper.get_professor_details(legacy_id)
            if details:
                results[prof_name] = details
                print(f"✅ Found! Diff: {details['avgDifficulty']}")
            else:
                results[prof_name] = {"found": False}
                print("⚠️  Details failed")
        else:
            results[prof_name] = {"found": False}
            print("❌ Not found")
            
        if i % 10 == 0:
            with open(output_json, 'w') as f:
                json.dump(results, f, indent=2)

    with open(output_json, 'w') as f:
        json.dump(results, f, indent=2)
    print(f"🎉 Done! Saved database to {output_json}")

if __name__ == "__main__":
    # Ensure this matches your actual file path
    PICKLE_FILE = "utils/neu_data_withprofs_graph_20251206_192309.pkl" 
    OUTPUT_FILE = "rmp_data.json"
    
    scrape_all_professors(PICKLE_FILE, OUTPUT_FILE)