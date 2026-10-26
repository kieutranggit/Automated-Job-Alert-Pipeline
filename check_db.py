import sqlite3
import pandas as pd

conn = sqlite3.connect("crawled_jobs.db")
df = pd.read_sql("SELECT * FROM jobs", conn)
conn.close()

print("So dong, so cot:", df.shape)
print("Ten cot:", df.columns.tolist())
print("So job_id bi trung:", df["job_id"].duplicated().sum())
print("So o bi thieu moi cot:")
print(df.isna().sum())

print(df[df["min_salary"].isna() & df["salary_unit"].notna()]["salary"].head(5))
print("So job Data Engineer:", df["job_title"].str.lower().str.contains("data engineer").sum())