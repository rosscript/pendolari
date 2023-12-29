from aiogram.dispatcher import FSMContext
from states import ShowTicket, EditTicket
from setup import dp
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import types  
import logging
from database import get_ticket_details, update_ticket, delete_ticket
from utils import valida_campo_ticket, convert_date_format_for_list

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dp.message_handler(lambda message: message.text.isdigit(), state=ShowTicket.waiting_for_ticket_id)
async def show_ticket_details(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    item_map = user_data.get('item_map', {})
    selection = int(message.text.strip())

    if selection in item_map and item_map[selection][0] == 'ticket':
        ticket_id = item_map[selection][1]

    if not ticket_id:
        await message.reply("Si è verificato un errore nel recupero dell'ID dell'annuncio.")
        return 

    ticket_details = await get_ticket_details(ticket_id)
    if ticket_details:
        response = (f"🎫 Cedo Biglietto 🎫\n\n"
                    f"📅 Data: {convert_date_format_for_list(ticket_details[6])}\n"
                    f"🚉 Partenza: {ticket_details[2]} alle {ticket_details[3]}\n"
                    f"🚉 Arrivo: {ticket_details[4]} alle {ticket_details[5]}\n"
                    f"💵 Prezzo: {ticket_details[7]}€\n"
                    f"🚄 Treno: {ticket_details[8]}\n"
                    f"🔍 Dettagli: {ticket_details[9]}\n")

        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(InlineKeyboardButton("✏️ Modifica", callback_data=f'modify_ticket_{ticket_id}'),
                     InlineKeyboardButton("🗑 Elimina", callback_data=f'delete_ticket_{ticket_id}'),
                     InlineKeyboardButton("🔙 Indietro", callback_data='start'))

        await message.answer(response, reply_markup=keyboard)
        await ShowTicket.next()
    else:
        await message.reply("Biglietto non trovato.")
    
    # Resetta lo stato o passa a un altro stato se necessario
    await ShowTicket.waiting_for_ticket_action.set()

# Recupero dei dettagli del biglietto da modificare
@dp.callback_query_handler(lambda c: c.data.startswith('modify_ticket_'), state=ShowTicket.waiting_for_ticket_action)
async def handle_modify_ticket(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    ticket_id = callback_query.data.split('_')[2]
    ticket_details = await get_ticket_details(int(ticket_id))

    if ticket_details:
        await state.update_data(current_ticket_details=ticket_details)

        response = format_ticket_details(ticket_details)
        keyboard = create_keyboard()

        sent_message = await callback_query.message.answer(response, reply_markup=keyboard)
        await state.update_data(message_id=sent_message.message_id)
        await state.update_data(ticket_id=ticket_id)
        await EditTicket.choosing_field.set()
    else:
        await callback_query.message.reply("Biglietto non trovato.")

# Modifica del biglietto
@dp.message_handler(state=EditTicket.choosing_field)
async def process_field_edit_ticket(message: types.Message, state: FSMContext):
    field_mapping = {
        0: 6,  # Data
        1: 2,  # Partenza
        2: 3,  # Ora di partenza
        3: 4,  # Arrivo
        4: 5,  # Ora di arrivo
        5: 7,  # Prezzo
        6: 8,  # Tipo di treno
        7: 9   # Dettagli
    }

    user_data = await state.get_data()
    ticket_details_list = list(user_data.get("current_ticket_details", []))
    is_modified = user_data.get("is_modified", False)
    
    try:
        field_number, new_value = message.text.split(maxsplit=1)
        field_number = int(field_number)
        tuple_index = field_mapping[field_number]

        field_name = next(key for key, value in field_mapping.items() if value == tuple_index)
        valid_value, error = valida_campo_ticket(field_name, new_value)

        if error:
            await message.reply(f"Errore di validazione: {error}")
            return

        ticket_details_list[tuple_index] = valid_value
        updated_ticket_details = tuple(ticket_details_list)
        await state.update_data(current_ticket_details=updated_ticket_details)
        await state.update_data(is_modified=True)
        
        response = format_ticket_details(updated_ticket_details)
        message_id = user_data.get("message_id")
        
        keyboard = create_keyboard_with_save()
            
        if message_id:
            await message.bot.edit_message_text(chat_id=message.chat.id, message_id=message_id, text=response, reply_markup=keyboard)
        else:
            await message.reply(response, reply_markup=keyboard)

    except (ValueError, IndexError, KeyError):
        await message.reply("Formato non valido, numero di campo errato, o campo non esistente. Riprova.")



def format_ticket_details(ticket_details):
    # Assumi che ticket_details sia una tupla con un ordine specifico
    # Ad esempio: (id, departure, departure_time, arrival, arrival_time, date, price, train_type, details)
    return (f"🎫 Cedo Biglietto 🎫\n\n"
            f"📅 [0] Data: {ticket_details[6]}\n"
            f"🚉 [1] Partenza: {ticket_details[2]}\n"
            f"🕙 [2] Ora partenza: {ticket_details[3]}\n"
            f"🚉 [3] Arrivo: {ticket_details[4]}\n"
            f"🕙 [4] Ora arrivo: {ticket_details[5]}\n"
            f"💵 [5] Prezzo: {ticket_details[7]}€\n"
            f"🚄 [6] Treno: {ticket_details[8]}\n"
            f"🔍 [7] Dettagli: {ticket_details[9]}\n\n"
            f"Modifica i campi inviando il codice del campo seguito dal nuovo valore. Es: '2 14:30' per cambiare l'orario di partenza.\n")

# Funzione ausiliaria per creare la keyboard inline
def create_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("🔙 Indietro", callback_data='myrides'))
    return keyboard

# Funzione ausiliaria per creare la keyboard con il pulsante "Salva modifiche"
def create_keyboard_with_save():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("✅ Salva modifiche", callback_data='approve'))
    keyboard.add(InlineKeyboardButton("🔙 Annulla", callback_data='myrides'))
    return keyboard

# Funzione ausiliaria per creare la keyboard con il pulsante "Salva modifiche"
def create_keyboard_with_home():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("🗂 I tuoi annunci", callback_data='myrides'))
    keyboard.add(InlineKeyboardButton("🏠 Home", callback_data='start'))
    return keyboard

#Approvazione delle modifiche
@dp.callback_query_handler(lambda c: c.data == 'approve', state=EditTicket.choosing_field)
async def approve_ticket_changes(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    ticket_id = user_data.get("ticket_id")
    current_ticket_details = user_data.get("current_ticket_details")

    if current_ticket_details:
        updates = {
            'departure': current_ticket_details[2],
            'departure_time': current_ticket_details[3],
            'arrival': current_ticket_details[4],
            'arrival_time': current_ticket_details[5],
            'date': current_ticket_details[6],
            'price': current_ticket_details[7],
            'train_type': current_ticket_details[8],
            'details': current_ticket_details[9]
        }

        try:
            await update_ticket(ticket_id, updates)
            keyboard = create_keyboard_with_home()
            await callback_query.message.reply("Modifiche salvate con successo nel database.", reply_markup=keyboard)
        except Exception as e:
            keyboard = create_keyboard_with_home()
            await callback_query.message.reply(f"Errore durante il salvataggio delle modifiche: {e}", reply_markup=keyboard)
    else:
        keyboard = create_keyboard_with_home()
        await callback_query.message.reply("Nessuna modifica da salvare.", reply_markup=keyboard)

    await state.finish()


#Eliminazione del biglietto
@dp.callback_query_handler(lambda c: c.data.startswith('delete_ticket_'), state=ShowTicket.waiting_for_ticket_action)
async def handle_delete_ticket(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    ticket_id = callback_query.data.split('_')[2]
    await state.update_data(ticket_id=ticket_id)

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("🗑 Elimina", callback_data=f'confirm_delete_ticket_{ticket_id}'),
                 InlineKeyboardButton("✖️ Annulla", callback_data='cancel_delete'))

    await callback_query.message.answer("Sei sicuro di voler eliminare questo biglietto?", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith('confirm_delete_ticket_'), state=ShowTicket.waiting_for_ticket_action)
async def confirm_delete_ticket(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    user_data = await state.get_data()
    ticket_id = user_data.get("ticket_id")

    await delete_ticket(int(ticket_id))
    markup = create_keyboard_with_home()
    await callback_query.message.answer("🗑 Biglietto eliminato con successo.", reply_markup=markup)
    await callback_query.message.edit_reply_markup(reply_markup=None)

    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'cancel_delete', state=ShowTicket.waiting_for_ticket_action)
async def cancel_delete_ticket(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    markup = create_keyboard_with_home()
    await callback_query.message.answer("✖️ Eliminazione annullata.", reply_markup=markup)
    await callback_query.message.edit_reply_markup(reply_markup=None)

    await state.finish()

