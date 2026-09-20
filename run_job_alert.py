import schedule
import time
from crawl_topcv import run

def job():
    print("\n===== Đến giờ crawl TopCV =====")
    run()

# Chạy 1 lần/ngày lúc 9h sáng (theo giờ hệ thống máy)
schedule.every().day.at("09:00").do(job)

print("Job Alert Bot đã khởi động, sẽ chạy mỗi ngày lúc 09:00")
print("Nhấn Ctrl+C để dừng chương trình")

while True:
    schedule.run_pending()
    time.sleep(60)