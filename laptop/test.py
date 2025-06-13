import pygame
import socket
import json
import time
import threading
import pickle
import struct
import cv2
from queue import Queue
import signal
import textwrap
from datetime import datetime

# ---------- CONFIGURACIÓN ----------
UDP_IP = "192.168.1.105"  # IP Orange Pi
UDP_PORT = 5005
TCP_HOST = "192.168.1.105"
TCP_PORT = 12345
BUFFER_SIZE = 4096
MAX_RETRIES = 5
RETRY_DELAY = 3

# ---------- VARIABLES GLOBALES ----------
status_data = {
    "motores": [1000, 1000, 1000, 1000],
    "servos": [1400]*10,
    "bombas": {"LLENAR": 0, "VACIAR": 0},
    "joystick": {"axes": [0.0]*8, "buttons": [0]*12, "hats": [(0,0)]},
    "last_update": time.time(),
    "video_connected": False,
    "connection_attempts": 0
}

# ---------- COLAS PARA COMUNICACIÓN ----------
video_restart_queue = Queue()
status_queue = Queue()

# ---------- FUNCIÓN PARA RECIBIR ESTADO ----------
def recibir_estado():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 5006))
    
    print("📊 Esperando datos de estado del robot...")
    while True:
        try:
            data, _ = sock.recvfrom(1024)
            estado = json.loads(data.decode('utf-8'))
            status_queue.put(estado)
            status_data["last_update"] = time.time()
        except Exception as e:
            print(f"⚠️ Error recibiendo estado: {str(e)}")
            time.sleep(1)

# ---------- FUNCIÓN MEJORADA PARA VIDEO CON RECONEXIÓN ----------
def recibir_video():
    retry_count = 0
    last_frame_time = time.time()
    
    while retry_count < MAX_RETRIES:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(10.0)
            client_socket.connect((TCP_HOST, TCP_PORT))
            print("✅ Conexión de video establecida")
            retry_count = 0
            
            data = b""
            payload_size = struct.calcsize("L")
            fps_counter = 0
            last_fps_time = time.time()
            
            cv2.namedWindow("Mosaico de Cámaras", cv2.WINDOW_NORMAL)
            cv2.resizeWindow("Mosaico de Cámaras", 640, 240)
            
            while True:
                # Recibe datos
                while len(data) < payload_size:
                    data += client_socket.recv(BUFFER_SIZE)
                
                packed_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("L", packed_size)[0]
                
                while len(data) < msg_size:
                    data += client_socket.recv(BUFFER_SIZE)
                
                frame_data = data[:msg_size]
                data = data[msg_size:]
                
                # Decodifica frame
                buffer = pickle.loads(frame_data)
                frame = cv2.imdecode(buffer, cv2.IMREAD_COLOR)
                
                # Calcula FPS
                fps_counter += 1
                if time.time() - last_fps_time >= 1.0:
                    print(f"📊 FPS: {fps_counter}")
                    fps_counter = 0
                    last_fps_time = time.time()
                
                # Muestra frame
                cv2.imshow("Mosaico de Cámaras", frame)
                
                if cv2.waitKey(1) == ord('q'):
                    raise KeyboardInterrupt
                
        except (socket.timeout, ConnectionError) as e:
            print(f"⚠️ Error: {str(e)}")
            retry_count += 1
            time.sleep(RETRY_DELAY)
        except KeyboardInterrupt:
            break
        finally:
            cv2.destroyAllWindows()
            client_socket.close() if 'client_socket' in locals() else None
    
    video_restart_queue.put("restart")
    
# ---------- FUNCIÓN PARA MOSTRAR ESTADO ----------
def mostrar_estado():
    last_clean_time = time.time()
    
    while True:
        if not status_queue.empty():
            estado = status_queue.get()
            status_data.update(estado)
        
        # Limpiar consola periódicamente
        if time.time() - last_clean_time > 1.0:
            print("\033c", end="")
            last_clean_time = time.time()
            
            # Mostrar información de conexión
            print("="*80)
            print("SISTEMA DE CONTROL REMOTO - ESTADO EN TIEMPO REAL".center(80))
            print(f"Última actualización: {datetime.now().strftime('%H:%M:%S')}".center(80))
            
            # Estado de conexión
            connection_status = "✅ CONECTADO" if status_data["video_connected"] else f"⚠️ RECONECTANDO (Intento {status_data['connection_attempts']})"
            print(f"\n🔗 Estado Conexión: {connection_status}")
            
            # Mostrar datos de estado
            print("\n💨 MOTORES:")
            print(f"  FL: {status_data['motores'][0]} | FR: {status_data['motores'][1]}")
            print(f"  RL: {status_data['motores'][2]} | RR: {status_data['motores'][3]}")
            
            print("\n⚙️ SERVOS:")
            print(f"  1-4: {status_data['servos'][:4]} (Botones ABXY)")
            print(f"  9-10: {status_data['servos'][8:10]} (Gatillos RT/LT)")
            
            print("\n💧 BOMBAS:")
            print(f"  Llenar: {'🔵 ACTIVADO' if status_data['bombas']['LLENAR'] else '⚪ Desactivado'} (Botón 7)")
            print(f"  Vaciar: {'🔴 ACTIVADO' if status_data['bombas']['VACIAR'] else '⚪ Desactivado'} (Botón 8)")
            
            print("\n🎮 JOYSTICK:")
            print(f"  Ejes X/Y: {status_data['joystick']['axes'][:2]} (HAT Digital)")
            print(f"  Gatillos: {status_data['joystick']['axes'][2:4]}")
            print(f"  Botones ABXY: {status_data['joystick']['buttons'][:4]}")
            print(f"  Botones LB/RB: {status_data['joystick']['buttons'][4:6]}")
            print(f"  Botones Bombas: {status_data['joystick']['buttons'][6:8]}")
            print(f"  Botones Sistema: {status_data['joystick']['buttons'][8:10]}")
            
            print("\n" + "="*80)
            print("Controles:".center(80))
            print("ABXY → Servos 1-4 | LB → Invertir | RT/LT → Servos 9-10".center(80))
            print("HAT → Motores | Botones 7/8 → Bombas | 9+RB → Reinicio".center(80))
            print("="*80)
        
        time.sleep(0.1)

# ---------- FUNCIÓN PARA ENVIAR DATOS DEL JOYSTICK ----------
def enviar_datos_joystick():
    pygame.init()
    try:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
        print(f"\n🎮 Control detectado: {joystick.get_name()}")
    except:
        print("\n❌ No se detectó joystick")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)

    print("🕹️ Enviando datos del control al robot...")
    while True:
        try:
            pygame.event.pump()
            
            axes = [round(joystick.get_axis(i), 2) for i in range(joystick.get_numaxes())]
            buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
            hats = [joystick.get_hat(i) for i in range(joystick.get_numhats())]

            # Actualizar estado local
            status_data["joystick"] = {
                "axes": axes + [0.0]*(8-len(axes)),
                "buttons": buttons + [0]*(12-len(buttons)),
                "hats": hats + [(0,0)]*(1-len(hats))
            }

            mensaje = json.dumps({
                "axes": axes,
                "buttons": buttons,
                "hats": hats
            }).encode('utf-8')
            
            sock.sendto(mensaje, (UDP_IP, UDP_PORT))
            time.sleep(0.1)

        except pygame.error as e:
            print(f"\n🎮 Error en joystick: {str(e)}")
            time.sleep(1)
        except socket.error as e:
            print(f"\n📡 Error de red: {str(e)}")
            time.sleep(1)

# ---------- MANEJADOR DE SEÑALES ----------
def handler(signum, frame):
    print("\n🔌 Cerrando conexiones...")
    video_restart_queue.put("exit")
    cv2.destroyAllWindows()
    raise SystemExit

signal.signal(signal.SIGINT, handler)

# ---------- HILO DE MONITOREO ----------
def monitor_thread():
    while True:
        msg = video_restart_queue.get()
        if msg == "exit":
            break
        elif msg == "restart":
            print(f"\n♻️ Reiniciando cliente de video en {RETRY_DELAY} segundos...")
            time.sleep(RETRY_DELAY)
            threading.Thread(target=recibir_video, daemon=True).start()

# ---------- EJECUCIÓN PRINCIPAL ----------
if __name__ == "__main__":
    print("\n🚀 Iniciando cliente de control y video")
    print(f"🔗 Conectando a Orange Pi en {TCP_HOST}")
    
    # Hilo de monitoreo
    threading.Thread(target=monitor_thread, daemon=True).start()
    
    # Hilos principales
    threading.Thread(target=recibir_video, daemon=True).start()
    threading.Thread(target=recibir_estado, daemon=True).start()
    threading.Thread(target=mostrar_estado, daemon=True).start()
    threading.Thread(target=enviar_datos_joystick, daemon=True).start()

    # Mantener el programa activo
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        handler(None, None)