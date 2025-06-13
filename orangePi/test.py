import serial
import time
import struct
import json
import socket
from threading import Thread ,Lock
from collections import defaultdict
import cv2
import pickle
import subprocess
import os
import sys
import gpiod

# ESTE ES EL QUE TIENE TOd0 EXCEPTO EL CONTROL DE BOMBAS


# --- CONFIGURACIÓN ---
UART_MOTOR_PORT = '/dev/ttyS0'
UART_SERVO_PORT = '/dev/ttyS4'
BAUDRATE = 115200
UDP_IP = "0.0.0.0"
UDP_PORT = 5005
TCP_VIDEO_IP = '192.168.1.105'
TCP_VIDEO_PORT = 12345
CAMERA_1 = '/dev/video0'
CAMERA_2 = '/dev/video1'
RESOLUCION = (320, 240)


# --- VARIABLES GLOBALES ---
joystick_data = {
    "axes": [0.0, 0.0],
    "buttons": [0] * 12,
    "hats": [(0, 0)]
}
joystick_updated = False

servo_positions = [1400,1400,1400,1400,
                   1400,1400,1400,1400,
                   1400,1400]

button_states = defaultdict(lambda: {'pressed': False, 'press_count': 0, 'last_press_time': 0})


# Configuración GPIOs para bombas
GPIO_MAPPING = {
    'BOMBA_LLENAR': {'chip': 'gpiochip1', 'offset': 3},   # GPIO35
    'BOMBA_VACIAR': {'chip': 'gpiochip2', 'offset': 28}, # GPIO92
}

# Camara
latest_frame1 = None
latest_frame2 = None
frame_lock = Lock()


# --- FUNCIONES DE CONTROL ---
def setup_gpios():
    lines = {}
    for name, config in GPIO_MAPPING.items():
        try:
            chip = gpiod.Chip(config['chip'])
            line = chip.get_line(config['offset'])
            line.request(consumer=name, type=gpiod.LINE_REQ_DIR_OUT)
            lines[name] = line
            print(f"✅ {name} configurado correctamente")
        except Exception as e:
            print(f"❌ Error configurando {name}: {str(e)}")
            raise
    return lines

def udp_receiver():
    global joystick_data, joystick_updated
    liberar_puertos()
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print("Esperando datos del control...")
    while True:
        data, _ = sock.recvfrom(1024)
        try:
            new_data = json.loads(data.decode('utf-8'))
            joystick_data["axes"] = new_data.get("axes", [0.0] * 8)  # o un número seguro de ejes
            joystick_data["buttons"] = new_data.get("buttons", [0] * 12)
            joystick_data["hats"] = new_data.get("hats", [(0, 0)])
            joystick_updated = True
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error en datos recibidos: {e}")

def map_joystick(value, in_min, in_max, out_min, out_max):
    value = max(in_min, min(in_max, value))
    return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

def calculate_motor_values(axes):

    m1= m2= m3 =m4 = 1000
      # # --HATs ---
    hat = tuple(joystick_data.get("hats", [(0, 0)])[0])
    hat_mappings = {
        (1, 0): 4,    # Derecha → Servo 5  → índice 4
        (-1, 0): 5,   # Izquierda → Servo 6 → índice 5
        (0, 1): 6,    # Arriba → Servo 7 → índice 6ae
        (0, -1): 7    # Abajo → Servo 8 → índice 7
    }

 # Aquí puedes agregar acciones específicas para cada dirección:
    if hat == (1, 0):    # Derecha
        m1 = 1750
        m2 = 1750
        m3 = 1750
        m4 = 1750

        pass
            
    elif hat == (-1, 0): # Izquierda
        m1 = 1255
        m2 = 1255
        m3 = 1255
        m4 = 1255
        pass
            
    elif hat == (0, 1):  # Arriba
        m1 = 1750
        m2 = 1255
        m3 = 1255
        m4 = 1750
        pass
            
    elif hat == (0, -1): # Abajo
        m1 = 1255
        m2 = 1750
        m3 = 1750
        m4 = 1255
    
        pass

    # Se le agrega este codigo para que los motores funcionen con el joystick 

    # eje_x, eje_y = axes[0], axes[1]
    # if abs(eje_x) < 0.1: eje_x = 0
    # if abs(eje_y) < 0.1: eje_y = 0
    # if eje_x != 0 or eje_y != 0:
    #         # Movimiento adelante/atrás (eje Y)
    #     if eje_y < 0:  # Adelante (joystick hacia arriba)
    #             # Misma lógica que HAT Arriba
    #         m1 = map_joystick(-eje_y, 0, 1, 1501, 2000)  # 1750 equivalente
    #         m2 = map_joystick(-eje_y, 0, 1, 1000, 1499)  # 1255 equivalente
    #         m3 = map_joystick(-eje_y, 0, 1, 1000, 1499)  # 1255 equivalente
    #         m4 = map_joystick(-eje_y, 0, 1, 1501, 2000)  # 1750 equivalente
                
    #     elif eje_y > 0:  # Atrás (joystick hacia abajo)
    #             # Misma lógica que HAT Abajo
    #         m1 = map_joystick(eje_y, 0, 1, 1000, 1499)   # 1255 equivalente
    #         m2 = map_joystick(eje_y, 0, 1, 1501, 2000)   # 1750 equivalente
    #         m3 = map_joystick(eje_y, 0, 1, 1501, 2000)  # 1750 equivalente
    #         m4 = map_joystick(eje_y, 0, 1, 1000, 1499)   # 1255 equivalente
            
    #         # Giro izquierda/derecha (eje X)
    #     if eje_x > 0:  # Derecha
    #             # Misma lógica que HAT Derecha
    #         m1 = map_joystick(eje_x, 0, 1, 1501, 2000)  # 1750 equivalente
    #         m2 = map_joystick(eje_x, 0, 1, 1501, 2000)  # 1750 equivalente
    #         m3 = map_joystick(eje_x, 0, 1, 1000, 1499)  # 1255 equivalente
    #         m4 = map_joystick(eje_x, 0, 1, 1000, 1499)  # 1255 equivalente
                
    #     elif eje_x < 0:  # Izquierda
    #             # Misma lógica que HAT Izquierda
    #         m1 = map_joystick(-eje_x, 0, 1, 1000, 1499)  # 1255 equivalente
    #         m2 = map_joystick(-eje_x, 0, 1, 1000, 1499)  # 1255 equivalente
    #         m3 = map_joystick(-eje_x, 0, 1, 1501, 2000)  # 1750 equivalente
    #         m4 = map_joystick(-eje_x, 0, 1, 1501, 2000)  # 1750 equivalente
            

        
    return [m1, m2, m3, m4]

def update_servo_positions():
    global servo_positions

    current_time = time.time()

    #  Configuracion de limites 
    limits_by_index = {
        0: (700, 2100),  # Servo 1
        1: (500, 2500),  # Servo 2
        2: (500, 2500),  # Servo 3
        3: (500, 2500),  # Servo 4
        #4: (500, 2500),  # Servo 5
        #5: (500, 2500),  # Servo 6
        #6: (500, 2500),  # Servo 7
        #7: (500, 2500),  # Servo 8
        8: (500, 2500),  # Servo 9
        9: (500, 2500),  # Servo 10

    }

    # Inversion botones 
    invert_buttons = 1 if joystick_data["buttons"][5] else 0  # RB

    # Control de servos 
    for i in range(4):
        if joystick_data['buttons'][i]:
            direction = -1 if invert_buttons else 1
            new_pos = servo_positions[i] + (50 * direction)
            min_limit, max_limit = limits_by_index[i]
            servo_positions[i] = max(min_limit, min(max_limit, new_pos))

    # --- Servos 9 y 10 con gatillos analógicos (ejes 3 y 6) ---
        eje_2 = joystick_data["axes"][2] if len(joystick_data["axes"]) > 2 else -1
        eje_5 = joystick_data["axes"][5] if len(joystick_data["axes"]) > 5 else -1


    servo_positions_9_10 = [
        map_joystick(eje_2, -1, 1, 500, 2500),
        map_joystick(eje_5, -1, 1, 500, 2500)
    ]


        # # --- Servos 5–8 con HATs --- Agregar 
    # hat = tuple(joystick_data.get("hats", [(0, 0)])[0])
    # hat_mappings = {
    #     (1, 0): 4,    # Derecha → Servo 5  → índice 4
    #     (-1, 0): 5,   # Izquierda → Servo 6 → índice 5
    #     (0, 1): 6,    # Arriba → Servo 7 → índice 6
    #     (0, -1): 7    # Abajo → Servo 8 → índice 7
    # }


    # for direction_vec, servo_index in hat_mappings.items():
    #     if hat == direction_vec:
    #         direction = -1 if invert_hats else 1
    #         new_pos = servo_positions[servo_index] + (50 * direction)
    #         min_limit, max_limit = limits_by_index[servo_index]
    #         servo_positions[servo_index] = max(min_limit, min(max_limit, new_pos))


def send_servo_commands(ser):
    commands = []
    for i, pos in enumerate(servo_positions, start=1):
        commands.append(f"#{i}P{int(pos)}T1000")
    full_command = "".join(commands) + "\r\n"
    ser.write(full_command.encode())
    print(f"S: {[int(p) for p in servo_positions]}", end=" ")

def send_msp(ser, command, data=[]):
    header = b'$M<'
    checksum = len(data) ^ command
    for d in data: checksum ^= d
    message = header + struct.pack('<BB', len(data), command) + bytes(data) + struct.pack('<B', checksum)
    ser.write(message)
def read_msp(ser):
    try:
        header = ser.read(3)
        if header != b'$M>':
            return None
        
        len_data = ser.read(1)[0]
        cmd = ser.read(1)[0]
        data = ser.read(len_data)
        checksum = ser.read(1)[0]
        
        calc_checksum = len_data ^ cmd
        for d in data: calc_checksum ^= d
        
        if checksum == calc_checksum:
            return (cmd, data)
        return None
    except:
        return None

def get_imu_data(ser):
    # Solicitar datos de actitud (pitch/roll/yaw)
    send_msp(ser, 108)  # MSP_ATTITUDE
    response = read_msp(ser)
    
    if response and response[0] == 108:
        data = response[1]
        roll = struct.unpack('<h', data[0:2])[0] / 10.0  # en grados
        pitch = struct.unpack('<h', data[2:4])[0] / 10.0
        yaw = struct.unpack('<h', data[4:6])[0] / 10.0
        return {"pitch": pitch, "roll": roll, "yaw": yaw}
    return None
# --- FUNCIONES DE VIDEO TCP ---
def camera_capture(camera_index, camera_path):
    global latest_frame1, latest_frame2
    cap = cv2.VideoCapture(camera_path)
    if not cap.isOpened():
        print(f"❌ Error grave: Cámara {camera_index} no detectada en {camera_path}")
        return  
    
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, RESOLUCION[0])  
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, RESOLUCION[1])
    
    while True:
        ret, frame = cap.read()
        if not ret:
            print(f"Error en cámara {camera_index}. Reintentando...")
            time.sleep(2)
            continue
        
        with frame_lock:
            if camera_index == 1:
                latest_frame1 = frame
            else:
                latest_frame2 = frame

def video_streamer():
    global latest_frame1, latest_frame2
    
    # Inicia hilos para cámaras
    cam_thread1 = Thread(target=camera_capture, args=(1, CAMERA_1), daemon=True)
    cam_thread2 = Thread(target=camera_capture, args=(2, CAMERA_2), daemon=True)
    cam_thread1.start()
    cam_thread2.start()
    
    time.sleep(2)  # Espera inicialización
    
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_socket:
                server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_socket.settimeout(5.0)
                server_socket.bind((TCP_VIDEO_IP, TCP_VIDEO_PORT))
                server_socket.listen(1)
                print("🔄 Servidor de video listo. Esperando conexión...")
                
                try:
                    conn, addr = server_socket.accept()
                    print(f"✅ Cliente conectado: {addr}")
                    
                    while True:
                        with frame_lock:
                            if latest_frame1 is None or latest_frame2 is None:
                                time.sleep(0.1)
                                continue
                                
                            try:
                                combined = cv2.hconcat([latest_frame1, latest_frame2])
                                _, buffer = cv2.imencode('.jpg', combined, 
                                                      [cv2.IMWRITE_JPEG_QUALITY, 70])
                                data = pickle.dumps(buffer)
                                conn.sendall(struct.pack("L", len(data)) + data)
                            except Exception as e:
                                print(f"⚠️ Error procesando frame: {e}")
                                break
                                
                except socket.timeout:
                    print("⏳ Timeout en accept(). Reintentando...")
                    continue
                    
        except Exception as e:
            print(f"❌ Error en servidor de video: {e}")
            time.sleep(1)
            
def liberar_puertos():
    # Libera puerto UDP
    subprocess.run(["fuser", "-k", f"{UDP_PORT}/udp"], stderr=subprocess.DEVNULL)
    # Libera puerto TCP de video
    subprocess.run(["fuser", "-k", f"{TCP_VIDEO_PORT}/tcp"], stderr=subprocess.DEVNULL)
    print("✅ Puertos liberados")

def control_bombas(lines):
    global joystick_data
    while True:
        if joystick_updated:
            buttons = joystick_data["buttons"]
            
            # Botón 7 (índice 6) - Llenar
            if buttons[6] == 1:
                lines['BOMBA_LLENAR'].set_value(1)
                lines['BOMBA_VACIAR'].set_value(0)
                print("🚰 Botón 7: Llenando tanque")
            
            # Botón 8 (índice 7) - Vaciar
            elif buttons[7] == 1:
                lines['BOMBA_LLENAR'].set_value(0)
                lines['BOMBA_VACIAR'].set_value(1)
                print("💨 Botón 8: Vaciando tanque")
            
            # Ningún botón activo
            else:
                lines['BOMBA_LLENAR'].set_value(0)
                lines['BOMBA_VACIAR'].set_value(0)
            
            time.sleep(0.1)  # Pequeña pausa para evitar sobrecarga

# --- FUNCIÓN PRINCIPAL ---
def main():
    global joystick_updated
    ser_motors = serial.Serial(UART_MOTOR_PORT, BAUDRATE, timeout=0.02)
    ser_servos = serial.Serial(UART_SERVO_PORT, BAUDRATE, timeout=0.02)
    ser_imu = serial.Serial(UART_MOTOR_PORT, BAUDRATE, timeout=0.02)  # Conexión UART para IMU

     
       # Inicialización
    lines = setup_gpios()

    Thread(target=udp_receiver, daemon=True).start()

    Thread(target=video_streamer, daemon=True).start()  # <-- Nuevo sistema de 2 cámaras

    control_thread = Thread(target=control_bombas, args=(lines,))
    control_thread.daemon = True
    control_thread.start()
    send_msp(ser_motors, 216, [1])  # MSP_SET_ARMING

    time.sleep(1)

    try:
        print("Control activo. Joystick para motores, botones 1-4 para servos.")
        print("Mantén botón para incrementar, doble-click+mantén para decrementar.")
        while True:
                        # --- Leer y mostrar datos del IMU ---
            imu_data = get_imu_data(ser_imu)
            if imu_data:
                print(
                    f"\rPitch: {imu_data['pitch']:6.1f}° | "
                    f"Roll: {imu_data['roll']:6.1f}° | "
                    f"Yaw: {imu_data['yaw']:6.1f}°",
                    end="", flush=True
                )
            if joystick_updated:
                if joystick_data["buttons"][8] == 1:  # Botón 9
                    if joystick_data["buttons"][9] == 1:  # Si también se presiona el botón RB (5)
                        print("⚡ REINICIO COMPLETO de Orange Pi")
                        subprocess.run(["sudo", "reboot"])
                    else:
                        print("🔄 Reiniciando solo el proceso Python")
                        os.execv(sys.executable, ['python3'] + sys.argv)
                
                     # Resto de tu lógica...
                motor_values = calculate_motor_values(joystick_data["axes"])
                data = struct.pack('<' + 'H'*4, *motor_values)
                send_msp(ser_motors, 214, data)  # MSP_SET_MOTOR

                update_servo_positions()
                send_servo_commands(ser_servos)

                print(f"\rM: {motor_values}", end="")
                joystick_updated = False
            time.sleep(0.02)
    except KeyboardInterrupt:
        print("\nDeteniendo motores y centrando servos...")
        send_msp(ser_motors, 214, struct.pack('<' + 'H'*4, *[1000]*4))
        for i in range(4):
            servo_positions[i] = 2000
        send_servo_commands(ser_servos)
    finally:
        ser_motors.close()
        ser_servos.close()
        for line in lines.values():
            line.release()

if __name__ == "__main__":
    main()
