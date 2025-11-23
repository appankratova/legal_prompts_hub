import re
import os
import docx
import pdfplumber  # NEW: Для чтения PDF
from openai import OpenAI

# === ⚙️ НАСТРОЙКИ (для новичков оставляю комментарии по коду)===

OPENAI_API_KEY = "sk-proj-................................"  # Вставьте ключ
INPUT_FILE = "contract.pdf"  # Можно указывать .docx, .txt или .pdf
SYSTEM_PROMPT = """
Ты — старший юрист M&A практики. Проанализируй этот договор.
Твоя задача:
1. Найти существенные риски для покупателя (удели внимание штрафам и расторжению).
2. Кратко резюмировать финансовые обязательства.
В тексте скрыты имена ([NAME_1]) и суммы ([MONEY_1]).
Игнорируй сам факт скрытия, анализируй правовой смысл.
"""

# === КОД ПРОГРАММЫ ===

try:
    from colorama import init, Fore, Style
    init(autoreset=True)
except ImportError:
    class Fore: YELLOW = GREEN = RED = CYAN = MAGENTA = ""
    class Style: RESET_ALL = ""

class LegalPipeline:
    def __init__(self):
        # Локальный клиент (LM Studio)
        self.local_client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
        
        # Облачный клиент (GPT)
        if "sk-" in OPENAI_API_KEY and len(OPENAI_API_KEY) > 20:
            self.cloud_client = OpenAI(api_key=OPENAI_API_KEY)
        else:
            self.cloud_client = None

        self.mapping = {}
        
        self.patterns = {
            "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
            "PHONE": r'(?:\+7|8)[\s\(]*\d{3}[\s\)]*\d{3}[\s-]*\d{2}[\s-]*\d{2}', # Ловит +7 (999) 123-45-67
            "MONEY": r'\d+(?:[\.,]\d+)?\s?(?:млн|тыс|миллионов|тысяч)?\s?(?:руб|RUB|USD|EUR|доллар|евро)[а-я\.]*',
            # Ловит "Иванов Иван Иванович", "Иванов И.И.", "Ivanov Ivan"
            "NAME": r'\b[A-ZА-Я][a-zа-я]+\s+(?:[A-ZА-Я]\.?\s?[A-ZА-Я]\.?|[A-ZА-Я][a-zа-я]+(?:\s+[A-ZА-Я][a-zа-я]+)?)\b'
        }

    def read_document(self, filename):
        if not os.path.exists(filename):
            print(f"{Fore.RED}❌ Файл '{filename}' не найден!{Style.RESET_ALL}")
            return None
        
        ext = filename.lower().split('.')[-1]
        text = ""
        
        try:
            if ext == "docx":
                doc = docx.Document(filename)
                text = "\n".join([p.text for p in doc.paragraphs])
            elif ext == "pdf": # NEW: Обработка PDF
                with pdfplumber.open(filename) as pdf:
                    text = "\n".join([page.extract_text() or "" for page in pdf.pages])
            else: # txt
                with open(filename, "r", encoding="utf-8") as f:
                    text = f.read()
        except Exception as e:
            print(f"{Fore.RED}❌ Ошибка чтения файла: {e}{Style.RESET_ALL}")
            return None
            
        return text

    def mask(self, text):
        """
        NEW: Сортировка по длине. 
        Если мы сначала заменим 'Иванов', а потом попытаемся 'Иванов Иван', будет ошибка.
        Поэтому сначала ищем самые длинные совпадения.
        """
        safe_text = text
        
        # 1. Собираем все находки в список
        matches_found = []
        for p_type, pattern in self.patterns.items():
            for m in re.finditer(pattern, text):
                matches_found.append({
                    "str": m.group(),
                    "type": p_type,
                    "start": m.start(),
                    "len": len(m.group())
                })

        # 2. Сортируем: сначала длинные фразы, чтобы не "разбить" их короткими заменами
        matches_found.sort(key=lambda x: x["len"], reverse=True)

        # 3. Заменяем
        counters = {k: 1 for k in self.patterns.keys()}
        
        for item in matches_found:
            original = item["str"]
            
            # Если это слово уже замаскировано ранее (например, дубль в тексте)
            if original in self.mapping:
                token = self.mapping[original]
            else:
                # Создаем новый токен
                p_type = item["type"]
                token = f"[{p_type}_{counters[p_type]}]"
                self.mapping[original] = token # Сохраняем: Иван -> [NAME_1]
                self.mapping[token] = original # Сохраняем: [NAME_1] -> Иван
                counters[p_type] += 1
            
            # Замена в тексте
            # Внимание: replace заменяет ВСЕ вхождения. 
            # Это нормально для простых документов, но может быть избыточно.
            safe_text = safe_text.replace(original, token)

        return safe_text

    def restore(self, text):
        # NEW: Восстанавливаем данные (сначала длинные токены, если бы они были, но тут важнее просто пройтись по всем)
        for token, real in self.mapping.items():
            if token.startswith("[") and token.endswith("]"):
                text = text.replace(token, real)
        return text

    def gatekeeper_check(self, text):
        print(f"{Fore.CYAN}👮‍♂️ Гейткипер анализирует безопасность...{Style.RESET_ALL}")
        try:
            # Проверяем случайные куски текста, а не только начало, чтобы поймать данные в футере
            snippet = text[:1000] + "\n...\n" + text[len(text)//2 : len(text)//2+1000]
            
            resp = self.local_client.chat.completions.create(
                model="local-model",
                messages=[
                    {"role": "system", "content": "You are a security auditor. Check text for PII (Names, Phones, Emails). Ignore tokens like [NAME_1]. If REAL PII found -> UNSAFE. If clean -> SAFE. Output ONLY one word."},
                    {"role": "user", "content": f"Check this:\n{snippet}"}
                ],
                temperature=0.0
            )
            verdict = resp.choices[0].message.content.strip().upper()
            
            if "SAFE" in verdict and "UNSAFE" not in verdict:
                print(f"{Fore.GREEN}✅ Гейткипер: Утечек не обнаружено.{Style.RESET_ALL}")
                return True
            else:
                print(f"{Fore.RED}🛑 Гейткипер: Обнаружены подозрительные данные!{Style.RESET_ALL}")
                print(f"Вердикт модели: {verdict}")
                return False
        except Exception as e:
            print(f"{Fore.YELLOW}⚠️ Локальная модель недоступна: {e}{Style.RESET_ALL}")
            # NEW: Предлагаем выбор пользователю
            user_choice = input(f"{Fore.YELLOW}Продолжить без проверки Гейткипера? (y/n): {Style.RESET_ALL}")
            return user_choice.lower() == 'y'

    def send_to_gpt(self, safe_text):
        if not self.cloud_client:
            return "❌ ОШИБКА: Нет API ключа OpenAI."

        # Оценка стоимости (грубая)
        tokens_est = len(safe_text) / 4
        price_est = (tokens_est / 1000) * 0.03 # Примерно $0.03 за 1к токенов (GPT-4 input)
        print(f"{Fore.MAGENTA}🚀 Отправка в GPT-4 (~{int(tokens_est)} токенов, ~${price_est:.4f})...{Style.RESET_ALL}")
        
        try:
            completion = self.cloud_client.chat.completions.create(
                model="gpt-4o", 
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": safe_text}
                ],
                temperature=0.3 # Понизили температуру для большей точности
            )
            return completion.choices[0].message.content
        except Exception as e:
            return f"Ошибка API OpenAI: {e}"

# === ЗАПУСК ===
if __name__ == "__main__":
    pipeline = LegalPipeline()

    print(f"📂 Читаю файл: {INPUT_FILE}...")
    original_text = pipeline.read_document(INPUT_FILE)

    if original_text:
        # 1. Маскировка
        masked_text = pipeline.mask(original_text)
        unique_entities = len([k for k in pipeline.mapping.keys() if not k.startswith("[")])
        print(f"{Fore.YELLOW}--- Текст обезличен (скрыто {unique_entities} уникальных сущностей) ---{Style.RESET_ALL}")
        
        # Для отладки можно сохранить маскированный текст
        # with open("debug_masked.txt", "w", encoding="utf-8") as f: f.write(masked_text)

        # 2. Гейткипер (с возможностью ручного пропуска)
        is_safe = pipeline.gatekeeper_check(masked_text)
        
        if not is_safe:
             # Если Гейткипер сказал НЕТ, спросим человека (Override)
             choice = input(f"{Fore.RED}⚠️ Внимание! Гейткипер заблокировал отправку. Вы хотите отправить принудительно? (yes/no): {Style.RESET_ALL}")
             if choice.lower() == "yes":
                 is_safe = True

        if is_safe:
            # 3. Облако
            cloud_response = pipeline.send_to_gpt(masked_text)
            
            # 4. Восстановление
            final_report = pipeline.restore(cloud_response)
            
            print(f"\n{Fore.GREEN}📝 === ЮРИДИЧЕСКОЕ ЗАКЛЮЧЕНИЕ === {Style.RESET_ALL}")
            print(final_report)
            
            with open("LEGAL_OPINION.txt", "w", encoding="utf-8") as f:
                f.write(final_report)
            print(f"\n💾 Результат сохранен в LEGAL_OPINION.txt")
        else:
            print("⛔ Отправка отменена пользователем или системой безопасности.")
