import pandas as pd
import sqlite3
from clean import main

DB_NAME = "jobs.db"


def load_to_db(df, table_name="jobs"):
    conn = sqlite3.connect(DB_NAME)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
    print(f"Đã load {len(df)} dòng vào bảng '{table_name}' trong {DB_NAME}")


def run_pipeline():
    try:
        df_clean = main()
        load_to_db(df_clean)
        print("Pipeline chạy thành công!")
    except FileNotFoundError:
        print("Lỗi: Không tìm thấy file data.csv")
    except Exception as e:
        print(f"Lỗi không xác định: {e}")


if __name__ == "__main__":
    run_pipeline()