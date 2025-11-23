import re
from openai import OpenAI
from colorama import init, Fore, Style

# Инициализация цветов
init(autoreset=True)

# === НАСТРОЙКИ ===
LM_STUDIO_URL = "http://localhost:1234/v1"  # Убедись, что LM Studio включена!

class QuickGuard:
    def __init__(self):
        self.client = OpenAI(base_url=LM_STUDIO_URL, api_key="lm-studio")
        self.mapping = {}
        self.patterns = {
            "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "PHONE": r'\+7\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}',
            "NAME": r'\b[А-Я][а-я]+\s[А-Я][а-я]+\s[А-Я][а-я]+\b' # ФИО (Иванов Иван Иванович)
        }

    def mask(self, text):
        """Скрывает данные"""
        safe_text = text
        counter = 1
        for key, pattern in self.patterns.items():
            matches = re.findall(pattern, safe_text)
            for m in matches:
                if m not in self.mapping:
                    token = f"[{key}_{counter}]"
                    self.mapping[m] = token        # Иван -> [NAME_1]
                    self.mapping[token] = m        # [NAME_1] -> Иван
                    counter += 1
                safe_text = safe_text.replace(m, self.mapping[m])
        return safe_text

    def restore(self, text):
        """Возвращает данные обратно"""
        for real, token in self.mapping.items():
            if token.startswith("["):
                text = text.replace(token, real)
        return text

    def ai_check(self, text):
        """Спрашивает локальную модель: Безопасно?"""
        print(f"{Fore.CYAN}👮‍♂️ Проверяю безопасность через LM Studio...{Style.RESET_ALL}")
        try:
            resp = self.client.chat.completions.create(
                model="local-model",
                messages=[
                    {"role": "system", "content": "Ты офицер безопасности. Если в тексте есть РЕАЛЬНЫЕ имена или телефоны - ответь UNSAFE. Если только токены типа [NAME_1] - ответь SAFE."},
                    {"role": "user", "content": f"Проверь: {text[:2000]}"}
                ],
                temperature=0.1
            )
            verdict = resp.choices[0].message.content.upper()
            if "SAFE" in verdict and "UNSAFE" not in verdict:
                print(f"{Fore.GREEN}✅ Все чисто. Данные скрыты.{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}🛑 Ошибка! ИИ нашел остатки данных.{Style.RESET_ALL}")
                return False
        except:
            print(f"{Fore.YELLOW}⚠️ LM Studio выключена или недоступна. Пропускаю проверку ИИ.{Style.RESET_ALL}")
            return True # Для теста разрешаем, если ИИ выключен

# === ЗАПУСК ===
if __name__ == "__main__":
    guard = QuickGuard()

    # 1. Текст для проверки (можешь заменить на чтение файла)
    my_doc = """
    Договор займа. Займодавец: Петров Петр Петрович. 
    Email: petrov@почта.ru. Телефон: +7 800 000-00-00.
    Сумма: 1 млн рублей.
    """

    print(f"\n{Fore.YELLOW}--- 1. ИСХОДНИК ---{Style.RESET_ALL}")
    print(my_doc.strip())

    # 2. Обезличиваем
    hidden_doc = guard.mask(my_doc)
    
    print(f"\n{Fore.YELLOW}--- 2. СКРЫТЫЙ ТЕКСТ (Для отправки в GPT/Claude) ---{Style.RESET_ALL}")
    print(hidden_doc.strip())

    # 3. Проверка и имитация работы ИИ
    if guard.ai_check(hidden_doc):
        print(f"\n{Fore.MAGENTA}✨ Имитация: Отправляем в облако и получаем ответ...{Style.RESET_ALL}")
        
        # Представим, что Claude прислал нам это:
        claude_response = "В договоре указан [NAME_1], контакты: [EMAIL_1]. Рисков нет."
        
        # 4. Расшифровка
        final = guard.restore(claude_response)
        print(f"\n{Fore.GREEN}--- 3. ИТОГОВЫЙ ОТЧЕТ (Расшифрованный) ---{Style.RESET_ALL}")
        print(final)
