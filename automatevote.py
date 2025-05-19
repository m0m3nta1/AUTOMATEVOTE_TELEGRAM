from telethon import TelegramClient, events
from telethon.errors import SessionPasswordNeededError, PasswordHashInvalidError, AuthRestartError, FloodWaitError, UserNotParticipantError
from telethon.types import TextWithEntities
import asyncio
from aiocron import crontab
import logging
import os


# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Запрашиваем данные у пользователя
api_id = input("Введите ваш API ID: ").strip()
api_hash = input("Введите ваш API Hash: ").strip()
phone = input("Введите ваш номер телефона (в формате +1234567890): ").strip()

# Пароль для 2FA (можно оставить через переменную окружения или запросить)
password = os.getenv('TELEGRAM_2FA_PASSWORD')
if not password:
    password = input("Введите ваш 2FA пароль (если нет, оставьте пустым и нажмите Enter): ").strip() or None

# ID чата (оставляем из логов, можно также запросить у пользователя, если нужно)
chat_id = -12345678 #chat_id можно найти в логах после авторизации или в Experemental settings телеграм выбрать пункт показывать id
# Создаем клиент
client = TelegramClient('session', int(api_id), api_hash)

async def ensure_connection():
    """Проверяет и устанавливает соединение с Telegram."""
    try:
        if not client.is_connected():
            logging.info("Клиент не подключен, устанавливаем соединение...")
            await client.connect()
            logging.info("Соединение установлено")
        else:
            logging.info("Клиент уже подключен")
    except (OSError, asyncio.TimeoutError) as e:
        logging.error(f"Ошибка соединения: {e}")
        raise

async def check_polls():
    """Проверяет последние сообщения на наличие опросов и голосует за '+'."""
    try:
        await ensure_connection()
        logging.info(f"Проверяем последние 50 сообщений в чате {chat_id}...")
        async for message in client.iter_messages(chat_id, limit=50):
            logging.info(f"Обработка сообщения ID {message.id}, дата: {message.date}")
            if hasattr(message, 'poll') and message.poll:
                poll = message.poll
                # Check if poll has an inner poll object
                if hasattr(poll, 'poll'):
                    inner_poll = poll.poll
                    question = getattr(inner_poll, 'question', 'Вопрос не указан')
                    logging.info(f"Найден опрос в сообщении ID {message.id}: {question}")
                    # Access answers from inner_poll
                    for index, option in enumerate(inner_poll.answers):
                        if isinstance(option.text, TextWithEntities):
                            option_text = option.text.text.strip()
                            logging.info(f"Вариант {index}: '{option_text}' (TextWithEntities)")
                        else:
                            option_text = option.text.strip()
                            logging.info(f"Вариант {index}: '{option_text}' (строка)")
                        if option_text in ['+', '＋', '+ ']:
                            try:
                                await message.click(index)
                                logging.info(f"Проголосовал за '{option_text}' в опросе ID {message.id}")
                                return
                            except FloodWaitError as e:
                                logging.error(f"Ограничение Telegram: нужно подождать {e.seconds} секунд")
                                return
                            except ValueError as e:
                                logging.error(f"Ошибка: опрос уже закрыт или недоступен для голосования в сообщении ID {message.id}: {e}")
                                return
                            except Exception as e:
                                logging.error(f"Ошибка при голосовании в опросе ID {message.id}: {e}")
                                return
                    logging.info(f"Вариант '+' не найден в опросе ID {message.id}")
                else:
                    logging.error(f"Poll object lacks inner 'poll' attribute in message ID {message.id}")
            else:
                logging.info(f"Сообщение ID {message.id} не содержит опрос")
        logging.info("[bold red]Опросы с вариантом '+' не найдены в последних 50 сообщений[/bold red]")
    except UserNotParticipantError:
        logging.error(f"Аккаунт не является участником чата {chat_id}")
    except Exception as e:
        logging.error(f"Ошибка при проверке опросов: {e}")

@client.on(events.NewMessage(chats=chat_id))
async def handler(event):
    """Обработчик новых сообщений с опросами."""
    try:
        await ensure_connection()
        message = event.message
        logging.info(f"Получено новое сообщение ID {message.id} в чате {chat_id}, дата: {message.date}")
        if hasattr(message, 'poll') and message.poll:
            poll = message.poll
            # Check if poll has an inner poll object
            if hasattr(poll, 'poll'):
                inner_poll = poll.poll
                question = getattr(inner_poll, 'question', 'Вопрос не указан')
                logging.info(f"[bold red]Найден опрос в новом сообщении ID {message.id}: {question}[/bold red]")
                # Access answers from inner_poll
                for index, option in enumerate(inner_poll.answers):
                    if isinstance(option.text, TextWithEntities):
                        option_text = option.text.text.strip()
                        logging.info(f"Вариант {index}: '{option_text}' (TextWithEntities)")
                    else:
                        option_text = option.text.strip()
                        logging.info(f"Вариант {index}: '{option_text}' (строка)")
                    if option_text in ['+', '＋', '+ ']:
                        try:
                            await message.click(index)
                            logging.info(f"[bold red]Проголосовал за '{option_text}' в опросе ID {message.id}[/bold red]")
                            return
                        except FloodWaitError as e:
                            logging.error(f"Ограничение Telegram: нужно подождать {e.seconds} секунд")
                            return
                        except ValueError as e:
                            logging.error(f"Ошибка: опрос уже закрыт или недоступен для голосования в сообщении ID {message.id}: {e}")
                            return
                        except Exception as e:
                            logging.error(f"Ошибка при голосовании в опросе ID {message.id}: {e}")
                            return
                logging.info(f"Вариант '+' не найден в опросе ID {message.id}")
            else:
                logging.error(f"Poll object lacks inner 'poll' attribute in message ID {message.id}")
        else:
            logging.info(f"Новое сообщение ID {message.id} не содержит опрос")
    except Exception as e:
        logging.error(f"Ошибка в обработчике сообщений: {e}")

@crontab('0 7 * * *')
async def morning_task():
    """Планировщик для выполнения проверки опросов каждое утро в 07:00."""
    logging.info("Запуск утренней проверки опросов...")
    await check_polls()

async def main():
    try:
        await ensure_connection()
        if not await client.is_user_authorized():
            logging.info("Пользователь не авторизован, запрашиваем код...")
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    await client.send_code_request(phone)
                    code = input("Введите код, полученный от Telegram: ")
                    try:
                        await client.sign_in(phone, code)
                        logging.info("Успешно вошли без пароля")
                        break
                    except SessionPasswordNeededError:
                        max_password_attempts = 3
                        auth_password = password
                        for password_attempt in range(max_password_attempts):
                            if not auth_password:
                                auth_password = input("Введите ваш 2FA пароль: ")
                                logging.info(f"Введен пароль (попытка {password_attempt + 1}/{max_password_attempts})")
                            try:
                                await client.sign_in(password=auth_password)
                                logging.info("Успешно вошли с паролем")
                                break
                            except PasswordHashInvalidError:
                                logging.error(f"Неверный пароль (попытка {password_attempt + 1}/{max_password_attempts}). Пожалуйста, попробуйте снова.")
                                auth_password = None
                                if password_attempt == max_password_attempts - 1:
                                    logging.error("Достигнуто максимальное количество попыток ввода пароля")
                                    return
                        else:
                            break
                    except AuthRestartError as e:
                        logging.warning(f"Ошибка авторизации Telegram, попытка {attempt + 1}/{max_retries}: {e}")
                        if attempt < max_retries - 1:
                            logging.info("Повторяем попытку через 10 секунд...")
                            await asyncio.sleep(10)
                        else:
                            logging.error("Достигнуто максимальное количество попыток авторизации")
                            return
                except Exception as e:
                    if "all available options for this type of number were already used" in str(e):
                        logging.error("Исчерпаны все методы отправки кода. Подождите 5–15 минут и попробуйте снова.")
                        return
                    logging.error(f"Ошибка при авторизации: {e}")
                    return

        logging.info("Список всех доступных чатов:")
        async for dialog in client.iter_dialogs():
            entity = dialog.entity
            chat_name = getattr(entity, 'title', getattr(entity, 'first_name', getattr(entity, 'username', 'Неизвестно')))
            chat_id_value = entity.id
            if hasattr(entity, 'title'):
                logging.info(f"Чат: {chat_name}, ID: -{chat_id_value}")
            else:
                logging.info(f"Пользователь/Бот: {chat_name}, ID: {chat_id_value}")

        try:
            entity = await client.get_entity(chat_id)
            if hasattr(entity, 'title'):
                logging.info(f"Чат найден: {entity.title} (ID: {chat_id})")
            elif hasattr(entity, 'username') or hasattr(entity, 'first_name'):
                logging.error(f"Ошибка: ID {chat_id} соответствует пользователю ({entity.first_name or entity.username}), а не группе или каналу")
                logging.info("Пожалуйста, обновите chat_id в коде, используя ID из списка чатов выше.")
                return
            else:
                logging.error(f"Неизвестный тип сущности для ID {chat_id}")
                return
        except Exception as e:
            logging.error(f"Ошибка при получении информации о чате {chat_id}: {e}")
            return

        logging.info("Выполняем немедленную проверку опросов...")
        await check_polls()

        logging.info("Клиент запущен и авторизован")
        await client.run_until_disconnected()

    except Exception as e:
        logging.error(f"Ошибка при запуске клиента: {e}")

if __name__ == '__main__':
    try:
        loop = asyncio.get_event_loop()
        loop.run_until_complete(main())
    except KeyboardInterrupt:
        logging.info("Программа остановлена пользователем")
        client.disconnect()
    except Exception as e:
        logging.error(f"Ошибка в главном цикле: {e}")
        client.disconnect()