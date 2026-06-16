# ============================================
# ЮРИДИЧЕСКИЙ ИИ-АССИСТЕНТ
# ============================================

import telebot
import requests
import json
import uuid
import PyPDF2
import docx
import os
import re
from datetime import datetime
from collections import Counter
import warnings
warnings.filterwarnings('ignore')
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ТОКЕНЫ (лучше через переменные окружения)
import os
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN', "8448215847:AAEc7o4MSdbMGYXWkb39KNAfKqkaBrGqdZs")
GIGACHAT_AUTH_KEY = os.getenv('GIGACHAT_AUTH_KEY', "MDE5YzllNWYtNTFhMC03OWFkLTkyYjItYjk4NDA2OTFkZjkxOmZiMWI0NTRjLTMwMDItNDI4NC05Yzk4LTU3NmYzYWRiMWQ1YQ==")

print("✅ Токены загружены")

# ИНИЦИАЛИЗАЦИЯ БОТА
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# СИСТЕМНЫЙ ПРОМПТ ДЛЯ GIGACHAT
SYSTEM_PROMPT = """
Ты - профессиональный юрист-аналитик по B2B договорам.
Проанализируй договор и верни СТРОГО JSON (без markdown, без лишнего текста):

{
    "стороны": ["Сторона 1", "Сторона 2"],
    "предмет_договора": "краткое описание",
    "сумма_и_валюта": "сумма",
    "сроки_исполнения": "ключевые даты",
    "порядок_оплаты": "условия",
    "штрафные_санкции": [
        {
            "вид_нарушения": "тип",
            "размер_штрафа": "размер",
            "степень_опасности": "критическая/высокая/средняя/низкая"
        }
    ],
    "рисковые_формулировки": [
        {
            "пункт_договора": "цитата",
            "описание_риска": "в чем опасность",
            "категория_риска": "финансовый/временной/юридический/репутационный",
            "уровень_критичности": "критический/высокий/средний/низкий",
            "рекомендация": "что изменить"
        }
    ],
    "ограничения_ответственности": ["пункт1"],
    "условия_расторжения": "описание",
    "подсудность": "где споры",
    "общий_уровень_риска": "критический/высокий/средний/низкий",
    "ключевые_рекомендации": ["рек1", "рек2"],
    "чек_лист_проверки": ["проверить1", "проверить2"]
}

Особое внимание обращай на формулировки:
- "но не более..."
- "за исключением..."
- "в одностороннем порядке"
- "без согласования"
- "неустойка в размере"
- "расторжение по инициативе"
- ограничения ответственности
- скрытые комиссии и платежи
- автоматическая пролонгация
"""

# ФУНКЦИИ GIGACHAT
def get_gigachat_token():
    """Получение токена доступа GigaChat"""
    url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    headers = {
        'Content-Type': 'application/x-www-form-urlencoded',
        'Accept': 'application/json',
        'RqUID': str(uuid.uuid4()),
        'Authorization': f'Basic {GIGACHAT_AUTH_KEY}'
    }
    
    try:
        response = requests.post(url, headers=headers, data='scope=GIGACHAT_API_PERS', verify=False, timeout=30)
        if response.status_code == 200:
            token = response.json().get('access_token')
            print("✅ Токен GigaChat получен")
            return token
        else:
            print(f"❌ Ошибка токена GigaChat: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Ошибка подключения к GigaChat: {e}")
        return None

def analyze_contract(text):
    """Анализ договора через GigaChat API"""
    token = get_gigachat_token()
    if not token:
        return None
    
    payload = {
        "model": "GigaChat",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Договор для анализа:\n\n{text[:40000]}"}
        ],
        "temperature": 0.2,
        "max_tokens": 4000
    }
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {token}'
    }
    
    try:
        print("🤖 Отправляю запрос в GigaChat...")
        response = requests.post(
            "https://gigachat.devices.sberbank.ru/api/v1/chat/completions",
            headers=headers,
            json=payload,
            verify=False,
            timeout=60
        )
        
        if response.status_code == 200:
            content = response.json()['choices'][0]['message']['content']
            print("✅ Ответ от GigaChat получен")
            
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group())
                except Exception as e:
                    print(f"❌ Ошибка парсинга JSON: {e}")
                    return None
        else:
            print(f"❌ Ошибка API GigaChat: {response.status_code}")
            return None
    except Exception as e:
        print(f"❌ Ошибка анализа: {e}")
        return None

# ИЗВЛЕЧЕНИЕ ТЕКСТА ИЗ ФАЙЛОВ
def extract_text_from_pdf(file_path):
    """Извлечение текста из PDF"""
    try:
        with open(file_path, 'rb') as f:
            reader = PyPDF2.PdfReader(f)
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
            print(f"📄 Извлечено из PDF: {len(text)} символов")
            return text
    except Exception as e:
        print(f"❌ Ошибка PDF: {e}")
        return ""

def extract_text_from_docx(file_path):
    """Извлечение текста из DOCX"""
    try:
        doc = docx.Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs])
        print(f"📄 Извлечено из DOCX: {len(text)} символов")
        return text
    except Exception as e:
        print(f"❌ Ошибка DOCX: {e}")
        return ""

# ФОРМАТИРОВАНИЕ РЕЗУЛЬТАТОВ
def format_result(analysis):
    """Форматирование результатов анализа"""
    if not analysis:
        return "❌ Не удалось проанализировать договор"
    
    risk_emoji = {"критический": "🔴", "высокий": "🟠", "средний": "🟡", "низкий": "🟢"}
    overall = analysis.get('общий_уровень_риска', 'средний')
    emoji = risk_emoji.get(overall, '⚪')
    
    lines = [
        f"{emoji} **АНАЛИЗ ДОГОВОРА**",
        f"**Общий уровень риска: {overall.upper()}**",
        "═" * 30,
        "",
        "📋 **ОСНОВНАЯ ИНФОРМАЦИЯ:**",
        f"• Стороны: {', '.join(analysis.get('стороны', ['Не указаны']))}",
        f"• Предмет: {analysis.get('предмет_договора', 'Не указан')}",
        f"• Сумма: {analysis.get('сумма_и_валюта', 'Не указана')}",
        f"• Сроки: {analysis.get('сроки_исполнения', 'Не указаны')}",
        f"• Оплата: {analysis.get('порядок_оплаты', 'Не указан')}",
    ]
    
    if analysis.get('подсудность'):
        lines.append(f"• Подсудность: {analysis['подсудность']}")
    
    penalties = analysis.get('штрафные_санкции', [])
    if penalties:
        lines.append("")
        lines.append("⚡ **ШТРАФНЫЕ САНКЦИИ:**")
        for p in penalties:
            d = p.get('степень_опасности', 'средняя')
            de = {"критическая": "🔴", "высокая": "🟠", "средняя": "🟡", "низкая": "🟢"}
            lines.append(f"{de.get(d, '⚪')} {p.get('вид_нарушения', '')}: {p.get('размер_штрафа', '')}")
    
    risks = analysis.get('рисковые_формулировки', [])
    if risks:
        lines.append("")
        lines.append(f"⚠️ **НАЙДЕНО РИСКОВ: {len(risks)}**")
        
        for level in ['критический', 'высокий', 'средний', 'низкий']:
            filtered = [r for r in risks if r.get('уровень_критичности') == level]
            if filtered:
                le = {
                    "критический": "🔴 КРИТИЧЕСКИЕ РИСКИ",
                    "высокий": "🟠 ВЫСОКИЕ РИСКИ",
                    "средний": "🟡 СРЕДНИЕ РИСКИ",
                    "низкий": "🟢 НИЗКИЕ РИСКИ"
                }
                lines.append("")
                lines.append(f"**{le.get(level, level.upper())}:**")
                for i, r in enumerate(filtered, 1):
                    lines.append(f"{i}. {r.get('пункт_договора', '')[:150]}")
                    lines.append(f"   ⚠️ {r.get('описание_риска', '')}")
                    if r.get('рекомендация'):
                        lines.append(f"   💡 {r['рекомендация']}")
    
    if analysis.get('условия_расторжения'):
        lines.append("")
        lines.append("🚪 **УСЛОВИЯ РАСТОРЖЕНИЯ:**")
        lines.append(f"{analysis['условия_расторжения']}")
    
    limitations = analysis.get('ограничения_ответственности', [])
    if limitations:
        lines.append("")
        lines.append("🛡️ **ОГРАНИЧЕНИЯ ОТВЕТСТВЕННОСТИ:**")
        for limit in limitations:
            lines.append(f"• {limit}")
    
    recs = analysis.get('ключевые_рекомендации', [])
    if recs:
        lines.append("")
        lines.append("💡 **КЛЮЧЕВЫЕ РЕКОМЕНДАЦИИ:**")
        for i, r in enumerate(recs, 1):
            lines.append(f"{i}. {r}")
    
    checklist = analysis.get('чек_лист_проверки', [])
    if checklist:
        lines.append("")
        lines.append("✅ **ЧЕК-ЛИСТ ПРОВЕРКИ:**")
        for item in checklist:
            lines.append(f"☐ {item}")
    
    if risks:
        cats = Counter(r.get('категория_риска', 'прочее') for r in risks)
        scores = {"критический": 3, "высокий": 2, "средний": 1, "низкий": 0}
        total = sum(scores.get(r.get('уровень_критичности', 'средний'), 1) for r in risks)
        danger_index = (total / (len(risks) * 3) * 100) if risks else 0
        
        lines.append("")
        lines.append("📊 **СТАТИСТИКА РИСКОВ:**")
        for cat, count in cats.most_common():
            lines.append(f"• {cat.title()}: {count}")
        lines.append(f"📈 **Индекс опасности: {danger_index:.0f}%**")
        
        if danger_index > 70:
            lines.append("🔴 Критический уровень - требуется пересмотр договора")
        elif danger_index > 40:
            lines.append("🟡 Средний уровень - рекомендуется доработка")
        else:
            lines.append("🟢 Приемлемый уровень")
    
    return "\n".join(lines)

# ОБРАБОТКА ДОКУМЕНТА
def process_document_file(message):
    """Обработка полученного документа"""
    user_id = message.from_user.id
    file_name = message.document.file_name
    
    print(f"📥 Получен файл: {file_name} от пользователя {user_id}")
    
    if not (file_name.lower().endswith('.pdf') or file_name.lower().endswith('.docx')):
        bot.reply_to(message, "❌ Поддерживаются только PDF и DOCX файлы.")
        return
    
    status_msg = bot.reply_to(message, "⏳ Загружаю договор...")
    
    try:
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Используем /tmp для сервера
        file_path = f"/tmp/{user_id}_{file_name}"
        with open(file_path, 'wb') as f:
            f.write(downloaded_file)
        
        bot.edit_message_text("📖 Извлекаю текст...", message.chat.id, status_msg.message_id)
        
        if file_name.endswith('.pdf'):
            text = extract_text_from_pdf(file_path)
        else:
            text = extract_text_from_docx(file_path)
        
        os.remove(file_path)
        
        if not text or len(text) < 50:
            bot.edit_message_text("❌ Не удалось извлечь текст.", message.chat.id, status_msg.message_id)
            return
        
        bot.edit_message_text(f"🤖 Анализирую...\n📄 {len(text)} символов\n⏳ ~30 секунд", message.chat.id, status_msg.message_id)
        
        analysis = analyze_contract(text)
        
        if not analysis:
            bot.edit_message_text("❌ Ошибка анализа.", message.chat.id, status_msg.message_id)
            return
        
        result_text = format_result(analysis)
        
        if len(result_text) > 4000:
            parts = [result_text[i:i+4000] for i in range(0, len(result_text), 4000)]
            bot.edit_message_text(parts[0], message.chat.id, status_msg.message_id, parse_mode='Markdown')
            for part in parts[1:]:
                bot.send_message(message.chat.id, part, parse_mode='Markdown')
        else:
            bot.edit_message_text(result_text, message.chat.id, status_msg.message_id, parse_mode='Markdown')
        
        print(f"✅ Анализ завершен")
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        try:
            bot.edit_message_text(f"❌ Ошибка: {str(e)[:200]}", message.chat.id, status_msg.message_id)
        except:
            bot.reply_to(message, "❌ Произошла ошибка")

# КОМАНДЫ
@bot.message_handler(commands=['start'])
def start_command(message):
    welcome = """
🏛️ **ЮРИДИЧЕСКИЙ AI-АССИСТЕНТ**

Я анализирую договоры с помощью GigaChat.

**📊 Что я проверяю:**
✅ Стороны, суммы, сроки
✅ Штрафные санкции
⚠️ Рисковые формулировки
⚖️ Условия расторжения
🛡️ Ограничения ответственности
📈 Индекс опасности

**📎 Форматы:** PDF, DOCX

⚠️ Я помогаю найти риски, но решение за юристом.

**Отправьте мне файл договора!**
    """
    bot.reply_to(message, welcome, parse_mode='Markdown')

@bot.message_handler(commands=['help'])
def help_command(message):
    bot.reply_to(message, "📚 Отправьте PDF или DOCX файл для анализа.\n/start - информация", parse_mode='Markdown')

@bot.message_handler(content_types=['document'])
def handle_document(message):
    print(f"📥 Получен документ: {message.document.file_name}")
    process_document_file(message)

@bot.message_handler(func=lambda message: True)
def handle_text(message):
    bot.reply_to(message, "📄 Отправьте PDF или DOCX файл договора для анализа.\n/start - информация", parse_mode='Markdown')

# ЗАПУСК
if __name__ == "__main__":
    print("=" * 50)
    print("✅ БОТ ЗАПУЩЕН!")
    print("=" * 50)
    bot.infinity_polling(timeout=60, long_polling_timeout=60)
