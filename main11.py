import RPi.GPIO as GPIO
import cv2, os
import numpy as np
from PIL import Image
import telebot
import time
from RPi_GPIO_i2c_LCD import lcd
from time import sleep
import threading
import os
import json
import random
import serial
import adafruit_fingerprint

#inisialisasi alat
lcdDisplay = lcd.HD44780(0x27)
uart = serial.Serial("/dev/ttyS0", baudrate=57600, timeout=1)
finger = adafruit_fingerprint.Adafruit_Fingerprint(uart)

# Inisialisasi bot Telegram
bot = telebot.TeleBot("6354339926:AAGJt4Mxbe5hxdDMnIlhQSkLsNP286f46rM")

# Konfigurasi pin GPIO
relay_pin = 27
vibration_pin = 17
ultrasonic_trig_pin = 23
ultrasonic_echo_pin = 24
push_button = 21

# Inisialisasi pin GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(relay_pin, GPIO.OUT)
GPIO.setup(vibration_pin, GPIO.IN)
GPIO.setup(ultrasonic_trig_pin, GPIO.OUT)
GPIO.setup(ultrasonic_echo_pin, GPIO.IN)
GPIO.setup(push_button, GPIO.IN,pull_up_down=GPIO.PUD_UP)

# Konfigurasi sensor getaran SW-18010P
GPIO.add_event_detect(vibration_pin, GPIO.BOTH, bouncetime=300)

#global variable
GLOBAL_ID_USER_FINGER = None 
GLOBAL_ID_USER_FACE = None
GLOBAL_AUTH_FINGER = False
GLOBAL_AUTH_FACE = False
GLOBAL_STOP_LOOP = False

def checkFile():
    global GLOBAL_AUTH_FINGER
    global GLOBAL_AUTH_FACE
    global GLOBAL_STOP_LOOP
    
    GLOBAL_AUTH_FINGER = False
    GLOBAL_AUTH_FACE = False
    GLOBAL_STOP_LOOP = False
    
    if os.path.exists("training.xml") and os.path.exists("data.json") and os.path.exists("dataJari.json"):
        print("file ada")
        lcdDisplay.set("Initiate       ",1)
        lcdDisplay.set("Success         ",2)
        time.sleep(5)
        authentication()
    else:
        lcdDisplay.set("Initiate        ",1)
        lcdDisplay.set("Error       ",2)
        print("File Tidak ada")

#menambahkan data sidik jari
def enroll_finger(nama):
    print("masuk enroll finger")
    lcdDisplay.set("Add             ",1)
    lcdDisplay.set("Finger          ",2)
    time.sleep(3)
    """Take a 2 finger images and template it, then store in specified location"""
    location = random.randint(1, 254)  # Menggunakan bilangan bulat acak

    # menginput data json baru
    with open('dataJari.json', 'r') as file:
        data = json.load(file)
        
    data_baru = {
        "id": location,
        "nama": nama
    }
    
    data.append(data_baru)
    with open('dataJari.json', 'w') as file:
        json.dump(data, file, indent=4)

    print("Data Jari baru berhasil ditambahkan ke JSON.")

    for fingerimg in range(1, 3):
        if fingerimg == 1:
            lcdDisplay.set("Place           ",1)
            lcdDisplay.set("Finger          ",2)
            print("Place finger on sensor...", end="")
        else:
            lcdDisplay.set("Place           ",1)
            lcdDisplay.set("Finger Again    ",2)
            print("Place same finger again...", end="")

        while True:
            i = finger.get_image()
            if i == adafruit_fingerprint.OK:
                lcdDisplay.set("Finger          ",1)
                lcdDisplay.set("Taken           ",2)
                print("Image taken")
                time.sleep(2)
                break
            if i == adafruit_fingerprint.NOFINGER:
                print(".", end="")
            elif i == adafruit_fingerprint.IMAGEFAIL:
                print("Imaging error")
                lcdDisplay.set("Image           ",1)
                lcdDisplay.set("Error           ",2)
                time.sleep(2)
                return False

        print("Templating...", end="")
        i = finger.image_2_tz(fingerimg)
        if i == adafruit_fingerprint.OK:
            print("Templated")
        else:
            if i == adafruit_fingerprint.IMAGEMESS:
                print("Image too messy")
            elif i == adafruit_fingerprint.FEATUREFAIL:
                print("Could not identify features")
            elif i == adafruit_fingerprint.INVALIDIMAGE:
                print("Image invalid")
            else:
                print("Other error")
            return False

        if fingerimg == 1:
            print("Remove finger")
            lcdDisplay.set("Remove          ",1)
            lcdDisplay.set("Finger          ",2)
            time.sleep(1)
            while i != adafruit_fingerprint.NOFINGER:
                i = finger.get_image()

    lcdDisplay.set("Creating         ",1)
    lcdDisplay.set("Model            ",2)
    print("Creating model...", end="")
    time.sleep(2)
    i = finger.create_model()
    if i == adafruit_fingerprint.OK:
        print("Created")
        lcdDisplay.set("Image           ",1)
        lcdDisplay.set("Create          ",2)
        time.sleep(2)
    else:
        if i == adafruit_fingerprint.ENROLLMISMATCH:
            lcdDisplay.set("Image           ",1)
            lcdDisplay.set("not Match       ",2)
            print("Prints did not match")
        else:
            lcdDisplay.set("Error           ",1)
            lcdDisplay.set("-               ",2)
            print("Other error")
        return False

    print(f"Storing model at ID #{location}...", end="")
    i = finger.store_model(location)
    if i == adafruit_fingerprint.OK:
        lcdDisplay.set("Finger              ",1)
        lcdDisplay.set("Stored              ",2)
        print("Stored")
    else:
        if i == adafruit_fingerprint.BADLOCATION:
            lcdDisplay.set("Error            ",1)
            lcdDisplay.set("Store             ",2)
            print("Bad storage location")
        elif i == adafruit_fingerprint.FLASHERR:
            lcdDisplay.set("Error             ",1)
            lcdDisplay.set("Store            ",2)
            print("Flash storage error")
        else:
            lcdDisplay.set("Error            ",1)
            lcdDisplay.set("Store            ",2)
            print("Other error")
        return False

    return True

def get_fingerprint():
    global GLOBAL_ID_USER_FINGER
    global GLOBAL_AUTH_FINGER
    global GLOBAL_STOP_LOOP
    status = False
    relay_status = False
    statusVibration = False
    vibration_start_time = 0
    
    try:
        """Get a finger print image, template it, and see if it matches!"""
        print("Waiting for image...")
        while finger.get_image() != adafruit_fingerprint.OK or not GLOBAL_STOP_LOOP:
            
            #untuk button buka
            inputValue = GPIO.input(21)
            if (inputValue == False):
                print("Button press ")
                threading.Thread(target=relayAction).start()
            
            if GPIO.event_detected(vibration_pin):
                bot.send_message("5499814195", "Ada yang mencoba untuk mendobrak pintu")
                print("dobrak pintu")
                statusVibration = True
                vibration_start_time = time.time()
                
            if statusVibration == True:
                # Deteksi jarak ultrasonik
                GPIO.output(ultrasonic_trig_pin, True)
                time.sleep(0.00001)
                GPIO.output(ultrasonic_trig_pin, False)

                while GPIO.input(ultrasonic_echo_pin) == 0:
                    pulse_start = time.time()

                while GPIO.input(ultrasonic_echo_pin) == 1:
                    pulse_end = time.time()

                pulse_duration = pulse_end - pulse_start
                distance = pulse_duration * 17150

                if distance < 5: #jarak ultrasonic satuan cm
                    bot.send_message("5499814195", "Pintu berhasil dibobol")
                    print("pintu dibobol")
                
                if time.time() - vibration_start_time >= 10:
                    statusVibration = False
                    print("status Vibration False")
            pass
        print("Templating...")
        if finger.image_2_tz(1) != adafruit_fingerprint.OK and GLOBAL_STOP_LOOP is not True:
            lcdDisplay.set("Finger is not    ",1)
            lcdDisplay.set("Registered       ",2)
            print("Citra Sidik Jari berantakan")
            bot.send_message("5499814195", "Jari tidak terdaftar")
            get_fingerprint()
        print("Searching...")
        if finger.finger_search() != adafruit_fingerprint.OK and GLOBAL_STOP_LOOP is not True:
            print("Sidik jari tidak terdaftar")
            bot.send_message("5499814195", "Jari tidak terdaftar")
            lcdDisplay.set("Finger is not    ",1)
            lcdDisplay.set("Registered       ",2)
            get_fingerprint()
                
        namaJari = searchDataJari(finger.finger_id)
        print("Sidik jari terdeteksi")
        print("ID:", finger.finger_id, "Confidence:", finger.confidence)
        bot.send_message("5499814195", "atas nama "+str(namaJari)+" masuk menggunakan Fingerprint")
        lcdDisplay.set("Finger is       ",1)
        lcdDisplay.set("Registered      ",2)
        time.sleep(1.5)
        lcdDisplay.set("Authentication   ",1)
        lcdDisplay.set("Success          ",2)
        GLOBAL_AUTH_FINGER = True
        GLOBAL_ID_USER_FINGER = int(finger.finger_id)
        return True
    except Exception as e:
        bot.send_message("5499814195", "Terjadi Error DI get_fingerprint")
        print("error = "+str(e))
    
# Fungsi untuk mengambil gambar data
def ambil_gambar(nama):
    print("masuk fungsi ambil gambar")
    lcdDisplay.set("Take Picture     ",1)
    lcdDisplay.set("Success          ",2)
    camera = 0
    video = cv2.VideoCapture(camera)

    if not video.isOpened():
        print("Gagal membuka kamera.")
        return

    faceDeteksi = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    
    # Menghasilkan ID bilangan bulat acak
    id = random.randint(1, 254)  # Menggunakan bilangan bulat acak

    # menginput data json baru
    with open('data.json', 'r') as file:
        data = json.load(file)
        
    data_baru = {
        "id": id,
        "nama": nama
    }
    
    data.append(data_baru)
    with open('data.json', 'w') as file:
        json.dump(data, file, indent=4)

    print("Data baru berhasil ditambahkan ke JSON.")
    
    a = 0
    while True:
        a = a + 1
        check, frame = video.read()

        if not check:
            print("Gagal membaca frame.")
            break

        abu = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        wajah = faceDeteksi.detectMultiScale(abu, 1.3, 5)

        for (x, y, w, h) in wajah:
            wajah_cropped = frame[y:y+h, x:x+w]

            # Simpan gambar dengan menggunakan ID bilangan bulat
            cv2.imwrite('DataSet/User.' + str(id) + '.' + str(a) + '.jpg', wajah_cropped)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            print("masuk")
            lcdDisplay.set("Take Picture       ",1)
            lcdDisplay.set(str(a),2)

        cv2.imshow("Face Recognition", frame)

        if a > 100:
            break

    video.release()
    cv2.destroyAllWindows()
    latih_model()
    print("fungsi ambil gambar berakhir")

# Fungsi untuk melatih model pengenalan wajah
def latih_model():
    print("masuk fungsi latih model")
    recognizer = cv2.face_LBPHFaceRecognizer.create()
    detector = cv2.CascadeClassifier("haarcascade_frontalface_default.xml")

    def getImagesWithLabels(path):
        imagePaths = [os.path.join(path, f) for f in os.listdir(path)]
        faceSamples = []
        Ids = []
        for imagePath in imagePaths:
            pilImage = Image.open(imagePath).convert('L')
            imageNp = np.array(pilImage, 'uint8')
            Id = int(os.path.split(imagePath)[-1].split(".")[1])
            faces = detector.detectMultiScale(imageNp)
            for (x, y, w, h) in faces:
                faceSamples.append(imageNp[y:y + h, x:x + w])
                Ids.append(Id)
        return faceSamples, Ids

    faces, Ids = getImagesWithLabels('DataSet')
    recognizer.train(faces, np.array(Ids))
    recognizer.save('training.xml')
    print("masuk fungsi latih model")

def relayAction():
    GPIO.output(relay_pin, GPIO.HIGH)
    relay_status = True
    time.sleep(10)
    GPIO.output(relay_pin, GPIO.LOW)
    print("udahan relay")
    
def searchDataMuka(id):
    with open('data.json', 'r') as file:
        data = json.load(file)

    # Iterasi melalui elemen-elemen dalam JSON
    for item in data:
        if item['id'] == id:
            print(item['nama'])
            return item['nama']
    else:
        print("ID tidak ditemukan")
        return False

def searchDataJari(id):
    with open('dataJari.json', 'r') as file:
        data = json.load(file)

    # Iterasi melalui elemen-elemen dalam JSON
    for item in data:
        if item['id'] == id:
            print(item['nama'])
            return item['nama']
    else:
        print("ID tidak ditemukan")
        return False

def authCamera():
    global GLOBAL_AUTH_FACE
    global GLOBAL_ID_USER_FACE
    global GLOBAL_STOP_LOOP
    camera = 0
    video = cv2.VideoCapture(camera)
    faceDeteksi = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    recognizer = cv2.face_LBPHFaceRecognizer.create()
    recognizer.read('training.xml')
    a = 0
    detected_face = None
    detected_start_time = None
    status = False
    relay_status = False
    statusVibration = False
    vibration_start_time = 0
    
    #authCamera
    while not GLOBAL_STOP_LOOP:
        a = a + 1
        check, frame = video.read()
        abu = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        wajah = faceDeteksi.detectMultiScale(abu, 1.3, 5)
        
        #untuk button buka
        inputValue = GPIO.input(21)
        if (inputValue == False):
            print("Button press ")
            threading.Thread(target=relayAction).start()

        for (x, y, w, h) in wajah:
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            id, conf = recognizer.predict(abu[y:y+h, x:x+w])
            if conf < 50:
                id = id
                cv2.putText(frame, str(id) + "=" + str(conf), (x + 40, y - 10), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0))
                if detected_face is None:
                    detected_face = frame[y:y+h, x:x+w]
                    detected_start_time = a
                elif a - detected_start_time >= 5:
                    takeName = searchDataMuka(int(id))
                    
                    if takeName is not False:
                        cv2.imwrite('detected_face.jpg', detected_face)
                        bot.send_photo("5499814195", photo=open('detected_face.jpg', 'rb'))
                        bot.send_message("5499814195", "Atas nama " + takeName + " telah memasuki ruangan")
                        status = True
                        if not relay_status:
                            lcdDisplay.set("Authentication  ",1)
                            lcdDisplay.set("Success         ",2)
                            GLOBAL_AUTH_FACE = True
                            threading.Thread(target=relayAction).start()
                            GLOBAL_ID_USER_FACE = int(id)
                        break
                    else:
                        cv2.imwrite('detected_face.jpg', detected_face)
                        bot.send_photo("5499814195", photo=open('detected_face.jpg', 'rb'))
                        bot.send_message("5499814195", "terjadi kesalahan Data muka tidak ditemukan")
                        lcdDisplay.set("Authentication",1)
                        lcdDisplay.set("Failed",2)
                        break
            else:
                detected_face = None

        # Deteksi gerakan
        if GPIO.event_detected(vibration_pin):
            bot.send_message("5499814195", "Ada yang mencoba untuk mendobrak pintu")
            print("dobrak pintu")
            statusVibration = True
            vibration_start_time = time.time()
            
        if statusVibration == True:
            # Deteksi jarak ultrasonik
            GPIO.output(ultrasonic_trig_pin, True)
            time.sleep(0.00001)
            GPIO.output(ultrasonic_trig_pin, False)

            while GPIO.input(ultrasonic_echo_pin) == 0:
                pulse_start = time.time()

            while GPIO.input(ultrasonic_echo_pin) == 1:
                pulse_end = time.time()

            pulse_duration = pulse_end - pulse_start
            distance = pulse_duration * 17150

            if distance < 5: #jarak ultrasonic satuan cm
                bot.send_message("5499814195", "Pintu berhasil dibobol")
                print("pintu dibobol")
            
            if time.time() - vibration_start_time >= 10:
                statusVibration = False
                print("status Vibration False")

        #cv2.imshow("Face Recognition", frame)
        key = cv2.waitKey(1)
        if key == ord('a') or status:
            break
            
        if key == ord('y') or status:
            changeStatusFinger()

    video.release()
    cv2.destroyAllWindows()
    
# Fungsi untuk melakukan pemindaian wajah
def authentication():
    global GLOBAL_ID_USER_FINGER
    global GLOBAL_ID_USER_FACE
    global GLOBAL_STOP_LOOP
    
    print("masuk function authentication")
    lcdDisplay.set("Authentication  ",1)
    lcdDisplay.set("Ready           ",2)
    
    if GLOBAL_STOP_LOOP is not True:
        # Membuat dan memulai thread untuk get_fingerprint
        fingerprint_thread = threading.Thread(target=get_fingerprint)
        fingerprint_thread.start()

    # Menunggu sampai thread get_fingerprint selesai
    fingerprint_thread.join()

    if GLOBAL_STOP_LOOP is not True:
        # Setelah thread get_fingerprint selesai, lanjut ke authCamera
        auth_camera_thread  = threading.Thread(target=authCamera)
        auth_camera_thread.start()
    
    # Menunggu sampai thread get_fingerprint selesai
    auth_camera_thread.join()
    
    #status_detect_finger = threading.Event()
    print("user finger = " + str(GLOBAL_ID_USER_FINGER))
    print("user face = " + str(GLOBAL_ID_USER_FACE))


@bot.message_handler(commands=['startService'])
def start_service_command(message):
    checkFile()
    
@bot.message_handler(commands=['stopService'])
def start_service_command(message):
    global GLOBAL_STOP_LOOP
    GLOBAL_STOP_LOOP = True
    
@bot.message_handler(commands=['ambilGambar'])
def ambil_gambar_command(message):
    bot.reply_to(message, "Silakan masukkan nama Anda:")
    bot.register_next_step_handler(message, handle_nama_input)

def handle_nama_input(message):
    nama = message.text
    ambil_gambar(nama)

@bot.message_handler(commands=['scanWajah'])
def ambil_gambar_command(message):
    authentication()
    
@bot.message_handler(commands=['scanJari'])
def scan_jari_command(message):
    if get_fingerprint():
        print("Detected #", finger.finger_id, "with confidence", finger.confidence)
    else:
        print("Finger not found")
    
@bot.message_handler(commands=['tambahJari'])
def add_finger(message):
    bot.reply_to(message, "Silakan masukkan nama untuk Jari yang didaftarkan:")
    bot.register_next_step_handler(message, handle_nama_input_jari)

def handle_nama_input_jari(message):
    nama = message.text
    enroll_finger(nama)

# Handler untuk perintah /start dan /help
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    bot.reply_to(message, "Howdy, how are you doing?")

# Handler untuk perintah /halo
@bot.message_handler(commands=['halo'])
def send_welcome(message):
    print("chatid = "+str(message.chat.id))
    bot.reply_to(message, "knp lol?")

# Handler umum
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    bot.reply_to(message, message.text)

GPIO.output(relay_pin, GPIO.LOW)
bot.infinity_polling()
