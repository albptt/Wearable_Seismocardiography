/* ========================================
 *
 * Politecnico di Milano 
 * LTEBS A.Y. 2023/24 
 * Mentasti, Pettenella, Salama, Vacca
 *
 * ========================================
*/

// Include header files
#include "global_variables.h"
#include "InterruptRoutines.h"
#include <stdlib.h>
#include "..\Oled-Psoc5\OLED.cydsn\ssd1306.h" // Oled-Psoc5 folder has to be cloned from the GitHub repository
// OLED display address
#define DISPLAY_ADDRESS 0x3D // 011110+SA0+RW - 0x3C or 0x3D 
// Define EEPROM variables
#define WRITE_EEPROM 0
#define R_LED_EEPROM_ADDRESS 0x00
#define G_LED_EEPROM_ADDRESS 0x01
#define B_LED_EEPROM_ADDRESS 0x02
#define BUZZ_EEPROM_ADDRESS 0x03
#define OLED_EEPROM_ADDRESS 0x04
#define OLED_STRING 0
// Define configuration variables
#define FIFO_REG_BYPASS 0x00
#define FIFO_REG_STREAM 0x80
#define OVR_INT_ENABLE 0x02
#define FIFO_ENABLE 0x40
#define ODR_AX_ENABLE 0x47
// String to print out messages over UART
char message[100] = {'\0'};
// startup strings
char *stringList_1[] = {
        "HeART",
        "START"       
    };
char *stringList_2[] = {
        "ATTACK",
        "DEVICE"
    };

int main(void)
{   
    // Enable Global Interrupts
    CyGlobalIntEnable; 
    
    // Configure Peripherals
    I2C_Peripheral_Start();
    UART_1_Start();
    isr_stream_1_StartEx(Custom_ISR_RX);
    display_init(DISPLAY_ADDRESS); 
    EEPROM_Start();
    
    // Enable Timers
    Timer_3_Init();
    Timer_3_Enable();
    Timer_30_Init();
    Timer_30_Enable();
    Timer_1H_Init();
    Timer_1H_Enable();
    
    // Enable Counters
    isr_Counter_3_StartEx(Custom_ISR_Counter_3);
    isr_Counter_30_StartEx(Custom_ISR_Counter_30);
    isr_Counter_1H_StartEx(Custom_ISR_Counter_1H);
    
    // Allow for boot procedure to complete
    CyDelay(5); 
    
    // Write EEPROM if needed
    if (WRITE_EEPROM)
    {   
        // Update Temperature to optimize WRITE operation
        EEPROM_UpdateTemperature();
        // Write initial LED states
        EEPROM_WriteByte(LOW,R_LED_EEPROM_ADDRESS);
        EEPROM_WriteByte(LOW,G_LED_EEPROM_ADDRESS);
        EEPROM_WriteByte(LOW,B_LED_EEPROM_ADDRESS);
        // Write initial BUZZ state
        EEPROM_WriteByte(LOW,BUZZ_EEPROM_ADDRESS);
        // Write initial OLED string
        EEPROM_WriteByte(OLED_STRING,OLED_EEPROM_ADDRESS);
        // Write accelerometer bit resolution 
        bit_resolution = NORMAL;
        EEPROM_WriteByte(bit_resolution,BIT_RESOLUTION_ADDRESS);
        // Write accelerometer g resolution
        g_resolution = 0;
        EEPROM_WriteByte(g_resolution,G_RESOLUTION_ADDRESS);
        // Write power state of device
        power_mode = NORMAL;
        EEPROM_WriteByte(g_resolution,POWER_ADDRESS);
    }
    
    // Set initial LED state
    LED_R_Write(EEPROM_ReadByte(R_LED_EEPROM_ADDRESS));
    LED_G_Write(EEPROM_ReadByte(G_LED_EEPROM_ADDRESS));
    LED_B_Write(EEPROM_ReadByte(B_LED_EEPROM_ADDRESS));
    
    // Write Startup String on the OLED
    update_oled(stringList_1[EEPROM_ReadByte(OLED_EEPROM_ADDRESS)], stringList_2[EEPROM_ReadByte(OLED_EEPROM_ADDRESS)], 40, 20, 35, 40);
    
    // Configure FIFO_CTRL_REG
    // Ensure Bypass mode is selected
    
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS,
                                         LIS3DH_FIFO_CTRL_REG,
                                         FIFO_REG_BYPASS);
    
    /*
    // Device 2
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS_2,
                                         LIS3DH_FIFO_CTRL_REG,
                                         FIFO_REG_BYPASS);
    */
        
    // Configure CTRL_REG2
    // Nothing to configure for the current operating mode
    
    // Configure CTRL_REG3
    // Enable interrupt (INT1) on FIFO overrun
    
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS,
                                         LIS3DH_CTRL_REG3,
                                         OVR_INT_ENABLE);
    /*
    // Device 2
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS_2,
                                         LIS3DH_CTRL_REG3,
                                         OVR_INT_ENABLE);
    */
    
    // Configure CTRL_REG4
    // Select g resolution from EEPROM
    
    CtrlReg4Config = EEPROM_ReadByte(G_RESOLUTION_ADDRESS);
    
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS,
                                         LIS3DH_CTRL_REG4,
                                         CtrlReg4Config);
    
    /*
    // Device 2
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS_2,
                                         LIS3DH_CTRL_REG4,
                                         CtrlReg4Config);
    */
    
    // Configure CTRL_REG5
    // Enable FIFO 
    
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS,
                                         LIS3DH_CTRL_REG5,
                                         FIFO_ENABLE);
    
    /*
    // Device 2
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS_2,
                                         LIS3DH_CTRL_REG5,
                                         FIFO_ENABLE);
    */
    
    // Configure CTRL_REG6
    // Nothing to configure for the current operating mode
    
    // Configure CTRL_REG1
    // Initialize from memory to 0x00
    
    CtrlReg1Config &= EEPROM_ReadByte(POWER_ADDRESS);
    
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS,
                                         LIS3DH_CTRL_REG1,
                                         CtrlReg1Config);
    
    /*
    // Device 2
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS_2,
                                         LIS3DH_CTRL_REG1,
                                         CtrlReg1Config);
    */
    
    // Now configure ODR and enable X, Y and Z axes
    // Select data rate: 50Hz -> CtrlReg1Config |= 0x47;
    // Select data rate: 200Hz -> CtrlReg1Config |= 0x67;
    // Select data rate: 400Hz -> CtrlReg1Config |= 0x77;
    
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS,
                                         LIS3DH_CTRL_REG1,
                                         ODR_AX_ENABLE);
    /*
    // Device 2
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS_2,
                                         LIS3DH_CTRL_REG1,
                                         ODR_AX_ENABLE);
    */
    
    // Enable Interrupts for the accelerometers
    isr_acc_1_StartEx(custom_acc_1_Interrupt);
    
    /*
    isr_acc_2_StartEx(custom_acc_2_Interrupt);
    */
    
    // Enable stream mode

    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS,
                                         LIS3DH_FIFO_CTRL_REG,
                                         FIFO_REG_STREAM);
    
    /*
    // Device 2
    error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS_2,
                                         LIS3DH_FIFO_CTRL_REG,
                                         FIFO_REG_STREAM);
    */
    
    // Configure Timers and ADC
    Timer_1H_Start();
    uint16 start_counter_bat=10;
    // Battery is initialized = 100%, but after 10 seconds from reset the battery is read
    Timer_1H_WriteCounter(start_counter_bat); 
    ADC_DelSig_Start();
    
    // Start PWM for LED_R to signal lack of connection
    PWM_LED_Start(); 
    
    // Set ALARM_ENABLE flag
    ALARM_ENABLED=1;

    for(;;){
    }   
}
    
    

