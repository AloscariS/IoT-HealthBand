from flask import Flask
from config import Config
import numpy as np
import requests
import time
from geopy import distance
from datetime import datetime
from c_config import ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY

from Adafruit_IO import Client

aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

appname = "IOT - sample1"
app = Flask(appname)
myconfig = Config
app.config.from_object(myconfig)

# funzione per restituire la stringa time_str (relativa ad un dato di tipo timestamp) ma aumentata di un'ora
def fusoOrario(time_str):
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


@app.route('/')
def testoHTML():
    return '<h1>I love IoT</h1>'


@app.route('/isNear/<lat>,<long>', methods=['GET'])
def isNear(lat, long):
    led_on = 0
    curr_lat = float(lat)
    curr_long = float(long)
    dang_lat_arr = aio.data('danger-latitude')
    dang_long_arr = aio.data('danger-longitude')
    i = -1
    # lettura di tutti i dati del feed 'danger-latitude' creati al massimo un'ora (3600 sec) prima rispetto al tempo corrente
    for lat_data in dang_lat_arr :
        dang_lat_datetime = str(lat_data.created_at).replace('T', ' ').replace('Z', '')
        dang_lat_datetime = fusoOrario(dang_lat_datetime)
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
        # calcolo distanza tra la coppia di coordinate correnti e la coppia di coordinate dei soggetti con temperatura alta
        dist = distance.distance(dang_coord, curr_coord).km
        if(dist < 0.700):
            led_on = 1
    
    if(led_on == 1):
        return '1'
    else:
        return '0'



if __name__ == '__main__':
    port = 10000
    interface = '0.0.0.0'
    app.run(host=interface,port=port)