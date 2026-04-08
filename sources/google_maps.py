"""Google Maps scraper using Selenium (no API key needed)."""

import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from sources.base import Business
import config


def _create_driver():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--lang=en-US")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    service = Service(ChromeDriverManager().install())
    return webdriver.Chrome(service=service, options=options)


def search(location: str, category: str, limit: int = 20, on_progress=None) -> list[Business]:
    """Scrape Google Maps. on_progress(step, detail) is called for live updates."""
    def emit(step, detail=""):
        if on_progress:
            on_progress(step, detail)

    query = f"{category} in {location}"
    url = f"https://www.google.com/maps/search/{query.replace(' ', '+')}"
    businesses = []

    driver = None
    try:
        emit("launch", "Starting Chrome...")
        driver = _create_driver()

        emit("load", f"Loading Google Maps...")
        driver.get(url)
        try:
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="feed"]'))
            )
        except Exception:
            time.sleep(2.5)

        emit("scroll", "Scrolling for more results...")
        _scroll_results(driver, limit, on_progress=on_progress)

        all_links = driver.find_elements(By.CSS_SELECTOR, 'a[aria-label]')
        places = []
        for link in all_links:
            href = link.get_attribute("href") or ""
            name = link.get_attribute("aria-label") or ""
            if "/maps/place/" in href and name:
                places.append((name, href))

        places = places[:limit]
        total = len(places)
        emit("found", f"Found {total} businesses")

        for i, (name, href) in enumerate(places):
            try:
                emit("scrape", f"({i+1}/{total}) {name}")
                driver.get(href)
                try:
                    WebDriverWait(driver, 3).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, 'button[data-item-id="address"], [data-item-id^="phone:"], a[data-item-id="authority"]'))
                    )
                except Exception:
                    time.sleep(0.8)

                biz = _extract_from_place_page(driver, name)
                if biz:
                    businesses.append(biz)
            except Exception:
                continue

    except Exception as e:
        emit("error", str(e))
    finally:
        if driver:
            driver.quit()

    return businesses


def _scroll_results(driver, target_count: int, on_progress=None):
    try:
        scrollable = driver.find_element(By.CSS_SELECTOR, 'div[role="feed"]')
        last_count = 0
        stale_rounds = 0

        for _ in range(20):
            links = [
                l for l in driver.find_elements(By.CSS_SELECTOR, 'a[aria-label]')
                if "/maps/place/" in (l.get_attribute("href") or "")
            ]
            current_count = len(links)

            if on_progress:
                on_progress("scroll", f"Loaded {current_count} results...")

            if current_count >= target_count:
                break
            if current_count == last_count:
                stale_rounds += 1
                if stale_rounds >= 3:
                    break
            else:
                stale_rounds = 0
            last_count = current_count

            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight;", scrollable)
            time.sleep(1)
    except Exception:
        pass


def _extract_from_place_page(driver, name: str) -> Business | None:
    address = ""
    phone = ""
    website = ""
    rating = 0.0
    review_count = 0
    category = ""

    try:
        el = driver.find_element(By.CSS_SELECTOR, 'button[data-item-id="address"]')
        address = " ".join(el.text.split())
    except Exception:
        pass

    try:
        el = driver.find_element(By.CSS_SELECTOR, '[data-item-id^="phone:"]')
        phone = " ".join(el.text.split())
    except Exception:
        pass

    try:
        el = driver.find_element(By.CSS_SELECTOR, 'a[data-item-id="authority"]')
        website = " ".join(el.text.split())
        if not website:
            website = el.get_attribute("href") or ""
    except Exception:
        pass

    try:
        el = driver.find_element(By.CSS_SELECTOR, 'div.F7nice span[aria-hidden="true"]')
        rating = float(el.text.strip().replace(",", "."))
    except Exception:
        pass

    try:
        els = driver.find_elements(By.CSS_SELECTOR, 'div.F7nice span[aria-label]')
        for el in els:
            label = el.get_attribute("aria-label") or ""
            if "review" in label.lower():
                nums = re.findall(r"[\d,]+", label)
                if nums:
                    review_count = int(nums[0].replace(",", ""))
                    break
    except Exception:
        pass

    try:
        el = driver.find_element(By.CSS_SELECTOR, "button.DkEaL")
        category = el.text.strip()
    except Exception:
        pass

    return Business(
        name=name,
        address=address,
        phone=phone,
        website=website,
        rating=rating,
        review_count=review_count,
        category=category,
        source="google_maps",
        has_website=bool(website),
    )
