import gpiod
import time

#ESTE CODIGO ES PARA VER GPIOS 

# Configuración de GPIOs (GPIO35, GPIO92, GPIO48, GPIO52)
GPIO_MAPPING = {
    'MOTOR_A': {'chip': 'gpiochip1', 'offset': 3},   # GPIO35 (pin 26)
    'MOTOR_B': {'chip': 'gpiochip2', 'offset': 28},  # GPIO92 (pin 22)
    'MOTOR_C': {'chip': 'gpiochip2', 'offset': 16},  # GPIO48 (pin 21) 🔄 Nuevo
    'MOTOR_D': {'chip': 'gpiochip2', 'offset': 20},  # GPIO52 (pin 24)
}

def setup_gpios():
    lines = {}
    for name, config in GPIO_MAPPING.items():
        try:
            chip = gpiod.Chip(config['chip'])
            line = chip.get_line(config['offset'])
            line.request(consumer="MOTORS", type=gpiod.LINE_REQ_DIR_OUT)
            lines[name] = line
            print(f"✅ {name} (offset {config['offset']}) configurado.")
        except Exception as e:
            print(f"❌ Error en {name}: {e}")
            print(f"Solución: Ejecuta 'echo {config['offset']} | sudo tee /sys/class/gpio/unexport'")
            print("O añade 'disable-spi4' en /boot/armbianEnv.txt y reinicia.")
            raise
    return lines

def main():
    try:
        lines = setup_gpios()
        print("Control activo. Presiona Ctrl+C para detener.")
        while True:
            # Secuencia 1: MOTOR_A=1, MOTOR_B=0, MOTOR_C=1, MOTOR_D=0
            lines['MOTOR_A'].set_value(1)
            lines['MOTOR_B'].set_value(0)
            lines['MOTOR_C'].set_value(1)
            lines['MOTOR_D'].set_value(0)
            time.sleep(2)
            
            # Secuencia 2: Invertir estados
            lines['MOTOR_A'].set_value(0)
            lines['MOTOR_B'].set_value(1)
            lines['MOTOR_C'].set_value(0)
            lines['MOTOR_D'].set_value(1)
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\nApagando GPIOs...")
        for line in lines.values():
            line.set_value(0)
            line.release()

if __name__ == "__main__":
    main()