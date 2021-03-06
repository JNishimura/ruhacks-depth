import numpy as np
from record3d import Record3DStream
import cv2
from threading import Event

import socketio
import time
from PIL import Image

from io import BytesIO
import sys


class DepthStreamer:
    def __init__(self):
        self.event = Event()
        self.session = None
        self.sio = socketio.Client()
        self.sio.connect('http://localhost:3000')

        @self.sio.on('achooResponse')
        def on_response(data):
            print(data)

    def on_new_frame(self):
        """
        This method is called from non-main thread, therefore cannot be used for presenting UI.
        """
        self.event.set()  # Notify the main thread to stop waiting and process new frame.

    def on_stream_stopped(self):
        self.sio.disconnect()
        print('Stream stopped')
        quit()

    def connect_to_device(self, dev_idx):
        print('Searching for devices')
        devs = Record3DStream.get_connected_devices()
        print('{} device(s) found'.format(len(devs)))
        for dev in devs:
            print('\tID: {}\n\tUDID: {}\n'.format(dev.product_id, dev.udid))

        if len(devs) <= dev_idx:
            raise RuntimeError('Cannot connect to device #{}, try different index.'
                               .format(dev_idx))

        dev = devs[dev_idx]
        self.session = Record3DStream()
        self.session.on_new_frame = self.on_new_frame
        self.session.on_stream_stopped = self.on_stream_stopped
        self.session.connect(dev)  # Initiate connection and start capturing

    def start_processing_stream(self):
        while True:
            self.event.wait()  # Wait for new frame to arrive

            # Copy the newly arrived RGBD frame
            depth = self.session.get_depth_frame()
            rgb = self.session.get_rgb_frame()
            # You can now e.g. create point cloud by projecting the depth map using the intrinsic matrix.

            # Postprocess it
            are_truedepth_camera_data_being_streamed = depth.shape[0] == 640
            if are_truedepth_camera_data_being_streamed:
                depth = cv2.flip(depth, 1)
                rgb = cv2.flip(rgb, 1)

            rgb_saved = BytesIO()
            Image.fromarray(rgb, 'RGB').save(rgb_saved, format="png")
            rgb = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

            filled_depth = self.fillInDepthNan(depth)

            encoded = self.encodeMWD(filled_depth)
            encoded_saved = BytesIO()
            Image.fromarray(encoded, 'RGB').save(encoded_saved, format="png")

            NUM_STEPS = 2
            zmax = np.nanmax(depth)
            zmin = np.nanmin(depth)
            zrange = zmax - zmin
            p = zrange / NUM_STEPS

            self.sio.emit('achoo', {'encoded': encoded_saved.getvalue(),
                                    'texture': rgb_saved.getvalue(),
                                    'zmin': str(zmin),
                                    'zmax': str(zmax),
                                    'p': str(p)})

            # Show the RGBD Stream
            cv2.imshow('RGB', rgb)
            cv2.imshow('Depth', depth)
            cv2.waitKey(1)

            self.event.clear()
    
    def encodeMWD(self, depth):
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

    def fillInDepthNan(self, depth):
        mask = np.isnan(depth)
        idx = np.where(~mask,np.arange(mask.shape[1]),0)
        np.maximum.accumulate(idx,axis=1, out=idx)
        out = depth[np.arange(idx.shape[0])[:,None], idx]
        return out
    
if __name__ == '__main__':
    app = DepthStreamer()
    app.connect_to_device(dev_idx=0)
    app.start_processing_stream()