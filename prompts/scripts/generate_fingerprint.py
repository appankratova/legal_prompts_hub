import os
import re
from datetime import datetime

def get_next_fingerprint(category: str, prompts_dir: str = "./prompts") -> str:
    """Генерирует следующий fingerprint для категории"""
    year = datetime.now().year
    pattern = rf"LPH-{year}-{category}-(\d{{4}})"
    
    max_num = 0
    for root, dirs, files in os.walk(prompts_dir):
        for file in files:
            if file.endswith(".md"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    content = f.read()
                    matches = re.findall(pattern, content)
                    for match in matches:
                        max_num = max(max_num, int(match))
    
    next_num = str(max_num + 1).zfill(4)
    return f"LPH-{year}-{category}-{next_num}"

# Пример использования
if __name__ == "__main__":
    print(get_next_fingerprint("DUE"))  # Output: LPH-2025-DUE-0001
