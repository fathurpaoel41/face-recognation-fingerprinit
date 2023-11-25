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
import shutil

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
GLOBAL_ADD_NEW_ID_USER = None
GLOBAL_ADD_NEW_NAME_USER = None
GLOBAL_DATA_JSON = None

def checkFile():
    global GLOBAL_AUTH_FINGER
    global GLOBAL_AUTH_FACE
    global GLOBAL_STOP_LOOP
    
    GLOBAL_AUTH_FINGER = False
    GLOBAL_AUTH_FACE = False
    GLOBAL_STOP_LOOP = False
    
    if os.path.exists("training.xml") and os.path.exists("data.json") and os.path.exists("dataJari.json"):
        print("file ada")
        lcdDisplay.set("Initiate        ",1)
        lcdDisplay.set("Success         ",2)
        time.sleep(1)
        authentication()
    else:
        lcdDisplay.set("Initiate        ",1)
        lcdDisplay.set("Error           ",2)
        print("File Tidak ada")
        
def check_id(new_name):
    global GLOBAL_ADD_NEW_ID_USER
    global GLOBAL_ADD_NEW_NAME_USER
    data = None
    with open('data.json', 'r') as f:
        data = json.load(f)
    new_id = random.randint(1, 200)

    # Mengecek apakah ID atau nama sudah ada dalam data
    for item in data:
        while item['id'] == new_id:
            new_id = random.randint(1, 200)
        if item['nama'].lower() == new_name.lower():
            bot.send_message("5499814195", "nama "+str(new_name)+" sudah terdaftar")
            return "Nama yang diinput sudah ada"

    # Mengembalikan data yang sudah diperbarui
    GLOBAL_ADD_NEW_ID_USER = new_id
    GLOBAL_ADD_NEW_NAME_USER = new_name
    enroll_finger()
    return new_id

def add_new_data():
    # Menambahkan data baru
    global GLOBAL_ADD_NEW_ID_USER
    global GLOBAL_ADD_NEW_NAME_USER
    data = None
    with open('data.json', 'r') as f:
        data = json.load(f)
        
    new_data = {
        "id": GLOBAL_ADD_NEW_ID_USER,
        "nama": GLOBAL_ADD_NEW_NAME_USER
    }
    data.append(new_data)
    with open('data.json', 'w') as file:
        json.dump(data, file, indent=4)

    print("Data berhasil ditambahkan ke JSON.")
    
def delete_item(nama):
    with open('data.json', 'r') as file:
        data = json.load(file)

    # Cari objek dengan nama "Fathur"
    for i in range(len(data)):
        if data[i]['nama'].lower() == nama.lower():
            id = data[i]['id']
            del data[i]
            with open('data.json', 'w') as file:
                json.dump(data, file)
            
            print("idnya = " + id)    
            finger.delete_model(id)
            delete_item_picture_thread = threading.Thread(target=deleteItemPicture, args=(id))
            delete_item_picture_thread.start()
            bot.send_message("5499814195", "Menghapus Data User Telah Berhasil!")
            
            latih_model()
            print(f"Data dengan nama {nama} dan ID {id} telah dihapus.")
            return

    print("Data tidak ditemukan")

def deleteItemPicture(id_user):
    # Mendapatkan daftar file di dalam folder
    file_list = os.listdir("Dataset")

    # Melakukan iterasi pada setiap file
    for file_name in file_list:
        if file_name.endswith(".txt"):
            # Memisahkan nama file menjadi bagian-bagian yang relevan
            name, file_id_user = file_name.split(".", 1)
            a,b = file_id_user.split(".", 1)
            print(file_id_user)
            print(file_name)
            # Memeriksa apakah idUser sama dengan id_user yang diberikan
            if str(a) == str(id_user):
                # Menghapus file
                print("masuk")
                file_path = os.path.join("Dataset", file_name)
                os.remove(file_path)
                print(f"File {file_name} telah dihapus.")




#menambahkan data sidik jari
def enroll_finger():
    print("masuk enroll finger")
    lcdDisplay.set("Add             ",1)
    lcdDisplay.set("Finger          ",2)
    time.sleep(3)
    """Take a 2 finger images and template it, then store in specified location"""
    location = GLOBAL_ADD_NEW_ID_USER

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
        ambil_gambar()
        return True
    else:
        if i == adafruit_fingerprint.BADLOCATION:
            lcdDisplay.set("Error            ",1)
            lcdDisplay.set("Store             ",2)
            print("Bad storage location")
            bot.send_message("5499814195", "Error Menambahkan data sidik jari")
        elif i == adafruit_fingerprint.FLASHERR:
            lcdDisplay.set("Error             ",1)
            lcdDisplay.set("Store            ",2)
            print("Flash storage error")
            bot.send_message("5499814195", "Error Menambahkan data sidik jari")
        else:
            lcdDisplay.set("Error            ",1)
            lcdDisplay.set("Store            ",2)
            print("Other error")
            bot.send_message("5499814195", "Error Menambahkan data sidik jari")
        return False

def get_fingerprint():
    global GLOBAL_ID_USER_FINGER
    global GLOBAL_AUTH_FINGER
    global GLOBAL_STOP_LOOP
    statusVibration = False
    vibration_start_time = 0
    lcdDisplay.set("Authentication   ",1)
    lcdDisplay.set("Finger Is Ready  ",2)
    
    try:
        """Get a finger print image, template it, and see if it matches!"""
        print("Waiting for image...")
        while finger.get_image() != adafruit_fingerprint.OK:
            if GLOBAL_STOP_LOOP:
                break
            
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
                
                if time.time() - vibration_start_time >= 10: #durasi aktif sensor ultrasonic satuan detik
                    statusVibration = False
                    print("status Vibration False")
            pass
        
        if not GLOBAL_STOP_LOOP:
            print("Templating...")
            if finger.image_2_tz(1) != adafruit_fingerprint.OK:
                lcdDisplay.set("Finger is not    ",1)
                lcdDisplay.set("Registered       ",2)
                time.sleep(1.5)
                print("Citra Sidik Jari berantakan")
                bot.send_message("5499814195", "Jari tidak terdaftar")
                get_fingerprint()
            print("Searching...")
            if finger.finger_search() != adafruit_fingerprint.OK:
                print("Sidik jari tidak terdaftar")
                bot.send_message("5499814195", "Jari tidak terdaftar")
                lcdDisplay.set("Finger is not    ",1)
                lcdDisplay.set("Registered       ",2)
                time.sleep(1.5)
                get_fingerprint()
            
            namaJari = searchDataJson(finger.finger_id)
            print("Sidik jari terdeteksi")
            print("ID:", finger.finger_id, "Confidence:", finger.confidence)
            bot.send_message("5499814195", "atas nama "+str(namaJari)+" melakukan authentication Fingerprint")
            lcdDisplay.set("Finger is       ",1)
            lcdDisplay.set("Registered      ",2)
            time.sleep(1.5)
            GLOBAL_AUTH_FINGER = True
            GLOBAL_ID_USER_FINGER = int(finger.finger_id)
            return True
    except Exception as e:
        bot.send_message("5499814195", "Terjadi Error DI get_fingerprint")
        print("error = "+str(e))
    
# Fungsi untuk mengambil gambar data
def ambil_gambar():
    print("masuk fungsi ambil gambar")
    lcdDisplay.set("Take Picture     ",1)
    lcdDisplay.set("                 ",2)
    camera = 0
    video = cv2.VideoCapture(camera)
    faceDeteksi = cv2.CascadeClassifier('haarcascade_frontalface_default.xml')
    id = GLOBAL_ADD_NEW_ID_USER

    if not video.isOpened():
        print("Gagal membuka kamera.")
        try:
            finger.delete_model(id)
        except Exception as e:
            print("Error Delete Finger "+str(e))
            bot.send_message("5499814195", "Terjadi Error delete finger")
        return False

    a = 0
    while True:
        check, frame = video.read()

        if not check:
            print("Gagal membaca frame.")
            bot.send_message("5499814195", "Gagal Membaca Frame")
            try:
                finger.delete_model(id)
            except Exception as e:
                print("Error Delete Finger "+str(e))
                bot.send_message("5499814195", "Terjadi Error delete finger")
            break

        abu = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        wajah = faceDeteksi.detectMultiScale(abu, 1.3, 5)

        for (x, y, w, h) in wajah:
            a = a + 1
            wajah_cropped = frame[y:y+h, x:x+w]

            # Simpan gambar dengan menggunakan ID bilangan bulat
            cv2.imwrite('DataSet/User.' + str(id) + '.' + str(a) + '.jpg', wajah_cropped)
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            print("masuk")
            lcdDisplay.set("Take Picture        ",1)
            lcdDisplay.set(str(a)+"             ",2)

        cv2.imshow("Face Recognition", frame)

        if a > 50: #value untuk melakukan berapa kali gambar data latih
            break

    video.release()
    cv2.destroyAllWindows()
    latih_model()
    add_new_data()
    print("fungsi ambil gambar berakhir")
    bot.send_message("5499814195", "Penambahan Data User Telah Berhasil!")
    lcdDisplay.set("Take Picture     ",1)
    lcdDisplay.set("Successfully     ",2)
    

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

def relayAction():
    GPIO.output(relay_pin, GPIO.HIGH)
    time.sleep(10)
    GPIO.output(relay_pin, GPIO.LOW)
    print("Relay Selesai")

def searchDataJson(id):
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

def authCamera():
    global GLOBAL_AUTH_FACE
    global GLOBAL_ID_USER_FACE
    global GLOBAL_STOP_LOOP
    
    print("masuk auth camera")
    lcdDisplay.set("Authentication   ",1)
    lcdDisplay.set("Face Is Ready    ",2)
    
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
            if conf < 50: #akurasi yang diterima pengenalan wajah, semakin kecil semakin akurat
                id = id
                cv2.putText(frame, str(id) + "=" + str(conf), (x + 40, y - 10), cv2.FONT_HERSHEY_COMPLEX, 1, (0, 255, 0))
                if detected_face is None:
                    detected_face = frame[y:y+h, x:x+w]
                    detected_start_time = a
                elif a - detected_start_time >= 5: #durasi terdeteksi muka
                    takeName = searchDataJson(int(id))
                    
                    if takeName is not False:
                        cv2.imwrite('detected_face.jpg', detected_face)
                        bot.send_photo("5499814195", photo=open('detected_face.jpg', 'rb'))
                        bot.send_message("5499814195", "Atas nama " + takeName + " melakukan authentication muka")
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
    
    if not GLOBAL_STOP_LOOP:
        # Membuat dan memulai thread untuk get_fingerprint
        fingerprint_thread = threading.Thread(target=get_fingerprint)
        fingerprint_thread.start()
        fingerprint_thread.join()


    if not GLOBAL_STOP_LOOP:
        # Setelah thread get_fingerprint selesai, lanjut ke authCamera
        auth_camera_thread  = threading.Thread(target=authCamera)
        auth_camera_thread.start()
        auth_camera_thread.join()
    
    if GLOBAL_AUTH_FACE and GLOBAL_AUTH_FINGER:
        print("user finger = " + str(GLOBAL_ID_USER_FINGER))
        print("user face = " + str(GLOBAL_ID_USER_FACE))
        lcdDisplay.set("Authentication   ",1)
        lcdDisplay.set("Successfully     ",2)
        threading.Thread(target=relayAction).start()
        takeName = searchDataJson(int(GLOBAL_ID_USER_FACE))
        bot.send_message("5499814195", "atas nama "+str(takeName)+" memasuki ruangan")
        time.sleep(1.5)
        checkFile()
    else:
        print("user finger = " + str(GLOBAL_ID_USER_FINGER))
        print("user face = " + str(GLOBAL_ID_USER_FACE))
        if not GLOBAL_STOP_LOOP:
            bot.send_message("5499814195", "Data sidik jari dan muka tidak sesuai")
            lcdDisplay.set("Authentication   ",1)
            lcdDisplay.set("is Failed        ",2)
            time.sleep(1.5)
            checkFile()
        else:
            lcdDisplay.set("Stop            ",1)
            lcdDisplay.set("Service         ",2)
            bot.send_message("5499814195", "Stop Service!!")


@bot.message_handler(commands=['startService'])
def start_service_command(message):
    checkFile()
    
@bot.message_handler(commands=['listUser'])
def list_user_command(message):
    nama_list = ""

    with open('data.json') as json_file:
        data = json.load(json_file)
        
    for object in data:
        nama = object['nama']
        nama_list += nama + ", "
        
    nama_list = nama_list[:-2]

    bot.reply_to(message, "Data User = "+nama_list)
    
@bot.message_handler(commands=['stopService'])
def start_service_command(message):
    global GLOBAL_STOP_LOOP
    GLOBAL_STOP_LOOP = True
    lcdDisplay.set("Stop            ",1)
    lcdDisplay.set("Service         ",2)
    print("stopService uy")
    
@bot.message_handler(commands=['addUser'])
def add_user_command(message):
    bot.reply_to(message, "Silakan masukkan nama identitas yang akan ditambahkan:")
    bot.register_next_step_handler(message, handle_nama_input)

def handle_nama_input(message):
    nama = message.text
    check_id(nama)

@bot.message_handler(commands=['removeUser'])
def remove_user_command(message):
    bot.reply_to(message, "Silakan masukkan nama identitas yang akan dihapus:")
    bot.register_next_step_handler(message, handle_remove_user_input)

def handle_remove_user_input(message):
    nama = message.text
    delete_item(nama)

# Handler untuk perintah /start dan /help
@bot.message_handler(commands=['help'])
def send_welcome(message):
    reply_message = """
    Smart Doorlock System is running!

    /startService = for start service authentication
    /stopService = for stop service authentication
    /addUser = for add new User authentication
    /removeUser = for remove User authentication
    /listUser = for see all user authentication
    """
    bot.reply_to(message, reply_message)

# Handler umum
@bot.message_handler(func=lambda message: True)
def echo_all(message):
    reply_message = """
    Smart Doorlock System is running!

    /startService = for start service authentication
    /stopService = for stop service authentication
    /addUser = for add new User authentication
    /removeUser = for remove User authentication
    /listUser = for see all user authentication
    """
    bot.reply_to(message, reply_message)
    
reply_message = """
    Smart Doorlock System is running!

    /startService = for start service authentication
    /stopService = for stop service authentication
    /addUser = for add new User authentication
    /removeUser = for remove User authentication
    /listUser = for see all user authentication
    """
bot.send_message("5499814195", reply_message)
#checkFile()

GPIO.output(relay_pin, GPIO.LOW)
bot.infinity_polling()
