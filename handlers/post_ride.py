from aiogram.dispatcher import FSMContext
from states import PostRide
from setup import dp, bot
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import types  
import aiogram.utils.exceptions
from aiogram.utils.exceptions import MessageNotModified
import logging
from database import save_ride, find_matching_searches_for_ride, check_ads_limit, get_user_type
from utils import valida_data, valida_nome_citta, valida_prezzo, valida_modello_veicolo, valida_dimensione_bagaglio, valida_numero_posti

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Funzione ausiliaria per aggiornare l'annuncio
async def update_ride_announcement(message, state: FSMContext):
    async with state.proxy() as data:
        annuncio = (
            f"Nuovo annuncio: compila la bozza inviando un campo per volta.\n\n"
            f"📢 Offro passaggio 📢\n\n"
            f"📆 Data: {data.get('date', '________')}\n"
            f"📍 Partenza: {data.get('departure', '________')}\n"
            f"🚩 Tappe: {data.get('stops', '________')}\n"
            f"🏁 Arrivo: {data.get('arrival', '________')}\n"
            f"💵 Prezzo: {data.get('price', '________')}€\n"
            f"🚗 Veicolo: {data.get('vehicle', '________')}\n"
            f"🧳 Bagaglio: {data.get('luggage', '________')}\n"
            f"💺 Posti: {data.get('seats', '________')}\n"
            f"🔍 Dettagli: {data.get('details', '________')}"
        )
        markup = get_cancel_markup()
        # Controlla se il messaggio è già stato inviato e se è necessario modificarlo
        if 'message_id' in data:
            try:
                await bot.edit_message_text(annuncio, chat_id=message.chat.id, message_id=data['message_id'], reply_markup=markup)
            except aiogram.utils.exceptions.MessageNotModified:
                pass  # Ignora l'errore se il messaggio non è modificato
        else:
            sent_msg = await message.reply(annuncio, reply_markup=markup)
            data['message_id'] = sent_msg.message_id

# Generazione pulsante Annulla
def get_cancel_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔙 Annulla", callback_data='cancel'))
    return markup

# Generazione dei pulsanti inline Pubblica e Annulla
def get_publish_cancel_markup():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("✅ Pubblica", callback_data='publish'),
               InlineKeyboardButton("🔙 Annulla", callback_data='cancel'))
    return markup

@dp.callback_query_handler(lambda c: c.data == 'post_ride', state='*')
async def process_post_ride_start(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_type = await get_user_type(user_id)  # Ottieni il tipo di utente
    already_posted = await check_ads_limit(user_id)  # Controlla se ha già pubblicato un annuncio

    if user_type != 'premium' and user_type != 'admin' and user_type != 'founder':
        if already_posted:
            # Informa l'utente standard che non può pubblicare un altro annuncio
            account_keyboard = InlineKeyboardMarkup()
            account_keyboard.add(InlineKeyboardButton("👤 Account", callback_data='account'))
            await callback_query.message.answer("⭐️ Funzionalità Premium: hai già un annuncio attivo.\n\nElimina l'annuncio o sottoscrivi un abbonamento Premium nella sezione Account.", reply_markup=account_keyboard)
            return

    # Procedi normalmente se l'utente è premium o non ha annunci attivi
    state = dp.current_state(chat=callback_query.message.chat.id, user=user_id)
    await state.set_state(PostRide.waiting_for_date)  # Imposta lo stato iniziale
    await update_ride_announcement(callback_query.message, state)
    instruction_message = await callback_query.message.answer("📆 Inserisci la data del viaggio nel formato DD/MM/AAAA:")
    async with state.proxy() as data:
        data['instruction_message_id'] = instruction_message.message_id


# Handler per la data
@dp.message_handler(state=PostRide.waiting_for_date)
async def process_date(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    data_formattata, errore = valida_data(message.text)

    if errore:
        error_text = f"📆 Inserisci la data del viaggio nel formato DD/MM/AAAA:\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['date'] = data_formattata
        await bot.edit_message_text("📍 Inserisci la città di partenza:", chat_id=message.chat.id, message_id=instruction_message_id)

    await PostRide.next()
    await update_ride_announcement(message, state)

# Handler per la partenza
@dp.message_handler(state=PostRide.waiting_for_departure)
async def process_departure(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    nome_citta_validato, errore = valida_nome_citta(message.text)

    if errore:
        error_text = f"📍 Inserisci la città di partenza:\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['departure'] = nome_citta_validato
        await bot.edit_message_text("🚩 Inserisci tappe intermedie separate da virgola (Es. 'Bari, Brindisi')\nDigita 'no' per non inserirle:", chat_id=message.chat.id, message_id=instruction_message_id)

    await PostRide.next()
    await update_ride_announcement(message, state)

@dp.message_handler(state=PostRide.waiting_for_stops)
async def process_departure(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')
    input_text = message.text.strip().lower()  # Normalizza l'input

    # Controllo per "no" come input
    if input_text == 'no' or input_text == 'No' or input_text == 'nessuna' or input_text == 'Nessuna':
        tappe = 'Nessuna'
    else:
        tappe = [tappa.strip() for tappa in input_text.split(',')]
        for tappa in tappe:
            nome_tappa_validato, errore = valida_nome_citta(tappa)
            if errore:
                error_text = ("🚩 Inserisci la partenza e eventuali tappe intermedie separate da virgola (Es. 'Torino', 'Torino, Milano'):\n\n"
                            f"❌ {errore} Riprova.")
                await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
                return
        tappe = ', '.join(tappe)  # Riunisci le tappe in una stringa

    async with state.proxy() as data:
        data['stops'] = tappe
        await bot.edit_message_text("🏁 Inserisci la città di arrivo:", chat_id=message.chat.id, message_id=instruction_message_id)

    await PostRide.next()
    await update_ride_announcement(message, state)

    
@dp.message_handler(state=PostRide.waiting_for_arrival)
async def process_arrival(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')
    nome_citta_validato, errore = valida_nome_citta(message.text)

    if errore:
        error_text = f"🏁 Inserisci la città di arrivo:\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['arrival'] = nome_citta_validato
        await bot.edit_message_text("💵 Inserisci il prezzo del passaggio (Es. '35'):", chat_id=message.chat.id, message_id=instruction_message_id)

    await PostRide.next() 
    await update_ride_announcement(message, state)


# Handler per il prezzo
@dp.message_handler(state=PostRide.waiting_for_price)
async def process_price(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    prezzo_validato, errore = valida_prezzo(message.text)
    if errore:
        error_text = f"💵 Inserisci il prezzo del passaggio (Es. '35'):\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['price'] = prezzo_validato
        await bot.edit_message_text("🚗 Inserisci il modello del mezzo (Es. 'Audi A3'):", chat_id=message.chat.id, message_id=instruction_message_id)

    await PostRide.next()
    await update_ride_announcement(message, state)


# Handler per il veicolo
@dp.message_handler(state=PostRide.waiting_for_vehicle)
async def process_vehicle(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    modello_validato, errore = valida_modello_veicolo(message.text)
    if errore:
        error_text = f"🚗 Inserisci il modello del mezzo (Es. 'Audi A3'):\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['vehicle'] = modello_validato
        await bot.edit_message_text("🧳 Inserisci le dimensioni del bagaglio (Piccolo | Medio | Grande):", chat_id=message.chat.id, message_id=instruction_message_id)

    await PostRide.next() 
    await update_ride_announcement(message, state)


# Handler per il bagaglio
@dp.message_handler(state=PostRide.waiting_for_luggage)
async def process_luggage(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    dimensione_validata, errore = valida_dimensione_bagaglio(message.text)
    if errore:
        error_text = f"🧳 Inserisci le dimensioni del bagaglio (Piccolo | Medio | Grande):\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['luggage'] = dimensione_validata
        await bot.edit_message_text("💺 Inserisci i posti disponibili (da 1 a 6):", chat_id=message.chat.id, message_id=instruction_message_id)

    await PostRide.next()
    await update_ride_announcement(message, state)


# Handler per i posti
@dp.message_handler(state=PostRide.waiting_for_seats)
async def process_seats(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    posti_validati, errore = valida_numero_posti(message.text)
    if errore:
        error_text = f"💺 Inserisci i posti disponibili (da 1 a 6):\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['seats'] = posti_validati
        await bot.edit_message_text("🔍 Inserisci eventuali dettagli (digita 'no' per non inserirli):", chat_id=message.chat.id, message_id=instruction_message_id)

    await PostRide.next()
    await update_ride_announcement(message, state)


# Handler per i dettagli e pubblicazione dell'annuncio
@dp.message_handler(state=PostRide.waiting_for_details)
async def process_details(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        # Imposta i dettagli a una stringa vuota se l'utente risponde "no", altrimenti usa il testo del messaggio
        data['details'] = 'Nessun dettaglio aggiuntivo' if message.text.strip().lower() == 'no' else message.text

        # Preparazione dell'annuncio completo
        annuncio_completo = (
            f"📢 Offro passaggio 📢\n\n"
            f"📆 Data: {data['date']}\n"
            f"📍 Partenza: {data['departure']}\n"
            f"🚩 Tappe: {data['stops']}\n"
            f"🏁 Arrivo: {data['arrival']}\n"
            f"💵 Prezzo: {data['price']}€\n"
            f"🚗 Veicolo: {data['vehicle']}\n"
            f"🧳 Bagaglio: {data['luggage']}\n"
            f"💺 Posti: {data['seats']}\n"
            f"🔍 Dettagli: {data['details']}"
        )
        markup = get_publish_cancel_markup()

        # Invio dell'annuncio completo e salvataggio del message_id
        sent_annuncio_message = await message.answer(annuncio_completo, reply_markup=markup)
        data['annuncio_message_id'] = sent_annuncio_message.message_id

        # Invio del messaggio di istruzioni e salvataggio del message_id
        instruction_message = await bot.send_message(chat_id=message.chat.id, text="Annuncio completo. Pubblica l'annuncio e attendi che qualcuno si unisca al tuo viaggio!")
        data['instruction_message_id'] = instruction_message.message_id

        
    await PostRide.next()
    await update_ride_announcement(message, state)

# Handler per la pubblicazione dell'annuncio
@dp.callback_query_handler(lambda c: c.data == 'publish', state=PostRide.all_states)
async def publish_ride(callback_query: CallbackQuery, state: FSMContext):
    # Recupera i dati dallo stato
    data = await state.get_data()
    user_id = callback_query.from_user.id
    departure = data['departure']
    stops = data['stops']
    arrival = data['arrival']
    date = data['date']
    details = data['details']
    ride_type = 'offro'
    vehicle = data['vehicle']
    price = data['price']
    luggage = data['luggage']
    seats = data['seats']

    # Salva i dati nel database
    await save_ride(user_id, departure, stops, arrival, date, details, ride_type, vehicle, price, luggage, seats)

    # Preparazione dei nuovi pulsanti inline
    new_markup = InlineKeyboardMarkup()
    new_markup.add(InlineKeyboardButton("🏠 Home", callback_data='start'),
                   InlineKeyboardButton("🗂 I tuoi annunci", callback_data='myrides'))

    # Recupera i message_id dallo stato
    data = await state.get_data()
    annuncio_message_id = data['annuncio_message_id']
    instruction_message_id = data['instruction_message_id']

    # Modifica il messaggio di istruzioni
    await bot.edit_message_text(chat_id=callback_query.from_user.id,
                                message_id=instruction_message_id,
                                text="Annuncio pubblicato! Abbiamo anche notificato i potenziali interessati in base alle loro preferenze.\n\nEcco i prossimi passi:",
                                reply_markup=new_markup)

    # Rimuovi la keyboard inline dal messaggio di annuncio
    await bot.edit_message_reply_markup(chat_id=callback_query.from_user.id,
                                        message_id=annuncio_message_id,
                                        reply_markup=None)


    # PARTE NOTIFICHE AGLI UTENTI
    matching_user_ids = await find_matching_searches_for_ride(departure, stops, arrival, date)
    print(f"Utenti da notificare: {matching_user_ids}")
    

    # Controlla se ci sono utenti da notificare
    if matching_user_ids:
        # Formatta il messaggio dell'annuncio
        announcement_message = (
            f"📢 Offro passaggio 📢\n\n"
            f"📆 Data: {date}\n"
            f"📍 Partenza: {departure}\n"
            f"🚩 Tappe: {stops}\n"
            f"🏁 Arrivo: {arrival}\n"
            f"💵 Prezzo: €{price}\n"
            f"🚗 Veicolo: {vehicle}\n"
            f"🧳 Bagaglio: {luggage}\n" 
            f"💺 Posti: {seats}\n"
            f"🔍 Dettagli: {details}"
        )

        # Preparazione dei pulsanti "Richiedi" e "Home"
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(InlineKeyboardButton("✔️ Richiedi", callback_data=f"contact_author:{user_id}"))
        keyboard.add(InlineKeyboardButton("✖️ Ignora", callback_data='ignore_announcement'))

        # Invia il messaggio agli utenti corrispondenti
        for user_id in matching_user_ids:
            try:
                if user_id != callback_query.from_user.id:
                    await bot.send_message(user_id, "🔔 Un annuncio appena pubblicato potrebbe interessarti!")
                    await bot.send_message(user_id, announcement_message, reply_markup=keyboard)
            except Exception as e:
                print(f"Errore nell'invio della notifica all'utente {user_id}: {e}")


    await PostRide.waiting_for_finish.set()


# Funzione ausiliaria per creare la keyboard con il pulsante "Salva modifiche"
def create_keyboard_with_home():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("🗂 I tuoi annunci", callback_data='myrides'))
    keyboard.add(InlineKeyboardButton("🏠 Home", callback_data='start'))
    return keyboard

@dp.callback_query_handler(lambda c: c.data == 'cancel', state=PostRide.all_states)
async def cancel_ride(callback_query: CallbackQuery, state: FSMContext):
    keyboard = create_keyboard_with_home()
    await bot.send_message(callback_query.from_user.id, "Creazione annuncio annullata.", reply_markup=keyboard)
    await state.finish()

async def edit_message_safe(chat_id, message_id, text, reply_markup=None):
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
    except MessageNotModified:
        pass  # Ignora l'eccezione se il messaggio non è modificato
    

@dp.callback_query_handler(lambda c: c.data and c.data.startswith('contact_author:'), state="*")
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
        # Se l'utente interessato ha un username, crea un pulsante per contattarlo
        if user_username:
            contact_keyboard = InlineKeyboardMarkup()
            contact_keyboard.add(InlineKeyboardButton("✉️ Contatta l'Interessato", url=f"tg://user?id={callback_query.from_user.id}"))

            # Invia un messaggio all'autore con l'username dell'utente interessato e il pulsante di contatto
            await bot.send_message(author_user_id, f"📨 Ciao, {user_info} è interessato al tuo annuncio! Contattalo in privato per discuterne.", reply_markup=contact_keyboard)
        else:
            # Invia solo un messaggio all'autore se l'utente interessato non ha un username
            await bot.send_message(author_user_id, f"📨 Ciao, {user_info} è interessato al tuo annuncio! Contattalo in privato per discuterne.")

        # Invia una conferma all'utente che ha cliccato il pulsante
        await bot.send_message(chat_id=callback_query.from_user.id, text="✅ Richiesta inviata all'autore dell'annuncio. L'autore ti contatterà in privato se interessato.")
    except Exception as e:
        # Gestisce eventuali errori
        await bot.send_message(chat_id=callback_query.from_user.id, text="Non è stato possibile contattare l'autore dell'annuncio.")
        # Log dell'errore, se necessario
        print(f"Errore durante l'invio del messaggio all'autore: {e}")


        
@dp.callback_query_handler(lambda c: c.data == 'ignore_announcement', state="*")
async def handle_ignore_announcement(callback_query: types.CallbackQuery):
    try:
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    except Exception as e:
        # Gestisce eventuali errori, ad esempio se il messaggio non può essere eliminato
        print(f"Errore durante l'eliminazione del messaggio: {e}")