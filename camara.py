import cv2
import socket
import struct
import pickle

# ESTE CODIGO ES PARA VER CAMARA

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(('192.168.1.105', 12345))
server_socket.listen(5)
print("Esperando conexión...")

conn, addr = server_socket.accept()
print("Conexión establecida con:", addr)

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
            print("Cliente desconectado")
            break
finally:
    cap.release()
    conn.close()
    server_socket.close()