import time
import RPi.GPIO as gpio
import os
import json
import logging
import threading
import pathlib
import serial
import subprocess
import paho.mqtt.client as mqtt
import pocketsphinx
from pocketsphinx import LiveSpeech
from multiprocessing import Process
import xml.etree.ElementTree as ET
from pydub import AudioSegment, silence

working_env = str(pathlib.Path(__file__).parent.absolute())
#
print(working_env)

# INICIA O DAEMON DO PULSEAUDIO
subprocess.call(["sudo /usr/bin/pulseaudio --start --log-target=syslog --system=false"], shell=True)

# SERIAL COMMUNICATION SETTINGS
serial_port = "/dev/ttyACM0"
baudrate    = 9600
ser         = serial.Serial(serial_port, baudrate)

# TRANSMISSION SETTINGS
tree = ET.parse(working_env+"/settings.xml")
root = tree.getroot()
current_freq   = int(root[0][0].text)
current_qos = int(root[0][1].text)
ready_to_update = True
free_to_recognize = True

# MQTT SETTINGS
broker      = "192.168.2.11" # ATENTAR PARA MUDAR ESSE PARÂMETRO
client_name = "MAIA CHANNEL 005"
mqtt_user   = "mqtt-test"
mqtt_pwd    = "mqtt-test"
mqtt_port   = 1883
keep_alive_broker = 60

# SPHINX SETTINGS
hmm  = working_env+"/model/pt_br"
lm   = working_env+"/model/data_lmtool_mensagem.lm.bin"
dict = working_env+"/model/data_lmtool_mensagem.dic"
new_command = []

# LED SETTINGS
REQ_LED_PIN = 32
gpio.setmode(gpio.BOARD)
gpio.setup(REQ_LED_PIN, gpio.OUT)
sign = gpio.PWM(REQ_LED_PIN, 120)

CON_LED_PIN = 35
gpio.setmode(gpio.BOARD)
gpio.setup(CON_LED_PIN, gpio.OUT)
sign_2 = gpio.PWM(CON_LED_PIN, 120)

lines = {
            "GLUM":         "GL1",
            "GLDOIS":       "GL2",
            "GLTRES":       "GL3",
            "GLQUATRO":     "GL4",
            "GLCINCO":      "GL5",
            "GLSEIS":       "GL6",
            "GLSETE":       "GL7",
            "GLOITO":       "GL8",
            "GLNOVE":       "GL9",
            "GLDEZ":       "GL10",
            "GLONZE":      "GL11",
            "GLDOZE":      "GL12",
            "GLTREZE":     "GL13",
            "GLQUATORZE":  "GL14",
            "GLQUINZE":    "GL15",
            "GLDEZESSEIS": "GL16",
            "GLDEZESSETE": "GL17",
            "GLDEZOITO":   "GL18",
            "GLDEZENOVE":  "GL19",
            "GLVINTE":     "GL20",
        }

messages =  {
                "REUNIAO" :   3,
                "CAFE":       1,
                "ERGONOMICA": 2
            }


# FUNCTIONS
def update(new_freq, new_qos):
    global current_freq
    global current_qos

    tree = ET.parse(working_env+"/settings.xml")
    root = tree.getroot()

    if (new_freq != current_freq):
        current_freq = new_freq
        root[0][0].text = str(new_freq)

        if (new_qos != current_qos):
            current_qos = new_qos
            root[0][1].text = str(new_qos)

        tree.write(working_env+"/settings.xml")
        msg = create_json(1, new_freq, 0)
        ser.write(msg.encode("utf-8"))

    elif (new_qos != current_qos):
        current_qos = new_qos
        root[0][1].text = str(new_qos)
        tree.write(working_env+"/settings.xml")


# MQTT FUNCTIONS
def on_log(client, userdata, level, buf):
    print("log: ", buf)


def on_connect(client, userdata, flags, rc):
    print("[STATUS] Broker connected. Conection results: "+str(rc))
    client.subscribe("maia/mc_update", qos=1)
    sign_2.start(20)


def on_message(client, userdata, msg):
    f_key = "freq"
    qos_key = "qos_value"
    try:
        payload = json.loads(msg.payload)
        if f_key and qos_key in payload:
            attempts = 3
            while(attempts > 0):
                if ready_to_update:
                    attempts = 0
                    update(payload[f_key], payload[qos_key])
                else:
                    attempts = attempts - 1
                    time.sleep(6)

    except:
        pass
        print ("Mensagem fora de padrão")


def send_mqtt_msg(dest, msg):
    client.publish("maia/notificacoes", json.dumps({"linha": dest, "msg":msg}), current_qos)


def look_for_correction(audio_path):
    audio = AudioSegment.from_wav(audio_path)
    s = silence.detect_silence(audio, min_silence_len=1000, silence_thresh=-28)
    s = [((start / 1000), (stop / 1000)) for start, stop in s]  # convert to sec
    silence_len = 0.98 * (len(audio)/1000) #O áudio será considerado silêncio se pelo menos 98% for silêncio

    if len(s) == 0:
        return True

    else:
        interval = 0
        for x in s:
            print(x)
            interval =  interval + (x[1] - x[0])

        if interval >= silence_len:
            return False

        return True


def play_audio(audio_name):
    audio_name+= ".wav"
    dir = working_env+"/audios/"+audio_name
    os.system("aplay "+dir)


def create_json(op_mode, freq, time_):
    """
    op_mode: can be equals to 0 or 1. The  first  case  is used to  make  a transmission,
    on the specified frequency, during the time given (in milliseconds); the second value
    is used to change the MAIA channel frequency, so in  this case  the time is not used.

    {"op_mode":0,"freq":462562,"time_":3000}

    """

    json_msg = {
                    "op_mode": op_mode,
                    "freq":    freq,
                    "time_":   time_
                }

    return str(json_msg)


def send_feedback(topic, msg):
    ser_msg = create_json(0, 0, 5500)  # Gera uma mensagem com a estrutura Json
    ser.write(ser_msg.encode("utf-8")) # Envia a mensagem pro Arduíno
    time.sleep(1.1) # Espera o Arduíno configurar o modo transmissor antes de reproduzir os áudios

    play_audio(lines[topic])
    time.sleep(1)

    play_audio(msg)
    time.sleep(1.5)


def handle():
    global new_command
    global free_to_recognize
    global ready_to_update

    while(True):
        if (len(new_command)):
            sign.start(3)

            print("[INFO] Comando válido detectado")
            print(new_command)

            send_feedback(new_command[0], new_command[1])
            time.sleep(2)
            print("[INFO] Realizando captura do áudio de correção...")
            pocketsphinx.capture[0] = True
            time.sleep(6)

            print("Chamando função de correção...")
            correction = look_for_correction("sphx_capture.wav")

            os.system("rm sphx_capture.wav")

            if correction:
                print ("Correção realizada!")
                ser_msg = create_json(0, 0, 3000)
                ser.write(ser_msg.encode("utf-8"))
                time.sleep(1.1)
                play_audio("BEEP")

                free_to_recognize = True
                ready_to_update = True
                new_command = []

            else:
                print ("Nenhuma correção realizada.\nPublicando mensagem ...")
                print(f'Tópico: {new_command[0]} | Mensagem: {new_command[1]}')
                send_mqtt_msg(lines[new_command[0]], messages[new_command[1]])

                free_to_recognize = True
                ready_to_update = True
                new_command = []

            sign.stop()


def main():
    global new_command
    global free_to_recognize
    global ready_to_update

    recognizer = LiveSpeech(verbose=False, sampling_rate=16000, buffer_size=2048,
                        no_search=False, full_utt=False, hmm=hmm, lm=lm, dic=dict)

    for phrase in recognizer:
        if free_to_recognize:
            # O menor comando válido possui 10 caracteres em sua estrutura
            # Essa verificação descarta processamento desnecessário com ruídos

            if len(str(phrase))>=10:

                dest = False
                msg = False
                voice_command = str(phrase)
                # Verifica se uma linha existe no comando
                for elem in lines:
                    if elem in voice_command:
                        dest = elem
                        break

                # Verifica se uma mensagem existe no comando
                for elem in messages:
                    if elem in voice_command:
                        msg = elem
                        break

                # Agora é verificado se um comando possui os dois parâmetros mínimos:
                # linha + mensagem
                if dest and msg:
                    new_command = list((dest, msg))
                    free_to_recognize = False
                    ready_to_update = False


print("[STATUS] Initializing MQTT...")

client = mqtt.Client(client_name)
client.on_log = on_log
client.on_connect = on_connect
client.username_pw_set(mqtt_user, mqtt_pwd)
client.on_message = on_message
client.connect(broker, mqtt_port, keep_alive_broker)
client.loop_start()


t = threading.Thread(target=handle, daemon=True)
t.start()
main()

