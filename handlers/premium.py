import asyncio
from aiogram.dispatcher import FSMContext
from states import AccountMenu
from aiogram.types.message import ContentTypes
from setup import dp, bot
from aiogram.types import CallbackQuery
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram import types  
import aiogram.utils.exceptions
from aiogram.utils.exceptions import MessageNotModified
import logging
from database import aggiorna_scadenza_utente
import os
from dotenv import load_dotenv

load_dotenv()

live_token = os.getenv("LIVE_TOKEN")
stripe_token = live_token


abbonamenti = {
    "tre": {
        "title": "⭐️ 3 Mesi - 5,99€",
        "playload": 90,
        "prices": [types.LabeledPrice(label='Abbonamento Premium (3 Mesi)', amount=599)]
    },
    "dodici": {
        "title": "🏅 12 Mesi - 19,99€",
        "playload": 365,
        "prices": [types.LabeledPrice(label='Abbonamento Premium (12 Mesi)', amount=1999)] 
    },
    "lifetime": {
        "title": "💎 Lifetime - 29,99€",
        "playload": 9999,
        "prices": [types.LabeledPrice(label='Abbonamento Premium (Lifetime)', amount=2999)]  
    }
}

@dp.callback_query_handler(lambda c: c.data == 'become_premium', state=AccountMenu.waiting_for_menu_action)
async def choose_premium_plan(callback_query: types.CallbackQuery, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup()


    # Aggiungi un pulsante per ogni opzione di abbonamento
    for plan, data in abbonamenti.items():
        button_text = data["title"]
        callback_data = f"premium:{plan}"
        keyboard.add(types.InlineKeyboardButton(text=button_text, callback_data=callback_data))
    
    back_button = types.InlineKeyboardButton(text="🔙 Indietro", callback_data="start")
    keyboard.add(back_button)

    testo = (
        "⭐️ <b>Premium:</b>\n"
        "<i>Diventando utente Premium con una piccola cifra, oltre a sostenere attivamente lo sviluppo del bot, ti sarà possibile:\n\n"
        "✅ Impostare avvisi di notifica.\n"
        "✅ Pubblicare annunci illimitati.\n"
        "🔜 Pubblicare annunci con priorità.\n"
        "🔜 Pubblicare annunci ricorrenti.\n"
        "🔜 Contattare in anticipo.\n"
        "🔜 Tutte le prossime novitá incluse.\n\n"
        "Scegli il periodo Premium da acquistare:</i>"
    )

    await callback_query.message.answer(testo, reply_markup=keyboard, parse_mode="HTML")

@dp.callback_query_handler(lambda c: c.data.startswith('premium:'), state=AccountMenu.waiting_for_menu_action)
async def become_premium(callback_query: types.CallbackQuery, state: FSMContext):
    chat_id = callback_query.message.chat.id
    plan = callback_query.data.split(':')[1]  # Estrai il piano di abbonamento scelto

    # Ottieni i dettagli del piano scelto
    selected_plan = abbonamenti.get(plan)
    
    await bot.send_invoice(chat_id, title=selected_plan["title"],
                           description="Accedi a funzionalità esclusive con l'abbonamento Premium. Pagamento sicuro con carta di credito tramite stripe.com ©.",
                           provider_token=stripe_token,
                           currency='eur',
                           prices=selected_plan["prices"],
                           start_parameter='become-premium',
                           payload=selected_plan["playload"])


@dp.pre_checkout_query_handler(lambda query: True, state=AccountMenu.waiting_for_menu_action)
async def checkout(pre_checkout_query: types.PreCheckoutQuery, state: FSMContext):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True,
                                        error_message="Ci dispiace, ma non siamo riusciti a processare il pagamento,"
                                                      "prova di nuovo tra qualche minuto, abbiamo bisogno di un piccolo riposo."
                                                      "Se il problema persiste, contattaci su @pendolari_assitenza_bot")


@dp.message_handler(content_types=ContentTypes.SUCCESSFUL_PAYMENT, state=AccountMenu.waiting_for_menu_action)
async def got_payment(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    abbonamento_payload = message.successful_payment.invoice_payload

    risultato_aggiornamento = await aggiorna_scadenza_utente(user_id, abbonamento_payload)
    keyboard = types.InlineKeyboardMarkup()
    home_button = types.InlineKeyboardButton(text="🏠 Home", callback_data="start")
    keyboard.add(home_button)

    if risultato_aggiornamento["success"]:
        new_expiration_date = risultato_aggiornamento["new_expiration"]
        if risultato_aggiornamento['message'] == 'extended':
            testo_messaggio = f"✅ Grazie! Abbiamo ricevuto il pagamento. Il tuo abbonamento Premium è stato prolungato fino al {new_expiration_date}.\n\nVai in Account per verificare il tuo nuovo stato Premium."
        elif risultato_aggiornamento['message'] == 'new':
            testo_messaggio = f"✅ Grazie! Sei ora un utente Premium! La tua scadenza è il {new_expiration_date}.\n\nVai in Account per verificare il tuo nuovo stato Premium."
        elif risultato_aggiornamento['message'] == 'lifetime':
            testo_messaggio = f"✅ Grazie mille! Hai ottenuto l'abbonamento Premium a vita!\n\nVai in Account per verificare il tuo nuovo stato Premium."
        else:
            testo_messaggio = f"✅ Grazie! Abbiamo ricevuto il pagamento.\n\nVai in Account per verificare il tuo nuovo stato Premium."
    else:
        testo_messaggio = f"❌ Si è verificato un errore: {risultato_aggiornamento['message']}"

    await state.finish()
    await bot.send_message(chat_id=message.chat.id, text=testo_messaggio, reply_markup=keyboard)

