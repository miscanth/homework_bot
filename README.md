![Python](https://img.shields.io/badge/python-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)  ![Telegram](https://img.shields.io/badge/Telegram-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)


# Telegram-бот

### Описание проекта

Telegram-бот для проверки статуса выполнения домашней работы на курсе Yandex.Practicum.

***Как работает бот:***

- Раз в 10 минут бот обращается к API сервиса Практикум.Домашка и проверяет статус отправленной на ревью домашней работы: взята ли домашка в ревью, проверена ли она, а если проверена — то принял её ревьюер или вернул на доработку, а также комментарий от ревьюера, если такой имеется;
- При обновлении статуса бот анализирует ответ API и отправляет соответствующее уведомление в Telegram;
- Бот логирует свою работу и сообщает о важных проблемах сообщением в Telegram.


### Технологии

- Python 3.9
- python-telegram-bot 13.7


***Для работы бота необходимы:***

* Токен авторизации от API сервиса Практикум.Домашка - PRACTICUM_TOKEN;
* Токен от Телеграм-бота- TELEGRAM_TOKEN;
* ID чата, куда бот будет отправлять сообщения - TELEGRAM_CHAT_ID.

Токены и ID чата сохраните в переменных окружения (в файл .env в папку с проектом).


### Запуск проекта

Клонировать репозиторий и перейти в него в командной строке: 
```
git clone git@github.com:miscanth/homework_bot.git
```
Cоздать и активировать виртуальное окружение: 
```
python3.9 -m venv venv 
```
* Если у вас Linux/macOS 

    ```
    source venv/bin/activate
    ```
* Если у вас windows 
 
    ```
    source venv/scripts/activate
    ```
```
python3.9 -m pip install --upgrade pip
```
Установить зависимости из файла requirements.txt:
```
pip install -r requirements.txt
```
Запустить проект:
```
python3.9 manage.py homework.py
```

## Разработчик (исполнитель):
👩🏼‍💻 Юлия: https://github.com/miscanth