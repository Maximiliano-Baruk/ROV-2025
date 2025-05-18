import serial
import time
import struct

# ESTE CODIGO CONTROLA LA SPEEDY PRENDE MOTORES Y DPS LOS APAGA

# Configuración del UART
uart_port = '/dev/ttyS0'  # UART0 en Orange Pi 5
baudrate = 115200

# Inicializar UART
ser = serial.Serial(uart_port, baudrate, timeout=1)

def send_msp(command, data=[]):
    # Cabecera MSP como bytes (ya concatenados)
    header = b'$M<'
    # Calcular checksum
    checksum = len(data) ^ command
    for d in data:
        checksum ^= d
    # Construir mensaje correctamente
    message = (
        header +                      # Cabecera fija '$M<'
        struct.pack('<BB', len(data), command) +  # Longitud y comando
        bytes(data) +                 # Datos (si hay)
        struct.pack('<B', checksum)   # Checksum
    )
    ser.write(message)

def arm_drone():
    # Comando MSP_SET_ARMING (216) para armar (data = [1])
    send_msp(216, [1])

def set_motor_values(motor_values):
    # Comando MSP_SET_MOTOR (214) - motor_values es una lista de 4 valores (0-1000)
    data = struct.pack('<'+'H'*4, *motor_values)
    send_msp(214, data)

try:
    # Armar el drone (¡Asegúrate de que las hélices están quitadas!)
    arm_drone()
    time.sleep(1)

    # Ejemplo: Encender motores al 10% (valores entre 1000-2000, 1000 = 0%)
    motor_values = [1200, 1200, 1200, 1200]  # Valores para los 4 motores
    set_motor_values(motor_values)
    time.sleep(10)

    # Detener motores
    set_motor_values([1000, 1000, 1000, 1000])

finally:
    ser.close()