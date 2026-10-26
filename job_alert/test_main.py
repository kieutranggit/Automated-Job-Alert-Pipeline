"""Tests for the daily job alert. They use fake data only: no internet, no Chrome, no Discord."""
import os
import sqlite3
import tempfile

import pandas as pd

import main


def make_jobs(titles, start=1):
    # Build a small fake crawl result
    rows = []
    for i, title in enumerate(titles):
        rows.append({"job_id": str(start + i), "job_title": title, "company": "Acme",
                     "salary": "Thỏa thuận", "city": "Hà Nội", "exp": "1 năm",
                     "link": f"https://example.com/{start + i}"})
    return pd.DataFrame(rows)


def setup():
    # Every test gets its own empty database file and a fake Discord that records what it was asked to send
    main.DB_NAME = os.path.join(tempfile.mkdtemp(), "test.db")
    main.MIN_JOBS = 1
    main.MAX_ALERTS = 20
    sent = []
    main.send_job_to_discord = lambda job: (sent.append(str(job["job_id"])) or True)
    return sent


def crawl(df, complete=True):
    # Pretend the crawler returned this table
    main.crawl_all_jobs = lambda max_pages=60: (df, complete)


def count_rows():
    # Number of jobs in the database (0 if the table was never created)
    conn = sqlite3.connect(main.DB_NAME)
    try:
        n = conn.execute("SELECT COUNT(*) FROM jobs").fetchone()[0]
    except sqlite3.OperationalError:
        n = 0
    conn.close()
    return n


def owed_ids():
    conn = sqlite3.connect(main.DB_NAME)
    ids = [r[0] for r in conn.execute("SELECT job_id FROM jobs WHERE notified = 0")]
    conn.close()
    return ids


def test_first_run_saves_everything_and_sends_nothing():
    sent = setup()
    crawl(make_jobs(["Data Engineer", "Backend Developer"]))
    main.run()
    assert sent == []
    assert count_rows() == 2


def test_only_new_data_engineer_job_is_sent_once():
    sent = setup()
    first = make_jobs(["Data Engineer", "Backend Developer"])
    crawl(first)
    main.run()                                   # first run = starting list
    today = pd.concat([first, make_jobs(["Senior Data Engineer", "Tester"], start=10)])
    crawl(today)
    main.run()
    assert sent == ["10"]                        # the new Tester job is not sent
    main.run()                                   # same data again
    assert sent == ["10"]                        # no repeated alert


def test_failed_send_is_retried_next_run():
    sent = setup()
    first = make_jobs(["Backend Developer"])
    crawl(first)
    main.run()
    today = pd.concat([first, make_jobs(["Data Engineer"], start=5)])
    crawl(today)
    main.send_job_to_discord = lambda job: False  # Discord is down
    main.run()
    assert owed_ids() == ["5"]                   # the alert is still owed
    main.send_job_to_discord = lambda job: (sent.append(str(job["job_id"])) or True)
    main.run()                                   # Discord works again
    assert sent == ["5"]
    assert owed_ids() == []


def test_incomplete_crawl_changes_nothing():
    sent = setup()
    crawl(make_jobs(["Data Engineer"]), complete=False)
    try:
        main.run()
        assert False, "run() should have raised an error"
    except RuntimeError:
        pass
    assert sent == []
    assert count_rows() == 0


def test_crawl_with_too_few_jobs_is_rejected():
    sent = setup()
    main.MIN_JOBS = 1500
    crawl(make_jobs(["Data Engineer"]))
    try:
        main.run()
        assert False, "run() should have raised an error"
    except RuntimeError:
        pass
    assert count_rows() == 0


def test_same_job_on_two_pages_is_saved_once():
    setup()
    jobs = make_jobs(["Backend Developer", "Tester"])
    crawl(pd.concat([jobs, jobs]))
    main.run()
    assert count_rows() == 2


def test_too_many_new_alerts_are_saved_but_not_sent():
    sent = setup()
    first = make_jobs(["Backend Developer"])
    crawl(first)
    main.run()
    main.MAX_ALERTS = 2
    crawl(pd.concat([first, make_jobs(["Data Engineer"] * 5, start=100)]))
    main.run()
    assert sent == []
    assert count_rows() == 6


def test_old_database_without_notified_column_still_works():
    sent = setup()
    old = make_jobs(["Data Engineer", "Backend Developer"])
    for column in ["min_salary", "max_salary", "salary_unit", "job_group"]:
        old[column] = None
    conn = sqlite3.connect(main.DB_NAME)
    old.to_sql("jobs", conn, index=False)       # a table like the one saved before "notified" existed
    conn.close()
    crawl(old)
    main.run()
    assert sent == []                            # old jobs are not alerted again
    assert owed_ids() == []