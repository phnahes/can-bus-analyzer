# CAN Examples for Testing

Este diretório contém exemplos práticos para testar e usar o CAN Analyzer com diferentes dispositivos e protocolos.

## 📋 Índice

- [Exemplos Python](#exemplos-python)
- [Exemplos Arduino](#exemplos-arduino)
- [Arduino como Interface CAN (CanHacker)](#arduino-como-interface-can-canhacker)
- [Protocolo CanHacker/Lawicel](#protocolo-canhackerlawicel)

---

## Exemplos Python

### `send_can_message.py` - CAN Message Sender

Python script for direct serial communication with CanHacker/Lawicel protocol devices. **No external dependencies** (only pyserial).

#### 🎯 Features

- ✅ Direct serial communication with CanHacker/Lawicel devices
- ✅ Native protocol implementation
- ✅ No external dependencies (only `pyserial`)
- ✅ Automatic message cycling
- ✅ Message reception monitoring
- ✅ Multiple CAN bitrate support

#### 📦 Requirements

```bash
pip install pyserial
```

#### 🚀 How to Use

**1. Identify serial port:**

```bash
# macOS
ls /dev/tty.usbmodem*

# Linux
ls /dev/ttyACM*
```

**2. Edit port in script (if needed):**

Open `send_can_message.py` and adjust:
```python
PORT = "/dev/tty.usbmodemA021E7C81"  # Your port here
```

**3. Run:**

```bash
# Automatically cycles through messages 1-7
python3 send_can_message.py

# Listen-only mode (receive messages only, no transmission)
python3 send_can_message.py --listen
# or
python3 send_can_message.py -l
```

**Default mode (no arguments):**
- Connect to the device
- Configure CAN channel (500 Kbps)
- Cycle through 7 messages automatically
- Listen for responses between messages
- Press Ctrl+C to stop

**Listen mode (`--listen` or `-l`):**
- Connect to the device
- Configure CAN channel (500 Kbps)
- Only receive and display messages
- No transmission
- Press Ctrl+C to stop

#### 📤 Example Output

**Default mode (cycling messages):**
```
✓ Connected to /dev/tty.usbmodemA021E7C81
✓ Bitrate configured: 500000 bps
✓ CAN channel opened (active mode)

============================================================
Starting automatic message cycling...
Press Ctrl+C to stop
============================================================

[Message 1/7]
✓ Message sent: ID=0x3DA, Data=[0x01, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]

📡 Listening for messages (1.0 seconds)...
📨 RX: ID=0x280, DLC=8, Data=[0xBB, 0x8E, 0x00, 0x00, 0x29, 0xFA, 0x29, 0x29]

[Message 2/7]
✓ Message sent: ID=0x3DA, Data=[0x02, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00]
...

✓ Disconnected
```

**Listen-only mode:**
```
✓ Connected to /dev/tty.usbmodemA021E7C81
✓ Bitrate configured: 500000 bps
✓ CAN channel opened (active mode)

============================================================
Listen-only mode - receiving CAN messages
Press Ctrl+C to stop
============================================================

📡 Listening for messages (1.0 seconds)...
📨 RX: ID=0x280, DLC=8, Data=[0xBB, 0x8E, 0x00, 0x00, 0x29, 0xFA, 0x29, 0x29]
📨 RX: ID=0x284, DLC=6, Data=[0x06, 0x06, 0x00, 0x00, 0x00, 0x00]
📨 RX: ID=0x480, DLC=8, Data=[0x54, 0x80, 0x00, 0x00, 0x19, 0x41, 0x00, 0x20]
📡 Listening for messages (1.0 seconds)...
📨 RX: ID=0x680, DLC=8, Data=[0x81, 0x00, 0x00, 0x7F, 0x00, 0xF0, 0x47, 0x01]
...

✓ Disconnected
```

#### 🐛 Troubleshooting

**Problem: "Failed to configure bitrate"**

This usually means the device is not responding to commands. Try these steps:

1. **Enable debug mode to see what's happening:**
   ```bash
   python3 send_can_message.py --debug
   ```

2. **Check if device responds:**
   - Look for `[DEBUG] Response:` lines
   - If you see `'\r'` (carriage return) = success
   - If you see `'\x07'` (bell) = error
   - If empty = device not responding

3. **Common causes:**
   - **Wrong port**: Make sure you're using the correct port
     ```bash
     # List available ports
     ls /dev/cu.* /dev/tty.*
     ```
   - **Device already open**: Close other programs using the port
   - **Wrong baudrate**: Try 9600 or 19200 instead of 115200
   - **Device not in reset mode**: Power cycle the Arduino
   - **Arduino not programmed**: Make sure you uploaded the CanHacker sketch

4. **Test device manually:**
   ```bash
   # Open serial connection
   screen /dev/cu.usbserial-110 115200
   
   # Type these commands (press Enter after each):
   V       # Should return version (e.g., V1013)
   N       # Should return serial number
   S6      # Configure 500 Kbps
   O       # Open channel
   C       # Close channel
   
   # Exit screen: Ctrl+A then K then Y
   ```

5. **For Arduino with CanHacker library:**
   - Make sure you uploaded the correct sketch
   - Verify MCP2515 connections (CS=Pin 10, INT=Pin 2)
   - Check if MCP2515 module is powered (LED should be on)
   - Try pressing reset button on Arduino

6. **Alternative baudrates:**
   Edit the script and try different baudrates:
   ```python
   # In send_can_message.py, change:
   baudrate=115200  # Try: 9600, 19200, 38400, 57600
   ```

#### 🔧 CanHacker/Lawicel Protocol

The script uses native CanHacker/Lawicel protocol commands:

| Comando | Descrição | Exemplo |
|---------|-----------|---------|
| `Sn` | Configurar bitrate | `S6` = 500 Kbps |
| `O` | Abrir canal (modo ativo) | `O` |
| `L` | Modo listen-only | `L` |
| `C` | Fechar canal | `C` |
| `tIIILDD...` | Enviar frame standard | `t3DA80164000000000000` |
| `TiiiiiiiiLDD...` | Enviar frame extended | `T000003DA80164000000000000` |

#### 📊 Taxas de Bits Suportadas

| Código | Bitrate | Comando |
|--------|---------|---------|
| S0 | 10 Kbps | `S0` |
| S1 | 20 Kbps | `S1` |
| S2 | 50 Kbps | `S2` |
| S3 | 100 Kbps | `S3` |
| S4 | 125 Kbps | `S4` |
| S5 | 250 Kbps | `S5` |
| S6 | 500 Kbps | `S6` |
| S7 | 800 Kbps | `S7` |
| S8 | 1 Mbps | `S8` |

---

## Exemplos Arduino

### 📁 Arquivos Disponíveis

#### 1. `arduino_msg_generator.ino` - Gerador de Mensagens CAN
Gera mensagens CAN para testar a **recepção** do analyzer (Python → Arduino não necessário).

#### 2. `arduino_msg_receiver.ino` - Receptor de Mensagens CAN
Recebe e exibe mensagens CAN para testar a **transmissão** do analyzer (Python → Arduino).

#### 3. `arduino_canhacker.ino` - Arduino como Interface CAN
Transforma Arduino + MCP2515 em um dispositivo compatível com protocolo CanHacker/Lawicel.

---

# CAN Message Generator (arduino_msg_generator.ino)

Gerador de mensagens CAN configurável para testar o CAN Analyzer.

## Características

- ✅ **Escolha entre Standard (11-bit) ou Extended (29-bit) IDs**
- ✅ **Envio de ID específico ou aleatório dentro de um range**
- ✅ **Comprimento de dados configurável (0-8 bytes ou aleatório)**
- ✅ **Periodicidade configurável (fixa ou aleatória)**
- ✅ **Conteúdo customizável (dados fixos ou aleatórios)**
- ✅ **Grupo de mensagens predefinidas (simular múltiplas ECUs)**
- ✅ **Suporte para Remote Frames**
- ✅ **Configuração estática via #define (ajuste antes do upload)**

## Hardware Necessário

- Arduino (Uno, Mega, etc.)
- CAN-BUS Shield com MCP2515 ou MCP2518FD
- Conexão CAN-BUS para teste

## Instalação

1. Instale as bibliotecas necessárias no Arduino IDE:
   - Para MCP2515: [Seeed CAN-BUS Shield Library](https://github.com/Seeed-Studio/Seeed_Arduino_CAN)
   - Para MCP2518FD: Incluída na mesma biblioteca acima

2. Abra o arquivo `can_message_generator.ino` no Arduino IDE

3. Configure o tipo de shield no início do código:
   ```cpp
   #define CAN_2515    // Para MCP2515
   // #define CAN_2518FD  // Para MCP2518FD (comente a linha acima)
   ```

4. Ajuste os pinos se necessário:
   ```cpp
   const int SPI_CS_PIN = 9;   // CS pin do shield
   const int CAN_INT_PIN = 2;  // Interrupt pin
   ```

5. Faça o upload para o Arduino

## Como Usar

### Configuração Estática

Antes de fazer o upload para o Arduino, edite a seção de configuração no início do arquivo `.ino`:

```cpp
// ============================================================================
// CONFIGURAÇÃO - AJUSTE AQUI ANTES DE FAZER O UPLOAD
// ============================================================================

// Modo de Operação
#define USE_MESSAGE_GROUP  false    // true = enviar grupo de mensagens, false = modo normal

// Tipo de ID (usado se USE_MESSAGE_GROUP = false)
#define USE_STANDARD_ID    true     // true = Standard (11-bit), false = Extended (29-bit)

// Modo de ID (usado se USE_MESSAGE_GROUP = false)
#define USE_SPECIFIC_ID    false    // true = ID específico, false = range aleatório

// ID Específico (usado se USE_SPECIFIC_ID = true)
#define SPECIFIC_ID        0x123    // ID fixo a ser enviado

// Range de IDs (usado se USE_SPECIFIC_ID = false)
#define MIN_ID             0x100    // ID mínimo
#define MAX_ID             0x200    // ID máximo

// Comprimento dos dados (usado se USE_MESSAGE_GROUP = false)
#define DATA_LENGTH        255      // 0-8 bytes fixo, ou 255 para aleatório

// Periodicidade (Delay entre mensagens)
#define USE_RANDOM_PERIOD  false    // true = período aleatório, false = período fixo
#define DELAY_MS           100      // Delay fixo em milissegundos
#define MIN_DELAY_MS       50       // Delay mínimo (se USE_RANDOM_PERIOD = true)
#define MAX_DELAY_MS       500      // Delay máximo (se USE_RANDOM_PERIOD = true)

// Conteúdo da mensagem (usado se USE_MESSAGE_GROUP = false)
#define USE_CUSTOM_DATA    false    // true = usar dados customizados, false = aleatório
#define CUSTOM_DATA        {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08}

// Remote Frames (usado se USE_MESSAGE_GROUP = false)
#define SEND_REMOTE_FRAMES false    // true = inclui remote frames (~30% das msgs)

// ============================================================================
// GRUPO DE MENSAGENS (usado se USE_MESSAGE_GROUP = true)
// ============================================================================
CANMessage messageGroup[] = {
    // ID,    Ext,   Rem,  Len, {Data bytes}
    {0x100, false, false,  2,  {0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},
    {0x200, false, false,  2,  {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},
    {0x300, false, false,  1,  {0x5A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},
};

#define DELAY_BETWEEN_GROUP_MSGS  10  // Delay entre mensagens do grupo (ms)
// ============================================================================
```

### Exemplos de Configuração

#### Exemplo 1: Mensagem periódica fixa com dados customizados
**Caso de uso**: Simular um sensor que envia dados específicos a cada 100ms
```cpp
#define USE_STANDARD_ID    true
#define USE_SPECIFIC_ID    true
#define SPECIFIC_ID        0x123
#define DATA_LENGTH        8
#define USE_RANDOM_PERIOD  false
#define DELAY_MS           100      // Período fixo de 100ms
#define USE_CUSTOM_DATA    true
#define CUSTOM_DATA        {0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88}
#define SEND_REMOTE_FRAMES false
```

#### Exemplo 2: Mensagem com período aleatório
**Caso de uso**: Simular eventos esporádicos com timing variável
```cpp
#define USE_STANDARD_ID    true
#define USE_SPECIFIC_ID    true
#define SPECIFIC_ID        0x456
#define DATA_LENGTH        4
#define USE_RANDOM_PERIOD  true     // Período aleatório
#define MIN_DELAY_MS       50       // Entre 50ms e 500ms
#define MAX_DELAY_MS       500
#define USE_CUSTOM_DATA    false    // Dados aleatórios
#define SEND_REMOTE_FRAMES false
```

#### Exemplo 3: Range de IDs Extended com dados aleatórios
**Caso de uso**: Teste de stress com múltiplos IDs
```cpp
#define USE_STANDARD_ID    false    // Extended
#define USE_SPECIFIC_ID    false    // Usar range
#define MIN_ID             0x1000
#define MAX_ID             0x2000
#define DATA_LENGTH        255      // Tamanho aleatório
#define USE_RANDOM_PERIOD  false
#define DELAY_MS           50
#define USE_CUSTOM_DATA    false    // Dados aleatórios
#define SEND_REMOTE_FRAMES false
```

#### Exemplo 4: Simulação de contador incremental
**Caso de uso**: Enviar sempre o mesmo padrão de dados para verificar consistência
```cpp
#define USE_STANDARD_ID    true
#define USE_SPECIFIC_ID    true
#define SPECIFIC_ID        0x200
#define DATA_LENGTH        8
#define USE_RANDOM_PERIOD  false
#define DELAY_MS           100
#define USE_CUSTOM_DATA    true
#define CUSTOM_DATA        {0x00, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07}
#define SEND_REMOTE_FRAMES false
```

#### Exemplo 5: Teste de alta velocidade com período variável
**Caso de uso**: Simular barramento com tráfego irregular
```cpp
#define USE_STANDARD_ID    true
#define USE_SPECIFIC_ID    false
#define MIN_ID             0x000
#define MAX_ID             0x7FF
#define DATA_LENGTH        8
#define USE_RANDOM_PERIOD  true
#define MIN_DELAY_MS       10       // Entre 10ms e 100ms
#define MAX_DELAY_MS       100
#define USE_CUSTOM_DATA    false
#define SEND_REMOTE_FRAMES true     // Inclui remote frames
```

#### Exemplo 6: Mensagem única repetitiva (heartbeat)
**Caso de uso**: Simular um heartbeat de ECU
```cpp
#define USE_MESSAGE_GROUP  false
#define USE_STANDARD_ID    true
#define USE_SPECIFIC_ID    true
#define SPECIFIC_ID        0x7FF    // ID de heartbeat
#define DATA_LENGTH        2
#define USE_RANDOM_PERIOD  false
#define DELAY_MS           1000     // A cada 1 segundo
#define USE_CUSTOM_DATA    true
#define CUSTOM_DATA        {0xAA, 0x55, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}
#define SEND_REMOTE_FRAMES false
```

#### Exemplo 7: Grupo de mensagens - Modo Sequencial
**Caso de uso**: Simular múltiplas mensagens enviadas em sequência
```cpp
#define USE_MESSAGE_GROUP      true     // Ativar modo grupo
#define USE_INDIVIDUAL_PERIODS false    // Modo sequencial
#define USE_RANDOM_PERIOD      false
#define DELAY_MS               100      // Enviar grupo a cada 100ms

// Definir grupo de mensagens:
CANMessage messageGroup[] = {
    // ID,    Ext,   Rem,  Len, Period, {Data bytes}
    {0x100, false, false,  2,   0,     {0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // RPM
    {0x200, false, false,  2,   0,     {0x00, 0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Velocidade
    {0x300, false, false,  1,   0,     {0x5A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Temperatura
    {0x400, false, false,  4,   0,     {0x01, 0x02, 0x03, 0x04, 0x00, 0x00, 0x00, 0x00}},  // Status
};

#define DELAY_BETWEEN_GROUP_MSGS  10  // 10ms entre cada mensagem do grupo
```

#### Exemplo 7b: Grupo com Períodos Individuais
**Caso de uso**: Simular ECU real onde cada mensagem tem seu próprio período
```cpp
#define USE_MESSAGE_GROUP      true     // Ativar modo grupo
#define USE_INDIVIDUAL_PERIODS true     // Modo individual - cada msg com seu período!
#define USE_RANDOM_PERIOD      false

CANMessage messageGroup[] = {
    // ID,    Ext,   Rem,  Len, Period, {Data bytes}
    {0x100, false, false,  2,   10,    {0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // RPM - 10ms (100Hz)
    {0x200, false, false,  2,   20,    {0x00, 0x32, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Velocidade - 20ms (50Hz)
    {0x300, false, false,  1,   100,   {0x5A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Temperatura - 100ms (10Hz)
    {0x400, false, false,  4,   50,    {0x01, 0x02, 0x03, 0x04, 0x00, 0x00, 0x00, 0x00}},  // Status - 50ms (20Hz)
    {0x7FF, false, false,  1,   1000,  {0xAA, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Heartbeat - 1000ms (1Hz)
};
```

#### Exemplo 8: Grupo misto - Standard e Extended
**Caso de uso**: Testar analyzer com mensagens de diferentes tipos no mesmo grupo
```cpp
#define USE_MESSAGE_GROUP      true
#define USE_INDIVIDUAL_PERIODS false
#define USE_RANDOM_PERIOD      false
#define DELAY_MS               200

CANMessage messageGroup[] = {
    // ID,      Ext,   Rem,  Len, Period, {Data bytes}
    {0x123,    false, false,  8,   0,     {0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88}},  // Standard
    {0x1FFFF,  true,  false,  4,   0,     {0xAA, 0xBB, 0xCC, 0xDD, 0x00, 0x00, 0x00, 0x00}},  // Extended
    {0x456,    false, false,  2,   0,     {0x12, 0x34, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Standard
    {0x500,    false, true,   0,   0,     {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Remote Frame
};

#define DELAY_BETWEEN_GROUP_MSGS  5
```

#### Exemplo 9: Grupo de sensores com período variável
**Caso de uso**: Simular múltiplos sensores com timing irregular
```cpp
#define USE_MESSAGE_GROUP      true
#define USE_INDIVIDUAL_PERIODS false
#define USE_RANDOM_PERIOD      true     // Período aleatório entre grupos
#define MIN_DELAY_MS           100
#define MAX_DELAY_MS           500

CANMessage messageGroup[] = {
    // ID,   Ext,   Rem,  Len, Period, {Data bytes}
    {0x201, false, false,  2,   0,     {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Sensor 1
    {0x202, false, false,  2,   0,     {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Sensor 2
    {0x203, false, false,  2,   0,     {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Sensor 3
};

#define DELAY_BETWEEN_GROUP_MSGS  15
```

#### Exemplo 10: Simulação realista de CAN automotivo
**Caso de uso**: Simular barramento CAN de veículo com períodos realistas
```cpp
#define USE_MESSAGE_GROUP      true
#define USE_INDIVIDUAL_PERIODS true     // Cada mensagem com seu período!

CANMessage messageGroup[] = {
    // Powertrain (alta frequência)
    {0x0C0, false, false,  8,   10,    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Engine RPM - 10ms
    {0x0C1, false, false,  8,   10,    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Throttle - 10ms
    {0x0C2, false, false,  8,   20,    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Transmission - 20ms
    
    // Chassis (média frequência)
    {0x1A0, false, false,  8,   50,    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Wheel Speed - 50ms
    {0x1A1, false, false,  8,   50,    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Brake Pressure - 50ms
    
    // Body (baixa frequência)
    {0x2A0, false, false,  4,   100,   {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Door Status - 100ms
    {0x2A1, false, false,  2,   200,   {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Light Status - 200ms
    {0x2A2, false, false,  1,   500,   {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Climate - 500ms
    
    // Diagnostic
    {0x7DF, false, false,  8,   1000,  {0x02, 0x01, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // OBD Request - 1s
};
```

### Configuração Padrão

A configuração padrão (como vem no código) é:
- **Mode**: Single Message (não grupo)
- **ID Type**: Standard (11-bit)
- **ID Mode**: Specific ID = 0x123
- **Data Length**: Random (0-8)
- **Period**: Fixed 100 ms
- **Data Content**: Random
- **Remote Frames**: Disabled

### Tabela de Referência Rápida

| Funcionalidade | Parâmetro | Valores | Descrição |
|----------------|-----------|---------|-----------|
| **Modo** | `USE_MESSAGE_GROUP` | `true`/`false` | Grupo ou mensagem única |
| **Tipo ID** | `USE_STANDARD_ID` | `true`/`false` | Standard (11-bit) ou Extended (29-bit) |
| **Modo ID** | `USE_SPECIFIC_ID` | `true`/`false` | ID fixo ou range aleatório |
| **ID Fixo** | `SPECIFIC_ID` | `0x000-0x7FF` (Std)<br>`0x000-0x1FFFFFFF` (Ext) | ID específico |
| **Range** | `MIN_ID`, `MAX_ID` | Mesmo acima | Range de IDs |
| **Tamanho** | `DATA_LENGTH` | `0-8` ou `255` | Bytes fixos ou aleatório |
| **Período** | `USE_RANDOM_PERIOD` | `true`/`false` | Período fixo ou aleatório |
| **Delay Fixo** | `DELAY_MS` | `1-65535` ms | Delay entre ciclos |
| **Delay Range** | `MIN_DELAY_MS`, `MAX_DELAY_MS` | `1-65535` ms | Range de delay |
| **Dados** | `USE_CUSTOM_DATA` | `true`/`false` | Dados fixos ou aleatórios |
| **Dados Custom** | `CUSTOM_DATA` | `{0x00, ...}` | Array de 8 bytes |
| **Remote** | `SEND_REMOTE_FRAMES` | `true`/`false` | Incluir remote frames |
| **Delay Grupo** | `DELAY_BETWEEN_GROUP_MSGS` | `1-65535` ms | Delay entre msgs do grupo |
| **Período Individual** | `USE_INDIVIDUAL_PERIODS` | `true`/`false` | Cada msg com seu período |
| **Período Msg** | `periodMs` (no grupo) | `0-65535` ms | 0 = usar padrão |

## Recursos Avançados

### Periodicidade Configurável

Você pode escolher entre dois modos de periodicidade:

1. **Período Fixo** (`USE_RANDOM_PERIOD = false`):
   - Mensagens enviadas em intervalos regulares
   - Útil para simular sensores periódicos
   - Configure o intervalo com `DELAY_MS`

2. **Período Aleatório** (`USE_RANDOM_PERIOD = true`):
   - Mensagens enviadas em intervalos variáveis
   - Útil para simular eventos esporádicos ou tráfego irregular
   - Configure o range com `MIN_DELAY_MS` e `MAX_DELAY_MS`

### Conteúdo Customizável

Você pode escolher entre dois modos de conteúdo:

1. **Dados Aleatórios** (`USE_CUSTOM_DATA = false`):
   - Cada byte é gerado aleatoriamente (0x00-0xFF)
   - Útil para testes de stress e variabilidade
   - Funciona com qualquer tamanho de dados

2. **Dados Customizados** (`USE_CUSTOM_DATA = true`):
   - Envia sempre os mesmos bytes definidos em `CUSTOM_DATA`
   - Útil para simular mensagens reais de ECUs
   - Requer `DATA_LENGTH` fixo (não pode ser 255)
   - Exemplo: `{0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88}`

**Nota**: Dados customizados só funcionam quando:
- `USE_CUSTOM_DATA = true`
- `DATA_LENGTH` é um valor fixo (0-8), não 255
- Não é um Remote Frame

### Grupo de Mensagens Predefinidas

O modo de grupo permite enviar múltiplas mensagens CAN em sequência, simulando um sistema real com várias ECUs.

**Como funciona:**

1. **Ative o modo grupo**: `USE_MESSAGE_GROUP = true`
2. **Defina suas mensagens** no array `messageGroup[]`
3. **Escolha o modo de período**:
   - **Sequencial** (`USE_INDIVIDUAL_PERIODS = false`): Envia todas as mensagens em sequência
   - **Individual** (`USE_INDIVIDUAL_PERIODS = true`): Cada mensagem tem seu próprio período
4. **Configure o timing**:
   - `DELAY_BETWEEN_GROUP_MSGS`: Delay padrão entre mensagens
   - `periodMs` em cada mensagem: Período individual (modo individual)
   - `DELAY_MS` ou `USE_RANDOM_PERIOD`: Delay entre repetições do grupo (modo sequencial)

**Estrutura de cada mensagem:**

```cpp
{ID, isExtended, isRemote, len, periodMs, {data bytes}}
```

**Parâmetros explicados:**

| Parâmetro | Tipo | Descrição | Valores |
|-----------|------|-----------|---------|
| **ID** | `uint32_t` | Identificador CAN | Standard: 0x000-0x7FF<br>Extended: 0x000-0x1FFFFFFF |
| **isExtended** | `bool` | Tipo de ID | `false` = Standard (11-bit)<br>`true` = Extended (29-bit) |
| **isRemote** | `bool` | Tipo de frame | `false` = Data Frame (envia dados)<br>`true` = Remote Frame (solicita dados) |
| **len** | `uint8_t` | **Comprimento dos dados** | 0-8 bytes (quantos bytes a mensagem contém) |
| **periodMs** | `uint16_t` | Período individual | 0 = usar delay padrão<br>1-65535 = período em ms |
| **data** | `byte[8]` | Dados da mensagem | Array de 8 bytes em hexadecimal |

**Exemplo de definição:**

```cpp
CANMessage messageGroup[] = {
    // ID,    Ext,   Rem,  Len, Period, {Data bytes (sempre 8 bytes)}
    {0x100, false, false,  2,   10,    {0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // 2 bytes, 10ms
    {0x200, false, false,  4,   20,    {0xAA, 0xBB, 0xCC, 0xDD, 0x00, 0x00, 0x00, 0x00}},  // 4 bytes, 20ms
    {0x1FFFF, true, false, 8,   100,   {0x11, 0x22, 0x33, 0x44, 0x55, 0x66, 0x77, 0x88}},  // 8 bytes, 100ms
};
```

**Notas importantes:**

**`len` (length) - Comprimento dos dados:**
- Define quantos bytes da mensagem são válidos (0-8)
- Exemplo: se `len = 2`, apenas os 2 primeiros bytes do array `data` serão enviados
- Os bytes restantes são ignorados, mas devem estar presentes no array (sempre 8 bytes)
- Para Remote Frames, `len` deve ser 0

**`isRemote` (Remote Frame):**
- **Data Frame** (`isRemote = false`): Mensagem normal que **envia dados**
- **Remote Frame** (`isRemote = true`): Mensagem especial que **solicita dados** de outro nó
  - Não carrega dados próprios (len = 0)
  - Usado em protocolos onde um nó pede informações a outro
  - Exemplo: Nó A envia Remote Frame com ID 0x123 → Nó B responde com Data Frame 0x123 contendo os dados
- Em testes, Remote Frames são úteis para verificar se o analyzer os identifica corretamente

**Casos de uso:**
- Simular ECU automotiva completa (motor, transmissão, freios, etc.)
- Testar filtros e parsing de múltiplos IDs
- Simular comunicação entre múltiplos nós
- Criar cenários de teste reproduzíveis
- Validar sincronização de mensagens no analyzer

**Modos de Timing:**

### Modo Sequencial (USE_INDIVIDUAL_PERIODS = false)
```
Ciclo 1:
  Msg1 -> [DELAY_BETWEEN_GROUP_MSGS] -> Msg2 -> [DELAY_BETWEEN_GROUP_MSGS] -> Msg3
                                                                                  |
                                                                        [DELAY_MS ou random]
                                                                                  |
Ciclo 2:                                                                          v
  Msg1 -> [DELAY_BETWEEN_GROUP_MSGS] -> Msg2 -> [DELAY_BETWEEN_GROUP_MSGS] -> Msg3
  ...
```

### Modo Individual (USE_INDIVIDUAL_PERIODS = true)
```
Timeline:
0ms:    Msg1 (period=10ms)
10ms:   Msg1
20ms:   Msg1, Msg2 (period=20ms)
30ms:   Msg1
40ms:   Msg1, Msg2
50ms:   Msg1, Msg3 (period=50ms)
...

Cada mensagem é enviada de acordo com seu próprio período, independentemente das outras.
```

**Exemplo de saída no Serial Monitor:**
```
TX: [00000100](00) 10 00
TX: [00000200](00) 00 32
TX: [00000300](00) 5A
TX: [00000400](00) 01 02 03 04
[aguarda DELAY_MS]
TX: [00000100](00) 10 00
TX: [00000200](00) 00 32
...
```

## Formato de Saída

As mensagens enviadas são exibidas no Serial Monitor no formato:

```
TX: [000001F3](00) A5 3C 7B 12 FF 00 8D 42
```

Onde:
- `000001F3` = ID da mensagem (hex)
- `(00)` = Tipo de mensagem:
  - `0x00` = Standard Data Frame
  - `0x02` = Extended Data Frame
  - `0x30` = Standard Remote Frame
  - `0x32` = Extended Remote Frame
- `A5 3C 7B...` = Dados (em hex)

## Glossário de Termos CAN

| Termo | Significado | Descrição |
|-------|-------------|-----------|
| **ID** | Identificador | Número único que identifica a mensagem (0x000-0x7FF para Standard, 0x000-0x1FFFFFFF para Extended) |
| **Standard** | ID de 11 bits | Formato padrão CAN 2.0A (2048 IDs possíveis) |
| **Extended** | ID de 29 bits | Formato estendido CAN 2.0B (536 milhões de IDs possíveis) |
| **Len** | Length (comprimento) | Número de bytes de dados na mensagem (0-8) |
| **Data Frame** | Frame de dados | Mensagem normal que transporta dados |
| **Remote Frame** | Frame remoto | Mensagem que solicita dados de outro nó (sem dados próprios) |
| **DLC** | Data Length Code | Código que indica o tamanho dos dados (mesmo que len) |
| **Period** | Período | Intervalo de tempo entre envios da mesma mensagem |

## Exemplos Práticos de Grupos de Mensagens

### Grupo 1: ECU de Motor Simples (Modo Sequencial)
```cpp
#define USE_INDIVIDUAL_PERIODS false

CANMessage messageGroup[] = {
    // ID,   Ext,   Rem,  Len, Period, {Data bytes}
    {0x0C0, false, false, 2,   0,     {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // RPM (0-16383)
    {0x0C1, false, false, 2,   0,     {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // TPS (0-100%)
    {0x0C2, false, false, 1,   0,     {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Coolant Temp
    {0x0C3, false, false, 1,   0,     {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Oil Pressure
};
```

### Grupo 2: Dashboard Automotivo (Modo Individual)
```cpp
#define USE_INDIVIDUAL_PERIODS true

CANMessage messageGroup[] = {
    // ID,   Ext,   Rem,  Len, Period, {Data bytes}
    {0x100, false, false, 2,   20,    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Velocidade - 20ms
    {0x101, false, false, 2,   10,    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // RPM - 10ms
    {0x102, false, false, 1,   100,   {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Nível combustível - 100ms
    {0x103, false, false, 1,   200,   {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Temperatura - 200ms
    {0x104, false, false, 4,   1000,  {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Odômetro - 1s
};
```

### Grupo 3: Sistema de Sensores IoT
```cpp
#define USE_INDIVIDUAL_PERIODS true

CANMessage messageGroup[] = {
    // ID,   Ext,   Rem,  Len, Period, {Data bytes}
    {0x201, false, false, 4,   50,    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Sensor 1 (float) - 50ms
    {0x202, false, false, 4,   50,    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Sensor 2 (float) - 50ms
    {0x203, false, false, 4,   50,    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Sensor 3 (float) - 50ms
    {0x204, false, false, 8,   100,   {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Timestamp - 100ms
};
```

### Grupo 4: Teste de Protocolo Misto (com Remote Frame)
```cpp
#define USE_INDIVIDUAL_PERIODS false

CANMessage messageGroup[] = {
    // ID,        Ext,   Rem,  Len, Period, {Data bytes}
    {0x123,      false, false, 8,   0,     {0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08}},  // Standard Data
    {0x18FF1234, true,  false, 8,   0,     {0xAA, 0xBB, 0xCC, 0xDD, 0xEE, 0xFF, 0x11, 0x22}},  // Extended Data
    {0x456,      false, false, 4,   0,     {0x12, 0x34, 0x56, 0x78, 0x00, 0x00, 0x00, 0x00}},  // Standard Data
    {0x500,      false, true,  0,   0,     {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Remote Frame (len=0!)
};
```

## Dicas para Teste

### Testes Básicos
1. **Teste de IDs Standard**: Use range 0x000 - 0x7FF
2. **Teste de IDs Extended**: Use range 0x000 - 0x1FFFFFFF
3. **Teste de Performance**: Reduza o delay para 10-20ms
4. **Teste de Variabilidade**: Use comprimento aleatório e habilite Remote Frames
5. **Teste de ID Específico**: Útil para verificar filtros no analyzer

### Testes Avançados com Novas Funcionalidades
6. **Teste de Periodicidade Fixa**: Configure `USE_RANDOM_PERIOD = false` e `DELAY_MS = 100` para verificar timing preciso
7. **Teste de Periodicidade Variável**: Configure `USE_RANDOM_PERIOD = true` para simular tráfego irregular
8. **Teste de Dados Customizados**: Use `USE_CUSTOM_DATA = true` com padrões específicos (ex: `{0x00, 0xFF, 0x00, 0xFF}`) para verificar integridade
9. **Teste de Heartbeat**: Configure ID específico com período de 1000ms e dados fixos para simular mensagens de status
10. **Teste de Múltiplos Cenários**: Faça upload de diferentes configurações para testar como o analyzer lida com diferentes padrões

### Testes com Grupos de Mensagens
11. **Teste de Grupo Simples**: Use 3-4 mensagens com IDs sequenciais para verificar captura ordenada
12. **Teste de Timing de Grupo**: Configure `DELAY_BETWEEN_GROUP_MSGS = 5ms` e verifique intervalos no analyzer
13. **Teste de Grupo Misto**: Combine Standard e Extended no mesmo grupo para testar parsing
14. **Teste de Sincronização**: Use grupo com período fixo para verificar consistência temporal
15. **Teste de Carga**: Crie grupo com 10+ mensagens e delay curto para stress test

## Troubleshooting

### CAN init fail
- Verifique as conexões do shield
- Confirme que o baudrate está correto (padrão: 500 KBPS)
- Verifique se o barramento CAN está terminado corretamente (120Ω em cada extremidade)

### Mensagens não aparecem no Analyzer
- Verifique se o baudrate do analyzer está configurado para 500 KBPS
- Confirme que os fios CAN-H e CAN-L estão conectados corretamente
- Verifique se há terminação adequada no barramento

### Serial Monitor não mostra nada
- Confirme que o baudrate está em 115200
- Verifique a porta COM correta
- Pressione o botão reset no Arduino

## Compatibilidade

Testado com:
- Arduino Uno
- Arduino Mega
- Seeed Studio CAN-BUS Shield V2.0
- MCP2515 CAN Controller
- Baudrate: 500 KBPS

---

# CAN Message Receiver (arduino_msg_receiver.ino)

Receptor de mensagens CAN para testar a **transmissão** do Python analyzer.

## Características

- ✅ **Recebe todas as mensagens CAN (Standard e Extended)**
- ✅ **Exibe detalhes completos (ID, tipo, comprimento, dados)**
- ✅ **Estatísticas em tempo real (contagem, taxa de mensagens)**
- ✅ **Suporte para filtros de ID (opcional)**
- ✅ **Timestamp para cada mensagem**
- ✅ **Detecta Remote Frames**

## Como Usar

### 1. Configuração Básica

```cpp
// Display settings
#define SHOW_TIMESTAMP     true    // Show timestamp for each message
#define SHOW_STATISTICS    true    // Show periodic statistics
#define STATS_INTERVAL     5000    // Statistics display interval (ms)

// Filter settings (optional)
#define USE_FILTER         false   // Enable ID filtering
#define FILTER_ID          0x100   // Only show messages with this ID
#define FILTER_MASK        0x7FF   // Mask for filtering
```

### 2. Upload para o Arduino

1. Abra `arduino_msg_receiver.ino` no Arduino IDE
2. Selecione a placa e porta corretas
3. Faça o upload
4. Abra o Serial Monitor (115200 baud)

### 3. Teste com o Python Analyzer

No analyzer Python:
1. Conecte-se ao barramento CAN
2. Use a função de **transmissão** para enviar mensagens
3. Observe as mensagens sendo recebidas no Serial Monitor do Arduino

## Formato de Saída

### Mensagem Recebida
```
[    123456] RX: [00000123](00) 11 22 33 44 55 66 77 88
```

Onde:
- `[123456]` = Timestamp em milissegundos (se `SHOW_TIMESTAMP = true`)
- `RX:` = Mensagem recebida
- `[00000123]` = ID da mensagem (hex)
- `(00)` = Tipo de mensagem:
  - `0x00` = Standard Data Frame
  - `0x02` = Extended Data Frame
  - `0x30` = Standard Remote Frame
  - `0x32` = Extended Remote Frame
- `11 22 33...` = Dados em hexadecimal

### Remote Frame
```
[    123456] RX: [00000500](30) (Remote Frame - DLC=8)
```

### Estatísticas (a cada 5 segundos)
```
--- Statistics ---
Total messages: 1234
Messages/sec: 45.67
Last message: 123 ms ago
------------------
```

## Configurações Avançadas

### Filtro de ID

Para receber apenas mensagens com ID específico:

```cpp
#define USE_FILTER         true
#define FILTER_ID          0x123   // Receber apenas ID 0x123
#define FILTER_MASK        0x7FF   // Máscara para match exato
```

**Máscaras comuns:**
- `0x7FF` = Match exato para Standard ID
- `0x700` = Match nos 3 bits superiores (0x700-0x7FF)
- `0x1FFFFFFF` = Match exato para Extended ID

### Desabilitar Timestamp

Para melhor performance em alta taxa de mensagens:

```cpp
#define SHOW_TIMESTAMP     false
```

### Desabilitar Estatísticas

```cpp
#define SHOW_STATISTICS    false
```

## Casos de Uso

### 1. Testar Transmissão do Analyzer
- Configure o receptor no Arduino
- Use o analyzer Python para enviar mensagens
- Verifique se as mensagens chegam corretamente

### 2. Monitorar Barramento CAN
- Conecte o Arduino ao barramento
- Observe todas as mensagens em tempo real
- Use filtros para focar em IDs específicos

### 3. Debug de Protocolo
- Verifique se os dados estão corretos
- Confirme tipos de mensagem (Standard/Extended)
- Valide Remote Frames

### 4. Teste de Performance
- Monitore taxa de mensagens/segundo
- Verifique se há perda de mensagens
- Teste limites do barramento

## Exemplo de Teste Completo

### Setup:
1. **Arduino 1** (Transmissor): `arduino_msg_generator.ino`
2. **Arduino 2** (Receptor): `arduino_msg_receiver.ino`
3. **Python Analyzer**: Conectado ao barramento

### Teste:
1. Arduino 1 gera mensagens → Analyzer recebe
2. Analyzer transmite mensagens → Arduino 2 recebe
3. Valide que todos os dados estão corretos

## Troubleshooting

### Nenhuma mensagem recebida
- Verifique conexões CAN-H e CAN-L
- Confirme baudrate (500 KBPS)
- Verifique terminação do barramento (120Ω)
- Desabilite filtros (`USE_FILTER = false`)

### Mensagens corrompidas
- Verifique qualidade dos cabos
- Confirme terminação adequada
- Reduza comprimento dos cabos
- Verifique interferência elétrica

### Taxa de mensagens baixa
- Verifique se há erros no barramento
- Confirme que não há conflitos de ID
- Teste com menos mensagens simultâneas

## Compatibilidade

Testado com:
- Arduino Uno
- Arduino Mega
- Seeed Studio CAN-BUS Shield V2.0
- MCP2515 CAN Controller
- Baudrate: 500 KBPS

---

## Arduino como Interface CAN (CanHacker)

### 🎯 Visão Geral

Transforme seu **Arduino + MCP2515** em uma interface CAN profissional compatível com o protocolo **CanHacker/Lawicel SLCAN**. Isso permite usar o Arduino como adaptador USB-CAN de baixo custo com qualquer software que suporte o protocolo CanHacker.

### ✨ Vantagens

- ✅ **Baixo custo**: Arduino + MCP2515 custa ~$10 (vs $50-100 para adaptadores comerciais)
- ✅ **Protocolo padrão**: Compatível com CanHacker, CANHacker, python-can, etc.
- ✅ **Open-source**: Código totalmente aberto e customizável
- ✅ **Sem drivers proprietários**: Usa comunicação serial padrão
- ✅ **Funcionalidade completa**: Suporta todos os recursos do protocolo Lawicel

### 🔌 Hardware Necessário

| Componente | Especificação | Preço Aprox. |
|------------|---------------|--------------|
| Arduino Uno/Nano/Mega | Qualquer modelo | $5-15 |
| Módulo MCP2515 | CAN controller + transceiver | $3-8 |
| Cabos Jumper | Para conexões | $1-2 |
| Terminadores 120Ω | 2x resistores | $0.50 |

**Total: ~$10-25** (vs $50-100 para adaptadores comerciais)

### 🔧 Conexões

#### Pinagem Padrão MCP2515 → Arduino

| MCP2515 | Arduino Uno/Nano | Arduino Mega |
|---------|------------------|--------------|
| VCC | 5V | 5V |
| GND | GND | GND |
| CS | Pin 10 | Pin 10 |
| SO (MISO) | Pin 12 | Pin 50 |
| SI (MOSI) | Pin 11 | Pin 51 |
| SCK | Pin 13 | Pin 52 |
| INT | Pin 2 | Pin 2 |

#### Conexão CAN Bus

| MCP2515 | CAN Bus |
|---------|---------|
| CANH | CAN-H |
| CANL | CAN-L |

**⚠️ Importante:** Adicione resistores de terminação de 120Ω entre CAN-H e CAN-L nas **duas extremidades** do barramento CAN.

### 📚 Instalação da Biblioteca

**Método 1: Arduino Library Manager (Recomendado)**

1. Abra Arduino IDE
2. Vá em **Sketch** → **Include Library** → **Manage Libraries...**
3. Procure por **"CanHacker"**
4. Instale **"CanHacker by autowp"**
5. Instale também **"MCP2515 by autowp"** (dependência)

**Método 2: Manual**

```bash
cd ~/Documents/Arduino/libraries/
git clone https://github.com/autowp/arduino-mcp2515.git
git clone https://github.com/autowp/arduino-canhacker.git
```

### 📝 Código Arduino

**Use o exemplo oficial da biblioteca arduino-canhacker:**

1. **Abra o exemplo no Arduino IDE:**
   - **File** → **Examples** → **CanHacker** → **usb_cdc**

2. **Ou acesse diretamente:**
   - **Repositório**: [arduino-canhacker](https://github.com/autowp/arduino-canhacker/tree/master)
   - **Exemplo**: [usb_cdc.ino](https://github.com/autowp/arduino-canhacker/blob/master/examples/usb_cdc/usb_cdc/usb_cdc.ino)

3. **Configuração de pinos (padrão):**
   - CS = Pin 10
   - INT = Pin 2
   - MOSI, MISO, SCK = Pinos SPI padrão do Arduino

### 🚀 Como Usar

#### 1. Upload do Código

1. Conecte o Arduino ao computador via USB
2. Abra o sketch no Arduino IDE
3. Selecione a placa correta: **Tools** → **Board** → **Arduino Uno** (ou sua placa)
4. Selecione a porta: **Tools** → **Port** → `/dev/tty.usbmodemXXXXXX`
5. Clique em **Upload** (ou Ctrl+U)

#### 2. Verificar Conexão

Abra o Serial Monitor (Ctrl+Shift+M) e configure:
- **Baud rate**: 115200
- **Line ending**: Carriage return

Digite `V` e pressione Enter. Você deve ver algo como:
```
V1013
```
(Versão de hardware e firmware)

#### 3. Configurar no CAN Analyzer

1. Abra o **CAN Analyzer**
2. Vá em **Settings** (Ctrl+,)
3. Configure:
   - **CAN Device**: `/dev/tty.usbmodemXXXXXX` (sua porta Arduino)
   - **COM Baudrate**: `115200 bit/s`
   - **CAN Baudrate**: `500K` (ou a velocidade do seu barramento)
   - **Simulation Mode**: ❌ Desmarque
4. Clique **OK**
5. Clique **Connect**

Pronto! Seu Arduino agora funciona como uma interface CAN profissional! 🎉

### 🧪 Teste de Funcionamento

#### Teste 1: Verificar Comunicação Serial

```bash
# macOS/Linux
screen /dev/tty.usbmodemXXXXXX 115200

# Digite comandos:
V       # Ver versão
S6      # Configurar 500 Kbps
O       # Abrir canal
C       # Fechar canal
```

#### Teste 2: Enviar Mensagem CAN

No Serial Monitor:
```
S6              # Configurar 500 Kbps
O               # Abrir canal
t1234567890A    # Enviar: ID=0x123, DLC=4, Data=0x56 0x78 0x90 0xA0
```

#### Teste 3: Receber Mensagens

Com o canal aberto (`O`), mensagens recebidas aparecem automaticamente:
```
t1234567890A
t2805BB8E000029FA2929
```

### 📖 Protocolo CanHacker/Lawicel

O Arduino implementa o protocolo **Lawicel SLCAN**, usado por dispositivos CanHacker, USBtin, LAWICEL CANUSB, etc.

#### Comandos Principais

| Comando | Descrição | Exemplo | Resposta |
|---------|-----------|---------|----------|
| `Sn` | Configurar bitrate | `S6` (500 Kbps) | `\r` (CR) |
| `O` | Abrir canal (modo normal) | `O` | `\r` |
| `L` | Abrir canal (listen-only) | `L` | `\r` |
| `C` | Fechar canal | `C` | `\r` |
| `V` | Ver versão hardware/firmware | `V` | `Vhhff\r` |
| `N` | Ver número de série | `N` | `Nxxxx\r` |
| `Zv` | Toggle timestamp | `Z1` | `\r` |

#### Envio de Mensagens

**Standard Frame (11-bit ID):**
```
tIIILDDDDDDDDDDDDDDDD[CR]

Exemplo:
t1234567890A    # ID=0x123, DLC=4, Data=0x56 0x78 0x90 0xA0
```

**Extended Frame (29-bit ID):**
```
TiiiiiiiiLDDDDDDDDDDDDDDDD[CR]

Exemplo:
T000012345812345678    # ID=0x00001234, DLC=5, Data=0x12 0x34 0x56 0x78
```

**Remote Frame (Standard):**
```
riiiL[CR]

Exemplo:
r1234    # ID=0x123, DLC=4 (solicita 4 bytes)
```

**Remote Frame (Extended):**
```
RiiiiiiiiL[CR]

Exemplo:
R000012345    # ID=0x00001234, DLC=5
```

#### Recepção de Mensagens

Mensagens recebidas são enviadas automaticamente no mesmo formato:

```
t1234567890A              # Standard frame recebido
T000012345812345678       # Extended frame recebido
r1234                     # Remote frame standard
R000012345                # Remote frame extended
```

Com timestamp habilitado (`Z1`):
```
t12345678901234           # Timestamp: 0x1234 (últimos 4 dígitos)
```

#### Códigos de Bitrate

| Código | Bitrate | Uso Comum |
|--------|---------|-----------|
| `S0` | 10 Kbps | Redes industriais lentas |
| `S1` | 20 Kbps | - |
| `S2` | 50 Kbps | - |
| `S3` | 100 Kbps | - |
| `S4` | 125 Kbps | Automotivo (CAN Low Speed) |
| `S5` | 250 Kbps | Automotivo, Industrial |
| `S6` | 500 Kbps | **Automotivo (padrão)** ⭐ |
| `S7` | 800 Kbps | - |
| `S8` | 1 Mbps | Automotivo (CAN High Speed) |

#### Máscaras e Filtros de Aceitação

```
Mxxxxxxxx    # Configurar acceptance code (hex)
mxxxxxxxx    # Configurar acceptance mask (hex)

Exemplo:
M00000000    # Aceitar todos (padrão)
mFFFFFFFF    # Máscara completa
```

**Como funcionam:**
- **Acceptance Code**: ID que você quer aceitar
- **Acceptance Mask**: Bits que devem corresponder (1 = deve corresponder, 0 = ignorar)

Exemplo - aceitar apenas ID 0x123:
```
M00000123    # Code = 0x123
m000007FF    # Mask = 0x7FF (todos os bits de ID standard)
```

### 🔗 Referências

#### Documentação Oficial

- **Protocolo CanHacker**: https://github.com/autowp/arduino-canhacker/blob/master/docs/en/protocol.md
- **Biblioteca Arduino**: https://github.com/autowp/arduino-canhacker
- **MCP2515 Library**: https://github.com/autowp/arduino-mcp2515

#### Protocolo Lawicel Original

- **LAWICEL CANUSB**: http://www.can232.com/docs/canusb_manual.pdf
- **CanHacker for Windows**: http://www.mictronics.de/projects/usb-can-bus/

### 🐛 Troubleshooting

#### Arduino não responde

1. Verifique se o código foi carregado corretamente
2. Confirme baudrate 115200 no Serial Monitor
3. Teste com comando `V` - deve retornar versão
4. Verifique conexões SPI (MOSI, MISO, SCK, CS)

#### Erro "CAN init fail" ou sem resposta

1. Verifique conexões do MCP2515:
   - VCC → 5V
   - GND → GND
   - CS → Pin 10
   - INT → Pin 2
2. Confirme que o módulo MCP2515 está alimentado (LED aceso)
3. Verifique se o cristal do MCP2515 é 8MHz ou 16MHz
4. Ajuste a frequência no código se necessário

#### Mensagens não aparecem

1. Verifique terminação do barramento (120Ω em cada extremidade)
2. Confirme que CAN-H e CAN-L estão conectados corretamente
3. Teste com comando `L` (listen-only) para descartar problemas de ACK
4. Use multímetro: deve haver ~2.5V entre CAN-H e CAN-L em repouso

#### Mensagens corrompidas

1. Verifique qualidade dos cabos CAN
2. Reduza comprimento dos cabos (máx 40m @ 1Mbps)
3. Adicione terminação adequada (120Ω)
4. Verifique interferência elétrica
5. Teste com bitrate menor (S6 → S5 → S4)

#### Dispositivo não aparece no CAN Analyzer

1. Verifique se Arduino está conectado: `ls /dev/tty.*`
2. Confirme que não está aberto em outro programa (Serial Monitor, etc.)
3. Dê permissão ao dispositivo: `sudo chmod 666 /dev/tty.usbmodem*`
4. Reinicie o Arduino (botão reset)

### 💡 Dicas Avançadas

#### Customizar Pinos

Se precisar usar pinos diferentes, edite no código:

```cpp
const int SPI_CS_PIN = 9;   // Mudar CS para Pin 9
const int INT_PIN = 3;      // Mudar INT para Pin 3
```

**Nota:** Pinos SPI (MOSI, MISO, SCK) são fixos no hardware.

#### Usar com Outros Softwares

O Arduino com CanHacker funciona com qualquer software que suporte o protocolo Lawicel:

- ✅ **CAN Analyzer** (este projeto)
- ✅ **python-can** (interface `slcan`)
- ✅ **CANHacker for Windows**
- ✅ **Kayak** (Java CAN tool)
- ✅ **SavvyCAN**
- ✅ **BUSMASTER**

#### Exemplo com python-can

```python
import can

# Conectar ao Arduino CanHacker
bus = can.interface.Bus(
    bustype='slcan',
    channel='/dev/tty.usbmodemXXXXXX',
    bitrate=500000
)

# Enviar mensagem
msg = can.Message(
    arbitration_id=0x123,
    data=[0x11, 0x22, 0x33, 0x44],
    is_extended_id=False
)
bus.send(msg)

# Receber mensagem
msg = bus.recv(timeout=1.0)
print(f"RX: ID={msg.arbitration_id:03X}, Data={msg.data.hex()}")

bus.shutdown()
```

### 📊 Comparação: Arduino vs Adaptadores Comerciais

| Característica | Arduino + MCP2515 | USBtin | PEAK PCAN-USB | Vector CANcase |
|----------------|-------------------|--------|---------------|----------------|
| **Preço** | ~$10 | ~$50 | ~$100 | ~$500+ |
| **Protocolo** | CanHacker/Lawicel | CanHacker/Lawicel | Proprietário | Proprietário |
| **Open-source** | ✅ Sim | ❌ Não | ❌ Não | ❌ Não |
| **Customizável** | ✅ Sim | ❌ Não | ❌ Não | ❌ Não |
| **Bitrate Max** | 1 Mbps | 1 Mbps | 1 Mbps | 1 Mbps |
| **Drivers** | ❌ Não precisa | ❌ Não precisa | ✅ Precisa | ✅ Precisa |
| **Suporte SW** | Amplo (Lawicel) | Amplo (Lawicel) | Específico | Específico |

**Conclusão:** Para uso geral e aprendizado, o Arduino é uma excelente opção! 🎯

---

## 🎓 Casos de Uso

### Caso 1: Desenvolvimento e Testes

**Cenário:** Você está desenvolvendo um dispositivo CAN e precisa testar comunicação.

**Setup:**
1. **Arduino 1** com `arduino_canhacker.ino` → Interface para o PC
2. **Arduino 2** com `arduino_msg_generator.ino` → Simula seu dispositivo
3. **CAN Analyzer** no PC → Monitora e envia mensagens

**Vantagens:**
- Custo baixo (~$20 total)
- Fácil de configurar
- Totalmente customizável

### Caso 2: Análise de Barramento Automotivo

**Cenário:** Você quer analisar mensagens CAN do seu carro.

**Setup:**
1. Arduino com `arduino_canhacker.ino`
2. Conectar ao OBD-II do veículo (via adaptador OBD-CAN)
3. CAN Analyzer no laptop

**Vantagens:**
- Mais barato que adaptadores profissionais
- Protocolo aberto
- Funciona com múltiplos softwares

### Caso 3: Educação e Aprendizado

**Cenário:** Você está aprendendo sobre CAN bus.

**Setup:**
1. 2x Arduino com MCP2515
2. Um com `arduino_canhacker.ino` (interface)
3. Outro com `arduino_msg_generator.ino` (gerador)
4. CAN Analyzer para visualizar

**Vantagens:**
- Entende o protocolo na prática
- Código aberto para estudar
- Baixo custo para experimentar

---

## Licença

Baseado no código original da Seeed Technology Co., Ltd.
Melhorias e documentação por Paulo Nahes - 2026

**Bibliotecas utilizadas:**
- **arduino-canhacker** by autowp - MIT License
- **arduino-mcp2515** by autowp - MIT License
- **Seeed CAN Bus Shield** by Seeed Studio - MIT License
