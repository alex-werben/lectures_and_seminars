import requests
import os
def check_internet_connection():
    try:
        response = requests.get('https://www.google.com', timeout=5)
        return response.status_code == 200
    except requests.ConnectionError:
        return False
def calculate_days_for_iphone(monthly_salary):
    price = 96980.0
    if not check_internet_connection():
        raise Exception('Нет доступа к интернету')
    if monthly_salary <= 0:
        raise ValueError('Зарплата должна быть больше нуля')
    days_needed = price / (monthly_salary / 22)
    return round(days_needed)
if __name__ == '__main__':
    print(calculate_days_for_iphone(50000))