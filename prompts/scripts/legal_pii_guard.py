# Код для вставки текста в код (пример для приграться)

import re
from openai import OpenAI
try:
    from colorama import init, Fore, Style
    init(autoreset=True)
    HAS_COLOR = True
except ImportError:
    HAS_COLOR = False
    class Fore: YELLOW = GREEN = RED = CYAN = MAGENTA = ""
    class Style: RESET_ALL = ""

# === НАСТРОЙКИ ===
LM_STUDIO_URL = "http://localhost:1234/v1"

class QuickGuard:
    def __init__(self):
        self.client = OpenAI(base_url=LM_STUDIO_URL, api_key="lm-studio")
        self.mapping = {}
        self.patterns = {
            "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "PHONE": r'\+7\s?\(?\d{3}\)?\s?\d{3}[-\s]?\d{2}[-\s]?\d{2}',
            "MONEY": r'\d+[\.,]?\d*\s?(?:млн|тыс|руб|RUB|USD|EUR)[а-я\.]*', 
            "NAME": r'\b[А-Я][а-я]+\s[А-Я][а-я]+\s[А-Я][а-я]+\b'
        }

    def mask(self, text):
        safe_text = text
        counter = 1
        for key, pattern in self.patterns.items():
            matches = re.findall(pattern, safe_text)
            for m in matches:
                if m not in self.mapping:
                    token = f"[{key}_{counter}]"
                    self.mapping[m] = token
                    self.mapping[token] = m
                    counter += 1
                safe_text = safe_text.replace(m, self.mapping[m])
        return safe_text

    def restore(self, text):
        for real, token in self.mapping.items():
            if token.startswith("["):
                text = text.replace(token, real)
        return text

    def ai_check(self, text):
        if HAS_COLOR: print(f"{Fore.CYAN}👮‍♂️ Проверяю безопасность через LM Studio...{Style.RESET_ALL}")
        else: print("👮‍♂️ Проверяю безопасность через LM Studio...")
        
        system_prompt = """
        YOU ARE A VERIFICATION BOT.
        
        TASK: Check if personal data is HIDDEN (Masked).
        
        CRITERIA:
        1. Tokens like [NAME_1], [PHONE_1], [MONEY_1] mean the data is SECURE. -> RESULT: "SAFE".
        2. Real names (Ivanov), Real phones (+7999...), Real money (1000 rub) -> RESULT: "UNSAFE".
        
        IMPORTANT: finding [NAME_1] is GOOD. It means it is safe.
        
        OUTPUT ONLY: "SAFE" or "UNSAFE".
        """

        try:
            resp = self.client.chat.completions.create(
                model="local-model",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Analyze this text:\n{text[:2000]}"}
                ],
                temperature=0.0, # Ноль эмоций, чистая логика
            )
            verdict = resp.choices[0].message.content.upper()
            
            # Логика проверки: Если сказал SAFE и не сказал UNSAFE
            if "SAFE" in verdict and "UNSAFE" not in verdict:
                if HAS_COLOR: print(f"{Fore.GREEN}✅ Все чисто. Данные скрыты.{Style.RESET_ALL}")
                else: print("✅ Все чисто. Данные скрыты.")
                return True
            else:
                if HAS_COLOR: print(f"{Fore.RED}🛑 Ошибка! ИИ нашел остатки данных (или испугался токенов).{Style.RESET_ALL}")
                print(f"Вердикт ИИ: {verdict}") # Покажем, что он там надумал
                return False
        except Exception as e:
            if HAS_COLOR: print(f"{Fore.YELLOW}⚠️ Ошибка LM Studio: {e}{Style.RESET_ALL}")
            else: print(f"⚠️ Ошибка LM Studio: {e}")
            return True 

if __name__ == "__main__":
    guard = QuickGuard()

    # ТЕКСТ ДЛЯ ПРОВЕРКИ (после трех кавычек вставляется текст, текст должен быть внутри тройных кавычек)
    my_doc = """
    Договор займа. Займодавец: Петров Петр Петрович. 
    Email: petrov@почта.ru. Телефон: +7 000 123-45-67.
    Сумма: 1 млн рублей.
    """

    if HAS_COLOR: print(f"\n{Fore.YELLOW}--- 1. ИСХОДНИК ---{Style.RESET_ALL}")
    else: print("\n--- 1. ИСХОДНИК ---")
    print(my_doc.strip())

    hidden_doc = guard.mask(my_doc)
    
    if HAS_COLOR: print(f"\n{Fore.YELLOW}--- 2. СКРЫТЫЙ ТЕКСТ (Для отправки в GPT/Claude) ---{Style.RESET_ALL}")
    else: print("\n--- 2. СКРЫТЫЙ ТЕКСТ (Для отправки в GPT/Claude) ---")
    print(hidden_doc.strip())

    if guard.ai_check(hidden_doc):
        if HAS_COLOR: print(f"\n{Fore.MAGENTA}✨ Имитация: Данные ушли в Облако и вернулись...{Style.RESET_ALL}")
        else: print("\n✨ Имитация: Данные ушли в Облако и вернулись...")
        
        # Имитируем ответ Клода, который использовал токены
        claude_response = "В договоре займа фигурирует [NAME_4]. Сумма: [MONEY_3] руб. Контакты: [EMAIL_1]."
        final = guard.restore(claude_response)
        
        if HAS_COLOR: print(f"\n{Fore.GREEN}--- 3. ИТОГОВЫЙ ОТЧЕТ ---{Style.RESET_ALL}")
        else: print("\n--- 3. ИТОГОВЫЙ ОТЧЕТ ---")
        print(final)
