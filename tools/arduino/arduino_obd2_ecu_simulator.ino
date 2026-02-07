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
const int SPI_CS_PIN = 9;
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

// Simulation Parameters
#define ENGINE_IDLE_RPM 800        // Idle RPM
#define ENGINE_MAX_RPM 6000        // Maximum RPM
#define SIMULATION_SPEED 50        // Update speed (ms)

// Debug Mode (set to true to enable Serial debug output)
#define DEBUG_MODE true

// ============================================================================
// GLOBAL VARIABLES
// ============================================================================

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
  
  while (CAN_OK != CAN.begin(CAN_500KBPS)) {
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
    
    // Check if it's an OBD-II request
    if (id == OBD2_REQUEST_ID && len >= 2) {
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
  
  // Response format: [Length, 0x43 (Service 03 response), Num DTCs, DTC1_H, DTC1_L, DTC2_H, DTC2_L, ...]
  byte response[8];
  response[0] = 0x06;  // Length: 6 bytes (service + count + 4 DTCs * 2 bytes, but limited to 8 total)
  response[1] = 0x43;  // Service 03 response (0x03 + 0x40)
  response[2] = 0x04;  // Number of DTCs: 4
  
  // DTC 1: P0171 - System Too Lean (Bank 1)
  // P = 00, 0171 = 0x0171
  response[3] = 0x01;  // High byte: 00 (P) + 01
  response[4] = 0x71;  // Low byte: 71
  
  // DTC 2: P0300 - Random/Multiple Cylinder Misfire Detected
  // P = 00, 0300 = 0x0300
  response[5] = 0x03;  // High byte: 00 (P) + 03
  response[6] = 0x00;  // Low byte: 00
  
  // DTC 3: C0035 - Left Front Wheel Speed Sensor Circuit (chassis)
  // C = 01, 0035 = 0x0035
  response[7] = 0x40;  // High byte: 01 (C) + 00
  
  // Send first CAN frame with DTCs 1-2 and part of DTC 3
  CAN.sendMsgBuf(OBD2_RESPONSE_ID, 0, 8, response);
  
  if (DEBUG_MODE) {
    SERIAL_PORT_MONITOR.print(F("→ Response: ID 0x"));
    SERIAL_PORT_MONITOR.print(OBD2_RESPONSE_ID, HEX);
    SERIAL_PORT_MONITOR.print(F(" ["));
    for (int i = 0; i < 8; i++) {
      if (response[i] < 0x10) SERIAL_PORT_MONITOR.print(F("0"));
      SERIAL_PORT_MONITOR.print(response[i], HEX);
      if (i < 7) SERIAL_PORT_MONITOR.print(F(" "));
    }
    SERIAL_PORT_MONITOR.println(F("]"));
  }
  
  // Send second frame with remaining DTCs
  delay(5);  // Small delay between frames
  
  byte response2[8];
  response2[0] = 0x04;  // Continuation
  response2[1] = 0x35;  // DTC 3 low byte
  
  // DTC 4: B1234 - Example Body Code
  // B = 10, 1234 = 0x1234
  response2[2] = 0x92;  // High byte: 10 (B) + 12
  response2[3] = 0x34;  // Low byte: 34
  
  // Fill remaining with padding
  for (int i = 4; i < 8; i++) {
    response2[i] = 0x00;
  }
  
  CAN.sendMsgBuf(OBD2_RESPONSE_ID, 0, 8, response2);
  
  if (DEBUG_MODE) {
    SERIAL_PORT_MONITOR.print(F("→ Response: ID 0x"));
    SERIAL_PORT_MONITOR.print(OBD2_RESPONSE_ID, HEX);
    SERIAL_PORT_MONITOR.print(F(" ["));
    for (int i = 0; i < 8; i++) {
      if (response2[i] < 0x10) SERIAL_PORT_MONITOR.print(F("0"));
      SERIAL_PORT_MONITOR.print(response2[i], HEX);
      if (i < 7) SERIAL_PORT_MONITOR.print(F(" "));
    }
    SERIAL_PORT_MONITOR.println(F("]"));
    SERIAL_PORT_MONITOR.println(F("  ✓ DTCs sent: P0171, P0300, C0035, B1234"));
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
    if (service == 0x01) {
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
