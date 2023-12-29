from aiogram import types
from aiogram.dispatcher import FSMContext
import asyncio, json, aiogram
from setup import dp, bot
from states import PostRide, SearchRide
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import MessageNotModified
from . import post_ride, search_ride, show_ride
from utils import valida_data, valida_nome_citta, valida_data_range, format_result
from database import search_rides_and_tickets, save_search, get_user_type
            
        

@dp.callback_query_handler(lambda c: c.data == 'search_ride', state='*')
async def process_search_ride_start(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(SearchRide.waiting_for_date_search)  # Assicurati che lo stato sia corretto

    # Invia il messaggio con la tastiera inline
    markup = get_date_choice_markup()
    instruction_message = await callback_query.message.answer("🔍 Nuova ricerca:\n\nVuoi cercare per un giorno preciso o in un periodo di tempo?", reply_markup=markup)
    async with state.proxy() as data:
        data['instruction_message_id'] = instruction_message.message_id

# Handler per la selezione della data esatta
@dp.callback_query_handler(lambda c: c.data == 'exact_date', state=SearchRide.waiting_for_date_search)
async def process_exact_date_selection(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("📆 Inserisci la data esatta nel formato DD/MM/AAAA:", reply_markup=None)
    await state.set_state(SearchRide.waiting_for_exact_date_input)

# Handler per la selezione del range di date
@dp.callback_query_handler(lambda c: c.data == 'date_range', state=SearchRide.waiting_for_date_search)
async def process_date_range_selection(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.edit_text("📅 Inserisci il periodo nel formato DD/MM/AAAA - DD/MM/AAAA:", reply_markup=None)
    await state.set_state(SearchRide.waiting_for_date_range_input)
    
# Handler per l'input della data esatta
@dp.message_handler(state=SearchRide.waiting_for_exact_date_input)
async def process_exact_date_input(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')
    
    data_formattata, errore = valida_data(message.text)
    
    if errore:
        error_text = f"📆 Inserisci la data del viaggio nel formato DD/MM/AAAA:\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return
    
    # Salva la data inserita dall'utente
    async with state.proxy() as data:
        data['date'] = message.text  # Ad esempio, salva la data esatta

    # Passa allo stato successivo
    await SearchRide.waiting_for_departure_search.set()
    # Invia il messaggio per il prossimo input (ad esempio, la partenza)
    await bot.edit_message_text("📍 Inserisci la città di partenza:", chat_id=message.chat.id, message_id=instruction_message_id)

# Handler per l'input del range di date
@dp.message_handler(state=SearchRide.waiting_for_date_range_input)
async def process_date_range_input(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')
    
    data_formattata, errore = valida_data_range(message.text)
    
    if errore:
        error_text = f"📆 Inserisci il periodo di date nel formato DD/MM/AAAA - DD/MM/AAAA:\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return
    
    # Salva il range di date inserito dall'utente
    async with state.proxy() as data:
        data['date'] = message.text  # Ad esempio, salva il range di date

    # Passa allo stato successivo
    await SearchRide.waiting_for_departure_search.set()
    # Invia il messaggio per il prossimo input (ad esempio, la partenza)
    await bot.edit_message_text("📍 Inserisci la città di partenza:", chat_id=message.chat.id, message_id=instruction_message_id)

# Handler per l'input della città di partenza
@dp.message_handler(state=SearchRide.waiting_for_departure_search)
async def process_departure_input(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')
    
    nome_citta_validato, errore = valida_nome_citta(message.text)

    if errore:
        error_text = f"📍 Inserisci la città di partenza:\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return
    
    # Salva la città di partenza inserita dall'utente
    async with state.proxy() as data:
        data['departure'] = message.text


    # Passa allo stato successivo per la città di arrivo
    await SearchRide.waiting_for_arrival_search.set()
    await bot.edit_message_text("🏁 Inserisci la città di arrivo:", chat_id=message.chat.id, message_id=instruction_message_id)

@dp.message_handler(state=SearchRide.waiting_for_arrival_search)
async def process_arrival_input(message: types.Message, state: FSMContext):
    user_data = await state.get_data()

    instruction_message_id = user_data.get('instruction_message_id')
    
    nome_citta_validato, errore = valida_nome_citta(message.text)
    if errore:
        error_text = f"🏁 Inserisci la città di arrivo:\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['arrival'] = message.text

        summary = f"🔍 Stai cercando..\n\n📅 Data: {data['date']}\n📍 Partenza: {data['departure']}\n🏁 Arrivo: {data['arrival']}\n"
        summary_message = await bot.send_message(chat_id=message.chat.id, text=summary)
        await bot.delete_message(chat_id=message.chat.id, message_id=instruction_message_id)

        clessidra_message = await bot.send_message(chat_id=message.chat.id, text="⏳")
        await asyncio.sleep(3)  # Simula l'attesa
        
        user_id = message.from_user.id
        search_results_json = await search_rides_and_tickets(user_id, data['date'], data['departure'], data['arrival'])

        search_results = json.loads(search_results_json)

        data['search_results'] = search_results
        await bot.delete_message(chat_id=message.chat.id, message_id=clessidra_message.message_id)

        if not search_results.get('rides') and not search_results.get('tickets'):
            await bot.delete_message(chat_id=message.chat.id, message_id=summary_message.message_id)
            await bot.send_message(
                chat_id=message.chat.id, 
                text="Nessun risultato trovato per la tua ricerca.\n\nVuoi essere notificato non appena un utente pubblica un passaggio con i parametri da te inseriti? Imposta una notifica!",
                reply_markup=get_notification_markup_home()
            )
        else:
            combined_results = search_results.get('rides', []) + search_results.get('tickets', [])
            num_results = len(combined_results)

            # Modifica il testo in base al numero di risultati
            if num_results == 1:
                summary_text = "🔍 1 Risultato trovato!"
            else:
                summary_text = f"🔍 {num_results} Risultati trovati! Scoprili navigando con le frecce."

            await bot.edit_message_text(chat_id=message.chat.id, message_id=summary_message.message_id, text=summary_text)

            # Mostra i risultati combinati
            if combined_results:
                first_result_message = await show_result(message, combined_results, 0, result_type=None)
                data['result_message_id'] = first_result_message.message_id if first_result_message else None

                
            # Invia un messaggio separato con il pulsante "Imposta Notifica"
            await bot.send_message(
                chat_id=message.chat.id, 
                text="Vuoi essere notificato per futuri passaggi simili? Imposta una notifica!",
                reply_markup=get_notification_markup()
            )
            
            await SearchRide.waiting_for_action.set()
            

async def show_result(message, combined_results, index, result_type=None, message_id=None):
    if index < len(combined_results):
        result = combined_results[index]
        result_message = format_result(result, result_type)
        navigation_markup = get_navigation_markup(index, len(combined_results), result_type)

        # Ottieni l'ID utente dell'autore dal risultato
        author_user_id = result.get('user_id')

        navigation_markup = get_navigation_markup(index, len(combined_results), result_type, author_user_id)
        if message_id:
            try:
                await bot.edit_message_text(chat_id=message.chat.id, message_id=message_id, text=result_message, reply_markup=navigation_markup)
            except MessageNotModified:
                pass  # Il messaggio non è stato modificato perché il testo è lo stesso
        else:
            sent_message = await bot.send_message(chat_id=message.chat.id, text=result_message, reply_markup=navigation_markup)
            return sent_message
    else:
        if message_id:
            await bot.edit_message_text(chat_id=message.chat.id, message_id=message_id, text="Nessun risultato trovato.")
        else:
            await bot.send_message(chat_id=message.chat.id, text="Nessun risultato trovato.")


def get_navigation_markup(current_index, max_index, result_type, author_user_id=None):
    markup = InlineKeyboardMarkup(row_width=3)

    # Pulsanti di navigazione
    if current_index > 0:
        markup.insert(InlineKeyboardButton("⬅️", callback_data=f"navigate:{current_index-1}:{result_type}"))
    else:
        markup.insert(InlineKeyboardButton("⬅️", callback_data=f"navigate:{max_index-1}:{result_type}"))
          
    current_position = f"{current_index + 1}/{max_index}"
    markup.insert(InlineKeyboardButton(current_position, callback_data="no_action"))
    
    if current_index < max_index - 1:
        markup.insert(InlineKeyboardButton("➡️", callback_data=f"navigate:{current_index+1}:{result_type}"))
    else:
        markup.insert(InlineKeyboardButton("➡️", callback_data=f"navigate:{0}:{result_type}"))

    # Pulsante per contattare l'autore
    if author_user_id:
        contact_button = InlineKeyboardButton("✔️ Richiedi", callback_data=f"contact_author:{author_user_id}")
        home_button = InlineKeyboardButton("🏠 Home", callback_data=f"start")
        markup.insert(contact_button)
        markup.insert(home_button)

    return markup


@dp.callback_query_handler(lambda c: c.data.startswith('navigate:'), state=SearchRide.all_states)
async def navigate_results(callback_query: types.CallbackQuery, state: FSMContext):
    _, index_str, result_type = callback_query.data.split(':')
    index = int(index_str)

    user_data = await state.get_data()
    if 'search_results' not in user_data:
        # Invia un messaggio di errore se non ci sono risultati salvati
        await bot.send_message(chat_id=callback_query.from_user.id, text="Errore: Nessun risultato di ricerca trovato.")
        return

    search_results = user_data['search_results']
    combined_results = search_results.get('rides', []) + search_results.get('tickets', [])

    # Calcola il nuovo indice e il tipo di risultato per la navigazione
    if result_type == 'rides' and index >= len(search_results.get('rides', [])):
        index = 0  # Riparti dall'inizio per 'tickets'
        result_type = 'tickets'
    elif result_type == 'tickets' and index >= len(search_results.get('tickets', [])):
        index = 0  # Riparti dall'inizio per 'rides'
        result_type = 'rides'

    # Ottieni l'ID del messaggio corrente per aggiornarlo
    message_id = callback_query.message.message_id

    # Mostra il risultato aggiornato
    await show_result(callback_query.message, combined_results, index, result_type, message_id=message_id)



@dp.callback_query_handler(lambda c: c.data and c.data.startswith('contact_author:'), state=SearchRide.all_states)
async def contact_author_callback(callback_query: types.CallbackQuery):
    # Estrai l'ID utente dell'autore dalla callback query
    author_user_id = callback_query.data.split(':')[1]
    
    # Verifica se l'utente che ha premuto il pulsante è lo stesso dell'autore dell'annuncio
    if str(callback_query.from_user.id) == author_user_id:
        await bot.answer_callback_query(callback_query.id, "Sei l'autore dell'annuncio.")
        return
    
    # Ottieni l'username dell'utente che ha premuto il pulsante
    user_username = callback_query.from_user.username
    if user_username is None:
        user_info = "un utente anonimo"
    else:
        user_info = f"@{user_username}"

    try:
        # Crea un pulsante per contattare direttamente l'utente interessato
        contact_keyboard = InlineKeyboardMarkup()
        contact_keyboard.add(InlineKeyboardButton("✉️ Contatta l'Interessato", url=f"tg://user?id={callback_query.from_user.id}"))

        # Invia un messaggio all'autore con l'username dell'utente interessato e il pulsante di contatto
        await bot.send_message(author_user_id, f"📨 Ciao, {user_info} è interessato al tuo annuncio! Contattalo in privato per discuterne.", reply_markup=contact_keyboard)

        # Crea un pulsante per contattare direttamente l'utente interessato
        home_keyboard = InlineKeyboardMarkup()
        home_keyboard.add(InlineKeyboardButton("🏠 Home", callback_data='start'))
        # Invia una conferma all'utente che ha cliccato il pulsante
        await bot.send_message(chat_id=callback_query.from_user.id, 
                            text="✅ Richiesta inviata all'autore dell'annuncio. L'autore ti contatterà in privato se interessato.", reply_markup=home_keyboard)
    except Exception as e:
        # Gestisce eventuali errori
        await bot.send_message(chat_id=callback_query.from_user.id, text="Non è stato possibile contattare l'autore dell'annuncio.")
        # Log dell'errore, se necessario
        print(f"Errore durante l'invio del messaggio all'autore: {e}")



@dp.callback_query_handler(lambda c: c.data == 'ignore_message_home', state=SearchRide.all_states)
async def handle_ignore_message_home(callback_query: types.CallbackQuery):
    try:
        # Modifica il messaggio esistente con i nuovi pulsanti
        await bot.edit_message_text(
            chat_id=callback_query.message.chat.id,
            message_id=callback_query.message.message_id,
            text="Nessun risultato trovato per la tua ricerca.",
            reply_markup=get_home_markup()
        )
    except Exception as e:
        print(f"Errore durante la modifica del messaggio: {e}")

@dp.callback_query_handler(lambda c: c.data == 'ignore_message', state=SearchRide.all_states)
async def handle_ignore_message(callback_query: types.CallbackQuery):
    try:
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    except Exception as e:
        # Gestisce eventuali errori, ad esempio se il messaggio non può essere eliminato
        print(f"Errore durante l'eliminazione del messaggio: {e}")
        
def get_home_markup():
    markup = InlineKeyboardMarkup()
    new_search_button = InlineKeyboardButton("🔍 Nuova Ricerca", callback_data="search_ride")
    home_button = InlineKeyboardButton("🏠 Home", callback_data="start")
    markup.add(new_search_button, home_button)
    return markup
       
# Generazione pulsante Annulla
def get_cancel_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Annulla", callback_data='cancel'))
    return markup

# Generazione dei pulsanti inline Pubblica e Annulla
def get_publish_cancel_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Pubblica", callback_data='publish_ticket'),
               InlineKeyboardButton("🔙 Annulla", callback_data='cancel'))
    return markup

# Funzione per creare la tastiera inline
def get_date_choice_markup():
    markup = InlineKeyboardMarkup(row_width=2)
    exact_date_button = InlineKeyboardButton("📆 Data Esatta", callback_data="exact_date")
    date_range_button = InlineKeyboardButton("📆 Periodo", callback_data="date_range")
    markup.add(exact_date_button, date_range_button)
    return markup

# Funzione ausiliaria per creare la keyboard con il pulsante "Salva modifiche"
def create_keyboard_with_home():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("🔍 Nuova ricera", callback_data='search_ride'))
    keyboard.add(InlineKeyboardButton("🏠 Home", callback_data='start'))
    return keyboard

@dp.callback_query_handler(lambda c: c.data == 'cancel', state=SearchRide.all_states)
async def cancel_ride(callback_query: types.CallbackQuery, state: FSMContext):
    keyboard = create_keyboard_with_home()
    await bot.send_message(callback_query.from_user.id, "Ricerca annullata.", reply_markup=keyboard)
    await state.finish()

async def edit_message_safe(chat_id, message_id, text, reply_markup=None):
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
    except MessageNotModified:
        pass  # Ignora l'eccezione se il messaggio non è modificato
    
def get_notification_markup_home():
    markup = InlineKeyboardMarkup()
    notification_button = InlineKeyboardButton("🔔 Avvisami", callback_data="set_notification")
    ignore_button = InlineKeyboardButton("❌ Ignora", callback_data="ignore_message_home")
    markup.add(notification_button, ignore_button)
    return markup

def get_notification_markup():
    markup = InlineKeyboardMarkup()
    notification_button = InlineKeyboardButton("🔔 Avvisami", callback_data="set_notification")
    ignore_button = InlineKeyboardButton("❌ Ignora", callback_data="ignore_message")
    markup.add(notification_button, ignore_button)
    return markup

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('set_notification'), state=SearchRide.all_states)
async def set_notification_handler(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user_type = await get_user_type(user_id)  # Ottieni il tipo di utente

    # Controlla se l'utente è premium
    if user_type != 'premium' and user_type != 'admin' and user_type != 'founder':
        # Mostra messaggio per gli utenti non premium
        account_keyboard = InlineKeyboardMarkup()
        account_keyboard.add(InlineKeyboardButton("👤 Account", callback_data='account'))
        account_keyboard.add(InlineKeyboardButton("🏠 Home", callback_data='start'))
        await bot.send_message(chat_id=user_id, text="⭐️ Funzionalità Premium: Vai nella sezione Account per sottoscrivere un abbonamento premium ed essere notificato ogni volta che un passaggio corrisponde ai tuoi criteri di ricerca!", reply_markup=account_keyboard)
        return
    
    # Recupera i dettagli della ricerca dallo stato
    user_data = await state.get_data()
    departure = user_data.get('departure')
    arrival = user_data.get('arrival')
    date = user_data.get('date')

    if not departure or not arrival or not date:
        await bot.send_message(chat_id=user_id, text="Mancano alcuni dettagli della ricerca. Riprova.")
        return

    try:
        # Salva la ricerca nel database
        is_inserted = await save_search(user_id, departure, arrival, date)
        
        # Crea una keyboard con il pulsante "Home"
        home_keyboard = InlineKeyboardMarkup()
        home_keyboard.add(InlineKeyboardButton("🏠 Home", callback_data='start'))
        try:
            await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
        except Exception as e:
            print(f"Errore durante l'eliminazione del messaggio: {e}")
        
        if is_inserted:
            # Agisci se il record è stato inserito (ad es., invia un messaggio di conferma)
            await bot.send_message(chat_id=callback_query.message.chat.id, text="🔔 Notifica impostata con successo!", reply_markup=home_keyboard)
        else:
            # Agisci se il record esiste già (ad es., invia un messaggio di avviso)
            await bot.send_message(chat_id=callback_query.message.chat.id, text="Avviso di notifica già impostato.", reply_markup=home_keyboard)
        
    except Exception as e:
        await bot.send_message(chat_id=user_id, text="Si è verificato un errore durante l'impostazione della notifica.")
        print(f"Errore durante il salvataggio della ricerca: {e}")
