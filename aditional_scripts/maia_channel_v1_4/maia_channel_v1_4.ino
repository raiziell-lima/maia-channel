//==============================================================================================================================================================//
//                                                                                                                                                              //
//                                                            MAIA - MOBILE AWARE INTERMODAL ASSISTANT                                                          //
//                                                    DELL LEAD - RESEARCH, DEVELOPMENT AND INNOVATION CENTER                                                   //
//                                                                                                                                                              //
//==============================================================================================================================================================//

//======================================================================== LIBRARIES ===========================================================================//

#include <SoftwareSerial.h>
#include <HamShield.h> 
#include <EEPROM.h>
#include <ArduinoJson.h>

//======================================================================= DEFINITIONS ==========================================================================//

#define MIC_PIN        3 // Pin responsible for sending audios in the raw format (It won't be used because the audios will be sent through the TRRS jack cable)
#define RESET_PIN     A3 // Reset pin
#define SWITCH_PIN     2 // Pin responsible for alternating between transmit and receive modes (switch)

//========================================================================= OBJECTS ============================================================================//

HamShield radio;
DynamicJsonDocument doc(200); // 200 is the maximum size of the data received during serial communication

//======================================================================== VARIABLES ===========================================================================//

char aux;                 
uint32_t freq;            
String requests = "";   
byte rssi;
bool muted, currently_tx; 

//================================================ FREQUENCIES (IN MHz) OF THE CHANNELS USED INSIDE THE FACTORY ================================================//
/*
    EMR Team (repair team)          01         (462.562 MHz)
    ARB Team                        02         (462.587 MHz)
    IT                              03         (462.612 MHz)
    PC - Production Control         04         (462.637 MHz)
    EHS – Emergency                 05         (462.662 MHz)
    CFI                             06         (462.687 MHz)
    Control Room / MDT / Office     07         (462.712 MHz)
    Process engineering             08         (467.562 MHz)
    Manufacture                     09         (467.587 MHz)
    Materials                       10         (467.612 MHz)
    Maintenance                     14         (467.712 MHz)
    Test engineering                15         (462.550 MHz)
    NPI                             17         (462.600 MHz)
    Quality                         20         (462.675 MHz)
*/

//======================================================================== USEFUL STRINGS ======================================================================//

// MQTT string example:    {"linha":"GL1","area":"Montagem","time_solicitado":"EMR","clientId":"eedd493b08543ca5","id":1591816377633}
// Serial string example : {"op_mode":0,"freq":462562,"time_":3000}

//==============================================================================================================================================================//

uint32_t read_from_eprom(){
  uint32_t f1 = EEPROM.read(0x00);
  uint32_t f2 = EEPROM.read(0x01);
  uint32_t f3 = EEPROM.read(0x02);

  f1 = f1 & 0xff;
  f2 = (f2 << 8) & 0xff00;
  f3 = (f3 << 16) & 0xff0000;

  uint32_t freq_backup = f1 + f2 + f3;
  return freq_backup;
}

//==============================================================================================================================================================//

void write_to_eprom(uint32_t new_maia_freq){
  //Serial.println("Alterando frequência de operação");
  freq = new_maia_freq;
  radio.frequency(freq);
  
  byte f1 = (new_maia_freq & 0xff);
  byte f2 = ((new_maia_freq >> 8) & 0xff);
  byte f3 = ((new_maia_freq >> 16) & 0xff);
  EEPROM.write(0x00, f1);
  EEPROM.write(0x01, f2);
  EEPROM.write(0x02, f3);
}

//==============================================================================================================================================================//

void transmit(long time_){
  radio.setModeTransmit();
  delay(time_ + 100); // Interval to Play the audio on raspberry
  radio.setMute();
  delay(1000); // Change 1500 to 1000 to apply the noise
  radio.setUnmute();
  radio.setModeReceive();
  radio.setMute();
  currently_tx = false;
  muted = true;
}

//==============================================================================================================================================================//

void setup() {
  // HamShield configuration
  pinMode(MIC_PIN, OUTPUT);  
  digitalWrite(MIC_PIN, LOW); // Will be kept at low logical level, since PWM will not be used to transmit the audios (we're using the TRRS cable)
  pinMode(SWITCH_PIN, INPUT_PULLUP);
  pinMode(RESET_PIN, OUTPUT);
  digitalWrite(RESET_PIN, LOW);
  
  pinMode(13, OUTPUT);
  digitalWrite(13, LOW);
  
  Serial.begin(9600);
  
  delay(100);
  digitalWrite(RESET_PIN, HIGH);
  delay(5); // Waits the system to stablish
  radio.initialize(); // Initializes automatically UHF 12.5kHz channel
  freq = read_from_eprom();
  Serial.println(freq);
  
  radio.dangerMode();
  radio.frequency(freq);
  radio.setModeReceive();
  currently_tx = false;
  
  radio.setSQOff();
  radio.setRfPower(7);
  radio.setCtcss(94.8); // Subcanal número 10
  radio.enableCtcss();
  Serial.println(radio.getCtcssFreqHz());
  
  delay(100);
  radio.setMute();
  muted = true;
  rssi = radio.readRSSI();
  Serial.println(radio.readRSSI());
}

//==============================================================================================================================================================//

void loop() {
  if (!currently_tx) {
    if (radio.getCtcssToneDetected()) {
      if (muted) {
        muted = false;
        radio.setUnmute();
      }
      // Keep hearing while a message is comming
      while(radio.readRSSI() > -70){
        delay(5);
      }
    } 
    
    else {
      if (!muted) {
        muted = true;
        radio.setMute();
      }
    }
  }
  
  if(Serial.available()){  
    requests = "";
    aux = ' ';
    
    while(Serial.available()){
      aux = Serial.read();
      requests+=aux;
      delay(3);
    }  
    
    deserializeJson(doc, requests);
    freq = doc["freq"];
    byte operation = doc["op_mode"]; 
    long time_ = doc["time_"];
    
    ///{"op_mode":0,"freq":462562,"time_":3000}
    
    if(!operation){
      if(time_){
        if (muted) {
          muted = false;
          radio.setUnmute();
        }
        currently_tx = true;
        transmit(time_);
      }
    }
    else{
      if(freq){
        write_to_eprom(freq);
      }
    }
  } // Global if
} // loop

//==============================================================================================================================================================//
