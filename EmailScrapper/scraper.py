import re
import time
import html
import shutil
import os
from datetime import datetime
from bs4 import BeautifulSoup
from scraper.models import EmailScrapeBatch, EmailScrapeJob
import undetected_chromedriver as uc
from selenium_stealth import stealth
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"

def get_next_batch_name():
    last_batch = EmailScrapeBatch.objects.order_by('-id').first()
    if not last_batch:
        return "RBSH001"
    last_number = int(last_batch.name.replace("RBSH", ""))
    return f"RBSH{str(last_number + 1).zfill(3)}"




def get_stealth_driver():

    chromium_path = "/snap/bin/chromium"

    user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.7339.207 Safari/537.36"

    options = uc.ChromeOptions()
    options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument(f"user-agent={user_agent}")
    options.add_argument("--start-maximized")

    # ⛑ If you're running as root, this flag is critical
    options.add_argument("--no-zygote")

    driver = uc.Chrome(driver_executable_path=chromium_path, options=options, use_subprocess=True)

    stealth(driver,
            languages=["en-US", "en"],
            vendor="Google Inc.",
            platform="Win32",
            webgl_vendor="Intel Inc.",
            renderer="Intel Iris OpenGL Engine",
            fix_hairline=True)

    return driver



def scrape_job(job):
    driver = None
    job.start_time = datetime.now()

    try:
        driver = get_stealth_driver()
        job.status = 'in_progress'

        print(f" Scraping: {job.url}")
        driver.get(job.url)

        print(" Waiting for JS to render...")
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(5)

        try:
            html_content = driver.page_source
            soup = BeautifulSoup(html_content, 'html.parser')

            try:
                print(" Page title:", driver.title)
            except:
                print(" Page title: [window closed early]")

            print(" First 10 chars of body:", soup.get_text()[:10])

            text = soup.get_text()
            raw_emails = re.findall(EMAIL_REGEX, text)
            mailto_links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith("mailto:")]
            mailto_emails = [html.unescape(link)[7:] for link in mailto_links]

            all_emails = set(raw_emails + mailto_emails)
            print(f" Found: {all_emails}")

            job.emails = ', '.join(all_emails)
            job.status = 'completed'

        except Exception as parse_err:
            job.emails = f"Parse Error: {str(parse_err)}"
            job.status = 'failed'
            print(f" Parse error on {job.url}: {parse_err}")

    except Exception as e:
        job.emails = f"Error: {str(e)}"
        job.status = 'failed'
        print(f" Error scraping {job.url}: {e}")

    finally:
        try:
            time.sleep(1)
            if driver:
                driver.quit()
        except:
            pass

        #  Clean up temp files right after each job to save space
        clean_temp_dirs()

        job.end_time = datetime.now()
        job.duration = job.end_time - job.start_time if job.start_time else None
        job.save()


def clean_temp_dirs():
    paths = [
        "/root/.local/share/undetected_chromedriver",
        "/root/.config/google-chrome",
        "/root/.config/chromium"
    ]
    for path in paths:
        try:
            if os.path.exists(path):
                shutil.rmtree(path)
                print(f"Cleaned: {path}")
        except Exception as e:
            print(f"Cleanup failed at {path}: {e}")


def scrape_emails_from_url_list(urls, uploaded_file_name):
    if EmailScrapeBatch.objects.filter(status='in_progress').exists():
        print(" Another batch is already in progress.")
        return None

    batch = EmailScrapeBatch.objects.create(
        name=get_next_batch_name(),
        status='in_progress',
        file_name=uploaded_file_name
    )

    for url in urls:
        EmailScrapeJob.objects.create(batch=batch, url=url, status='pending')

    try:
        for job in batch.jobs.all():
            scrape_job(job)

    except Exception as err:
        print(f" Fatal scraping error: {err}")
        for job in batch.jobs.filter(status__in=['pending', 'in_progress']):
            job.status = 'failed'
            job.end_time = datetime.now()
            job.duration = None
            job.emails = f"Batch failed due to: {str(err)}"
            job.save()
        batch.status = 'failed'
        batch.save()
        raise err

    try:
        batch.status = 'completed' if not batch.jobs.filter(status='failed').exists() else 'completed_with_errors'
        batch.save()
        print(f"\n Batch {batch.name} finished.")
    except Exception as e:
        print(f" Failed to update batch status: {e}")

    clean_temp_dirs()
    return batch.name
