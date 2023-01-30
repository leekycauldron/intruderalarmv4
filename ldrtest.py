#!/usr/local/bin/python

import RPi.GPIO as GPIO
from discord_webhook import DiscordWebhook
import time
import threading
import paho.mqtt.client as mqtt
from urllib.parse import DefragResult, urlparse
import socket, os, datetime, requests
import http.client as httplib
from urllib.parse import urlencode
from picamera import PiCamera

camera = PiCamera()

user = ""
passwd = ""
port = 00000

arm = False

def on_connect(client, userdata, flags, rc):
    print("rc: " + str(rc))

def on_message(client, obj, msg):
    global arm
    print(msg.payload.decode('utf-8'))
    if msg.payload.decode('utf-8') == "arm":
        arm = True
        mqttc.publish(topic, "armed")
    elif msg.payload.decode('utf-8') == "disarm":
        arm = False
        mqttc.publish(topic, "disarmed")

def on_publish(client, obj, mid):
    print("mid: " + str(mid))

def on_subscribe(client, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(client, obj, level, string):
    print("mqtt log {}".format(string))


mqttc = mqtt.Client()


def getImage():
    now = int(time.time())
    try:
        camera.capture(f"{now}.jpg")
        return str(now)
    except: return False

def send_pushover(sender="Intruder Alarm", subject="", img_path=""):
    try:
        
        r = requests.post("https://api.pushover.net/1/messages.json", data={"token":"","user":"","message":subject}, files={"attachment":open(img_path,"rb")})
    
        return True
    except Exception as e:
        return False

# Assign event callbacks
mqttc.on_message = on_message
mqttc.on_connect = on_connect
mqttc.on_publish = on_publish
mqttc.on_subscribe = on_subscribe

url_str = "http://tailor.cloudmqtt.com"
url = urlparse(url_str)
topic = url.path[1:] or 'ia'
# Connect
mqttc.username_pw_set(user, passwd)

def connect():
    print("Connected to MQTT...")
    mqttc.connect("tailor.cloudmqtt.com", port)
    mqttc.subscribe(topic,0)


GPIO.setmode(GPIO.BCM)

#define the pin that goes to the circuit

pin_to_circuit = 14
buzzer_pin = 15
alarm = False

GPIO.setup(buzzer_pin, GPIO.OUT)
buzzer = GPIO.PWM(buzzer_pin, 440)

def playBuzzer():
    while True:
        if alarm:
            buzzer.start(50)
            time.sleep(0.1)
        buzzer.stop()
        time.sleep(0.1)

def mqttloop():
    while True:
        try:
            connect()
            rc = 0
            while rc == 0:
                rc = mqttc.loop()
                
            print("rc: " + str(rc))
        except Exception as e:
            print(e)

sending = False

def sendAlert():
        sending = True
        fname = getImage()
        #print(send_pushover(subject="Tripwire crossed.", img_path=fname+".jpg")) # PUSHOVER
        webhook = DiscordWebhook(url='https://discord.com/api/webhooks//--wCvTB4fGQcsTQIr', content='<@> Tripwire Crossed!!! https://tenor.com/view/spongebob-patrick-panic-run-scream-gif-4656335')
        response = webhook.execute() # DISCORD
        mqttc.publish(topic, "alert") # MQTT 
        sending = False

def rc_time (pin_to_circuit):
    global alarm
    count = 0
  
    #Output on the pin for 
    GPIO.setup(pin_to_circuit, GPIO.OUT)
    GPIO.output(pin_to_circuit, GPIO.LOW)
    time.sleep(0.1)

    #Change the pin back to input
    GPIO.setup(pin_to_circuit, GPIO.IN)
  
    #Count until the capactior discharges
    while (GPIO.input(pin_to_circuit) == GPIO.LOW):
        count += 1
    if count != 0: 
        # IF the alarm just started going off AND the alarm is not already sending a pushover, send it
        if alarm == False and sending == False:
            if arm:
                threading.Thread(target=sendAlert).start()
                alarm = True
        # IF the alarm just started going off AND the alarm is already sending a pushover, don't send it and keep the alarm off
        elif alarm == False and sending == True:
            alarm = False
        # IF the alarm is already going off, keep it going off.
        else:
            if arm:
                alarm = True
            else: alarm = False
        
    else: alarm = False
    return count




#Catch when script is interrupted, cleanup correctly
if __name__ == "__main__":
    threading.Thread(target=playBuzzer,daemon=True).start()
    threading.Thread(target=mqttloop,daemon=True).start()
    try:
        while True:
            print(rc_time(pin_to_circuit)) # get laser value
        
    except KeyboardInterrupt: pass
    finally: GPIO.cleanup()
