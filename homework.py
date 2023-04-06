import requests
import logging
import os
import sys
import time
import telegram
from json import decoder
from http import HTTPStatus
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
from exceptions import (
    NotAllTokenException, UnavaliableEndpointException,
    TelegramErrorException
)

load_dotenv()


PRACTICUM_TOKEN = os.getenv('P_TOKEN')
TELEGRAM_TOKEN = os.getenv('T_TOKEN')
TELEGRAM_CHAT_ID = 242577505

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
                'program.log', maxBytes=50000000, backupCount=5
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
        logger.error(f'Ошибка при запросе к API Яндекс.Практикум: {error}')
        raise ConnectionError(f'API Яндекс.Практикум не доступно: {error}')
    if homework_data.status_code != HTTPStatus.OK:
        logger.error(
            f'API Яндекс.Практикум не доступно. Код ответа API: '
            f'{homework_data.status_code}'
        )
        raise UnavaliableEndpointException('API Яндекс.Практикум не доступно!')
    try:
        response = homework_data.json()
    except decoder.JSONDecodeError:
        logger.error(
            'Сервер вернул невалидный json - '
            'Ответ содержит некорректный тип данных.'
        )
    return response


def check_response(response: dict) -> list:
    """Проверка типа данных, полученных от API."""
    if not isinstance(response, dict):
        logger.error('Неверный тип данных')
        raise TypeError('Неверный тип данных')
    homeworks = response.get('homeworks')
    if 'homeworks' not in response:
        logger.error('Ключа homeworks в словаре response не обнаружено')
        raise KeyError('Ключа homeworks в словаре response не обнаружено')
    if not isinstance(homeworks, list):
        logger.error('Неверный тип данных')
        raise TypeError('Неверный тип данных')
    return homeworks


def parse_status(homework: dict):
    """Отслеживание изменения статуса домашней работы."""
    if 'homework_name' not in homework:
        logger.error(
            'Ключа homework_name в списке домашних работ не обнаружено'
        )
        raise KeyError(
            'Ключа homework_name в списке домашних работ не обнаружено'
        )
    homework_name = homework.get('homework_name')
    homework_status = homework.get('status')
    if homework_status not in HOMEWORK_VERDICTS:
        logger.error(f'Передан неверный ключ {homework_status}')
        raise KeyError('Передан неверный ключ для статуса')
    for status, verdict in HOMEWORK_VERDICTS.items():
        if homework_status == status:
            return (
                f'Изменился статус проверки работы '
                f'"{homework_name}". {verdict}'
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
            raise NotAllTokenException(message)
        # sys.exit()
    timestamp = int(time.time())
    STATUS = ''
    last_message_error = ''
    while True:
        try:
            response = get_api_answer(timestamp)
            homeworks = check_response(response)
            new_status = parse_status(homeworks[0])
            if STATUS != new_status:
                STATUS = new_status
                send_message(bot, new_status)
            else:
                logger.debug('Статус проверки домашней работы не изменился.')
            timestamp = response.get('current_date')
            # if logger.level == logging.ERROR or logging.CRITICAL:
            # send_message(bot, 'logger.message')
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
