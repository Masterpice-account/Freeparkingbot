import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext, MessageHandler, Filters
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Настройки
TOKEN = "7730856052:AAEESnS64VLnUZ3ckE4r4oE8gRohf3FUV6A"
GOOGLE_SHEETS_KEY = "https://docs.google.com/spreadsheets/d/1NtkB8lz_Aqs7f9dvglbpX_OBtXZMV9yIm5Ue3tninUs/edit?usp=sharing"

# Подключение к Google Таблицам
scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
client = gspread.authorize(creds)
sheet = client.open_by_url(GOOGLE_SHEETS_KEY)

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Кнопки районов
DISTRICTS = ["ЦАО", "САО", "СВАО", "ВАО", "ЮВАО", "ЮАО", "ЮЗАО", "ЗАО", "СЗАО"]

def start(update: Update, context: CallbackContext):
    user = update.message.from_user
    update.message.reply_text(
        f"Привет, {user.first_name}! В каком районе Москвы ты находишься?",
        reply_markup=district_buttons()
    )

def district_buttons():
    buttons = [[InlineKeyboardButton(d, callback_data=d)] for d in DISTRICTS]
    return InlineKeyboardMarkup(buttons)

def button_click(update: Update, context: CallbackContext):
    query = update.callback_query
    data = query.data

    if data in DISTRICTS:
        context.user_data['district'] = data
        query.edit_message_text(text=f"Ты выбрал {data}. Хочешь получить список парковок или добавить адрес?",
                               reply_markup=action_buttons())
    elif data == "get_list":
        send_parking_list(update, context)
    elif data == "add_address":
        context.bot.send_message(chat_id=query.message.chat_id, 
                                text="Напиши адрес парковки (например: Улица Тверская, 10):")
        return "wait_address"
    elif data == "cancel":
        query.edit_message_text(text="Действие отменено.")
        return -1

def action_buttons():
    buttons = [
        [InlineKeyboardButton("Получить список парковок", callback_data="get_list")],
        [InlineKeyboardButton("Добавить адрес парковки", callback_data="add_address")]
    ]
    return InlineKeyboardMarkup(buttons)

def send_parking_list(update: Update, context: CallbackContext):
    district = context.user_data['district']
    worksheet = sheet.worksheet('Проверенные')
    records = worksheet.get_all_records()
    addresses = [f"📍 {row['Адрес']}" for row in records if row['Район'] == district]
    
    if addresses:
        context.bot.send_message(chat_id=update.callback_query.message.chat_id, 
                                text=f"Список парковок в {district}:\n\n" + "\n".join(addresses))
    else:
        context.bot.send_message(chat_id=update.callback_query.message.chat_id, 
                                text="В этом районе пока нет проверенных парковок 😢")

def save_address(update: Update, context: CallbackContext):
    address = update.message.text
    district = context.user_data['district']
    worksheet = sheet.worksheet('Непроверенные')
    worksheet.append_row([district, address, "На проверке"])
    
    update.message.reply_text("Спасибо! Адрес отправлен на проверку администраторам ✅")
    return -1

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CallbackQueryHandler(button_click))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, save_address), group=1)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
