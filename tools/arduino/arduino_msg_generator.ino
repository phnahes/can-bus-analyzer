/*
 * CAN Message Generator for Testing
 * Simplified version with message groups
 * 
 * Features:
 * - Define multiple CAN messages with individual periods
 * - Support for Standard (11-bit) and Extended (29-bit) IDs
 * - Configurable data length and content
 * - Individual or sequential transmission modes
 * - Remote Frame support
 * 
 * Copyright (C) 2020 Seeed Technology Co.,Ltd.
 * Enhanced by phnahes - 2026
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
// CONFIGURATION - ADJUST HERE BEFORE UPLOAD
// ============================================================================

// Message structure:
// {ID, isExtended, isRemote, length, periodMs, {data bytes}}
//
// Parameters:
// - ID: CAN identifier (0x000-0x7FF for Standard, 0x000-0x1FFFFFFF for Extended)
// - isExtended: false = Standard (11-bit), true = Extended (29-bit)
// - isRemote: false = Data Frame, true = Remote Frame (requests data, doesn't send)
// - len (length): Number of data bytes (0-8)
// - periodMs: Transmission period in ms (0 = use DELAY_BETWEEN_MSGS)
// - data: Array of 8 bytes with message data
//
// Example simulating automotive ECU:
// - 0x100: Engine RPM (2 bytes) - sent every 10ms
// - 0x200: Vehicle Speed (2 bytes) - sent every 20ms
// - 0x300: Temperature (1 byte) - sent every 100ms
// - 0x400: Status (4 bytes) - sent every 50ms

struct CANMessage {
    uint32_t id;
    bool isExtended;
    bool isRemote;
    uint8_t len;
    uint16_t periodMs;      // Individual period (0 = use default)
    byte data[8];
};

// Define your messages here
CANMessage messageGroup[] = {
    // ID,    Ext,   Rem,  Len, Period, {Data bytes}
    {0x100, false, false,  2,   100,    {0x10, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // RPM - 10ms
    {0x200, false, false,  2,   200,    {0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Speed - 20ms
    {0x300, false, false,  1,   1000,   {0x5A, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00}},  // Temp - 100ms
    {0x400, false, false,  4,   500,    {0x01, 0x02, 0x03, 0x04, 0x00, 0x00, 0x00, 0x00}},  // Status - 50ms
};

#define MESSAGE_GROUP_SIZE (sizeof(messageGroup) / sizeof(CANMessage))

// Transmission mode
#define USE_INDIVIDUAL_PERIODS true   // true = each message uses its own period, false = sequential group transmission

// Reception mode
#define ENABLE_RECEIVE         true   // true = also receive and display incoming messages, false = transmit only

// Sequential mode: uses periodMs from each message as delay after sending it
// Individual mode: uses periodMs as the transmission period for each message independently

// ============================================================================

// Variables for individual period control
unsigned long lastSendTime[20] = {0};  // Supports up to 20 messages in group

// Variables for reception
unsigned long rxMessageCount = 0;

void setup() {
    SERIAL_PORT_MONITOR.begin(115200);
    while (!SERIAL_PORT_MONITOR) {}

    SERIAL_PORT_MONITOR.println(F("\n================================="));
    SERIAL_PORT_MONITOR.println(F("CAN Message Generator for Testing"));
    SERIAL_PORT_MONITOR.println(F("=================================\n"));

    #if MAX_DATA_SIZE > 8
    CAN.setMode(CAN_NORMAL_MODE);
    #endif
    
    while (CAN_OK != CAN.begin(CAN_500KBPS)) {
        SERIAL_PORT_MONITOR.println(F("CAN init fail, retry..."));
        delay(100);
    }
    SERIAL_PORT_MONITOR.println(F("CAN init ok!\n"));

    randomSeed(millis());
    
    printCurrentConfig();
    
    if (ENABLE_RECEIVE) {
        SERIAL_PORT_MONITOR.println(F("Reception enabled - will display incoming messages\n"));
    }
    
    SERIAL_PORT_MONITOR.println(F("Starting message transmission...\n"));
}

void printCurrentConfig() {
    SERIAL_PORT_MONITOR.println(F("--- Configuration ---"));
    SERIAL_PORT_MONITOR.print(F("Group Size: "));
    SERIAL_PORT_MONITOR.print(MESSAGE_GROUP_SIZE);
    SERIAL_PORT_MONITOR.println(F(" messages"));
    
    SERIAL_PORT_MONITOR.print(F("Transmission Mode: "));
    if (USE_INDIVIDUAL_PERIODS) {
        SERIAL_PORT_MONITOR.println(F("Individual Periods"));
        SERIAL_PORT_MONITOR.println(F("  (each message sent independently at its own period)"));
    } else {
        SERIAL_PORT_MONITOR.println(F("Sequential"));
        SERIAL_PORT_MONITOR.println(F("  (messages sent in sequence, periodMs = delay after each)"));
    }
    
    SERIAL_PORT_MONITOR.print(F("Reception: "));
    SERIAL_PORT_MONITOR.println(ENABLE_RECEIVE ? F("Enabled") : F("Disabled"));
    
    SERIAL_PORT_MONITOR.println(F("\nMessages in group:"));
    for (int i = 0; i < MESSAGE_GROUP_SIZE; i++) {
        SERIAL_PORT_MONITOR.print(F("  ["));
        SERIAL_PORT_MONITOR.print(i + 1);
        SERIAL_PORT_MONITOR.print(F("] ID: 0x"));
        SERIAL_PORT_MONITOR.print(messageGroup[i].id, HEX);
        SERIAL_PORT_MONITOR.print(F(" ("));
        SERIAL_PORT_MONITOR.print(messageGroup[i].isExtended ? F("Ext") : F("Std"));
        SERIAL_PORT_MONITOR.print(F("), Len: "));
        SERIAL_PORT_MONITOR.print(messageGroup[i].len);
        
        if (messageGroup[i].isRemote) {
            SERIAL_PORT_MONITOR.print(F(", Remote"));
        }
        
        if (USE_INDIVIDUAL_PERIODS) {
            SERIAL_PORT_MONITOR.print(F(", Period: "));
            SERIAL_PORT_MONITOR.print(messageGroup[i].periodMs);
            SERIAL_PORT_MONITOR.print(F("ms"));
        }
        
        SERIAL_PORT_MONITOR.println();
    }
    
    SERIAL_PORT_MONITOR.println(F("---------------------\n"));
}

void sendSingleMessage(int index) {
    CANMessage* msg = &messageGroup[index];
    
    // Send message
    CAN.sendMsgBuf(msg->id, msg->isExtended, msg->isRemote, msg->len, msg->data);
    
    // Print message info
    char prbuf[32 + MAX_DATA_SIZE * 3];
    int n;
    
    // Format type byte for display
    uint8_t typeDisplay = 0x00;
    if (msg->isExtended) typeDisplay |= 0x02;
    if (msg->isRemote) typeDisplay |= 0x30;
    
    n = sprintf(prbuf, "TX: [%08lX](%02X) ", (unsigned long)msg->id, typeDisplay);
    
    for (int j = 0; j < msg->len; j++) {
        n += sprintf(prbuf + n, "%02X ", msg->data[j]);
    }
    SERIAL_PORT_MONITOR.println(prbuf);
}

void sendSequentialGroup() {
    // Send all messages in sequence, using periodMs as delay after each message
    for (int i = 0; i < MESSAGE_GROUP_SIZE; i++) {
        sendSingleMessage(i);
        
        // Use message's periodMs as delay (default 10ms if 0)
        uint16_t delayTime = messageGroup[i].periodMs > 0 ? messageGroup[i].periodMs : 10;
        delay(delayTime);
    }
}

void sendIndividualPeriods() {
    unsigned long currentTime = millis();
    
    // Check each message and send if period has elapsed
    for (int i = 0; i < MESSAGE_GROUP_SIZE; i++) {
        uint16_t period = messageGroup[i].periodMs > 0 ? messageGroup[i].periodMs : 10;
        
        // Check if period has elapsed since last send
        if (currentTime - lastSendTime[i] >= period) {
            sendSingleMessage(i);
            lastSendTime[i] = currentTime;
        }
    }
}

void checkReceiveMessages() {
    // Check if there's a message available
    if (CAN_MSGAVAIL == CAN.checkReceive()) {
        unsigned long id;
        byte len;
        byte buf[MAX_DATA_SIZE];
        byte ext;
        byte rtr;
        
        // Read the message
        CAN.readMsgBuf(&len, buf);
        id = CAN.getCanId();
        ext = CAN.isExtendedFrame();
        rtr = CAN.isRemoteRequest();
        
        // Update counter
        rxMessageCount++;
        
        // Display the received message
        char prbuf[128];
        int n = 0;
        
        // Format type byte for display
        uint8_t typeDisplay = 0x00;
        if (ext) typeDisplay |= 0x02;  // Extended
        if (rtr) typeDisplay |= 0x30;  // Remote
        
        n = sprintf(prbuf, "RX: [%08lX](%02X) ", id, typeDisplay);
        
        // Display data bytes
        if (!rtr && len > 0) {
            for (int i = 0; i < len; i++) {
                n += sprintf(prbuf + n, "%02X ", buf[i]);
            }
        } else if (rtr) {
            n += sprintf(prbuf + n, "(Remote Frame - DLC=%d)", len);
        }
        
        SERIAL_PORT_MONITOR.println(prbuf);
    }
}

void loop() {
    // Check for incoming messages if reception is enabled
    if (ENABLE_RECEIVE) {
        checkReceiveMessages();
    }
    
    // Transmit messages
    if (USE_INDIVIDUAL_PERIODS) {
        // Individual period mode: each message has its own timing
        sendIndividualPeriods();
        delay(1);  // Small delay to avoid overloading the loop
    } else {
        // Sequential mode: send all messages in sequence
        sendSequentialGroup();
    }
}

// END FILE
