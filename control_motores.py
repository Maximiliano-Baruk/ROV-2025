import serial
import time
import struct
import json
import socket
from threading import Thread

# ESTE CODIGO LEE EL CONTROL Y CONTROLA LOS MOTORES

# Configuración
UART_PORT = '/dev/ttyS0'
BAUDRATE = 115200
UDP_IP = "0.0.0.0"
UDP_PORT = 5005

# Variables globales seguras para compartir datos
joystick_data = {"axes": [0.0, 0.0], "buttons": [0]*12}
joystick_updated = False

def udp_receiver():
    """Hilo que recibe datos del control Xbox"""
    global joystick_data, joystick_updated
    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    
    print("Esperando datos del control...")
    while True:
        data, _ = sock.recvfrom(1024)
        try:
            new_data = json.loads(data.decode('utf-8'))
            joystick_data["axes"] = new_data["axes"][:2]  # Solo nos interesan ejes 0 y 1
            joystick_data["buttons"] = new_data["buttons"]
            joystick_updated = True
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error en datos recibidos: {e}")

def map_joystick(value, in_min, in_max, out_min, out_max):
    """Mapeo lineal con límites"""
    value = max(in_min, min(in_max, value))  # Limitar al rango
    return int((value - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

def calculate_motor_values(axes):
    """Calcula los valores de los 4 motores basados en los ejes del joystick"""
    eje_x, eje_y = axes[0], axes[1]
    
    # Zona muerta para evitar vibraciones
    if abs(eje_x) < 0.1: eje_x = 0
    if abs(eje_y) < 0.1: eje_y = 0
    
    # Motor 1 y 3 (controlados por eje Y)
    if eje_y >= 0:
        m1 = m3 = map_joystick(eje_y, 0, 1, 1000, 1499)
    else:
        m1 = m3 = map_joystick(-eje_y, 0, 1, 1501, 2020)
    
    # Motor 2 y 4 (controlados por eje X)
    if eje_x >= 0:
        m2 = m4 = map_joystick(eje_x, 0, 1, 1000, 1499)
    else:
        m2 = m4 = map_joystick(-eje_x, 0, 1, 1501, 2020)
    
    return [m1, m2, m3, m4]

def main():
    global joystick_updated
    
    # Inicializar UART
    ser = serial.Serial(UART_PORT, BAUDRATE, timeout=1)
    
    # Iniciar hilo receptor
    Thread(target=udp_receiver, daemon=True).start()
    
    # Armar los motores
    def send_msp(command, data=[]):
        header = b'$M<'
        checksum = len(data) ^ command
        for d in data: checksum ^= d
        message = header + struct.pack('<BB', len(data), command) + bytes(data) + struct.pack('<B', checksum)
        ser.write(message)
    
    send_msp(216, [1])  # MSP_SET_ARMING
    time.sleep(1)
    
    try:
        print("Control activo. Usa el joystick izquierdo. Ctrl+C para salir.")
        while True:
            if joystick_updated:
                motor_values = calculate_motor_values(joystick_data["axes"])
                data = struct.pack('<'+'H'*4, *motor_values)
                send_msp(214, data)  # MSP_SET_MOTOR
                
                print(f"\rMotores: {motor_values} | X: {joystick_data['axes'][0]:.2f} | Y: {joystick_data['axes'][1]:.2f}", end="")
                joystick_updated = False
                
            time.sleep(0.02)
            
    except KeyboardInterrupt:
        print("\nDeteniendo motores...")
        send_msp(214, struct.pack('<'+'H'*4, *[1000]*4))
    finally:
        ser.close()

if __name__ == "__main__":
    main()