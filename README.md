# TopCV Job Data and Daily Job Alert

Two connected parts:

1. **`job_data_analysis/`**: clean, store and analyse IT job listings.
2. **`job_alert/`**: crawl TopCV every day and alert on **new** Data Engineer jobs.

## Result

| | Part 1: job_data_analysis | Part 2: job_alert |
|---|---|---|
| Rows in | 1,933 (`data.csv`) | about 2,800 jobs on the TopCV list |
| Rows out | **1,933** (`data_clean.csv`), none lost | **2,802** jobs saved (`crawled_jobs.db`) |
| New columns | `min_salary`, `max_salary`, `salary_unit`, `city`, `district`, `job_group` | `notified` (added on the first run) |
| Checks | 10 unit tests pass | 8 tests pass, `check_db.py`: 0 duplicate `job_id`, 0 empty `job_id`, `job_title`, `company`, `salary`, `city`, `exp`, `link`, `job_group` |
| Output | `jobs.db` and 4 charts | 29 jobs with "data engineer" in the title |

Salary min and max are empty for jobs with a negotiable salary or only a maximum (for example "Tới 25 triệu"). That is expected, not an error: the original `salary` text is always kept.

## Pipeline

**Part 1**

```
data.csv --clean.py--> data_clean.csv --pipeline.py--> jobs.db --analysis.py--> 4 charts
```

**Part 2**

```
crawl all pages (main.py)
   -> trust check: crawl complete? at least 1,500 jobs?
   -> remove duplicates by job_id
   -> compare with crawled_jobs.db -> new jobs
   -> keep titles containing "data engineer"
   -> send to Discord (discord_notify.py)
   -> mark "notified" only after Discord accepted the message
```

## Reliability (Part 2)

| What can go wrong | What the code does |
|---|---|
| Crawl is blocked half way | Stops with an error and **does not change the database** |
| Crawl is far too small | Fewer than 1,500 jobs is rejected the same way |
| Same job on several pages (promoted jobs) | Removed by `job_id` |
| First run would alert on every old job | First run only saves a starting list and sends nothing |
| Discord is down | The job stays "not notified" and is sent on the next run |
| A bug creates a flood of alerts | More than 20 new Data Engineer jobs in one run are saved, not sent |
| Old database has no `notified` column | Old jobs count as already handled |
| Webhook leaked | Kept in `.env` (ignored by Git) and in a GitHub Secret, never in the code |

## Design decisions

- **Crawl every page every day.** TopCV pins promoted jobs at the top, so "stop at the first job I know" is not reliable.
- **`undetected_chromedriver`.** TopCV is behind Cloudflare: `requests` got 403, and plain Selenium was blocked on page 2.
- **SQLite file committed to the repository.** GitHub Actions machines are deleted after each run, so the list of seen jobs must live in the repo.
- **Save first, then send.** A crash while sending never loses the new jobs.
- **Data Engineer = "data engineer" in the title.** Simple and easy to check.

## Tests

All tests use fake data: no internet, no Chrome, no Discord.

- `job_data_analysis/test_clean.py`: **10 tests** for the cleaning functions.
- `job_alert/test_main.py`: **8 tests**: first run sends nothing; only the new Data Engineer job is sent, once; a failed send is retried; an incomplete crawl changes nothing; a too-small crawl is rejected; duplicates are saved once; too many alerts are saved but not sent; an old database without `notified` still works.

## Project structure

```
├── README.md
├── .gitignore
├── .github/workflows/daily.yml
├── job_data_analysis/
│   ├── data.csv                    raw data
│   ├── clean.py                    step 1: clean
│   ├── pipeline.py                 step 2: load into SQLite
│   ├── analysis.py                 step 3: charts
│   ├── test_clean.py               tests
│   ├── data_clean.csv, jobs.db     outputs
│   └── chart1a, chart1b, chart2, chart3 (.png)
└── job_alert/
    ├── main.py                     crawl, compare, save, alert
    ├── discord_notify.py           send one job to Discord
    ├── check_db.py                 data quality check
    ├── clean.py                    salary parsing, shared with part 1
    ├── test_main.py                tests
    ├── crawled_jobs.db             every job seen so far
    └── requirements.txt
```

## How to run

Each part reads files by name, so run it from inside its own folder.

```bash
# Part 1
pip install pandas matplotlib seaborn pytest
cd job_data_analysis
python clean.py          # data.csv -> data_clean.csv
python pipeline.py       # data_clean.csv -> jobs.db
python analysis.py       # jobs.db -> charts
python -m pytest -q      # 10 passed

# Part 2
cd ../job_alert
pip install -r requirements.txt
python -m pytest -q      # 8 passed
python check_db.py       # data quality check
```

To send alerts, create a `.env` file in the repository root with one line: `DISCORD_WEBHOOK_URL=<your webhook>`, then run `python main.py` from `job_alert/` (needs Google Chrome).

## Known limitations

- **TopCV blocks GitHub's servers.** The crawl works on my own computer. On GitHub Actions, Cloudflare blocked the first page (`Page title: Attention Required! | Cloudflare`, `Sorry, you have been blocked`). The run failed safely: nothing was saved or sent. So the schedule in `daily.yml` cannot work from GitHub's cloud; the job has to run from a machine whose IP Cloudflare accepts, such as my own computer.
- Data Engineer jobs are found by title only, so a title like "Kỹ sư dữ liệu" is missed.
- If TopCV changes its HTML, the crawl returns no jobs and the run fails instead of saving bad data.

*Built with Python, pandas, matplotlib, seaborn, BeautifulSoup, Selenium (undetected-chromedriver), SQLite, GitHub Actions.*