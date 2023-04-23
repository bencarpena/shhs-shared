'''
########################################################################
Project name    :   Alphacentauri Temp + Humidity program
Description     :   [+] Reads temp and humidity at my local area 
                :   [+] and posts data/readings at Slack 
                :   [-] and Cloud-based services (IoT Hub + Stream Analytics + Azure SQL DB)
@bencarpena     :   20190301 : 	initial codes created
                :   20190518 :  Added Slack feature
                :   20190727 :  Changed sensor to DHT from AM2302
                :   20200103 :  Added timestamp at each message and round half up sensor data
				:	20201219 :  Added MQTT and Azure IoT Hub integration
                :   20201226 :	Reformatted JSON payload to IoT Hub
                :   20210110 :  Updated closing message routine
                :	20210201 :	Added sys.exc_info
                :   20210908 :  Muted exception error <class 'socket.gaierror'>; exception cause: Azure IoT Hub deactivated
                :   20220311 :  Upgraded to return uptime data
                :   20221223 :  Enhanced led subroutine for greater user interaction
                :   20221224 :  Changed Slack message alias from `alphacentauri (iothub bypass dht)` to Hagrid the Blessed 
                :   20221225 :  Added ip at output
                :   20230111 :  Upgraded print outputs
                :   20230115 :  Added disk space monitoring and reporting to Slack
                :   20230228 :  Upgraded system uptime message to include GPU and CPU temperature in output
                :   20230402 :  added parallel processing


Credits:

#SwitchDoc Labs May 2016
# reads all four channels from the Grove4Ch16BitADC Board in single ended mode
# also reads raw values
#

# MQTT personal notes:
https://onedrive.live.com/view.aspx?resid=BE42616FC86F2AB8%2119663&id=documents&wd=target%28IoT.one%7C2C2A8BC3-E1B8-2541-9366-F6F8E984C1BF%2FIntegrating%20MQTT%20and%20Azure%20IoT%20Hub%7CCB2F4618-D393-034D-95F5-04A5DFAE8239%2F%29
onenote:https://d.docs.live.net/be42616fc86f2ab8/Documents/archived/Technical%20Notebook/IoT.one#Integrating%20MQTT%20and%20Azure%20IoT%20Hub&section-id={2C2A8BC3-E1B8-2541-9366-F6F8E984C1BF}&page-id={CB2F4618-D393-034D-95F5-04A5DFAE8239}&end

########################################################################
'''

#!/usr/bin/python
# Copyright (c) 2014 Adafruit Industries
# Author: Tony DiCola

# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:

# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.

# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
import sys

import Adafruit_DHT

import ssl, os
import requests
import json

import subprocess

from gpiozero import LED
from time import sleep
#from datetime import datetime, timezone
from datetime import datetime
import math

import RPi.GPIO as GPIO

from paho.mqtt import client as mqtt
import pytz
import os

from multiprocessing import Process


webhook_url = 'https://hooks.slack.com/services/webhookaddresshere'

raspi_current_ip  = subprocess.check_output("ifconfig -a | grep cast | grep net", shell=True, universal_newlines=True).strip()
output_ip = raspi_current_ip.split(' ')[1]

cpu_temperature_exec = subprocess.check_output('cat /sys/class/thermal/thermal_zone0/temp', shell=True, universal_newlines=True).strip()
cpu_temperature_exec = int(cpu_temperature_exec) / 1000
cpu_temperature = str(cpu_temperature_exec) + ' C'
gpu_temperature = subprocess.check_output("vcgencmd measure_temp | egrep  -o  '[[:digit:]].*'", shell=True, universal_newlines=True).strip().replace("'", " ")

if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)): 
			ssl._create_default_https_context = ssl._create_unverified_context

# Parse command line parameters.
sensor_args = { '11': Adafruit_DHT.DHT11,
                '22': Adafruit_DHT.DHT22,
                '2302': Adafruit_DHT.AM2302 }
if len(sys.argv) == 3 and sys.argv[1] in sensor_args:
    sensor = sensor_args[sys.argv[1]]
    pin = sys.argv[2]
else:
    slack_msg = {'text' : 'Hagrid the Blessed (weather_man | iot/w01) : System usage error : Read from an AM2302 connected to GPIO pin #4 | ip : ' + output_ip + ' '}
    requests.post(webhook_url, data=json.dumps(slack_msg))
    sys.exit(1)

# Try to grab a sensor reading.  Use the read_retry method which will retry up
# to 15 times to get a sensor reading (waiting 2 seconds between each retry).
humidity, temperature = Adafruit_DHT.read_retry(sensor, pin)

# Un-comment the line below to convert the temperature to Fahrenheit.
# temperature = temperature * 9/5.0 + 32

# Note that sometimes you won't get a reading and
# the results will be null (because Linux can't
# guarantee the timing of calls to read the sensor).
# If this happens try again!


led = LED(17)

def illuminate_led(seconds):
    print ("INFO: illuminating status led...")
    led.on()
    sleep(int(seconds))
     

def round_half_up(n, decimals=0):
    multiplier = 10 ** decimals
    return math.floor(n*multiplier + 0.5) / multiplier


def on_connect(client, userdata, flags, rc):
    print("alphacentauri (mode: iot/w01) connected with result code: " + str(rc))


def on_disconnect(client, userdata, rc):
    print("alphacentauri (mode: iot/w01) disconnected with result code: " + str(rc))


def on_publish(client, userdata, mid):
    print("alphacentauri (mode: iot/w01) sent message!")
    print("JSON payload sent: ", slack_msg_mqtt)


def on_message(client, userdata, message):
    print("message received " ,str(message.payload.decode("utf-8")))
    print("message topic=",message.topic)
    print("message qos=",message.qos)
    print("message retain flag=",message.retain)

def on_log(client, userdata, level, buf):
    print("log: ",buf)



def get_sensor_readings():
    print ("INFO: getting sensor readings...")
    blnExecute = True
    while blnExecute == True:

        if humidity is not None and temperature is not None:
            #20190727 @bencarpena : Added feature to turn on/off LED            
            #20230112 : print('Temp={0:0.1f}*  Humidity={1:0.1f}%'.format(temperature, humidity))
            #20230112 : print(temperature) #20210227 debug only

            # ##########################################################
            # OUTPUT
            #   20230112 : upgraded output message 
            # ##########################################################
            print('dt local : ' + str(datetime.now()) + '| dt utc : ' + str(datetime.now(pytz.utc)) + ' | Location : 30.112101353012203, -95.5456394050205 | Temperature : ' + str(round_half_up(temperature, 1)) + ' C | Humidity : ' + str(round_half_up(humidity, 1)) + ' %' )

            dtstamp = datetime.now()
            slack_msg = {'text' : 'Hagrid the Blessed (weather_man - iothub bypass dht) | ' + str(dtstamp) + ' | Temperature : ' + str(round_half_up(temperature, 1)) + ' C | Humidity : ' + str(round_half_up(humidity, 1)) + ' % '}
            requests.post(webhook_url, data=json.dumps(slack_msg))

            slack_msg = {'text' : 'Hagrid the Blessed (weather_man - iothub bypass dht) | ip : ' + output_ip + ' | Location : 30.112101353012203, -95.5456394050205'}
            requests.post(webhook_url, data=json.dumps(slack_msg))


        
            # 20230111 : print ("Success : Posted data to Slack!")
            #20201226 : Updated to send JSON payload
            slack_msg_mqtt = '{"iot_msg_from" : "Hagrid : alphacentauri(iot/w01)", "iot_dt" : "' + str(dtstamp) + '", "iot_rd" : "sensor = am2302 | Temperature = ' + str(round_half_up(temperature, 1)) + ' C | Humidity = ' + str(round_half_up(humidity, 1)) + ' %"}'
            blnExecute = False

            # @bencarpena 20201219 : Send message to IoT Hub via MQTT
            # START : MQTT < #############################
            path_to_root_cert = '/directoryhere/certs/Baltimore.pem'
            device_id = 'alphard02'
            sas_token = 'SharedAccessSignature sr=iotpythonmqtt.azure-devices.net%token_here'
            iot_hub_name = "iotpythonmqtt"


            client = mqtt.Client(client_id=device_id, protocol=mqtt.MQTTv311)
            client.on_message=on_message 
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            client.on_publish = on_publish

            client.username_pw_set(username=iot_hub_name+".azure-devices.net/" +
                                device_id + "/?api-version=2018-06-30", password=sas_token)

            client.tls_set(ca_certs=path_to_root_cert, certfile=None, keyfile=None,
                        cert_reqs=ssl.CERT_REQUIRED, tls_version=ssl.PROTOCOL_TLSv1_2, ciphers=None)
            client.tls_insecure_set(False)

            client.connect(iot_hub_name+".azure-devices.net", port=8883)

            #start the loop
            client.loop_start() 

            #subscribe to topic
            client.subscribe("devices/" + device_id + "/messages/events/")

            #publish message
            client.publish("devices/" + device_id + "/messages/events/", slack_msg_mqtt, qos=1) 

            #give time to process subroutines
            sleep(5)

            #display log
            client.on_log=on_log


            #end the loop
            client.loop_stop()

            # END MQTT > #############################
        else:
            #print('Failed to get reading. Try again!')
            console_data = subprocess.check_output("uptime", shell=True, universal_newlines=True)
            slack_msg = {'text' : 'Hagrid the Blessed (weather_man | iot/w01) : Error occurred! : failed to get reading. Try again or fix me please. | ip : ' + output_ip + ' | dt : ' + str(datetime.now())}
            requests.post(webhook_url, data=json.dumps(slack_msg))
            slack_msg = {'text' : 'Hagrid the Blessed (weather_man | iot/w01) : System Uptime : ' + console_data}
            requests.post(webhook_url, data=json.dumps(slack_msg))
            blnExecute = False

    
# ########################
# CODE DRIVER
# ########################

try:
    Process(target=illuminate_led, args=(10,)).start()
    Process(target=get_sensor_readings).start()
    
except:
    _exception = sys.exc_info()[0]
    
    raspi_current_ip  = subprocess.check_output("ifconfig -a | grep cast | grep net", shell=True, universal_newlines=True).strip()
    output_ip = raspi_current_ip.split(' ')[1]
    
    if "socket.gaierror" in str(_exception): 
        # 20210908 @bencarpena : Azure iot hub deactivated; no cause for alarm
        slack_msg = {'text' : 'Hagrid the Blessed (weather_man | iot/w01) : Hmmm... OK! ' + str(datetime.now())}
        requests.post(webhook_url, data=json.dumps(slack_msg))
        console_data = subprocess.check_output("uptime", shell=True, universal_newlines=True)
    else:
        slack_msg = {'text' : 'Hagrid the Blessed (weather_man | iot/w01) : Error occurred! : Exception message = ' + str(_exception) + ' ' + str(datetime.now())}
        requests.post(webhook_url, data=json.dumps(slack_msg))

finally:
    # Get free disk space and % free ====
    #mymac : df_data  = subprocess.check_output("df -kh | grep disk3s1s1", shell=True, universal_newlines=True).strip()
    df_data  = subprocess.check_output("df -kh | grep root", shell=True, universal_newlines=True).strip()
    avail_disk_size = df_data.split('  ')[6].strip()
    percentage_disk_free = df_data.split('  ')[7].strip().replace('/' ,'')
    slack_msg = {'text' : 'Hagrid the Blessed (weather_man | iot/w01) : Free Disk space : ' + avail_disk_size + ' | % free : ' + percentage_disk_free + ' '}
    requests.post(webhook_url, data=json.dumps(slack_msg))

    console_data = subprocess.check_output("uptime", shell=True, universal_newlines=True)
    slack_msg = {'text' : 'Hagrid the Blessed (weather_man | iot/w01) : System Uptime : ' + console_data + ' | ip : ' + output_ip + ' | cpu temp : ' + str(cpu_temperature) + ' | gpu temp : ' + str(gpu_temperature)}
    requests.post(webhook_url, data=json.dumps(slack_msg))

