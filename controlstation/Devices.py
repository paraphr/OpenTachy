# -*- coding: utf-8 -*-
"""
Created on Sun Jun 30 17:45:47 2024

@author: Paul
"""

import serial
import time
import serial.tools.list_ports
import re

class Printer:
    def __init__(self, port, baudrate, timeout=1, max_retries=3, connection_timeout=5):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.max_retries = max_retries
        self.connection_timeout = connection_timeout
        self.serial_connection = None

    def connect(self):
        # available_ports = [port.device for port in serial.tools.list_ports.comports()]
        # if self.port not in available_ports:
        #     print(f"Error: The port {self.port} is not available. Available ports: {available_ports}")
        #     return False
        try:
            print(f"Trying to connect to {self.port} at {self.baudrate} baud.")
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=self.timeout)
            start_time = time.time()
            while (time.time() - start_time) < self.connection_timeout:
                if self.serial_connection.is_open:
                    self.flush_initial_data()
                    print(f"Connected to {self.port} at {self.baudrate} baud.")
                    self.start_setup()
                    return True
                time.sleep(0.1)
            self.serial_connection.close()
            print(f"Connection attempt to {self.port} timed out.")
            return False
        except serial.SerialException as e:
            print(f"Error connecting to 3D printer: {e}")
            return False

    def disconnect(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print("Disconnected from the 3D printer.")

    def flush_initial_data(self):
        start_time = time.time()
        timeout = 5  # seconds
        while self.serial_connection.in_waiting or (time.time() - start_time) < timeout:
            if self.serial_connection.in_waiting:
                initial_data = self.serial_connection.readline().decode('utf-8').strip()
                print(f"Flushed initial data: {initial_data}")


    def start_setup(self):
        print("Setting up")
        self.send_command("G1 X0 Y0")   # Home
        self.send_command("M211 S0")   # Soft End Stop Off
        self.send_command("G90")   # Positioning Relativ
        return None

    def send_command(self, command):
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Serial connection is not open.")
            return None
        retries = 0
        while retries < self.max_retries:
            try:
                print(f"Sending command: {command}")
                self.serial_connection.write(f"{command}\n".encode('utf-8'))
                time.sleep(0.1)
                response = self.serial_connection.readline().decode('utf-8').strip()
                print(f"Response: {response}")
                return self._handle_response(response)
            except serial.SerialTimeoutException:
                print("Error: Serial connection timed out.")
                retries += 1
                print(f"Retrying... ({retries}/{self.max_retries})")
            except serial.SerialException as e:
                print(f"Serial communication error: {e}")
                break
        print("Failed to send command after multiple retries.")
        return None

    def capture_position(self):
        self.flush_initial_data()
        print("Current Position:")
        response = self.send_command("M114 R")
        if response:
            match = re.search(r'X:(-?\d+\.\d+) Y:(-?\d+\.\d+)', response)
            if match:
                x = float(match.group(1))
                y = float(match.group(2))+100
                return {'X': x, 'Y': y}
            else:
                print("Failed to parse current position response.")

        return None

    def _handle_response(self, response):
        if response.startswith('Error'):
            print(f"Printer reported an error: {response}")
            return None
        return response
    

class EDM:
    def __init__(self, port, baudrate, timeout=1, max_retries=3, connection_timeout=5, bytesize=8, parity=serial.PARITY_NONE):
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.bytesize = bytesize
        self.parity = parity
        self.max_retries = max_retries
        self.connection_timeout = connection_timeout
        self.serial_connection = None

    def connect(self):
        # available_ports = [port.device for port in serial.tools.list_ports.comports()]
        # if self.port not in available_ports:
        #     print(f"Error: The port {self.port} is not available. Available ports: {available_ports}")
        #     return False
        try:
            print(f"Trying to connect to {self.port} at {self.baudrate} baud.")
            self.serial_connection = serial.Serial(self.port, self.baudrate, timeout=self.timeout, parity=self.parity, bytesize=self.bytesize)
            start_time = time.time()
            while (time.time() - start_time) < self.connection_timeout:
                if self.serial_connection.is_open:
                    print(f"Connected to {self.port} at {self.baudrate} baud.")
                    self.start_setup()
                    return True
                time.sleep(0.1)
            self.serial_connection.close()
            print(f"Connection attempt to {self.port} timed out.")
            return False
        except serial.SerialException as e:
            print(f"Error connecting to EDM: {e}")
            return False

    def disconnect(self):
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()
            print("Disconnected from the EDM.")

    def start_setup(self):
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Serial connection is not open.")
            return
        
        try:
            print("Setting up")
            self.send_command("s0o")
        except Exception as e:
            print(f"Error during setup: {e}")

    def send_command(self, command):
        if not self.serial_connection or not self.serial_connection.is_open:
            print("Serial connection is not open.")
            return None
        
        retries = 0
        while retries < self.max_retries:
            try:
                print(f"Sending command: {command}")
                self.serial_connection.write(f"{command}\r\n".encode('utf-8'))
                time.sleep(0.1)
                response = self.serial_connection.readline().decode('utf-8').strip()
                print(f"Response: {response}")
                return self._handle_response(response)
            except serial.SerialTimeoutException:
                print("Error: Serial connection timed out.")
                retries += 1
                print(f"Retrying... ({retries}/{self.max_retries})")
            except serial.SerialException as e:
                print(f"Serial communication error: {e}")
                break
        print("Failed to send command after multiple retries.")
        return None

    def capture_distance(self):
        print("Get Distance")
        response = self.send_command("s0g")
        self.send_command("s0o")
        if response:
            match = re.search(r'g0g([+-]?\d+)', response)
            if match:
                distance = int(match.group(1))/10000
                return distance
            else:
                print("Failed to parse distance response.")
        return None
    
    def laser(self, state):
        if state:
            self.send_command("s0o")
        else:
            self.send_command("s0c")

    def _handle_response(self, response):
        if response.startswith('Error'):
            print(f"EDM reported an error: {response}")
            return None
        return response