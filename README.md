# Telegram Бот для сбора заявок

Бот собирает заявки от пользователей (имя, телефон, описание) и отправляет их в указанную Telegram-группу.

## Возможности

- Пошаговый сбор данных: имя → телефон → описание
- Валидация всех полей
- Кнопка «Поделиться контактом» для быстрой отправки номера
- Отправка заявок в Telegram-группу
- Команда `/chatid` для получения ID чата

## Переменные окружения

| Переменная | Описание |
|---|---|
| `BOT_TOKEN` | Токен бота от @BotFather |
| `GROUP_CHAT_ID` | ID группы для получения заявок |

## Запуск

```bash
export BOT_TOKEN="your_token"
export GROUP_CHAT_ID="-100xxxxxxxxxx"
pip install -r requirements.txt
python main.py
```

## Docker

```bash
docker build -t zayavki-bot .
docker run -e BOT_TOKEN="your_token" -e GROUP_CHAT_ID="-100xxxxxxxxxx" zayavki-bot
```

## Команды бота

- `/start` — начать заполнение заявки
- `/cancel` — отменить текущую заявку
- `/chatid` — показать ID текущего чата
