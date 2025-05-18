import serial  # Importa la biblioteca para comunicación serial
import time    # Importa la biblioteca para funciones de tiempo (como sleep)




# ESTE CODIGO CONTROLA LA TOROBOT






# --- Configuración ---
# ¡IMPORTANTE! Reemplaza '/dev/ttyS?' con el nombre real del puerto serie en tu Orange Pi 5.
# Podría ser algo como /dev/ttyS1, /dev/ttyS3, /dev/ttyAMA0, etc.
# Puedes intentar averiguarlo con comandos como: ls /dev/tty*
# O revisando la documentación específica de tu Orange Pi y cómo habilitaste el UART.
serial_port_name = '/dev/ttyS4' # <--- CAMBIA ESTO
baud_rate = 115200

# --- Bloque 'setup' (se ejecuta una vez) ---
try:
    # Inicializa la conexión serial (equivalente a Serial.begin())
    # timeout=1 significa que las lecturas esperarán máximo 1 segundo (aunque aquí solo escribimos)
    ser = serial.Serial(serial_port_name, baud_rate, timeout=1)
    print(f"Puerto serie {serial_port_name} abierto correctamente a {baud_rate} baudios.")
    # Es buena práctica esperar un momento después de abrir el puerto
    time.sleep(2)

    # --- Bloque 'loop' (se ejecuta continuamente) ---
    while True:
        # Define el primer comando. 'b' lo convierte en bytes.
        # Añadimos '\r\n' para replicar el comportamiento de println()
        comando1 = b"#1P2500T1000\r\n" 
        #3P500T1000\r\n ser.write(comando2)
        # Envía el comando por el puerto serie (equivalente a Serial.println(...))
        ser.write(comando1)
       
        # Opcional: Imprime en la consola de Python lo que se envió (sin el \r\n)
        print(f"Enviado: {comando1.decode('utf-8').strip()}")

        # Espera 1000 milisegundos (1 segundo), equivalente a delay(1000)
        time.sleep(1.0)

        # # Define el segundo comando
        # comando2 = b"#3P1500T1000\r\n"
        # # Envía el segundo comando
        # ser.write(comando2)
        # # Opcional: Imprime en la consola de Python lo que se envió
        # print(f"Enviado: {comando2.decode('utf-8').strip()}")

        # # Espera 1 segundo
        # time.sleep(1.0)

# --- Manejo de errores y cierre ---
except serial.SerialException as e:
    # Se ejecuta si hay un error al abrir o usar el puerto serie
    print(f"Error al abrir o escribir en el puerto serie {serial_port_name}: {e}")
    print("Verifica que el nombre del puerto sea correcto y que tengas permisos.")
except KeyboardInterrupt:
    # Se ejecuta si presionas Ctrl+C para detener el script
    print("\nPrograma detenido por el usuario.")
finally:
    # Este bloque se ejecuta siempre al final, ya sea por error o interrupción
    if 'ser' in locals() and ser.is_open:
        ser.close() # Cierra el puerto serie si estaba abierto
        print(f"Puerto serie {serial_port_name} cerrado.")