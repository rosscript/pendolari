from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher import FSMContext
from setup import dp, bot
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
import aiogram.utils.exceptions
from aiogram.utils.exceptions import MessageNotModified
import logging
from aiogram import types 
from states import SellTicket
from database import save_ticket, find_matching_searches_for_ticket, get_user_type, check_ads_limit
from utils import valida_data, valida_nome_citta, valida_prezzo, valida_orario

logging.basicConfig(level=logging.INFO) 
logger = logging.getLogger(__name__)

# Funzione ausiliaria per aggiornare l'annuncio
async def update_ticket_announcement(message, state: FSMContext):
    async with state.proxy() as data:
        annuncio = (
            f"Nuovo annuncio: compila la bozza inviando un campo per volta.\n\n"
            f"🎫 Cedo biglietto 🎫\n\n"
            f"📅 Data: {data.get('date', '________')}\n"
            f"🚉 Partenza: {data.get('departure', '________')} alle {data.get('departure_time', '____')}\n"
            f"🚉 Arrivo: {data.get('arrival', '________')} alle {data.get('arrival_time', '____')}\n"
            f"💵 Prezzo: {data.get('price', '________')}€\n"
            f"🚄 Treno: {data.get('train_type', '________')}\n"
            f"🔍 Dettagli: {data.get('details', '________')}"
        )
        markup = get_cancel_markup()  # Assicurati di aver definito questa funzione o adattala secondo le tue esigenze

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
    markup.add(InlineKeyboardButton("✅ Pubblica", callback_data='publish_ticket'),
               InlineKeyboardButton("🔙 Annulla", callback_data='cancel'))
    return markup

# Handler per il pulsante Vendi un Biglietto
@dp.callback_query_handler(lambda c: c.data == 'sell_ticket', state='*')
async def process_sell_ticket_start(callback_query: types.CallbackQuery):
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
        
    state = dp.current_state(chat=callback_query.message.chat.id, user=callback_query.from_user.id)
    await state.set_state(SellTicket.waiting_for_date)  # Imposta lo stato iniziale per la vendita del biglietto
    await update_ticket_announcement(callback_query.message, state)
    instruction_message = await callback_query.message.answer("📆 Inserisci la data del viaggio nel formato DD/MM/AAAA:")
    async with state.proxy() as data:
        data['instruction_message_id'] = instruction_message.message_id


# Handler per la data (vendita biglietto)
@dp.message_handler(state=SellTicket.waiting_for_date)
async def process_date_ticket(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    data_formattata, errore = valida_data(message.text)

    if errore:
        error_text = f"📆 Inserisci la data del viaggio nel formato DD/MM/AAAA:\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['date'] = data_formattata
        # Modifica il messaggio successivo per chiedere la città di partenza
        await bot.edit_message_text("🚉 Inserisci la stazione di partenza:", chat_id=message.chat.id, message_id=instruction_message_id)

    await SellTicket.next()  # Passa al prossimo stato
    await update_ticket_announcement(message, state)


# Handler per la stazione di partenza (vendita biglietto)
@dp.message_handler(state=SellTicket.waiting_for_departure)
async def process_departure_ticket(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    nome_stazione_validato, errore = valida_nome_citta(message.text)  # Assumi che valida_nome_citta possa essere usata anche per le stazioni

    if errore:
        error_text = f"Inserisci la stazione di partenza:\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['departure'] = nome_stazione_validato
        await bot.edit_message_text("🕙 Inserisci l'orario di partenza (formato 24h, es: 15:30):", chat_id=message.chat.id, message_id=instruction_message_id)

    await SellTicket.next()  # Passa al prossimo stato, che potrebbe essere l'orario di partenza
    await update_ticket_announcement(message, state)


# Handler per l'orario di partenza (vendita biglietto)
@dp.message_handler(state=SellTicket.waiting_for_departure_time)
async def process_departure_time(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    orario_validato, errore = valida_orario(message.text)

    if errore:
        error_text = f"🕙 Inserisci l'orario di partenza (formato 24h, es: 15:30):\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['departure_time'] = orario_validato
        await bot.edit_message_text("🚉 Inserisci la stazione di arrivo:", chat_id=message.chat.id, message_id=instruction_message_id)

    await SellTicket.next()  # Passa al prossimo stato
    await update_ticket_announcement(message, state)

# Handler per la stazione di arrivo (vendita biglietto)
@dp.message_handler(state=SellTicket.waiting_for_arrival)
async def process_arrival_station(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    nome_stazione_validato, errore = valida_nome_citta(message.text)  # Usiamo la stessa validazione delle stazioni di partenza

    if errore:
        error_text = f"🚉 Inserisci la stazione di arrivo:\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['arrival'] = nome_stazione_validato
        await bot.edit_message_text("🕙 Inserisci l'orario di arrivo (formato 24h, es: 17:45):", chat_id=message.chat.id, message_id=instruction_message_id)

    await SellTicket.next()  # Passa al prossimo stato, che dovrebbe essere l'orario di arrivo
    await update_ticket_announcement(message, state)

# Handler per l'orario di arrivo (vendita biglietto)
@dp.message_handler(state=SellTicket.waiting_for_arrival_time)
async def process_arrival_time(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    orario_validato, errore = valida_orario(message.text)

    if errore:
        error_text = f"🕙 Inserisci l'orario di arrivo (formato 24h, es: 17:45):\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['arrival_time'] = orario_validato
        await bot.edit_message_text("💵 Inserisci il prezzo del biglietto:", chat_id=message.chat.id, message_id=instruction_message_id)

    await SellTicket.next()  # Passa al prossimo stato, che potrebbe essere l'inserimento del prezzo
    await update_ticket_announcement(message, state)

# Handler per il prezzo del biglietto
@dp.message_handler(state=SellTicket.waiting_for_price)
async def process_ticket_price(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    prezzo_validato, errore = valida_prezzo(message.text)
    if errore:
        error_text = f"💵 Inserisci il prezzo del biglietto (Es. '35'):\n\n❌ {errore}"
        await edit_message_safe(chat_id=message.chat.id, message_id=instruction_message_id, text=error_text)
        return

    async with state.proxy() as data:
        data['price'] = prezzo_validato
        await bot.edit_message_text("🚄 Inserisci il tipo di treno (Es. 'Frecciarossa'):", chat_id=message.chat.id, message_id=instruction_message_id)

    await SellTicket.next()  # Passa al prossimo stato, che potrebbe essere il tipo di treno
    await update_ticket_announcement(message, state)


# Handler per il tipo di treno
@dp.message_handler(state=SellTicket.waiting_for_train_type)
async def process_train_type(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    instruction_message_id = user_data.get('instruction_message_id')

    # Non c'è una validazione specifica, quindi accettiamo direttamente l'input
    train_type = message.text.strip()

    async with state.proxy() as data:
        data['train_type'] = train_type
        await bot.edit_message_text("🔍 Inserisci eventuali dettagli aggiuntivi o digita 'no' per ometterli:", chat_id=message.chat.id, message_id=instruction_message_id)

    await SellTicket.next()  # Passa al prossimo stato, che potrebbe essere l'inserimento di dettagli aggiuntivi
    await update_ticket_announcement(message, state)


# Handler per i dettagli del biglietto
@dp.message_handler(state=SellTicket.waiting_for_details)
async def process_ticket_details(message: types.Message, state: FSMContext):
    async with state.proxy() as data:
        # Imposta i dettagli a una stringa vuota se l'utente risponde "no", altrimenti usa il testo del messaggio
        data['details'] = 'Nessun dettaglio aggiuntivo' if message.text.strip().lower() == 'no' else message.text

        # Preparazione dell'annuncio completo
        annuncio_completo = (
            f"🎫 Cedo biglietto 🎫\n\n"
            f"📅 Data: {data['date']}\n"
            f"🚉 Partenza: {data['departure']} alle {data['departure_time']}\n"
            f"🚉 Arrivo: {data['arrival']} alle {data['arrival_time']}\n"
            f"💵 Prezzo: {data['price']}€\n"
            f"🚄 Treno: {data['train_type']}\n"
            f"🔍 Dettagli: {data['details']}"
        )
        markup = get_publish_cancel_markup()  # Assicurati che questa funzione sia definita

        # Invio dell'annuncio completo e salvataggio del message_id
        sent_annuncio_message = await message.answer(annuncio_completo, reply_markup=markup)
        data['annuncio_message_id'] = sent_annuncio_message.message_id

        # Invio del messaggio di istruzioni e salvataggio del message_id
        instruction_message = await bot.send_message(chat_id=message.chat.id, text="Annuncio completo. Pubblica l'annuncio e attendi che qualcuno acquisti il tuo biglietto!")
        data['instruction_message_id'] = instruction_message.message_id

    await SellTicket.next()  # Potrebbe essere la fine del flusso di stato o un passaggio successivo, se presente
    await update_ticket_announcement(message, state)


# Handler per la pubblicazione dell'annuncio di vendita del biglietto
@dp.callback_query_handler(lambda c: c.data == 'publish_ticket', state=SellTicket.all_states)
async def publish_ticket(callback_query: CallbackQuery, state: FSMContext):
    # Recupera i dati dallo stato
    data = await state.get_data()
    user_id = callback_query.from_user.id
    departure = data['departure']
    departure_time = data['departure_time']
    arrival = data['arrival']
    arrival_time = data['arrival_time']
    date = data['date']
    details = data['details']
    train_type = data['train_type']
    price = data['price']

    # Salva i dati del biglietto nel database
    await save_ticket(user_id, departure, departure_time, arrival, arrival_time, date, price, train_type, details)

    # Preparazione dei nuovi pulsanti inline
    new_markup = InlineKeyboardMarkup()
    new_markup.add(InlineKeyboardButton("🏠 Home", callback_data='start'),
                   InlineKeyboardButton("🗂 I tuoi annunci", callback_data='myrides'))

    # Recupera i message_id dallo stato
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
    
    # PARTE NOTIFICHE AGLI UTENTI PER I BIGLIETTI
    matching_user_ids = await find_matching_searches_for_ticket(departure, arrival, date)
    print(f"Utenti da notificare per il biglietto: {matching_user_ids}")

    # Controlla se ci sono utenti da notificare
    if matching_user_ids:
        # Formatta il messaggio dell'annuncio del biglietto
        ticket_announcement_message = (
            f"🎫 Cedo biglietto 🎫\n\n"
            f"📅 Data: {date}\n"
            f"🚉 Partenza: {departure} alle {departure_time}\n"
            f"🚉 Arrivo: {arrival} alle {arrival_time}\n"
            f"💵 Prezzo: €{price}\n"
            f"🚄 Treno: {train_type}\n"
            f"🔍 Dettagli: {details}"
        )

        # Preparazione dei pulsanti "Richiedi" e "Home"
        keyboard = InlineKeyboardMarkup(row_width=1)
        keyboard.add(InlineKeyboardButton("✔️ Richiedi", callback_data=f"contact_author_ticket:{user_id}"))
        keyboard.add(InlineKeyboardButton("✖️ Ignora", callback_data='ignore_announcement_ticket'))

        # Invia il messaggio agli utenti corrispondenti
        for user_id in matching_user_ids:
            try:
                if user_id != callback_query.from_user.id:
                    await bot.send_message(user_id, "🔔 Un annuncio di biglietto appena pubblicato potrebbe interessarti!")
                    await bot.send_message(user_id, ticket_announcement_message, reply_markup=keyboard)
            except Exception as e:
                print(f"Errore nell'invio della notifica all'utente {user_id} per il biglietto: {e}")

    await SellTicket.waiting_for_finish.set()  # Imposta lo stato finale 
    

# Funzione ausiliaria per creare la keyboard con il pulsante "Salva modifiche"
def create_keyboard_with_home():
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton("🗂 I tuoi annunci", callback_data='myrides'))
    keyboard.add(InlineKeyboardButton("🏠 Home", callback_data='start'))
    return keyboard

@dp.callback_query_handler(lambda c: c.data == 'cancel', state=SellTicket.all_states)
async def cancel_ride(callback_query: CallbackQuery, state: FSMContext):
    keyboard = create_keyboard_with_home()
    await bot.send_message(callback_query.from_user.id, "Creazione annuncio annullata.", reply_markup=keyboard)
    await state.finish()

async def edit_message_safe(chat_id, message_id, text, reply_markup=None):
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id, text=text, reply_markup=reply_markup)
    except MessageNotModified:
        pass  # Ignora l'eccezione se il messaggio non è modificato
    
@dp.callback_query_handler(lambda c: c.data and c.data.startswith('contact_author_ticket:'), state="*")
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
        
@dp.callback_query_handler(lambda c: c.data == 'ignore_announcement_ticket', state="*")
async def handle_ignore_announcement(callback_query: types.CallbackQuery):
    try:
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=callback_query.message.message_id)
    except Exception as e:
        # Gestisce eventuali errori, ad esempio se il messaggio non può essere eliminato
        print(f"Errore durante l'eliminazione del messaggio: {e}")