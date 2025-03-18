const int pinosReceptores[44] = { 15, 17, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13,
                                  22, 23, 24, 25, 26, 27, 28, 29, 30, 31,
                                  32, 33, 34, 35, 36, 37, 38, 39, 40, 41,
                                  42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53 };

const int relePin = 14;      // Relé para iniciar a contagem
const int relePinNovo = 19;  // Relé para parar a contagem

int leituras[44];  // Array para armazenar leituras dos sensores
bool contagemPausada = false;

void setup() {
  Serial.begin(115200);

  // Configura os pinos dos sensores como INPUT_PULLDOWN para evitar leituras flutuantes
  for (int i = 0; i < 44; i++) {
    pinMode(pinosReceptores[i], INPUT_PULLDOWN);
  }

  // Configura os pinos dos relés
  pinMode(relePin, OUTPUT);
  digitalWrite(relePin, HIGH);  // Relé original começa ativado

  pinMode(relePinNovo, OUTPUT);
  digitalWrite(relePinNovo, LOW);  // Relé novo começa desativado
}

void loop() {
  String retorno;
  bool esteiraComProduto = false;

  // Verifica se há comandos na serial
  if (Serial.available() > 0) {
    String comando = Serial.readString();
    if (comando == "ATIVAR_RELE") {
      digitalWrite(relePin, HIGH);
    } else if (comando == "DESATIVAR_RELE") {
      digitalWrite(relePin, LOW);
    }
  }

  // Verifica se o relé da porta 19 está ativado
  bool releNovoAtivado = digitalRead(relePinNovo) == HIGH;

  // Leitura dos sensores
  for (int k = 0; k < 44; k++) {
    if (releNovoAtivado) {
      retorno += "0;";  // Força todas as leituras a 0 quando o relé 19 está ativado
    } else {
      leituras[k] = digitalRead(pinosReceptores[k]);
      retorno += leituras[k] ? "1;" : "0;";
      if (leituras[k] == HIGH) {
        esteiraComProduto = true;
      }
    }
  }

  // Controle do relé baseado na esteira e no relé 19
  if (releNovoAtivado && !contagemPausada) {
    digitalWrite(relePin, LOW);  // Desativa a contagem
    contagemPausada = true;
  } else if (!releNovoAtivado && esteiraComProduto && contagemPausada) {
    digitalWrite(relePin, HIGH);  // Reativa a contagem
    contagemPausada = false;
  }

  Serial.println(retorno);
  delay(100);
}
