import asyncio
from playwright.async_api import async_playwright
import json
import logging
import pickle
from typing import List, Dict

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

class SearchNEUScraper:
    """SearchNEU scraper using Playwright (handles JavaScript)"""
    
    CATALOG_URL = "https://searchneu.com/catalog"
    CACHE_FILE = "professor_cache.pkl"
    
    def __init__(self):
        self.professor_cache = self._load_cache()
    
    def _load_cache(self) -> Dict:
        try:
            with open(self.CACHE_FILE, "rb") as f:
                return pickle.load(f)
        except FileNotFoundError:
            return {}
    
    def _save_cache(self):
        with open(self.CACHE_FILE, "wb") as f:
            pickle.dump(self.professor_cache, f)
        logger.info(f"✅ Cache saved: {len(self.professor_cache)} courses")
    
    async def get_course_sections(self, term_id: str, course_code: str) -> list:
        """Scrape using Playwright"""
        url = f"{self.CATALOG_URL}/{term_id}/{course_code}"
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            try:
                await page.goto(url, wait_until="networkidle")
                
                # Wait for table to load
                await page.wait_for_selector("tr", timeout=5000)
                
                # Extract sections
                sections = []
                rows = await page.query_selector_all("tr")
                
                for row in rows:
                    cells = await row.query_selector_all("td")
                    if len(cells) < 6:
                        continue
                    
                    crn = (await cells[0].text_content()).strip()
                    if not crn.isdigit():
                        continue
                    
                    professor = (await cells[4].text_content()).strip()
                    campus = (await cells[5].text_content()).strip()
                    
                    if professor and professor != "TBA":
                        sections.append({
                            "crn": crn,
                            "professor": professor,
                            "campus": campus
                        })
                
                self.professor_cache[f"{term_id}_{course_code}"] = sections
                self._save_cache()
                
                logger.info(f"{course_code}: {len(sections)} sections")
                return sections
                
            except Exception as e:
                logger.error(f"Error scraping {course_code}: {e}")
                return []
            finally:
                await browser.close()
    
    async def get_all_courses_professors(self, term_id: str, courses: List[str]) -> Dict[str, List]:
        """Batch scrape"""
        results = {}
        for i, course_code in enumerate(courses):
            sections = await self.get_course_sections(term_id, course_code)
            results[course_code] = sections
            if (i + 1) % 5 == 0:
                logger.info(f"Progress: {i + 1}/{len(courses)}")
        return results
    
    def export_professor_data(self, output_file: str = "professor_data.json"):
        with open(output_file, "w") as f:
            json.dump(self.professor_cache, f, indent=2)
        logger.info(f"✅ Exported to {output_file}")

# Usage
async def main():
    scraper = SearchNEUScraper()
    
    # Single course
    sections = await scraper.get_course_sections("202510", "CS5010")
    for sec in sections:
        print(f"Prof: {sec['professor']}, Campus: {sec['campus']}")
    
    # Batch
    courses = ["CS5010", "CS5100", "CS5200"]
    await scraper.get_all_courses_professors("202510", courses)
    scraper.export_professor_data()

if __name__ == "__main__":
    asyncio.run(main())
