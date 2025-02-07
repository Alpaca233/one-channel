import serial
from serial.tools import list_ports
import threading
import time

class TCMController():
    def __init__(self, sn, baud_rate=57600, timeout=0.5):
        port = [p.device for p in list_ports.comports() if sn == p.serial_number]

        if not port:
            raise ValueError(f"No device found with serial number: {sn}")

        self.serial = serial.Serial(port[0], baudrate=baud_rate, timeout=timeout)
        self.serial_lock = threading.Lock()

        self.target_temperature = self.get_target_temperature()
        self.current_temp = 0

        self.temperature_updating_callback = None
        self.actual_temp_updating_thread = threading.Thread(target=self.update_temperature, daemon=True)
        self.terminate_temperature_updating_thread = False

    def send_command(self, command, module='TC1'):
        with self.serial_lock:
            self.serial.write(f"{module}:{command}\r".encode())
            response = self.serial.readline().decode().strip()
            if response[:4] == 'CMD:' and response[-1] != '1' and response[-1] != '8':
                raise Exception(f"Error from controller: {response}")
            return response

    def get_target_temperature(self):
        response = self.send_command('TCADJTEMP?')
        temp = float(response[14:])
        self.target_temperature = temp
        return temp

    def set_target_temperature(self, t):
        self.send_command('TCADJTEMP=' + str(t))
        self.target_temperature = t

    def save_target_temperature(self):
        response = self.send_command('TCADJTEMP!')
        print('Save target temperature: ', response)

    def get_actual_temperature(self):
        response = self.send_command('TCACTUALTEMP?')
        try:
            temp = float(response[17:])
            self.current_temp = temp
        except:
            # Handle empty responses by returning last known temperature
            temp = self.current_temp
        return temp

    def update_temperature(self):
        while self.terminate_temperature_updating_thread == False:
            time.sleep(1)
            temp = self.get_actual_temperature()
            if self.temperature_updating_callback is not None:
                try:
                    self.temperature_updating_callback(temp, 0)  # Second parameter is dummy for compatibility
                except TypeError as ex:
                    print("Temperature read callback failed")

class TCMControllerSimulation():
    def __init__(self, sn, baud_rate=57600, timeout=0.5):
        self.target_temperature = self.get_target_temperature()
        
        self.temperature_updating_callback = None
        self.actual_temp_updating_thread = threading.Thread(target=self.update_temperature, daemon=True)
        self.terminate_temperature_updating_thread = False

    def send_command(self, command, module='TC1'):
        pass

    def get_target_temperature(self):
        return 10.0

    def set_target_temperature(self, t):
        pass

    def save_target_temperature(self):
        pass

    def get_actual_temperature(self):
        return 12.0

    def update_temperature(self):
        while self.terminate_temperature_updating_thread == False:
            time.sleep(1)
            temp = self.get_actual_temperature()
            if self.temperature_updating_callback is not None:
                try:
                    self.temperature_updating_callback(temp, 0)  # Second parameter is dummy for compatibility
                except TypeError as ex:
                    print("Temperature read callback failed")
