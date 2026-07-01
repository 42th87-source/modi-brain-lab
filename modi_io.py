import math
import modi

class ModiIO:
    def __init__(self):
        print("MODI 연결 중...")
        self.bundle = modi.MODI()

        self.button = self.bundle.buttons[0]
        self.gyro = self.bundle.gyros[0]
        self.led = self.bundle.leds[0]
        self.speaker = self.bundle.speakers[0]

        print("MODI 연결 완료")

    def stimulus_on(self):
        self.led.rgb = 100, 100, 100
        self.speaker.tune = 880, 100

    def stimulus_off(self):
        self.led.turn_off()
        self.speaker.turn_off()

    def led_off(self):
        self.led.turn_off()

    def is_button_pressed(self):
        return self.button.pressed

    def get_gyro_state(self):
        pitch = self.gyro.pitch
        roll = self.gyro.roll

        wx = self.gyro.angular_vel_x
        wy = self.gyro.angular_vel_y
        wz = self.gyro.angular_vel_z

        angular_velocity = math.sqrt(wx ** 2 + wy ** 2 + wz ** 2)

        return {
            "pitch": pitch,
            "roll": roll,
            "angular_velocity": angular_velocity
        }