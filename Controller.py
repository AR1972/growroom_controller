from BME280 import *
from TSL2591 import *
from MCP230xx import *
from MHZ16 import *
from time import localtime, strftime
import curses
import threading

ON = 0
OFF = 1

LIGHT_1 = 0
LIGHT_2 = 1
EXHAUST = 2
HEAT = 3
COOL = 4
CIRCULATION = 5
CO2 = 6
DEHUMIDIFIER = 7

LIGHT_1_FLOWER = 0 # 1 = 12 hours, 0 = 18 hours
LIGHT_2_FLOWER = 0 # 1 = 12 hours, 0 = 18 hours

HEAT_HI = 21
HEAT_LOW = 20
COOL_HI = 30
COOL_LOW = 27
HUMIDITY_HI = 50
HUMIDITY_LOW = 45
CO2_LOW = 1000
CO2_HIGH = 1500
CO2_SAFETY = 2000

cooling_enable = 1
dehumidifier_enable = 1
safety_enable = 0
bus_lock = 0
run = 1
air_sensor = BME280(p_mode=BME280_OSAMPLE_8, t_mode=BME280_OSAMPLE_2, h_mode=BME280_OSAMPLE_1, filter=BME280_FILTER_16)
light_sensor = TSL2591()
co2_sensor = MHZ16(0x4D)
co2_sensor.begin()
co2_sensor.power_on()
co2_sensor_starting = 1
co2_restart_hour = 0
relays = MCP23017()
degrees = 0
pascals = 0
humidity = 0
ppm = 0
lux = 0

def cooling_lockout():
  global cooling_enable
  global run
  i = 0
  while run == 1 and i < 600:
    time.sleep(.5)
    i += 1
  cooling_enable = 1

def dehumidifier_lockout():
  global dehumidifier_enable
  global run
  i = 0
  while run == 1 and i < 600:
    time.sleep(.5)
    i += 1
  dehumidifier_enable = 1

def safety_lockout():
  global safety_enable
  global run
  global ppm
  global bus_lock
  i = 0
  # wait for co2 to be over the safty limit for 5 min
  while run == 1 and i < 600:
    time.sleep(.5)
    i += 1
  # if co2 level still above safty limit vent the room
  # for a minimum 1 min or until co2 level is safe and
  # block turning on any other equipment
  if ppm > CO2_SAFETY:
    while bus_lock == 1:
      time.sleep(.1)
    bus_lock = 1
    relays.output(EXHAUST, ON)
    bus_lock = 0
    safety_enable = 1
  i = 0
  while (run == 1 and ppm > CO2_SAFETY) or (run == 1 and i < 120):
    i += 1
    time.sleep(.5)
  # co2 should be at a safe level now, if we were in safty lock out
  # turn off exaust fan and clear lock out flag
  if safety_enable == 1:
    while bus_lock == 1:
      time.sleep(.1)
    bus_lock = 1
    relays.output(EXHAUST, OFF)
    bus_lock = 0
  safety_enable = 0

def co2_sensor_delay():
  global run
  global co2_sensor_starting
  i = 0
  while run == 1 and i <= 120:
    co2_sensor_starting = 1
    time.sleep(.5)
    i += 1
  co2_sensor_starting = 0

def read_sensors():
  try:
    global degrees
    global pascals
    global humidity
    global ppm
    global lux
    global bus_lock
    while run == 1:
      while bus_lock == 1:
        time.sleep(.1)
      bus_lock = 1
      degrees = air_sensor.read_temperature()
      pascals = air_sensor.read_pressure()
      humidity = air_sensor.read_humidity()
      if co2_sensor.measure():
        ppm = co2_sensor.ppm
      full, ir = light_sensor.get_full_luminosity()
      lux = light_sensor.calculate_lux(full, ir)
      bus_lock = 0
      time.sleep(.1)
  except:
    pass

def main(stdscr):
  try:
    relays.write_gpio([0xFF])
    relays.write_iodir([0x00])
    r = threading.Thread(target=read_sensors)
    d1 = threading.Thread(target=co2_sensor_delay)
    global run
    global cooling_enable
    global dehumidifier_enable
    global degrees
    global pascals
    global humidity
    global ppm
    global lux
    global safety_enable
    global bus_lock
    global co2_sensor_starting
    global co2_restart_hour
    r.start()
    d1.start()
    # restart co2 sensor every 12 hours to avoid auto calabration
    co2_restart_hour = localtime().tm_hour + 12
    if co2_restart_hour >= 24:
      co2_restart_hour = co2_restart_hour - 24
    time.sleep(1) # give sensors a sec to start outputing data
    stdscr.nodelay(1)
    while 1:
      k = stdscr.getch()
      if k == ord('q'):
        run = 0
        while bus_lock == 1:
          time.sleep(.1)
        bus_lock = 1
        relays.write_gpio([0xFF])
        co2_sensor.power_off()
        bus_lock = 0
        exit(0)
      hectopascals = pascals / 100
      hours = localtime().tm_hour
      minutes = localtime().tm_min
      seconds = localtime().tm_sec

# restart co2 sensor to avoid auto calibration -----

      if hours == co2_restart_hour:
        d2 = threading.Thread(target=co2_sensor_delay)
        d2.start()
        while bus_lock == 1:
          time.sleep(.1)
        bus_lock = 1
        co2_sensor.power_off()
        co2_sensor.power_on()
        bus_lock = 0
        co2_restart_hour = localtime().tm_hour + 12
        if co2_restart_hour >= 24:
          co2_restart_hour = co2_restart_hour - 24

# lock the I2C bus ---------------------------------

      while bus_lock == 1:
        time.sleep(.1)
      bus_lock = 1

# circulation --------------------------------------

      relays.output(CIRCULATION, ON)

# light 1 timer ------------------------------------

      if LIGHT_1_FLOWER == 1:
        if int(hours) >= 6 and int(minutes) >= 00:
          if int(hours) <=  17 and int(minutes) <= 59:
            relays.output(LIGHT_1, ON)
          else:
            relays.output(LIGHT_1, OFF)
        else:
           relays.output(LIGHT_1, OFF)
      else:
        if int(hours) >= 6 and int(minutes) >= 00:
          if int(hours) <= 23 and int(minutes) <= 59:
            relays.output(LIGHT_1, ON)
          else:
            relays.output(LIGHT_1, OFF)
        else:
            relays.output(LIGHT_1, OFF)

# light 2 timer ------------------------------------

      if LIGHT_2_FLOWER == 1:
        if int(hours) >= 6 and int(minutes) >= 00:
          if int(hours) <=  17 and int(minutes) <= 59:
            relays.output(LIGHT_2, ON)
          else:
            relays.output(LIGHT_2, OFF)
        else:
          relays.output(LIGHT_2, OFF)
      else:
        if int(hours) >= 6 and int(minutes) >= 00:
          if int(hours) <= 23 and int(minutes) <= 59:
            relays.output(LIGHT_2, ON)
          else:
            relays.output(LIGHT_2, OFF)
        else:
          relays.output(LIGHT_2, OFF)

# cooling -----------------------------------------

      if degrees > COOL_HI:
        if cooling_enable == 1:
          if saftey_enable == 0:
            relays.output(COOL, ON)
            cooling_enable = 0
            c = threading.Thread(target=cooling_lockout)
            c.start()
            relays.output(EXHAUST, ON)
      elif degrees <= COOL_LOW:
          relays.output(COOL, OFF)
          if safety_enable == 0:
            relays.output(EXHAUST, OFF)

# heating ------------------------------------------

      if degrees < HEAT_LOW:
        if safety_enable == 0:
          relays.output(HEAT, ON)
          relays.output(EXHAUST, OFF)
      elif degrees >= HEAT_HI:
        relays.output(HEAT, OFF)

# humidity ------------------------------------------

      if humidity > HUMIDITY_HI:
        if dehumidifier_enable == 1:
          if safety_enable == 0:
            relays.output(DEHUMIDIFIER, ON)
            dehumidifier_enable = 0
            h = threading.Thread(target=dehumidifier_lockout)
            h.start()
      elif  humidity <= HUMIDITY_LOW:
          relays.output(DEHUMIDIFIER, OFF)

# CO2 ------------------------------------------------

      if ppm < CO2_LOW:
        if safety_enable == 0 and co2_sensor_starting == 0:
          relays.output(CO2, ON)
      elif ppm >= CO2_HIGH:
        relays.output(CO2, OFF)
      if ppm > CO2_SAFETY:
        s = threading.Thread(target=safety_lockout)
        s.start()

# unlock the I2C bus ---------------------------------

      bus_lock = 0

# display sensor output ------------------------------

      stdscr.erase()
      stdscr.addstr(0, 0, 'Time      = %s:%s:%s' % (str(hours).zfill(2), str(minutes).zfill(2), str(seconds).zfill(2)))
      stdscr.addstr(1, 0, 'Temp      = %0.3f deg C (%0.3f deg F)' % (degrees, ((degrees*9/5)+32)))
      stdscr.addstr(2, 0, 'Pressure  = %0.2f hPa' % hectopascals)
      stdscr.addstr(3, 0, 'Humidity  = %0.2f %%' % humidity)
      stdscr.addstr(4, 0, 'Light     = %s lux' % lux)
      stdscr.addstr(5, 0, 'CO2       = %s ppm' % ppm)
      stdscr.addstr(7, 0, 'Press Q key to exit...')
      stdscr.refresh()
      time.sleep(.1)
  except Exception as e:
    z = e
    print z
  finally:
    run = 0
    co2_sensor.power_off()
    relays.write_gpio([0xFF])
    bus_lock = 0
    exit(1)
curses.wrapper(main)
