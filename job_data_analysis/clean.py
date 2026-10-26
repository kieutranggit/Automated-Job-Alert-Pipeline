import pandas as pd
import re

def extract_numbers(text):
    text_clean = text.replace(",", "")
    numbers = re.findall(r'\d+\.?\d*', text_clean)
    return [float(n) for n in numbers]


def deal_salary(text):
    if pd.isna(text):
        return None, None, None

    text = str(text).strip()
    text_lower = text.lower()

    # Case: Thỏa thuận
    if "thỏa thuận" in text_lower or "thoả thuận" in text_lower:
        return None, None, None

    # Xác định đơn vị
    unit = "USD" if ("$" in text or "usd" in text_lower) else "VND"

    # Extracting numbers 
    numbers = extract_numbers(text)
    if not numbers:
        return None, None, unit

    if unit == "USD" and max(numbers) > 10000:
        unit = "VND"
    if unit == "VND" and max(numbers) > 1000:
        return None, None, unit

    # Case: có "tới"/"up to"/"đến" -> chỉ có max
    if "tới" in text_lower or "up to" in text_lower or "đến" in text_lower:
        return None, numbers[0], unit

    # Case: có "trên" -> chỉ có min
    if "trên" in text_lower:
        return numbers[0], None, unit

    # Case: khoảng "X - Y"
    if "-" in text and len(numbers) == 2:
        return numbers[0], numbers[1], unit

    # Case: chỉ có 1 số duy nhất
    if len(numbers) == 1:
        return numbers[0], numbers[0], unit

    return None, None, unit


## Data processing with address

def parse_address(text):
    if pd.isna(text):
        return None, None

    text = str(text).strip()

    #case 1: Nước ngoài 
    if "nước ngoài" in text.lower():
        return "Nước ngoài", None

    #case 2: Toàn Quốc 
    if "toàn quốc" in text.lower():
        return "Toàn Quốc", None

    # Những trường hợp còn lại, ngăn cách bằng dấu ":"
    parts = text.split(":")
    parts = [p.strip() for p in parts]
    cities  = []
    districts = []

    # Processing with one more parts 
    for i in range (0, len(parts), 2):
        city_part = parts[i]
        cities.append(city_part)

        if i + 1 < len(parts):
            district_part = parts[ i + 1]
            districts.append(district_part)

    city = ", ".join(cities)
    district = ", ".join(districts) if districts else None
    return city, district

job_groups = {
    "Backend Developer": ["backend", "back-end", "back end"],
    "Frontend Developer": ["frontend", "front-end", "front end"],
    "Full-stack Developer": ["full stack", "full-stack", "fullstack"],
    ".NET Developer": [".net"],
    "Java Developer": ["java "],
    "PHP Developer": ["php"],
    "Mobile Developer": ["mobile", "ios", "android", "flutter", "react native"],
    "DevOps Engineer": ["devops", "sre", "site reliability"],
    "Data Engineer/Scientist": ["data engineer", "data scientist", "big data"],
    "Data Analyst": ["data analyst", "business analyst", "chuyên viên phân tích"],
    "Tester/QA": ["tester", "qa", "qc", "kiểm thử"],
    "Project Manager": ["project manager", "pm ", "quản lý dự án"],
    "Software Developer": ["developer", "dev", "lập trình", "programmer", "engineer"],
}

def group_job_title(title):
    if pd.isna(title):
        return "Không xác định"
    
    title_lower = str(title).lower()
    
    for group_name, keywords in job_groups.items():
        for kw in keywords:
            if kw in title_lower:
                return group_name
    
    return "Khác"


def main():
    df = pd.read_csv("data.csv")

    df[['min_salary', 'max_salary', 'salary_unit']] = df['salary'].apply(
        lambda x: pd.Series(deal_salary(x))
    )

    df[['city', 'district']] = df['address'].apply(
        lambda x: pd.Series(parse_address(x))
    )

    df['job_group'] = df['job_title'].apply(group_job_title)

    return df


if __name__ == "__main__":
    df = main()

    print(df[['salary', 'min_salary', 'max_salary', 'salary_unit',
              'address', 'city', 'district',
              'job_title', 'job_group']].head(10))

    df.to_csv("data_clean.csv", index=False, encoding="utf-8-sig")
    print("Saved to data_clean.csv")