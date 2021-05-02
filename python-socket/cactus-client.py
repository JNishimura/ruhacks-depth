from PIL import Image
import numpy as np
import cv2
import socketio
import time
from io import BytesIO
import sys

image_dir = './cactusgarden_png/'
base_string = '00000'

sio = socketio.Client()
sio.connect('http://localhost:3000')

@sio.on('achooResponse')
def on_response(data):
    print(data)

time.sleep(1)

rgb_saved = BytesIO()
encoded_saved = BytesIO()

def encodeMWD(depth):
    NUM_STEPS = 2
    zmax = np.nanmax(depth)
    zmin = np.nanmin(depth)
    zrange = zmax - zmin
    p = zrange / NUM_STEPS

    depth = depth - (np.ones(np.shape(depth)) * (zmin + zmax) / 2)

    i_r = np.copy(depth)
    i_g = np.copy(depth)
    i_b = np.copy(depth)

    i_r[~np.isnan(i_r)] = 0.5 + 0.5 * np.sin(2 * np.pi * i_r[~np.isnan(i_r)] / p)
    i_g[~np.isnan(i_g)] = 0.5 + 0.5 * np.cos(2 * np.pi * i_g[~np.isnan(i_g)] / p)
    i_b[~np.isnan(i_b)] = (i_b[~np.isnan(i_b)] - zmin) / zrange

    encoded_rgb = np.stack([i_r, i_g, i_b], axis = -1)

    encoded_rgb *= 255
    encoded_rgb = encoded_rgb.astype(np.uint8)

    return encoded_rgb

for i in range(1, 200):
    if i == 10 or i == 100 or i == 1000:
        base_string = base_string[:-1]
    
    image_string = base_string + str(i) + '.png'

    print(image_string)

    rgb = Image.open(image_dir + 'color/' + image_string)
    depth = Image.open(image_dir + 'depth/' + image_string)

    rgb = np.asarray(rgb)
    depth = np.asarray(depth) / 1000

    if i == 4:
        print(np.min(depth), np.max(depth))
        print(np.min(rgb), np.max(rgb))

    encoded = encodeMWD(depth)
    cv2.imshow('RGB', rgb)
    cv2.imshow('Encoded', encoded)

    Image.fromarray(rgb, 'RGB').save(rgb_saved, format="png")
    Image.fromarray(encoded, 'RGB').save(encoded_saved, format="png")
    NUM_STEPS = 2
    zmax = np.nanmax(depth)
    zmin = np.nanmin(depth)
    zrange = zmax - zmin
    p = zrange / NUM_STEPS

    print(sys.getsizeof(encoded_saved.getvalue()))
    print(sys.getsizeof(rgb_saved.getvalue()))

    time.sleep(0.03)
    sio.emit('achoo', {'encoded': encoded_saved.getvalue(),
                       'texture': rgb_saved.getvalue(),
                       'zmin': str(zmin),
                       'zmax': str(zmax),
                       'p': str(p)})

    time.sleep(0.03)
sio.disconnect()