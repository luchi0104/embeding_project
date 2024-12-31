import RPi.GPIO as GPIO
import time
from flask import Flask, render_template, request, jsonify
from threading import Timer
from threading import Thread
# 初始化 Flask
app = Flask(__name__)

# 設定 GPIO 腳位
PIR_PIN = 17  # HC-SR501
SERVO_PIN = 18  # SG90 伺服馬達
capacity = 20  # 酒精容量初始值

# 記錄上一個偵測狀態
previous_state = False  # False 表示沒有偵測到動作

# 初始化 GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(PIR_PIN, GPIO.IN)
GPIO.setup(SERVO_PIN, GPIO.OUT)

# 初始化 PWM
pwm = GPIO.PWM(SERVO_PIN, 50)
pwm.start(0)

# 角度轉換函數
def set_angle(angle):
    duty_cycle = 2 + (angle / 18)  # 將角度轉換為佔空比
    GPIO.output(SERVO_PIN, True)
    pwm.ChangeDutyCycle(duty_cycle)
    time.sleep(0.5)
    GPIO.output(SERVO_PIN, False)
    pwm.ChangeDutyCycle(0)

# 酒精噴射邏輯
def spray():
    global capacity, previous_state
    current_state = GPIO.input(PIR_PIN) 
    if current_state and not previous_state:
        if capacity > 1:
            set_angle(180)  # 噴射動作
            time.sleep(1)
            set_angle(0)
            capacity -= 1  # 減少容量
            time.sleep(0.5)
        else:
            print("容量不足，無法噴射！")
    previous_state = current_state

# 網頁路由
@app.route('/')
def index():
    global capacity
    warning = "容量不足！請補充酒精！" if capacity < 3 else ""
    return render_template('index.html', capacity=capacity, warning=warning)

@app.route('/reset', methods=['POST'])
def reset_capacity():
    global capacity
    capacity = 10  # 重置容量
    return jsonify({"capacity": capacity})

# 背景偵測動作
@app.route('/detect', methods=['POST'])
def detect():
    global capacity, previous_state
    # current_state = GPIO.input(PIR_PIN)  # 讀取當前 PIR 狀態

    # 當前狀態為 True（偵測到動作），且上一狀態為 False（沒有動作）時觸發噴射
    # if current_state and not previous_state:
    #     spray()

    # 更新上一狀態
    # previous_state = current_state

    return jsonify({"capacity": capacity})

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
        app.run(host='0.0.0.0', port=5000, debug=True)
    except KeyboardInterrupt:
        GPIO.cleanup()