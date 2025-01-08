const int pinosReceptores[44] = { 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,
                                  22, 23, 24, 25, 26, 27, 28, 29, 30, 31,
                                  32, 33, 34, 35, 36, 37, 38, 39, 40, 41,
                                  42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53 };
const int relePin = 14;
int leituras[44];

void setup() {
  Serial.begin(115200);


  for (int i = 0; i < 44; i++) {
    pinMode(pinosReceptores[i], INPUT);
  }
  pinMode(relePin, OUTPUT);
  digitalWrite(relePin, HIGH);
}

void loop() {
  int k = 0;
  String retorno;
  if (Serial.available() > 0) {
    String comando = Serial.readString();
    if (comando == "ATIVAR_RELE") {
      digitalWrite(relePin, HIGH);
    }

    if (comando == "DESATIVAR_RELE") {
      digitalWrite(relePin, LOW);
    }
  }

  for (k = 0; k < 44; k++) {
    leituras[k] = digitalRead(pinosReceptores[k]);

    if (digitalRead(pinosReceptores[k]) == HIGH) {
      retorno += "1;";
    } else {
      retorno += "0;";
    }
  }
  Serial.println(retorno);
  delay(100);
}
