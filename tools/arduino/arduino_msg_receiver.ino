/*
 * CAN Message Receiver for Testing
 * Receives and displays CAN messages from the Python analyzer
 * 
 * Features:
 * - Receives all CAN messages (Standard and Extended)
 * - Displays message details (ID, type, length, data)
 * - Shows message statistics (count, rate)
 * - Filters support (optional)
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

// Display settings
#define SHOW_TIMESTAMP     true    // Show timestamp for each message
#define SHOW_STATISTICS    true    // Show periodic statistics
#define STATS_INTERVAL     5000    // Statistics display interval (ms)

// Filter settings (optional)
#define USE_FILTER         false   // Enable ID filtering
#define FILTER_ID          0x100   // Only show messages with this ID
#define FILTER_MASK        0x7FF   // Mask for filtering (0x7FF = exact match for Standard)

// ============================================================================

// Statistics variables
unsigned long messageCount = 0;
unsigned long lastStatsTime = 0;
unsigned long lastMessageTime = 0;
unsigned long statsMessageCount = 0;

void setup() {
    SERIAL_PORT_MONITOR.begin(115200);
    while (!SERIAL_PORT_MONITOR) {}

    SERIAL_PORT_MONITOR.println(F("\n================================="));
    SERIAL_PORT_MONITOR.println(F("CAN Message Receiver for Testing"));
    SERIAL_PORT_MONITOR.println(F("=================================\n"));

    #if MAX_DATA_SIZE > 8
    CAN.setMode(CAN_NORMAL_MODE);
    #endif
    
    // Initialize CAN bus at 500 KBPS
    while (CAN_OK != CAN.begin(CAN_500KBPS)) {
        SERIAL_PORT_MONITOR.println(F("CAN init fail, retry..."));
        delay(100);
    }
    SERIAL_PORT_MONITOR.println(F("CAN init ok!"));

    // Set up filter if enabled
    if (USE_FILTER) {
        // Set filter to receive only specific ID
        // Mask 0: Standard IDs, Mask 1: Extended IDs
        CAN.init_Mask(0, 0, FILTER_MASK);
        CAN.init_Mask(1, 0, FILTER_MASK);
        CAN.init_Filt(0, 0, FILTER_ID);
        CAN.init_Filt(1, 0, FILTER_ID);
        
        SERIAL_PORT_MONITOR.print(F("Filter enabled: ID = 0x"));
        SERIAL_PORT_MONITOR.print(FILTER_ID, HEX);
        SERIAL_PORT_MONITOR.print(F(", Mask = 0x"));
        SERIAL_PORT_MONITOR.println(FILTER_MASK, HEX);
    } else {
        SERIAL_PORT_MONITOR.println(F("Filter disabled - receiving all messages"));
    }

    SERIAL_PORT_MONITOR.println(F("\nWaiting for CAN messages...\n"));
    SERIAL_PORT_MONITOR.println(F("Format: RX: [ID](TYPE) DATA"));
    SERIAL_PORT_MONITOR.println(F("  TYPE: 00=Std Data, 02=Ext Data, 30=Std Remote, 32=Ext Remote\n"));
    
    lastStatsTime = millis();
}

void displayMessage(unsigned long id, byte ext, byte rtr, byte len, byte *buf) {
    char prbuf[128];
    int n = 0;
    
    // Show timestamp if enabled
    if (SHOW_TIMESTAMP) {
        unsigned long timestamp = millis();
        n += sprintf(prbuf + n, "[%10lu] ", timestamp);
    }
    
    // Format type byte for display
    uint8_t typeDisplay = 0x00;
    if (ext) typeDisplay |= 0x02;  // Extended
    if (rtr) typeDisplay |= 0x30;  // Remote
    
    // Display message
    n += sprintf(prbuf + n, "RX: [%08lX](%02X) ", id, typeDisplay);
    
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

void displayStatistics() {
    unsigned long currentTime = millis();
    unsigned long elapsed = currentTime - lastStatsTime;
    
    if (elapsed >= STATS_INTERVAL) {
        float messagesPerSecond = (statsMessageCount * 1000.0) / elapsed;
        
        SERIAL_PORT_MONITOR.println(F("\n--- Statistics ---"));
        SERIAL_PORT_MONITOR.print(F("Total messages: "));
        SERIAL_PORT_MONITOR.println(messageCount);
        SERIAL_PORT_MONITOR.print(F("Messages/sec: "));
        SERIAL_PORT_MONITOR.println(messagesPerSecond, 2);
        SERIAL_PORT_MONITOR.print(F("Last message: "));
        SERIAL_PORT_MONITOR.print(currentTime - lastMessageTime);
        SERIAL_PORT_MONITOR.println(F(" ms ago"));
        SERIAL_PORT_MONITOR.println(F("------------------\n"));
        
        // Reset stats counters
        lastStatsTime = currentTime;
        statsMessageCount = 0;
    }
}

void loop() {
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
        
        // Update statistics
        messageCount++;
        statsMessageCount++;
        lastMessageTime = millis();
        
        // Display the message
        displayMessage(id, ext, rtr, len, buf);
    }
    
    // Display statistics periodically
    if (SHOW_STATISTICS) {
        displayStatistics();
    }
    
    // Small delay to avoid overwhelming the serial port
    delay(1);
}

// END FILE
