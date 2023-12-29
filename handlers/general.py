from aiogram import types
from aiogram.dispatcher import FSMContext
from setup import dp, bot
from database import *
from states import ShowRide, ShowTicket, ManageAdmins, AccountMenu, ManagePremium, BroadcastMessage
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from . import post_ride, sell_ticket, search_ride, show_ride, show_ticket, show_search, premium
from utils import convert_date_format_for_list, convert_date_registration, is_valid_url
import datetime

async def send_welcome_message(chat_id):
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔍 Cerca", callback_data='search_ride'))
    keyboard.row(InlineKeyboardButton("🚗 Offri passaggio", callback_data='post_ride'),
                 InlineKeyboardButton("🎫 Cedi biglietto", callback_data='sell_ticket'))
    keyboard.row(InlineKeyboardButton("🗂 I tuoi annunci", callback_data='myrides'),
                InlineKeyboardButton("🔔 Avvisi attivi", callback_data='show_search'))
    keyboard.row(InlineKeyboardButton("👤 Account", callback_data='account'),
                InlineKeyboardButton("ℹ️ Info", callback_data='help'))
    
    welcome_text = (
        "🚘 Benvenuto su PendolariBOT! 🚉\n\n"
        "<b>Sei pronto a partire?</b> Scegli un'opzione e iniziamo!\n\nℹ️ Info per maggiori informazioni."
    )


    await bot.send_message(chat_id=chat_id, text=welcome_text, reply_markup=keyboard, parse_mode='HTML')

@dp.message_handler(commands=['start'], state='*')
async def send_welcome(message: types.Message, state: FSMContext):
    await state.finish()
    user_id = message.from_user.id
    username = message.from_user.username
    referral_user_id = None

    # Ottieni il testo del messaggio e separa il comando dagli argomenti
    command, *args = message.text.split(maxsplit=1)
    args = args[0] if args else None  # Imposta args su None se non ci sono argomenti

    # Gestisci il referral se presente
    if args:
        try:
            # Prova a convertire gli argomenti in un intero (ID dell'utente referente)
            referral_user_id = int(args)
        except ValueError:
            # Se gli argomenti non sono un numero intero, ignora il referral
            referral_user_id = None

    if username is None:
        # Invia un messaggio all'utente chiedendogli di impostare un username
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("✅ Ho impostato il mio username", callback_data='check_username'))
        await message.answer("Per utilizzare questo bot è necessario avere un username (@esempio).\nImposta un username nelle impostazioni del tuo account Telegram.", reply_markup=markup)
    else:
        if referral_user_id and await user_exists(referral_user_id):
                ok = await register_user(user_id, message.from_user.username, referral_user_id=referral_user_id, is_premium=True)
                if ok:
                    await update_referral_count(referral_user_id)
                    await message.answer(f"✅ Sei stato registrato come utente Premium per 30 giorni grazie ad un referral.")

                    # Invia una notifica all'utente che ha fornito il referral
                    referral_notification = f"🎉 @{message.from_user.username} si è iscritto tramite il tuo referral, hai ottenuto 10 giorni di abbonamento Premium!"
                    await bot.send_message(referral_user_id, referral_notification)
                else:
                    await message.answer("⚠️ Referral non valido in quanto risulti già registrato.")
        else:
            await register_user(user_id, message.from_user.username)

        await send_welcome_message(message.chat.id)
    

@dp.callback_query_handler(lambda c: c.data == 'start', state='*')
async def handle_start_button(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    username = callback_query.from_user.username

    # Aggiorna l'username nel database per prevenire eventuali discrepanze alla modifica
    await update_username(user_id, username)

    await state.finish()
    await send_welcome_message(callback_query.from_user.id)


# Elenco annunci dell'utente con pulsanti per le categorie
@dp.callback_query_handler(lambda c: c.data == 'myrides', state="*")
async def show_my_rides(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    user_rides = await get_user_rides(user_id)
    user_tickets = await get_user_tickets(user_id)
    # Aggiungi qui la chiamata per le ricerche se implementato

    # Conta il numero di annunci per ogni categoria
    count_rides = len(user_rides)
    count_tickets = len(user_tickets)
    # count_searches = len(user_searches) # Se implementato

    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(InlineKeyboardButton(f"🚗 Offri ({count_rides})", callback_data='show_offri'),
                 InlineKeyboardButton(f"🎫 Cedi ({count_tickets})", callback_data='show_cedi'))
                 # Aggiungi un pulsante per "Cerchi" se implementato
    keyboard.add(InlineKeyboardButton("🔙 Indietro", callback_data='start'))

    await callback_query.message.edit_text("Scegli la categoria di annunci da visualizzare:", reply_markup=keyboard)

# Funzione per mostrare gli annunci in base alla tipologia scelta
@dp.callback_query_handler(lambda c: c.data in ['show_offri', 'show_cedi'], state="*")
async def list_announcements_by_type(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    response = ""
    item_map = {}  # Mappa per associare l'indice visualizzato all'utente all'ID reale

    if callback_query.data == 'show_offri':
        user_rides = await get_user_rides(user_id)
        response += "🚗 Offri:\n"
        for i, ride in enumerate(user_rides, start=1):
            response += f"[{i}] {ride[1]} - {ride[3]} il {convert_date_format_for_list(ride[4])}\n"
            item_map[i] = ('ride', ride[0])
        await state.set_state(ShowRide.waiting_for_ride_id)
    elif callback_query.data == 'show_cedi':
        user_tickets = await get_user_tickets(user_id)
        response += "🎫 Cedi:\n"
        for i, ticket in enumerate(user_tickets, start=1):
            response += f"[{i}] {ticket[1]} - {ticket[3]} il {convert_date_format_for_list(ticket[5])}\n" 
            item_map[i] = ('ticket', ticket[0])
        await state.set_state(ShowTicket.waiting_for_ticket_id)

    # Salva la mappatura nello stato
    await state.update_data(item_map=item_map)

    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🔙 Indietro", callback_data='myrides'))
    await callback_query.message.edit_text(response, reply_markup=keyboard)


@dp.callback_query_handler(lambda c: c.data == 'help', state='*')
async def handle_help_button(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()

    help_text = (
        "<b>A cosa serve questo bot?</b>\n\n"
        "<i>Il bot ha la mission di connettere gratuitamente pendolari e fuorisede di tutta Italia nei loro innumerevoli viaggi.\n"
        "Tutti gli utenti possono eseguire ricerche <b>illimitate</b>, accordarsi liberamente in privato e pubblicare annunci.\n"
        "In particolare:</i>\n\n"
        "🔍 <b>Cerca</b>:<i> se non hai un'auto e cerchi un passaggio o un biglietto di seconda mano.</i>\n\n"
        "🚗 <b>Offri passaggio</b>: <i>se hai un'auto e vuoi condividerla con altri pendolari, pubblica un annuncio.</i>\n\n"
        "🎫 <b>Cedi biglietto</b>: <i>se hai un biglietto e non puoi più usarlo, pubblica un annuncio di cessione biglietto.</i>\n\n"
        "🗂 <b>I tuoi annunci</b>: <i>gestisci liberamente i tuoi annunci.</i>\n\n"
        "<i>Gli utenti standard possono eseguire ricerche illimitate, ma pubblicare massimo un annuncio per volta. Inoltre, non possono impostare notifiche personalizzate.</i>\n\n"

        "⭐️ <b>Premium:</b>\n"
        "<i>Diventando utenti Premium con una cifra simbolica sarà possibile:\n\n"
        "✅ Impostare avvisi di notifica.\n"
        "✅ Pubblicare annunci illimitati.\n"
        "🔜 Pubblicare annunci con priorità.\n"
        "🔜 Pubblicare annunci ricorrenti.\n"
        "🔜 Contattare in anticipo.\n"
        "🔜 Tutte le novitá future.</i>\n\n"

        "👥 <b>Referral:</b>\n"
        "<i>Ottieni 10 giorni di abbonamento premium per ogni amico invitato. Vai nella sezione account.</i>\n\n"
                
        "⚠️ <b>Responsabilità:</b>\n"
        "<i>Il bot fornisce una modo per connettere utenti e NON è responsabile per eventuali transazioni illecite, truffe, comportamenti violenti e qualsiasi tipo di reato che ne può derivare. Se hai dei comportamenti scorretti da segnalare, contattaci.</i>\n\n"

        "📥 <b>Supporto e Commercial:</b>\n"
        "<i>Se hai domande o hai bisogno di supporto e assistenza, non esitare a contattarci.</i>"
    )

    # Pulsante per contattare l'assistenza
    contact_button = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("📥 Contattaci", url="https://t.me/pendolari_assitenza_bot")],
        [InlineKeyboardButton("🔙 Indietro", callback_data='start')]
    ])


    await callback_query.message.answer(help_text, reply_markup=contact_button, parse_mode='HTML')



@dp.callback_query_handler(lambda c: c.data == 'check_username')
async def check_username(callback_query: types.CallbackQuery):
    await callback_query.answer()

    user_id = callback_query.from_user.id
    username = callback_query.from_user.username

    if not username:
        await callback_query.message.answer("Sembra che tu non abbia ancora impostato un username. Per favore, impostalo nelle impostazioni del tuo account Telegram.")
    else:
        await register_user(user_id, username)
        await send_welcome_message(callback_query.from_user.id)


@dp.callback_query_handler(lambda c: c.data == 'account', state='*')
async def account_settings(callback_query: types.CallbackQuery, state: FSMContext):
    await AccountMenu.waiting_for_menu_action.set()
    user_id = callback_query.from_user.id
    user_data = await get_user_data(user_id)

    if user_data:
        username = user_data['username']
        user_type = user_data['user_type']
        premium_expiration = convert_date_registration(user_data['premium_expiration']) or 'N/A'
        referral_link = f"https://t.me/pendolari_bot?start={user_id}"

        account_info = (
            f"🆔 ID: {user_id}\n"
            f"👤 Nome: @{user_data['username']}\n"
            f"🏅 Tipo Account: {user_type}\n"
            f"📅 Registrazione: {convert_date_registration(user_data['registered_at'])}\n"
            f"📅 Scadenza Premium: {premium_expiration}\n"
            f"👥 Referral: {user_data['referral_count']}\n\n"
            f"🔗 Referral Link:\n<code>{referral_link}</code>\n\n<i>Ottieni 10 giorni di Premium in omaggio per ogni utente che si iscrive utilizzando il tuo link!</i>"
        )

        keyboard = InlineKeyboardMarkup()
        if user_type == 'standard':
            keyboard.add(InlineKeyboardButton("⭐️ Diventa Premium", callback_data='become_premium'))
            keyboard.add(InlineKeyboardButton("📊 Statistiche", callback_data='metrics'))
            keyboard.add(InlineKeyboardButton("🔙 Indietro", callback_data='start'))
        elif user_type == 'premium':
            keyboard.add(InlineKeyboardButton("⭐️ Estendi Premium", callback_data='become_premium'))
            keyboard.add(InlineKeyboardButton("📊 Statistiche", callback_data='metrics'))
            keyboard.add(InlineKeyboardButton("🔙 Indietro", callback_data='start'))
        elif user_type == 'admin':
            keyboard.add(InlineKeyboardButton("📊 Statistiche", callback_data='metrics'))
            keyboard.add(InlineKeyboardButton("📣 Broadcast", callback_data='send_broadcast'))
            keyboard.add(InlineKeyboardButton("⭐️ Gestisci Premium", callback_data='show_premium'))
            keyboard.add(InlineKeyboardButton("⚙️ Impostazioni", callback_data='settings'))
            keyboard.add(InlineKeyboardButton("🔙 Indietro", callback_data='start'))
        elif user_type == 'founder':
            keyboard.add(InlineKeyboardButton("📊 Statistiche", callback_data='metrics'))
            keyboard.add(InlineKeyboardButton("📣 Broadcast", callback_data='send_broadcast'))
            keyboard.add(InlineKeyboardButton("👥 Gestisci Admins", callback_data='manage_admins'))
            keyboard.add(InlineKeyboardButton("⭐️ Gestisci Premium", callback_data='show_premium'))
            keyboard.add(InlineKeyboardButton("⚙️ Impostazioni", callback_data='settings'))
            keyboard.add(InlineKeyboardButton("🔙 Indietro", callback_data='start'))

        await callback_query.message.edit_text(
                text=account_info, 
                reply_markup=keyboard, 
                parse_mode='HTML'
            )
    else:
        await callback_query.message.edit_text(text="Non è stato possibile recuperare le informazioni del tuo account.")

    await callback_query.answer()  # È importante rispondere alla CallbackQuery

@dp.callback_query_handler(lambda c: c.data == 'settings', state=AccountMenu.waiting_for_menu_action)
async def become_premium(callback_query: types.CallbackQuery, state: FSMContext):
    # Implementa la logica per diventare un utente premium
    await callback_query.message.answer("Funzionalità 'Impostazioni' in fase di sviluppo.")


@dp.callback_query_handler(lambda c: c.data == 'manage_admins', state=AccountMenu.waiting_for_menu_action)
async def manage_admins(callback_query: types.CallbackQuery, state: FSMContext):
    await ManageAdmins.showing_admins.set()

    # Ottieni l'elenco degli amministratori dal database
    admins = await get_admins()

    # Costruisci e invia il messaggio con l'elenco degli amministratori
    response = "👑 Founder & Dev:\n"
    founder_listed = False
    for admin in admins:
        username, user_type = admin  # Destrutturazione della tupla
        if user_type == 'founder':
            response += f"-    @{username}\n"
            founder_listed = True
        elif founder_listed and user_type != 'founder':
            response += "👤 Admins:\n" + f"-    @{username}\n"
            founder_listed = False  # Per evitare di ripetere "Admins:" per ogni admin
        elif user_type != 'founder':
            response += f"@{username}\n"

    response += "\nInviando un @username presente nell'elenco, rimuoverai l'admin. Se non presente, renderai l'utente un admin."

    back_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Indietro", callback_data="account")]
        ]
    )
    await callback_query.message.reply(response, reply_markup=back_button)

    # Passa allo stato per processare la risposta dell'utente
    await ManageAdmins.processing_admin.set()

@dp.message_handler(state=ManageAdmins.processing_admin)
async def process_admin_action(message: types.Message, state: FSMContext):
    # Estrai il nome utente dalla risposta
    username = message.text.strip().lstrip('@')

    # Ottieni l'elenco degli amministratori attuali per verificare se l'username è già un admin
    current_admins = await get_admins()
    current_admin_usernames = [admin[0] for admin in current_admins]  # Estrai solo i nomi utente

    new_role = 'admin'
    if username in current_admin_usernames:
        # L'utente è già un admin, quindi sarà rimosso
        new_role = 'standard'

    # Aggiorna il ruolo dell'utente nel database
    user_updated = await update_user_role(username, new_role)
    
    back_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Indietro", callback_data="account")]
        ]
    )
    
    if user_updated:
        response = f"L'utente @{username} è ora un {new_role}."
        await message.reply(response, reply_markup=back_button)
        await state.finish()  # Chiude lo stato corrente se l'aggiornamento ha avuto successo
    else:
        response = f"Impossibile trovare o aggiornare l'utente @{username}. Assicurati che l'username sia di un utente del bot e riprova."
        await message.reply(response, reply_markup=back_button)
        # Non chiudere lo stato, permetti all'utente di riprovare

@dp.callback_query_handler(lambda c: c.data == 'show_premium', state='*')
async def showing_premium(callback_query: types.CallbackQuery, state: FSMContext):
    await ManagePremium.showing_premium.set()

    premium_users = await get_premium_users()

    response = "Utenti Premium:\n"
    for username, expiration in premium_users:
        expiration_text = expiration[:16] if expiration else "N/A"
        response += f"@{username} scadenza {expiration_text}\n"

    back_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Indietro", callback_data="account")]
        ]
    )
    response += f"\nInvia '@username' per rimuovere il premium. Invia '@username N' per aggiungere N giorni premium da oggi."
    await callback_query.message.reply(response, reply_markup=back_button)

    # Passa allo stato per processare la risposta dell'utente
    await ManagePremium.processing_premium.set()

@dp.message_handler(state=ManagePremium.processing_premium)
async def processing_premium(message: types.Message, state: FSMContext):
    parts = message.text.strip().split()
    username = parts[0].lstrip('@')

    if len(parts) == 2 and parts[1].isdigit():
        days = int(parts[1])
        user_updated = await update_premium_status(username, days)
        if user_updated:
            response = f"✅ {days} giorni premium da oggi all'utente @{username}."
        else:
            response = f"Impossibile aggiornare l'utente @{username}. Assicurati che esista e sia un utente standard."
    else:
        user_updated = await update_premium_status(username)
        if user_updated:
            response = f"✅ L'utente @{username} è ora standard."
        else:
            response = f"Impossibile aggiornare l'utente @{username}. Assicurati che esista e sia un utente premium."
    
    back_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Indietro", callback_data="account")]
        ]
    )
    await message.reply(response, reply_markup=back_button)
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'send_broadcast', state='*')
async def choose_broadcast_audience(callback_query: types.CallbackQuery, state: FSMContext):
    await BroadcastMessage.choosing_audience.set()
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("👥 Tutti gli Utenti", callback_data="broadcast_all")],
        [InlineKeyboardButton("⭐️ Solo Premium", callback_data="broadcast_premium")],
        [InlineKeyboardButton("👤 Solo Standard", callback_data="broadcast_standard")],
        [InlineKeyboardButton("🔙 Indietro", callback_data="account")]
    ])
    await callback_query.message.answer("Scegli a chi vuoi inviare il broadcast:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data in ["broadcast_all", "broadcast_premium", "broadcast_standard"], state=BroadcastMessage.choosing_audience)
async def set_broadcast_audience(callback_query: types.CallbackQuery, state: FSMContext):
    await state.update_data(audience=callback_query.data)
    await BroadcastMessage.waiting_for_message.set()
    await callback_query.message.answer("Invia ora il messaggio che vuoi trasmettere.")
 
@dp.message_handler(state=BroadcastMessage.waiting_for_message)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    # Salva il messaggio broadcast nello stato
    await state.update_data(broadcast_message=message.text)
    await BroadcastMessage.waiting_for_buttons.set()
    await message.answer("Invia i dettagli dei pulsanti nel formato: 'TestoPulsante, URL'. Separa i pulsanti con una nuova riga.")

# Handler per raccogliere i dettagli dei pulsanti
@dp.message_handler(state=BroadcastMessage.waiting_for_buttons)
async def process_broadcast_buttons(message: types.Message, state: FSMContext):
    buttons_info = message.text.strip().split('\n')
    buttons = []

    for info in buttons_info:
        if ',' in info:
            text, url = [x.strip() for x in info.split(',', 1)]
            if is_valid_url(url):
                buttons.append([InlineKeyboardButton(text=text, url=url)])
            else:
                await message.answer(f"URL non valido rilevato: {url}. Assicurati che sia nel formato corretto e riprova.")
                return  # Interrompe l'esecuzione e attende input valido

    # Se tutti gli URL sono validi, procedi
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)

    user_data = await state.get_data()
    broadcast_message = user_data.get("broadcast_message")

    # Salva i pulsanti nello stato
    await state.update_data(buttons=keyboard)

    # Mostra l'anteprima del messaggio e chiedi conferma
    confirm_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("✔️ Conferma", callback_data="confirm_broadcast")],
        [InlineKeyboardButton("❌ Annulla", callback_data="cancel_broadcast")]
    ])
    await message.answer(broadcast_message, reply_markup=keyboard)
    await message.answer("Confermi l'invio del messaggio?", reply_markup=confirm_keyboard)

    await BroadcastMessage.confirm_broadcast.set()

# Handler per inviare il broadcast dopo la conferma
@dp.callback_query_handler(lambda c: c.data == 'confirm_broadcast', state=BroadcastMessage.confirm_broadcast)
async def send_broadcast(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    audience = user_data.get("audience")
    broadcast_message = user_data.get("broadcast_message")
    buttons = user_data.get("buttons")

    # Invia il messaggio ai destinatari
    if audience == "broadcast_all":
        users = await get_all_users()
    elif audience == "broadcast_premium":
        users = await get_premium_users()
    elif audience == "broadcast_standard":
        users = await get_standard_users()

    for user_id in users:
        try:
            await dp.bot.send_message(user_id, broadcast_message, reply_markup=buttons)
            await asyncio.sleep(.05)
        except Exception as e:
            pass  # Gestisci eventuali errori

    back_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Indietro", callback_data="account")]
        ]
    )
    await callback_query.message.answer("Messaggio broadcast inviato correttamente.", reply_markup=back_button)
    await state.finish()

# Handler per annullare il broadcast
@dp.callback_query_handler(lambda c: c.data == 'cancel_broadcast', state=BroadcastMessage.confirm_broadcast)
async def cancel_broadcast(callback_query: types.CallbackQuery, state: FSMContext):
    back_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Indietro", callback_data="account")]
        ]
    )
    await callback_query.message.answer("Invio broadcast annullato.", reply_markup=back_button)
    await state.finish()

@dp.callback_query_handler(lambda c: c.data == 'metrics', state='*')
async def show_metrics(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    user_type = await get_user_type(user_id)  # Recupera il tipo di utente

    # Prepara le statistiche personali
    personal_stats = await get_personal_statistics(user_id)
    personal_stats_message = (
        "📊👤 Statistiche Personali:\n\n"
        f"- {personal_stats['searches']} ricerche effettuate\n"
        f"- {personal_stats['ads_published']} annunci pubblicati\n"
        f"- {personal_stats['ride_ads']} di tipo passaggio \n"
        f"- {personal_stats['ticket_ads']} di tipo biglietto\n"
    )

    response = personal_stats_message

    # Aggiungi statistiche globali se l'utente è admin o founder
    if user_type in ['admin', 'founder']:
        global_stats = await get_global_statistics()
        global_stats_message = (
            "\n📊🌐 Statistiche Globali:\n\n"
            f"- {global_stats['total_users']} utenti registrati\n"
            f"- {global_stats['total_premium']} utenti premium\n"
            f"- {global_stats['total_ads']} annunci totali\n"
            f"- {global_stats['total_search']} ricerche effettuate\n"
            f"- {global_stats['total_rides']} passaggi\n"
            f"- {global_stats['total_tickets']} biglietti\n"
            f"- {global_stats['total_notifications']} avvisi attivi\n"
        )
        response += global_stats_message
    
    back_button = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Indietro", callback_data="account")]
        ]
    )
    await callback_query.message.answer(response, reply_markup=back_button)
