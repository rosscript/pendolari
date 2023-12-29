TODO

Necessarie:
0 - Controllo esistenza username all avvio. FATTO
1- Sistemare id nella lista degli annunci, inventarsi qualcosa FATTO
2- Gestire modifica dei biglietti, show_ticket.py FATTO
3- Possibilita di non inserire tappe nelle rides FATTO
4- Implementare ricerca:
    -Sfogliare risultati ricerca con frecce avanti indietro per user experience FATTO
    -Impostare notifica nuovi annunci compatibili con i propri parametri FATTO
    -Implementazione sistema di notifica alla pubblicazione di un annuncio FATTO
5- La ricerca e la notifica devono superare eventuali discrepanze tra i campi (not exact match.) FATTO DA RIVEDERE MEGLIO
6- Logo e dati del bot

Di contorno:
1- Integrare funzionalità statistiche per utenti administrator e nella home (Numero annunci attivi ecc)
2- Integrare handler aggiuntivi, di supporto e di donazione
3- Possibilita per admin di inviare un messaggio broadcast.

Avanzate:
1- Ricerca e notifica in grado di interpretare arrivo e destinazione per suggerire soluzioni non perfette ma compatibili o accettabili: ad esempio, se l'utente cerca passaggio da Roma e l'annuncio ha come partenza Anagnina oppure Lecce con Lequile. In parte risolto da funzione tappe intermedie. (API esterne?)
2- Pensare di integrare limitazioni per utenti non premium, far pagare una tantum per:
    - Avere attivi più di 1 annuncio per volta (massimo gratuito 1 passaggio e 1 biglietto contemporaneamente)
    - Essere notificati (in questo caso manterrei gratuito per un certo periodo di tempo o altro)
3- Pensare ad un prezzo onesto per account premium e valutare integrazione stripe se fattibile
4- Integrare referral per avere più tempo a disposizione in modo gratuito per ogni utente portato FATTO
5- Funzionalità admin come eliminazione e ban

Sciccherie:
1- Integrare ricerca tramite API gpt (ricerca tramite vocale e risposta vocale)
2- Integrare grafiche automatiche per la composizione di immagini con i dati degli annunci
3- Possibilità per utenti premium di impostare campi preferiti come la tratta percorsa e il modello di macchina
4- Aggiungere step prima della ricerca che mostra le tratte piu diffuse tra gli annunci 

Valutabile ma difficile:
1- Gestire gli scambi economici direttamente in bot tramite stripe(pericoloso)