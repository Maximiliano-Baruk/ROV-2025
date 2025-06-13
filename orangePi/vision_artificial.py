import cv2
import numpy as np

# Configuración inicial
KNOWN_DISTANCE = 20.0  # Distancia inicial de calibración (cm)
KNOWN_WIDTH = 10.0      # Ancho conocido del objeto de calibración (cm)

# Variables globales
ref_points = []
measurements = []
focal_length = None
measuring = False
current_points = []
window_created = False  # Bandera para controlar si la ventana fue creada

def calculate_focal_length(measured_width, known_width, known_distance):
    """Calcula la longitud focal usando la fórmula de perspectiva"""
    return (measured_width * known_distance) / known_width

def distance_to_camera(known_width, focal_length, perceived_width):
    """Calcula la distancia a la cámara usando la longitud focal"""
    return (known_width * focal_length) / perceived_width

def click_event(event, x, y, flags, params):
    global ref_points, focal_length, measuring, current_points
    
    if measuring:
        if event == cv2.EVENT_LBUTTONDOWN and len(current_points) < 2:
            current_points.append((x, y))
    else:
        if event == cv2.EVENT_LBUTTONDOWN and len(ref_points) < 2:
            ref_points.append((x, y))
            
            if len(ref_points) == 2:
                pixel_width = np.sqrt((ref_points[1][0] - ref_points[0][0])**2 + 
                             (ref_points[1][1] - ref_points[0][1])**2)
                
                if focal_length is None:
                    focal_length = calculate_focal_length(pixel_width, KNOWN_WIDTH, KNOWN_DISTANCE)
                    print(f"Longitud focal calibrada: {focal_length:.2f} píxeles")
                
                measurements.append({
                    'points': ref_points.copy(),
                    'pixel_width': pixel_width,
                    'distance': KNOWN_DISTANCE,
                    'measured_width': KNOWN_WIDTH
                })
                ref_points = []

def draw_measurements(frame):
    for i, m in enumerate(measurements):
        pt1, pt2 = m['points']
        cv2.line(frame, pt1, pt2, (0, 255, 0), 2)
        cv2.circle(frame, pt1, 5, (0, 0, 255), -1)
        cv2.circle(frame, pt2, 5, (0, 0, 255), -1)
        
        mid_x = (pt1[0] + pt2[0]) // 2
        mid_y = (pt1[1] + pt2[1]) // 2
        
        text = f"{m['measured_width']}cm @ {m['distance']}cm"
        cv2.putText(frame, text, (mid_x, mid_y - 10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 0), 2)

def measure_new_object(p1, p2):
    if focal_length is None:
        return 0, 0
    
    pixel_width = np.sqrt((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)
    avg_distance = np.mean([m['distance'] for m in measurements]) if measurements else KNOWN_DISTANCE
    real_width = (pixel_width * avg_distance) / focal_length
    
    return pixel_width, real_width

# Configuración principal
cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("Error: No se pudo abrir la cámara")
    exit()

# Intenta crear la ventana varias veces si es necesario
max_attempts = 5
attempt = 0
window_name = "Sistema de Medición"

while attempt < max_attempts and not window_created:
    try:
        cv2.namedWindow(window_name, cv2.WINDOW_NORMAL)
        cv2.resizeWindow(window_name, 800, 600)
        cv2.setMouseCallback(window_name, click_event)
        window_created = True
    except:
        attempt += 1
        print(f"Intento {attempt} de crear ventana falló, reintentando...")
        cv2.waitKey(100)  # Pequeña pausa

if not window_created:
    print("Error: No se pudo crear la ventana después de varios intentos")
    cap.release()
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        print("Error: No se pudo capturar el frame")
        break
    
    frame = cv2.flip(frame, 1)
    
    # Dibujar instrucciones
    if focal_length is None:
        cv2.putText(frame, "1. Haz clic en los extremos de un objeto de 10cm a 20cm", 
                   (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
        cv2.putText(frame, f"(Actual: {len(ref_points)}/2 puntos)", 
                   (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    else:
        cv2.putText(frame, "2. Presiona 'm' para medir, luego haz clic en dos puntos", 
                   (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 1)
    
    draw_measurements(frame)
    
    if len(current_points) == 1:
        cv2.circle(frame, current_points[0], 5, (255, 0, 0), -1)
    elif len(current_points) == 2:
        pixel_width, real_width = measure_new_object(current_points[0], current_points[1])
        cv2.line(frame, current_points[0], current_points[1], (255, 0, 0), 2)
        cv2.putText(frame, f"{real_width:.1f} cm", 
                   ((current_points[0][0] + current_points[1][0]) // 2,
                    (current_points[0][1] + current_points[1][1]) // 2), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
    
    cv2.imshow(window_name, frame)
    
    key = cv2.waitKey(1) & 0xFF
    if key == ord('q'):
        break
    elif key == ord('m') and focal_length is not None:
        measuring = not measuring
        current_points = []
        print("Modo medición: " + ("ON" if measuring else "OFF"))
    elif key == ord('c'):
        try:
            new_dist = float(input("Ingrese nueva distancia de calibración (cm): "))
            KNOWN_DISTANCE = new_dist
            print(f"Nueva distancia de calibración: {KNOWN_DISTANCE}cm")
        except:
            print("Entrada inválida")

cap.release()
cv2.destroyAllWindows()