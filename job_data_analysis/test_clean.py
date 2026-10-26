from clean import deal_salary, parse_address, group_job_title


def test_deal_salary_thoa_thuan():
    result = deal_salary("Thỏa thuận")
    assert result == (None, None, None)


def test_deal_salary_khoang():
    result = deal_salary("10 - 20 triệu")
    assert result == (10.0, 20.0, "VND")


def test_deal_salary_toi():
    result = deal_salary("Tới 35 triệu")
    assert result == (None, 35.0, "VND")


def test_deal_salary_tren():
    result = deal_salary("Trên 10 triệu")
    assert result == (10.0, None, "VND")


def test_deal_salary_usd():
    result = deal_salary("2,500 - 3,000 USD")
    assert result == (2500.0, 3000.0, "USD")



def test_parse_address_binh_thuong():
    result = parse_address("Hà Nội: Cầu Giấy")
    assert result == ("Hà Nội", "Cầu Giấy")


def test_parse_address_toan_quoc():
    result = parse_address("Toàn Quốc")
    assert result == ("Toàn Quốc", None)


def test_parse_address_nuoc_ngoai():
    result = parse_address("Nước ngoài")
    assert result == ("Nước ngoài", None)



def test_group_job_title_backend():
    result = group_job_title("Senior Backend Developer")
    assert result == "Backend Developer"


def test_group_job_title_unknown():
    result = group_job_title("Nhân viên pha chế")
    assert result == "Khác"