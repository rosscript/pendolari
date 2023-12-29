from aiogram.dispatcher import FSMContext
from states import ShowSearch
from setup import dp
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import types  
import logging
from database import get_search_details, delete_search, get_user_searches
from utils import valida_campo_ticket, convert_date_format_for_list

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@dp.callback_query_handler(lambda c: c.data == 'show_search', state="*")
async def list_active_notifications(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user_searches = await get_user_searches(user_id)
    item_map = {}
    response = "🔔 Avvisi attivi:\n"
    
    if user_searches:
        for i, search in enumerate(user_searches, start=1):
            departure = search[2]
            arrival = search[3]
            start_date = search[4]
            end_date = search[5]

            if start_date == end_date:
                date_str = f"il {convert_date_format_for_list(start_date)}"
            else:
                date_str = f"il {convert_date_format_for_list(start_date)} - {convert_date_format_for_list(end_date)}"

            response += f"[{i}] {departure} - {arrival} {date_str}\n"
            item_map[i] = search[0]  # Assumi che l'ID dell'avviso sia il primo elemento
        response += "\nInvia il numero relativo per eliminare l'avviso di notifica."
    else:
        response += "Non ci sono avvisi attivi al momento.\n\nPer impostare un avviso di notifica, effettua una ricerca."

    await state.set_state(ShowSearch.waiting_for_search_id)
    await state.update_data(item_map=item_map)

    keyboard = create_keyboard()
    await callback_query.message.edit_text(response, reply_markup=keyboard)



@dp.message_handler(state=ShowSearch.waiting_for_search_id)
async def handle_search_deletion_request(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    item_map = user_data.get('item_map', {})

    try:
        selected_index = int(message.text)
        search_id = item_map.get(selected_index)

        if search_id:
            # Mostra la richiesta di conferma
            confirm_keyboard = InlineKeyboardMarkup(row_width=2)
            confirm_keyboard.add(
                InlineKeyboardButton("🗑 Elimina", callback_data=f'confirm_delete_search_{search_id}'),
                InlineKeyboardButton("✖️ Annulla", callback_data='cancel_delete')
            )
            await message.answer(f"Confermi di voler eliminare l'avviso?", reply_markup=confirm_keyboard)
            await ShowSearch.waiting_for_search_confirmation.set()
        else:
            await message.answer("Numero non valido. Riprova.")
    except ValueError:
        await message.answer("Per favore, invia un numero valido.")

@dp.callback_query_handler(lambda c: c.data.startswith('confirm_delete_search_'), state=ShowSearch.waiting_for_search_confirmation)
async def confirm_delete_search(callback_query: types.CallbackQuery, state: FSMContext):
    search_id = int(callback_query.data.split('_')[-1])
    await delete_search(search_id)  # Assumi che questa funzione elimini l'avviso dal database

    # Crea una keyboard con il pulsante "Home"
    home_keyboard = InlineKeyboardMarkup()
    home_keyboard.add(InlineKeyboardButton("🏠 Home", callback_data='start'))

    await callback_query.message.answer("Avviso eliminato con successo.", reply_markup=home_keyboard)
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await ShowSearch.waiting_for_search_id.set()


@dp.callback_query_handler(lambda c: c.data == 'cancel_delete', state=ShowSearch.waiting_for_search_confirmation)
async def cancel_delete_search(callback_query: types.CallbackQuery, state: FSMContext):
    # Crea una keyboard con il pulsante "Home"
    home_keyboard = InlineKeyboardMarkup()
    home_keyboard.add(InlineKeyboardButton("🏠 Home", callback_data='start'))

    await callback_query.message.answer("Eliminazione annullata.", reply_markup=home_keyboard)
    await callback_query.message.edit_reply_markup(reply_markup=None)
    await ShowSearch.waiting_for_search_id.set()


# Funzione ausiliaria per creare la keyboard inline
def create_keyboard():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("🔙 Indietro", callback_data='start'))
    return keyboard
