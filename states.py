from aiogram.dispatcher.filters.state import State, StatesGroup

class PostRide(StatesGroup):
    waiting_for_date = State()
    waiting_for_departure = State()
    waiting_for_stops = State()
    waiting_for_arrival = State()
    waiting_for_price = State()
    waiting_for_vehicle = State()
    waiting_for_luggage = State()
    waiting_for_seats = State()
    waiting_for_details = State()
    waiting_for_confirmation = State()
    waiting_for_finish = State()

class ShowRide(StatesGroup):
    waiting_for_ride_id = State()
    waiting_for_ride_action = State()

class EditRide(StatesGroup):
    choosing_field = State()
    editing_field = State()   

class SellTicket(StatesGroup):
    waiting_for_date = State()
    waiting_for_departure = State()
    waiting_for_departure_time = State()
    waiting_for_arrival = State()
    waiting_for_arrival_time = State()
    waiting_for_price = State()
    waiting_for_train_type = State()
    waiting_for_details = State()
    waiting_for_confirmation = State()
    waiting_for_finish = State()

class ShowTicket(StatesGroup):
    waiting_for_ticket_id = State()
    waiting_for_ticket_action = State()

class EditTicket(StatesGroup):
    choosing_field = State()
    editing_field = State()   

class SearchRide(StatesGroup):
    waiting_for_date_search = State()
    waiting_for_exact_date_input = State()  # Stato per l'input della data esatta
    waiting_for_date_range_input = State()  # Stato per l'input del range di date
    waiting_for_departure_search = State()
    waiting_for_arrival_search = State()
    waiting_for_action = State()

class ShowSearch(StatesGroup):
    waiting_for_search_id = State()
    waiting_for_search_action = State()
    waiting_for_search_confirmation = State()

class ManageAdmins(StatesGroup):
    showing_admins = State() 
    processing_admin = State() 

class ManagePremium(StatesGroup):
    showing_premium = State() 
    processing_premium = State() 
    
class AccountMenu(StatesGroup):
    waiting_for_menu_action = State()

class BroadcastMessage(StatesGroup):
    choosing_audience = State()
    waiting_for_message = State()
    waiting_for_buttons = State()  # Nuovo stato per raccogliere i dettagli dei pulsanti
    confirm_broadcast = State()  # Nuovo stato per la conferma finale

class BuyPremium(StatesGroup):
    waiting_subscription = State()
    waiting_payment = State()
    waiting_confirmation = State()
    waiting_finish = State()