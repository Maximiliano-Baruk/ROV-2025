import serial
import time
import struct
import json
import socket
from threading import Thread
from collections import defaultdict
import cv2
import pickle

# --- CONFIGURACIÓN ---
UART_MOTOR_PORT = '/dev/ttyS0'
UART_SERVO_PORT = '/dev/ttyS4'
BAUDRATE = 115200
UDP_IP = "0.0.0.0"
UDP_PORT = 5005
TCP_VIDEO_IP = '192.168.1.102'
TCP_VIDEO_PORT = 12345

# --- VARIABLES GLOBALES ---
joystick_data = {
    "axes": [0.0, 0.0],
    "buttons": [0] * 12,
    "hats": [(0, 0)]
}
joystick_updated = False

servo_positions = [1000, 1000, 1000, 1000]
servo_limits = (500, 2500)
button_states = defaultdict(lambda: {'pressed': False, 'press_count': 0, 'last_press_time': 0})

# --- FUNCIONES DE CONTROL ---
def udp_receiver():
    global joystick_data, joystick_updated
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print("Esperando datos del control...")
    while True:
        data, _ = sock.recvfrom(1024)
        try:
            new_data = json.loads(data.decode('utf-8'))
            joystick_data["axes"] = new_data.get("axes", [0.0, 0.0])[:2]
            joystick_data["buttons"] = new_data.get("buttons", [0] * 12)
            joystick_data["hats"] = new_data.get("hats", [(0, 0)])
            joystick_updated = True
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error en datos recibidos: {e}")

def map_joystick(value, in_min, in_max, out_min, out_max):
    value = max(in_min, min(in_max, value))
    return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

def calculate_motor_values(axes):
    eje_x, eje_y = axes[0], axes[1]
    if abs(eje_x) < 0.1: eje_x = 0
    if abs(eje_y) < 0.1: eje_y = 0
    if eje_y >= 0:
        m1 = m3 = map_joystick(eje_y, 0, 1, 1000, 1499)
    else:
        m1 = m3 = map_joystick(-eje_y, 0, 1, 1501, 2020)
    if eje_x >= 0:
        m2 = m4 = map_joystick(eje_x, 0, 1, 1000, 1499)
    else:
        m2 = m4 = map_joystick(-eje_x, 0, 1, 1501, 2020)
    return [m1, m2, m3, m4]

def update_servo_positions():
    global servo_positions, button_states
    current_time = time.time()
    double_click_threshold = 0.3
    for i in range(4):
        if joystick_data['buttons'][i]:
            if not button_states[i]['pressed']:
                time_since_last = current_time - button_states[i]['last_press_time']
                if time_since_last < double_click_threshold:
                    button_states[i]['press_count'] += 1
                else:
                    button_states[i]['press_count'] = 1
                button_states[i]['last_press_time'] = current_time
                button_states[i]['pressed'] = True
            direction = 1 if button_states[i]['press_count'] % 2 == 1 else -1
            new_pos = servo_positions[i] + (50 * direction)
            servo_positions[i] = max(servo_limits[0], min(servo_limits[1], new_pos))
        else:
            button_states[i]['pressed'] = False

def send_servo_commands(ser):
    commands = []
    for i, pos in enumerate(servo_positions, start=1):
        commands.append(f"#{i}P{int(pos)}T1000")
    full_command = "".join(commands) + "\r\n"
    ser.write(full_command.encode())
    print(f"Servos: {[int(p) for p in servo_positions]}", end=" ")

def send_msp(ser, command, data=[]):
    header = b'$M<'
    checksum = len(data) ^ command
    for d in data: checksum ^= d
    message = header + struct.pack('<BB', len(data), command) + bytes(data) + struct.pack('<B', checksum)
    ser.write(message)

# --- FUNCIONES DE VIDEO TCP ---
def video_streamer():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((TCP_VIDEO_IP, TCP_VIDEO_PORT))
    server_socket.listen(1)
    print("Esperando conexión de cliente de video...")
    conn, addr = server_socket.accept()
    print("Conexión de video establecida con:", addr)

    cap = cv2.VideoCapture('/dev/video0')
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            frame = cv2.resize(frame, (640, 480))
            data = pickle.dumps(frame)
            try:
                conn.sendall(struct.pack("L", len(data)) + data)
            except (ConnectionResetError, BrokenPipeError):
                print("Cliente de video desconectado")
                break
    finally:
        cap.release()
        conn.close()
        server_socket.close()

# --- FUNCIÓN PRINCIPAL ---
def main():
    global joystick_updated
    ser_motors = serial.Serial(UART_MOTOR_PORT, BAUDRATE, timeout=1)
    ser_servos = serial.Serial(UART_SERVO_PORT, BAUDRATE, timeout=1)
    time.sleep(1)

    Thread(target=udp_receiver, daemon=True).start()
    Thread(target=video_streamer, daemon=True).start()

    send_msp(ser_motors, 216, [1])  # MSP_SET_ARMING
    time.sleep(1)

    try:
        print("Control activo. Joystick para motores, botones 1-4 para servos.")
        print("Mantén botón para incrementar, doble-click+mantén para decrementar.")
        while True:
            if joystick_updated:
                motor_values = calculate_motor_values(joystick_data["axes"])
                data = struct.pack('<' + 'H'*4, *motor_values)
                send_msp(ser_motors, 214, data)  # MSP_SET_MOTOR

                update_servo_positions()
                send_servo_commands(ser_servos)

                print(f"\rMotores: {motor_values} | X: {joystick_data['axes'][0]:.2f} | Y: {joystick_data['axes'][1]:.2f} | Hats: {joystick_data['hats']}", end="")
                joystick_updated = False
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("\nDeteniendo motores y centrando servos...")
        send_msp(ser_motors, 214, struct.pack('<' + 'H'*4, *[1000]*4))
        for i in range(4):
            servo_positions[i] = 1000
        send_servo_commands(ser_servos)
    finally:
        ser_motors.close()
        ser_servos.close()

if __name__ == "__main__":
    main()
