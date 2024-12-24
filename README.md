# homework_bot

Python Telegram Bot для проверки статусов домашних заданий.

## Описание

Этот бот автоматически проверяет статус домашних заданий на платформе (https://practicum.yandex.ru/) и уведомляет пользователя через Telegram при обновлении статуса.

## Используемые технологии

- Python 3.9
- [python-telegram-bot]
- [requests]
- [python-dotenv]
- logging (встроенная библиотека Python)

## Установка

1. Клонируйте репозиторий:
   bash
   git clone https://github.com/maashuup/homework_bot.git
   cd homework_bot

2. Установите зависимости:
   bash
   pip install -r requirements.txt

3. Создайте файл `.env` в корне проекта и добавьте ваши токены:
   PRACTICUM_TOKEN=ваш_токен_Практикума
   TELEGRAM_TOKEN=ваш_токен_Telegram
   TELEGRAM_CHAT_ID=ваш_chat_id

## Запуск

Запустите бота:
bash
python homework.py
