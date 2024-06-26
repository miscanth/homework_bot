import logging
import os
import sys
import time
from http import HTTPStatus
from json import decoder
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

from exceptions import (JSONDecodeErrorException, TelegramErrorException,
                        UnavaliableEndpointException)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('P_TOKEN')
TELEGRAM_TOKEN = os.getenv('T_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MAX_BYTES = 50000000
BACKUP_COUNT = 5


TOKENS = {
    'PRACTICUM_TOKEN': PRACTICUM_TOKEN,
    'TELEGRAM_TOKEN': TELEGRAM_TOKEN,
    'TELEGRAM_CHAT_ID': TELEGRAM_CHAT_ID
}

RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def init_logger():
    """Настройки логгера."""
    logging.basicConfig(
        handlers=[
            RotatingFileHandler(
                'program.log', maxBytes=MAX_BYTES, backupCount=BACKUP_COUNT
            ),
            logging.StreamHandler(sys.stdout)
        ],
        level=logging.DEBUG,
        format='%(asctime)s, %(levelname)s, %(message)s, %(name)s'
    )
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    return logger


logger = init_logger()


def check_tokens() -> bool:
    """Проверяет доступность переменных окружения."""
    for token_name in TOKENS:
        if not all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID]):
            message = (
                f'Отсутствует обязательная переменная окружения: '
                f'{token_name}. Программа принудительно остановлена.'
            )
            logger.critical(message)
            return False
    return True


def send_message(bot, message: str) -> None:
    """Отправляет сообщение в Телеграм чат."""
    logger.info('Начинаем отправку сообщения в Telegram')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug(f'Удачная отправка сообщения в Telegram: {message}')
    except telegram.error.TelegramError as error:
        logger.error(
            f'Сбой при отправке сообщения {message} в Телеграмм: {error}'
        )
        raise TelegramErrorException(error)


def get_api_answer(timestamp: int) -> dict:
    """Получение ответа от API Яндекс.Практикум."""
    payload = {'from_date': timestamp}
    logger.info('Начали запрос к API')
    try:
        homework_data = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.RequestException as error:
        logger.error(f'Ошибка при запросе к API Яндекс.Практикум: {error}')
    except Exception as error:
        raise ConnectionError(f'API Яндекс.Практикум не доступно: {error}')
    if homework_data.status_code != HTTPStatus.OK:
        raise UnavaliableEndpointException(
            'API Яндекс.Практикум не доступно! '
            f'Код ответа API: {homework_data.status_code}'
        )
    try:
        response = homework_data.json()
    except decoder.JSONDecodeError:
        raise JSONDecodeErrorException(
            'Сервер вернул невалидный json - '
            'Ответ содержит некорректный тип данных.'
        )
    return response


def check_response(response: dict) -> list:
    """Проверка типа данных, полученных от API."""
    if not isinstance(response, dict):
        raise TypeError('Неверный тип данных')
    homeworks = response.get('homeworks')
    if 'homeworks' not in response:
        raise KeyError('Ключа homeworks в словаре response не обнаружено')
    if not isinstance(homeworks, list):
        raise TypeError('Неверный тип данных')
    return homeworks


def parse_status(homework: dict):
    """Отслеживание изменения статуса домашней работы."""
    if 'homework_name' not in homework:
        raise KeyError(
            'Ключа homework_name в списке домашних работ не обнаружено'
        )
    homework_name = homework.get('homework_name')
    reviewer_comment = homework.get('reviewer_comment')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        raise KeyError('Передан неверный ключ для статуса')
    return (
        f'Изменился статус проверки работы '
        f'"{homework_name}". {HOMEWORK_VERDICTS[status]}\n'
        f'{reviewer_comment}'
    )


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    if not check_tokens():
        sys.exit('Ошибка: Токены не прошли валидацию')
    timestamp = 0
    last_status = ''
    last_message_error = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            if homeworks:
                message = parse_status(homeworks[0])
                if message != last_status:
                    send_message(bot, message)
                    last_status = message
                else:
                    logger.info(
                        'Статус проверки домашней работы не изменился.'
                    )
            else:
                logger.info('Нет домашних работ')
            timestamp = response.get('current_date')
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if str(error) != last_message_error:
                last_message_error = str(error)
                send_message(bot, message)
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
