import logging
import os
import sys
import time
from http import HTTPStatus

import requests
from dotenv import load_dotenv
from telebot import TeleBot

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s, %(levelname)s, %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def check_tokens():
    """Проверяет доступность всех необходимых токенов."""
    tokens = [PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]
    if not all(tokens):
        logging.critical('Отсутствуют обязательные переменные окружения.')
        return False
    return all(tokens)


def send_message(bot, message):
    """Отправляет сообщение в Telegram."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Бот отправил сообщение: {message}')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения: {error}')


def get_api_answer(timestamp):
    """Делает запрос к API Практикума."""
    params = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            error_message = (
                f'Эндпоинт {ENDPOINT} недоступен.'
                f'Код ответа: {response.status_code}'
            )
            logging.error(error_message)
            raise Exception(error_message)
        return response.json()
    except Exception as error:
        error_message = f'Ошибка при запросе к API: {error}'
        logging.error(error_message)
        raise Exception(f'Ошибка запроса: {error}') from error


def check_response(response):
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        logging.error('Ответ API не является словарем.')
        raise TypeError('Ответ API должен быть словарем.')
    if 'homeworks' not in response or 'current_date' not in response:
        logging.error('В ответе API отсутствуют ожидаемые ключи.')
        raise KeyError('Отсутствуют обязательные ключи в ответе API.')
    if not isinstance(response['homeworks'], list):
        logging.error('Домашние работы не представлены списком.')
        raise TypeError('Значение ключа "homeworks" должно быть списком.')
    return response['homeworks']


def parse_status(homework):
    """Извлекает статус работы из ответа API."""
    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError('Отсутствуют ожидаемые ключи в ответе API.')
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_VERDICTS:
        logging.error(f'Недокументированный статус работы: {homework_status}')
        raise ValueError(f'Неизвестный статус работы: {homework_status}')

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""

    if not check_tokens():
        logging.critical('Отсутствуют обязательные переменные окружения.')
        return

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error = None

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                for homework in homeworks:
                    message = parse_status(homework)
                    send_message(bot, message)
            else:
                logging.debug('Новых статусов нет.')
            timestamp = response.get('current_date')
            last_error = None

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(f'Сбой в работе программы: {error}')
            if last_error != str(error):
                send_message(bot, message)
                last_error = str(error)

        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
