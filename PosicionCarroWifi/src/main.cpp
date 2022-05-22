#include <SPI.h>
#include <MFRC522.h>
#include <string.h>

//WIFI
#include <ESP8266Wifi.h>
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
WiFiClient wf;

//lector de rfid
unsigned int posb,posf,trash;
int blockNum = 5;
byte bufferLen = 18;
byte readBlockData[20];
MFRC522::StatusCode status;

//color de carro
String color = "Verde";   
bool llama;

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

  wf.connect("10.70.1.19", 8080);
  http.begin(wf, "10.70.1.19", 8080, link);     //Specify request destination
  
  int code = http.GET();
  http.end();
}

bool connectWifi()
{
  if (WiFi.status() == WL_CONNECTED)
  {
    return true;
  }

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
  Serial.println(WiFi.localIP());

  //wf.connect("10.70.1.19", 8080);

  return true;
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
	if (Front.PICC_IsNewCardPresent()) {  
  	//Seleccionamos una tarjeta
         if ( Front.PICC_ReadCardSerial()) {  
               if (ReadFront(blockNum, readBlockData)) {
                trash = *((unsigned int*) readBlockData);          
                if (trash != posf) {
                  posf = trash;     
                  llama = true;
                }  
              }     
         }      
	}	


  if (llama) postEnWeb();
}