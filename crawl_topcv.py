import random
import time
import pandas as pd
import sqlite3
import undetected_chromedriver as uc
from bs4 import BeautifulSoup
from clean import deal_salary, group_job_title
from discord_notify import send_job_to_discord

DB_NAME = "crawled_jobs.db"

BASE_URL = "https://www.topcv.vn/tim-viec-lam-cong-nghe-thong-tin-cr257"
PARAMS = "sort=new&type_keyword=1&disable_auto_detect_type_keyword=1&category_family=r257&saturday_status=0"


def crawl_all_jobs(max_pages=60):
    """Crawl toàn bộ job, dừng khi hết trang thật hoặc bị chặn."""
    options = uc.ChromeOptions()
    options.add_argument("--start-maximized")

    driver = uc.Chrome(options=options)
    all_jobs = []
    page = 1

    for page in range(1, max_pages + 1):
        if page == 1:
            url = f"{BASE_URL}?{PARAMS}"
        else:
            url = f"{BASE_URL}?{PARAMS}&page={page}"

        print(f"Đang crawl trang {page}: {url}")
        driver.get(url)
        time.sleep(random.uniform(7, 12))

        html = driver.page_source
        soup = BeautifulSoup(html, "html.parser")
        job_cards = soup.find_all("div", class_="job-item-search-result")

        if not job_cards:
            if "Sorry, you have been blocked" in html or "Cloudflare" in html:
                print(f"!!! BỊ CHẶN BỞI CLOUDFLARE ở trang {page}. Dừng crawl, giữ dữ liệu đã thu được.")
            else:
                print(f"Trang {page} không có job -> đã hết dữ liệu thật, dừng crawl.")
            break

        print(f"  -> Tìm thấy {len(job_cards)} job")

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
                continue

        pause = random.uniform(6, 11)
        print(f"  -> Nghỉ {pause:.1f}s trước trang tiếp theo...")
        time.sleep(pause)

    driver.quit()
    print(f"\nTổng cộng crawl được {len(all_jobs)} job, qua {page} trang")
    return pd.DataFrame(all_jobs)


def process_jobs(df):
    df[['min_salary', 'max_salary', 'salary_unit']] = df['salary'].apply(
        lambda x: pd.Series(deal_salary(x))
    )
    df['job_group'] = df['job_title'].apply(group_job_title)
    return df


def get_existing_job_ids():
    try:
        conn = sqlite3.connect(DB_NAME)
        existing = pd.read_sql("SELECT job_id FROM jobs", conn)
        conn.close()
        return set(existing['job_id'].astype(str))
    except Exception:
        return set()


def save_to_db(df, table_name="jobs"):
    conn = sqlite3.connect(DB_NAME)
    try:
        old_df = pd.read_sql(f"SELECT * FROM {table_name}", conn)
        combined = pd.concat([old_df, df], ignore_index=True)
        combined['job_id'] = combined['job_id'].astype(str)
        combined = combined.drop_duplicates(subset='job_id', keep='last')
    except Exception:
        combined = df

    combined.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    print(f"Database hiện có tổng cộng {len(combined)} job (đã loại trùng)")


def run():
    old_ids = get_existing_job_ids()
    print(f"Đã có {len(old_ids)} job trong database từ trước")

    df = crawl_all_jobs(max_pages=60)

    if len(df) == 0:
        print("Không crawl được job nào. Kết thúc.")
        return

    df = process_jobs(df)
    df['job_id'] = df['job_id'].astype(str)

    new_jobs = df[~df['job_id'].isin(old_ids)]
    print(f"Phát hiện {len(new_jobs)} job MỚI (chưa từng thấy)")

    de_new_jobs = new_jobs[new_jobs['job_group'] == 'Data Engineer/Scientist']
    print(f"Trong đó có {len(de_new_jobs)} job Data Engineer mới")

    for _, job in de_new_jobs.iterrows():
        success = send_job_to_discord(job)
        if success:
            print(f"Đã gửi: {job['job_title']}")
        else:
            print(f"Gửi thất bại: {job['job_title']}")

    save_to_db(df)


if __name__ == "__main__":
    run()