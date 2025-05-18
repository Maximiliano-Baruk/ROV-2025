import serial
import time
import struct
import json
import socket
from threading import Thread
from collections import defaultdict

# ESTE CODIGO LEE EL CONTROL Y CONTROLA EL BRAZO

# Configuración
UART_MOTOR_PORT = '/dev/ttyS0'  # Puerto para motores
UART_SERVO_PORT = '/dev/ttyS4'  # Puerto para servos (ajustar)
BAUDRATE = 115200
UDP_IP = "0.0.0.0"
UDP_PORT = 5005

# Variables globales
joystick_data = {"axes": [0.0, 0.0], "buttons": [0]*12}
joystick_updated = False

# Variables para servos
servo_positions = [1000, 1000, 1000, 1000]  # Posiciones iniciales
servo_limits = (500, 2500)  # Límites de movimiento
button_states = defaultdict(lambda: {'pressed': False, 'press_count': 0, 'last_press_time': 0})

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
            joystick_data["axes"] = new_data["axes"][:2]  # Solo ejes 0 y 1
            joystick_data["buttons"] = new_data["buttons"]
            joystick_updated = True
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error en datos recibidos: {e}")

def map_joystick(value, in_min, in_max, out_min, out_max):
    """Mapeo lineal con límites"""
    value = max(in_min, min(in_max, value))
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

def update_servo_positions():
    """Actualiza las posiciones de los servos basado en los botones presionados"""
    global servo_positions, button_states
    
    current_time = time.time()
    double_click_threshold = 0.3  # Segundos para considerar doble click
    
    for i in range(4):  # Solo los primeros 4 botones
        if joystick_data['buttons'][i]:
            # Lógica para detectar doble click
            if not button_states[i]['pressed']:
                time_since_last = current_time - button_states[i]['last_press_time']
                if time_since_last < double_click_threshold:
                    button_states[i]['press_count'] += 1
                else:
                    button_states[i]['press_count'] = 1
                
                button_states[i]['last_press_time'] = current_time
                button_states[i]['pressed'] = True
            
            # Determinar dirección basada en número de clicks
            direction = 1 if button_states[i]['press_count'] % 2 == 1 else -1
            
            # Actualizar posición con límites
            new_pos = servo_positions[i] + (50 * direction)
            servo_positions[i] = max(servo_limits[0], min(servo_limits[1], new_pos))
        else:
            button_states[i]['pressed'] = False

def send_servo_commands(ser):
    """Envía los comandos actuales de los servos"""
    commands = []
    for i, pos in enumerate(servo_positions, start=1):
        commands.append(f"#{i}P{int(pos)}T1000")
    full_command = "".join(commands) + "\r\n"
    ser.write(full_command.encode())
    print(f"Servos: {[int(p) for p in servo_positions]}", end=" ")

def send_msp(ser, command, data=[]):
    """Envía comandos MSP a los motores"""
    header = b'$M<'
    checksum = len(data) ^ command
    for d in data: checksum ^= d
    message = header + struct.pack('<BB', len(data), command) + bytes(data) + struct.pack('<B', checksum)
    ser.write(message)

def main():
    global joystick_updated
    
    # Inicializar UARTs
    ser_motors = serial.Serial(UART_MOTOR_PORT, BAUDRATE, timeout=1)
    ser_servos = serial.Serial(UART_SERVO_PORT, BAUDRATE, timeout=1)
    time.sleep(1)  # Esperar inicialización
    
    # Iniciar hilo receptor
    Thread(target=udp_receiver, daemon=True).start()
    
    # Armar los motores
    send_msp(ser_motors, 216, [1])  # MSP_SET_ARMING
    time.sleep(1)
    
    try:
        print("Control activo. Joystick para motores, botones 1-4 para servos.")
        print("Mantén botón para incrementar, doble-click+mantén para decrementar.")
        
        while True:
            if joystick_updated:
                # Control de motores
                motor_values = calculate_motor_values(joystick_data["axes"])
                data = struct.pack('<'+'H'*4, *motor_values)
                send_msp(ser_motors, 214, data)  # MSP_SET_MOTOR
                
                # Control de servos
                update_servo_positions()
                send_servo_commands(ser_servos)
                
                # Mostrar estado
                print(f"\rMotores: {motor_values} | X: {joystick_data['axes'][0]:.2f} | Y: {joystick_data['axes'][1]:.2f}", end="")
                joystick_updated = False
                
            time.sleep(0.02)
            
    except KeyboardInterrupt:
        print("\nDeteniendo motores y centrando servos...")
        send_msp(ser_motors, 214, struct.pack('<'+'H'*4, *[1000]*4))
        for i in range(4):
            servo_positions[i] = 1000
        send_servo_commands(ser_servos)
    finally:
        ser_motors.close()
        ser_servos.close()

if __name__ == "__main__":
    main()