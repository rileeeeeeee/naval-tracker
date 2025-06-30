# scraper.py (v15 - Interactive Debugging & Cookie Handling)

import sqlite3
import re
from datetime import datetime
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

DATABASE_FILE = 'fleet.db'
USNI_CATEGORY_URL = 'https://news.usni.org/category/fleet-tracker'

HULL_TO_CLASS = {
    'CVN': 'Aircraft Carrier', 'LHA': 'Amphibious Assault Ship', 'LHD': 'Amphibious Assault Ship',
    'LPD': 'Amphibious Transport Dock', 'LSD': 'Dock Landing Ship', 'CG': 'Cruiser',
    'DDG': 'Destroyer', 'LCS': 'Littoral Combat Ship', 'SSN': 'Submarine',
    'SSBN': 'Submarine', 'SSGN': 'Submarine', 'ESB': 'Expeditionary Sea Base',
    'LCC': 'Command Ship', 'T-AO': 'Replenishment Oiler', 'R': 'Aircraft Carrier',
    'DDH': 'Helicopter Destroyer'
}

def get_class_from_hull(hull):
    match = re.match(r'([A-Z]+)', hull)
    if match:
        prefix = match.group(1)
        return HULL_TO_CLASS.get(prefix, 'Unknown')
    return 'Unknown'

def init_db():
    conn = sqlite3.connect(DATABASE_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS ships (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL, hull TEXT, class TEXT,
            status TEXT, locationReported TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print("Database initialized.")

def get_page_source_with_selenium(url, driver, wait_for_class=None):
    print(f"Navigating to: {url}")
    driver.get(url)
    
    # --- NEW INTERACTIVE STEP: HANDLE COOKIE BANNER ---
    try:
        # Wait up to 5 seconds for the cookie accept button to be clickable
        cookie_button_wait = WebDriverWait(driver, 5)
        # Using CSS_SELECTOR to find the button by its ID
        cookie_button = cookie_button_wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "#gdpr-accept")))
        print("Cookie consent banner found. Clicking 'Accept'...")
        cookie_button.click()
        # Give it a moment to disappear
        time.sleep(2)
    except Exception:
        # If the button isn't there, no problem. Just continue.
        print("No cookie consent banner found, or it was not clickable in time.")

    if wait_for_class:
        try:
            print(f"Waiting up to 30 seconds for element with class '{wait_for_class}' to appear...")
            wait = WebDriverWait(driver, 30)
            wait.until(EC.presence_of_element_located((By.CLASS_NAME, wait_for_class)))
            print("Element found. Page is ready.")
        except Exception as e:
            print(f"Timeout occurred. The element '{wait_for_class}' did not appear within 30 seconds.")
            return driver.page_source
    else:
        print("Waiting for page to load (5 seconds)...")
        time.sleep(5)

    print("Page source fetched.")
    return driver.page_source

def clean_status_text(text):
    text = text.strip()
    phrases_to_remove = [ r',\s*according to ship spotters\.?$', r',\s*according to local media reports\.?$' ]
    for phrase in phrases_to_remove:
        text = re.sub(phrase, '', text, flags=re.IGNORECASE)
    text = text.strip()
    if text and not text.endswith(('.', '!', '?')):
        text += '.'
    if text:
        text = text[0].upper() + text[1:]
    return text

def scrape_and_update():
    print("Launching VISIBLE Chrome browser for debugging...")
    chrome_options = Options()
    
    # --- MODIFICATION: The '--headless' argument is commented out so you can see the browser. ---
    # To run blind again, uncomment the line below
    # chrome_options.add_argument("--headless")
    
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        html_content_category = get_page_source_with_selenium(USNI_CATEGORY_URL, driver)
        if not html_content_category:
            raise Exception("Failed to get category page source.")

        soup_category = BeautifulSoup(html_content_category, 'html.parser')
        heading = soup_category.find('h3', class_='title56')
        if not heading or not heading.find('a'):
            raise Exception("Could not find latest article link.")

        latest_url = heading.find('a')['href']
        print(f"Found latest post URL: {latest_url}")

        # Let's try waiting for 'entry-content' as an alternative, since 'td-post-content' is failing
        html_content_post = get_page_source_with_selenium(latest_url, driver, wait_for_class='entry-content')
        if not html_content_post:
            raise Exception("Failed to get post page source.")

        soup_post = BeautifulSoup(html_content_post, 'html.parser')
        
        # We are trying to find 'entry-content' first.
        post_content = soup_post.find('div', class_='entry-content')

        if not post_content:
            # If that fails, let's try our original idea as a fallback
            post_content = soup_post.find('div', class_='td-post-content')

        if not post_content:
            with open("debug_page.html", "w", encoding="utf-8") as f:
                f.write(html_content_post)
            print("DEBUGGING: Saved the page content to 'debug_page.html'.")
            raise Exception("Could not find a valid content div ('entry-content' or 'td-post-content').")

        date_tag = soup_post.find('time', class_='entry-date')
        update_date = date_tag.text.strip() if date_tag else datetime.now().strftime("%B %d, %Y")
        print(f"Found fleet data from: {update_date}")

        ships = []
        for p in post_content.find_all('p'):
            text = p.get_text()
            matches = re.finditer(r'(USS|HMS|JS|FS|HMAS)\s+([\w\s\'-]+?)\s+\(([\w\s-]+)\)', text)
            for match in matches:
                prefix, name, hull = match.groups()
                raw_status = text[match.end():].strip().replace('•', '').strip()
                if len(raw_status) > 10:
                    ships.append({
                        'name': f"{prefix} {name.strip()}",
                        'hull': hull.strip(),
                        'class': get_class_from_hull(hull.strip()),
                        'status': clean_status_text(raw_status),
                        'locationReported': update_date
                    })

        if not ships:
            print("No ships parsed. Text format may have changed or no ships listed in the usual format.")
            return

        print(f"Successfully scraped {len(ships)} ships. Updating database...")
        conn = sqlite3.connect(DATABASE_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM ships")
        for ship in ships:
            cursor.execute("INSERT INTO ships (name, hull, class, status, locationReported) VALUES (?, ?, ?, ?, ?)",
                           (ship['name'], ship['hull'], ship['class'], ship['status'], ship['locationReported']))
        conn.commit()
        conn.close()
        print("Database update complete.")

    except Exception as e:
        print(f"An unexpected error occurred during scraping: {e}")
    finally:
        driver.quit()
        print("Browser closed.")

if __name__ == '__main__':
    init_db()
    scrape_and_update()