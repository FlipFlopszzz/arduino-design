#include <SPI.h>
#include <LoRa.h>
#include "config.h"
#include "Node.h"

PeerNode node;

void setup() {
  node.setup();
}

void loop() {
  node.loop();
}
