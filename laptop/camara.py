import socket
import pickle
import struct
import cv2

HOST = '192.168.1.102'
PORT = 12345

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))

data = b""
payload_size = struct.calcsize("L")

cv2.namedWindow("Video", cv2.WINDOW_NORMAL)

try:
    while True:
        while len(data) < payload_size:
            data += client_socket.recv(4096)
        packed_msg_size = data[:payload_size]
        data = data[payload_size:]
        msg_size = struct.unpack("L", packed_msg_size)[0]
        
        while len(data) < msg_size:
            data += client_socket.recv(4096)
        frame_data = data[:msg_size]
        data = data[msg_size:]
        frame = pickle.loads(frame_data)
        
        cv2.imshow("Video", frame)
        if cv2.waitKey(25) == ord('q'):
            break
finally:
    client_socket.close()
    cv2.destroyAllWindows()