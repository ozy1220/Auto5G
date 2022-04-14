#include <ESP8266Wifi.h>
#include <ESP8266HTTPClient.h>
#include <WiFiClient.h>
#include <string.h>

#define EnA 13 //10
#define EnB 16 //5
#define In1 12 //9
#define In2 14 //8
#define In3 4 //7
#define In4 5 //6

const char* WIFI_SSID = "EcoCharlyBravo";
const char* WIFI_PASSWORD = "6322167445Eco87";

String lastpos;

WiFiClient wf;
  

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
void este() {
  digitalWrite(In1, HIGH);
  digitalWrite(In2, LOW);
  digitalWrite(In3, LOW);
  digitalWrite(In4, HIGH);
  analogWrite(EnA, 150);
  analogWrite(EnB, 150);
}
void oeste() {
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

  wf.connect("10.70.1.19", 8080);

  return true;
}

char obtenDeWeb() {
  HTTPClient http;    //Declare object of class HTTPClient

  String link = "/querycarro/" + lastpos;
  Serial.println(link);

  wf.connect("10.70.1.19", 8080);
  http.begin(wf, "10.70.1.19", 8080, link);     //Specify request destination
  
  int code = http.GET();
  Serial.println(code);

  String payload = http.getString();    //Get the response payload
  Serial.println(payload);

  http.end();  //Close connection 

  // Regresa el primer caracter luego de las comillas
  return payload[1];

}

void setup() {

  pinMode(EnA, OUTPUT);
  pinMode(EnB, OUTPUT);
  pinMode(In1, OUTPUT);
  pinMode(In2, OUTPUT);
  pinMode(In3, OUTPUT);
  pinMode(In4, OUTPUT);
  
  Serial.begin(115200);
  Serial.println();

  lastpos = "limbo";

  Serial.print("Connecting to ");
  Serial.println(WIFI_SSID);
  if (connectWifi()) Serial.println("Estoy conectado");
  else Serial.println("Se intento y no se logro :'(");
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
  delay(50);
}