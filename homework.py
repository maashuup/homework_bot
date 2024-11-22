import logging
import os
import sys
import time

from http import HTTPStatus
from dotenv import load_dotenv
import requests
from telebot import TeleBot
from telebot.apihelper import ApiException
from typing import List, Any

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


def check_tokens() -> List[str]:
    """Проверяет доступность всех необходимых токенов."""
    tokens = {
        'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
        'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
        'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID,
    }
    missing_tokens = [name for name, value in tokens.items() if not value]
    return missing_tokens


def send_message(bot: TeleBot, message: str) -> None:
    """Отправляет сообщение в Telegram."""
    try:
        logging.info(f'Отправка сообщения {message}')
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Сообщение успешно отправлено: {message}')
    except ApiException as error:
        raise RuntimeError(f'Ошибка при отправке сообщения: {error}')
    except requests.exceptions.RequestException as error:
        raise RuntimeError(f'Ошибка при запросе: {error}')
    else:
        logging.debug(
            f'Бот успешно отправил сообщение: {message}'
        )


class APIRequestError(Exception):
    """Исключение для ошибок при работе с API."""
    pass


def get_api_answer(timestamp: int) -> dict[str, Any]:
    """Делает запрос к API Практикума."""
    params = {'from_date': timestamp}
    try:
        logging.debug(f'Начало запроса к API: {ENDPOINT}, параметры: {params}')
        response = requests.get(ENDPOINT, headers=HEADERS, params=params)
        if response.status_code != HTTPStatus.OK:
            error_message = (
                f'Эндпоинт {ENDPOINT} недоступен.'
                f'Код ответа: {response.status_code}'
            )
            raise APIRequestError(error_message)
        return response.json()
    except requests.exceptions.RequestException as error:
        raise APIRequestError(f'Ошибка при запросе к API: {error}') from error


def check_response(response) -> list:
    """Проверяет ответ API на соответствие документации."""
    if not isinstance(response, dict):
        raise TypeError('Ответ API должен быть словарем.')
    if 'homeworks' not in response or 'current_date' not in response:
        raise KeyError('Отсутствуют обязательные ключи в ответе API.')
    if not isinstance(response['homeworks'], list):
        raise TypeError('Значение ключа "homeworks" должно быть списком.')
    return response['homeworks']


def parse_status(homework: dict) -> str:
    """Извлекает статус работы из ответа API."""
    if 'homework_name' not in homework or 'status' not in homework:
        raise KeyError('Отсутствуют ожидаемые ключи в ответе API.')
    homework_name = homework['homework_name']
    homework_status = homework['status']

    if homework_status not in HOMEWORK_VERDICTS:
        raise ValueError(f'Неизвестный статус работы: {homework_status}')

    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s',
        handlers=[logging.StreamHandler(sys.stdout)]
    )

    load_dotenv()

    bot = TeleBot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    last_error = None
    last_status = None

    missing_tokens = check_tokens()
    if missing_tokens:
        logging.critical(
            'Отсутствуют обязательные переменные окружения: '
            f'{", ".join(missing_tokens)}'
        )
        sys.exit()

    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if message != last_status:
                    send_message(bot, message)
                    last_status = message
                    timestamp = response.get('current_date', timestamp)
                else:
                    logging.debug(
                        'Статус не изменился, сообщение не отправлено.'
                    )
            else:
                logging.debug('В ответе нет домашних работ.')
                send_message(bot, 'В ответе нет домашних работ.')
            last_error = None
        except APIRequestError as error:
            logging.error(f'Ошибка при работе с API: {error}')
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
