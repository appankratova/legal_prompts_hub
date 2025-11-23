import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pii_guard.protection import LegalPIIGuard
from colorama import Fore, Style

def load_prompt(category, filename):
    """Загружает промпт из твоей структуры папок"""
    path = os.path.join("prompts", category, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        return "Проанализируй этот текст и найди риски."

def main():
    # Инициализация защиты
    guard = LegalPIIGuard(lm_studio_url="http://localhost:1234/v1")
    
    # Пример: Работаем с M&A сделкой
    # 1. Загружаем твой профессиональный промпт
    system_prompt = load_prompt("mna", "risk_analysis.md") # Предположим, он там есть
    
    # 2. Читаем грязный документ
    doc_text = """
    Покупатель: ООО "Ромашка" (ИНН 7700000000). 
    Сумма сделки: 100 млн рублей. Директор Иванов И.И.
    """
    
    print(f"{Fore.YELLOW}--- 1. МАСКИРОВКА ДАННЫХ ---{Style.RESET_ALL}")
    safe_text = guard.mask_text(doc_text)
    print(safe_text)
    
    # 3. Гейткипер
    if guard.ai_gatekeeper(safe_text):
        print(f"\n{Fore.MAGENTA}--- 2. ОТПРАВКА В AI С ТВОИМ ПРОМПТОМ ---{Style.RESET_ALL}")
        # Здесь код отправки в Claude/GPT с использованием system_prompt
        # ...
        print("Имитация анализа...")
        
        # 4. Восстановление
        fake_response = "Риск: Компания [COMPANY_1] имеет плохую кредитную историю."
        final = guard.restore_text(fake_response)
        print(f"\n{Fore.GREEN}--- 3. РЕЗУЛЬТАТ ---{Style.RESET_ALL}")
        print(final)

if __name__ == "__main__":
    main()
