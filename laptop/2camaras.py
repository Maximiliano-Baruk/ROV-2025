import cv2
import socket
import pickle
import struct
import time

def setup_windows():
    cv2.namedWindow('Cámara 1', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Cámara 1', 640, 480)
    cv2.moveWindow('Cámara 1', 100, 100)
    
    cv2.namedWindow('Cámara 2', cv2.WINDOW_NORMAL)
    cv2.resizeWindow('Cámara 2', 640, 480)
    cv2.moveWindow('Cámara 2', 800, 100)

def close_windows():
    cv2.destroyAllWindows()
    for i in range(5):  # Asegurar cierre de todas las ventanas
        cv2.waitKey(1)

def receive_video():
    setup_windows()
    
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.settimeout(5.0)  # Timeout de 5 segundos
    
    try:
        client_socket.connect(('192.168.1.105', 12345))
        print("✅ Conexión establecida con el servidor")
        
        data = b""
        payload_size = struct.calcsize("Q")
        last_update = time.time()
        
        while True:
            # Control de tiempo para evitar bucles infinitos
            if time.time() - last_update > 10.0:
                print("⚠️ Timeout: No se recibieron datos en 10 segundos")
                break
            
            # Recepción de datos
            try:
                while len(data) < payload_size:
                    packet = client_socket.recv(4096)
                    if not packet:
                        raise ConnectionError("Conexión cerrada por el servidor")
                    data += packet
                    last_update = time.time()
                
                packed_msg_size = data[:payload_size]
                data = data[payload_size:]
                msg_size = struct.unpack("Q", packed_msg_size)[0]
                
                while len(data) < msg_size:
                    packet = client_socket.recv(4096)
                    if not packet:
                        raise ConnectionError("Conexión interrumpida")
                    data += packet
                    last_update = time.time()
                
                frame_data = data[:msg_size]
                data = data[msg_size:]
                
                try:
                    received = pickle.loads(frame_data)
                    frame1 = received.get('cam1')
                    frame2 = received.get('cam2')
                    
                    if frame1 is not None and frame2 is not None:
                        cv2.imshow('Cámara 1', frame1)
                        cv2.imshow('Cámara 2', frame2)
                    else:
                        print("⚠️ Frame nulo recibido")
                        
                    # Tecla 'q' para salir
                    if cv2.waitKey(25) & 0xFF == ord('q'):
                        break
                        
                except Exception as e:
                    print(f"⚠️ Error procesando frame: {str(e)}")
                    
            except socket.timeout:
                print("⚠️ Timeout en recepción de datos")
                continue
                
    except Exception as e:
        print(f"❌ Error de conexión: {str(e)}")
    finally:
        client_socket.close()
        close_windows()
        print("🔌 Conexión cerrada")

if __name__ == "__main__":
    print("🚀 Iniciando cliente de video...")
    receive_video()
    print("👋 Programa terminado")