import logging
from geopy import distance
from pkg_resources import find_distributions
from datetime import datetime
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
from telegram import Chat, bot, ParseMode
from config import BOTKEY, chatID, ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY

from threading import Timer,Thread,Event

# Importazione della libreria di Adafruit e creazione dell'istanza REST Client
from Adafruit_IO import Client, Feed

aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)
# Creazione degli un oggetti di tipo Feed
bpmFeed = Feed(name='bmp')
tempFeed = Feed(name='temperature')

logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Definire alcuni handler (gestori) di comandi. Questi di solito prendono i due argomenti update e
# context. Gli handler ricevono anche l'oggetto TelegramError che viene sollevato in caso d'errore.
def start(update, context):
    """Send a message when the command /start is issued."""
    update.message.reply_text("Ciao, io sono <b>Healthband Bot</b>. Ti aiuterò a monitorare "
    "tutti i parametri misurati dalla Healthband, ti invierò un messaggio qualora i parametri "
    "raggiungerebbero un valore anomalo.\n\nPotrai utilizzare i seguenti comandi:\n\n/help - lista "
    "dei comandi disponibili\n/getBpm - visualizzare l'attuale valore di frequenza cardiaca\n/getTemperature - visualizzare "
    "l'attuale valore di temperatura corporea\n/getParameters - ottieni i valori attuali di tutti i parametri misurati"
    "\n/getCurrAddress - ottieni l'ultimo indirizzo localizzato", parse_mode=ParseMode.HTML)


def help_command(update, context):
    """Send a message when the command /help is issued."""
    update.message.reply_text("<b>Comandi disponibili:</b>\n\n/help - lista dei comandi disponibili "
    "\n/getBpm - visualizzare l'attuale valore di frequenza cardiaca\n/getTemperature - visualizzare "
    "l'attuale valore di temperatura corporea\n/getParameters - ottieni i valori attuali di tutti i parametri misurati"
    "\n/getCurrAddress - ottieni l'ultimo indirizzo localizzato", parse_mode=ParseMode.HTML)

def getBpm_command(update, context):
    bpmVal = aio.receive('bpm').value
    update.message.reply_text('Frequenza cardiaca attuale:\n' + str(bpmVal) + ' bpm ❤️')

def getTemp_command(update, context):
    tempVal = aio.receive('temperature').value
    update.message.reply_text('Temperatura corporea attuale:\n' + str(tempVal) + '°C 🌡')

def getParam_command(update, context):
    bpmVal = aio.receive('bpm').value
    tempVal = aio.receive('temperature').value
    update.message.reply_text('<b>VALORI ATTUALI:</b>\n\nFrequenza cardiaca: ' + str(bpmVal) + ' bpm ❤️' + '\nTemperatura'
    ' corporea: ' + str(tempVal) + '°C 🌡', parse_mode=ParseMode.HTML)

def getAddress_command(update, context):
    address_str = aio.receive('address').value
    creation_time = aio.receive('address').created_at
    creation_time_str = str(creation_time).replace('T' , ' 🕐').replace('Z' , ' ')
    creation_time_str = fusoOrario(creation_time_str)
    update.message.reply_text('<b>ULTIMA POSIZIONE RILEVATA:</b>\n\nDATA e ORA:\n🗓️' + creation_time_str + '\n\nINDIRIZZO:\n' + str(address_str) + '📍', parse_mode=ParseMode.HTML)
    
# Funzione per restituire la stringa time_str (relativa ad un dato di tipo timestamp) ma aumentata di un'ora.
# Versione di fusoOrario in cui passo time_str con emoji
def fusoOrario(time_str):
    d = int(time_str[12:14])
    if d == 23:
        res = '00'
    if d >= 9 and d != 23:
        d+= 1
        res = str(d)
    if d < 9:
        res = '0' + str(d+1)
    def_res = time_str[:12] + res + time_str[14:]
    return def_res

# Funzione per restituire la stringa time_str (relativa ad un dato di tipo timestamp) ma aumentata di un'ora.
# Versione di fusoOrario in cui passo time_str senza emoji
def fusoOrario2(time_str):
    d = int(time_str[11:13])
    if d == 23:
        res = '00'
    if d >= 9 and d != 23:
        d+= 1
        res = str(d)
    if d < 9:
        res = '0' + str(d+1)
    def_res = time_str[:11] + res + time_str[13:]
    return def_res


def startBot():
    global updater
    """Start the bot."""
    # Creazione dell'Updater e passaggio del token del bot telegram.
    # Assicurarsi di settare use_context=True
    updater = Updater(BOTKEY, use_context=True)

    # Ottenere il dispatcher per registrare gli handler  (callbacks)
    dp = updater.dispatcher

    # Aggiunta di un handler per ogni comando
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("getBpm", getBpm_command))
    dp.add_handler(CommandHandler("getTemperature", getTemp_command))
    dp.add_handler(CommandHandler("getParameters", getParam_command))
    dp.add_handler(CommandHandler("getCurrAddress", getAddress_command))




    # Avvio del Bot (polling per aspettare i messaggi)
    # La chiamata di questa funzione NON è bloccante
    updater.start_polling()

    return updater




# Creiamo manualmente un timer per chiamare una funzione ogni t secondi
# Il bot sarà anche in grado di avviare una conversazione in una chat con ID = chatID
class perpetualTimer():

    def __init__(self, t, hFunction, param):
        self.t = t
        self.hFunction = hFunction
        self.param = param
        self.thread = Timer(self.t, self.handle_function)

    def handle_function(self):
        self.hFunction(self.param)
        self.thread = Timer(self.t, self.handle_function)
        self.thread.start()

    def start(self):
        self.thread.start()

    def cancel(self):
        self.thread.cancel()


# Classe di utilità per la gestione dei dati recuperati dal feed di adafruit
class adafruitInfo():

    def __init__(self, val):
        self.firstUpdate = val
    
    def setFlag(self, val):
        self.firstUpdate = val

    def setLastBpmData(self, Data):
        self.lastBpmData = Data
    
    def setLastTempData(self, Data):
        self.lastTempData = Data
    
    def setLastExitData(self, Data):
        self.lastExitData = Data

    def setLastDangLatData(self, Data):
        self.lastDangLatData = Data


# Recupero e controllo dei dati recuperati dai feed di adafruit
def adafruitUpdate(updater):
    bpmData = aio.receive('bpm')
    tempData = aio.receive('temperature')
    exitData = aio.receive('exit')
    dangLatData = aio.receive('danger-latitude')
    bpmVal = bpmData.value
    tempVal = tempData.value
    exitVal = exitData.value
    dang_addr = aio.receive('danger-addr').value

    if aioInfo.firstUpdate :
        aioInfo.setLastBpmData(bpmData)
        aioInfo.setLastTempData(tempData)
        aioInfo.setLastExitData(exitData)
        aioInfo.setLastDangLatData(dangLatData)


    # Trigger per Danger Zone
    if  aioInfo.firstUpdate or dangLatData.id != aioInfo.lastDangLatData.id :
        sendText = 0
        curr_lat = aio.receive('latitude').value
        curr_long = aio.receive('longitude').value
        dang_lat_arr = aio.data('danger-latitude')
        dang_long_arr = aio.data('danger-longitude')
        i = -1
        # Lettura di tutti i dati del feed 'danger-latitude' creati al massimo un'ora (3600 sec) prima rispetto al tempo corrente
        for lat_data in dang_lat_arr :
            dang_lat_datetime = str(lat_data.created_at).replace('T', ' ').replace('Z', '')
            dang_lat_datetime = fusoOrario2(dang_lat_datetime)
            print('\n\n\n\ni= ' + str(i) +'\nDATO DI DANG_LAT=' + str(lat_data) + '\ncreato il: ' + str(dang_lat_datetime) + '\n')
            elapsed_lat_time = (datetime.now() - datetime.strptime(dang_lat_datetime, '%Y-%m-%d %H:%M:%S')).total_seconds()
            print( str(elapsed_lat_time) + 'secondi fa')
            if elapsed_lat_time >= 3600 :
                break
            i+=1
            long_val = dang_long_arr[i].value
            dang_coord = (lat_data.value, long_val)
            print( "\n COPPIA dang_lat-corr creata: ")
            print(dang_coord)
            curr_coord = (curr_lat, curr_long)
            # Calcolo distanza tra la coppia di coordinate correnti e la coppia di coordinate dei soggetti con temperatura alta
            dist = distance.distance(dang_coord, curr_coord).km
            if(dist < 0.700):
                sendText = 1

        if(sendText == 1):
            updater.bot.send_message(chat_id=chatID, text='<b>ATTENZIONE</b>:\nUn\'altra healthband vicina a te ha rilevato un valore '
            'eccessivo di temperatura in un altro soggetto nel raggio di 700m ☢️', parse_mode=ParseMode.HTML)
            aioInfo.setLastDangLatData(dangLatData)
            

    # Trigger per frequenza cardiaca
    if  aioInfo.firstUpdate or bpmData.id != aioInfo.lastBpmData.id :
        if int(bpmVal) >= 140 :
            updater.bot.send_message(chat_id=chatID, text='<b>ATTENZIONE</b>:\nFrequenza cardiaca eccessiva:\n' + str(bpmVal) + ' bpm ❤️', parse_mode=ParseMode.HTML)
            aioInfo.setLastBpmData(bpmData)

    # Trigger per temperatura
    if  aioInfo.firstUpdate or tempData.id != aioInfo.lastTempData.id :
        if int(tempVal) >38 :
            updater.bot.send_message(chat_id=chatID, text='<b>ATTENZIONE</b>:\nTemperatura corporea eccessiva:\n' + str(tempVal) + '°C 🌡', parse_mode=ParseMode.HTML)
            aioInfo.setLastTempData(tempData)
    
    # Trigger per l'uscita
    if  aioInfo.firstUpdate or exitData.id != aioInfo.lastExitData.id :
        if int(exitVal) == 1 :
            address_str = aio.receive('address').value
            creation_time = aio.receive('address').created_at
            creation_time_str = str(creation_time).replace('T' , ' 🕐').replace('Z' , ' ')
            creation_time_str = fusoOrario(creation_time_str)
            updater.bot.send_message(chat_id=chatID, text='<b>ATTENZIONE</b>:\nIl soggetto è uscito dall\'area di casa 🏃\n\n\n'
            '<b>ULTIMA POSIZIONE RILEVATA:</b>\n\nDATA e ORA:\n🗓️' + creation_time_str + '\n\nINDIRIZZO:\n' + str(address_str) + '📍', parse_mode=ParseMode.HTML)
            aioInfo.setLastExitData(exitData)
    
    # Fine di firstUpdate
    if aioInfo.firstUpdate : 
        aioInfo.setFlag(0)



if __name__ == '__main__':
    # Avvio del bot
    updater = startBot()
    aioInfo = adafruitInfo(1) #setta ad 1 il flag indicatore del primo "update" effettuato da adafruit
    # avvio il thread
    # Avremo 2 thread: un primo thread con il timer in esecuzione e l'altro bloccato
    randomizer = perpetualTimer(10,adafruitUpdate,updater)
    randomizer.start()

    # idle = inattività (blocco)
    updater.idle()
