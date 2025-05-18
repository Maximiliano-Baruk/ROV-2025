import pygame
import socket
import json
import time

# Inicializar pygame y el joystick
pygame.init()
joystick = pygame.joystick.Joystick(0)
joystick.init()

# Configuración UDP
UDP_IP = "192.168.1.102"  # IP de la Orange Pi
UDP_PORT = 5005
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

print("Enviando datos JSON del control... (Ctrl+C para detener)")
try:
    while True:
        pygame.event.pump()  # Procesar eventos
        
        # Capturar ejes, botones y hats (SOLO AGREGADO ESTA LÍNEA)
        axes = [round(joystick.get_axis(i), 2) for i in range(joystick.get_numaxes())]
        buttons = [joystick.get_button(i) for i in range(joystick.get_numbuttons())]
        hats = [joystick.get_hat(i) for i in range(joystick.get_numhats())]  # <- NUEVO
        
        # Crear estructura JSON con identificadores claros (AGREGADO "hats")
        datos = {
            "axes": axes,
            "buttons": buttons,
            "hats": hats,  # <- NUEVO
            #"timestamp": time.time()
        }
        
        # Enviar como JSON
        mensaje = json.dumps(datos).encode('utf-8')
        sock.sendto(mensaje, (UDP_IP, UDP_PORT))
        print(f"Enviado: {datos}")

        time.sleep(0.1)  # Evitar saturación

except KeyboardInterrupt:
    print("\nCliente detenido.")
    sock.close()