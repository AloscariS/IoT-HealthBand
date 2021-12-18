import serial
import serial.tools.list_ports
import numpy as np
import requests
from geopy import distance
from datetime import datetime
from b_config import ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY

from Adafruit_IO import Client

aio = Client(ADAFRUIT_IO_USERNAME, ADAFRUIT_IO_KEY)

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

class AFBridge():


    def setupSerial(self):
        # apertura della porta seriale
        self.ser = None
        # lista delle porte disponibili
        ports = serial.tools.list_ports.comports()
        self.portname=""
        for port in ports:
            print (port.device)
            print (port.description)
            if 'arduino' in port.description.lower():
                self.portname = port.device
        print ("connecting to " + self.portname)

        try:
            if self.portname is not None:
                self.ser = serial.Serial(self.portname, 9600, timeout=0)
        except:
            print("ATTENZIONE: self.ser = None!!")
            self.ser = None

        # buffer di input dalla seriale
        self.inbuffer = []


    def setup(self):

        self.setupSerial()

    def loop(self):
        # loop infinito per la gestione della seriale
        lasttime = datetime.now()
        while (True):
            # aspetta un byte dalla seriale
            if not self.ser is None:

                if self.ser.in_waiting > 0:
                    # alcuni dati nella seriale sono pronti per essere letti
                    lastchar = self.ser.read(1)

                    if lastchar == b'\xfe':  # EOL
                        print("\nValue received")
                        self.useData()
                        self.inbuffer = []
                    else:
                        self.inbuffer.append(lastchar)
            sec_diff = (datetime.now() - lasttime).total_seconds()
            if sec_diff > 10 :
                curr_lat = aio.receive('latitude').value
                curr_long = aio.receive('longitude').value
                URL = 'http://localhost:10000/isNear/' + str(curr_lat) + ',' + str(curr_long)
                r = requests.get(URL)     
                if(int(r.content)):
                    self.ser.write(b'ON')
                else:
                    self.ser.write(b'OFF')


    def useData(self):
        # è stata ricevuta una linea dalla porta seriale, adesso si utilizza
        if len(self.inbuffer) < 3:  # al minimo header, dimensione e footer
            return False
        # controllo dell'header del pacchetto
        if self.inbuffer[0] != b'\xff' and self.inbuffer[0] != b'\xfd': # xff {xfd} è l'header per dati relativi alla frequenza cardiaca {alla temperatura}
            return False

        numval = int.from_bytes(self.inbuffer[1], byteorder='little')
        if numval>1:
            i=0
            val = int.from_bytes(self.inbuffer[i + 2], byteorder='little')
            strval = "SENDING: Sensor "+ str(i) + ": " + str(val)
            print(strval)
            if self.inbuffer[0] == b'\xff':
                print("Sent to the BPM feed!")
                aio.send('bpm', val)
            if self.inbuffer[0] == b'\xfd':
                print("Sent to the temperature feed!")
                aio.send('temperature', val)




if __name__ == '__main__':
    br=AFBridge()
    br.setup()

    br.loop()
