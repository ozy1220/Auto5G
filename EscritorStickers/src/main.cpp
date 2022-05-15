#include <SPI.h>
#include <MFRC522.h>

#define SS_PIN D10  
#define RST_PIN D9  

MFRC522 mfrc522(SS_PIN, RST_PIN);

unsigned int ini = 396;
unsigned int fin = 600;

int blockNum = 5;  

/* Create an array of 16 Bytes and fill it with data */
/* This is the actual data which is going to be written into the card */
unsigned int blockData = ini;

/* Create another array to read data from Block */
/* Legthn of buffer should be 2 Bytes more than the size of Block (16 Bytes) */
byte bufferLen = 18;
byte readBlockData[18];

MFRC522::StatusCode status;

bool WriteDataToBlock(int blockNum, int blockData) 
{ 
  /* Write data to the block */
  status = mfrc522.MIFARE_Ultralight_Write(blockNum, (byte *) &blockData, 4);
  if (status != MFRC522::STATUS_OK)
  {
    Serial.print("Writing to Block failed: ");
    Serial.println(mfrc522.GetStatusCodeName(status));
    return false;
  }
  else
  {
    Serial.println("Data was written into Block successfully");
    return true;
  }
  
}

bool ReadDataFromBlock(int blockNum, byte readBlockData[]) 
{
  /* Reading data from the Block */
  status = mfrc522.MIFARE_Read(blockNum, readBlockData, &bufferLen);
  if (status != MFRC522::STATUS_OK)
  {
    Serial.print("Reading failed: ");
    Serial.println(mfrc522.GetStatusCodeName(status));
    return false;
  }
  else
  {
    Serial.println("Block was read successfully");  
    return true;
  }
  
}

void setup() 
{
  Serial.begin(115200);
  SPI.begin();
  mfrc522.PCD_Init();
  Serial.println("Scan a MIFARE Ultralight C Tag to write data...");
}

void loop()
{

  //detecta cartas
  if ( ! mfrc522.PICC_IsNewCardPresent()) return;
  if ( ! mfrc522.PICC_ReadCardSerial()) return;
  Serial.print("\n");
  Serial.println("**Card Detected**");
    
  while (blockData <= fin) {
    Serial.print("\n");
    Serial.print("Writing ");
    Serial.print(blockData);
    Serial.println(" to Data Block...");
    if (WriteDataToBlock(blockNum, blockData)) {
      blockData++;
      delay(1500);
      Serial.println("Listo para escribir");
    }
    return;
  }
   
  Serial.print("TERMINE");
  delay(10000);
}