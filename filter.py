import json
import ollama
from pathlib import Path
import re

BASE_DIR = Path(__file__).parent


def normalize(text):
    return re.sub(r"\s+", " ", text.lower()).strip()


# ---------------- MEMORY ----------------

def load_memory():
    path = BASE_DIR / "config" / "memory.json"

    if not path.exists():
        return []

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except:
        return []


def tokenize(text):
    return set(re.findall(r"[a-zа-яё0-9]+", normalize(text)))

def keyword_signal(text, keywords):
    text_norm = normalize(text)
    text_tokens = tokenize(text)

    best_score = 0
    best_keyword = None

    for keyword in keywords:
        keyword_norm = normalize(keyword)
        keyword_tokens = tokenize(keyword)

        if not keyword_tokens:
            continue

        if keyword_norm in text_norm:
            return {
                "matched": True,
                "keyword": keyword,
                "score": 1
            }

        intersection = text_tokens.intersection(keyword_tokens)
        score = len(intersection) / len(keyword_tokens)

        if score > best_score:
            best_score = score
            best_keyword = keyword

    if best_score >= 0.5:
        return {
            "matched": True,
            "keyword": best_keyword,
            "score": best_score
        }

    return {
        "matched": False,
        "keyword": None,
        "score": best_score
    }


def looks_like_private_message(text):
    tokens = tokenize(text)

    if len(tokens) <= 2:
        return True

    return False


def similarity(text1, text2):
    tokens1 = tokenize(text1)
    tokens2 = tokenize(text2)

    if not tokens1 or not tokens2:
        return 0

    intersection = tokens1.intersection(tokens2)
    union = tokens1.union(tokens2)

    return len(intersection) / len(union)


def find_memory_match(text, memory):
    best_match = None
    best_score = 0

    for item in memory:
        memory_text = item.get("text")
        rating = item.get("rating")

        if not memory_text or rating not in ("good", "bad"):
            continue

        current_score = similarity(text, memory_text)

        if current_score > best_score:
            best_score = current_score
            best_match = item

    if not best_match:
        return None

    if best_score >= 0.75:
        return {
            "item": best_match,
            "similarity": best_score
        }

    return None


def save_memory(item):
    path = BASE_DIR / "config" / "memory.json"

    memory = load_memory()

    memory.append({
      "text": item.text,
      "lead": item.lead
    })

    memory = memory[-200:]

    path.write_text(
        json.dumps(memory, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )


# ---------------- CONFIG ----------------

def load_lines(filename):
    path = BASE_DIR / "config" / filename

    if not path.exists():
        return []

    with open(path, "r", encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


def load_text(filename):
    path = BASE_DIR / "config" / filename

    if not path.exists():
        return ""

    return path.read_text(encoding="utf-8").strip()


KEYWORDS = load_lines("keywords.txt")
BLACKLIST = load_lines("blacklist.txt")
ABOUT = load_text("about.txt")


# ---------------- CORE ----------------

def is_lead(text):
    if not text:
        return None

    memory = load_memory()
    text_norm = normalize(text)

    # -------- blacklist fast path --------
    for word in BLACKLIST:
        word_norm = normalize(word)

        if word_norm in text_norm:
            print("⛔ BLACKLIST:", word)
            return {
                "lead": 0,
                "score": 0,
                "text": text
            }

    # -------- memory hard override --------
    memory_match = find_memory_match(text, memory)

    if memory_match:
        matched_item = memory_match["item"]
        rating = matched_item.get("rating")
        similarity_score = memory_match["similarity"]

        print(
            "🧠 MEMORY MATCH:",
            rating,
            round(similarity_score, 2),
            matched_item.get("text")
        )

        if rating == "bad":
            return {
                "lead": 0,
                "score": 0,
                "text": text
            }

        if rating == "good":
            return {
                "lead": 1,
                "score": max(int(matched_item.get("score", 80)), 60),
                "text": text
            }

    # -------- keyword signal fast path --------
    signal = keyword_signal(text, KEYWORDS)

    if signal["matched"]:
        print(
            "✅ KEYWORD SIGNAL:",
            signal["keyword"],
            round(signal["score"], 2)
        )
    else:
        print("ℹ️ NO KEYWORD SIGNAL, sending to Ollama:", text)

    # -------- examples from memory --------
    memory_examples = []
    for m in memory[-50:]:
        rating = m.get("rating")

        if rating == "good":
            expected_lead = 1
            expected_score = max(int(m.get("score", 80)), 60)
        elif rating == "bad":
            expected_lead = 0
            expected_score = 0
        else:
            continue

        memory_examples.append({
            "message": m.get("text"),
            "user_rating": rating,
            "expected_json": {
                "lead": expected_lead,
                "score": expected_score
            }
        })

    # -------- prompt --------
    prompt = f"""
Ты классификатор лидов.

Тебе нужно определить, является ли сообщение потенциальным клиентом для компании.

КОМПАНИЯ:
{ABOUT}

КЛЮЧЕВЫЕ ТЕМЫ:
{chr(10).join(KEYWORDS)}

РЕЗУЛЬТАТ ПОИСКА КЛЮЧЕВОГО СИГНАЛА:
{json.dumps(signal, ensure_ascii=False, indent=2)}

ВАЖНО:
- Отсутствие точного совпадения с ключевыми темами НЕ означает, что сообщение не лид.
- Если в сообщении есть явный запрос, намерение купить услугу, просьба помочь, срочность, вопрос "кто может", "сколько стоит", "нужно сделать" — оценивай по смыслу.
- Ключевые темы используются только как дополнительный ориентир.

ЗАПРЕЩЁННЫЕ ТИПЫ ЗАПРОСОВ:
{chr(10).join(BLACKLIST)}

ПРИМЕРЫ ИЗ ПАМЯТИ ПОЛЬЗОВАТЕЛЯ:
Эти примеры важнее базовых правил.
Если похожее сообщение ранее было оценено пользователем как "bad", похожие сообщения считай не лидами.
Если похожее сообщение ранее было оценено пользователем как "good", похожие сообщения считай лидами.

{json.dumps(memory_examples, ensure_ascii=False, indent=2)}

БАЗОВЫЕ ПРАВИЛА:
1. Лидом считается только сообщение, где есть явный деловой запрос, проблема, потребность или намерение купить/получить услугу компании.
2. Личная переписка, бытовые сообщения, приветствия, благодарности, шутки, обсуждения без запроса услуги — всегда не лид.
3. Если человек хочет легально получить, оформить, выпустить или заказать коды маркировки через Честный Знак — это лид.
4. Если человек хочет регистрацию в Честном Знаке, регистрацию в GS1, помощь с DataMatrix, настройку кабинета или обучение — это лид.
5. Если человек хочет купить готовые, чужие, серые коды или обойти легальную маркировку — это не лид.
6. Слова "куплю коды" сами по себе НЕ означают плохой лид.
7. Плохим лидом это становится только при явных признаках: "готовые коды", "чужие коды", "серые коды", "садовод", "рынок", "карго", обход Честного Знака.
8. Если сообщение совпадает по смыслу с запрещёнными типами запросов — lead = 0 и score = 0.
9. Если нет явного запроса услуги или проблемы клиента — lead = 0 и score = 0.
10. Не ставь score 80 по умолчанию. Оцени строго по смыслу.

БАЗОВЫЕ ПРИМЕРЫ:
[
  {{
    "message": "Нужна регистрация в ЧЗ",
    "expected_json": {{
      "lead": 1,
      "score": 95
    }}
  }},
  {{
    "message": "Как передать УПД с маркировкой",
    "expected_json": {{
      "lead": 1,
      "score": 95
    }}
  }},
  {{
    "message": "Куплю коды для обуви",
    "expected_json": {{
      "lead": 1,
      "score": 90
    }}
  }},
  {{
    "message": "Нужны коды маркировки для обуви",
    "expected_json": {{
      "lead": 1,
      "score": 90
    }}
  }},
  {{
    "message": "Куплю готовые коды",
    "expected_json": {{
      "lead": 0,
      "score": 0
    }}
  }},
  {{
    "message": "Куплю серые коды честный знак",
    "expected_json": {{
      "lead": 0,
      "score": 0
    }}
  }},
  {{
    "message": "Куплю коды маркировки для вещей с садовода",
    "expected_json": {{
      "lead": 0,
      "score": 0
    }}
  }}
]

СООБЩЕНИЕ ДЛЯ ПРОВЕРКИ:
{text}

ВЕРНИ СТРОГО ОДИН JSON-ОБЪЕКТ.

ЕДИНСТВЕННО ДОПУСТИМЫЙ ФОРМАТ ОТВЕТА:
{{
  "lead": 0,
  "score": 0
}}

ИЛИ:

{{
  "lead": 1,
  "score": 90
}}

ЗАПРЕЩЕНО возвращать поля:
- "message"
- "user_rating"
- "expected_json"
- "text"
- "explanation"
- "reason"

Финальный ответ должен содержать только два поля:
- "lead"
- "score"

НЕ копируй примеры из памяти.
НЕ возвращай объект из блока "ПРИМЕРЫ ИЗ ПАМЯТИ ПОЛЬЗОВАТЕЛЯ".
НЕ добавляй текст.
НЕ добавляй markdown.
НЕ добавляй пояснения.
НЕ добавляй несколько JSON-объектов.
"""

    try:
        response = ollama.chat(
            model="llama3.2",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ты API-классификатор. "
                        "Всегда возвращай только JSON с двумя полями: "
                        "{\"lead\": 0 или 1, \"score\": число от 0 до 100}. "
                        "Не возвращай message, user_rating, expected_json, explanation или markdown."
                    )
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            format="json"
        )

        content = response["message"]["content"].strip()

        print("RAW:", content)

        data = extract_json(content)

        if not data:
            print("⚠️ Модель вернула не JSON:", content)
            return None

        normalized_result = normalize_model_result(data)

        if not normalized_result:
            return None

        result = {
            "lead": normalized_result["lead"],
            "score": normalized_result["score"],
            "text": text
        }

        return result

    except Exception as e:
        print("❌ Ollama error:", e)

        return None


def normalize_model_result(data):
    if not isinstance(data, dict):
        return None

    if "lead" in data and "score" in data:
        source = data
    elif isinstance(data.get("expected_json"), dict):
        source = data["expected_json"]
    else:
        print("⚠️ JSON без lead/score:", data)
        return None

    try:
        lead = int(source.get("lead", 0))
        score = int(source.get("score", 0))
    except (TypeError, ValueError):
        print("⚠️ Некорректные lead/score:", source)
        return None

    lead = 1 if lead == 1 else 0
    score = max(0, min(score, 100))

    return {
        "lead": lead,
        "score": score
    }


def extract_json(text):
    decoder = json.JSONDecoder()

    text = text.strip()

    # ищем первую открывающую скобку
    start = text.find("{")

    if start == -1:
        return None

    try:
        data, end = decoder.raw_decode(text[start:])
        return data

    except Exception as e:
        print("❌ JSON extract error:", e)
        return None