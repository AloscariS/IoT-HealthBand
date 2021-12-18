#include <Wire.h>
#include <Adafruit_MLX90614.h>
#include <math.h>


Adafruit_MLX90614 mlx = Adafruit_MLX90614();  //adafruit's library object to manage temperature sensor

const int tempLedPin = 4; //Digital output pin of the bpm led
const int tempPin1 = A4;  // FIRST Analog input pin that the temperature sensor is attached to
const int tempPin2 = A5;  // SECOND Analog input pin that the temperature sensor is attached to

const int pulsePin = A0;  // Analog input pin that the pulsossimeter is attached to

const int ledPin = 2; // Led which is turned on when the zone is "dangerous"
// states: 0: waiting, 1: 'O', 2: 'ON', 3: 'OF', 4: 'OFF'
int iState;

unsigned long last_temp_time;
unsigned long last_bpm_sample;
unsigned long last_bpm_write;



int tempValue = 0;    // FIRST temperature value
int lastTempValue = 0;    // FIRST temperature value


#define intervallo 20
#define samples 22

#define affidabilita 20

long contatore = 0; 
double BPM =0; 
double bpmRes = 0; 
double bpmVal = 0;
double lastBpmVal = 0;


double start_time = 0; 
double end_time = 0;


int differenza_campioni(){
  float primo_campione = read_sample();
  delay (intervallo);
  float secondo_campione = read_sample();
  float differenza = secondo_campione - primo_campione; 
  return differenza;
}

float read_sample(){
  float somma=0;
  for(int i=0;i<samples;i++)
    somma+=analogRead(pulsePin);

  return somma/samples;
}


void setup() {
  // initialize serial communications at 9600 bps:
  Serial.begin(9600);
  mlx.begin();            //initialize adafruit's library object
  pinMode(tempLedPin, OUTPUT);
  pinMode(pulsePin, INPUT);
  pinMode(tempPin1, INPUT);
  pinMode(tempPin2, INPUT);
  pinMode(ledPin, OUTPUT);
 
  digitalWrite(ledPin, LOW);
  digitalWrite(tempLedPin, LOW);
  
  last_temp_time=millis();
  last_bpm_sample=millis();

  iState=0;

}

// funzione per calibrare la misurazione dei bpm a seconda dei dati restituiti dal sensore
double getBpm()
{
    float differenza= differenza_campioni();
    if (differenza>0) // f(x+1)>f(x) ==> funzione crescente 
    {
      while (differenza>0)
      {
      differenza= differenza_campioni();
      } 
      contatore++; 
      if (contatore == 1) 
      {
      start_time = millis(); 
      }
    }
    else // f(x+1)<f(x) ==> abbiamo raggiunto un picco di massimo/minimo - funzione decrescente
    {
      while (differenza<=0)
      {
        differenza= differenza_campioni();
      } 
      contatore++; 
      if (contatore == 1)
      {
        start_time = millis(); // time at the time of first pick
      } 
    }

    if (contatore==affidabilita) 
    {
      end_time = millis(); 
      BPM = ((contatore*30000))/((end_time-start_time)) ; 
      bpmRes=BPM*0.19+30.56;
      contatore  = 0; 
    }
    return bpmRes;
}

/*
 *ATTENZIONE: 
 *Non scrivere su seriale commenti per debug altrimenti il bridge funzionerà in modo errato
*/

void loop()
{
  // bpmVal viene aggiornato ogni 10ms
  if (millis() - last_bpm_sample > 10)
  {
    last_bpm_sample = millis();
    bpmVal= getBpm();
  }
  
  // bpmVal viene scritto su Seriale ogni 3min
  if (millis() - last_bpm_write > 20000)
  {
    last_bpm_write = millis();
    if(bpmVal && bpmVal != lastBpmVal)
    {
      // print bmpVal to the Serial
      Serial.write(0xff);
      Serial.write(0x02);
      Serial.write((char)bpmVal);
      Serial.write(0xfe);
      lastBpmVal=bpmVal;
    }
  }
  
  //ogni 3min si controlla il valore di temperatura
  if (millis() - last_temp_time > 20000)
  {
    last_temp_time = millis();

    tempValue = getTemp();
    if(tempValue && tempValue != lastTempValue)
    {
      // print the results to the Serial:
      // Il pacchetto contenente il valore di temperatura inizia con 0xfd invece che 0xff
      Serial.write(0xfd);
      Serial.write(0x02);
      Serial.write((char)tempValue);
      Serial.write(0xfe);
      lastTempValue = tempValue;
      if(tempValue >= 40){
        digitalWrite(tempLedPin, HIGH);
      }
      else
      {
        digitalWrite(tempLedPin, LOW);
      }
    }
  }

  int iFutureState;
  int iReceived;

  if (Serial.available()>0)
  { 
    iReceived = Serial.read();

    // default: back to the first state
    iFutureState=0;

    if (iState==0 && iReceived=='O') iFutureState=1;
    if (iState==1 && iReceived=='N') iFutureState=2;
    if (iState==1 && iReceived=='F') iFutureState=3;
    if (iState==3 && iReceived=='F') iFutureState=4;
    if (iState==4 && iReceived=='O') iFutureState=1;
    if (iState==2 && iReceived=='O') iFutureState=1;
    
    // CR and LF always skipped (no transition)
    if (iReceived==10 || iReceived==13) iFutureState=iState;

     // onEnter Actions
    
     if (iFutureState==2 && iState==1) digitalWrite(ledPin, HIGH);  // switch on from 1 to 2
     if (iFutureState==4 && iState==3) digitalWrite(ledPin, LOW);  // switch off from 3 to 4
     
     // state transition
     iState = iFutureState;

     // Moore outputs
     // NO ADDITIONAL OUTPUTS
  }

}


float getTemp()
{
  float tempObjec = mlx.readObjectTempC();
  return tempObjec;
}

void printTemp()
{
    float tmp=getTemp();
    Serial.print("Body temp:");
    Serial.print(" ");    
    Serial.print(tmp);
    Serial.print("\xC2\xB0");      
    Serial.println("C");
}
