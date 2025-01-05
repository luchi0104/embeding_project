import RPi.GPIO as GPIO
import time
from flask import Flask, render_template, request, jsonify
from threading import Timer
from threading import Thread
from threading import Lock
# 初始化 Flask
app = Flask(__name__)

# 設定 GPIO 腳位
PIR_PIN = 17  # HC-SR501
SERVO_PIN = 18  # SG90 伺服馬達
capacity = 5  # 酒精容量初始值
LED_PIN = 27  # LED 狀態指示燈
system_active = False  # 系統初始狀態為關閉
# 記錄上一個偵測狀態
previous_state = False  # False 表示沒有偵測到動作

# 初始化 GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)
GPIO.setup(SERVO_PIN, GPIO.OUT)
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.output(LED_PIN, False) 

# 初始化 PWM
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

# 時間戳
last_spray_time = 0
COOLDOWN = 4.0  

spray_lock = Lock()

# 角度轉換函數
def set_angle(angle):
    duty_cycle = 2 + (angle / 18)  # 將角度轉換為佔空比
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5)
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)

def universal_spray():
    global capacity, last_spray_time

    now = time.time()
    if (now - last_spray_time) < COOLDOWN:
        print("短時間內已噴射，跳過")
        return

    if capacity > 1:
        set_angle(180)
        time.sleep(1)
        set_angle(0)
        capacity -= 1
        time.sleep(0.5)
        last_spray_time = now
        print("噴射成功！剩餘容量:", capacity)
    else:
        print("容量不足，無法噴射！")

# 酒精噴射邏輯
def spray():
    global previous_state
    if not system_active:  # 如果系統關閉，直接跳過
        return
    current_state = GPIO.input(PIR_PIN)
    if current_state and not previous_state:
        with spray_lock:
            universal_spray()
    previous_state = current_state

def manual_spray():
    with spray_lock:
        universal_spray()

# 網頁路由
@app.route('/')
def index():
    global capacity
    warning = "容量不足！請補充酒精！" if capacity < 3 else ""
    return render_template('index.html', capacity=capacity, warning=warning)

@app.route('/reset', methods=['POST'])
def reset_capacity():
    global capacity
    capacity = 5  # 重置容量
    return jsonify({"capacity": capacity})

# 背景偵測動作
@app.route('/detect', methods=['POST'])
def detect():
    global capacity, previous_state
    return jsonify({"capacity": capacity})

@app.route('/inject', methods=['POST'])
def inject():
    global capacity
    if capacity > 1:
        manual_spray()  # ← 不透過原本 spray()，避免 PIR 限制
        return jsonify({"status": "success", "capacity": capacity})
    else:
        return jsonify({"status": "error", "message": "容量不足！請補充酒精！"})

@app.route('/toggle', methods=['POST'])
def toggle_system():
    global system_active
    system_active = not system_active  # 切換系統狀態
    GPIO.output(LED_PIN, system_active)  # 根據系統狀態控制 LED
    status = "啟動" if system_active else "關閉"
    return jsonify({"status": status, "system_active": system_active})

# 清理 GPIO
@app.route('/shutdown', methods=['POST'])
def shutdown():
    GPIO.cleanup()
    return "系統已清理 GPIO！"

def background_task():
    while True:
        spray()
        time.sleep(2)

if __name__ == '__main__':
    try:
        thread = Thread(target=background_task)
        thread.daemon = True  # 設為守護執行緒
        thread.start()
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        GPIO.cleanup()
