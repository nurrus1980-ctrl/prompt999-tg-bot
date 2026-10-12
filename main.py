import os
import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from openai import AsyncOpenAI

BOT_TOKEN = os.getenv("BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o-mini")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN))
dp = Dispatcher()
client = AsyncOpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)

SYSTEM_PROMPT = """
Ты — профессиональный инженер промптов (Prompt Engineer). Твоя цель — превращать сырые запросы пользователя в идеальные, точные промпты для LLM.

ПРАВИЛА:
1. Если задача сформулирована слишком коротко или неясна цель, задай 2-3 коротких вопроса для уточнения контекста.
2. Если деталей достаточно, собери готовый промпт по схеме:
   - Роль и цель (Role & Goal)
   - Контекст и ограничения (Context & Constraints)
   - Точный формат выдачи (Output Format)
   - Переменные поля выдели в виде [Вставь_данные_сюда].

ОТВЕТ:
- Краткий комментарий (1 предложение).
- Готовый промпт ОБЯЗАТЕЛЬНО помести внутрь блока кода markdown для удобного копирования в 1 клик.
- Один совет по доработке.
"""

user_sessions: dict[int, list[dict]] = {}

def get_history(user_id: int) -> list[dict]:
    if user_id not in user_sessions:
        user_sessions[user_id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    return user_sessions[user_id]

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_sessions[message.from_user.id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    await message.answer(
        "👋 *Привет! Я генератор идеальных промптов.*\n\n"
        "Напиши свою идею или черновик (например: _«нужен промпт для резюме»_ или _«промпт для анализа отзывов»_).\n"
        "Я помогу докрутить детали и выдам готовый шаблон."
    )

@dp.message(Command("clear"))
async def clear_handler(message: types.Message):
    user_sessions[message.from_user.id] = [{"role": "system", "content": SYSTEM_PROMPT}]
    await message.answer("🔄 Память очищена! Опиши следующую задачу.")

@dp.message()
async def chat_handler(message: types.Message):
    user_id = message.from_user.id
    history = get_history(user_id)
    history.append({"role": "user", "content": message.text})

    if len(history) > 9:
        history = [history[0]] + history[-8:]
        user_sessions[user_id] = history

    await bot.send_chat_action(chat_id=message.chat.id, action="typing")

    try:
        response = await client.chat.completions.create(
            model=MODEL_NAME,
            messages=history,
            temperature=0.7,
        )
        answer = response.choices[0].message.content
        history.append({"role": "assistant", "content": answer})
        await message.answer(answer)
    except Exception as e:
        await message.answer(f"⚠️ Ошибка вызова нейросети: `{e}`")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
