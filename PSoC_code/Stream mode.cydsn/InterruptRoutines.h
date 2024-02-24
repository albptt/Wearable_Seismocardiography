/* ========================================
 *
 * Politecnico di Milano 
 * LTEBS A.Y. 2023/24 
 * Mentasti, Pettenella, Salama, Vacca
 *
 * ========================================
*/

#ifndef __INTERRUPT_ROUTINES_H_
    #define __INTERRUPT_ROUTINES_H_
    
    // Include header files
    #include "LIS3DH.h"
    #include "project.h"
    #include "I2C_Interface.h"
    #include "ssd1306.h"
    
    // Declare isr prototypes
    CY_ISR_PROTO(custom_acc_1_Interrupt);
    CY_ISR_PROTO(custom_acc_2_Interrupt);
    CY_ISR_PROTO(Custom_ISR_RX);
    CY_ISR_PROTO(Custom_ISR_Counter_3);
    CY_ISR_PROTO(Custom_ISR_Counter_30);
    CY_ISR_PROTO(Custom_ISR_Counter_1H);
    
    // Declare function prototype
    void update_oled(char line_1[10], char line_2[10], int cursor_x_line1, int cursor_y_line1, int cursor_x_line2, int cursor_y_line2);
    
#endif

/* [] END OF FILE */
