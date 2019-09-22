from bluepy.btle import UUID, Peripheral, DefaultDelegate, BTLEException, \
     BTLEDisconnectError
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
from AWSIoTPythonSDK.exception.AWSIoTExceptions import connectTimeoutException, \
     disconnectTimeoutException, publishTimeoutException
from datetime import datetime
from binascii import b2a_hex
import sys
import json


class NotifyDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)
        
    def handleNotification(self, cHandle, data):
        current_data = bl475e.read()
        print(current_data)
        message = {}
        message['fahrenheit'] = str(current_data.deg_fahrenheit)
        message['humidity'] = str(current_data.rel_humidity)
        message['timestamp'] = current_data.timestamp
        json_message = json.dumps(message)
        try:
            client.publish(topic, json_message, 1)
        except publishTimeoutException:
            pass
        

class CurrentData:
    def __init__(self):
        self.deg_celsius = None
        self.deg_fahrenheit = None
        self.rel_humidity = None
        self.timestamp = None
        
    def __str__(self):
        return "B-L475E data: {} {}\xb0F, {}% RH".format(self.timestamp, self.deg_fahrenheit, self.rel_humidity)
        
    def set(self, raw_temperature, raw_humidity):
        self.deg_celsius = round(self.raw2units(raw_temperature), 1)
        self.deg_fahrenheit = round(((9 * self.deg_celsius) / 5 + 32), 1)
        self.rel_humidity = round(self.raw2units(raw_humidity), 1)
        
        date_time = datetime.now()
        self.timestamp = date_time.strftime("%Y-%m-%d %H:%M:%S")
        
    @staticmethod
    def raw2units(raw_data):
        hex_data = bytearray(raw_data)
        hex_data.reverse()
        return float(int(b2a_hex(hex_data), 16) / 10)
        

class HTSensor:
    
    temperature_uuid = UUID("A32E5520-E477-11E2-A9E3-0002A5D5C51B")
    rel_humidity_uuid = UUID("01C50B60-E48C-11E2-A073-0002A5D5C51B")
    time_seconds_uuid = UUID("0A366E80-CF3A-11E1-9AB4-0002A5D5C51B")
    
    def __init__(self, mac_address):
        self.peripheral = None
        self.mac_address = mac_address
        self.temperature_char = None
        self.rel_humidity_char = None
        self.time_seconds_char = None
        
    def is_connected(self):
        try:
            return self.peripheral.getState() == "conn"
        except Exception:
            return False
        
    def connect(self, max_retries=3):
        tries = 0
        while tries < max_retries and self.is_connected() is False:
            tries += 1
            try:
                self.peripheral = Peripheral(self.mac_address)
                self.temperature_char = self.peripheral.getCharacteristics(uuid=self.temperature_uuid)[0]
                self.rel_humidity_char = self.peripheral.getCharacteristics(uuid=self.rel_humidity_uuid)[0]
                self.time_seconds_char = self.peripheral.getCharacteristics(uuid=self.time_seconds_uuid)[0]
                
                self.peripheral.setDelegate(NotifyDelegate())
                self.peripheral.writeCharacteristic(self.time_seconds_char.valHandle + 1, b"\x01\x00")
                
                print("B-L475E connected.")
            except BTLEException:
                if tries == max_retries:
                    print("Unable to establish BLE connection with B-L475E.")
                    print("Make sure:")
                    print("- B-L475E is powered on")
                    print("- blue LED is on (BLE enabled)")
                    print("- green LED is blinking (in advertising mode)")
                    sys.exit()
                else:
                    print("retrying BLE connection with B-L475E (retry #{}) ...".format(tries))
        
    def check_time_seconds_notify(self):
        try:
            return self.peripheral.waitForNotifications(1.0)
        except BTLEDisconnectError:
            print("B-L475E disconnected.")
            print("attempting to reestablish connection...")
            bl475e.connect()
    
    def read(self):
        raw_temperature = self.temperature_char.read()
        raw_humidity = self.rel_humidity_char.read()     
        current_data = CurrentData()
        current_data.set(raw_temperature, raw_humidity)
        return current_data
    
    def disconnect(self):
        if self.peripheral is not None:
            self.peripheral.disconnect()
            self.peripheral = None
            self.temperature_char = None
            self.rel_humidity_char = None
            self.time_seconds_char = None
            
        
bl475e_mac_address = "02:80:E1:00:34:12"

host = "your-endpoint-url"
client_id = "your-thing-name-here"
topic = "your-topic-name-here"
cert_path = "/home/pi/aws_iot/certs/"
root_ca = cert_path + "AmazonRootCA1.pem"
certificate = cert_path + "certificate.pem.crt"
private_key = cert_path + "private.pem.key"

# connect to B-L475E
bl475e = HTSensor(bl475e_mac_address)
bl475e.connect()

# construct the AWS Iot MQTT client
#client = None
client = AWSIoTMQTTClient(client_id)
client.configureEndpoint(host, 8883)
client.configureCredentials(root_ca, private_key, certificate)
client.configureAutoReconnectBackoffTime(1, 32, 20)
client.configureOfflinePublishQueueing(-1)
client.configureDrainingFrequency(2)
client.configureConnectDisconnectTimeout(10)
client.configureMQTTOperationTimeout(5)

# connect to AWS Iot Core
attempts = 0
connected = 0
while attempts <= 3 and not connected:
    attempts += 1
    try:
        client.connect()
        print("Connected to AWS IoT Core.")
        connected = 1
    except connectTimeoutException:
        if attempts > 3:
            print("Unable to connect to AWS IoT Core.")
            bl475e.disconnect()
            print("B-L475E disconnected.")
            sys.exit()
        else:
            print("Retrying connection to AWS IoT Core.")

while True:
    try:
        if bl475e.check_time_seconds_notify():
            continue
    except KeyboardInterrupt:
        bl475e.disconnect()
        print("B-L475E disconnected.")
        try:
            client.disconnect()
            print("Disconnected from AWS IoT Core")
        except disconnectTimeoutException:
            pass
        sys.exit()

