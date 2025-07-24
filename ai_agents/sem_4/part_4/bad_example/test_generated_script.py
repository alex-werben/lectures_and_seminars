from generated_script import check_internet_connection, calculate_days_for_iphone

def test_check_internet_connection():
    assert isinstance(check_internet_connection(), bool)

def test_calculate_days_for_iphone_valid_salary():
    assert calculate_days_for_iphone(50000) == 43

def test_calculate_days_for_iphone_zero_salary():
    try:
        calculate_days_for_iphone(0)
    except Exception as e:
        assert str(e) == 'Зарплата должна быть больше нуля'

def test_calculate_days_for_iphone_negative_salary():
    try:
        calculate_days_for_iphone(-10000)
    except Exception as e:
        assert str(e) == 'Зарплата должна быть больше нуля'