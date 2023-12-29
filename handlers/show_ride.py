from aiogram.dispatcher import FSMContext
from states import ShowRide, EditRide
from setup import dp
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import types  
import logging
from database import get_ride_details, update_ride, delete_ride
from utils import valida_campo_annuncio, convert_date_format_for_list

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dp.message_handler(lambda message: message.text.isdigit(), state=ShowRide.waiting_for_ride_id)
async def show_ride_details(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    item_map = user_data.get('item_map', {})
    selection = int(message.text.strip())

    ride_id = None
    if selection in item_map and item_map[selection][0] == 'ride':
        ride_id = item_map[selection][1]

    if not ride_id:
        await message.reply("Si è verificato un errore nel recupero dell'ID dell'annuncio.")
        return

    ride_details = await get_ride_details(ride_id)
    if ride_details:
        # Formatta i dettagli dell'annuncio
        tappe_text = f"🚩 Tappe: {ride_details[3]}\n" if ride_details[3] != "Nessuna" else ""
        response = (f"📢 Offro Passaggio 📢\n\n"
                    f"📆 Data: {convert_date_format_for_list(ride_details[5])}\n"
                    f"📍 Partenza: {ride_details[2]}\n"
                    + tappe_text +
                    f"🏁 Arrivo: {ride_details[4]}\n"
                    f"💵 Prezzo: {ride_details[9]}€\n"
                    f"🚗 Veicolo: {ride_details[8]}\n"
                    f"🧳 Bagaglio: {ride_details[10]}\n"
                    f"💺 Posti: {ride_details[11]}\n"
                    f"🔍 Dettagli: {ride_details[6]}\n")

        # Crea la keyboard inline con i pulsanti
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(InlineKeyboardButton("✏️ Modifica", callback_data=f'modify_{ride_id}'),
                     InlineKeyboardButton("🗑 Elimina", callback_data=f'delete_{ride_id}'),
                     InlineKeyboardButton("🔙 Indietro", callback_data='myrides'))

        # Invia il messaggio con i dettagli dell'annuncio
        await message.answer(response, reply_markup=keyboard)
        await ShowRide.next()
    else:
        await message.reply("Annuncio non trovato.")

    # Resetta lo stato o passa a un altro stato se necessario
    await ShowRide.waiting_for_ride_action.set()


@dp.callback_query_handler(lambda c: c.data.startswith('modify_'), state=ShowRide.waiting_for_ride_action)
async def handle_modify_button(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    ride_id = callback_query.data.split('_')[1]
    ride_details = await get_ride_details(int(ride_id))

    if ride_details:
        # Inizialmente, imposta i dettagli correnti dell'annuncio come lo stato iniziale per le modifiche
        await state.update_data(current_ride_details=ride_details)

        response = format_ride_details(ride_details)
        keyboard = create_keyboard()

        sent_message = await callback_query.message.answer(response, reply_markup=keyboard)
        await state.update_data(message_id=sent_message.message_id)
        await state.update_data(ride_id=ride_id)
        await EditRide.choosing_field.set()
    else:
        await callback_query.message.reply("Annuncio non trovato.")

@dp.message_handler(state=EditRide.choosing_field)
async def process_field_edit(message: types.Message, state: FSMContext):
    field_mapping = {
        0: 5,  # Data
        1: 2,  # Partenza
        2: 3,  # Tappe
        3: 4,  # Arrivo
        4: 9,  # Prezzo
        5: 8,  # Veicolo
        6: 10, # Bagaglio
        7: 11, # Posti
        8: 6   # Dettagli
    }

    user_data = await state.get_data()
    ride_details_list = list(user_data.get("current_ride_details", []))

    try:
        field_number, new_value = message.text.split(maxsplit=1)
        field_number = int(field_number)
        actual_index = field_mapping[field_number]

        # Gestione input 'no' per tappe e dettagli
        if actual_index == 3 and new_value.lower() == 'no':  # Tappe
            valid_value = 'Nessuna'
            error = None
        elif actual_index == 6 and new_value.lower() == 'no':  # Dettagli
            valid_value = 'Nessun dettaglio'
            error = None
        else:
            valid_value, error = valida_campo_annuncio(actual_index, new_value)

        if error:
            await message.reply(f"Errore di validazione: {error}")
            return

        ride_details_list[actual_index] = valid_value
        updated_ride_details = tuple(ride_details_list)
        await state.update_data(current_ride_details=updated_ride_details)

        response = format_ride_details(updated_ride_details)
        keyboard = create_keyboard_with_save()

        message_id = user_data.get("message_id")
        if message_id:
            await message.bot.edit_message_text(chat_id=message.chat.id, message_id=message_id, text=response, reply_markup=keyboard)
        else:
            await message.reply("Errore: ID del messaggio non trovato.")

    except (ValueError, IndexError, KeyError):
        await message.reply("Formato non valido, numero di campo errato, o campo non esistente. Riprova.")



# Funzione ausiliaria per formattare i dettagli dell'annuncio
def format_ride_details(ride_details):
    return (f"📢 Offro passaggio 📢\n\n"
            f"📆 [0] Data: {convert_date_format_for_list(ride_details[5])}\n"
            f"📍 [1] Partenza: {ride_details[2]}\n"
            f"🚩 [2] Tappe: {ride_details[3]}\n"
            f"🏁 [3] Arrivo: {ride_details[4]}\n"
            f"💵 [4] Prezzo: {ride_details[9]}€\n"
            f"🚗 [5] Veicolo: {ride_details[8]}\n"
            f"🧳 [6] Bagaglio: {ride_details[10]}\n"
            f"💺 [7] Posti: {ride_details[11]}\n"
            f"🔍 [8] Dettagli: {ride_details[6]}\n\n"
            f"Modifica i campi inviando il codice del campo seguito dal nuovo valore. Es: '1 Torino' per cambiare la città di partenza in Torino. \n")

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

@dp.callback_query_handler(lambda c: c.data == 'approve', state=EditRide.choosing_field)
async def approve_changes(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    ride_id = user_data.get("ride_id")
    current_ride_details = user_data.get("current_ride_details")

    if current_ride_details:
        # Aggiornamento del dizionario in base alla struttura della tabella rides
        updates = {
            'user_id': current_ride_details[1],    # user_id
            'departure': current_ride_details[2],  # Partenza
            'stops': current_ride_details[3],      # Tappe
            'arrival': current_ride_details[4],    # Arrivo
            'date': current_ride_details[5],       # Data
            'details': current_ride_details[6],    # Dettagli
            'ride_type': current_ride_details[7],  # Tipo di annuncio
            'vehicle': current_ride_details[8],    # Veicolo
            'price': current_ride_details[9],      # Prezzo
            'luggage': current_ride_details[10],   # Bagaglio
            'seats': current_ride_details[11],     # Posti
        }
        keyboard = create_keyboard_with_home()
        try:
            await update_ride(ride_id, updates)
            await callback_query.message.reply("Modifiche salvate con successo nel database.", reply_markup=keyboard)
        except Exception as e:
            await callback_query.message.reply(f"Errore durante il salvataggio delle modifiche: {e}")
    else:
        await callback_query.message.reply("Nessuna modifica da salvare.")

    await state.finish()  # Termina lo stato attuale


# Gestore per il pulsante "Elimina"
@dp.callback_query_handler(lambda c: c.data.startswith('delete_'), state=ShowRide.waiting_for_ride_action)
async def handle_delete_button(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    ride_id = callback_query.data.split('_')[1]
    await state.update_data(ride_id=ride_id)

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("🗑 Elimina", callback_data=f'confirm_delete_{ride_id}'),
                 InlineKeyboardButton("✖️ Annulla", callback_data='cancel_delete'))

    await callback_query.message.answer("Sei sicuro di voler eliminare questo annuncio?", reply_markup=keyboard)

# Gestore per la conferma di eliminazione
@dp.callback_query_handler(lambda c: c.data.startswith('confirm_delete_'), state=ShowRide.waiting_for_ride_action)
async def confirm_delete(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()

    user_data = await state.get_data()
    ride_id = user_data.get("ride_id")

    # Implementazione dell'eliminazione dell'annuncio
    await delete_ride(int(ride_id)) 
    keyboard = create_keyboard_with_home()
    await callback_query.message.answer("🗑 Annuncio eliminato con successo.", reply_markup=keyboard)
    # Nascondere la tastiera
    await callback_query.message.edit_reply_markup(reply_markup=None)

    await state.finish()

# Gestore per annullare l'eliminazione
@dp.callback_query_handler(lambda c: c.data == 'cancel_delete', state=ShowRide.waiting_for_ride_action)
async def cancel_delete(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.answer()
    keyboard = create_keyboard_with_home()
    await callback_query.message.answer("✖️ Eliminazione annullata.", reply_markup=keyboard)
    # Nascondere la tastiera
    await callback_query.message.edit_reply_markup(reply_markup=None)

    await state.finish()
