import os
import random
import time
import pandas as pd
import sqlite3
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from clean import deal_salary, group_job_title
from discord_notify import send_job_to_discord

DB_NAME = "crawled_jobs.db"

# The list has about 2,800 jobs; far fewer means the crawl was cut short
MIN_JOBS = 1500

# If more new Data Engineer jobs than this show up in one run, something is wrong
MAX_ALERTS = 20

# The IT job list on TopCV, newest jobs first (sort=new)
BASE_URL = "https://www.topcv.vn/tim-viec-lam-cong-nghe-thong-tin-cr257"
PARAMS = "sort=new&type_keyword=1&disable_auto_detect_type_keyword=1&category_family=r257&saturday_status=0"


def crawl_all_jobs(max_pages=60):
    """Crawl every page of the job list.
    Returns (jobs table, complete). complete is True only if we reached the real end of the list."""
    # undetected_chromedriver is used because plain Selenium gets blocked by Cloudflare
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")

    # On GitHub Actions the workflow sets CHROME_MAJOR (for example 155) so the downloaded
    # driver matches the installed Chrome. On your own computer it is not set, so we use None.
    chrome_major = os.getenv("CHROME_MAJOR")
    version_main = int(chrome_major) if chrome_major else None
    driver = uc.Chrome(options=options, version_main=version_main)

    all_jobs = []
    page = 1
    complete = False  # stays False if we get blocked, so a partial crawl is never trusted

    for page in range(1, max_pages + 1):
        # Page 1 has no &page= parameter, later pages do
        if page == 1:
            url = f"{BASE_URL}?{PARAMS}"
        else:
            url = f"{BASE_URL}?{PARAMS}&page={page}"

        print(f"Crawling page {page}: {url}")
        driver.get(url)
        time.sleep(random.uniform(7, 12))  # wait for the page to load, random so we look less like a bot

        # Each job on the page is a <div class="job-item-search-result">
        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        job_cards = soup.find_all("div", class_="job-item-search-result")

        # Cloudflare's "Just a moment" check page can pass by itself, so wait once and look again
        if not job_cards and "Just a moment" in html:
            print("Cloudflare check page. Waiting 30 seconds and looking again...")
            time.sleep(30)
            html = driver.page_source
            soup = BeautifulSoup(html, "html.parser")
            job_cards = soup.find_all("div", class_="job-item-search-result")

        # No job cards: either we are blocked, or we passed the last page
        if not job_cards:
            # Show what the page says, so we can tell a block from a normal empty page
            print(f"Page title: {driver.title}")
            print(f"First 300 characters of the page: {soup.get_text(' ', strip=True)[:300]}")
            if "Sorry, you have been blocked" in html or "Just a moment" in html:
                print(f"!!! Blocked by Cloudflare on page {page}. Stopping.")
            else:
                print(f"Page {page} has no jobs -> reached the end of the list.")
                complete = True
            break

        print(f"  -> Found {len(job_cards)} jobs")

        # Read the fields we need from each job card
        for card in job_cards:
            try:
                job_id = card.get("data-job-id")
                title_tag = card.find("h3", class_="title").find("a")
                job_title = title_tag.find("span").get_text(strip=True)
                link = title_tag.get("href")
                company = card.find("span", class_="company-name").get_text(strip=True)
                salary = card.find("label", class_="title-salary").get_text(strip=True)
                city = card.find("span", class_="city-text").get_text(strip=True)
                exp = card.find("label", class_="exp").get_text(strip=True)

                all_jobs.append({
                    "job_id": job_id, "job_title": job_title, "company": company,
                    "salary": salary, "city": city, "exp": exp, "link": link
                })
            except AttributeError:
                continue  # skip a card that is missing a field instead of crashing

        # Pause between pages to avoid being blocked
        pause = random.uniform(6, 11)
        print(f"  -> Waiting {pause:.1f}s before the next page...")
        time.sleep(pause)

    driver.quit()
    print(f"\nCrawled {len(all_jobs)} jobs in total, stopped at page {page}")
    return pd.DataFrame(all_jobs), complete


def process_jobs(df):
    # Split the salary text into min, max and unit, and label each job with a group
    df[['min_salary', 'max_salary', 'salary_unit']] = df['salary'].apply(
        lambda x: pd.Series(deal_salary(x))
    )
    df['job_group'] = df['job_title'].apply(group_job_title)
    return df


def get_existing_job_ids():
    # Return the set of job_ids already saved in the database (empty set if there is no database yet)
    try:
        conn = sqlite3.connect(DB_NAME)
        existing = pd.read_sql("SELECT job_id FROM jobs", conn)
        conn.close()
        return set(existing['job_id'].astype(str))
    except Exception:
        return set()


def save_to_db(new_jobs, table_name="jobs"):
    # Add the new jobs to the table. Jobs already in the table are never touched.
    # The column "notified" means: 1 = nothing left to send, 0 = a Discord alert is still owed.
    conn = sqlite3.connect(DB_NAME)
    try:
        old_df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        combined = pd.concat([old_df, new_jobs], ignore_index=True)
    except Exception:
        combined = new_jobs

    combined['job_id'] = combined['job_id'].astype(str)
    # Rows saved before this column existed were already handled, so they count as notified
    combined['notified'] = combined['notified'].fillna(1).astype(int)
    combined = combined.drop_duplicates(subset='job_id', keep='first')

    combined.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    print(f"Database now holds {len(combined)} jobs")


def send_owed_alerts():
    # Send every alert that is still owed, including ones that failed on earlier days.
    # A job is marked as notified ONLY after Discord accepted it.
    conn = sqlite3.connect(DB_NAME)
    owed = pd.read_sql("SELECT * FROM jobs WHERE notified = 0", conn)
    print(f"{len(owed)} alerts to send")

    for _, job in owed.iterrows():
        success = send_job_to_discord(job)
        if success:
            conn.execute("UPDATE jobs SET notified = 1 WHERE job_id = ?", (job['job_id'],))
            conn.commit()
            print(f"Sent: {job['job_title']}")
            time.sleep(1)  # stay under Discord's rate limit
        else:
            print(f"Failed to send, will retry next run: {job['job_title']}")
    conn.close()


def run():
    old_ids = get_existing_job_ids()
    print(f"{len(old_ids)} jobs already in the database")

    df, complete = crawl_all_jobs(max_pages=60)

    # Do not trust a crawl that was cut short: the jobs it missed would look "new" on the next run
    if not complete or len(df) < MIN_JOBS:
        # Raising an error makes the GitHub Actions run turn red, so you notice
        raise RuntimeError(f"Crawl not trusted (complete={complete}, jobs={len(df)}). Database not changed.")

    df = process_jobs(df)
    df['job_id'] = df['job_id'].astype(str)
    df = df.drop_duplicates(subset='job_id')  # promoted jobs can appear on several pages

    # A job is new if its job_id is not in the database yet
    new_jobs = df[~df['job_id'].isin(old_ids)].copy()
    print(f"Found {len(new_jobs)} NEW jobs")

    # A job is a Data Engineer job if its title contains "data engineer" (any upper/lower case)
    is_data_engineer = new_jobs['job_title'].str.lower().str.contains("data engineer")
    print(f"{is_data_engineer.sum()} of them are Data Engineer jobs")

    # Start with "nothing owed" (notified = 1), then mark the Data Engineer jobs as owed (notified = 0)
    new_jobs['notified'] = 1
    first_run = len(old_ids) == 0
    if first_run:
        print("First run: saving all jobs as the starting list, no alerts sent.")
    elif is_data_engineer.sum() > MAX_ALERTS:
        print(f"WARNING: more than {MAX_ALERTS} new Data Engineer jobs. Saved without alerts.")
    else:
        new_jobs.loc[is_data_engineer, 'notified'] = 0

    # Save first, then send, so a crash while sending never loses the new jobs
    save_to_db(new_jobs)
    send_owed_alerts()


if __name__ == "__main__":
    run()