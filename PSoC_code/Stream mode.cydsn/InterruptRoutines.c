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
#include "stdlib.h"

// Define min battery value
#define BAT_MIN 3.3
// Define HR threshold for alarm
#define MAX_HR 120 
// Define size of data buffer
#define DATA_BUFFER_SIZE 194
#define RES_BUFFER_SIZE 3
// Define configuration variables
#define CTRL_REG1_LOW_POWER 0x08
#define CTRL_REG1_NORMAL_POWER 0xF7
#define CTRL_REG4_4G 0x10
#define CTRL_REG4_2G 0x00
// Initialize FIFO register configuration variable 
uint8_t FifoRegConfig;
// Initialize other auxiliary variables
char message[100];
ErrorCode error;
char ch_received; // Character to start and stop the streaming of data
char start_stream;
uint8 Number_mode = 0; 
int HR_received = 0; // HR value received by pc via bluetooth
char string_HR[10];
char string_bat[10]; 
char message[100];
char received_char;
// Declare initial Battery status
int32 battery_perc = 100; 
float32 battery_volt = 0;
// Initialize data buffer of 194 bytes (192 + header and tail) for device 1
uint8_t DataStream_1[DATA_BUFFER_SIZE];
uint8_t DataStream_2[DATA_BUFFER_SIZE];

CY_ISR(Custom_ISR_Counter_3)
{
    // Terminate buzzer sound
    PWM_BUZ_Stop();
    Timer_3_Stop();
    Timer_3_ReadStatusRegister();
    ALARM_ENABLED = 0;
    // Start refractory period for the buzzer
    Timer_30_Start();
}

CY_ISR(Custom_ISR_Counter_30)
{
    // Buzzer returns to triggerable mode
    Timer_30_Stop();
    Timer_30_ReadStatusRegister();
    ALARM_ENABLED = 1;
}

CY_ISR(Custom_ISR_Counter_1H)
{
    /* 
    When the battery is at 100% we should read 9V --> 5V  
    When the battery is at 0% we should read 6V --> 3.3V
    */
    
    // Read ADC to sample Battery and perform conversion
    battery_volt = ADC_DelSig_CountsTo_Volts(ADC_DelSig_Read32());
    battery_perc = ((battery_volt-BAT_MIN)*100)/(5-BAT_MIN);
    // Inform the ser via OLED
    sprintf(string_HR, "HR:%d", HR_received);
    sprintf(string_bat, "Bat:%ld%%", battery_perc);
    // Call the update function
    update_oled(string_HR, string_bat, 2, 20, 2, 40);
    
    Timer_1H_ReadStatusRegister();
    
    if(battery_perc<5 && ALARM_ENABLED==1){
        // Set high the ALARM and BATTERY_LOW flag
        PWM_BUZ_Start();
        Timer_3_Start();
        // Write on EEPROM LOW_POWER mode
        EEPROM_UpdateTemperature();
        bit_resolution = LOW_POWER;
        EEPROM_WriteByte(bit_resolution,BIT_RESOLUTION_ADDRESS);
        // Set LOW POWER MODE on the two devices
        CtrlReg1Config |= CTRL_REG1_LOW_POWER;
        // Device 1
        error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS,
                                         LIS3DH_CTRL_REG1,
                                         CtrlReg1Config);
    
        // Device 2
        /*
        error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS_2,
                                         LIS3DH_CTRL_REG1,
                                         CtrlReg1Config);
        */
        
        // Send new configuration via UART
        Bit_ResolutionBuffer[0] = 0xA3;
        Bit_ResolutionBuffer[1] = bit_resolution;
        Bit_ResolutionBuffer[2] = 0xC3;
        UART_1_PutArray(Bit_ResolutionBuffer, RES_BUFFER_SIZE);
        // Send LOW POWER MODE flag
        LowPowerBuffer[0] = 0xA4;
        LowPowerBuffer[1] = LOW_POWER;
        LowPowerBuffer[2] = 0xC4;
        UART_1_PutArray(LowPowerBuffer, RES_BUFFER_SIZE);
        // Change ALARM flag
        ALARM_ENABLED = 0;
    }
}

CY_ISR(Custom_ISR_RX){
    if(Number_mode == 0)
        ch_received = UART_1_GetChar();
    else
        ch_received = 'n';
        
    switch(ch_received){
        
        case 'v':
            start_stream = 0;
            // Stop red blinking LED
            PWM_LED_Stop();
            // Signal to the user that connection took place via LED
            LED_G_Write(LOW);
            LED_B_Write(HIGH);
            // Send message via UART
            sprintf(message, "Go $$$\r\n");
            UART_1_PutString(message); 
            break;
            
        case 'b':
            start_stream = 1;
            // Signal to the user that streaming is starting via LED
            LED_G_Write(HIGH);
            LED_B_Write(LOW);
            break;
            
        case 's':
            // Interrupt data stream
            start_stream = 0;
            // Signal to the user that the device is still connected via LED
            LED_G_Write(LOW);
            LED_B_Write(HIGH);
            break;
            
        case 'k':
            // Read configuration from EEPROM
            Bit_ResolutionBuffer[1] = EEPROM_ReadByte(BIT_RESOLUTION_ADDRESS);
            G_ResolutionBuffer[1] = EEPROM_ReadByte(G_RESOLUTION_ADDRESS);
            LowPowerBuffer[1] = EEPROM_ReadByte(POWER_ADDRESS);
            // Add header and tail to configuration buffers
            G_ResolutionBuffer[0] = 0xA2;
            G_ResolutionBuffer[2] = 0xC2;
            Bit_ResolutionBuffer[0] = 0xA3;
            Bit_ResolutionBuffer[2] = 0xC3;
            LowPowerBuffer[0] = 0xA4;
            LowPowerBuffer[2] = 0xC4;
            // Send Buffers via UART
            UART_1_PutArray(G_ResolutionBuffer, RES_BUFFER_SIZE);
            CyDelay(5);
            UART_1_PutArray(Bit_ResolutionBuffer, RES_BUFFER_SIZE);
            CyDelay(5);
            UART_1_PutArray(LowPowerBuffer, RES_BUFFER_SIZE);
            CyDelay(5);
            break;
            
        case 'h':
            Number_mode=1;
            break;
            
        case 'p': // bit resolution
            error = I2C_Peripheral_ReadRegister(LIS3DH_DEVICE_ADDRESS,LIS3DH_CTRL_REG1,&CtrlReg1Config);
            if(CtrlReg1Config & CTRL_REG1_LOW_POWER){ // we are in low power (8 bit)
                                        
                CtrlReg1Config &= CTRL_REG1_NORMAL_POWER;
                error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS,
                                        LIS3DH_CTRL_REG1,
                                        CtrlReg1Config); 
                /*
                error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS_2,
                                        LIS3DH_CTRL_REG1,
                                        CtrlReg1Config); 
                */
                bit_resolution = NORMAL;
            }
                
            else{ // we are in normal (10 bit)
                CtrlReg1Config |= CTRL_REG1_LOW_POWER;
                error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS,
                                        LIS3DH_CTRL_REG1,
                                        CtrlReg1Config); 
                /*
                error = I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS_2,
                                        LIS3DH_CTRL_REG1,
                                        CtrlReg1Config); 
                */
                bit_resolution = LOW_POWER;
            }
            // Write new settings on EEPROM
            EEPROM_UpdateTemperature();
            EEPROM_WriteByte(bit_resolution,BIT_RESOLUTION_ADDRESS);
            break;
            
        case 'g': // g resolution
            error = I2C_Peripheral_ReadRegister(LIS3DH_DEVICE_ADDRESS,LIS3DH_CTRL_REG4,&CtrlReg4Config);
            if(CtrlReg4Config & CTRL_REG4_4G){ // we are in 4g        
                CtrlReg4Config &= CTRL_REG4_2G;
                I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS,
                                         LIS3DH_CTRL_REG4,
                                         CtrlReg4Config);
                /*
                I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS_2,
                                         LIS3DH_CTRL_REG4,
                                         CtrlReg4Config); 
                */
                g_resolution = 0;
            }
            else{ // we are in 2g --> move to 4g
                CtrlReg4Config |= CTRL_REG4_4G;
                I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS,
                                         LIS3DH_CTRL_REG4,
                                         CtrlReg4Config);
                /*
                I2C_Peripheral_WriteRegister(LIS3DH_DEVICE_ADDRESS_2,
                                         LIS3DH_CTRL_REG4,
                                         CtrlReg4Config);  
                */
                g_resolution = 1;
            }
            // Write new settings on EEPROM
            EEPROM_UpdateTemperature();
            EEPROM_WriteByte(g_resolution,G_RESOLUTION_ADDRESS);
            break;
                        
        case 'n':
            // Check received HR value
            HR_received = (int)UART_1_GetChar();
            if(HR_received > MAX_HR && ALARM_ENABLED == 1){
                PWM_BUZ_Start();
                Timer_3_Start();
            }
            // Inform user via OLED
            sprintf(string_HR, "HR:%d", HR_received);
            sprintf(string_bat, "Bat:%ld%%", battery_perc);
            // Call update function
            update_oled(string_HR, string_bat, 2, 20, 2, 40);
            
            Number_mode = 0;  
            break;
            
        default:
            break;
    }
}

CY_ISR(custom_acc_1_Interrupt) // when the interrupt arrives on INT1, OVRN is high
{   
    // Read data in STREAM mode
    error = I2C_Peripheral_ReadRegisterMulti(LIS3DH_DEVICE_ADDRESS, OUT_X_L, DATA_BUFFER_SIZE-2, &DataStream_1[1]);

    // add header and tail to buffer
    DataStream_1[0] = 0xA0;
    DataStream_1[193] = 0xC0;
    if(start_stream)
        UART_1_PutArray(DataStream_1, DATA_BUFFER_SIZE);
}

// Function to wrap the OLED display update operations
void update_oled(char line_1[], char line_2[], int cursor_x_line1, int cursor_y_line1, int cursor_x_line2, int cursor_y_line2){
    display_clear();    
    display_update();    
    // Set title
    gfx_setTextSize(1);
    gfx_setTextColor(WHITE);
    gfx_setCursor(55,2);
    gfx_println("HEA");
    // Set cursor for line 1
    gfx_setTextSize(2);
    gfx_setCursor(cursor_x_line1, cursor_y_line1);
    gfx_println(line_1);
    // Set cursor for line 2
    gfx_setCursor(cursor_x_line2, cursor_y_line2);
    gfx_println(line_2);
    
    display_update(); 
}

/*
CY_ISR(custom_acc_2_Interrupt)
{
    // Read data in STREAM mode
    error = I2C_Peripheral_ReadRegisterMulti(LIS3DH_DEVICE_ADDRESS_2, OUT_X_L, 192, &DataStream_2[1]);
    
    // add header and tail to buffer
    DataStream_2[0] = 0xA1;
    DataStream_2[193] = 0xC1;
    if(start_stream)
        UART_1_PutArray(DataStream_2, 194);
}*/
/* [] END OF FILE */