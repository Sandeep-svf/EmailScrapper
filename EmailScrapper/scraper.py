import re
import time
import html
from datetime import datetime
from bs4 import BeautifulSoup
from scraper.models import EmailScrapeBatch, EmailScrapeJob
import undetected_chromedriver as uc

EMAIL_REGEX = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"

def get_next_batch_name():
    last_batch = EmailScrapeBatch.objects.order_by('-id').first()
    if not last_batch:
        return "RBSH001"
    last_number = int(last_batch.name.replace("RBSH", ""))
    return f"RBSH{str(last_number + 1).zfill(3)}"

def scrape_emails_from_url_list(urls, uploaded_file_name):
    # Prevent concurrent scraping
    if EmailScrapeBatch.objects.filter(status='in_progress').exists():
        return None

    # Create new batch
    batch = EmailScrapeBatch.objects.create(
        name=get_next_batch_name(),
        status='in_progress',
        file_name=uploaded_file_name
    )

    # Pre-create jobs with pending status
    for url in urls:
        EmailScrapeJob.objects.create(batch=batch, url=url, status='pending')

    # Setup headless Chrome for VPS
    options = uc.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-blink-features=AutomationControlled')

    try:
        driver = uc.Chrome(options=options, headless=True)

        for job in batch.jobs.all():
            job.status = 'in_progress'
            job.start_time = datetime.now()
            try:
                driver.get(job.url)
                time.sleep(3)

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                text = soup.get_text()
                raw_emails = re.findall(EMAIL_REGEX, text)

                mailto_links = [a['href'] for a in soup.find_all('a', href=True) if a['href'].startswith("mailto:")]
                mailto_emails = [html.unescape(link)[7:] for link in mailto_links]

                all_emails = set(raw_emails).union(mailto_emails)
                job.emails = ', '.join(all_emails)
                job.status = 'completed'
            except Exception as e:
                job.emails = f"Error: {str(e)}"
                job.status = 'failed'

            job.end_time = datetime.now()
            job.duration = job.end_time - job.start_time
            job.save()

    except Exception as err:
        batch.status = 'failed'
        batch.save()
        raise err

    finally:
        try:
            driver.quit()
        except:
            pass

    batch.status = 'completed'
    batch.save()
    return batch.name
