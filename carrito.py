import tkinter as tk
import math
import time
import random
import threading

# --- CLASE PIDController (Sin cambios) ---
class PIDController:
    def _init_(self, Kp, Ki, Kd):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.prev_error = 0
        self.integral = 0
        self.last_output = 0

    def compute(self, error, dt):
        if dt <= 0:
            derivative = 0
        else:
            derivative = (error - self.prev_error) / dt * 0.7
        self.integral = max(-50, min(self.integral + error * dt, 50))
        raw_output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        smoothed_output = 0.3 * raw_output + 0.7 * self.last_output
        self.last_output = smoothed_output
        self.prev_error = error
        return smoothed_output

# --- CLASE LineFollowerCar ---
class LineFollowerCar:
    def _init_(self, canvas, stops_list):
        self.canvas = canvas
        self.stops = stops_list
        self.car_x = self.stops[0][0] + 10
        self.car_y = self.stops[0][1] - 20
        if len(self.stops) > 1:
            dx = self.stops[1][0] - self.stops[0][0]
            dy = self.stops[1][1] - self.stops[0][1]
            self.car_angle = math.degrees(math.atan2(dy, dx))
        else:
            self.car_angle = 0

        self.speed = 1.5
        self.sensor_distance = 30
        self.sensor_offset = 20
        self.pid = PIDController(2.0, 0.00001, 0.00002)
        # Inicializar last_time AHORA
        self.last_time = time.time() # <<< Asegurarse de inicializarlo aquí
        self.trail = []
        self.last_angle_change = 0
        self.max_turn_rate = 3.5

        self.is_stopped_at_station = False
        self.waiting_for_station_confirmation = False
        self.current_stop_index = -1
        self.stop_radius = 30
        self.stop_message_id = None

        self.body = self.create_car_body()
        self.left_wheel = self.create_wheel()
        self.right_wheel = self.create_wheel()
        self.sensor_left = self.create_sensor()
        self.sensor_right = self.create_sensor()
        self.update_car()

    # --- (create_car_body, create_wheel, create_sensor, update_car, _update_wheel, get_sensor_positions sin cambios) ---
    def create_car_body(self):
        return self.canvas.create_polygon([0,0, 30,0, 30,20, 0,20], fill='#2E86C1', outline='#1B4F72', width=2)

    def create_wheel(self):
        return self.canvas.create_oval(0,0,8,8, fill='#2C3E50', outline='#1B2631')

    def create_sensor(self):
        return self.canvas.create_oval(0,0,6,6, fill='#E74C3C', outline='#922B21', width=1)

    def update_car(self):
        car_width = 20
        car_length = 30
        angle_rad = math.radians(self.car_angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        half_len = car_length / 2
        half_wid = car_width / 2
        points = [
            (-half_len, -half_wid), (half_len, -half_wid),
            (half_len, half_wid), (-half_len, half_wid)
        ]
        abs_points = []
        for x, y in points:
            rot_x = x * cos_a - y * sin_a
            rot_y = x * sin_a + y * cos_a
            abs_points.extend([self.car_x + rot_x, self.car_y + rot_y])
        self.canvas.coords(self.body, *abs_points)
        self._update_wheel(self.left_wheel, half_len * 0.6, -half_wid, angle_rad)
        self._update_wheel(self.right_wheel, half_len * 0.6, half_wid, angle_rad)
        sl, sr = self.get_sensor_positions()
        self.canvas.coords(self.sensor_left, sl[0]-3, sl[1]-3, sl[0]+3, sl[1]+3)
        self.canvas.coords(self.sensor_right, sr[0]-3, sr[1]-3, sr[0]+3, sr[1]+3)

    def _update_wheel(self, wheel, rel_x, rel_y, angle_rad):
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        rot_x = rel_x * cos_a - rel_y * sin_a
        rot_y = rel_x * sin_a + rel_y * cos_a
        center_x = self.car_x + rot_x
        center_y = self.car_y + rot_y
        wheel_radius = 4
        self.canvas.coords(wheel, center_x-wheel_radius, center_y-wheel_radius,
                           center_x+wheel_radius, center_y+wheel_radius)

    def get_sensor_positions(self):
        angle_rad = math.radians(self.car_angle)
        cos_a = math.cos(angle_rad)
        sin_a = math.sin(angle_rad)
        front_x = self.car_x + self.sensor_distance * cos_a
        front_y = self.car_y + self.sensor_distance * sin_a
        sensor_left_x = front_x - self.sensor_offset * sin_a
        sensor_left_y = front_y + self.sensor_offset * cos_a
        sensor_right_x = front_x + self.sensor_offset * sin_a
        sensor_right_y = front_y - self.sensor_offset * cos_a
        return (sensor_left_x, sensor_left_y), (sensor_right_x, sensor_right_y)


    # --- MODIFICACIÓN AQUÍ ---
    def wait_for_station_confirmation_thread(self):
        input() # Espera Enter en la consola
        print(f"--- Continuando desde Parada {self.current_stop_index + 1}... ---")

        # <<< ¡¡¡ LA CLAVE ESTÁ AQUÍ !!! >>>
        # Reseteamos last_time al tiempo actual ANTES de permitir que move() se ejecute de nuevo.
        self.last_time = time.time()

        # Ahora reseteamos los flags para permitir el movimiento
        self.is_stopped_at_station = False
        self.waiting_for_station_confirmation = False
        if self.stop_message_id:
            self.canvas.delete(self.stop_message_id)
            self.stop_message_id = None


    # --- (check_proximity_to_stops sin cambios lógicos) ---
    def check_proximity_to_stops(self):
        if self.waiting_for_station_confirmation:
            return True

        for i, stop_coord in enumerate(self.stops):
            dist_sq = (self.car_x - stop_coord[0])*2 + (self.car_y - stop_coord[1])*2
            if dist_sq < self.stop_radius**2 and i != self.current_stop_index and not self.is_stopped_at_station:
                self.is_stopped_at_station = True
                self.waiting_for_station_confirmation = True
                self.current_stop_index = i
                self.speed = 0 # Detener velocidad VISUAL

                print(f"\n=== Coche en Parada {i+1} ({stop_coord[0]}, {stop_coord[1]}) ===")
                print(">>> Presiona Enter en esta consola para continuar <<<")

                if self.stop_message_id:
                    self.canvas.delete(self.stop_message_id)
                self.stop_message_id = self.canvas.create_text(
                    stop_coord[0], stop_coord[1] - 35,
                    text=f"PARADA {i+1}\nEsperando...",
                    font=("Arial", 10, "bold"),
                    fill="blue",
                    anchor=tk.CENTER
                )

                confirm_thread = threading.Thread(target=self.wait_for_station_confirmation_thread, daemon=True)
                confirm_thread.start()
                return True
        return False


    # --- MODIFICACIÓN AQUÍ ---
    def move(self):
        if self.check_proximity_to_stops():
             self.update_car()
             return

        now = time.time()
        dt = now - self.last_time if now > self.last_time else 1e-3 # Calcular dt normal

        # <<< LIMITAR DT MÁXIMO >>>
        # Limita el paso de tiempo máximo a, por ejemplo, 0.1 segundos (100ms)
        # Esto previene saltos enormes si el bucle se retrasa mucho por cualquier razón.
        dt = min(dt, 0.1)

        self.last_time = now # Actualizar last_time para el próximo ciclo

        # --- Resto de la lógica de move sin cambios ---
        sl, sr = self.get_sensor_positions()
        sc = ((sl[0]+sr[0])/2, (sl[1]+sr[1])/2)

        left_active = self.check_sensor(*sl)
        right_active = self.check_sensor(*sr)
        center_active = self.check_sensor(*sc)

        state = 'none'
        if left_active and right_active: state = 'both'
        elif left_active: state = 'left'
        elif right_active: state = 'right'
        elif center_active: state = 'center'

        error = 0
        base_speed = 1.5
        if state == 'none':
            self.speed = base_speed * 0.5
            error = self.pid.prev_error * 1.5
        else:
            if state == 'both': self.speed = base_speed * 1.2; error = 0
            elif state == 'center': self.speed = base_speed; error = 0.1 * self.pid.prev_error
            elif state == 'left': self.speed = base_speed * 0.7; error = 3.0
            elif state == 'right': self.speed = base_speed * 0.7; error = -3.0

            steering = self.pid.compute(error, dt) # PID usa el dt (ahora limitado)
            steering = max(-self.max_turn_rate, min(steering, self.max_turn_rate))
            self.car_angle += steering

        rad = math.radians(self.car_angle)
        # El movimiento usa el dt (ahora limitado)
        move_dist = self.speed * dt * 60
        self.car_x += move_dist * math.cos(rad)
        self.car_y += move_dist * math.sin(rad)

        self.car_x = max(20, min(self.car_x, 780))
        self.car_y = max(20, min(self.car_y, 580))

        self.trail.append((self.car_x, self.car_y))
        if len(self.trail) > 150: self.trail.pop(0)
        self.update_car()


    def check_sensor(self, x, y):
        global guide_line
        sensor_check_radius = 4
        overlap = self.canvas.find_overlapping(x - sensor_check_radius, y - sensor_check_radius,
                                               x + sensor_check_radius, y + sensor_check_radius)
        return guide_line in overlap


# --- Funciones Auxiliares y Configuración Global (sin cambios) ---
def create_track_path(stop_points_for_line):
    pts = []
    pts.extend(stop_points_for_line)
    return [coord for pt in pts for coord in pt]

window = tk.Tk()
window.title("Seguidor de Línea con Paradas (Fix Teleport)")
canvas = tk.Canvas(window, width=800, height=600, bg='#EAEAEA')
canvas.pack()

stops_unique_coords = [
    (200, 500), (350, 150), (650, 150), (700, 400), (400, 550),
]
stops_for_line_drawing = stops_unique_coords + [stops_unique_coords[0]]

track_width = 60
track = canvas.create_line(
    create_track_path(stops_for_line_drawing),
    fill='#4D5656', width=track_width,
    capstyle=tk.ROUND, joinstyle=tk.ROUND
)

guide_line_width = 15
global guide_line
guide_line = canvas.create_line(
    create_track_path(stops_for_line_drawing),
    fill='black', width=guide_line_width,
    joinstyle=tk.ROUND, capstyle=tk.ROUND
)

for i, (x,y) in enumerate(stops_unique_coords, start=1):
    canvas.create_oval(x-20, y-20, x+20, y+20,
                       fill='#F1C40F', outline='#B7950B', width=3)
    canvas.create_text(x, y, text=f"S{i}", font=("Arial",12,"bold"))

car = LineFollowerCar(canvas, stops_unique_coords)

canvas.create_text(400, 30, text="Seguidor de Línea - Pista Irregular", font=("Arial",16,"bold"))

def game_loop():
    if not car.waiting_for_station_confirmation:
        car.move() # move ahora calcula dt correctamente después de pausa
        if random.random() > 0.7:
             if car.trail:
                last_pos = car.trail[-1]
                canvas.create_oval(last_pos[0]-0.5, last_pos[1]-0.5,
                                   last_pos[0]+0.5, last_pos[1]+0.5,
                                   fill='#E67E22', outline='')
    else:
        car.update_car()

    window.after(25, game_loop)

game_loop()
window.mainloop()