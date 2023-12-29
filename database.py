import aiosqlite
from utils import convert_date_format
import json
from datetime import datetime
from datetime import timedelta
from aiogram import Bot
import logging

DB_FILE = 'database.db'

async def create_tables():
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS rides (
                                id INTEGER PRIMARY KEY,
                                user_id INTEGER,
                                departure TEXT,
                                stops TEXT,
                                arrival TEXT,
                                date TEXT,
                                details TEXT,
                                ride_type TEXT,
                                vehicle TEXT,
                                price REAL,
                                luggage TEXT,
                                seats INTEGER)''')

        await db.execute('''CREATE TABLE IF NOT EXISTS tickets (
                                id INTEGER PRIMARY KEY,
                                user_id INTEGER,
                                departure TEXT,
                                departure_time TEXT,
                                arrival TEXT,
                                arrival_time TEXT,
                                date TEXT,
                                price REAL,
                                train_type TEXT,
                                details TEXT)''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS search (
                                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                                        user_id INTEGER,
                                        departure TEXT,
                                        arrival TEXT,
                                        start_date TEXT,  
                                        end_date TEXT,  
                                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)''')
        
        await db.execute('''CREATE TABLE IF NOT EXISTS users (
                                user_id INTEGER PRIMARY KEY,
                                username TEXT,
                                registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                                user_type TEXT DEFAULT 'standard',
                                premium_expiration DATETIME,
                                referral_user INTEGER,
                                referral_count INTEGER DEFAULT 0,
                                FOREIGN KEY (referral_user) REFERENCES users(user_id)  )''')
                
        await db.execute('''CREATE TABLE IF NOT EXISTS personal (
                                user_id INTEGER PRIMARY KEY,
                                searches INTEGER DEFAULT 0,
                                ads_published INTEGER DEFAULT 0,
                                ride_ads INTEGER DEFAULT 0,
                                ticket_ads INTEGER DEFAULT 0,
                                FOREIGN KEY (user_id) REFERENCES users(user_id)  )''')
        
        await db.commit()

async def set_premium_expiration_to_yesterday():
    """Imposta la data di scadenza premium a ieri per gli utenti specificati."""
    yesterday = datetime.now() - timedelta(days=1)
    id = 5904550853 #utente ivarrson
    user_ids = [id]
    
    async with aiosqlite.connect(DB_FILE) as db:
        for user_id in user_ids:
            await db.execute("UPDATE users SET user_type = 'premium', premium_expiration = ? WHERE user_id = ?", (yesterday, user_id))
            print(f"Impostata scadenza premium a ieri per l'utente {user_id}.")
        
        await db.commit()

async def verify_and_update_subscriptions(bot: Bot):
    logging.info("Inizio verifica abbonamenti scaduti...")

    async with aiosqlite.connect(DB_FILE) as db:
        # Seleziona gli utenti con abbonamenti scaduti
        cursor = await db.execute("SELECT user_id FROM users WHERE user_type = 'premium' AND premium_expiration < ?", (datetime.now(),))
        users = await cursor.fetchall()

        if users:
            logging.info(f"Trovati {len(users)} utenti con abbonamenti premium scaduti.")

        # Aggiorna lo stato degli utenti
        for user_id in users:
            await db.execute("UPDATE users SET user_type = 'standard', premium_expiration = NULL WHERE user_id = ?", (user_id[0],))
            logging.info(f"Aggiornato stato utente {user_id[0]} a standard.")
            try:
                # Invia un messaggio all'utente per informarlo dell'aggiornamento
                await bot.send_message(user_id[0], "⭐️ Premium scaduto: il tuo account è stato aggiornato a standard.\n\nRinnova l'abbonamento nella sezione Account per continuare ad usare Premium.")
            except Exception as e:
                logging.error(f"Errore nell'invio del messaggio all'utente {user_id[0]}: {e}")

        await db.commit()

    logging.info("Verifica abbonamenti completata.")
    

async def save_ride(user_id, departure, stops, arrival, date, details, ride_type, vehicle, price, luggage, seats):
    date = convert_date_format(date)
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('INSERT INTO rides (user_id, departure, stops, arrival, date, details, ride_type, vehicle, price, luggage, seats) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                         (user_id, departure, stops, arrival, date, details, ride_type, vehicle, price, luggage, seats))
        await db.commit()
    await add_ride_ads(user_id)
    await add_ads_published(user_id)

async def update_ride(ride_id, updates):
    # Verifica se la data è tra gli aggiornamenti e convertila
    if 'date' in updates:
        updates['date'] = convert_date_format(updates['date'])

    set_clause = ', '.join([f"{key} = ?" for key in updates])
    values = list(updates.values()) + [ride_id]  # Includi solo i valori di 'updates' più ride_id

    sql = f'UPDATE rides SET {set_clause} WHERE id = ?'

    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(sql, values)
        await db.commit()

async def get_user_rides(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute('SELECT id, departure, stops, arrival, date, details, ride_type, vehicle, price, luggage, seats FROM rides WHERE user_id = ?', (user_id,))
        rows = await cursor.fetchall()
        return rows

async def get_ride_details(ride_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute('SELECT * FROM rides WHERE id = ?', (ride_id,))
        ride_details = await cursor.fetchone()
        return ride_details

async def delete_ride(ride_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM rides WHERE id = ?', (ride_id,))
        await db.commit()

async def save_ticket(user_id, departure, departure_time, arrival, arrival_time, date, price, train_type, details):
    date = convert_date_format(date)
    query = '''
    INSERT INTO tickets (user_id, departure, departure_time, arrival, arrival_time, date, price, train_type, details)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    '''
    async with aiosqlite.connect(DB_FILE) as db:  # Sostituisci con il percorso effettivo al tuo database
        await db.execute(query, (user_id, departure, departure_time, arrival, arrival_time, date, price, train_type, details))
        await db.commit()
    await add_ticket_ads(user_id)
    await add_ads_published(user_id)

async def update_ticket(ticket_id, updates):
    # Verifica se la data è tra gli aggiornamenti e convertila
    if 'date' in updates:
        updates['date'] = convert_date_format(updates['date'])

    set_clause = ', '.join([f"{key} = ?" for key in updates])
    values = list(updates.values()) + [ticket_id]  # Includi solo i valori di 'updates' più ticket_id

    sql = f'UPDATE tickets SET {set_clause} WHERE id = ?'

    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute(sql, values)
        await db.commit()


async def get_user_tickets(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute('SELECT id, departure, departure_time, arrival, arrival_time, date, price, train_type, details FROM tickets WHERE user_id = ?', (user_id,))
        rows = await cursor.fetchall()
        return rows

async def get_ticket_details(ticket_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute('SELECT * FROM tickets WHERE id = ?', (ticket_id,))
        ticket_details = await cursor.fetchone()
        return ticket_details

async def delete_ticket(ticket_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM tickets WHERE id = ?', (ticket_id,))
        await db.commit()


async def save_search(user_id, departure, arrival, date):
    # Controlla se la data è un intervallo o una data singola
    if '-' in date:
        # Intervallo di date
        start_date_str, end_date_str = date.split(' - ')
        start_date = convert_date_format(start_date_str.strip())
        end_date = convert_date_format(end_date_str.strip())
    else:
        # Data singola
        start_date = convert_date_format(date.strip())
        end_date = start_date  # La data di fine è uguale alla data di inizio

    async with aiosqlite.connect(DB_FILE) as db:
        # Controlla se esiste già un record con gli stessi dati
        cursor = await db.execute('SELECT * FROM search WHERE user_id = ? AND departure = ? AND arrival = ? AND start_date = ? AND end_date = ?',
                                (user_id, departure, arrival, start_date, end_date))
        result = await cursor.fetchone()
        
    if not result:   
        async with aiosqlite.connect(DB_FILE) as db:
            await db.execute('INSERT INTO search (user_id, departure, arrival, start_date, end_date) VALUES (?, ?, ?, ?, ?)',
                            (user_id, departure, arrival, start_date, end_date))
            await db.commit()
            return True  # Ritorna True se il record è stato inserito
    return False  # Ritorna False se il record esiste già


async def delete_search(search_id):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM search WHERE id = ?', (search_id,))
        await db.commit()

async def get_user_searches(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute('SELECT * FROM search WHERE user_id = ?', (user_id,))
        searches = await cursor.fetchall()
        return searches

async def get_search_details(search_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute('SELECT * FROM search WHERE id = ?', (search_id,))
        search_details = await cursor.fetchone()
        return search_details

async def search_rides_and_tickets(user_id, date, departure, arrival):
    async with aiosqlite.connect(DB_FILE) as db:
        stops_pattern_departure = f'%{departure}%'  # Ricerca per tappe intermedie con partenza
        stops_pattern_arrival = f'%{arrival}%'      # Ricerca per tappe intermedie con arrivo

        if '-' in date:  # Se la data è un intervallo
            start_date_str, end_date_str = date.split(' - ')
            start_date = convert_date_format(start_date_str)
            end_date = convert_date_format(end_date_str)
            rides_query = '''
                SELECT * FROM rides WHERE LOWER(date) BETWEEN LOWER(?) AND LOWER(?) AND 
                ((LOWER(departure) = LOWER(?) AND (LOWER(arrival) = LOWER(?) OR LOWER(stops) LIKE LOWER(?))) OR
                (LOWER(stops) LIKE LOWER(?) AND (LOWER(arrival) = LOWER(?) OR LOWER(stops) LIKE LOWER(?))) OR
                (LOWER(arrival) = LOWER(?) AND LOWER(stops) LIKE LOWER(?)))
            '''

            params = (start_date, end_date, departure, arrival, stops_pattern_arrival, stops_pattern_departure, arrival, stops_pattern_arrival, arrival, stops_pattern_departure)
        else:  # Se la data è esatta
            date_converted = convert_date_format(date)
            rides_query = '''
                SELECT * FROM rides WHERE LOWER(date) = LOWER(?) AND 
                ((LOWER(departure) = LOWER(?) AND (LOWER(arrival) = LOWER(?) OR LOWER(stops) LIKE LOWER(?))) OR
                (LOWER(stops) LIKE LOWER(?) AND (LOWER(arrival) = LOWER(?) OR LOWER(stops) LIKE LOWER(?))) OR
                (LOWER(arrival) = LOWER(?) AND LOWER(stops) LIKE LOWER(?)))
            '''

            params = (date_converted, departure, arrival, stops_pattern_arrival, stops_pattern_departure, arrival, stops_pattern_arrival, arrival, stops_pattern_departure)

        # Esegui la ricerca nella tabella rides
        cursor = await db.execute(rides_query, params)
        rides_results = await cursor.fetchall()
        
        if '-' in date:  # Se la data è un intervallo
            start_date_str, end_date_str = date.split(' - ')
            start_date = convert_date_format(start_date_str)
            end_date = convert_date_format(end_date_str)
            tickets_query = '''
                SELECT * FROM tickets WHERE LOWER(date) BETWEEN LOWER(?) AND LOWER(?) AND (LOWER(departure) = LOWER(?) OR LOWER(arrival) = LOWER(?))
            '''

            tickets_params = (start_date, end_date, departure, arrival)
        else:  # Se la data è esatta
            date_converted = convert_date_format(date)
            tickets_query = '''
                SELECT * FROM tickets WHERE LOWER(date) = LOWER(?) AND (LOWER(departure) = LOWER(?) OR LOWER(arrival) = LOWER(?))
            '''
            tickets_params = (date_converted, departure, arrival)

        # Esegui la ricerca nella tabella tickets
        cursor = await db.execute(tickets_query, tickets_params)
        tickets_results = await cursor.fetchall()

        # Converte i risultati in formato JSON
        rides_json = [
            {
                "id": r[0], "user_id": r[1], "departure": r[2], "stops": r[3], "arrival": r[4],
                "date": r[5], "details": r[6], "ride_type": r[7], "vehicle": r[8],
                "price": r[9], "luggage": r[10], "seats": r[11]
            }
            for r in rides_results
        ]

        tickets_json = [
            {
                "id": t[0], "user_id": t[1], "departure": t[2], "departure_time": t[3],
                "arrival": t[4], "arrival_time": t[5], "date": t[6], "price": t[7],
                "train_type": t[8], "details": t[9]
            }
            for t in tickets_results
        ]

        # Unisce i due tipi di risultati in un unico oggetto JSON
        combined_results = {
            "rides": rides_json,
            "tickets": tickets_json
        }
        await add_search(user_id)
        return json.dumps(combined_results)

async def find_matching_searches_for_ride(departure, stops, arrival, date):
    date = convert_date_format(date)
    stops_list = stops.lower().split(',') if stops else []

    async with aiosqlite.connect(DB_FILE) as db:
        # Preparazione della parte della query per le fermate intermedie
        stops_query_part = ' OR '.join(['(LOWER(departure) = ? OR LOWER(arrival) = ?)' for _ in stops_list])

        # Query per trovare corrispondenze per 'rides'
        query = f'''
            SELECT user_id FROM search WHERE 
            (start_date <= ? AND end_date >= ?) AND
            (LOWER(departure) = ? OR LOWER(arrival) = ? {(' OR ' + stops_query_part) if stops_query_part else ''})
        '''

        # Preparazione dei parametri, inclusi quelli per le fermate intermedie
        params = [date, date, departure.lower(), arrival.lower()] + [stop.strip() for stop in stops_list for _ in (0, 1)]

        cursor = await db.execute(query, params)
        search_results = await cursor.fetchall()

        unique_user_ids = {user_id[0] for user_id in search_results}
        return list(unique_user_ids)


async def find_matching_searches_for_ticket(departure, arrival, date):
    date = convert_date_format(date)

    async with aiosqlite.connect(DB_FILE) as db:
        # Query per trovare corrispondenze per 'tickets'
        query = '''
            SELECT user_id FROM search WHERE 
            (start_date <= ? AND end_date >= ?) AND
            (LOWER(departure) = ? AND LOWER(arrival) = ?)
        '''

        # Preparazione dei parametri
        params = [date, date, departure.lower(), arrival.lower()]

        cursor = await db.execute(query, params)
        search_results = await cursor.fetchall()

        unique_user_ids = {user_id[0] for user_id in search_results}
        return list(unique_user_ids)

async def register_user(user_id, username, referral_user_id=None, is_premium=False):
    timestamp = datetime.now()
    user_type = 'standard'  # Imposta di default a 'standard'
    premium_expiration = None
    
    if user_id == 136529457:
        user_type = 'founder'

    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute('SELECT * FROM users WHERE user_id = ?', (user_id,))
        user = await cursor.fetchone()

        if user:
            # L'utente esiste già, quindi non aggiorniamo lo stato premium e restituiamo False
            await db.execute('UPDATE users SET username = ?, registered_at = ? WHERE user_id = ?', 
                             (username, timestamp, user_id))
            await db.commit()
            return False
        else:
            # Nuova registrazione: controlla se deve essere premium
            if is_premium:
                premium_expiration = datetime.now() + timedelta(days=30)
                user_type = 'premium'

            # Inserisce un nuovo utente in users
            await db.execute('INSERT INTO users (user_id, username, registered_at, user_type, premium_expiration, referral_user) VALUES (?, ?, ?, ?, ?, ?)', 
                             (user_id, username, timestamp, user_type, premium_expiration, referral_user_id))

            # Inserisce una nuova riga in personal con statistiche iniziali a zero
            await db.execute('INSERT INTO personal (user_id, searches, ads_published, ride_ads, ticket_ads) VALUES (?, 0, 0, 0, 0)', 
                             (user_id,))

            await db.commit()
            return True


async def get_user_data(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute(
            'SELECT username, user_type, premium_expiration, registered_at, referral_user, referral_count FROM users WHERE user_id = ?',
            (user_id,))
        row = await cursor.fetchone()

        if row:
            # Converti la tupla in un dizionario
            keys = ["username", "user_type", "premium_expiration", "registered_at", "referral_user", "referral_count"]
            return dict(zip(keys, row))
        else:
            return None

async def user_exists(user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,))
        return await cursor.fetchone() is not None

async def update_referral_count(referral_user_id):
    async with aiosqlite.connect(DB_FILE) as db:
        # Recupera il tipo di utente e la data di scadenza del premium attuale
        cursor = await db.execute('SELECT user_type, premium_expiration FROM users WHERE user_id = ?', (referral_user_id,))
        user_info = await cursor.fetchone()

        if user_info:
            user_type, current_expiration = user_info

            # Se l'utente è admin o founder, non aggiornare la scadenza premium
            if user_type in ['admin', 'founder']:
                await db.execute('UPDATE users SET referral_count = referral_count + 1 WHERE user_id = ?', (referral_user_id,))
                await db.commit()
                return

            if current_expiration:
                # Converti la stringa in datetime e aggiungi giorni
                new_expiration = datetime.strptime(current_expiration, "%Y-%m-%d %H:%M:%S.%f") + timedelta(days=10)
            else:
                # Se premium_expiration è null, imposta una nuova data di scadenza partendo da oggi e aggiungi 10 giorni
                new_expiration = datetime.now() + timedelta(days=10)

            # Aggiorna il conteggio dei referral e la data di scadenza del premium
            await db.execute('UPDATE users SET referral_count = referral_count + 1, premium_expiration = ?, user_type = "premium" WHERE user_id = ?', (new_expiration.strftime("%Y-%m-%d %H:%M:%S.%f"), referral_user_id))
            await db.commit()

async def get_admins():
    """Ottieni l'elenco degli amministratori dal database in modo asincrono."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT username, user_type FROM users WHERE user_type IN ('admin', 'founder')")
        return await cursor.fetchall() 

async def update_user_role(username, new_role):
    """Aggiorna il ruolo dell'utente nel database e restituisce True se l'utente esiste, altrimenti False."""
    async with aiosqlite.connect(DB_FILE) as db:
        # Controlla se l'utente esiste
        cursor = await db.execute("SELECT 1 FROM users WHERE username = ?", (username,))
        user_exists = await cursor.fetchone() is not None

        if user_exists:
            # Aggiorna il ruolo dell'utente
            await db.execute("UPDATE users SET user_type = ? WHERE username = ?", (new_role, username))
            await db.commit()
            return True
        else:
            return False

async def get_premium_users_broadcast():
    """Restituisce gli ID degli utenti premium."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE user_type IN ('premium', 'founder', 'admin')")
        users = await cursor.fetchall()
        return [user[0] for user in users]

async def get_premium_users():
    """Restituisce una lista di utenti premium con username e data di scadenza."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT username, premium_expiration FROM users WHERE user_type IN ('premium', 'founder', 'admin')")
        return await cursor.fetchall()

async def update_premium_status(username, days=None):
    """Aggiorna lo status premium di un utente. Rimuovi premium se days è None, altrimenti aggiungi giorni."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = None
        if days is None:
            # Rimuovi premium
            cursor = await db.execute("UPDATE users SET user_type = 'standard', premium_expiration = NULL WHERE username = ?", (username,))
        else:
            # Aggiungi giorni premium
            current_time = datetime.now()
            new_expiration = current_time + timedelta(days=days)
            cursor = await db.execute("UPDATE users SET user_type = 'premium', premium_expiration = ? WHERE username = ?", (new_expiration, username,))

        await db.commit()
        return cursor.rowcount > 0  # Restituisce True se almeno una riga è stata modificata

async def get_all_users():
    """Restituisce tutti gli ID utente registrati nel bot."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT user_id FROM users")
        users = await cursor.fetchall()
        return [user[0] for user in users]

async def get_standard_users():
    """Restituisce gli ID degli utenti standard."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT user_id FROM users WHERE user_type = 'standard'")
        users = await cursor.fetchall()
        return [user[0] for user in users]


async def get_user_type(user_id):
    """Ottieni il tipo di un utente dal database."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT user_type FROM users WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        return result[0] if result else None

async def check_ads_limit(user_id):
    """Controlla se l'utente ha già pubblicato un annuncio (ride o ticket)."""
    async with aiosqlite.connect(DB_FILE) as db:
        # Controlla nella tabella degli annunci di ride
        cursor = await db.execute("SELECT 1 FROM rides WHERE user_id = ?", (user_id,))
        ride_exists = await cursor.fetchone() is not None

        # Controlla nella tabella degli annunci di ticket
        cursor = await db.execute("SELECT 1 FROM tickets WHERE user_id = ?", (user_id,))
        ticket_exists = await cursor.fetchone() is not None

        return ride_exists or ticket_exists

async def update_username(user_id, username):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE users SET username = ? WHERE user_id = ?", (username, user_id))
        await db.commit()

async def get_personal_statistics(user_id):
    """Ottieni le statistiche personali di un utente dal database."""
    async with aiosqlite.connect(DB_FILE) as db:
        cursor = await db.execute("SELECT searches, ads_published, ride_ads, ticket_ads FROM personal WHERE user_id = ?", (user_id,))
        result = await cursor.fetchone()
        if result:
            stats = {
                'searches': result[0],
                'ads_published': result[1],
                'ride_ads': result[2],
                'ticket_ads': result[3]
            }
            return stats
        else:
            # Restituisci valori di default se non ci sono dati
            return {'searches': 0, 'ads_published': 0, 'ride_ads': 0, 'ticket_ads': 0}

async def add_search(user_id):
    """Incrementa il numero di ricerche per un utente."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE personal SET searches = searches + 1 WHERE user_id = ?", (user_id,))
        await db.commit()
async def add_ads_published(user_id):
    """Incrementa il numero di annunci pubblicati per un utente."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE personal SET ads_published = ads_published + 1 WHERE user_id = ?", (user_id,))
        await db.commit()
async def add_ride_ads(user_id):
    """Incrementa il numero di annunci di passaggi per un utente."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE personal SET ride_ads = ride_ads + 1 WHERE user_id = ?", (user_id,))
        await db.commit()
async def add_ticket_ads(user_id):
    """Incrementa il numero di annunci di biglietti per un utente."""
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute("UPDATE personal SET ticket_ads = ticket_ads + 1 WHERE user_id = ?", (user_id,))
        await db.commit()

async def get_global_statistics():
    """Ottieni statistiche globali dal database."""
    async with aiosqlite.connect(DB_FILE) as db:
        # Ottieni il totale degli utenti
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]

        # Ottieni il totale degli utenti premium
        cursor = await db.execute("SELECT COUNT(*) FROM users WHERE user_type = 'premium'")
        total_premium = (await cursor.fetchone())[0]

        # Ottieni il totale dei passaggi
        cursor = await db.execute("SELECT COUNT(*) FROM rides")  
        total_rides = (await cursor.fetchone())[0]
        
        # Ottieni il totale dei biglietti
        cursor = await db.execute("SELECT COUNT(*) FROM tickets")  
        total_tickets = (await cursor.fetchone())[0]
        
        # Ottieni il totale degli annunci
        total_ads = total_rides + total_tickets
        
        # Ottieni il totale delle notifiche 
        cursor = await db.execute("SELECT COUNT(*) FROM search") 
        total_notifications = (await cursor.fetchone())[0]
        
        # Aggiungi qui: Ottieni il totale delle ricerche
        cursor = await db.execute("SELECT SUM(searches) FROM personal")
        total_search = (await cursor.fetchone())[0]

        return {
            'total_users': total_users,
            'total_premium': total_premium,
            'total_ads': total_ads,
            'total_rides': total_rides,
            'total_tickets': total_tickets,
            'total_notifications': total_notifications,
            'total_search': total_search
        }

async def aggiorna_scadenza_utente(user_id, days):
    async with aiosqlite.connect(DB_FILE) as db:
        try:
            days = int(days)
        except ValueError:
            # Gestisci il caso in cui days non sia convertibile in intero
            return {"success": False, "message": "Valore di giorni non valido"}

        # Controlla lo stato corrente dell'utente
        cursor = await db.execute("SELECT user_type, premium_expiration FROM users WHERE user_id = ?", (user_id,))
        user_data = await cursor.fetchone()

        if user_data is None:
            # L'utente non esiste nel database
            return {"success": False, "message": "Utente non trovato"}

        user_type, current_expiration = user_data

        # Se l'utente è admin o founder, non fare nulla
        if user_type in ['admin', 'founder']:
            return {"success": False, "message": "Nessuna azione richiesta per admin o founder"}

        # Controlla se i giorni sono 9999 per l'abbonamento a vita
        if days == 9999:
            new_expiration = datetime(2099, 12, 31)
            status_message = "lifetime"
        else:
            # Modifica la gestione del formato della data
            try:
                # Prova prima con il formato che include la frazione di secondo
                new_expiration = datetime.strptime(current_expiration, "%Y-%m-%d %H:%M:%S.%f") + timedelta(days=days)
            except (ValueError, TypeError):
                # Se fallisce, prova con il formato senza frazione di secondo
                try:
                    new_expiration = datetime.strptime(current_expiration, "%Y-%m-%d %H:%M:%S") + timedelta(days=days)
                except (ValueError, TypeError):
                    # Se anche questo fallisce, gestisci l'errore
                    return {"success": False, "message": "Formato data non valido"}
            status_message = "new" if user_type != 'premium' else "extended"

        # Aggiorna lo stato dell'utente e la data di scadenza
        await db.execute("UPDATE users SET user_type = 'premium', premium_expiration = ? WHERE user_id = ?", (new_expiration.strftime("%Y-%m-%d %H:%M:%S"), user_id))
        await db.commit()

        return {"success": True, "message": status_message, "new_expiration": new_expiration.strftime("%d/%m/%Y")}