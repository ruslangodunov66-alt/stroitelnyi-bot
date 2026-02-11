import telebot
from telebot import types
from config import *
from database import Database
from matching import MatchingAlgorithm
import time

bot = telebot.TeleBot(BOT_TOKEN)
db = Database()
matcher = MatchingAlgorithm()

# Хранилище временных данных пользователей
user_data = {}

# ============= КЛАВИАТУРЫ =============
def get_main_keyboard(user_type=None):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if user_type == 'prorab':
        keyboard.add(types.KeyboardButton('?? Создать заявку (ищу заказ)'))
        keyboard.add(types.KeyboardButton('?? Найти заказы'))
        keyboard.add(types.KeyboardButton('?? Мои заявки'))
        keyboard.add(types.KeyboardButton('?? Профиль'))
    elif user_type == 'owner':
        keyboard.add(types.KeyboardButton('?? Создать заявку (ищу бригаду)'))
        keyboard.add(types.KeyboardButton('?? Найти бригады'))
        keyboard.add(types.KeyboardButton('?? Мои заявки'))
        keyboard.add(types.KeyboardButton('?? Профиль'))
    else:
        keyboard.add(types.KeyboardButton('?? Регистрация'))
        keyboard.add(types.KeyboardButton('?? О боте'))
    
    return keyboard

def get_cancel_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('? Отменить'))
    return keyboard

# ============= ОБРАБОТЧИКИ КОМАНД =============
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # Проверяем, зарегистрирован ли пользователь
    user_requests = db.get_user_requests(user_id)
    if user_requests:
        # Получаем тип пользователя из последней заявки
        last_request = user_requests[0]
        user_type = last_request[2]
        bot.send_message(
            user_id,
            f"?? С возвращением, {message.from_user.first_name}!",
            reply_markup=get_main_keyboard(user_type)
        )
    else:
        bot.send_message(
            user_id,
            "?? Добро пожаловать в строительный бот!\n\n"
            "Здесь вы можете найти профессионального прораба "
            "или заказчика для ремонта и строительства.\n\n"
            "Наш алгоритм подберет наиболее подходящие варианты "
            "на основе ваших критериев.",
            reply_markup=get_main_keyboard()
        )

@bot.message_handler(func=lambda message: message.text == '?? Регистрация')
def register_start(message):
    user_id = message.from_user.id
    user_data[user_id] = {'step': 'choose_type'}
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("?? Прораб", callback_data="type_prorab"),
        types.InlineKeyboardButton("?? Собственник", callback_data="type_owner")
    )
    
    bot.send_message(
        user_id,
        "?? Выберите вашу роль:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('type_'))
def process_user_type(call):
    user_id = call.from_user.id
    user_type = call.data.replace('type_', '')
    
    # Сохраняем пользователя в БД
    db.add_user(
        user_id=user_id,
        username=call.from_user.username,
        full_name=call.from_user.full_name,
        user_type=user_type
    )
    
    bot.answer_callback_query(call.id, "Регистрация завершена!")
    bot.edit_message_text(
        f"? Вы зарегистрированы как: {USER_TYPES[user_type]}",
        user_id,
        call.message.message_id
    )
    
    bot.send_message(
        user_id,
        "Теперь вы можете создавать заявки и искать партнеров!",
        reply_markup=get_main_keyboard(user_type)
    )

# ============= СОЗДАНИЕ ЗАЯВКИ =============
@bot.message_handler(func=lambda message: message.text in [
    '?? Создать заявку (ищу заказ)',
    '?? Создать заявку (ищу бригаду)'
])
def create_request_start(message):
    user_id = message.from_user.id
    user_requests = db.get_user_requests(user_id)
    
    if not user_requests:
        bot.send_message(user_id, "Сначала нужно зарегистрироваться!")
        return
    
    last_request = user_requests[0]
    user_type = last_request[2]
    
    user_data[user_id] = {
        'step': 'city',
        'user_type': user_type
    }
    
    # Создаем клавиатуру с городами
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for city in CITIES:
        keyboard.add(types.InlineKeyboardButton(city, callback_data=f"city_{city}"))
    
    bot.send_message(
        user_id,
        "?? В каком городе находится объект?",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('city_'))
def process_city(call):
    user_id = call.from_user.id
    city = call.data.replace('city_', '')
    
    user_data[user_id]['city'] = city
    user_data[user_id]['step'] = 'object_type'
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for key, value in OBJECT_TYPES.items():
        keyboard.add(types.InlineKeyboardButton(value, callback_data=f"obj_{key}"))
    
    bot.edit_message_text(
        f"? Город: {city}\n\n?? Выберите тип объекта:",
        user_id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('obj_'))
def process_object_type(call):
    user_id = call.from_user.id
    object_type = call.data.replace('obj_', '')
    
    user_data[user_id]['object_type'] = object_type
    user_data[user_id]['step'] = 'work_type'
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for key, value in WORK_TYPES.items():
        keyboard.add(types.InlineKeyboardButton(value, callback_data=f"work_{key}"))
    
    bot.edit_message_text(
        f"? Тип объекта: {OBJECT_TYPES[object_type]}\n\n"
        "?? Выберите вид работ:",
        user_id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('work_'))
def process_work_type(call):
    user_id = call.from_user.id
    work_type = call.data.replace('work_', '')
    
    user_data[user_id]['work_type'] = work_type
    user_data[user_id]['step'] = 'budget'
    
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for key, value in BUDGET_RANGES.items():
        keyboard.add(types.InlineKeyboardButton(value, callback_data=f"budget_{key}"))
    
    bot.edit_message_text(
        f"? Вид работ: {WORK_TYPES[work_type]}\n\n"
        "?? Выберите бюджет:",
        user_id,
        call.message.message_id,
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('budget_'))
def process_budget(call):
    user_id = call.from_user.id
    budget = call.data.replace('budget_', '')
    
    user_data[user_id]['budget'] = budget
    user_data[user_id]['step'] = 'square'
    
    bot.edit_message_text(
        f"? Бюджет: {BUDGET_RANGES[budget]}\n\n"
        "?? Введите площадь помещения (в м?):\n"
        "(или отправьте '0', если не знаете)",
        user_id,
        call.message.message_id
    )
    
    bot.register_next_step_handler_by_chat_id(user_id, process_square)

def process_square(message):
    user_id = message.from_user.id
    
    try:
        square = int(message.text)
        user_data[user_id]['square'] = square
        user_data[user_id]['step'] = 'description'
        
        bot.send_message(
            user_id,
            "?? Добавьте описание вашего проекта.\n"
            "Укажите особенности, сроки, пожелания:\n"
            "(или отправьте '-', чтобы пропустить)",
            reply_markup=get_cancel_keyboard()
        )
        
        bot.register_next_step_handler(message, process_description)
    except ValueError:
        bot.send_message(
            user_id,
            "? Пожалуйста, введите число.\n"
            "?? Площадь помещения (в м?):"
        )
        bot.register_next_step_handler(message, process_square)

def process_description(message):
    user_id = message.from_user.id
    
    if message.text == '? Отменить':
        cancel_creation(message)
        return
    
    description = message.text if message.text != '-' else ""
    
    # Сохраняем заявку в БД
    request_id = db.add_request(
        user_id=user_id,
        user_type=user_data[user_id]['user_type'],
        city=user_data[user_id]['city'],
        object_type=user_data[user_id]['object_type'],
        work_type=user_data[user_id]['work_type'],
        budget_range=user_data[user_id]['budget'],
        square_meters=user_data[user_id]['square'],
        description=description
    )
    
    bot.send_message(
        user_id,
        "? Заявка успешно создана!\n"
        "?? Начинаем поиск подходящих вариантов...",
        reply_markup=get_main_keyboard(user_data[user_id]['user_type'])
    )
    
    # Запускаем поиск совпадений
    find_matches(user_id, request_id)
    
    del user_data[user_id]

def cancel_creation(message):
    user_id = message.from_user.id
    user_requests = db.get_user_requests(user_id)
    user_type = user_requests[0][2] if user_requests else None
    
    bot.send_message(
        user_id,
        "? Создание заявки отменено",
        reply_markup=get_main_keyboard(user_type)
    )
    
    if user_id in user_data:
        del user_data[user_id]

# ============= АЛГОРИТМ ПОДБОРА =============
def find_matches(user_id, request_id):
    """Находит подходящие заявки для только что созданной"""
    
    # Получаем целевую заявку
    db.cursor.execute('SELECT * FROM requests WHERE request_id = ?', (request_id,))
    target_request = db.cursor.fetchone()
    
    # Определяем, кого ищем
    looking_for = 'owner' if target_request[2] == 'prorab' else 'prorab'
    
    # Получаем все активные заявки противоположного типа
    potential_requests = db.get_active_requests(user_type=looking_for)
    
    # Ищем совпадения
    matches = matcher.find_best_matches(target_request, potential_requests, limit=5)
    
    # Сохраняем найденные совпадения
    for request, score in matches:
        db.save_match(request_id, request[0], score)
    
    # Отправляем результат пользователю
    if matches:
        send_matches_to_user(user_id, request_id, matches)
    else:
        bot.send_message(
            user_id,
            "?? Пока не найдено подходящих вариантов.\n"
            "Мы продолжим поиск и уведомим вас, когда появятся новые заявки!"
        )

def send_matches_to_user(user_id, request_id, matches):
    """Отправляет найденные совпадения пользователю"""
    
    text = f"?? Найдено {len(matches)} подходящих вариантов!\n\n"
    
    for i, (request, score) in enumerate(matches, 1):
        text += f"?? Вариант #{i}\n"
        text += f"?? Совпадение: {score}%\n"
        
        if request[2] == 'owner':
            text += f"?? Собственник ищет: {OBJECT_TYPES.get(request[4], 'Не указано')}\n"
        else:
            text += f"?? Прораб: {WORK_TYPES.get(request[5], 'Не указано')}\n"
        
        text += f"?? Город: {request[3]}\n"
        text += f"?? Бюджет: {BUDGET_RANGES.get(request[6], 'Не указано')}\n"
        
        if request[7]:  # площадь
            text += f"?? Площадь: {request[7]} м?\n"
        
        text += "\n"
    
    text += "Для просмотра деталей используйте раздел 'Мои заявки'"
    
    bot.send_message(user_id, text)

# ============= ПОИСК ЗАЯВОК =============
@bot.message_handler(func=lambda message: message.text in ['?? Найти заказы', '?? Найти бригады'])
def search_requests(message):
    user_id = message.from_user.id
    
    user_requests = db.get_user_requests(user_id)
    if not user_requests:
        bot.send_message(user_id, "Сначала создайте заявку!")
        return
    
    # Получаем последнюю активную заявку пользователя
    active_requests = [r for r in user_requests if r[9] == 'active']
    
    if not active_requests:
        bot.send_message(
            user_id,
            "У вас нет активных заявок. Создайте новую заявку для поиска!"
        )
        return
    
    last_request = active_requests[0]
    
    # Получаем сохраненные совпадения
    matches = db.get_matches_for_request(last_request[0])
    
    if matches:
        send_matches_from_db(user_id, matches)
    else:
        bot.send_message(
            user_id,
            "? Пока нет новых совпадений.\n"
            "Мы уведомим вас, когда появятся подходящие варианты!"
        )

def send_matches_from_db(user_id, matches):
    """Отправляет пользователю совпадения из базы данных"""
    
    for match in matches[:3]:  # Показываем по 3 за раз
        match_data = match[4:]  # Данные заявки
        score = match[3]  # Процент совпадения
        
        # Создаем карточку заявки
        if match_data[2] == 'owner':  # это заявка собственника
            text = f"?? **ЗАКАЗЧИК**\n"
            text += f"?? Совпадение: {score}%\n"
            text += f"?? Город: {match_data[3]}\n"
            text += f"?? Объект: {OBJECT_TYPES.get(match_data[4], 'Не указано')}\n"
            text += f"?? Работы: {WORK_TYPES.get(match_data[5], 'Не указано')}\n"
            text += f"?? Бюджет: {BUDGET_RANGES.get(match_data[6], 'Не указано')}\n"
            
            if match_data[7]:
                text += f"?? Площадь: {match_data[7]} м?\n"
            
            if match_data[8]:
                text += f"?? Описание: {match_data[8][:200]}...\n"
            
        else:  # заявка прораба
            text = f"?? **ПРОРАБ**\n"
            text += f"?? Совпадение: {score}%\n"
            text += f"?? Город: {match_data[3]}\n"
            text += f"?? Специализация: {WORK_TYPES.get(match_data[5], 'Не указано')}\n"
            text += f"?? Бюджет: {BUDGET_RANGES.get(match_data[6], 'Не указано')}\n"
            
            if match_data[7]:
                text += f"?? Площадь: {match_data[7]} м?\n"
            
            if match_data[8]:
                text += f"?? Описание: {match_data[8][:200]}...\n"
        
        # Кнопки для взаимодействия
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "?? Показать контакты",
                callback_data=f"show_contact_{match_data[1]}"  # user_id
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "? Откликнуться",
                callback_data=f"respond_{match[0]}"  # match_id
            )
        )
        
        bot.send_message(user_id, text, reply_markup=keyboard, parse_mode='Markdown')
        db.mark_match_viewed(match[0])

@bot.callback_query_handler(func=lambda call: call.data.startswith('show_contact_'))
def show_contact(call):
    user_id = int(call.data.replace('show_contact_', ''))
    
    # Получаем данные пользователя
    db.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = db.cursor.fetchone()
    
    if user and user[4]:  # phone
        contact_text = f"?? Контактный телефон: {user[4]}"
    else:
        contact_text = "?? Пользователь не указал контактный телефон"
    
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, contact_text)

@bot.callback_query_handler(func=lambda call: call.data.startswith('respond_'))
def respond_to_match(call):
    match_id = int(call.data.replace('respond_', ''))
    
    # Получаем информацию о совпадении
    db.cursor.execute('''
        SELECT m.*, r1.user_id as target_user, r2.user_id as matched_user 
        FROM matches m
        JOIN requests r1 ON m.request_id = r1.request_id
        JOIN requests r2 ON m.matched_request_id = r2.request_id
        WHERE m.match_id = ?
    ''', (match_id,))
    
    match = db.cursor.fetchone()
    
    if match:
        bot.answer_callback_query(call.id, "? Отклик отправлен!")
        
        # Отправляем уведомление другой стороне
        bot.send_message(
            match[5],  # matched_user
            "?? Новый отклик на вашу заявку!\n"
            "Кто-то заинтересовался вашим предложением."
        )
        
        bot.send_message(
            call.from_user.id,
            "? Ваш отклик отправлен. Ожидайте ответа!"
        )
    else:
        bot.answer_callback_query(call.id, "? Ошибка")

# ============= ПРОФИЛЬ И ЗАЯВКИ =============
@bot.message_handler(func=lambda message: message.text == '?? Мои заявки')
def show_my_requests(message):
    user_id = message.from_user.id
    
    requests = db.get_user_requests(user_id)
    
    if not requests:
        bot.send_message(
            user_id,
            "У вас еще нет заявок.\n"
            "Создайте первую заявку через главное меню!"
        )
        return
    
    text = "?? **Ваши заявки:**\n\n"
    
    for i, req in enumerate(requests[:5], 1):  # Показываем последние 5
        status = "?? Активна" if req[9] == 'active' else "?? Закрыта"
        
        if req[2] == 'owner':
            text += f"{i}. {status} - Ищу бригаду\n"
            text += f"   Объект: {OBJECT_TYPES.get(req[4], 'Не указано')}\n"
        else:
            text += f"{i}. {status} - Ищу заказ\n"
            text += f"   Работы: {WORK_TYPES.get(req[5], 'Не указано')}\n"
        
        text += f"   Город: {req[3]}\n"
        text += f"   Дата: {req[10][:10]}\n\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            "? Закрыть последнюю заявку",
            callback_data="close_last_request"
        )
    )
    
    bot.send_message(user_id, text, reply_markup=keyboard, parse_mode='Markdown')

@bot.callback_query_handler(func=lambda call: call.data == 'close_last_request')
def close_last_request(call):
    user_id = call.from_user.id
    
    requests = db.get_user_requests(user_id)
    active_requests = [r for r in requests if r[9] == 'active']
    
    if active_requests:
        db.close_request(active_requests[0][0])
        bot.answer_callback_query(call.id, "? Заявка закрыта!")
        bot.send_message(user_id, "? Последняя заявка закрыта")
    else:
        bot.answer_callback_query(call.id, "? Нет активных заявок")

@bot.message_handler(func=lambda message: message.text == '?? Профиль')
def show_profile(message):
    user_id = message.from_user.id
    
    db.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = db.cursor.fetchone()
    
    if user:
        text = f"?? **Ваш профиль**\n\n"
        text += f"Имя: {user[3]}\n"
        text += f"Username: @{user[2] if user[2] else 'не указан'}\n"
        text += f"Роль: {USER_TYPES.get(user[4], 'Не указана')}\n"
        text += f"Телефон: {user[5] if user[5] else 'не указан'}\n"
        text += f"Дата регистрации: {user[6][:10]}\n"
        
        # Получаем статистику
        requests = db.get_user_requests(user_id)
        active_requests = len([r for r in requests if r[9] == 'active'])
        
        text += f"\n?? Статистика:\n"
        text += f"Всего заявок: {len(requests)}\n"
        text += f"Активных: {active_requests}\n"
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "?? Указать телефон",
                callback_data="set_phone"
            )
        )
        
        bot.send_message(user_id, text, reply_markup=keyboard, parse_mode='Markdown')
    else:
        bot.send_message(user_id, "Сначала зарегистрируйтесь!")

@bot.callback_query_handler(func=lambda call: call.data == 'set_phone')
def set_phone_start(call):
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    bot.send_message(
        user_id,
        "?? Отправьте ваш номер телефона для связи:",
        reply_markup=get_cancel_keyboard()
    )
    
    bot.register_next_step_handler_by_chat_id(user_id, save_phone)

def save_phone(message):
    user_id = message.from_user.id
    
    if message.text