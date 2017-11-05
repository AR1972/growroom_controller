from BME280 import *
from TSL2591 import *
from MCP230xx import *
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

cooling_enable = 1
dehumidifier_enable = 1

run = 1

air_sensor = BME280(p_mode=BME280_OSAMPLE_8, t_mode=BME280_OSAMPLE_2, h_mode=BME280_OSAMPLE_1, filter=BME280_FILTER_16)
light_sensor = TSL2591()
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

def read_sensors():
  try:
    global degrees
    global pascals
    global humidity
    global ppm
    global lux
    while run == 1:
      degrees = air_sensor.read_temperature()
      pascals = air_sensor.read_pressure()
      humidity = air_sensor.read_humidity()
      ppm = 420
      full, ir = light_sensor.get_full_luminosity()
      lux = light_sensor.calculate_lux(full, ir)

  finally:
    exit(0)

def main(stdscr):
  try:
    for i in range(8):
      relays.setup(i, GPIO.OUT)

    for i in range(8):
      relays.output(i, OFF)

    r = threading.Thread(target=read_sensors)

    global run
    global cooling_enable
    global dehumidifier_enable
    global degrees
    global pascals
    global humidity
    global ppm
    global lux

    r.start()
    time.sleep(1) # give sensors a sec to start outputing data
    stdscr.nodelay(1)
    while 1:
      k = stdscr.getch()
      if k == ord('q'):
        run = 0
        for i in range(8):
          relays.output(i, OFF)

        exit(0)

      hectopascals = pascals / 100
      hours = strftime("%H", localtime())
      minutes = strftime("%M", localtime())
      seconds = strftime("%S", localtime())

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

      if degrees > 30:
        if cooling_enable == 1:
          relays.output(COOL, ON)
          cooling_enable = 0
          c = threading.Thread(target=cooling_lockout)
          c.start()
          relays.output(EXHAUST, ON)
      elif degrees <= 27:
          relays.output(COOL, OFF)
          relays.output(EXHAUST, OFF)

# heating ------------------------------------------

      if degrees < 20:
        relays.output(HEAT, ON)
        relays.output(EXHAUST, OFF)
      elif degrees >= 21:
        relays.output(HEAT, OFF)

# humidity ------------------------------------------

      if humidity > 50:
        if dehumidifier_enable == 1:
          relays.output(DEHUMIDIFIER, ON)
          dehumidifier_enable = 0
          h = threading.Thread(target=dehumidifier_lockout)
          h.start()
      elif  humidity <= 45:
          relays.output(DEHUMIDIFIER, OFF)

# CO2 ------------------------------------------------

      if ppm < 400:
        relays.output(CO2, ON)
      elif ppm >= 600:
        relays.output(CO2, OFF)
      elif ppm > 2000:
        relays.output(CO2, OFF)
        relays.output(EXHAUST, ON)

# display sensor output ------------------------------

      stdscr.erase()
      stdscr.addstr(0, 0, 'Time      = %s:%s:%s' % (hours, minutes, seconds))
      stdscr.addstr(1, 0, 'Temp      = %0.3f deg C (%0.3f deg F)' % (degrees, ((degrees*9/5)+32)))
      stdscr.addstr(2, 0, 'Pressure  = %0.2f hPa' % hectopascals)
      stdscr.addstr(3, 0, 'Humidity  = %0.2f %%' % humidity)
      stdscr.addstr(4, 0, 'Lux       = %s' % lux)
      stdscr.addstr(5, 0, 'PPM       = %s' % ppm)
      stdscr.addstr(7, 0, 'Press Q key to exit...')
      stdscr.refresh()
      time.sleep(.5)

  finally:
    run = 0
    for i in range(8):
      relays.output(i, OFF)

    exit(0)

curses.wrapper(main)
