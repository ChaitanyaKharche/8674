"""
NEU Course Scraper - Production Version
Scrapes SearchNEU GraphQL API, builds dependency graph, and saves combined data
with professor information for curriculum optimization.

Usage:
    python neu_scraper.py --university neu --term 202510 --subjects CS DS MATH CY --output neu_data_with_profs
"""

import requests
import pickle
import networkx as nx
import time
import logging
import json
import re
from typing import List, Dict, Set, Any, Optional
from datetime import datetime
from collections import defaultdict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(levelname)s %(message)s"
)
logger = logging.getLogger(__name__)


class NEUCourseScraper:
    """Northeastern University course scraper using SearchNEU GraphQL API"""

    SEARCHNEU_GRAPHQL = "https://api.searchneu.com/graphql"
    CATALOG_URL = "https://catalog.northeastern.edu"

    def __init__(self):
        self.api_url = self.SEARCHNEU_GRAPHQL
        self.headers = {"Content-Type": "application/json"}
        self.session = requests.Session()
        self.merged_courses = {}
        self.graph = nx.DiGraph()

    def get_all_courses(self, term_id: str, subjects: List[str] = None) -> Dict[str, Dict]:
        """
        Fetch all courses using SearchNEU GraphQL API.
        """
        if subjects is None:
            subjects = ["CS", "DS", "MATH", "CY"]

        merged_courses = {}

        for subject in subjects:
            logger.info(f"Scraping {subject} courses for term {term_id}...")
            courses = self._fetch_subject_courses(term_id, subject)

            for course in courses:
                cid = f"{course['subject']}{course['classId']}"
                if cid not in merged_courses:
                    merged_courses[cid] = course
                else:
                    existing = merged_courses[cid]
                    if course.get('description') and not existing.get('description'):
                        merged_courses[cid] = course
                    # Merge professors if they exist
                    if course.get('professors'):
                        existing_profs = set(existing.get('professors', []))
                        new_profs = set(course.get('professors', []))
                        merged_courses[cid]['professors'] = sorted(list(existing_profs | new_profs))

            time.sleep(0.3)

        self.merged_courses = merged_courses
        logger.info(f"Total unique courses collected: {len(self.merged_courses)}")
        return self.merged_courses

    def _fetch_subject_courses(self, term_id: str, subject: str) -> List[Dict]:
        """
        Fetch all courses for a subject via pagination.
        Extracts professor information from sections.
        """
        all_courses = []
        offset = 0
        page = 1
        max_failures = 3
        consecutive_failures = 0

        while consecutive_failures < max_failures:
            query = """
            query searchQuery($termId: String!, $query: String!, $first: Int, $offset: Int) {
              search(termId: $termId, query: $query, first: $first, offset: $offset) {
                totalCount
                nodes {
                  __typename
                  ... on ClassOccurrence {
                    subject
                    classId
                    name
                    desc
                    prereqs
                    coreqs
                    minCredits
                    maxCredits
                    sections {
                      termId
                      profs
                    }
                  }
                }
              }
            }
            """

            variables = {
                "termId": term_id,
                "query": subject,
                "first": 100,
                "offset": offset
            }

            try:
                resp = self.session.post(
                    self.api_url,
                    json={"query": query, "variables": variables},
                    headers=self.headers,
                    timeout=10
                )
                resp.raise_for_status()
                data = resp.json()

                if "errors" in data:
                    error_msg = data.get("errors", [{}])[0].get("message", "Unknown error")
                    logger.warning(f"GraphQL error: {error_msg}")
                    consecutive_failures += 1
                    time.sleep(2 ** consecutive_failures)
                    continue

                search_data = data.get("data", {}).get("search", {})
                nodes = search_data.get("nodes", [])

                page_courses = [
                    c for c in nodes if c.get("__typename") == "ClassOccurrence"
                ]

                # EXTRACT PROFESSORS FROM SECTIONS
                for course in page_courses:
                    profs_set = set()
                    for section in course.get("sections", []):
                        section_profs = section.get("profs", [])
                        # Handle both list and None
                        if section_profs and isinstance(section_profs, list):
                            for prof in section_profs:
                                if isinstance(prof, dict):
                                    # If prof is a dict, extract name
                                    if "name" in prof:
                                        profs_set.add(prof["name"])
                                    elif "firstName" in prof and "lastName" in prof:
                                        profs_set.add(f"{prof['firstName']} {prof['lastName']}")
                                elif isinstance(prof, str):
                                    # If prof is a string, use directly
                                    profs_set.add(prof)
                    
                    # Add professors list to course
                    course['professors'] = sorted(list(profs_set))

                all_courses.extend(page_courses)
                logger.info(
                    f"[{term_id}] {subject} Page {page}: {len(page_courses)} courses "
                    f"(Total: {len(all_courses)})"
                )

                if len(page_courses) < 100:
                    break

                offset += 100
                page += 1
                consecutive_failures = 0

            except requests.exceptions.RequestException as e:
                consecutive_failures += 1
                logger.error(f"Network error fetching {subject} page {page}: {e}")
                time.sleep(2 ** consecutive_failures)
            except Exception as e:
                consecutive_failures += 1
                logger.error(f"Unexpected error: {e}")

        logger.info(f"[{term_id}] {subject}: {len(all_courses)} total courses")
        return all_courses

    def _recursive_parse_prereqs(self, prereq_obj: Any) -> Set[str]:
        """Extract course IDs from nested prerequisite structures"""
        ids = set()

        if not isinstance(prereq_obj, dict):
            return ids

        if "classId" in prereq_obj and "subject" in prereq_obj:
            ids.add(f"{prereq_obj['subject']}{prereq_obj['classId']}")
            return ids

        if prereq_obj.get("type") in ["and", "or"]:
            for val in prereq_obj.get("values", []):
                ids |= self._recursive_parse_prereqs(val)
        elif "values" in prereq_obj:
            for val in prereq_obj.get("values", []):
                ids |= self._recursive_parse_prereqs(val)

        return ids

    def build_graph(self) -> nx.DiGraph:
        """Build NetworkX graph from course data"""
        logger.info("Building course dependency graph...")

        for cid, cdata in self.merged_courses.items():
            self.graph.add_node(cid, **{
                "name": cdata.get("name", ""),
                "subject": cdata.get("subject", ""),
                "classId": cdata.get("classId", ""),
                "description": cdata.get("desc", ""),
                "minCredits": cdata.get("minCredits", 0),
                "maxCredits": cdata.get("maxCredits", 0),
                "professors": cdata.get("professors", [])
            })

        edge_count = 0
        for cid, cdata in self.merged_courses.items():
            prereqs = cdata.get("prereqs", {})
            if prereqs:
                prereq_ids = self._recursive_parse_prereqs(prereqs)
                for pid in prereq_ids:
                    if pid in self.graph:
                        self.graph.add_edge(pid, cid, relationship="prerequisite")
                        edge_count += 1
                    else:
                        logger.warning(f"Prereq {pid} for {cid} not in graph")

        logger.info(f"Graph: {self.graph.number_of_nodes()} nodes, {edge_count} edges")
        return self.graph

    def save_data(self, prefix: str = "neu"):
        """Save graph, courses, and combined data for API"""
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        gfile = f"{prefix}_graph_{ts}.pkl"
        cfile = f"{prefix}_courses_{ts}.pkl"
        combined_file = f"{prefix}_combined_{ts}.pkl"

        # Save individual files
        with open(gfile, "wb") as gf:
            pickle.dump(self.graph, gf)

        with open(cfile, "wb") as cf:
            pickle.dump(self.merged_courses, cf)

        # Save combined format for API (REQUIRED)
        combined_data = {
            "graph": self.graph,
            "courses": self.merged_courses
        }
        with open(combined_file, "wb") as comb_f:
            pickle.dump(combined_data, comb_f)

        logger.info(f"\n✅ Data saved:")
        logger.info(f"   Graph: {gfile}")
        logger.info(f"   Courses: {cfile}")
        logger.info(f"   Combined (UPLOAD THIS): {combined_file}\n")

        return gfile, cfile, combined_file


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="NEU Course Scraper - SearchNEU GraphQL with Professors"
    )
    parser.add_argument(
        "--university",
        choices=["neu"],
        default="neu",
        help="University to scrape (currently only NEU supported)"
    )
    parser.add_argument(
        "--term",
        required=True,
        help="Term ID (e.g., 202510 for Fall 2025, 202530 for Spring 2026)"
    )
    parser.add_argument(
        "--subjects",
        nargs="+",
        default=["CS", "DS", "MATH", "CY"],
        help="Subjects to scrape (default: CS DS MATH CY)"
    )
    parser.add_argument(
        "--output",
        default="neu_data",
        help="Output file prefix (default: neu_data)"
    )

    args = parser.parse_args()

    if args.university == "neu":
        scraper = NEUCourseScraper()

        logger.info(f"🚀 Scraping NEU for term {args.term}...")
        logger.info(f"📚 Subjects: {', '.join(args.subjects)}")

        courses = scraper.get_all_courses(args.term, args.subjects)
        scraper.build_graph()
        gfile, cfile, combined_file = scraper.save_data(args.output)

        logger.info(f"✅ Scraping complete!")
        logger.info(f"\n📋 NEXT STEP: Upload '{combined_file}' to the web app frontend")

    else:
        logger.error(f"University '{args.university}' not yet implemented")


if __name__ == "__main__":
    main()
