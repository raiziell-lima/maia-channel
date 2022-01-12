import os
import time
import pathlib
import subprocess
import RPi.GPIO as gpio
from multiprocessing import Process

curr_env = str(pathlib.Path(__file__).parent.absolute())

arduino_file = "maia_channel.ino"
files = [arduino_file, "maia_channel.py", "model"]

# LED SETTINGS
PWR_LED_PIN = 33
gpio.setmode(gpio.BOARD)
gpio.setup(PWR_LED_PIN, gpio.OUT)
sign = gpio.PWM(PWR_LED_PIN, 120)
sign.start(0.1)

def blink():
    PWR_LED_PIN = 33
    gpio.setmode(gpio.BOARD)
    gpio.setup(PWR_LED_PIN, gpio.OUT)
    sign = gpio.PWM(PWR_LED_PIN, 120)

    while True:
        sign.start(0.1)
        time.sleep(0.5)

        sign.stop()
        time.sleep(0.25)

#OK
def detect_usb_fdrive():
   if os.path.exists("/dev/sda"):
       print("\n[INFO] Device detected")
       return True
   else:
       print("[INFO] No device detected")
       return False

#OK
def mount_storage_device():
    print("[STATUS] Mounting storage device...")
    process = subprocess.call(["sudo mount /dev/sda1 /media/maia"], shell=True)
    print("[INFO] Done\n")

#OK
def get_existing_files():
    update_dir = "/media/maia/update"
    if os.path.exists(update_dir):
        print("[STATUS] Getting existing files...")
        files_list = os.listdir(update_dir)
        if files_list:
            print("[INFO] Existing files:")
            for file in files_list:
                print(file)
            print("[INFO] Done\n")
            return files_list
        return False
    return False

#OK
def update_files(files_list):
    print("[STATUS] Updating files...")
    for file in files:
        if file in files_list:
            if file == arduino_file:
                update_arduino_fmw()
            else:
                print("[STATUS] Removing current file/directory...")
                print(f"rm -r {curr_env}/{file}")
                process = subprocess.call([f"rm -r {curr_env}/{file}"], shell=True)

                print("[STATUS] Copying new file/directory...")
                print(f"cp -r /media/maia/update/{file} {curr_env}/{file}")
                process = subprocess.call([f"cp -r /media/maia/update/{file} {curr_env}/{file}"], shell=True)
                time.sleep(2)

#OK
def update_arduino_fmw():
    try:
        print(f"rm {curr_env}/sketchbook/*.ino")
        process = subprocess.call([f"rm {curr_env}/sketchbook/*.ino"], shell=True)

    except:
        pass

    process = subprocess.call([f"cp /media/maia/update/{arduino_file} {curr_env}/sketchbook"], shell=True)
    os.chdir(f"{curr_env}/sketchbook") # Vai até o diretório onde se encontram os arquivos do arduino

    if os.path.exists(f"{curr_env}/sketchbook/build-uno/"):
        print('[INFO] Directory "build-uno" exists!')
        print("[STATUS] Deleting directory...")
        process = subprocess.call(["make clean"], shell=True)
        print("[INFO] Directory deleted successfully!")

    print("[STATUS] Creating directory...")
    process = subprocess.call(["make"], shell=True)
    print("[INFO] Directory created successfully!")

    print("[STATUS] Uploading to the board...")
    process = subprocess.call(["make upload"], shell=True)
    print("[INFO] The upload is done!")

    process = subprocess.call(["make clean"], shell=True)
    print("[INFO] The process is finished!")

#OK
def umount_storage_device():
    print("[STATUS] Unmounting storage device...")
    process = subprocess.call(["sudo umount /dev/sda1"], shell=True)
    print("[INFO] Storage device umounted")

#OK
def eject_storage_device():
    print("[STATUS] Ejecting storage device...")
    process = subprocess.call(["sudo udisksctl power-off -b /dev/sda"], shell=True)
    if not process:
        print("[INFO] Device ejected")

#OK
def main():
    if detect_usb_fdrive():
        mount_storage_device()
        files_list = get_existing_files()
        print (files_list)

        time.sleep(1)

        if files_list:
            sign.stop()
            blink_state = Process(target=blink)
            blink_state.start()

            print("[STATUS] Stopping main application...")
            process = subprocess.call(["sudo systemctl stop maia_channel.service"], shell=True)
            time.sleep(1)

            update_files(files_list)

            process = subprocess.call(["sudo systemctl daemon-reload"], shell=True)
            process = subprocess.call(["sudo systemctl start maia_channel.service"], shell=True)
            blink_state.terminate()
            sign.start(0.1)

        else:
            print("[INFO] No files to be updated...")

        umount_storage_device()
        eject_storage_device()
        print("[INFO] Done!\n\n")

    time.sleep(1)


if __name__ == "__main__":
    while True:
        main()