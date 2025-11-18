import os
import requests

API_KEY = os.getenv("FNS_API_KEY")

def search_company(query):
    url = "https://api-fns.ru/api/search"
    params = {
        "q": query,       # пример: ИНН, ОГРН или название юрлица
        "key": API_KEY
    }
    r = requests.get(url, params=params)
    r.raise_for_status()
    return r.json()["items"]

# --- Тест запуска ---
if __name__ == "__main__":
    test_inn = "7707083893"  # ИНН Сбербанка (можно подставить любой)
    results = search_company(test_inn)
    for item in results:
        if "ЮЛ" in item:
            print("Полное наименование:", item["ЮЛ"].get("НаимПолнЮЛ"))
            print("ИНН:", item["ЮЛ"].get("ИНН"))
            print("Статус:", item["ЮЛ"].get("Статус"))
            print("Адрес:", item["ЮЛ"].get("АдресПолн"))
            print("-"*40)
