import socketio
import time

sio = socketio.Client()
data = []

for i in range(10):
    sio.connect('http://localhost:3000')
    time.sleep(1)

    data.append(i)
    sio.emit('achoo', {'message': data})
    time.sleep(1)

    sio.disconnect()
    time.sleep(1)