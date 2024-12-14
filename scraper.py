# scraper.py
import requests
from bs4 import BeautifulSoup
import json
import time

def fetch_course_data(course_id, term_code):
    url = f"https://searchneu.com/NEU/{term_code}/search/{course_id}"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # Extract course details based on identified HTML structure
    course_data = {
        "id": course_id,
        "name": soup.find("h1").text.strip() if soup.find("h1") else "",
        "description": soup.find("section", {"aria-labelledby": "courseDescription"}).text.strip() if soup.find("section", {"aria-labelledby": "courseDescription"}) else "",
        "credits": soup.find("span", string=lambda text: text and "CREDITS" in text).text.strip() if soup.find("span", string=lambda text: text and "CREDITS" in text) else "",
        "prerequisites": [prereq.text.strip() for prereq in soup.find_all("div", {"class": "prerequisite"})],
        "corequisites": [coreq.text.strip() for coreq in soup.find_all("div", {"class": "corequisite"})]
    }
    return course_data

def save_to_json(data, filename="courses.json"):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def main():
    term_codes = ["202510", "202410", "202430", "202450"]
    course_ids = ["5004", "5001", "5002"]
    
    all_data = []
    for term_code in term_codes:
        for course_id in course_ids:
            course_info = fetch_course_data(course_id, term_code)
            all_data.append(course_info)
            time.sleep(1)  # Prevent rate limiting

    save_to_json(all_data)

if __name__ == "__main__":
    main()
