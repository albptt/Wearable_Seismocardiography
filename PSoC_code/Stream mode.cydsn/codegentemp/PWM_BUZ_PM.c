/*******************************************************************************
* File Name: PWM_BUZ_PM.c
* Version 3.30
*
* Description:
*  This file provides the power management source code to API for the
*  PWM.
*
* Note:
*
********************************************************************************
* Copyright 2008-2014, Cypress Semiconductor Corporation.  All rights reserved.
* You may use this file only in accordance with the license, terms, conditions,
* disclaimers, and limitations in the end user license agreement accompanying
* the software package with which this file was provided.
*******************************************************************************/

#include "PWM_BUZ.h"

static PWM_BUZ_backupStruct PWM_BUZ_backup;


/*******************************************************************************
* Function Name: PWM_BUZ_SaveConfig
********************************************************************************
*
* Summary:
*  Saves the current user configuration of the component.
*
* Parameters:
*  None
*
* Return:
*  None
*
* Global variables:
*  PWM_BUZ_backup:  Variables of this global structure are modified to
*  store the values of non retention configuration registers when Sleep() API is
*  called.
*
*******************************************************************************/
void PWM_BUZ_SaveConfig(void) 
{

    #if(!PWM_BUZ_UsingFixedFunction)
        #if(!PWM_BUZ_PWMModeIsCenterAligned)
            PWM_BUZ_backup.PWMPeriod = PWM_BUZ_ReadPeriod();
        #endif /* (!PWM_BUZ_PWMModeIsCenterAligned) */
        PWM_BUZ_backup.PWMUdb = PWM_BUZ_ReadCounter();
        #if (PWM_BUZ_UseStatus)
            PWM_BUZ_backup.InterruptMaskValue = PWM_BUZ_STATUS_MASK;
        #endif /* (PWM_BUZ_UseStatus) */

        #if(PWM_BUZ_DeadBandMode == PWM_BUZ__B_PWM__DBM_256_CLOCKS || \
            PWM_BUZ_DeadBandMode == PWM_BUZ__B_PWM__DBM_2_4_CLOCKS)
            PWM_BUZ_backup.PWMdeadBandValue = PWM_BUZ_ReadDeadTime();
        #endif /*  deadband count is either 2-4 clocks or 256 clocks */

        #if(PWM_BUZ_KillModeMinTime)
             PWM_BUZ_backup.PWMKillCounterPeriod = PWM_BUZ_ReadKillTime();
        #endif /* (PWM_BUZ_KillModeMinTime) */

        #if(PWM_BUZ_UseControl)
            PWM_BUZ_backup.PWMControlRegister = PWM_BUZ_ReadControlRegister();
        #endif /* (PWM_BUZ_UseControl) */
    #endif  /* (!PWM_BUZ_UsingFixedFunction) */
}


/*******************************************************************************
* Function Name: PWM_BUZ_RestoreConfig
********************************************************************************
*
* Summary:
*  Restores the current user configuration of the component.
*
* Parameters:
*  None
*
* Return:
*  None
*
* Global variables:
*  PWM_BUZ_backup:  Variables of this global structure are used to
*  restore the values of non retention registers on wakeup from sleep mode.
*
*******************************************************************************/
void PWM_BUZ_RestoreConfig(void) 
{
        #if(!PWM_BUZ_UsingFixedFunction)
            #if(!PWM_BUZ_PWMModeIsCenterAligned)
                PWM_BUZ_WritePeriod(PWM_BUZ_backup.PWMPeriod);
            #endif /* (!PWM_BUZ_PWMModeIsCenterAligned) */

            PWM_BUZ_WriteCounter(PWM_BUZ_backup.PWMUdb);

            #if (PWM_BUZ_UseStatus)
                PWM_BUZ_STATUS_MASK = PWM_BUZ_backup.InterruptMaskValue;
            #endif /* (PWM_BUZ_UseStatus) */

            #if(PWM_BUZ_DeadBandMode == PWM_BUZ__B_PWM__DBM_256_CLOCKS || \
                PWM_BUZ_DeadBandMode == PWM_BUZ__B_PWM__DBM_2_4_CLOCKS)
                PWM_BUZ_WriteDeadTime(PWM_BUZ_backup.PWMdeadBandValue);
            #endif /* deadband count is either 2-4 clocks or 256 clocks */

            #if(PWM_BUZ_KillModeMinTime)
                PWM_BUZ_WriteKillTime(PWM_BUZ_backup.PWMKillCounterPeriod);
            #endif /* (PWM_BUZ_KillModeMinTime) */

            #if(PWM_BUZ_UseControl)
                PWM_BUZ_WriteControlRegister(PWM_BUZ_backup.PWMControlRegister);
            #endif /* (PWM_BUZ_UseControl) */
        #endif  /* (!PWM_BUZ_UsingFixedFunction) */
    }


/*******************************************************************************
* Function Name: PWM_BUZ_Sleep
********************************************************************************
*
* Summary:
*  Disables block's operation and saves the user configuration. Should be called
*  just prior to entering sleep.
*
* Parameters:
*  None
*
* Return:
*  None
*
* Global variables:
*  PWM_BUZ_backup.PWMEnableState:  Is modified depending on the enable
*  state of the block before entering sleep mode.
*
*******************************************************************************/
void PWM_BUZ_Sleep(void) 
{
    #if(PWM_BUZ_UseControl)
        if(PWM_BUZ_CTRL_ENABLE == (PWM_BUZ_CONTROL & PWM_BUZ_CTRL_ENABLE))
        {
            /*Component is enabled */
            PWM_BUZ_backup.PWMEnableState = 1u;
        }
        else
        {
            /* Component is disabled */
            PWM_BUZ_backup.PWMEnableState = 0u;
        }
    #endif /* (PWM_BUZ_UseControl) */

    /* Stop component */
    PWM_BUZ_Stop();

    /* Save registers configuration */
    PWM_BUZ_SaveConfig();
}


/*******************************************************************************
* Function Name: PWM_BUZ_Wakeup
********************************************************************************
*
* Summary:
*  Restores and enables the user configuration. Should be called just after
*  awaking from sleep.
*
* Parameters:
*  None
*
* Return:
*  None
*
* Global variables:
*  PWM_BUZ_backup.pwmEnable:  Is used to restore the enable state of
*  block on wakeup from sleep mode.
*
*******************************************************************************/
void PWM_BUZ_Wakeup(void) 
{
     /* Restore registers values */
    PWM_BUZ_RestoreConfig();

    if(PWM_BUZ_backup.PWMEnableState != 0u)
    {
        /* Enable component's operation */
        PWM_BUZ_Enable();
    } /* Do nothing if component's block was disabled before */

}


/* [] END OF FILE */
