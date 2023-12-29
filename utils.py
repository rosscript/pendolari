from datetime import datetime
import re

def convert_date_format(date_str):
    """
    Converte una data dai formati DD/MM/YYYY, DD/MM/YY o YYYY-MM-DD al formato YYYY-MM-DD.

    Args:
    date_str (str): Data in uno dei formati DD/MM/YYYY, DD/MM/YY o YYYY-MM-DD.

    Returns:
    str: Data convertita in formato YYYY-MM-DD.
    """
    if date_str is None:
        return None

    # Prova a convertire dal formato 'DD/MM/YYYY'
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        pass  # Continua a controllare gli altri formati

    # Prova a convertire dal formato 'DD/MM/YY'
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%y')
        return date_obj.strftime('%Y-%m-%d')
    except ValueError:
        pass  # Continua a controllare gli altri formati

    # Prova a convertire dal formato 'YYYY-MM-DD' (se già in questo formato, restituiscilo così com'è)
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return date_str  # Già nel formato corretto
    except ValueError:
        print(f"Data non valida: {date_str}")
        return None

    
def valida_data(input_data):
    try:
        data_valida = datetime.strptime(input_data, '%d/%m/%Y')
        return data_valida.strftime('%d/%m/%Y'), None
    except ValueError:
        return None, "Data non valida. Inserisci la data nel formato DD/MM/AAAA"

def valida_data_range(input_data_range):
    try:
        # Verifica che il formato sia corretto con il trattino "-"
        if " - " not in input_data_range:
            return None, "Formato non valido."

        # Divide l'input in data di inizio e data di fine
        data_inizio_str, data_fine_str = input_data_range.split(" - ")
        data_inizio = datetime.strptime(data_inizio_str, '%d/%m/%Y')
        data_fine = datetime.strptime(data_fine_str, '%d/%m/%Y')

        # Verifica che la data di inizio non sia successiva alla data di fine
        if data_inizio > data_fine:
            return None, "La data di inizio deve essere precedente alla data di fine."

        return data_inizio.strftime('%d/%m/%Y') + " - " + data_fine.strftime('%d/%m/%Y'), None
    except ValueError:
        return None, "Formato non valido."
    except Exception as e:
        return None, str(e)
    
    
def valida_nome_citta(nome_citta):
    nome_citta = nome_citta.strip()
    if 2 <= len(nome_citta) <= 18:
        return nome_citta, None
    else:
        return None, "Nome di città non valido. Inserisci una città con lunghezza tra 2 e 18 caratteri"

def valida_prezzo(input_prezzo):
    try:
        prezzo = float(input_prezzo.strip().replace(",", "."))
        if prezzo < 0:
            return None, "Il prezzo non può essere negativo."
        return prezzo, None
    except ValueError:
        return None, "Prezzo non valido. Inserisci un valore numerico."

def valida_modello_veicolo(modello):
    modello = modello.strip()
    if 2 <= len(modello) <= 20:
        return modello, None
    else:
        return None, "Modello di veicolo non valido. Inserisci una stringa con lunghezza tra 2 e 20 caratteri"

def valida_dimensione_bagaglio(dimensione):
    dimensione = dimensione.strip().lower()
    if dimensione in ['piccolo', 'medio', 'grande']:
        return dimensione.capitalize(), None
    else:
        return None, "Dimensione del bagaglio non valida. Scegli tra 'Piccolo', 'Medio', 'Grande'"

def valida_numero_posti(input_posti):
    try:
        posti = int(input_posti.strip())
        if 1 <= posti <= 6:
            return posti, None
        else:
            return None, "Numero di posti non valido. Inserisci un valore tra 1 e 6."
    except ValueError:
        return None, "Numero di posti non valido. Inserisci un valore numerico."

def valida_campo_annuncio(indice_campo, nuovo_valore):
    if indice_campo == 5:  # Partenza
        return valida_data(nuovo_valore)
    elif indice_campo == 2:  # Partenza
        return valida_nome_citta(nuovo_valore)
    elif indice_campo == 3:  # Tappe
        tappe = nuovo_valore.split(',')
        valid_value = []
        for tappa in tappe:
            tappa_validata, errore_tappa = valida_nome_citta(tappa.strip())
            if errore_tappa:
                return None, errore_tappa
            valid_value.append(tappa_validata)
        return ', '.join(valid_value), None
    elif indice_campo == 4:  # Arrivo
        return valida_nome_citta(nuovo_valore)
    elif indice_campo == 9:  # Prezzo
        return valida_prezzo(nuovo_valore)
    elif indice_campo == 8:  # Veicolo
        return valida_modello_veicolo(nuovo_valore)
    elif indice_campo == 10: # Bagaglio
        return valida_dimensione_bagaglio(nuovo_valore)
    elif indice_campo == 11: # Posti
        return valida_numero_posti(nuovo_valore)
    elif indice_campo == 6:  # Dettagli
        return nuovo_valore, None  # Nessuna validazione specifica
    else:
        return None, "Campo non riconosciuto"

def valida_campo_ticket(indice_campo, nuovo_valore):
    if indice_campo == 0:  # Data
        return valida_data(nuovo_valore)
    elif indice_campo == 1:  # Partenza
        return valida_nome_citta(nuovo_valore)
    elif indice_campo == 2:  # Ora partenza
        return valida_orario(nuovo_valore)
    elif indice_campo == 3:  # Arrivo
        return valida_nome_citta(nuovo_valore)
    elif indice_campo == 4:  # Ora arrivo
        return valida_orario(nuovo_valore)
    elif indice_campo == 5:  # Prezzo
        return valida_prezzo(nuovo_valore)
    elif indice_campo == 6:  # Tipo di treno
        return valida_nome_citta(nuovo_valore)
    elif indice_campo == 7:  # Dettagli
        return nuovo_valore, None  # Nessuna validazione specifica
    else:
        return None, "Indice di campo non riconosciuto"


def valida_orario(orario):
    # Il formato dell'orario è HH:MM (formato 24 ore)
    if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', orario):
        return None, "Orario non valido. Inserisci l'orario nel formato 24h (es: 15:30)"
    return orario, None


def convert_date_format_for_list(date_str):
    if date_str is None:
        return None

    # Prova a convertire dal formato 'AAAA-MM-GG'
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        return date_obj.strftime('%d/%m/%y')  # Converte in 'GG/MM/AA'
    except ValueError:
        pass  # Continua a controllare gli altri formati

    # Prova a convertire dal formato 'GG/MM/AAAA'
    try:
        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
        return date_obj.strftime('%d/%m/%y')  # Converte in 'GG/MM/AA'
    except ValueError:
        pass  # Continua a controllare gli altri formati

    # Prova a convertire dal formato 'GG/MM/AA' (se già in questo formato, restituiscilo così com'è)
    try:
        datetime.strptime(date_str, '%d/%m/%y')
        return date_str  # Già nel formato corretto
    except ValueError:
        print(f"Data non valida: {date_str}")
        return None

def convert_date_registration(date_str):
    if date_str is None:
        return None

    # Prova a convertire dal formato 'AAAA-MM-GG HH:MM:SS.mmmmmm'
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S.%f')
        return date_obj.strftime('%d/%m/%y')  # Converte in 'GG/MM/AA'
    except ValueError:
        pass  # Continua a controllare gli altri formati

    # Aggiungi qui: Prova a convertire dal formato 'AAAA-MM-GG HH:MM:SS'
    try:
        date_obj = datetime.strptime(date_str, '%Y-%m-%d %H:%M:%S')
        return date_obj.strftime('%d/%m/%y')  # Converte in 'GG/MM/AA'
    except ValueError:
        pass  # Continua a controllare gli altri formati

    # I tuoi altri blocchi try-except per i formati 'AAAA-MM-GG', 'GG/MM/AAAA', e 'GG/MM/AA'

    # Restituisce None se nessuno dei formati corrisponde
    print(f"Data non valida: {date_str}")
    return None

# Funzione per formattare un singolo risultato
def format_result(result, result_type):
    if 'vehicle' in result:
        # Formatta come ride
        return (
            f"📢 Offro passaggio 📢\n\n"
            f"📆 Data: {result['date']}\n"
            f"📍 Partenza: {result['departure']}\n"
            f"🚩 Tappe: {result.get('stops', 'N/A')}\n"
            f"🏁 Arrivo: {result['arrival']}\n"
            f"💵 Prezzo: €{result['price']}\n"
            f"🚗 Veicolo: {result['vehicle']}\n"
            f"🧳 Bagaglio: {result['luggage']}\n"
            f"💺 Posti: {result['seats']}\n"
            f"🔍 Dettagli: {result['details']}\n"
        )
    elif 'train_type' in result:
        return (
            f"🎫 Cedo biglietto 🎫\n\n"
            f"📅 Data: {result['date']}\n"
            f"🚉 Partenza: {result['departure']} alle {result['departure_time']}\n"
            f"🚉 Arrivo: {result['arrival']} alle {result['arrival_time']}\n"
            f"💵 Prezzo: €{result['price']}\n"
            f"🚄 Treno: {result['train_type']}\n"
            f"🔍 Dettagli: {result['details']}\n"
        )
    else:
        return "Formato del risultato non riconosciuto."
    
# Funzione di validazione dell'URL migliorata
def is_valid_url(url):
    regex = re.compile(
        r'^(https?://)?'  # http:// o https:// (opzionale)
        r'(\S+\.)'  # dominio di primo livello
        r'(\S+)$'  # dominio di secondo livello
    )
    return re.match(regex, url) is not None