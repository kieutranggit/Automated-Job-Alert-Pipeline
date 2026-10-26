import pandas as pd
import sqlite3
import matplotlib.pyplot as plt
import seaborn as sns

DB_NAME = "jobs.db"

conn = sqlite3.connect(DB_NAME)
df = pd.read_sql("SELECT * FROM jobs", conn)
conn.close()

print(df.head())
print(df.shape)

df_salary = df.dropna(subset=['min_salary', 'job_group'])


df_vnd = df_salary[df_salary['salary_unit'] == 'VND']
df_usd = df_salary[df_salary['salary_unit'] == 'USD']

print(f"Số dòng VND: {len(df_vnd)}")
print(f"Số dòng USD: {len(df_usd)}")


plt.figure(figsize=(14, 6))
sns.boxplot(data=df_vnd, x='job_group', y='min_salary')
plt.xticks(rotation=45, ha='right')
plt.title("Phân bố mức lương tối thiểu theo nhóm nghề (VND - triệu đồng)")
plt.xlabel("Nhóm nghề")
plt.ylabel("Lương tối thiểu (triệu VND)")
plt.tight_layout()
plt.savefig("chart1a_salary_vnd.png")
plt.show()


plt.figure(figsize=(14, 6))
sns.boxplot(data=df_usd, x='job_group', y='min_salary')
plt.xticks(rotation=45, ha='right')
plt.title("Phân bố mức lương tối thiểu theo nhóm nghề (USD)")
plt.xlabel("Nhóm nghề")
plt.ylabel("Lương tối thiểu (USD)")
plt.tight_layout()
plt.savefig("chart1b_salary_usd.png")
plt.show()


df_map = df.dropna(subset=['city', 'job_group'])


pivot = df_map.pivot_table(
    index='city',
    columns='job_group',
    values='job_title',
    aggfunc='count',
    fill_value=0
)

print(pivot)

df_map = df.dropna(subset=['city', 'job_group'])

pivot = df_map.pivot_table(
    index='city',
    columns='job_group',
    values='job_title',
    aggfunc='count',
    fill_value=0
)
print(f"Số lượng thành phố: {pivot.shape[0]}")
print(f"Số lượng nhóm nghề: {pivot.shape[1]}")


top_cities = df_map['city'].value_counts().head(15).index
pivot_top = pivot.loc[pivot.index.isin(top_cities)]

plt.figure(figsize=(16, 8))
sns.heatmap(pivot_top, annot=True, fmt='d', cmap='YlOrRd', linewidths=0.5)
plt.title("Bản đồ nhiệt: Phân bố việc làm theo khu vực và nhóm nghề")
plt.xlabel("Nhóm nghề")
plt.ylabel("Thành phố")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig("chart2_heatmap_location.png")
plt.show()

from collections import Counter

tech_keywords = [
    "python", "java", "javascript", "php", "c#", ".net",
    "react", "angular", "vue", "node",
    "sql", "mysql", "postgresql", "mongodb",
    "aws", "azure", "docker", "kubernetes",
    "android", "ios", "flutter", "react native",
]

tech_counts = Counter()

for title in df['job_title'].dropna():
    title_lower = str(title).lower()
    for tech in tech_keywords:
        if tech in title_lower:
            tech_counts[tech] += 1

tech_df = pd.DataFrame(tech_counts.items(), columns=['technology', 'count'])
tech_df = tech_df.sort_values('count', ascending=False)

print(tech_df)

plt.figure(figsize=(12, 6))
sns.barplot(data=tech_df, x='count', y='technology', palette='viridis')
plt.title("Xu hướng công nghệ hot trong tuyển dụng")
plt.xlabel("Số lượng tin tuyển dụng nhắc tới")
plt.ylabel("Công nghệ")
plt.tight_layout()
plt.savefig("chart3_tech_trend.png")
plt.show()