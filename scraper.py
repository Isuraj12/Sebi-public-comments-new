from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import db

def init_driver():
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--window-size=1920,1080')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    return webdriver.Chrome(options=options)

def extract_rows_from_page(driver):
    circulars_found = []
    try:
        # Wait until table is present
        time.sleep(2) # Give DOM time to update after pagination
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//table"))
        )
        table = driver.find_element(By.XPATH, "//table")
        rows = table.find_elements(By.XPATH, ".//tr")
        for row in rows[1:]: # Skip header
            tds = row.find_elements(By.XPATH, ".//td")
            if len(tds) >= 2:
                try:
                    date = tds[0].text.strip()
                    a_tag = tds[1].find_element(By.XPATH, ".//a")
                    title = a_tag.text.strip()
                    html_href = a_tag.get_attribute("href")
                    
                    if title and html_href:
                        exists_in_db = db.get_circular_by_title(title)
                        if exists_in_db:
                            # Skip the slow PDF link extraction if it's already in the DB
                            circulars_found.append({"date": date, "title": title, "pdf_url": exists_in_db['pdf_url'], "exists": True})
                            continue
                            
                        # Extract real PDF URL by opening tab (SLOW operation, ~3-5s per new circular)
                        main_window = driver.current_window_handle
                        driver.execute_script("window.open(arguments[0], '_blank');", html_href)
                        WebDriverWait(driver, 5).until(lambda d: len(d.window_handles) > 1)
                        driver.switch_to.window(driver.window_handles[-1])
                        
                        pdf_url = html_href
                        try:
                            # wait for iframe
                            iframe = WebDriverWait(driver, 3).until(EC.presence_of_element_located((By.XPATH, "//iframe")))
                            src = iframe.get_attribute("src")
                            if src and "file=" in src.lower():
                                pdf_url = src.split("file=")[-1]
                            elif src and ".pdf" in src.lower():
                                pdf_url = src
                        except:
                            try:
                                links = driver.find_elements(By.XPATH, "//a[contains(@href, '.pdf')]")
                                if links:
                                    pdf_url = links[0].get_attribute("href")
                            except:
                                pass
                                
                        driver.close()
                        driver.switch_to.window(main_window)
                        
                        circulars_found.append({"date": date, "title": title, "pdf_url": pdf_url, "exists": False})
                except Exception as row_e:
                    # Skip rows that don't match exactly
                    pass
    except Exception as e:
        print(f"Error extracting rows from page: {e}")
    return circulars_found

def get_sebi_circulars(max_pages=21, stop_if_exists=False):
    db.init_db()
    driver = init_driver()
# wait, block by WAF? SEBI main page doesn't usually block.
    url = "https://www.sebi.gov.in/sebiweb/home/HomeAction.do?doListing=yes&sid=4&ssid=38&smid=35"
    driver.get(url)
    
    total_added = 0
    pages_scraped = 0

    while pages_scraped < max_pages:
        time.sleep(3) # Wait for table to load
        print(f"Scraping page {pages_scraped + 1}...")
        current_page_circulars = extract_rows_from_page(driver)
        
        if not current_page_circulars:
            print("No circulars found on this page. Stopping.")
            break
            
        page_added = 0
        for circ in current_page_circulars:
            if not circ.get("exists", False):
                inserted = db.insert_circular(circ["date"], circ["title"], circ["pdf_url"])
                if inserted:
                    page_added += 1
            elif stop_if_exists:
                # If we encounter an already existing circular and are in update mode, we stop completely.
                print("Found existing circular. Stopping update check.")
                driver.quit()
                return total_added + page_added
                
        total_added += page_added
        
        # Click Next page
        try:
            pages_scraped += 1
            if pages_scraped < max_pages:
                driver.execute_script("searchFormNewsList('n','-1');")
            time.sleep(3) # Wait for Ajax page load
        except Exception as e:
            print("Could not execute pagination Javascript. Stopping.")
            break

    driver.quit()
    return total_added

def scrape_all():
    print("Scraping all pages up to 21...")
    return get_sebi_circulars(max_pages=21, stop_if_exists=False)

def check_new():
    print("Checking for new circulars...")
    return get_sebi_circulars(max_pages=5, stop_if_exists=True)

if __name__ == "__main__":
    print(f"Total new circulars inserted testing first 1 page: {get_sebi_circulars(max_pages=1)}")
