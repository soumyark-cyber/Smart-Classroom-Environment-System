from machine import Pin, I2C
import time
import dht

# ---------------- LCD DRIVER ----------------
class I2cLcd:
    def __init__(self, i2c, addr, rows, cols):
        self.i2c = i2c
        self.addr = addr
        self.rows = rows
        self.cols = cols
        self.backlight = 0x08
        self._init_lcd()

    def _write_byte(self, data):
        self.i2c.writeto(self.addr, bytes([data | self.backlight]))

    def _pulse_enable(self, data):
        self._write_byte(data | 0x04)
        time.sleep_us(500)
        self._write_byte(data & ~0x04)
        time.sleep_us(100)

    def _write4bits(self, data):
        self._write_byte(data)
        self._pulse_enable(data)

    def _send(self, value, mode):
        self._write4bits((value & 0xF0) | mode)
        self._write4bits(((value << 4) & 0xF0) | mode)

    def command(self, cmd):
        self._send(cmd, 0)
        time.sleep_ms(2)

    def write_char(self, char):
        self._send(ord(char), 1)

    def clear(self):
        self.command(0x01)

    def move_to(self, col, row):
        row_offsets = [0x00, 0x40]
        self.command(0x80 | (col + row_offsets[row]))

    def putstr(self, text):
        for c in text:
            self.write_char(c)

    def _init_lcd(self):
        time.sleep_ms(20)
        self._write4bits(0x30)
        time.sleep_ms(5)
        self._write4bits(0x30)
        self._write4bits(0x20)
        self.command(0x28)
        self.command(0x0C)
        self.command(0x06)
        self.clear()

# ---------------- HARDWARE ----------------
i2c = I2C(0, scl=Pin(22), sda=Pin(21))
lcd = I2cLcd(i2c, 0x27, 2, 16)

dht_sensor = dht.DHT11(Pin(4))
mq2 = Pin(15, Pin.IN)

ir_entry = Pin(33, Pin.IN)
ir_exit = Pin(12, Pin.IN)

# LEDs & Fan (FIXED GPIO)
light1 = Pin(18, Pin.OUT)
light2 = Pin(19, Pin.OUT)
light3 = Pin(23, Pin.OUT)   
fan = Pin(14, Pin.OUT)
alert_led = Pin(5, Pin.OUT)
buzzer = Pin(25, Pin.OUT)

# ---------------- VARIABLES ----------------
count_in = 0
count_out = 0
in_class = 0

entry_state = 1
exit_state = 1

TEMP_LIMIT = 40

lcd.putstr("Smart Classroom")
time.sleep(2)
lcd.clear()

# ---------------- MAIN LOOP ----------------
while True:

    # ENTRY DETECTION
    if ir_entry.value() == 0 and entry_state == 1:
        in_class += 1
        count_in += 1
        entry_state = 0

    if ir_entry.value() == 1:
        entry_state = 1

    # EXIT DETECTION
    if ir_exit.value() == 0 and exit_state == 1:
        if in_class > 0:
            in_class -= 1
            count_out += 1
        exit_state = 0

    if ir_exit.value() == 1:
        exit_state = 1

    # SENSOR READ
    try:
        dht_sensor.measure()
        temp = dht_sensor.temperature()
    except:
        temp = 25   # safer default

    gas = mq2.value()

    # ALERT SYSTEM
    danger = False
    if gas == 0 or temp >= TEMP_LIMIT:
        alert_led.on()
        buzzer.on()
        danger = True
    else:
        alert_led.off()
        buzzer.off()

    # LIGHT CONTROL
    if in_class > 0:
        light1.on()
        light2.on()
        light3.on()
    else:
        light1.off()
        light2.off()
        light3.off()

    # FAN CONTROL
    if in_class > 0 and temp > 25:
        fan.on()
    else:
        fan.off()

    # LCD DISPLAY (NO FLICKER)
    lcd.move_to(0, 0)
    lcd.putstr("IN:{} OUT:{}  ".format(count_in, count_out))

    lcd.move_to(0, 1)
    if danger:
        lcd.putstr("ALERT!         ")
    else:
        lcd.putstr("P:{} T:{}C   ".format(in_class, temp))

    time.sleep(1)