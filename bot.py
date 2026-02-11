# -*- coding: utf-8 -*-
import telebot
from telebot import types
from config import *
from database import Database
from matching import MatchingAlgorithm
import time

bot = telebot.TeleBot(BOT_TOKEN)
db = Database()
matcher = MatchingAlgorithm()

# Õðàíèëèùå âðåìåííûõ äàííûõ ïîëüçîâàòåëåé
user_data = {}

# ============= ÊËÀÂÈÀÒÓÐÛ =============
def get_main_keyboard(user_type=None):
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    
    if user_type == 'prorab':
        keyboard.add(types.KeyboardButton('?? Ñîçäàòü çàÿâêó (èùó çàêàç)'))
        keyboard.add(types.KeyboardButton('?? Íàéòè çàêàçû'))
        keyboard.add(types.KeyboardButton('?? Ìîè çàÿâêè'))
        keyboard.add(types.KeyboardButton('?? Ïðîôèëü'))
    elif user_type == 'owner':
        keyboard.add(types.KeyboardButton('?? Ñîçäàòü çàÿâêó (èùó áðèãàäó)'))
        keyboard.add(types.KeyboardButton('?? Íàéòè áðèãàäû'))
        keyboard.add(types.KeyboardButton('?? Ìîè çàÿâêè'))
        keyboard.add(types.KeyboardButton('?? Ïðîôèëü'))
    else:
        keyboard.add(types.KeyboardButton('?? Ðåãèñòðàöèÿ'))
        keyboard.add(types.KeyboardButton('?? Î áîòå'))
    
    return keyboard

def get_cancel_keyboard():
    keyboard = types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(types.KeyboardButton('? Îòìåíèòü'))
    return keyboard

# ============= ÎÁÐÀÁÎÒ×ÈÊÈ ÊÎÌÀÍÄ =============
@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    
    # Ïðîâåðÿåì, çàðåãèñòðèðîâàí ëè ïîëüçîâàòåëü
    user_requests = db.get_user_requests(user_id)
    if user_requests:
        # Ïîëó÷àåì òèï ïîëüçîâàòåëÿ èç ïîñëåäíåé çàÿâêè
        last_request = user_requests[0]
        user_type = last_request[2]
        bot.send_message(
            user_id,
            f"?? Ñ âîçâðàùåíèåì, {message.from_user.first_name}!",
            reply_markup=get_main_keyboard(user_type)
        )
    else:
        bot.send_message(
            user_id,
            "?? Äîáðî ïîæàëîâàòü â ñòðîèòåëüíûé áîò!\n\n"
            "Çäåñü âû ìîæåòå íàéòè ïðîôåññèîíàëüíîãî ïðîðàáà "
            "èëè çàêàç÷èêà äëÿ ðåìîíòà è ñòðîèòåëüñòâà.\n\n"
            "Íàø àëãîðèòì ïîäáåðåò íàèáîëåå ïîäõîäÿùèå âàðèàíòû "
            "íà îñíîâå âàøèõ êðèòåðèåâ.",
            reply_markup=get_main_keyboard()
        )

@bot.message_handler(func=lambda message: message.text == '?? Ðåãèñòðàöèÿ')
def register_start(message):
    user_id = message.from_user.id
    user_data[user_id] = {'step': 'choose_type'}
    
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        types.InlineKeyboardButton("?? Ïðîðàá", callback_data="type_prorab"),
        types.InlineKeyboardButton("?? Ñîáñòâåííèê", callback_data="type_owner")
    )
    
    bot.send_message(
        user_id,
        "?? Âûáåðèòå âàøó ðîëü:",
        reply_markup=keyboard
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('type_'))
def process_user_type(call):
    user_id = call.from_user.id
    user_type = call.data.replace('type_', '')
    
    # Ñîõðàíÿåì ïîëüçîâàòåëÿ â ÁÄ
    db.add_user(
        user_id=user_id,
        username=call.from_user.username,
        full_name=call.from_user.full_name,
        user_type=user_type
    )
    
    bot.answer_callback_query(call.id, "Ðåãèñòðàöèÿ çàâåðøåíà!")
    bot.edit_message_text(
        f"? Âû çàðåãèñòðèðîâàíû êàê: {USER_TYPES[user_type]}",
        user_id,
        call.message.message_id
    )
    
    bot.send_message(
        user_id,
        "Òåïåðü âû ìîæåòå ñîçäàâàòü çàÿâêè è èñêàòü ïàðòíåðîâ!",
        reply_markup=get_main_keyboard(user_type)
    )

# ============= ÑÎÇÄÀÍÈÅ ÇÀßÂÊÈ =============
@bot.message_handler(func=lambda message: message.text in [
    '?? Ñîçäàòü çàÿâêó (èùó çàêàç)',
    '?? Ñîçäàòü çàÿâêó (èùó áðèãàäó)'
])
def create_request_start(message):
    user_id = message.from_user.id
    user_requests = db.get_user_requests(user_id)
    
    if not user_requests:
        bot.send_message(user_id, "Ñíà÷àëà íóæíî çàðåãèñòðèðîâàòüñÿ!")
        return
    
    last_request = user_requests[0]
    user_type = last_request[2]
    
    user_data[user_id] = {
        'step': 'city',
        'user_type': user_type
    }
    
    # Ñîçäàåì êëàâèàòóðó ñ ãîðîäàìè
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    for city in CITIES:
        keyboard.add(types.InlineKeyboardButton(city, callback_data=f"city_{city}"))
    
    bot.send_message(
        user_id,
        "?? Â êàêîì ãîðîäå íàõîäèòñÿ îáúåêò?",
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
        f"? Ãîðîä: {city}\n\n?? Âûáåðèòå òèï îáúåêòà:",
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
        f"? Òèï îáúåêòà: {OBJECT_TYPES[object_type]}\n\n"
        "?? Âûáåðèòå âèä ðàáîò:",
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
        f"? Âèä ðàáîò: {WORK_TYPES[work_type]}\n\n"
        "?? Âûáåðèòå áþäæåò:",
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
        f"? Áþäæåò: {BUDGET_RANGES[budget]}\n\n"
        "?? Ââåäèòå ïëîùàäü ïîìåùåíèÿ (â ì?):\n"
        "(èëè îòïðàâüòå '0', åñëè íå çíàåòå)",
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
            "?? Äîáàâüòå îïèñàíèå âàøåãî ïðîåêòà.\n"
            "Óêàæèòå îñîáåííîñòè, ñðîêè, ïîæåëàíèÿ:\n"
            "(èëè îòïðàâüòå '-', ÷òîáû ïðîïóñòèòü)",
            reply_markup=get_cancel_keyboard()
        )
        
        bot.register_next_step_handler(message, process_description)
    except ValueError:
        bot.send_message(
            user_id,
            "? Ïîæàëóéñòà, ââåäèòå ÷èñëî.\n"
            "?? Ïëîùàäü ïîìåùåíèÿ (â ì?):"
        )
        bot.register_next_step_handler(message, process_square)

def process_description(message):
    user_id = message.from_user.id
    
    if message.text == '? Îòìåíèòü':
        cancel_creation(message)
        return
    
    description = message.text if message.text != '-' else ""
    
    # Ñîõðàíÿåì çàÿâêó â ÁÄ
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
        "? Çàÿâêà óñïåøíî ñîçäàíà!\n"
        "?? Íà÷èíàåì ïîèñê ïîäõîäÿùèõ âàðèàíòîâ...",
        reply_markup=get_main_keyboard(user_data[user_id]['user_type'])
    )
    
    # Çàïóñêàåì ïîèñê ñîâïàäåíèé
    find_matches(user_id, request_id)
    
    del user_data[user_id]

def cancel_creation(message):
    user_id = message.from_user.id
    user_requests = db.get_user_requests(user_id)
    user_type = user_requests[0][2] if user_requests else None
    
    bot.send_message(
        user_id,
        "? Ñîçäàíèå çàÿâêè îòìåíåíî",
        reply_markup=get_main_keyboard(user_type)
    )
    
    if user_id in user_data:
        del user_data[user_id]

# ============= ÀËÃÎÐÈÒÌ ÏÎÄÁÎÐÀ =============
def find_matches(user_id, request_id):
    """Íàõîäèò ïîäõîäÿùèå çàÿâêè äëÿ òîëüêî ÷òî ñîçäàííîé"""
    
    # Ïîëó÷àåì öåëåâóþ çàÿâêó
    db.cursor.execute('SELECT * FROM requests WHERE request_id = ?', (request_id,))
    target_request = db.cursor.fetchone()
    
    # Îïðåäåëÿåì, êîãî èùåì
    looking_for = 'owner' if target_request[2] == 'prorab' else 'prorab'
    
    # Ïîëó÷àåì âñå àêòèâíûå çàÿâêè ïðîòèâîïîëîæíîãî òèïà
    potential_requests = db.get_active_requests(user_type=looking_for)
    
    # Èùåì ñîâïàäåíèÿ
    matches = matcher.find_best_matches(target_request, potential_requests, limit=5)
    
    # Ñîõðàíÿåì íàéäåííûå ñîâïàäåíèÿ
    for request, score in matches:
        db.save_match(request_id, request[0], score)
    
    # Îòïðàâëÿåì ðåçóëüòàò ïîëüçîâàòåëþ
    if matches:
        send_matches_to_user(user_id, request_id, matches)
    else:
        bot.send_message(
            user_id,
            "?? Ïîêà íå íàéäåíî ïîäõîäÿùèõ âàðèàíòîâ.\n"
            "Ìû ïðîäîëæèì ïîèñê è óâåäîìèì âàñ, êîãäà ïîÿâÿòñÿ íîâûå çàÿâêè!"
        )

def send_matches_to_user(user_id, request_id, matches):
    """Îòïðàâëÿåò íàéäåííûå ñîâïàäåíèÿ ïîëüçîâàòåëþ"""
    
    text = f"?? Íàéäåíî {len(matches)} ïîäõîäÿùèõ âàðèàíòîâ!\n\n"
    
    for i, (request, score) in enumerate(matches, 1):
        text += f"?? Âàðèàíò #{i}\n"
        text += f"?? Ñîâïàäåíèå: {score}%\n"
        
        if request[2] == 'owner':
            text += f"?? Ñîáñòâåííèê èùåò: {OBJECT_TYPES.get(request[4], 'Íå óêàçàíî')}\n"
        else:
            text += f"?? Ïðîðàá: {WORK_TYPES.get(request[5], 'Íå óêàçàíî')}\n"
        
        text += f"?? Ãîðîä: {request[3]}\n"
        text += f"?? Áþäæåò: {BUDGET_RANGES.get(request[6], 'Íå óêàçàíî')}\n"
        
        if request[7]:  # ïëîùàäü
            text += f"?? Ïëîùàäü: {request[7]} ì?\n"
        
        text += "\n"
    
    text += "Äëÿ ïðîñìîòðà äåòàëåé èñïîëüçóéòå ðàçäåë 'Ìîè çàÿâêè'"
    
    bot.send_message(user_id, text)

# ============= ÏÎÈÑÊ ÇÀßÂÎÊ =============
@bot.message_handler(func=lambda message: message.text in ['?? Íàéòè çàêàçû', '?? Íàéòè áðèãàäû'])
def search_requests(message):
    user_id = message.from_user.id
    
    user_requests = db.get_user_requests(user_id)
    if not user_requests:
        bot.send_message(user_id, "Ñíà÷àëà ñîçäàéòå çàÿâêó!")
        return
    
    # Ïîëó÷àåì ïîñëåäíþþ àêòèâíóþ çàÿâêó ïîëüçîâàòåëÿ
    active_requests = [r for r in user_requests if r[9] == 'active']
    
    if not active_requests:
        bot.send_message(
            user_id,
            "Ó âàñ íåò àêòèâíûõ çàÿâîê. Ñîçäàéòå íîâóþ çàÿâêó äëÿ ïîèñêà!"
        )
        return
    
    last_request = active_requests[0]
    
    # Ïîëó÷àåì ñîõðàíåííûå ñîâïàäåíèÿ
    matches = db.get_matches_for_request(last_request[0])
    
    if matches:
        send_matches_from_db(user_id, matches)
    else:
        bot.send_message(
            user_id,
            "? Ïîêà íåò íîâûõ ñîâïàäåíèé.\n"
            "Ìû óâåäîìèì âàñ, êîãäà ïîÿâÿòñÿ ïîäõîäÿùèå âàðèàíòû!"
        )

def send_matches_from_db(user_id, matches):
    """Îòïðàâëÿåò ïîëüçîâàòåëþ ñîâïàäåíèÿ èç áàçû äàííûõ"""
    
    for match in matches[:3]:  # Ïîêàçûâàåì ïî 3 çà ðàç
        match_data = match[4:]  # Äàííûå çàÿâêè
        score = match[3]  # Ïðîöåíò ñîâïàäåíèÿ
        
        # Ñîçäàåì êàðòî÷êó çàÿâêè
        if match_data[2] == 'owner':  # ýòî çàÿâêà ñîáñòâåííèêà
            text = f"?? **ÇÀÊÀÇ×ÈÊ**\n"
            text += f"?? Ñîâïàäåíèå: {score}%\n"
            text += f"?? Ãîðîä: {match_data[3]}\n"
            text += f"?? Îáúåêò: {OBJECT_TYPES.get(match_data[4], 'Íå óêàçàíî')}\n"
            text += f"?? Ðàáîòû: {WORK_TYPES.get(match_data[5], 'Íå óêàçàíî')}\n"
            text += f"?? Áþäæåò: {BUDGET_RANGES.get(match_data[6], 'Íå óêàçàíî')}\n"
            
            if match_data[7]:
                text += f"?? Ïëîùàäü: {match_data[7]} ì?\n"
            
            if match_data[8]:
                text += f"?? Îïèñàíèå: {match_data[8][:200]}...\n"
            
        else:  # çàÿâêà ïðîðàáà
            text = f"?? **ÏÐÎÐÀÁ**\n"
            text += f"?? Ñîâïàäåíèå: {score}%\n"
            text += f"?? Ãîðîä: {match_data[3]}\n"
            text += f"?? Ñïåöèàëèçàöèÿ: {WORK_TYPES.get(match_data[5], 'Íå óêàçàíî')}\n"
            text += f"?? Áþäæåò: {BUDGET_RANGES.get(match_data[6], 'Íå óêàçàíî')}\n"
            
            if match_data[7]:
                text += f"?? Ïëîùàäü: {match_data[7]} ì?\n"
            
            if match_data[8]:
                text += f"?? Îïèñàíèå: {match_data[8][:200]}...\n"
        
        # Êíîïêè äëÿ âçàèìîäåéñòâèÿ
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "?? Ïîêàçàòü êîíòàêòû",
                callback_data=f"show_contact_{match_data[1]}"  # user_id
            )
        )
        keyboard.add(
            types.InlineKeyboardButton(
                "? Îòêëèêíóòüñÿ",
                callback_data=f"respond_{match[0]}"  # match_id
            )
        )
        
        bot.send_message(user_id, text, reply_markup=keyboard, parse_mode='Markdown')
        db.mark_match_viewed(match[0])

@bot.callback_query_handler(func=lambda call: call.data.startswith('show_contact_'))
def show_contact(call):
    user_id = int(call.data.replace('show_contact_', ''))
    
    # Ïîëó÷àåì äàííûå ïîëüçîâàòåëÿ
    db.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = db.cursor.fetchone()
    
    if user and user[4]:  # phone
        contact_text = f"?? Êîíòàêòíûé òåëåôîí: {user[4]}"
    else:
        contact_text = "?? Ïîëüçîâàòåëü íå óêàçàë êîíòàêòíûé òåëåôîí"
    
    bot.answer_callback_query(call.id)
    bot.send_message(call.from_user.id, contact_text)

@bot.callback_query_handler(func=lambda call: call.data.startswith('respond_'))
def respond_to_match(call):
    match_id = int(call.data.replace('respond_', ''))
    
    # Ïîëó÷àåì èíôîðìàöèþ î ñîâïàäåíèè
    db.cursor.execute('''
        SELECT m.*, r1.user_id as target_user, r2.user_id as matched_user 
        FROM matches m
        JOIN requests r1 ON m.request_id = r1.request_id
        JOIN requests r2 ON m.matched_request_id = r2.request_id
        WHERE m.match_id = ?
    ''', (match_id,))
    
    match = db.cursor.fetchone()
    
    if match:
        bot.answer_callback_query(call.id, "? Îòêëèê îòïðàâëåí!")
        
        # Îòïðàâëÿåì óâåäîìëåíèå äðóãîé ñòîðîíå
        bot.send_message(
            match[5],  # matched_user
            "?? Íîâûé îòêëèê íà âàøó çàÿâêó!\n"
            "Êòî-òî çàèíòåðåñîâàëñÿ âàøèì ïðåäëîæåíèåì."
        )
        
        bot.send_message(
            call.from_user.id,
            "? Âàø îòêëèê îòïðàâëåí. Îæèäàéòå îòâåòà!"
        )
    else:
        bot.answer_callback_query(call.id, "? Îøèáêà")

# ============= ÏÐÎÔÈËÜ È ÇÀßÂÊÈ =============
@bot.message_handler(func=lambda message: message.text == '?? Ìîè çàÿâêè')
def show_my_requests(message):
    user_id = message.from_user.id
    
    requests = db.get_user_requests(user_id)
    
    if not requests:
        bot.send_message(
            user_id,
            "Ó âàñ åùå íåò çàÿâîê.\n"
            "Ñîçäàéòå ïåðâóþ çàÿâêó ÷åðåç ãëàâíîå ìåíþ!"
        )
        return
    
    text = "?? **Âàøè çàÿâêè:**\n\n"
    
    for i, req in enumerate(requests[:5], 1):  # Ïîêàçûâàåì ïîñëåäíèå 5
        status = "?? Àêòèâíà" if req[9] == 'active' else "?? Çàêðûòà"
        
        if req[2] == 'owner':
            text += f"{i}. {status} - Èùó áðèãàäó\n"
            text += f"   Îáúåêò: {OBJECT_TYPES.get(req[4], 'Íå óêàçàíî')}\n"
        else:
            text += f"{i}. {status} - Èùó çàêàç\n"
            text += f"   Ðàáîòû: {WORK_TYPES.get(req[5], 'Íå óêàçàíî')}\n"
        
        text += f"   Ãîðîä: {req[3]}\n"
        text += f"   Äàòà: {req[10][:10]}\n\n"
    
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(
        types.InlineKeyboardButton(
            "? Çàêðûòü ïîñëåäíþþ çàÿâêó",
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
        bot.answer_callback_query(call.id, "? Çàÿâêà çàêðûòà!")
        bot.send_message(user_id, "? Ïîñëåäíÿÿ çàÿâêà çàêðûòà")
    else:
        bot.answer_callback_query(call.id, "? Íåò àêòèâíûõ çàÿâîê")

@bot.message_handler(func=lambda message: message.text == '?? Ïðîôèëü')
def show_profile(message):
    user_id = message.from_user.id
    
    db.cursor.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
    user = db.cursor.fetchone()
    
    if user:
        text = f"?? **Âàø ïðîôèëü**\n\n"
        text += f"Èìÿ: {user[3]}\n"
        text += f"Username: @{user[2] if user[2] else 'íå óêàçàí'}\n"
        text += f"Ðîëü: {USER_TYPES.get(user[4], 'Íå óêàçàíà')}\n"
        text += f"Òåëåôîí: {user[5] if user[5] else 'íå óêàçàí'}\n"
        text += f"Äàòà ðåãèñòðàöèè: {user[6][:10]}\n"
        
        # Ïîëó÷àåì ñòàòèñòèêó
        requests = db.get_user_requests(user_id)
        active_requests = len([r for r in requests if r[9] == 'active'])
        
        text += f"\n?? Ñòàòèñòèêà:\n"
        text += f"Âñåãî çàÿâîê: {len(requests)}\n"
        text += f"Àêòèâíûõ: {active_requests}\n"
        
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(
            types.InlineKeyboardButton(
                "?? Óêàçàòü òåëåôîí",
                callback_data="set_phone"
            )
        )
        
        bot.send_message(user_id, text, reply_markup=keyboard, parse_mode='Markdown')
    else:
        bot.send_message(user_id, "Ñíà÷àëà çàðåãèñòðèðóéòåñü!")

@bot.callback_query_handler(func=lambda call: call.data == 'set_phone')
def set_phone_start(call):
    user_id = call.from_user.id
    
    bot.answer_callback_query(call.id)
    bot.send_message(
        user_id,
        "?? Îòïðàâüòå âàø íîìåð òåëåôîíà äëÿ ñâÿçè:",
        reply_markup=get_cancel_keyboard()
    )
    
    bot.register_next_step_handler_by_chat_id(user_id, save_phone)

def save_phone(message):
    user_id = message.from_user.id
    

    if message.text
