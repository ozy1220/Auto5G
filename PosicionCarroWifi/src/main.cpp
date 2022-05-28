#include <SPI.h>
#include <MFRC522.h>
#include <string.h>

//WIFI
#include <ESP8266Wifi.h>
#include <ESPAsyncTCP.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>

//RESET 8,9
//SS 10,2
#define R_PIN_1	D8   //Pin 9 para el reset del RC522
#define SS_PIN_1 D2   //Pin 10 para el SS (SDA) del RC522
#define R_PIN_2 D9
#define SS_PIN_2 D10

MFRC522 Front(SS_PIN_1, R_PIN_1); //Creamos el objeto para el RC522
MFRC522 Back(SS_PIN_2, R_PIN_2);

//WIFI
const char* WIFI_SSID = "EcoCharlyBravo";
const char* WIFI_PASSWORD = "6322167445Eco87";
const char* IP_SERVER = "10.70.1.19";  
const char* ATCP_SERVER = "10.70.1.208";
uint16_t ATCP_PORT = 8888;
WiFiClient wf;

AsyncClient* client;

//lector de rfid
unsigned int posb,posf,trash,parb,parf;
int blockNum = 5;
byte bufferLen = 18;
byte readBlockData[20];
MFRC522::StatusCode status;

//color de carro
String color = "Azul";   
bool llama,repe;

bool ReadBack(int blockNum, byte *readBlockData) 
{
  /* Reading data from the Block */
  bufferLen = 18;
  status = Back.MIFARE_Read(blockNum, readBlockData, &bufferLen);
  if (status != MFRC522::STATUS_OK)
  {
    Serial.print("Reading failed: ");
    Serial.println(Back.GetStatusCodeName(status));
    return false;
  }
  else
  {
    Serial.println("Block was read successfully");  
    return true;
  }
  
}
bool ReadFront(int blockNum, byte *readBlockData) 
{
  /* Reading data from the Block */
  bufferLen = 18;
  status = Front.MIFARE_Read(blockNum, readBlockData, &bufferLen);
  if (status != MFRC522::STATUS_OK)
  {
    Serial.print("Reading failed: ");
    Serial.println(Front.GetStatusCodeName(status));
    return false;
  }
  else
  {
    Serial.println("Block was read successfully");  
    return true;
  }
  
}

void postEnWeb() {
  HTTPClient http;    //Declare object of class HTTPClient

  String link = "/posicion/" + color + '/' + posf + '/' + posb ;
  Serial.println(link);

  wf.connect(IP_SERVER, 8080);
  http.begin(wf, IP_SERVER, 8080, link);     //Specify request destination
  
  int code = http.GET();
  Serial.println(code);
  http.end();
}

bool connectWifi()
{
  if (WiFi.status() == WL_CONNECTED)
  {
    return true;
  }

  Serial.println(WIFI_SSID);
  Serial.println(WIFI_PASSWORD);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  int maxRetries = 40;
  while (WiFi.status() != WL_CONNECTED)
  {
    delay(500);
    Serial.print(".");
    maxRetries--;
    if (maxRetries <= 0)
    {
      return false;
    }
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println(WIFI_SSID);
  Serial.println(WIFI_PASSWORD);
  Serial.println(WiFi.localIP());

  //wf.connect("10.70.1.19", 8080);

  return true;
}


static void handleData(void* arg, AsyncClient* client, void *data, size_t len) {
	Serial.printf("\n data received from %s \n", client->remoteIP().toString().c_str());
	Serial.write((uint8_t*)data, len);
}

void onConnect(void* arg, AsyncClient* client) {
	Serial.printf("\n client has been connected to %s on port %d \n", ATCP_SERVER, ATCP_PORT);
}



void setup() {
	Serial.begin(115200); //Iniciamos la comunicación  serial
	SPI.begin();        //Iniciamos el Bus SPI
	Front.PCD_Init(); // Iniciamos  el MFRC522
  Back.PCD_Init();

  Serial.print("\n");
  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);
  if (connectWifi()) Serial.println("Estoy conectado");
  else Serial.println("Se intento y no se logro :'(");

// connects to access point
	WiFi.mode(WIFI_STA);
	WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
	while (WiFi.status() != WL_CONNECTED) {
		Serial.print('.');
		delay(500);
	}

  client = new AsyncClient;
	client->onData(&handleData, client);
	client->onConnect(&onConnect, client);
	client->connect(ATCP_SERVER, ATCP_PORT);

}

void loop() {
  llama = false;

  //BACK
  if ( Back.PICC_IsNewCardPresent()) {  
  	//Seleccionamos una tarjeta
      if ( Back.PICC_ReadCardSerial()) {   

        if (ReadBack(blockNum, readBlockData)) {
          trash = *((unsigned int*) readBlockData);     
          if (trash != posb) {
            posb = trash;     
            llama = true;
          } 
        }
                     
      }      
	}

	// Revisamos si hay nuevas tarjetas  presentes
  trash = posf;
	if (Front.PICC_IsNewCardPresent()) {  
  	//Seleccionamos una tarjeta
    if ( Front.PICC_ReadCardSerial()) {  
      if (ReadFront(blockNum, readBlockData)) {
        trash = *((unsigned int*) readBlockData);
        parf = 0;          
      }     
    }     
	}
  else {
    if (!parf) parf = 1;
    else if (parf == 1) {
      parf = 2;
      trash = 0;
    }
  }	

  if (posf != trash){
    posf = trash;
    llama = true;
  }

  
  if (llama){
		char message[2];
		message[0] = 'V';
    message[1] = (char) 0;
		client->add(message, strlen(message));
		client->send();    
    //postEnWeb();
  }
}