import sys
import requests
import colorthief

from io import BytesIO

resp = requests.get(sys.argv[1])
file = BytesIO(resp.content)
print('{:02x}{:02x}{:02x}'.format(*colorthief.ColorThief(file).get_color()))
