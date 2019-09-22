# rpi3-aws-iot-ble-sensor-example

AWS IoT BLE sensor example using the St Micro BL-475E-IOT01A Discovery Kit and Raspberry Pi3 B+.

This is a simple AWS IoT BLE sensor demo that does the following:

- uses a Raspberry Pi3 running a Python script and acting as a defacto IoT gateway to:
-- establish a BLE connection with a ST Micro BL-475E-IOT01A Discovery IoT board
-- enable a BLE time notification set to occur every minute on the Discovery IoT board
-- establish a connection to the AWS Iot Core service and subscribe to a specified MQTT topic
-- upon receiving time notification from the Discovery board, read it's temperature/humidity values
-- publish the values to the specified MQTT topic on the AWS IoT Core cloud service


Python script detects when there's no BLE connection to the Discovery IoT board and will retry the connection 3 times before exiting.
The script will also determine if the connection to the AWS IoT Core service has been lost. 

Corresponding code for the Discovery IoT board can be found in the following repository:

https://github.com/msbaylis/b-l475e-iot01a-ble-sensor-example.git