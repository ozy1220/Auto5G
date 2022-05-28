#include <ESP8266Wifi.h>
#include <ESPAsyncTCP.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <string.h>
#include <SPI.h>

#define EnA D7 
#define EnB D2 
#define In1 D6 
#define In2 D5 
#define In3 D4 
#define In4 D3

#define MSK_1 (1 << In1)
#define MSK_2 (1 << In2)
#define MSK_3 (1 << In3)
#define MSK_4 (1 << In4)

const char* WIFI_SSID = "EcoCharlyBravo";
const char* DIR_IP = "10.70.1.19";
const char* WIFI_PASSWORD = "6322167445Eco87";

WiFiClient wf, clientePosicion;
WiFiServer wifiServer(8888);
HTTPClient http;    //Declare object of class HTTPClient
static std::vector<AsyncClient*> clients; // a list to hold all clients

//color de carro
String color = "Azul";
int vh,vl,vn;
int a,b,c,d,v1,v2;
char pas;

// Diagonales por aumento de velocidad

void norte() {
  int msk = MSK_2 | MSK_4;
  GPOC = msk;

  msk = MSK_1 | MSK_3;
  GPOS = msk;

  if (v1 != vn) analogWrite(EnA, vn);
  if (v2 != vn) analogWrite(EnB, vn);
  a = 1; b = 0; c = 1; d = 0; v1 = vn; v2 = vn;
}
void sur() {
  int msk = MSK_1 | MSK_3;
  GPOC = msk;

  msk = MSK_2 | MSK_4;
  GPOS = msk; 

  if (v1 != vn) analogWrite(EnA, vn);
  if (v2 != vn) analogWrite(EnB, vn);
  a = 0; b = 1; c = 0; d = 1; v1 = vn; v2 = vn;
}
void oeste() {
  int msk = MSK_2 | MSK_3;
  GPOC = msk;

  msk = MSK_1 | MSK_4;
  GPOS = msk;

  if (v1 != vn) analogWrite(EnA, vn);
  if (v2 != vn) analogWrite(EnB, vn);
  a = 1; b = 0; c = 0; d = 1; v1 = vn; v2 = vn;
}
void este() {
  int msk = MSK_1 | MSK_4;
  GPOC = msk;

  msk = MSK_2 | MSK_3;
  GPOS = msk;
  if (v1 != vn) analogWrite(EnA, vn);
  if (v2 != vn) analogWrite(EnB, vn);
  a = 0; b = 1; c = 1; d = 0; v1 = vn; v2 = vn;
}
void para() {
  int msk = MSK_1 | MSK_2 | MSK_3 | MSK_4;
  GPOC = msk;

  if (v1 != vn) analogWrite(EnA, vn);
  if (v2 != vn) analogWrite(EnB, vn);
  a = 0; b = 0; c = 0; d = 0; v1 = vn; v2 = vn;

}

void noreste() { 
  norte();
  if (v1 != vl) analogWrite(EnA, vl);
  if (v2 != vh) analogWrite(EnB, vh);
  a = 1; b = 0; c = 1; d = 0; v1= vl; v2 = vh;  
}
void noroeste() {
  norte();
  if (v1 != vh) analogWrite(EnA, vh);
  if (v2 != vl)analogWrite(EnB, vl);
  a = 1; b = 0; c = 1; d = 0; v1= vh; v2 = vl;
}
void suroeste() {
  sur();
  if (v1 != vh) analogWrite(EnA, vh);
  if (v2 != vl) analogWrite(EnB, vl);
  a = 0; b = 1; c = 0; d = 1; v1 = vh; v2 = vl;
}
void sureste() {
  sur();
  if (v1 != vl) analogWrite(EnA, vl);
  if (v2 != vh) analogWrite(EnB, vh);
  a = 0; b = 1; c = 0; d = 1; v1 = vl; v2 = vh;
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

  //wf.connect(DIR_IP, 8080);

  return true;
}

void aplicaDireccion(char c){
    if (pas != c) {
      if (c == 'N') norte();
      else if (c == 'S') sur();
      else if (c == 'E') este();
      else if (c == 'O') oeste();
      else if (c == 'W') noroeste();
      else if (c == 'X') suroeste();
      else if (c == 'Y') sureste();
      else if (c == 'Z') noreste();
      else para();
      pas = c;
    }
}

char obtenDeWeb() {

  String link = "/avanzaMotores/" + color;
  //Serial.println(DIR_IP + link);

  if (!wf.connected()){
    http.end();
    wf.connect(DIR_IP, 8080);    
    http.setTimeout(15000);
    http.begin(wf, DIR_IP, 8080, link);     //Specify request destination
  }

  int code = http.GET();
  if (code != 200) Serial.println(code);

  String payload = http.getString();    //Get the response payload
  //Serial.println(payload);

  //http.end();  //Close connection 

  // Regresa el primer caracter luego de las comillas 
  return payload[1];

}

void registraMotores() {

  String link = "/registraArduino/" + color + "/motores";

  wf.connect(DIR_IP, 8080);
  http.setTimeout(1000);
  http.begin(wf, DIR_IP, 8080, link);
  int code = http.GET();
  if (code != 200) Serial.println(code);
  http.end();
}

/* clients events */
static void handleError(void* arg, AsyncClient* client, int8_t error) {
	Serial.printf("\n connection error %s from client %s \n", client->errorToString(error), client->remoteIP().toString().c_str());
}

static void handleData(void* arg, AsyncClient* client, void *data, size_t len) {
	Serial.printf("\n data received from client %s \n", client->remoteIP().toString().c_str());
	Serial.write((uint8_t*)data, len);
  aplicaDireccion(*(char*)data);
}

static void handleDisconnect(void* arg, AsyncClient* client) {
	Serial.printf("\n client %s disconnected \n", client->remoteIP().toString().c_str());
}

static void handleTimeOut(void* arg, AsyncClient* client, uint32_t time) {
	Serial.printf("\n client ACK timeout ip: %s \n", client->remoteIP().toString().c_str());
}

/* server events */
static void handleNewClient(void* arg, AsyncClient* client) {
	Serial.printf("\n new client has been connected to server, ip: %s", client->remoteIP().toString().c_str());

	// add to list
	clients.push_back(client);
	
	// register events
	client->onData(&handleData, NULL);
	client->onError(&handleError, NULL);
	client->onDisconnect(&handleDisconnect, NULL);
	client->onTimeout(&handleTimeOut, NULL);
}


void setup() {
  
  Serial.begin(115200);
  Serial.println();

  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);
  if (connectWifi()) Serial.println("Estoy conectado");
  else Serial.println("Se intento y no se logro :'(");
  pas = 'V';

	while (!WiFi.softAP(WIFI_SSID, WIFI_PASSWORD, 6, false, 15)) {
		delay(500);
	}
  
  //velocidades
  vn = 150;
  vh = 200;
  vl = 100;
  
  // Configura pines de PWM
  pinMode(EnA, OUTPUT);
  pinMode(EnB, OUTPUT);
  analogWrite(EnA, vn);
  analogWrite(EnB, vn);

  // Configura pines de salida de los motores
  pinMode(In1, OUTPUT);
  pinMode(In2, OUTPUT);
  pinMode(In3, OUTPUT);
  pinMode(In4, OUTPUT);

  // Abre servidor en puerto 8888
	AsyncServer* server = new AsyncServer(8888); // start listening on tcp port 8888
	server->onClient(&handleNewClient, server);
	server->begin();

  // Manda registro al server web
  registraMotores();
}


void loop() {

    char c;
    c = obtenDeWeb();
    aplicaDireccion(c);
     
    //delay(50);
}