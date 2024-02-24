/*******************************************************************************
* File Name: Timer_30_PM.c
* Version 2.80
*
*  Description:
*     This file provides the power management source code to API for the
*     Timer.
*
*   Note:
*     None
*
*******************************************************************************
* Copyright 2008-2017, Cypress Semiconductor Corporation.  All rights reserved.
* You may use this file only in accordance with the license, terms, conditions,
* disclaimers, and limitations in the end user license agreement accompanying
* the software package with which this file was provided.
********************************************************************************/

#include "Timer_30.h"

static Timer_30_backupStruct Timer_30_backup;


/*******************************************************************************
* Function Name: Timer_30_SaveConfig
********************************************************************************
*
* Summary:
*     Save the current user configuration
*
* Parameters:
*  void
*
* Return:
*  void
*
* Global variables:
*  Timer_30_backup:  Variables of this global structure are modified to
*  store the values of non retention configuration registers when Sleep() API is
*  called.
*
*******************************************************************************/
void Timer_30_SaveConfig(void) 
{
    #if (!Timer_30_UsingFixedFunction)
        Timer_30_backup.TimerUdb = Timer_30_ReadCounter();
        Timer_30_backup.InterruptMaskValue = Timer_30_STATUS_MASK;
        #if (Timer_30_UsingHWCaptureCounter)
            Timer_30_backup.TimerCaptureCounter = Timer_30_ReadCaptureCount();
        #endif /* Back Up capture counter register  */

        #if(!Timer_30_UDB_CONTROL_REG_REMOVED)
            Timer_30_backup.TimerControlRegister = Timer_30_ReadControlRegister();
        #endif /* Backup the enable state of the Timer component */
    #endif /* Backup non retention registers in UDB implementation. All fixed function registers are retention */
}


/*******************************************************************************
* Function Name: Timer_30_RestoreConfig
********************************************************************************
*
* Summary:
*  Restores the current user configuration.
*
* Parameters:
*  void
*
* Return:
*  void
*
* Global variables:
*  Timer_30_backup:  Variables of this global structure are used to
*  restore the values of non retention registers on wakeup from sleep mode.
*
*******************************************************************************/
void Timer_30_RestoreConfig(void) 
{   
    #if (!Timer_30_UsingFixedFunction)

        Timer_30_WriteCounter(Timer_30_backup.TimerUdb);
        Timer_30_STATUS_MASK =Timer_30_backup.InterruptMaskValue;
        #if (Timer_30_UsingHWCaptureCounter)
            Timer_30_SetCaptureCount(Timer_30_backup.TimerCaptureCounter);
        #endif /* Restore Capture counter register*/

        #if(!Timer_30_UDB_CONTROL_REG_REMOVED)
            Timer_30_WriteControlRegister(Timer_30_backup.TimerControlRegister);
        #endif /* Restore the enable state of the Timer component */
    #endif /* Restore non retention registers in the UDB implementation only */
}


/*******************************************************************************
* Function Name: Timer_30_Sleep
********************************************************************************
*
* Summary:
*     Stop and Save the user configuration
*
* Parameters:
*  void
*
* Return:
*  void
*
* Global variables:
*  Timer_30_backup.TimerEnableState:  Is modified depending on the
*  enable state of the block before entering sleep mode.
*
*******************************************************************************/
void Timer_30_Sleep(void) 
{
    #if(!Timer_30_UDB_CONTROL_REG_REMOVED)
        /* Save Counter's enable state */
        if(Timer_30_CTRL_ENABLE == (Timer_30_CONTROL & Timer_30_CTRL_ENABLE))
        {
            /* Timer is enabled */
            Timer_30_backup.TimerEnableState = 1u;
        }
        else
        {
            /* Timer is disabled */
            Timer_30_backup.TimerEnableState = 0u;
        }
    #endif /* Back up enable state from the Timer control register */
    Timer_30_Stop();
    Timer_30_SaveConfig();
}


/*******************************************************************************
* Function Name: Timer_30_Wakeup
********************************************************************************
*
* Summary:
*  Restores and enables the user configuration
*
* Parameters:
*  void
*
* Return:
*  void
*
* Global variables:
*  Timer_30_backup.enableState:  Is used to restore the enable state of
*  block on wakeup from sleep mode.
*
*******************************************************************************/
void Timer_30_Wakeup(void) 
{
    Timer_30_RestoreConfig();
    #if(!Timer_30_UDB_CONTROL_REG_REMOVED)
        if(Timer_30_backup.TimerEnableState == 1u)
        {     /* Enable Timer's operation */
                Timer_30_Enable();
        } /* Do nothing if Timer was disabled before */
    #endif /* Remove this code section if Control register is removed */
}


/* [] END OF FILE */
