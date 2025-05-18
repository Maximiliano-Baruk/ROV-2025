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

# ---------- CONFIGURACIÓN MEJORADA ----------
UDP_IP = "192.168.1.105"  # IP Orange Pi
UDP_PORT = 5005
TCP_HOST = "192.168.1.105"
TCP_PORT = 12345
BUFFER_SIZE = 4096
MAX_RETRIES = 5
RETRY_DELAY = 3

# ---------- COLA PARA COMUNICACIÓN ENTRE HILOS ----------
video_restart_queue = Queue()

# ---------- FUNCIÓN MEJORADA PARA VIDEO ----------
def recibir_video():
    retry_count = 0
    while retry_count < MAX_RETRIES:
        try:
            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.settimeout(5.0)  # Timeout para conexión
            
            print(f"🔌 Conectando a {TCP_HOST}:{TCP_PORT}...")
            client_socket.connect((TCP_HOST, TCP_PORT))
            print("✅ Conexión de video establecida")
            
            data = b""
            payload_size = struct.calcsize("L")
            retry_count = 0  # Resetear contador si hay éxito

            while True:
                try:
                    # Recepción de frames con timeout
                    while len(data) < payload_size:
                        chunk = client_socket.recv(BUFFER_SIZE)
                        if not chunk:
                            raise ConnectionError("Conexión cerrada por el servidor")
                        data += chunk

                    packed_msg_size = data[:payload_size]
                    data = data[payload_size:]
                    msg_size = struct.unpack("L", packed_msg_size)[0]

                    while len(data) < msg_size:
                        chunk = client_socket.recv(BUFFER_SIZE)
                        if not chunk:
                            raise ConnectionError("Conexión interrumpida")
                        data += chunk

                    frame_data = data[:msg_size]
                    data = data[msg_size:]
                    frame = pickle.loads(frame_data)
                    cv2.imshow("Video Stream", frame)
                    
                    if cv2.waitKey(25) == ord('q'):
                        break

                except (socket.timeout, ConnectionError) as e:
                    print(f"⚠️ Error en video: {str(e)}")
                    break

        except Exception as e:
            retry_count += 1
            print(f"❌ Fallo conexión video (Intento {retry_count}/{MAX_RETRIES}): {str(e)}")
            if client_socket:
                client_socket.close()
            time.sleep(RETRY_DELAY)
            
        finally:
            if 'client_socket' in locals():
                client_socket.close()
            cv2.destroyAllWindows()

    video_restart_queue.put("restart")

# ---------- FUNCIÓN MEJORADA PARA JOYSTICK ----------
def enviar_datos_joystick():
    pygame.init()
    try:
        joystick = pygame.joystick.Joystick(0)
        joystick.init()
    except:
        print("❌ No se detectó joystick")
        return

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)

    print("🕹️ Enviando datos del control...")
    while True:
        try:
            pygame.event.pump()
            
            axes = [round(joystick.get_axis(i), 2) for i in range(joystick.get_numaxes())]
            buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
            hats = [joystick.get_hat(i) for i in range(joystick.get_numhats())]

            mensaje = json.dumps({
                "axes": axes,
                "buttons": buttons,
                "hats": hats
            }).encode('utf-8')
            
            sock.sendto(mensaje, (UDP_IP, UDP_PORT))
            time.sleep(0.1)

        except pygame.error as e:
            print(f"🎮 Error en joystick: {str(e)}")
            time.sleep(1)
        except socket.error as e:
            print(f"📡 Error de red: {str(e)}")
            time.sleep(1)

# ---------- MANEJADOR DE SEÑALES ----------
def handler(signum, frame):
    print("\n🔌 Cerrando conexiones...")
    video_restart_queue.put("exit")
    raise SystemExit

signal.signal(signal.SIGINT, handler)

# ---------- HILO DE MONITOREO ----------
def monitor_thread():
    while True:
        msg = video_restart_queue.get()
        if msg == "exit":
            break
        elif msg == "restart":
            print("\n♻️ Reiniciando cliente de video...")
            time.sleep(RETRY_DELAY)
            threading.Thread(target=recibir_video, daemon=True).start()

# ---------- EJECUCIÓN PRINCIPAL ----------
if __name__ == "__main__":
    print("🚀 Iniciando cliente de control y video")
    
    # Hilo de monitoreo
    threading.Thread(target=monitor_thread, daemon=True).start()
    
    # Hilos principales
    threading.Thread(target=recibir_video, daemon=True).start()
    threading.Thread(target=enviar_datos_joystick, daemon=True).start()

    # Mantener el programa activo
    while True:
        time.sleep(1)