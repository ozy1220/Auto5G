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

const char* WIFI_SSID = "EcoCharlyBravo";
const char* DIR_IP = "10.70.1.19";
const char* WIFI_PASSWORD = "6322167445Eco87";

  WiFiClient wf;
  
//color de carro
String color = "Verde";

void norte() {
  digitalWrite(In1, HIGH);
  digitalWrite(In2, LOW);
  digitalWrite(In3, HIGH);
  digitalWrite(In4, LOW);
  analogWrite(EnA, 150);
  analogWrite(EnB, 150);
}
void sur() {
  digitalWrite(In1, LOW);
  digitalWrite(In2, HIGH);
  digitalWrite(In3, LOW);
  digitalWrite(In4, HIGH);
  analogWrite(EnA, 150);
  analogWrite(EnB, 150);
}
void oeste() {
  digitalWrite(In1, HIGH);
  digitalWrite(In2, LOW);
  digitalWrite(In3, LOW);
  digitalWrite(In4, HIGH);
  analogWrite(EnA, 150);
  analogWrite(EnB, 150);
}
void este() {
  digitalWrite(In1, LOW);
  digitalWrite(In2, HIGH);
  digitalWrite(In3, HIGH);
  digitalWrite(In4, LOW);
  analogWrite(EnA, 150);
  analogWrite(EnB, 150);
}
void para() {
  digitalWrite(In1, LOW);
  digitalWrite(In2, LOW);
  digitalWrite(In3, LOW);
  digitalWrite(In4, LOW);
  analogWrite(EnA, 150);
  analogWrite(EnB, 150);
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

  wf.connect(DIR_IP, 8080);

  return true;
}

char obtenDeWeb() {
  HTTPClient http;    //Declare object of class HTTPClient

  String link = "/avanzaMotores/" + color;
  Serial.println(link);

  wf.connect(DIR_IP, 8080);
  http.begin(wf, DIR_IP, 8080, link);     //Specify request destination
  
  int code = http.GET();
  Serial.println(code);

  String payload = http.getString();    //Get the response payload
  Serial.println(payload);

  http.end();  //Close connection 

  // Regresa el primer caracter luego de las comillas 
  return payload[1];

}

void setup() {
  
  Serial.begin(115200);
  Serial.println();

  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);
  if (connectWifi()) Serial.println("Estoy conectado");
  else Serial.println("Se intento y no se logro :'(");
  
  pinMode(EnA, OUTPUT);
  pinMode(EnB, OUTPUT);
  pinMode(In1, OUTPUT);
  pinMode(In2, OUTPUT);
  pinMode(In3, OUTPUT);
  pinMode(In4, OUTPUT);
}

void loop() {

    char c;
    c = obtenDeWeb();
    Serial.println(c);

    if (c == 'N') norte();
    else if (c == 'S') sur();
    else if (c == 'E') este();
    else if (c == 'O') oeste();
    else para();
    //delay(50);
}