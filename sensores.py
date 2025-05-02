import network
import time
import ntptime
import machine
import urequests
from hx711 import HX711

# Configuración WiFi
SSID = "Familia VC"
PASSWORD = "sergio10203."

# Configuración de Firebase
FIREBASE_URL = "https://trabajo-12ee4-default-rtdb.firebaseio.com/"

# Zona horaria (UTC-5)
TIMEZONE_OFFSET = -5 * 3600

def conectar_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(SSID, PASSWORD)
    print("Conectando...")
    for _ in range(10):
        if wlan.isconnected():
            print("Conectado")
            return True
        time.sleep(1)
    return False

def obtener_fecha_hora():
    try:
        ntptime.settime()
        tiempo = time.localtime(time.time() + TIMEZONE_OFFSET)
        return list(tiempo[:6])
    except Exception as e:
        print("Error obteniendo hora:", e)
        return [0,0,0,0,0,0]

def incrementar_segundo(fecha_hora):
    fecha_hora[5] += 1
    if fecha_hora[5] >= 60:
        fecha_hora[5] = 0
        fecha_hora[4] += 1
        if fecha_hora[4] >= 60:
            fecha_hora[4] = 0
            fecha_hora[3] += 1
            if fecha_hora[3] >= 24:
                fecha_hora[3] = 0
                fecha_hora[2] += 1
    return fecha_hora

def redondear_peso(peso):
    return round(peso)

def enviar_a_firebase(datos):
    url = FIREBASE_URL + "monedas.json"
    for intento in range(5):
        try:
            respuesta = urequests.post(url, json=datos)
            respuesta.close()
            print("✅ Enviado")
            return
        except Exception as e:
            print(f"Error Firebase (Intento {intento+1}):", e)
            time.sleep(2)

if conectar_wifi():
    time.sleep(2)
    fecha_hora_actual = obtener_fecha_hora()

# Sensores IR
sensor_ir_caja1 = machine.Pin(16, machine.Pin.IN)
sensor_ir_caja2 = machine.Pin(17, machine.Pin.IN)
sensor_ir_caja3 = machine.Pin(18, machine.Pin.IN)

# Sensores HX711
hx_caja1 = HX711(dout=4, pd_sck=5)
hx_caja2 = HX711(dout=19, pd_sck=21)
hx_caja3 = HX711(dout=22, pd_sck=23)

hx_caja1.tare()
hx_caja2.tare()
hx_caja3.tare()

wdt = machine.WDT(timeout=5000)

conteo_global = 0
caja1 = caja2 = caja3 = 0
peso_caja1 = peso_caja2 = peso_caja3 = 0
buffer_datos = []
MAX_DATOS = 10

while True:
    wdt.feed()

    # Leer pesos
    try:
        peso1 = redondear_peso((hx_caja1.read() + 378000) * 20000 / 2100)
        peso2 = redondear_peso((hx_caja2.read() + 378000) * 20000 / 2100)
        peso3 = redondear_peso((hx_caja3.read() + 378000) * 20000 / 2100)
    except Exception as e:
        print("Error en HX711:", e)
        peso1 = peso2 = peso3 = 0

    # Lectura sensores IR
    if sensor_ir_caja1.value() == 1:
        caja1 += 1
        conteo_global += 1

    if sensor_ir_caja2.value() == 1:
        caja2 += 1
        conteo_global += 1

    if sensor_ir_caja3.value() == 1:
        caja3 += 1
        conteo_global += 1

    fecha_hora_actual = incrementar_segundo(fecha_hora_actual)
    fecha_hora_str = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d}".format(*fecha_hora_actual)

    datos = {
        "conteo_global": conteo_global,
        "fecha_hora_recoleccion": fecha_hora_str,
        "peso_caja1": peso1,
        "peso_caja2": peso2,
        "peso_caja3": peso3,
        "conteo_caja1": caja1,
        "conteo_caja2": caja2,
        "conteo_caja3": caja3
    }

    print(datos)
    buffer_datos.append(datos)

    if len(buffer_datos) >= MAX_DATOS:
        enviar_a_firebase(buffer_datos)
        buffer_datos.clear()

    time.sleep(1)