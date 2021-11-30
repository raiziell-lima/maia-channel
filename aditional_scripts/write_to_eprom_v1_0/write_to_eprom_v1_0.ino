#include <EEPROM.h>
uint32_t freq = 462700; // Canal 21
void setup() {
  byte f1 = (freq & 0xff);
  byte f2 = ((freq >> 8) & 0xff);
  byte f3 = ((freq >> 16) & 0xff);
  EEPROM.write(0x00, f1);
  EEPROM.write(0x01, f2);
  EEPROM.write(0x02, f3);
}

void loop() {
//
}
