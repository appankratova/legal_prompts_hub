import os
import requests
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("FNS_API_KEY")

if not API_KEY:
    raise RuntimeError("FNS_API_KEY не найден в .env")

def search_company(query):
    url = "https://api-fns.ru/api/search"
    params = {"q": query, "key": API_KEY}
    r = requests.get(url, params=params)

    if r.status_code != 200:
        print("HTTP статус:", r.status_code)
        print("Тело ответа:")
        print(r.text[:500])
        raise RuntimeError("Запрос к API-ФНС завершился ошибкой")

    data = r.json()
    return data["items"]

if __name__ == "__main__":
    test_inn = "7707083893"
    results = search_company(test_inn)

    # Фильтруем только действующее юрлицо с нужным ИНН
    active_matches = []
    for item in results:
        company = item.get("ЮЛ")
        if not company:
            continue
        if company.get("ИНН") != test_inn:
            continue
        if company.get("Статус") != "Действующее":
            continue
        active_matches.append(company)

    if not active_matches:
        print("Действующая компания с ИНН", test_inn, "не найдена")
    else:
        company = active_matches[0]  # берём первую подходящую
        print('Название:', company.get('НаимПолнЮЛ'))
        print('ИНН:', company.get('ИНН'))
        print('Статус:', company.get('Статус'))
        print('Адрес:', company.get('АдресПолн'))
