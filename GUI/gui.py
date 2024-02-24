from PyQt5 import QtCore, QtGui, QtWidgets
import numpy as np
import scipy
import scipy.signal 
#import peakutils
#from peakutils import peak
#from peakutils.peak import find_peaks
#import threading
from pyqtgraph import PlotWidget
import sys
import time
import logging
import struct
import os

import pandas as pd 
import openpyxl
from openpyxl import Workbook 

from PyQt5 import QtCore
from PyQt5.QtCore import (
    QObject,
    QThreadPool, 
    QRunnable, 
    pyqtSignal, 
    pyqtSlot
)
from PyQt5.QtGui import QKeyEvent, QColor

from PyQt5.QtWidgets import (
    QMessageBox,
    QApplication,
    QMainWindow,
    QPushButton,
    QComboBox,
    QHBoxLayout,
    QWidget,
)

import serial
import serial.tools.list_ports

# Globals
CONN_STATUS = False
LINE_RECEIVED = False
KILL        = False
stop        = 1
calibration = 1
first_time = 1
recalibrate = 1

g_configuration = [2, 4]
bit_configuration = [10, 8]

LOW_BATTERY = False
G_RESOLUTION = 2
BIT_RESOLUTION = 10

# Logging config
logging.basicConfig(format="%(message)s", level=logging.INFO) 

#########################
# SERIAL_WORKER_SIGNALS # 
#########################
class SerialWorkerSignals(QObject): 
    """!
    @brief Class that defines the signals available to a serialworker.

    Available signals (with respective inputs) are:
        - device_port:
            str --> port name to which a device is connected
        - status:
            str --> port name
            int --> macro representing the state (0 - error during opening, 1 - success)
    """
    
    device_port = pyqtSignal(str) 
    status = pyqtSignal(str, int) 
    error_occurred = pyqtSignal(str) # signal needed to display the message boxes

#################
# SERIAL_WORKER #
#################
class SerialWorker(QRunnable): 
    """!
    @brief Main class for serial communication: handles connection with device.
    """
    
    def __init__(self, serial_port_name): 
        """!
        @brief Init worker.
        """
        global stop, calibration, first_time
        super().__init__()
        self.port = serial.Serial()
        self.port_name = serial_port_name 
        self.baudrate = 9600
        self.signals = SerialWorkerSignals()
        self.acc_tot = np.zeros(3000) 
        self.data_buffer_normalized = np.zeros(3000)
        self.data_buffer_normalized_abs = np.zeros(3000)

        self.count = 0
        self.ready = 0
        self.ready_processing = 0
        self.HR_vect = []
        self.buf_sampl = 0
        self.buf_sampl_processing = 0
        self.HR_int = 0
        self.HR_mean_raw = 0
        self.HR_mean = 0
        self.start_time = 0
        self.start_time2 = 0
        self.HR_sum_mean = 0
        self.count_mean = 0
                               
    @pyqtSlot() 
    def run(self): 
        """!
        @brief Establish connection with the desired serial port.
        """
        global CONN_STATUS 
        global BIT_RESOLUTION, G_RESOLUTION, LINE_RECEIVED
        global LOW_BATTERY
        global stop, calibration, first_time

        if not CONN_STATUS:
            try:
                self.port = serial.Serial(port=self.port_name, baudrate=self.baudrate,
                                        write_timeout=0, timeout=2)                
                if self.port.is_open:
                    sent_message = 'v\r\n'  # Include the expected line ending
                    print("Sending:", sent_message)
                    self.send('v')
                    time.sleep(1)
                    CONN_STATUS = True
                    try:
                        if self.port.in_waiting: # if the port has data in the buffer
                            print("Port in waiting")
                            line = self.port.readline().decode('utf').strip()
                            print("line:", line)
                            print(line == "Go $$$")
                            if line == "Go $$$": 
                                LINE_RECEIVED = True
                                first_time = 1
                                self.signals.status.emit(self.port_name, 1) 
                                time.sleep(0.01)
                                # Retrieve configuration from EEPROM
                                sent_message = 'k\r\n' 
                                print("Sending:", sent_message)
                                self.send('k')
                                time.sleep(0.5)
                            else:
                                LINE_RECEIVED = False
                        else:
                            self.signals.status.emit(self.port_name, 0)
                            print("Unexpected response from the device - change port or check device connection")
                            self.signals.error_occurred.emit("Unexpected response from the device - change port or check device connection")
                    except Exception as e:
                        self.signals.status.emit(self.port_name, 0)
                        logging.error("Error reading data from port {}: {}".format(self.port_name, str(e)))
                        self.signals.error_occurred.emit("Error reading data from {}. Please retry".format(self.port_name))
            except serial.SerialException:
                self.signals.status.emit(self.port_name, 0)
                logging.info("Error with port {}.".format(self.port_name)) 
                self.signals.error_occurred.emit("Error with port {}. Please retry".format(self.port_name))
                time.sleep(0.01)

        data_acc_1 = []
        data_acc_2 = []
        #create buffer
        buffer_size = 1500
        data_buffer = np.zeros(buffer_size)
        #### REQUIREMENTS: Read data from accelerometer ####
        while CONN_STATUS and LINE_RECEIVED:
            processing_flag = 0
            try:
                if self.port.in_waiting: # if the port has data in the buffer
                    header = self.port.read(1)
                    if header == b'\xA0':
                        data_acc_1.append(self.acquire_data(0xC0, 1))
                        flatten_data_acc_1 = [item for sublist1 in data_acc_1 for sublist2 in sublist1 for item in sublist2] # expand the nested list
                        sublists = [flatten_data_acc_1[i:i+3] for i in range(0, len(flatten_data_acc_1), 3)] # create sublists of 3 elements
                        sublists = np.array(sublists) # convert to numpy array
                        self.ready = 0
                        self.ready_processing = 0
                        processing_flag = 1 
                    if header == b'\xA1':
                        data_acc_2.append(self.acquire_data(0xC1, 2))
                        data_acc_2 = np.array(data_acc_2)
                    if header == b'\xA2':
                        g_res_bytes = self.port.read(1)
                        g_res = int.from_bytes(g_res_bytes, byteorder='big')
                        tail = self.port.read(1)
                        if tail == b'\xC2':                            
                            G_RESOLUTION = g_configuration[g_res]
                            print("G_RESOLUTION:", G_RESOLUTION)
                    if header == b'\xA3':
                        bit_res_bytes = self.port.read(1)
                        bit_res = int.from_bytes(bit_res_bytes, byteorder='big')
                        tail = self.port.read(1)
                        if tail == b'\xC3':
                            BIT_RESOLUTION = bit_configuration[bit_res]
                            print("BIT_RESOLUTION:", BIT_RESOLUTION)
                    if header == b'\xA4':
                        low_power_bytes = self.port.read(1)
                        low_power = int.from_bytes(low_power_bytes, byteorder='big')
                        tail = self.port.read(1)
                        if tail == b'\xC4':
                            LOW_BATTERY = low_power
                            if LOW_BATTERY:
                                print("LOW BATTERY POWER, PLEASE CHARGE THE DEVICE")        

                    if first_time == 1:
                        self.start_time = time.time()
                        first_time = 0
                        HR_sum_ist = 0
                        count_ist = 0
                    actual_time = time.time()  

                    if(actual_time - self.start_time > 45): # the calibration lasts 45 seconds; 
                        # afterwards, the calibration flag can be set to 0
                        calibration = 0   
                        self.start_time2 = time.time()
                        self.HR_sum_mean = 0
                        self.count_mean = 0
                        self.HR_mean_raw = 0
                        self.HR_mean = 0

                    # Implement code for processing and HR computation
                    if processing_flag:
                        self.buf_sampl += 32 # buf_sampl counts the number of samples of acc_tot from the last update of the graph; it's reset in update_plot
                        self.buf_sampl_processing += 32
                        self.count += 32

                        print("Processing data")
                        self.acc1_x = sublists[:,0].reshape(sublists.shape[0])
                        self.acc1_y = sublists[:,1].reshape(sublists.shape[0])
                        self.acc1_z = sublists[:,2].reshape(sublists.shape[0])
                        
                        self.acc_tot = self.acc1_z
                        self.count += 32 # count counts the total number of samples of acc_tot from the start of the acquisition
                        self.buf_sampl += 32 # buf_sampl counts the number of samples of acc_tot from the last update of the graph; it's reset in update_plot
                        self.ready = 1
                        
                        # HR computation
                        data_buffer[:-32] = data_buffer[32:] # update new_buffer skipping the previous 32 values
                        data_buffer[-32:] = self.acc1_z[-32:] # fill the last 32 values of new_buffer with the last values of acc1_z
                        
                        # Rectification
                        data_buffer_abs = np.abs(data_buffer)

                        # High pass filter with f_cutoff = 18 Hz
                        filter_order=4
                        normalized_cutoff_frequency=18/50
                        b, a = scipy.signal.butter(filter_order, normalized_cutoff_frequency, btype='high', analog=False, output='ba')
                        self.data_buffer_high = scipy.signal.lfilter(b, a, data_buffer_abs)

                        # Remove noisy samples
                        self.data_buffer_high=self.data_buffer_high[100:]

                        self.ready_processing = 1

                        # Normalization
                        self.data_buffer_normalized  = scipy.stats.zscore(self.data_buffer_high)

                        # Rectification
                        self.data_buffer_normalized_abs = np.abs(self.data_buffer_normalized)

                        # Energy based threshold
                        threshold =(np.std(np.square(self.data_buffer_normalized_abs)))*0.8

                        # Find peaks
                        peaks_filtered, _ = scipy.signal.find_peaks(self.data_buffer_normalized_abs, height=threshold, distance=25)

                        # HR computation basing on the time difference between peaks
                        interval_filtered = np.diff(peaks_filtered) / 50
                        HR_interval = 60 / np.mean(interval_filtered)

                        HR_sum_ist += HR_interval 
                        self.HR_sum_mean += HR_interval 
                        count_ist += 1 
                        self.count_mean += 1
                        
                        actual_time = time.time()     

                        # Every 5 seconds the istantaneous HR is computed as the mean HR of the 5s window 
                        if((actual_time - self.start_time >= 5) and (calibration == 0)):
                            HR_ist = HR_sum_ist / count_ist
                            self.HR_int = HR_ist.astype(int)
                            self.HR_vect.append(self.HR_int)
                            HR = bytes([self.HR_int & 0xFF])
                            letter = bytes([0x68]) # h
                            self.port.write(letter)
                            time.sleep(0.005)
                            self.port.write(HR)
                            first_time = 1
                            
                        # Every 60 seconds the mean HR is computed as the mean HR of the 60s window 
                        if((actual_time - self.start_time2 >= 60) and (calibration == 0)):
                            self.HR_mean_raw = self.HR_sum_mean / self.count_mean
                            self.HR_mean  = self.HR_mean_raw.astype(int)
                            self.HR_sum_mean = 0
                            self.count_mean = 0
                            self.start_time2 = time.time()
                                                           
                                         
            except Exception as e:
                logging.error("Device disconnected from port {}: {}".format(self.port_name, str(e)))
                self.signals.error_occurred.emit("Device disconnected from port {}".format(self.port_name))
                break
    #######################################################
        
    def acquire_data(self, tail_byte, ID_acc): # b'\xC0'
        all_integers = []
        data = self.port.read(192)
        tail = self.port.read(1)
        if tail == bytes([tail_byte]):
            # Define the format string for unpacking 32 levels of 6 bytes each
            format_string = '>{0}B'.format(6 * 32)
            # Unpack the data using struct.unpack
            unpacked_data = struct.unpack(format_string, data)
            # Extract x, y, z values from the unpacked data
            x_low = unpacked_data[0::6] # extract every 6th element starting from 0
            x_high = unpacked_data[1::6]
            y_low = unpacked_data[2::6]
            y_high = unpacked_data[3::6]
            z_low = unpacked_data[4::6] 
            z_high = unpacked_data[5::6] 
            
            for i in range(len(x_high)): # 32
                # Combine the higher-order and lower-order bits
                x_unsigned = ((x_high[i] << 8) | x_low[i]) >> (16-BIT_RESOLUTION)
                y_unsigned = ((y_high[i] << 8) | y_low[i]) >> (16-BIT_RESOLUTION)
                z_unsigned = ((z_high[i] << 8) | z_low[i]) >> (16-BIT_RESOLUTION)

                x_signed = x_unsigned - 2**BIT_RESOLUTION if x_unsigned >= 2**(BIT_RESOLUTION-1) else x_unsigned   
                y_signed = y_unsigned - 2**BIT_RESOLUTION if y_unsigned >= 2**(BIT_RESOLUTION-1) else y_unsigned  
                z_signed = z_unsigned - 2**BIT_RESOLUTION if z_unsigned >= 2**(BIT_RESOLUTION-1) else z_unsigned 

                x_conv = round(x_signed*((2*G_RESOLUTION)/(2**BIT_RESOLUTION))*9.81,4)
                y_conv = round(y_signed*((2*G_RESOLUTION)/(2**BIT_RESOLUTION))*9.81,4)
                z_conv = round(z_signed*((2*G_RESOLUTION)/(2**BIT_RESOLUTION))*9.81,4) 

                print(f"x_conv {ID_acc}:", x_conv, f"y_conv {ID_acc}:", y_conv, f"z_conv {ID_acc}:", z_conv)
                # print("G_RESOLUTION:", G_RESOLUTION)
                # print("BIT_RESOLUTION:", BIT_RESOLUTION)
                integers = [x_conv, y_conv, z_conv]
                all_integers.append(integers)
            all_integers = np.array(all_integers)
        return all_integers

    def savgol_filt(to_filter, order):
        return scipy.signal.savgol_filter(to_filter, order) #, window_length=500, deriv=0, delta=1.0, axis=-1, mode='interp', cval=0.0

    def bw_filter(data, sampling_freq):
        order = 5
        cutoff_lowf = 0.5
        cutoff_highf = 5
        b, a = scipy.signal.butter(N=order, Wn=[cutoff_lowf, cutoff_highf], btype='bandpass', analog=False, output='ba', fs=sampling_freq) # [cutoff_lowf, cutoff_highf]
        y_bwfilt = scipy.signal.lfilter(b=b, a=a, x=data)
        return y_bwfilt

    @pyqtSlot()
    def send(self, char):
        """!
        @brief Basic function to send a single char on serial port.
        """
        try:
            self.port.flushOutput()  # Clear the sent characters from the buffer
            self.port.write(char.encode('utf-8') + b'\r\n') 
            logging.info("Written {} on port {}.".format(char, self.port_name))
        except:
            logging.info("Could not write {} on port {}.".format(char, self.port_name))

    @pyqtSlot()
    def killed(self):
        """!
        @brief Close the serial port before closing the app.
        """
        global CONN_STATUS, LINE_RECEIVED
        global KILL

        if KILL and CONN_STATUS:
            self.port.close()
            time.sleep(0.01)
            CONN_STATUS = False 
            LINE_RECEIVED = False
            self.signals.device_port.emit(self.port_name)
            
        KILL = False 
        logging.info("Process killed") 

class SerialScanner(QObject):
    ports_updated = pyqtSignal(list) ###############

    def __init__(self):
        super().__init__()
    
    def scan(self):
        serial_ports = [port.device for port in serial.tools.list_ports.comports()]
        self.ports_updated.emit(serial_ports)
        time.sleep(0.1)

class Ui_MainWindow(object):#

    def __init__(self):
        """!
        @brief Init MainWindow.
        """
        global BIT_RESOLUTION, G_RESOLUTION, LOW_BATTERY
        global stop, calibration, recalibrate, first_time
        # define worker
        self.serial_worker = SerialWorker(None)
        super(Ui_MainWindow, self).__init__()

        # create thread handler
        self.threadpool = QThreadPool()
        self.connected = CONN_STATUS
        self.scan_clicked = 0
        self.start = 0 # set the start of the x-axis of the plot
        self.end = 0
        self.last_acq_time = np.inf
        self.vect_end = []
        self.serialscan()
        self.timer = QtCore.QTimer()
        self.timer.setInterval(1000) # timer to update plot is called every second
        self.timer.timeout.connect(lambda: self.is_acc_tot_ready(self.serial_worker.acc_tot, 
                                                                 self.serial_worker.data_buffer_normalized_abs, 
                                                                 self.serial_worker.ready, 
                                            self.serial_worker.ready_processing)) #self.serial_worker.data_buffer_filtered
        self.timer.start()

        self.timer_lcd_ist = QtCore.QTimer()
        self.timer_lcd_ist.setInterval(1000)
        self.timer_lcd_ist.timeout.connect(self.update_lcd_ist)
        self.timer_lcd_ist.start()

        self.timer_lcd_mean = QtCore.QTimer()
        self.timer_lcd_mean.setInterval(1000)
        self.timer_lcd_mean.timeout.connect(self.update_lcd_mean)
        self.timer_lcd_mean.start()

    def setupUi(self, MainWindow): #MainWindow
        MainWindow.setObjectName("MainWindow") 
        MainWindow.setFixedSize(1600, 950) #resize(826, 657)
        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        color = QColor(255, 230, 220)  # RGB
        self.centralwidget.setStyleSheet(f"background-color: {color.name()};")

        
        self.label_title = QtWidgets.QLabel(self.centralwidget)
        self.label_title.setGeometry(QtCore.QRect(400, 20, 830, 70))
        font = QtGui.QFont()
        font.setFamily(".SF Arabic Rounded")
        font.setPointSize(26)
        font.setBold(True)
        font.setWeight(75)
        self.label_title.setFont(font)
        self.label_title.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.label_title.setLineWidth(3)
        self.label_title.setScaledContents(True)
        self.label_title.setAlignment(QtCore.Qt.AlignCenter)
        self.label_title.setWordWrap(False)
        self.label_title.setObjectName("label_title")
        
        self.label = QtWidgets.QLabel(self.centralwidget)
        self.label.setGeometry(QtCore.QRect(530, 10, 80, 80))
        self.label.setText("")
        self.label.setPixmap(QtGui.QPixmap("../heart_title.png"))
        self.label.setScaledContents(True)
        self.label.setObjectName("label")
       
        self.layoutWidget_setting = QtWidgets.QWidget(self.centralwidget)
        self.layoutWidget_setting.setGeometry(QtCore.QRect(1200, 730, 350, 80))
        self.layoutWidget_setting.setObjectName("layoutWidget1")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget_setting)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout") 
        self.label_res = QtWidgets.QLabel(self.layoutWidget_setting)
        self.verticalLayout.addWidget(self.label_res)
        self.label_res.setText("Current full scale: ")
        self.label_fs = QtWidgets.QLabel(self.layoutWidget_setting)
        self.verticalLayout.addWidget(self.label_fs)
        self.label_fs.setText("Current resolution:  ")
        self.label_calibration = QtWidgets.QLabel(self.layoutWidget_setting)
        self.label_calibration.setFont(QtGui.QFont('Calibri', 14))
        self.verticalLayout.addWidget(self.label_calibration)
        font = QtGui.QFont('Calibri', 12)
        self.label_res.setFont(font)
        self.label_fs.setFont(font)
    
        self.graphicsView = PlotWidget(self.centralwidget)
        self.graphicsView.setGeometry(QtCore.QRect(50, 100, 1100, 600))
        self.graphicsView.setAutoFillBackground(False)
        self.graphicsView.setObjectName("graphicsView")


        self.layoutWidget = QtWidgets.QWidget(self.centralwidget)
        self.layoutWidget.setGeometry(QtCore.QRect(50, 730, 1100, 50))
        self.layoutWidget.setObjectName("layoutWidget")
        self.horizontalLayout = QtWidgets.QHBoxLayout(self.layoutWidget)
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout.setObjectName("horizontalLayout") 
       
        self.button_bn = QtWidgets.QPushButton(self.layoutWidget)
        self.button_bn.setObjectName("button_bn")
        self.horizontalLayout.addWidget(self.button_bn)
        self.button_bn.clicked.connect(self.button_bn_clicked)
        
        self.button_scan = QtWidgets.QPushButton(self.layoutWidget)
        self.button_scan.setObjectName("button_scan")
        self.button_scan.clicked.connect(self.button_scan_clicked)
        self.serial_scanner = SerialScanner()
        self.serial_scanner.ports_updated.connect(self.update_combo_box)

        self.button_raw = QtWidgets.QPushButton(self.layoutWidget)
        self.button_raw.setObjectName("button_raw")
        self.horizontalLayout.addWidget(self.button_raw)
        self.button_raw.clicked.connect(self.button_raw_clicked)

        self.button_clear = QtWidgets.QPushButton(self.layoutWidget)
        self.button_clear.setObjectName("button_clear")
        self.horizontalLayout.addWidget(self.button_clear)
        self.button_clear.clicked.connect(self.button_clear_clicked)
        
        self.layoutWidget1 = QtWidgets.QWidget(self.centralwidget)
        self.layoutWidget1.setGeometry(QtCore.QRect(1200, 90, 350, 200))
        self.layoutWidget1.setObjectName("layoutWidget1")
        self.verticalLayout = QtWidgets.QVBoxLayout(self.layoutWidget1)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout.setObjectName("verticalLayout")
        self.label_datisoggetto = QtWidgets.QLabel(self.layoutWidget1)
        self.label_datisoggetto.setObjectName("label_datisoggetto")
        self.verticalLayout.addWidget(self.label_datisoggetto)
        self.lineEdit_name = QtWidgets.QLineEdit(self.layoutWidget1)
        self.lineEdit_name.setText("")
        self.lineEdit_name.setObjectName("lineEdit_name")
        self.verticalLayout.addWidget(self.lineEdit_name)
        self.lineEdit_surname = QtWidgets.QLineEdit(self.layoutWidget1)
        self.lineEdit_surname.setText("")
        self.lineEdit_surname.setObjectName("lineEdit_surname")
        self.verticalLayout.addWidget(self.lineEdit_surname)
        self.lineEdit_age = QtWidgets.QLineEdit(self.layoutWidget1)
        self.lineEdit_age.setText("")
        self.lineEdit_age.setObjectName("lineEdit_age")
        self.verticalLayout.addWidget(self.lineEdit_age)
        
        
        self.lcdNumber_ist = QtWidgets.QLCDNumber(self.centralwidget)
        self.lcdNumber_ist.setGeometry(QtCore.QRect(1200, 320, 350, 120))
        self.lcdNumber_ist.setObjectName("lcdNumber_ist")
        
        
        self.label_hr_ist = QtWidgets.QLabel(self.centralwidget)
        self.label_hr_ist.setGeometry(QtCore.QRect(1200, 300, 350, 20))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_hr_ist.setFont(font)
        self.label_hr_ist.setScaledContents(True)
        self.label_hr_ist.setAlignment(QtCore.Qt.AlignCenter)
        self.label_hr_ist.setObjectName("label_hr_ist")
        
        self.label_hr_medio = QtWidgets.QLabel(self.centralwidget)
        self.label_hr_medio.setGeometry(QtCore.QRect(1200, 450, 350, 20))
        font = QtGui.QFont()
        font.setBold(True)
        font.setWeight(75)
        self.label_hr_medio.setFont(font)
        self.label_hr_medio.setScaledContents(True)
        self.label_hr_medio.setAlignment(QtCore.Qt.AlignCenter)
        self.label_hr_medio.setObjectName("label_hr_medio")
        
        self.lcdNumber_mean = QtWidgets.QLCDNumber(self.centralwidget)
        self.lcdNumber_mean.setGeometry(QtCore.QRect(1200, 470, 350, 120))
        self.lcdNumber_mean.setObjectName("lcdNumber_mean")
        self.widget = QtWidgets.QWidget(self.centralwidget)
        self.widget.setGeometry(QtCore.QRect(50, 800, 1100, 50))
        self.widget.setObjectName("widget")
        
        #comboBox
        self.horizontalLayout_2 = QtWidgets.QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout_2.addWidget(self.comboBox_serialport)
        self.horizontalLayout_2.addWidget(self.button_scan)

    
        self.verticalLayout_2 = QtWidgets.QVBoxLayout(self.widget) ##############################
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout_2.addLayout(self.horizontalLayout_2)
        self.verticalLayout_2.addWidget(self.conn_btn)
    

        
        MainWindow.setCentralWidget(self.centralwidget)
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 826, 24))
        self.menubar.setObjectName("menubar")
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuFile.setObjectName("menuFile")
        self.menuSettings = QtWidgets.QMenu(self.menubar)
        self.menuSettings.setObjectName("menuSettings")
        MainWindow.setMenuBar(self.menubar)
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        self.statusbar.setObjectName("statusbar")
        MainWindow.setStatusBar(self.statusbar)

        self.actionResolution_Mode = QtWidgets.QAction(MainWindow)
        self.actionResolution_Mode.setObjectName("actionResolution_Mode")   
        self.actionResolution_Mode.triggered.connect(self.resolution_mode_clicked) #bit_res
        self.actionFull_Scale = QtWidgets.QAction(MainWindow)
        self.actionFull_Scale.setObjectName("actionFull_Scale")
        self.actionFull_Scale.triggered.connect(self.full_scale_clicked) #g_res
        self.actionSelect_Port = QtWidgets.QAction(MainWindow)
        self.actionSelect_Port.setObjectName("actionSelect_Port")

        self.actionStart_acquisition = QtWidgets.QAction(MainWindow)
        self.actionStart_acquisition.setObjectName("actionStart_acquisition")
        self.actionStart_acquisition.setShortcut('Ctrl+B')
        self.actionStart_acquisition.triggered.connect(self.start_acq_clicked)

        self.actionStop_acquisition = QtWidgets.QAction(MainWindow)
        self.actionStop_acquisition.setObjectName("actionStop_acquisition")
        self.actionStop_acquisition.setShortcut('Ctrl+F')
        self.actionStop_acquisition.triggered.connect(self.stop_acq_clicked)

        self.actionSave_data = QtWidgets.QAction(MainWindow)
        self.actionSave_data.setObjectName("actionSave_data")
        self.actionSave_data.setShortcut('Ctrl+S') #forse è meglio cambiare la lettera allo stop
        self.actionSave_data.triggered.connect(self.save_data_clicked)

        self.menuFile.addAction(self.actionStart_acquisition)
        self.menuFile.addAction(self.actionStop_acquisition)
        self.menuFile.addAction(self.actionSave_data)

        self.menuSettings.addAction(self.actionResolution_Mode)
        self.menuSettings.addAction(self.actionFull_Scale)
        self.menubar.addAction(self.menuFile.menuAction())
        self.menubar.addAction(self.menuSettings.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)
        
        self.time = list(range(320))
        self.acc_tot_graph = np.zeros(320) 
        
        self.line_acc_tot = self.graphicsView.plot(
            self.time,
            self.acc_tot_graph,
            name="Accelerazione totale Raw",
        )

        self.current_mode_raw = "Raw Data"

    def show_error_message(self, message):
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Critical)
        msg.setText("Warning")
        msg.setInformativeText(message)
        msg.setWindowTitle("Warning")
        msg.exec_()

    def update_combo_box(self, serial_ports):
        self.comboBox_serialport.clear()
        self.comboBox_serialport.addItems(serial_ports)

    @pyqtSlot(np.ndarray, int, int)
    def is_acc_tot_ready(self, acc_tot, data_buffer_filtered, ready, ready_processing): 
        global calibration, stop, recalibrate
        if (ready == 1 and self.current_mode_raw == "Raw Data" and calibration==0 and stop==0):
            self.update_plot(acc_tot)
        if(ready_processing==1 and self.current_mode_raw == "Processed Data" and calibration==0 and stop==0): 
            self.update_plot(data_buffer_filtered)
        if(calibration==1 and stop==0 and recalibrate==1): # calibration phase: data are not ready to be plotted, nor
            # to be sent to the psoc; recalibrate is set to 0 when less than one minute has passed
            time.sleep(0.5)
            number = int(45 - (time.time()-self.serial_worker.start_time))
            if(number > 0 and number <= 45):
                self.label_calibration.setText("Calibration... {} s".format(number)) 
        elif(stop==1): # the user has pressed stop (stop==1) during the calibration -> from the next acquisition, the 
            # calibration should start from the beginning
            time.sleep(0.5)
            self.label_calibration.setText("")
        elif(calibration==0 and stop==0): # we are acquiring data after the calibration phase
            self.label_calibration.setText("")

    def update_plot(self, acc_tot):
        print(self.serial_worker.count)
        if(self.current_mode_raw == "Processed Data"): # if current mode is Processed Data,
            # we need to plot the raw data (we plot the opposite of what is written on the button)
            if(self.serial_worker.buf_sampl < 320):
                num_samples = self.serial_worker.buf_sampl
            else:
                num_samples = 320
            self.start += self.serial_worker.buf_sampl #count-32 # set the start of the x-axis
            self.end = self.start + 320 # set the end of the x-axis
            self.time = np.arange(self.start, self.end) # define the x-axis
            self.acc_tot_graph = self.acc_tot_graph[num_samples:] # assign to acc_tot_graph the last values of the previous acc_tot_graph
            self.acc_tot_graph = np.append(self.acc_tot_graph, acc_tot[-num_samples:]) # append the new values of acc_tot to acc_tot_graph
            self.line_acc_tot.setData(self.time, self.acc_tot_graph) # set the data that will update the plot
            
            self.serial_worker.buf_sampl = 0 # the number of samples to put in the graph now can be reset to 0
            self.serial_worker.buf_sampl_processing = 0
            self.serial_worker.ready = 0 
        else:
            # mettere grafico con data processed self.buf_sampl_processing
            if(self.serial_worker.buf_sampl_processing < 320):
                num_samples = self.serial_worker.buf_sampl_processing
            else:
                num_samples = 320
            self.start += self.serial_worker.buf_sampl_processing #count-32 # set the start of the x-axis
            self.end = self.start + 320 # set the end of the x-axis
            self.time = np.arange(self.start, self.end) # define the x-axis
            self.acc_tot_graph = self.acc_tot_graph[num_samples:] # assign to acc_tot_graph the last values of the previous acc_tot_graph
            self.acc_tot_graph = np.append(self.acc_tot_graph, acc_tot[-num_samples:]) # append the new values of acc_tot to acc_tot_graph
            self.line_acc_tot.setData(self.time, self.acc_tot_graph) # set the data that will update the plot
            self.serial_worker.buf_sampl = 0
            self.serial_worker.buf_sampl_processing = 0 # the number of samples to put in the graph now can be reset to 0
            self.serial_worker.ready_processing = 1

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "(He)Art Attack"))
        self.label_title.setText(_translate("MainWindow", "(He)Art Attack"))
        self.button_bn.setText(_translate("MainWindow", "Light Mode"))
        self.button_raw.setText(_translate("MainWindow", "Processed Data"))
        self.button_clear.setText(_translate("MainWindow", "Clear"))
        self.label_datisoggetto.setText(_translate("MainWindow", "Insert data"))
        self.lineEdit_name.setPlaceholderText(_translate("MainWindow", "Name:"))
        self.lineEdit_surname.setPlaceholderText(_translate("MainWindow", "Surname:"))
        self.lineEdit_age.setPlaceholderText(_translate("MainWindow", "Age:"))
        self.label_hr_ist.setText(_translate("MainWindow", "Instantaneous HR"))
        self.label_hr_medio.setText(_translate("MainWindow", "Mean HR"))
        self.menuFile.setTitle(_translate("MainWindow", "File"))
        self.menuSettings.setTitle(_translate("MainWindow", "Settings"))

        self.button_scan.setText(_translate("MainWindow", "Scan")) 

        # # Set resolution and full scale buttons
        # if BIT_RESOLUTION == 10:
        #     self.actionResolution_Mode.setText(_translate("MainWindow", "Switch resolution to 8 bit"))
        # elif BIT_RESOLUTION == 8 and LOW_BATTERY == 0:
        #     self.actionResolution_Mode.setText(_translate("MainWindow", "Switch resolution to 10 bit"))
        # elif BIT_RESOLUTION == 8 and LOW_BATTERY == 1:
        #     self.actionResolution_Mode.setText(_translate("MainWindow", "Low battery. Cannot change settings"))
        
        # if G_RESOLUTION == 2:
        #     self.actionFull_Scale.setText(_translate("MainWindow", "Switch Full Scale to 4g"))
        # else:
        #     self.actionFull_Scale.setText(_translate("MainWindow", "Switch Full Scale to 2g"))
        self.actionResolution_Mode.setText(_translate("MainWindow", "Switch bit resolution"))
        self.actionFull_Scale.setText(_translate("MainWindow", "Switch Full Scale"))
        self.actionSelect_Port.setText(_translate("MainWindow", "Serial Port"))
        self.actionStart_acquisition.setText(_translate("MainWindow", "Start acquisition"))
        self.actionStop_acquisition.setText(_translate("MainWindow", "Stop acquisition"))
        self.actionSave_data.setText(_translate("MainWindow", "Save data .xlsx"))

    def update_lcd_ist(self):
        self.lcdNumber_ist.display(self.serial_worker.HR_int)

    def update_lcd_mean(self):
        self.lcdNumber_mean.display(self.serial_worker.HR_mean)

    def button_bn_clicked(self):
        current_mode = self.button_bn.text()
        if current_mode == "Dark Mode":
            self.button_bn.setText("Light Mode")
            self.graphicsView.setBackground("k")
            self.mode = "chiara"
        else:
            self.button_bn.setText("Dark Mode")
            self.graphicsView.setBackground("w")
            self.mode = "scura"
    def button_raw_clicked(self):
        self.current_mode_raw = self.button_raw.text()
        if self.current_mode_raw == "Raw Data":
            self.button_raw.setText("Processed Data")
            #self.start=0
            #self.acc_tot_graph = np.zeros(320) 
        else:
            self.button_raw.setText("Raw Data")
            #self.start=0
            #self.acc_tot_graph = np.zeros(320) 

    def button_clear_clicked(self):
        self.time = list(range(320))
        self.acc_tot_graph = np.zeros(320)
        self.line_acc_tot.setData(self.time, self.acc_tot_graph)

    def start_acq_clicked(self):
        self.serial_worker.send('b')
        global BIT_RESOLUTION, G_RESOLUTION, calibration, stop, recalibrate, first_time
        stop = 0
        self.label_fs.setText("Current resolution: {} bit" .format(BIT_RESOLUTION))
        self.label_res.setText("Current full scale: +/-{} g" .format(G_RESOLUTION))
        if((time.time() - self.last_acq_time) >= 120): 
            recalibrate = 1
            calibration = 1
        first_time = 1 # needed to update correctly the start_time in the serial worker

    def stop_acq_clicked(self):
        global stop, first_time, calibration, recalibrate
        stop = 1
        self.serial_worker.send('s')
        self.serial_worker.count = 0
        self.serial_worker.ready = 0
        self.serial_worker.ready_processing = 0
        if((time.time() - self.last_acq_time) < 120 and calibration==0): # the calibration phase has ended
            # but less than one minute has passed from the last acquisition -> no need to re-calibrate
            recalibrate = 0
        self.last_acq_time = time.time() # save the time instant at the end of the acquisition

    def save_data_clicked(self):
        df = pd.DataFrame({'Acc z': self.serial_worker.acc_tot})
        df_HR = pd.DataFrame({'HR ist': self.serial_worker.HR_vect})

        cognome = self.lineEdit_surname.text()
        nome = self.lineEdit_name.text()
        age = self.lineEdit_age.text()
    
        nome_file = f'{nome}_{cognome}_{age}.xlsx'
        nome_file_HR = f'{nome}_{cognome}_{age}_HR.xlsx'
        df.to_excel(nome_file, index=False)
        df_HR.to_excel(nome_file_HR, index=False)
        print(f'DataFrame salvato nel file: {nome_file}')

        
    def resolution_mode_clicked(self):#resolution
        global BIT_RESOLUTION, LOW_BATTERY
        
        if BIT_RESOLUTION == 10:
            self.serial_worker.send('p')
            BIT_RESOLUTION = 8
            self.label_fs.setText("Current resolution: 8 bit ")

        elif BIT_RESOLUTION == 8 and LOW_BATTERY == 0:
            self.serial_worker.send('p')
            BIT_RESOLUTION = 10
            self.label_fs.setText("Current resolution: 10 bit ")
        elif BIT_RESOLUTION == 8 and LOW_BATTERY == 1:
            self.actionResolution_Mode.setText("Low battery. Cannot change settings")

            
    def full_scale_clicked(self): #, full_scale
        global G_RESOLUTION
        self.serial_worker.send('g')

        if(LINE_RECEIVED):
            self.show_error_message("Next HR value may not be accurate.")
        
        if G_RESOLUTION == 2:
            G_RESOLUTION = 4
            self.label_res.setText("Current full scale: +/- 4 g ")
        else:
            G_RESOLUTION = 2
            self.label_res.setText("Current full scale: +/- 2 g")
    
    def button_scan_clicked(self): ##################
        self.serial_scanner.scan()

    ####################
    # SERIAL INTERFACE #
    ####################
    def serialscan(self):
        """!
        @brief Scans all serial ports and create a list.
        """
        # create the combo box to host port list
        self.port_text = ""
        self.comboBox_serialport = QtWidgets.QComboBox()
        self.comboBox_serialport.setObjectName("comboBox_serialport")
        self.comboBox_serialport.currentTextChanged.connect(self.port_changed)
        #### REQUIREMENTS: Automatic detection of the COM port ####
        self.conn_btn = QPushButton(
            text=("Connect to port {}".format(self.port_text)), 
            checkable=True,
        )
        self.conn_btn.toggled.connect(lambda checked: self.on_toggle(checked))

        ###########################################################
        # acquire list of serial ports and add it to the combo box
        serial_ports = [
                p.name
                for p in serial.tools.list_ports.comports() 
            ]
        self.comboBox_serialport.addItems(serial_ports)  
        
    ##################
    # SERIAL SIGNALS #
    ##################
    def port_changed(self): 
        """!
        @brief Update conn_btn label based on selected port.
        """
        self.port_text = self.comboBox_serialport.currentText()
        self.conn_btn.setText("Connect to port {}".format(self.port_text)) # Connect to port

    #### REQUIREMENTS: allow start/stop data streaming ####
    # the QKeyEvent is used to allow the user to start/stop the data streaming by pressing the 'b' and 's' key
    # it is automatically called when a key is pressed
    def keyPressEvent(self, event: QKeyEvent):
        """!
        @brief Handle key press events.
        """
        if event.text().lower() == 'b':
            self.serial_worker.send('b') # _from_key
        if event.text().lower() == 's':
            self.serial_worker.send('s') # _from_key
        if event.text().lower() == 'k':
            self.serial_worker.send('k') # _from_key
        if event.text().lower() == 'g':
            self.serial_worker.send('g') # _from_key
            time.sleep(0.1)
            self.serial_worker.send('k') # show new seetings
        if event.text().lower() == 'p':
            if LOW_BATTERY:
                print("LOW BATTERY. CANNOT CHANGE SETTINGS")
            else:
                self.serial_worker.send('p') # _from_key
                time.sleep(0.1)
            self.serial_worker.send('k') # show new seetings
    #######################################################
   
    @pyqtSlot(bool) 
    def on_toggle(self, checked):
        """!
        @brief Allow connection and disconnection from selected serial port.
        """
        if checked: 
            self.serial_worker = SerialWorker(self.port_text) 
            self.serial_worker.signals.status.connect(self.check_serialport_status) 
            self.serial_worker.signals.device_port.connect(self.connected_device)
            self.threadpool.start(self.serial_worker) 
        else:
            # kill thread
            global KILL, stop
            KILL = True
            stop = 1#self.stop = 1
            self.serial_worker.signals.error_occurred.connect(self.show_error_message)
            self.serial_worker.killed()
            self.comboBox_serialport.setDisabled(False) 
            self.conn_btn.setText(
                "Connect to port {}".format(self.port_text) 
            )
        
    def check_serialport_status(self, port_name, status):
        """!
        @brief Handle the status of the serial port connection.

        Available status:
            - 0  --> Error during opening of serial port
            - 1  --> Serial port opened correctly
        """
        if status == 0: 
            self.conn_btn.setChecked(False)
            self.show_error_message("Error during opening of serial port. Check device connection or change port.")
        elif status == 1: 
            self.comboBox_serialport.setDisabled(True) 
            self.conn_btn.setText(
                "Disconnect from port {}".format(port_name)
            )

    def connected_device(self, port_name):
        """!
        @brief Checks on the termination of the serial worker.
        """
        logging.info("Port {} closed.".format(port_name))

    def ExitHandler(self):
        """!
        @brief Kill every possible running thread upon exiting application.
        """
        global KILL
        KILL = True
        self.serial_worker.killed()

if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    app.aboutToQuit.connect(ui.ExitHandler) 
    MainWindow.show()
    sys.exit(app.exec_())