#include <SPI.h>
#include <MFRC522.h>

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
unsigned int pos;
int blockNum = 5;
byte bufferLen = 18;
byte readBlockData[18];
MFRC522::StatusCode status;  

bool ReadBack(int blockNum, byte readBlockData[]) 
{
  /* Reading data from the Block */
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
bool ReadFront(int blockNum, byte readBlockData[]) 
{
  /* Reading data from the Block */
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

  //BACK
  if ( Back.PICC_IsNewCardPresent()) {  
  	//Seleccionamos una tarjeta
      if ( Back.PICC_ReadCardSerial()) {   

        if (ReadBack(blockNum, readBlockData)) {
          pos = *((unsigned int*) readBlockData);
          //hacer la query
          
        }

                      
      }      
	}	

	// Revisamos si hay nuevas tarjetas  presentes
	if (Front.PICC_IsNewCardPresent()) 
        {  
  		//Seleccionamos una tarjeta
            if ( Front.PICC_ReadCardSerial()) 
            {
                  // Enviamos serialemente su UID
                  Serial.print("FRONT     Card UID:");
                  for (byte i = 0; i < Front.uid.size; i++) {
                          Serial.print(Front.uid.uidByte[i] < 0x10 ? " 0" : " ");
                          Serial.print(Front.uid.uidByte[i], HEX);   
                  } 
                  Serial.println();
                  // Terminamos la lectura de la tarjeta  actual
                  Front.PICC_HaltA();         
            }      
	}	
}