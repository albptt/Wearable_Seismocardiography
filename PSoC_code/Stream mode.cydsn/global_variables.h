/* ========================================
 *
 * Politecnico di Milano 
 * LTEBS A.Y. 2023/24 
 * Mentasti, Pettenella, Salama, Vacca
 *
 * ========================================
*/

#ifndef SHARED_VARIABLES_H
    #define SHARED_VARIABLES_H
    
    // Declare global constants
    #define LOW_POWER 1
    #define NORMAL 0
    #define HIGH 1
    #define LOW 0
    #define BIT_RESOLUTION_ADDRESS 0X05
    #define G_RESOLUTION_ADDRESS 0X06
    #define POWER_ADDRESS 0x07
    
    // Include header files
    #include <stdio.h>
    #include "ErrorCodes.h"
    
    // Declare global variables;
    int ALARM_ENABLED;
    uint8_t bit_resolution; // NORMAL: 10bit, LOW_POWER: 8bit
    uint8_t g_resolution; // 0: +-2g, 1: +-4g
    uint8_t power_mode; // NORMAL: normal operating mode, LOW_POWER: low power mode
    uint8_t Bit_ResolutionBuffer[3];
    uint8_t G_ResolutionBuffer[3];
    uint8_t LowPowerBuffer[3];
    uint8_t CtrlReg1Config;
    uint8_t CtrlReg4Config;
    ErrorCode error;
    
#endif  // SHARED_VARIABLES_H
