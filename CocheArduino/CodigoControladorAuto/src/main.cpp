#include <ESP8266Wifi.h>
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


const char* WIFI_SSID = "TP-Link_3D01";
const char* DIR_IP = "192.168.0.100";
const char* WIFI_PASSWORD = "01138580";

/*
const char* WIFI_SSID = "OSAIH6666";
const char* DIR_IP = "192.168.137.1";  
const char* WIFI_PASSWORD = "cuartoninos2";
*/

WiFiClient wf;

//color de carro
String color = "Verde";
int vh,vl,vn;
int a,b,c,d,v1,v2;
char pas;


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
  este();
  delay(50);
  para();
}
void noroeste() {
  oeste();
  delay(50);
  para();
}
void suroeste() {
  este();
  delay(50);
  para();
}
void sureste() {
  oeste();
  delay(50);
  para();
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
  String payload;

  if (wf.connect(DIR_IP, 8080)){    
    HTTPClient http;
    http.setTimeout(16000);
    http.begin(wf, DIR_IP, 8080, link);     //Specify request destination

    int code = http.GET();

    switch (code){
      case 200: payload = "V"; break;
      case 201: payload = "N"; break;
      case 202: payload = "S"; break;
      case 203: payload = "E"; break;
      case 204: payload = "O"; break;
      case 205: payload = "W"; break;
      case 206: payload = "X"; break;
      case 207: payload = "Y"; break;
      case 208: payload = "Z"; break;
    }

    //if (code != 200) Serial.println(code);

    //if (code > 0) payload = http.getString();    //Get the response payload
    //else payload = "V";
  
    http.end();
  }

  Serial.println(link + ": " + payload);
  if (payload.length() >= 1) return payload[0];
  else return 'V';
}

void obtenVelocidades() {

  String link = "/velocidad/" + color;

/*  if (wf.connect(DIR_IP, 8080)){
      String getstr = "GET " + link + " HTTP/1.1";
      Serial.println(getstr);
      wf.println(getstr);
      wf.println("Host: 192.168.137.1:8080");
      wf.println("User-Agent: ESP8266");
      wf.println("Content-Length: 0");
      wf.println();
      
      Serial.println("Reading");
      String velocidades = wf.readStringUntil('$');
      Serial.println(velocidades);
  }
*/

  WiFiClient wf;
  HTTPClient http;
  
  wf.connect(DIR_IP, 8080);    
  http.setTimeout(5000);
  http.begin(wf, DIR_IP, 8080, link);     //Specify request destination

  int code = http.GET();
  if (code != 200) Serial.println(code);

  String payload = http.getString();    //Get the response payload
  Serial.println("Pidiendo velocidades: " + payload);
  if (payload.length() >= 9){
    String strvh = payload.substring(0, 3);
    String strvl = payload.substring(3, 6);
    String strvn = payload.substring(6, 9);

    vh = strvh.toInt();
    vl = strvl.toInt();
    vn = strvn.toInt();
    Serial.println(vh);
    Serial.println(vl);
    Serial.println(vn);
  }
  http.end();

}

void registraMotores() {

  WiFiClient wf;
  HTTPClient http;  
  String link = "/registraArduino/" + color + "/motores";

  wf.connect(DIR_IP, 8080);
  http.setTimeout(1000);
  http.begin(wf, DIR_IP, 8080, link);
  int code = http.GET();
  if (code != 200) Serial.println(code);
  http.end();
}


void setup() {
  
  Serial.begin(115200);
  Serial.println();

  WiFi.setSleepMode(WIFI_NONE_SLEEP);
  WiFi.mode(WIFI_STA);

  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);
  if (connectWifi()) Serial.println("Estoy conectado");
  else Serial.println("Se intento y no se logro :'(");
  pas = 'V';
  
  //velocidades
  vn = 150;
  vh = 200;
  vl = 100;
  obtenVelocidades();
  
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

}

void loop() {

    char c;
    c = obtenDeWeb();
    aplicaDireccion(c);
    //delay(1);
}