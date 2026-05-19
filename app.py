from flask import Flask, render_template, jsonify, request
import serial
import threading
import time
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)

SERIAL_PORT = 'COM8'
BAUD_RATE = 9600

# Setări email — completează cu datele tale!
EMAIL_SENDER   = 'emanuelabacos@gmail.com'
EMAIL_PASSWORD = 'pdpy hhpv hsxq epdh'
EMAIL_RECEIVER = 'emabacos@gmail.com'

temperatura_curenta = 0.0
led_status = False
evenimente = []  # lista evenimente inundatie
ser = None
email_lock = threading.Lock()

def conectare_serial():
    global ser
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)
        print(f"Conectat la {SERIAL_PORT}")
    except Exception as e:
        print(f"Eroare conectare serial: {e}")

def trimite_email(mesaj):
    try:
        with email_lock:
            msg = MIMEText(mesaj)
            msg['Subject'] = '🚨 ALERTĂ INUNDAȚIE - Sistema Arduino'
            msg['From']    = EMAIL_SENDER
            msg['To']      = EMAIL_RECEIVER
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(EMAIL_SENDER, EMAIL_PASSWORD)
                server.send_message(msg)
            print("Email trimis cu succes!")
    except Exception as e:
        print(f"Eroare email: {e}")

def citire_serial():
    global temperatura_curenta, evenimente
    while True:
        try:
            if ser and ser.in_waiting:
                linie = ser.readline().decode('utf-8').strip()
                if 'Temperatura:' in linie:
                    temp = linie.replace('Temperatura:', '').replace('°C', '').strip()
                    temperatura_curenta = float(temp)
                elif 'INUNDATIE DETECTATA' in linie:
                    timestamp = datetime.now().strftime('%d/%m/%Y %H:%M:%S')
                    eveniment = {
                        'id': len(evenimente),
                        'timestamp': timestamp,
                        'mesaj': 'Inundație detectată'
                    }
                    evenimente.insert(0, eveniment)
                    # Păstrează doar ultimele 10
                    if len(evenimente) > 10:
                        evenimente = evenimente[:10]
                    # Trimite email în thread separat
                    t = threading.Thread(
                        target=trimite_email,
                        args=(f"ALERTĂ INUNDAȚIE!\nDetectată la: {timestamp}",)
                    )
                    t.start()
        except:
            pass
        time.sleep(0.1)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/temperatura')
def get_temperatura():
    return jsonify({'temperatura': temperatura_curenta})

@app.route('/led', methods=['POST'])
def control_led():
    global led_status
    data = request.json
    comanda = data.get('comanda')
    if ser:
        if comanda == 'ON':
            ser.write(b'A\n')
            led_status = True
        elif comanda == 'OFF':
            ser.write(b'S\n')
            led_status = False
    return jsonify({'led': led_status})

@app.route('/led_status')
def get_led_status():
    return jsonify({'led': led_status})

@app.route('/mesaj', methods=['POST'])
def trimite_mesaj():
    data = request.json
    mesaj = data.get('mesaj', '').strip()
    if mesaj and ser:
        ser.write((mesaj + '\n').encode('utf-8'))
        time.sleep(0.5)
    return jsonify({'status': 'ok'})

@app.route('/evenimente')
def get_evenimente():
    return jsonify({'evenimente': evenimente})

@app.route('/evenimente/<int:idx>', methods=['DELETE'])
def sterge_eveniment(idx):
    global evenimente
    evenimente = [e for e in evenimente if e['id'] != idx]
    return jsonify({'status': 'ok'})

if __name__ == '__main__':
    conectare_serial()
    thread = threading.Thread(target=citire_serial, daemon=True)
    thread.start()
    app.run(debug=False, host='0.0.0.0', port=5000)