import socket
import json
import gpiod
from collections import defaultdict
import time
from threading import Thread

# ESTE CODIGO LEE EL CONTROL Y CONTROLA LAS BOMBAS
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

servo_positions = [1750,2000,1450,2350,1000,1000,1000,1000,1000,1000]

button_states = defaultdict(lambda: {'pressed': False, 'press_count': 0, 'last_press_time': 0})

# Configuración GPIOs para bombas
GPIO_MAPPING = {
    'BOMBA_LLENAR': {'chip': 'gpiochip1', 'offset': 3},   # GPIO35
    'BOMBA_VACIAR': {'chip': 'gpiochip2', 'offset': 28}, # GPIO92
}

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

def udp_receiver():
    global joystick_data, joystick_updated
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print("Esperando datos del control...")
    
    while True:
        data, _ = sock.recvfrom(1024)
        try:
            new_data = json.loads(data.decode('utf-8'))
            joystick_data["axes"] = new_data.get("axes", [0.0] * 8)
            joystick_data["buttons"] = new_data.get("buttons", [0] * 12)
            joystick_data["hats"] = new_data.get("hats", [(0, 0)])
            joystick_updated = True
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error en datos recibidos: {e}")

def main():
    # Inicialización
    lines = setup_gpios()
    
    # Hilos para operación concurrente
    udp_thread = Thread(target=udp_receiver)
    control_thread = Thread(target=control_bombas, args=(lines,))
    
    udp_thread.daemon = True
    control_thread.daemon = True
    
    udp_thread.start()
    control_thread.start()
    
    try:
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        print("\nApagando sistema...")
        for line in lines.values():
            line.set_value(0)
            line.release()
        print("Sistema apagado correctamente")

if __name__ == "__main__":
    main()