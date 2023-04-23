################################################################################################
# ARCTURUS - Garage Bouncer
################################################################################################
# Edited and enhanced  	: @bencarpena
#      
#	Change log: 
#		20190909 :	Initial setup; no LED; set sleep to 2 from 0.1
#		20190909 :	Added Slack post feature and PIR
#		20191024 :	Added subroutine for capturing images every motion is detected 
# 		20200528 : 	Added try - catch exception 	
# 		20210104 :	Enhance try catch, addressed asyncio error in Slack	
# 		20210224 :	Added Hue light integration		
#		20210226 :	Fine tuned exception handling; added catch all
#		20210227 :	Added assertion at response_hue
#		20210309 :	Changed Hue IP address
#		20210819 :	Regenerated Slack API token;
#				 :	Regenerate at https://benjcarpena.slack.com/services/B013VQT08RM
#		20210909 :	added AssertionError capture; changed Hue bridge IP Address
#		20220116 :	changed Hue IP
#		20220311 :	Added uptime reporting routine
#		20220521 :	changed Hue IP from .12 to .11
#		20221105 :	changed Hue IP from .26 to .25
#		20221105 :	changed Hue IP from .25 to .11
#		20221210 :	changed Hue IP from 192.168.0.25 to 192.168.1.41 (MAC 00:17:88:73:C3:6D)
#		20221229 :	changed name to Bob
#		20230117 : 	updated outputs and assembled new housing / case for Bob :)
#				 :	added subroutine to filter noise in pir reading
#		20230118 :	removed rnp protocol
#		20230122 :	reinstated rnp protocol; Software induced resistance
#		20230208 :	changed Hue IP due to change in router; new ip 10.0.0.27
#				 :	increased rnp protocol to 5
#		20230228 :	upgraded webhooks
#		20230301 :	updated channel to post pictures from #cvx-iot-arcturus to #arcturus-bob
#		20230308 :	changed ip to 10.0.0.26 from .27

################################################################################################


import RPi.GPIO as GPIO
import time
import datetime

import subprocess

import requests
import json
import os, ssl
import slack
import sys
import traceback
import logging

from slack import WebClient

import datetime
import slack
from slack import WebClient

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(11, GPIO.IN)         #Read output from PIR motion sensor
GPIO.setup(3, GPIO.OUT)         #LED output pin

global webhook_url
webhook_url = 'https://hooks.slack.com/services/webhookaddresshere'
hue_ip = '10.0.0.xx'

if (not os.environ.get('PYTHONHTTPSVERIFY', '') and getattr(ssl, '_create_unverified_context', None)): 
			ssl._create_default_https_context = ssl._create_unverified_context

def postUptime():
	console_data = subprocess.check_output("uptime", shell=True, universal_newlines=True)
	print("### SYSTEM UPTIME: " + console_data)
	slack_msg = {'text' : 'Bob the Bouncer (Garage Bouncer iothub-bypass) : System Uptime | ' + console_data}
	requests.post(webhook_url, data=json.dumps(slack_msg))

try:
	while True:
		i=GPIO.input(11)
		if i==0:                 #When output from motion sensor is LOW
			print ("Bob the Bouncer (iothub bypass) | PIR Motion sensor : No movement", i)
			#GPIO.output(3, 0)  #Turn OFF LED
			time.sleep(1.5)
		elif i==1:               #When output from motion sensor is HIGH
			
			print ("Bob the Bouncer (iothub bypass) | PIR Motion sensor : Movement detected ", datetime.datetime.now())
			slack_msg = {'text' : 'Bob the Bouncer (iothub bypass) | PIR Motion sensor : Movement detected ' + str(datetime.datetime.now())}
			
			requests.post(webhook_url, data=json.dumps(slack_msg))
			time.sleep(1.5)
	
			url = "http://" + hue_ip + "/api/apikeyhere/lights/14/state"
			payload = "{\"on\":true, \"bri\":254}"
			headers = {
			'Content-Type': 'text/plain'
			}
			response_hue = requests.request("PUT", url, headers=headers, data = payload)
			assert response_hue.status_code == 200 
			time.sleep(1)

			
			client = slack.WebClient('xoxb-tokenhere')

			TakePic = 'raspistill -o /directoryhere/Camera/77389-garage.jpg -ISO 200 -ev 10'
			os.system(TakePic)
			response = client.files_upload(
			channels='#arcturus-bob',
			file="/home/pi/Scripts/Camera/77389-garage.jpg",
			media="file",
			initial_comment="movement screenshot : " + str(datetime.datetime.now()))
			assert response["ok"]
			
			time.sleep(2)

			# --- Turn off lights  ---
			url = "http://" + hue_ip + "/api/apikeyhere/lights/14/state"
			payload = "{\"on\":false, \"bri\":254}"
			headers = {
			'Content-Type': 'text/plain'
			}
			response_hue = requests.request("PUT", url, headers=headers, data = payload)
			assert response_hue.status_code == 200 
			

				

except AssertionError as e:
    
    slack_msg = {'text' : 'Bob the Bouncer (iothub bypass) | Hue lights error: router ip changed! Please reconfigure. : ' + str(datetime.datetime.now())}
    requests.post(webhook_url, data=json.dumps(slack_msg))

    
    logging.error("AssertionError but I can't quit...", exc_info=True)
    print("AssertionError encountered : " + str(e))

    raise e
    exit(1)
    
except SlackApiError as e:
	slack_msg = {'text' : 'Bob the Bouncer (iothub bypass) | PIR Motion sensor : Slack API exception occurred : ' + str(datetime.datetime.now()) + " | " + str(e)}
	requests.post(webhook_url, data=json.dumps(slack_msg))


	raise e
except:
	err = sys.exc_info()[0]
	slack_msg = {'text' : 'Bob the Bouncer (iothub bypass) | Exception occurred : ' + str(datetime.datetime.now()) + " | " + str(err)}
	requests.post(webhook_url, data=json.dumps(slack_msg))
	
	
	raise
finally:
	postUptime()

	# --- Turn off lights  ---
	url = "http://" + hue_ip + "/api/apikeyhere/lights/14/state"
	payload = "{\"on\":false, \"bri\":254}"
	headers = {
	'Content-Type': 'text/plain'
	}
	response_hue = requests.request("PUT", url, headers=headers, data = payload)
	assert response_hue.status_code == 200 
	os.execv(__file__, sys.argv) #20200605 : Heal process and restart
