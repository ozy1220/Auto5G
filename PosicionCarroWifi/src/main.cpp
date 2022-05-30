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

const char* WIFI_SSID = "TP-Link_3D01";
const char* DIR_IP = "192.168.0.100";
const char* WIFI_PASSWORD = "01138580";


/*
const char* WIFI_SSID = "OSAIH6666";
const char* DIR_IP = "192.168.137.1";  
const char* WIFI_PASSWORD = "cuartoninos2";
*/

  WiFiClient wf;
  HTTPClient http;


//lector de rfid
unsigned int ultb, penb, ultf, penf, trash;
int blockNum = 5;
byte bufferLen = 18;
byte readBlockData[20];
MFRC522::StatusCode status;

//color de carro
String color = "Verde";   
bool llama,repe;
bool primeraVez = true;

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
    //Serial.println("Block was read successfully");  
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
    //Serial.println("Block was read successfully");  
    return true;
  }
  
}

void postEnWeb() {

  String link = "/posicion/" + color + '/' + ultf + '/' + ultb ;
  Serial.println(link);

  if (primeraVez){
    Serial.println("Conectando cliente WiFi por primera vez");
    wf.connect(DIR_IP, 8080);
    primeraVez = false;
  }
 // if (!wf.connected()){
 //   http.end();
 //   wf.connect(DIR_IP, 8080);
//    wf.disableKeepAlive();    
//    http.begin(wf, DIR_IP, 8080, link);     //Specify request destination
  //}

  Serial.println("Haciendo peticon get");
  http.begin(wf, DIR_IP, 8080, link);
  int code = http.GET();
  Serial.println("Fin del get");
  if (code != 200) Serial.println(code);
  http.end();

}

void obtenVelocidades() {

  String link = "/velocidad/Pos_" + color;

  WiFiClient wf;
  HTTPClient http;
  
  wf.connect(DIR_IP, 8080);    
  http.setTimeout(15000);
  http.begin(wf, DIR_IP, 8080, link);     //Specify request destination

  int code = http.GET();
  if (code != 200) Serial.println(code);

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
    Serial.print(WiFi.status());
    maxRetries--;
    if (maxRetries <= 0)
    {
      return false;
    }
  }
  Serial.println("");
  Serial.println("WiFi connected");
  Serial.println(WiFi.localIP());

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

  WiFi.setSleepMode(WIFI_NONE_SLEEP);
  WiFi.mode(WIFI_STA);
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
          if (trash != ultb) {
            int dif = ultb - penb;
            if (dif < 0) dif *= -1;

            if (dif != 1 || trash != penb){
              penb = ultb;
              ultb = trash;
              llama = true;
            }
          } 
        }
                     
      }      
	}

	// Revisamos si hay nuevas tarjetas  presentes
  trash = ultf;
	if (Front.PICC_IsNewCardPresent()) {  
  	//Seleccionamos una tarjeta
    if ( Front.PICC_ReadCardSerial()) {  
      if (ReadFront(blockNum, readBlockData)) {
        trash = *((unsigned int*) readBlockData);
        if (ultf != trash){
            int dif = ultf - penf;
            if (dif < 0) dif *= -1;

            if (dif != 1 || trash != penf) {
              penf = ultf;
              ultf = trash;
              llama = true;
            }
        }
      }     
    }     
	}

  
  if (llama) postEnWeb();
}