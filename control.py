import socket
import json

# ESTE CODIGO LEE EL CONTROL

UDP_IP = "0.0.0.0"
UDP_PORT = 5005

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print("Esperando datos del control (mismo formato que la laptop)...")
try:
    while True:
        data, addr = sock.recvfrom(1024)
        try:
            # Decodificar JSON y mostrarlo IDÉNTICO a la laptop
            datos = json.loads(data.decode('utf-8'))
            print("\nRecibido:")
            print(json.dumps(datos, indent=2))  # Pretty-print idéntico
            
            # Opcional: Mostrar ejes y botones por separado
            print("\nResumen:")
            print("Ejes:", datos["axes"])
            print("Botones:", datos["buttons"])
            
        except json.JSONDecodeError:
            print("Error: Datos no son JSON válido. Raw:", data)

except KeyboardInterrupt:
    print("\nServidor detenido.")
    sock.close()