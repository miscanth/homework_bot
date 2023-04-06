from http import HTTPStatus
from json import decoder
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import time

from dotenv import load_dotenv
import requests
import telegram

from exceptions import (
    UnavaliableEndpointException,
    TelegramErrorException, JSONDecodeErrorException
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('P_TOKEN')
TELEGRAM_TOKEN = os.getenv('T_TOKEN')
TELEGRAM_CHAT_ID = 242577505
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
    return all([PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID])


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
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        raise KeyError('Передан неверный ключ для статуса')
    for status in HOMEWORK_VERDICTS.keys():
        if homework_status == status:
            return (
                f'Изменился статус проверки работы '
                f'"{homework_name}". {HOMEWORK_VERDICTS[status]}'
            )


def main():
    """Основная логика работы бота."""
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    if not check_tokens():
        for name in TOKENS.keys():
            message = (
                f'Отсутствует обязательная переменная окружения: '
                f'{name}. Программа принудительно остановлена.'
            )
            logger.critical(message)
            send_message(bot, message)
            sys.exit('Ошибка: Токены не прошли валидацию')
    timestamp = int(time.time())
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
