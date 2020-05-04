# Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

import time
import board
import busio
from digitalio import DigitalInOut
import neopixel
from adafruit_esp32spi import adafruit_esp32spi
from adafruit_esp32spi import adafruit_esp32spi_wifimanager
import adafruit_pyportal
import displayio
from adafruit_display_text.label import Label

from adafruit_bitmap_font import bitmap_font
font = bitmap_font.load_font("/fonts/OstrichSans-Heavy-18.bdf")

# font terminalio.FONT
# import terminalio

pyportal = adafruit_pyportal.PyPortal()
display = board.DISPLAY
splash = displayio.Group(max_size=9)
bg_group = displayio.Group(max_size=1)
btm_view = displayio.Group(max_size=9, x=20, y=140)
top_view = displayio.Group(max_size=9, x=20, y=20)

splash.append(bg_group)
splash.append(btm_view)
splash.append(top_view)

### WiFi ###

# Get wifi details and more from a secrets.py file
try:
    from secrets import secrets
except ImportError:
    print("WiFi secrets are kept in secrets.py, please add them there!")
    raise

interval_minutes = secrets['interval_minutes']
wifi = adafruit_esp32spi_wifimanager.ESPSPI_WiFiManager(pyportal._esp, secrets, None)

def invokeLambda(mars_api_url):
    headers = {"x-api-key": secrets['mars_api_key']}
    response = wifi.get(mars_api_url, headers=headers, timeout=30)
    data = response.json()
    print("JSON Response: ", data)
    response.close()
    return data

def downloadImage(url):
    max_retries = 5
    for i in range(max_retries):
        try:
            pyportal.wget(url, '/sd/cache.bmp', chunk_size=4096)
        except OSError as error:
            print(error)
            print("""\n\nNo writable filesystem found. Insert an SD card.""")
            continue
        except RuntimeError as error:
            print(error)
            print("wget didn't write a complete file")
            continue
        break

def setText(group, text, value, x, y):
    text = text + str(value)
    status_label = Label(font, text=text, color=0xa1251b, max_glyphs=200)
    status_label.x = x
    status_label.y = y
    group.append(status_label)
    return

def clearGroup(group):
    if group:
        size = len(group) - 1
        for x in range(0, size):
            group.pop()


def setInsight(insight):

    clearGroup(btm_view)
    clearGroup(top_view)

    setText(btm_view, 'Sol: ', insight['sol'], 0, 0)
    setText(btm_view, 'Avg Air Temp: ', insight['av_at'], 0, 20)
    setText(btm_view, 'Avg Wind Speed: ', insight['av_HWS'], 0, 40)
    setText(btm_view, 'Avg Pressure: ', insight['av_PRE'], 0, 60)

    setText(top_view, 'Last_UTC: ', insight['Last_UTC'], 0,0)
    setText(top_view, 'Martian Season: ', insight['season'], 0,20)
    return

def showDisplay(insight, displayTime=60.0):
    print('Setting background')
    with open("/sd/cache.bmp", "rb") as bitmap_file:
        bitmap = displayio.OnDiskBitmap(bitmap_file)
        tile_grid = displayio.TileGrid(bitmap, pixel_shader=displayio.ColorConverter())

        if bg_group:
            bg_group.pop()
        bg_group.append(tile_grid)

        setInsight(insight)

        display.show(splash)
        start = time.monotonic()
        while time.monotonic() - start < displayTime:
            pass

while True:
    data = invokeLambda(secrets['mars_api_url'])
    downloadImage(data['image_url'])
    showDisplay(data['insight'], displayTime=60*interval_minutes)
