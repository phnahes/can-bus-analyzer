/*
 * OBD-II ECU Simulator for Arduino with MCP2515 CAN Module
 * 
 * This sketch simulates an OBD-II ECU (Engine Control Unit) that responds
 * to standard OBD-II requests with realistic fake data.
 * 
 * Hardware Required:
 * - Arduino (Uno, Nano, Mega, etc.)
 * - MCP2515 CAN Bus Module (Seeed Studio or compatible)
 * - CAN Bus connection (CAN-H, CAN-L, GND)
 * 
 * Wiring (MCP2515 to Arduino):
 * - VCC  -> 5V
 * - GND  -> GND
 * - CS   -> Pin 9 (configurable below)
 * - SO   -> Pin 12 (MISO)
 * - SI   -> Pin 11 (MOSI)
 * - SCK  -> Pin 13
 * - INT  -> Pin 2 (optional)
 * 
 * Library Required:
 * - Seeed Arduino CAN by Seeed Studio
 *   Install via: Arduino IDE -> Tools -> Manage Libraries -> Search "Seeed Arduino CAN"
 * 
 * Usage:
 * 1. Upload this sketch to Arduino
 * 2. Connect Arduino CAN module to CAN bus (500 kbps)
 * 3. Open CAN Analyzer OBD-II Monitor
 * 4. Select PIDs to monitor and start polling
 * 5. Arduino will respond with simulated data
 * 
 * Supported Services:
 * - Service 01 (Show current data):
 *   Support PIDs (for PID discovery):
 *   - 0x00: PIDs supported [01-20] ✓
 *   - 0x20: PIDs supported [21-40] ✓
 *   - 0x40: PIDs supported [41-60] ✓
 *   - 0x60: PIDs supported [61-80] ✓
 *   
 *   Data PIDs:
 *   - 0x04: Engine Load (%)
 *   - 0x05: Coolant Temperature (°C)
 *   - 0x0C: Engine RPM (animated 800-3000 RPM)
 *   - 0x0D: Vehicle Speed (km/h)
 *   - 0x0F: Intake Air Temperature (°C)
 *   - 0x10: MAF Air Flow (g/s)
 *   - 0x11: Throttle Position (%)
 *   - 0x2F: Fuel Level (%)
 *   - 0x42: Control Module Voltage (V)
 *   - 0x46: Ambient Air Temperature (°C)
 *   - 0x5C: Engine Oil Temperature (°C)
 * 
 * - Service 03 (Read DTCs):
 *   Returns 4 simulated DTCs:
 *   - P0171: System Too Lean (Bank 1)
 *   - P0300: Random/Multiple Cylinder Misfire Detected
 *   - C0035: Left Front Wheel Speed Sensor Circuit
 *   - B1234: Example Body Code
 *
 * - Service 09 (Vehicle information):
 *   - PID 0x02: VIN (17 ASCII chars, ISO-TP multi-frame)
 * 
 * Author: CAN Analyzer Team
 * Date: 2026-02-05
 * License: MIT
 */

#include <SPI.h>

#define CAN_2515
// #define CAN_2518FD

// Set SPI CS Pin according to your hardware
#if defined(SEEED_WIO_TERMINAL) && defined(CAN_2518FD)
const int SPI_CS_PIN  = BCM8;
const int CAN_INT_PIN = BCM25;
#else
const int SPI_CS_PIN = 10;
const int CAN_INT_PIN = 2;
#endif

#ifdef CAN_2518FD
#include "mcp2518fd_can.h"
mcp2518fd CAN(SPI_CS_PIN);
#define MAX_DATA_SIZE 8
#endif

#ifdef CAN_2515
#include "mcp2515_can.h"
mcp2515_can CAN(SPI_CS_PIN);
#define MAX_DATA_SIZE 8
#endif

// ============================================================================
// CONFIGURATION
// ============================================================================

// OBD-II IDs
#define OBD2_REQUEST_ID  0x7DF     // Standard OBD-II request ID (broadcast)
#define OBD2_RESPONSE_ID 0x7E8     // ECU response ID (ECU #1)
// Many scanners send ISO-TP Flow Control to the physical tester->ECU ID (0x7E0)
#define OBD2_PHYSICAL_REQUEST_ID 0x7E0

// Simulation Parameters
#define ENGINE_IDLE_RPM 800        // Idle RPM
#define ENGINE_MAX_RPM 6000        // Maximum RPM
#define SIMULATION_SPEED 50        // Update speed (ms)

// Debug Mode (set to true to enable Serial debug output)
#define DEBUG_MODE true

// Fake VIN to return in Service 09 PID 02 (must be 17 ASCII characters)
static const char VIN_STRING[] = "1HGBH41JXMN109186";

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================


#define CAN_CRYSTAL_CLOCK  MCP_8MHz   // MCP_16MHz, MCP_12MHz, or MCP_8MHz
#define CAN_SPEED         CAN_500KBPS  // e.g. CAN_250KBPS, CAN_500KBPS, CAN_1000KBPS

// Simulated engine parameters (will change over time)
struct EngineState {
  float rpm;              // Engine RPM
  float speed;            // Vehicle speed (km/h)
  float coolant_temp;     // Coolant temperature (°C)
  float intake_temp;      // Intake air temperature (°C)
  float oil_temp;         // Oil temperature (°C)
  float throttle;         // Throttle position (%)
  float load;             // Engine load (%)
  float maf;              // MAF air flow (g/s)
  float fuel_level;       // Fuel level (%)
  float voltage;          // Control module voltage (V)
  float ambient_temp;     // Ambient temperature (°C)
} engine;

// Animation state
unsigned long last_update = 0;
unsigned long request_count = 0;
unsigned long response_count = 0;

// ============================================================================
// SETUP
// ============================================================================

void setup() {
  // Initialize Serial for debugging
  SERIAL_PORT_MONITOR.begin(115200);
  while (!SERIAL_PORT_MONITOR) {}
  
  if (DEBUG_MODE) {
    SERIAL_PORT_MONITOR.println(F("\n========================================"));
    SERIAL_PORT_MONITOR.println(F("OBD-II ECU Simulator"));
    SERIAL_PORT_MONITOR.println(F("========================================\n"));
  }
  
  // Initialize MCP2515
  #if MAX_DATA_SIZE > 8
  CAN.setMode(CAN_NORMAL_MODE);
  #endif
  
  while (CAN_OK != CAN.begin(CAN_SPEED, CAN_CRYSTAL_CLOCK)) {
    SERIAL_PORT_MONITOR.println(F("CAN init fail, retry..."));
    delay(100);
  }
  
  if (DEBUG_MODE) {
    SERIAL_PORT_MONITOR.println(F("✓ MCP2515 initialized"));
    SERIAL_PORT_MONITOR.print(F("  Baudrate: "));
    SERIAL_PORT_MONITOR.println(F("500 kbps"));
    SERIAL_PORT_MONITOR.print(F("  Response ID: 0x"));
    SERIAL_PORT_MONITOR.println(OBD2_RESPONSE_ID, HEX);
    SERIAL_PORT_MONITOR.println();
    SERIAL_PORT_MONITOR.println(F("Waiting for OBD-II requests..."));
    SERIAL_PORT_MONITOR.println();
  }
  
  // Initialize engine state with realistic values
  engine.rpm = ENGINE_IDLE_RPM;
  engine.speed = 0;
  engine.coolant_temp = 85.0;      // Normal operating temp
  engine.intake_temp = 25.0;       // Room temperature
  engine.oil_temp = 90.0;          // Slightly higher than coolant
  engine.throttle = 0.0;           // Closed throttle
  engine.load = 15.0;              // Idle load
  engine.maf = 2.5;                // Idle air flow
  engine.fuel_level = 75.0;        // 75% full
  engine.voltage = 14.2;           // Normal alternator voltage
  engine.ambient_temp = 22.0;      // Room temperature
}

// ============================================================================
// MAIN LOOP
// ============================================================================

void loop() {
  // Update simulated engine parameters
  update_engine_simulation();
  
  // Check for incoming CAN messages
  if (CAN_MSGAVAIL == CAN.checkReceive()) {
    unsigned long id;
    byte len;
    byte buf[MAX_DATA_SIZE];
    
    // Read the message
    CAN.readMsgBuf(&len, buf);
    id = CAN.getCanId();
    
    // Check if it's an OBD-II request (functional 0x7DF or physical 0x7E0).
    // This simulator expects single-frame requests where buf[0] is the payload length (<= 0x07).
    // Ignore ISO-TP Flow Control/FF/CF frames (e.g. 0x30..).
    if ((id == OBD2_REQUEST_ID || id == OBD2_PHYSICAL_REQUEST_ID) &&
        len >= 2 &&
        ((buf[0] & 0xF0) == 0x00)) {
      request_count++;
      handle_obd2_request(buf, len);
    }
  }
  
  delay(1);  // Small delay to prevent overwhelming the bus
}

// ============================================================================
// ENGINE SIMULATION
// ============================================================================

void update_engine_simulation() {
  unsigned long now = millis();
  
  if (now - last_update < SIMULATION_SPEED) {
    return;  // Not time to update yet
  }
  
  last_update = now;
  
  // Simulate RPM variation (smooth sine wave)
  static float rpm_phase = 0.0;
  rpm_phase += 0.02;
  if (rpm_phase > 6.28) rpm_phase = 0.0;  // 2*PI
  
  // RPM varies between idle and 3000 RPM
  engine.rpm = ENGINE_IDLE_RPM + (2200.0 * (0.5 + 0.5 * sin(rpm_phase)));
  
  // Speed proportional to RPM (simplified)
  engine.speed = (engine.rpm - ENGINE_IDLE_RPM) / 50.0;
  if (engine.speed < 0) engine.speed = 0;
  
  // Throttle follows RPM
  engine.throttle = ((engine.rpm - ENGINE_IDLE_RPM) / (ENGINE_MAX_RPM - ENGINE_IDLE_RPM)) * 100.0;
  if (engine.throttle < 0) engine.throttle = 0;
  if (engine.throttle > 100) engine.throttle = 100;
  
  // Load follows throttle
  engine.load = 15.0 + (engine.throttle * 0.7);
  
  // MAF increases with RPM
  engine.maf = 2.5 + (engine.rpm - ENGINE_IDLE_RPM) / 400.0;
  
  // Temperatures slowly increase with load (simplified)
  static float temp_accumulator = 0.0;
  temp_accumulator += (engine.load - 20.0) * 0.001;
  if (temp_accumulator > 10.0) temp_accumulator = 10.0;
  if (temp_accumulator < -5.0) temp_accumulator = -5.0;
  
  engine.coolant_temp = 85.0 + temp_accumulator;
  engine.oil_temp = 90.0 + temp_accumulator;
  engine.intake_temp = 25.0 + (temp_accumulator * 0.5);
  
  // Fuel level slowly decreases (very slowly)
  static unsigned long fuel_timer = 0;
  if (now - fuel_timer > 10000) {  // Every 10 seconds
    fuel_timer = now;
    engine.fuel_level -= 0.1;
    if (engine.fuel_level < 10.0) engine.fuel_level = 100.0;  // Reset to full
  }
  
  // Voltage varies slightly (alternator simulation)
  engine.voltage = 14.2 + (sin(rpm_phase * 3.0) * 0.2);
}

// ============================================================================
// OBD-II REQUEST HANDLER
// ============================================================================

// Handle Service 03: Read Diagnostic Trouble Codes
void handle_dtc_request() {
  if (DEBUG_MODE) {
    SERIAL_PORT_MONITOR.println(F("  → Sending 4 DTCs"));
  }
  
  // Real vehicles typically use ISO-TP (ISO 15765-2) for multi-frame responses.
  // Payload for Service 03 response:
  //   0x43, count, (dtc_hi, dtc_lo) * count
  //
  // With 4 DTCs: 1 + 1 + 8 = 10 bytes => does not fit in a single CAN frame => ISO-TP FF + CF.

  const uint8_t dtc_count = 4;
  const uint16_t payload_len = 2 + (dtc_count * 2);  // 0x43 + count + pairs

  // Build payload bytes (10 bytes)
  byte payload[10];
  payload[0] = 0x43;       // Service 03 response (0x03 + 0x40)
  payload[1] = dtc_count;  // Number of DTCs

  // DTC 1: P0171 (0x0171)
  payload[2] = 0x01;
  payload[3] = 0x71;

  // DTC 2: P0300 (0x0300)
  payload[4] = 0x03;
  payload[5] = 0x00;

  // DTC 3: C0035 (C = 01 => 0x40xx, 0x0035)
  payload[6] = 0x40;
  payload[7] = 0x35;

  // DTC 4: B1234 (B = 10 => 0x80xx, 0x1234 => high 0x92, low 0x34)
  payload[8] = 0x92;
  payload[9] = 0x34;

  // ISO-TP First Frame:
  //   [0] = 0x10 | (len_hi)
  //   [1] = len_lo
  //   [2..7] = first 6 bytes of payload
  byte ff[8];
  ff[0] = 0x10 | ((payload_len >> 8) & 0x0F);
  ff[1] = payload_len & 0xFF;
  for (int i = 0; i < 6; i++) {
    ff[2 + i] = payload[i];
  }

  CAN.sendMsgBuf(OBD2_RESPONSE_ID, 0, 8, ff);

  if (DEBUG_MODE) {
    SERIAL_PORT_MONITOR.print(F("→ ISO-TP FF (DTC): ID 0x"));
    SERIAL_PORT_MONITOR.print(OBD2_RESPONSE_ID, HEX);
    SERIAL_PORT_MONITOR.print(F(" ["));
    for (int i = 0; i < 8; i++) {
      if (ff[i] < 0x10) SERIAL_PORT_MONITOR.print(F("0"));
      SERIAL_PORT_MONITOR.print(ff[i], HEX);
      if (i < 7) SERIAL_PORT_MONITOR.print(F(" "));
    }
    SERIAL_PORT_MONITOR.println(F("]"));
  }

  // Wait for ISO-TP Flow Control (like a real ECU would).
  uint16_t stmin_ms = 0;
  bool got_fc = wait_for_isotp_flow_control(stmin_ms);
  if (!got_fc && DEBUG_MODE) {
    SERIAL_PORT_MONITOR.println(F("  ⚠️ No ISO-TP Flow Control received (continuing anyway)"));
  }

  // ISO-TP Consecutive Frame 1 (seq=1): remaining 4 bytes of payload
  byte cf1[8];
  cf1[0] = 0x21;  // CF seq 1
  cf1[1] = payload[6];
  cf1[2] = payload[7];
  cf1[3] = payload[8];
  cf1[4] = payload[9];
  cf1[5] = 0x00;
  cf1[6] = 0x00;
  cf1[7] = 0x00;

  // Respect STmin if provided
  if (stmin_ms > 0) {
    delay(stmin_ms);
  } else {
    delay(5);
  }

  CAN.sendMsgBuf(OBD2_RESPONSE_ID, 0, 8, cf1);

  if (DEBUG_MODE) {
    SERIAL_PORT_MONITOR.print(F("→ ISO-TP CF1 (DTC): ID 0x"));
    SERIAL_PORT_MONITOR.print(OBD2_RESPONSE_ID, HEX);
    SERIAL_PORT_MONITOR.print(F(" ["));
    for (int i = 0; i < 8; i++) {
      if (cf1[i] < 0x10) SERIAL_PORT_MONITOR.print(F("0"));
      SERIAL_PORT_MONITOR.print(cf1[i], HEX);
      if (i < 7) SERIAL_PORT_MONITOR.print(F(" "));
    }
    SERIAL_PORT_MONITOR.println(F("]"));
    SERIAL_PORT_MONITOR.println(F("  ✓ DTCs sent (ISO-TP): P0171, P0300, C0035, B1234"));
  }
}

// Handle Service 04: Clear Diagnostic Trouble Codes
// Real ECUs may or may not reply. For bench testing we send an ACK-like response.
static void handle_clear_dtcs_request() {
  // Response format (common): [Len, 0x44, 0x00, ...padding]
  byte response[8];
  response[0] = 0x01;  // Length (just the service byte)
  response[1] = 0x44;  // Service 04 response (0x04 + 0x40)
  for (int i = 2; i < 8; i++) response[i] = 0x00;

  CAN.sendMsgBuf(OBD2_RESPONSE_ID, 0, 8, response);
  response_count++;

  if (DEBUG_MODE) {
    SERIAL_PORT_MONITOR.print(F("→ Response: Clear DTCs (Service 04 ACK) ID 0x"));
    SERIAL_PORT_MONITOR.print(OBD2_RESPONSE_ID, HEX);
    SERIAL_PORT_MONITOR.print(F(" ["));
    for (int i = 0; i < 8; i++) {
      if (response[i] < 0x10) SERIAL_PORT_MONITOR.print(F("0"));
      SERIAL_PORT_MONITOR.print(response[i], HEX);
      if (i < 7) SERIAL_PORT_MONITOR.print(F(" "));
    }
    SERIAL_PORT_MONITOR.println(F("]"));
  }
}

// ============================================================================
// SERVICE 09 (VEHICLE INFORMATION) - VIN (PID 0x02)
// ============================================================================

static bool wait_for_isotp_flow_control(uint16_t &out_stmin_ms) {
  // ISO-TP FC: 0x30 (Continue to send), BS, STmin, ...
  const unsigned long timeout_ms = 60;
  unsigned long start = millis();

  while (millis() - start < timeout_ms) {
    if (CAN_MSGAVAIL == CAN.checkReceive()) {
      unsigned long id;
      byte len;
      byte buf[MAX_DATA_SIZE];

      CAN.readMsgBuf(&len, buf);
      id = CAN.getCanId();

      if (len >= 3 && (id == OBD2_PHYSICAL_REQUEST_ID || id == OBD2_REQUEST_ID)) {
        if ((buf[0] & 0xF0) == 0x30) {
          uint8_t stmin = buf[2];
          // STmin 0x00-0x7F = milliseconds. Other encodings ignored for simplicity.
          out_stmin_ms = (stmin <= 0x7F) ? stmin : 0;
          return true;
        }
      }
    }
    delay(1);
  }

  return false;
}

static void handle_vin_request() {
  // VIN response payload (without ISO-TP PCI):
  // 0x49, 0x02, 0x01, then 17 ASCII chars.
  // Total payload length = 3 + 17 = 20 (0x14) bytes -> 1 FF + 2 CF.
  const uint8_t payload_len = 0x14;

  // Ensure we always transmit exactly 17 bytes (pad with spaces if shorter).
  char vin[17];
  for (int i = 0; i < 17; i++) vin[i] = ' ';
  for (int i = 0; i < 17 && VIN_STRING[i] != '\0'; i++) vin[i] = VIN_STRING[i];

  uint8_t payload[0x14];
  payload[0] = 0x49;  // 0x09 + 0x40
  payload[1] = 0x02;  // PID 0x02 (VIN)
  payload[2] = 0x01;  // VIN message count / frame index (common: 0x01)
  for (int i = 0; i < 17; i++) {
    payload[3 + i] = (uint8_t)vin[i];
  }

  if (DEBUG_MODE) {
    SERIAL_PORT_MONITOR.print(F("  → Sending VIN (Mode 09 PID 02): "));
    for (int i = 0; i < 17; i++) SERIAL_PORT_MONITOR.print(vin[i]);
    SERIAL_PORT_MONITOR.println();
  }

  // First Frame (FF): [0x10 | (len >> 8), len, payload[0..5]]
  byte ff[8];
  ff[0] = 0x10 | ((payload_len >> 8) & 0x0F);
  ff[1] = payload_len & 0xFF;
  for (int i = 0; i < 6; i++) ff[2 + i] = payload[i];
  CAN.sendMsgBuf(OBD2_RESPONSE_ID, 0, 8, ff);

  // Wait for Flow Control (best-effort). If none arrives, continue with a safe delay.
  uint16_t stmin_ms = 5;
  uint16_t stmin_from_fc = 0;
  if (wait_for_isotp_flow_control(stmin_from_fc)) {
    stmin_ms = stmin_from_fc;
  }
  if (stmin_ms < 1) stmin_ms = 1;

  // Consecutive Frame 1 (CF1): [0x21, payload[6..12]]
  delay(stmin_ms);
  byte cf1[8];
  cf1[0] = 0x21;
  for (int i = 0; i < 7; i++) cf1[1 + i] = payload[6 + i];
  CAN.sendMsgBuf(OBD2_RESPONSE_ID, 0, 8, cf1);

  // Consecutive Frame 2 (CF2): [0x22, payload[13..19]]
  delay(stmin_ms);
  byte cf2[8];
  cf2[0] = 0x22;
  for (int i = 0; i < 7; i++) cf2[1 + i] = payload[13 + i];
  CAN.sendMsgBuf(OBD2_RESPONSE_ID, 0, 8, cf2);

  response_count++;

  if (DEBUG_MODE) {
    SERIAL_PORT_MONITOR.println(F("  ✓ VIN sent (ISO-TP multi-frame)"));
  }
}

void handle_obd2_request(byte *request, byte len) {
  // OBD-II request format: [Length, Service, PID, ...]
  uint8_t length = request[0];
  uint8_t service = request[1];
  uint8_t pid = (len > 2) ? request[2] : 0x00;
  
  if (DEBUG_MODE) {
    SERIAL_PORT_MONITOR.print(F("← Request: Service 0x"));
    if (service < 0x10) SERIAL_PORT_MONITOR.print(F("0"));
    SERIAL_PORT_MONITOR.print(service, HEX);
    if (service == 0x01 || service == 0x09) {
      SERIAL_PORT_MONITOR.print(F(", PID 0x"));
      if (pid < 0x10) SERIAL_PORT_MONITOR.print(F("0"));
      SERIAL_PORT_MONITOR.print(pid, HEX);
    }
    SERIAL_PORT_MONITOR.println();
  }
  
  // Handle Service 03 (Read DTCs)
  if (service == 0x03) {
    handle_dtc_request();
    return;
  }

  // Handle Service 04 (Clear DTCs)
  if (service == 0x04) {
    handle_clear_dtcs_request();
    return;
  }

  // Handle Service 09 (Vehicle information) - VIN
  if (service == 0x09) {
    if (pid == 0x02) {
      handle_vin_request();
    } else if (DEBUG_MODE) {
      SERIAL_PORT_MONITOR.println(F("  ✗ Unsupported Service 09 PID"));
    }
    return;
  }
  
  // Only handle Service 01 (Show current data)
  if (service != 0x01) {
    if (DEBUG_MODE) {
      SERIAL_PORT_MONITOR.println(F("  ✗ Unsupported service"));
    }
    return;
  }
  
  // Prepare response buffer
  byte response[8];
  response[1] = 0x41;  // Service 01 response (0x01 + 0x40)
  response[2] = pid;
  
  // Fill remaining bytes with zeros
  for (int i = 3; i < 8; i++) {
    response[i] = 0x00;
  }
  
  // Fill response based on PID
  bool pid_supported = true;
  
  switch (pid) {
    case 0x00:  // PIDs supported [01-20]
      response[0] = 0x06;  // Length
      // Bitfield: Support PIDs 0x04, 0x05, 0x0C, 0x0D, 0x0F, 0x10, 0x11
      response[3] = 0xBE;  // 10111110
      response[4] = 0x1F;  // 00011111
      response[5] = 0xA8;  // 10101000
      response[6] = 0x13;  // 00010011
      break;
      
    case 0x04:  // Engine Load (%)
      response[0] = 0x03;  // Length
      response[3] = (uint8_t)((engine.load / 100.0) * 255.0);
      break;
      
    case 0x05:  // Coolant Temperature (°C)
      response[0] = 0x03;  // Length
      response[3] = (uint8_t)(engine.coolant_temp + 40);
      break;
      
    case 0x0C:  // Engine RPM
      response[0] = 0x04;  // Length
      {
        uint16_t rpm_raw = (uint16_t)(engine.rpm * 4.0);
        response[3] = rpm_raw >> 8;    // MSB
        response[4] = rpm_raw & 0xFF;  // LSB
      }
      break;
      
    case 0x0D:  // Vehicle Speed (km/h)
      response[0] = 0x03;  // Length
      response[3] = (uint8_t)engine.speed;
      break;
      
    case 0x0F:  // Intake Air Temperature (°C)
      response[0] = 0x03;  // Length
      response[3] = (uint8_t)(engine.intake_temp + 40);
      break;
      
    case 0x10:  // MAF Air Flow (g/s)
      response[0] = 0x04;  // Length
      {
        uint16_t maf_raw = (uint16_t)(engine.maf * 100.0);
        response[3] = maf_raw >> 8;
        response[4] = maf_raw & 0xFF;
      }
      break;
      
    case 0x11:  // Throttle Position (%)
      response[0] = 0x03;  // Length
      response[3] = (uint8_t)((engine.throttle / 100.0) * 255.0);
      break;
      
    case 0x2F:  // Fuel Level (%)
      response[0] = 0x03;  // Length
      response[3] = (uint8_t)((engine.fuel_level / 100.0) * 255.0);
      break;
      
    case 0x42:  // Control Module Voltage (V)
      response[0] = 0x04;  // Length
      {
        uint16_t voltage_raw = (uint16_t)(engine.voltage * 1000.0);
        response[3] = voltage_raw >> 8;
        response[4] = voltage_raw & 0xFF;
      }
      break;
      
    case 0x46:  // Ambient Air Temperature (°C)
      response[0] = 0x03;  // Length
      response[3] = (uint8_t)(engine.ambient_temp + 40);
      break;
      
    case 0x5C:  // Engine Oil Temperature (°C)
      response[0] = 0x03;  // Length
      response[3] = (uint8_t)(engine.oil_temp + 40);
      break;
      
    // Support PIDs - indicate no additional PIDs supported beyond 0x20
    case 0x20:  // PIDs supported [21-40]
      response[0] = 0x06;  // Length
      response[3] = 0x80;  // 10000000 - Only bit 31 set (indicates PID 0x21 = next support PID 0x40)
      response[4] = 0x00;  // No PIDs 0x22-0x29
      response[5] = 0x00;  // No PIDs 0x2A-0x31
      response[6] = 0x01;  // 00000001 - Bit 0 set (indicates PID 0x40 exists)
      break;
      
    case 0x40:  // PIDs supported [41-60]
      response[0] = 0x06;  // Length
      response[3] = 0x40;  // 01000000 - Support PID 0x42 and 0x46
      response[4] = 0x08;  // 00001000 - Support PID 0x4C
      response[5] = 0x00;  // No PIDs 0x4A-0x51
      response[6] = 0x10;  // 00010000 - Support PID 0x5C, bit 0 indicates PID 0x60 exists
      break;
      
    case 0x60:  // PIDs supported [61-80]
      response[0] = 0x06;  // Length
      response[3] = 0x00;  // No PIDs in this range
      response[4] = 0x00;
      response[5] = 0x00;
      response[6] = 0x00;  // Bit 0 = 0 means no more support PIDs
      break;
      
    default:
      pid_supported = false;
      if (DEBUG_MODE) {
        SERIAL_PORT_MONITOR.println(F("  ✗ PID not supported"));
      }
      break;
  }
  
  // Send response if PID is supported
  if (pid_supported) {
    // Send CAN message
    CAN.sendMsgBuf(OBD2_RESPONSE_ID, 0, 8, response);
    response_count++;
    
    if (DEBUG_MODE) {
      SERIAL_PORT_MONITOR.print(F("→ Response: ID 0x"));
      SERIAL_PORT_MONITOR.print(OBD2_RESPONSE_ID, HEX);
      SERIAL_PORT_MONITOR.print(F(" ["));
      for (int i = 0; i < 8; i++) {
        if (response[i] < 0x10) SERIAL_PORT_MONITOR.print(F("0"));
        SERIAL_PORT_MONITOR.print(response[i], HEX);
        if (i < 7) SERIAL_PORT_MONITOR.print(F(" "));
      }
      SERIAL_PORT_MONITOR.print(F("]"));
      
      print_decoded_value(pid);
      SERIAL_PORT_MONITOR.println();
      
      // Print statistics every 10 responses
      if (response_count % 10 == 0) {
        SERIAL_PORT_MONITOR.print(F("  Stats: Requests="));
        SERIAL_PORT_MONITOR.print(request_count);
        SERIAL_PORT_MONITOR.print(F(", Responses="));
        SERIAL_PORT_MONITOR.println(response_count);
      }
    }
  }
}

// ============================================================================
// DEBUG HELPERS
// ============================================================================

void print_decoded_value(uint8_t pid) {
  SERIAL_PORT_MONITOR.print(F("  Value: "));
  
  switch (pid) {
    case 0x00:
      SERIAL_PORT_MONITOR.print(F("PIDs supported"));
      break;
    case 0x04:
      SERIAL_PORT_MONITOR.print(engine.load, 1);
      SERIAL_PORT_MONITOR.print(F("%"));
      break;
    case 0x05:
      SERIAL_PORT_MONITOR.print(engine.coolant_temp, 1);
      SERIAL_PORT_MONITOR.print(F("°C"));
      break;
    case 0x0C:
      SERIAL_PORT_MONITOR.print(engine.rpm, 0);
      SERIAL_PORT_MONITOR.print(F(" RPM"));
      break;
    case 0x0D:
      SERIAL_PORT_MONITOR.print(engine.speed, 0);
      SERIAL_PORT_MONITOR.print(F(" km/h"));
      break;
    case 0x0F:
      SERIAL_PORT_MONITOR.print(engine.intake_temp, 1);
      SERIAL_PORT_MONITOR.print(F("°C"));
      break;
    case 0x10:
      SERIAL_PORT_MONITOR.print(engine.maf, 2);
      SERIAL_PORT_MONITOR.print(F(" g/s"));
      break;
    case 0x11:
      SERIAL_PORT_MONITOR.print(engine.throttle, 1);
      SERIAL_PORT_MONITOR.print(F("%"));
      break;
    case 0x2F:
      SERIAL_PORT_MONITOR.print(engine.fuel_level, 1);
      SERIAL_PORT_MONITOR.print(F("%"));
      break;
    case 0x42:
      SERIAL_PORT_MONITOR.print(engine.voltage, 2);
      SERIAL_PORT_MONITOR.print(F("V"));
      break;
    case 0x46:
      SERIAL_PORT_MONITOR.print(engine.ambient_temp, 1);
      SERIAL_PORT_MONITOR.print(F("°C"));
      break;
    case 0x5C:
      SERIAL_PORT_MONITOR.print(engine.oil_temp, 1);
      SERIAL_PORT_MONITOR.print(F("°C"));
      break;
  }
}

// END FILE
