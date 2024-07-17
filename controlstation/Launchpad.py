# -*- coding: utf-8 -*-
"""
Created on Tue Jul 16 21:46:24 2024

@author: Paul
"""

import tkinter as tk
from PIL import Image, ImageTk
import cv2
import sys
from arena_api.system import system
from arena_api.buffer import BufferFactory
import numpy as np
import time
import ctypes
import serial

class MouseControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("OpenTachy - Control")

        # Screen dimensions
        self.WIDTH, self.HEIGHT = 1024, 750
        
        self.ser = serial.Serial("/dev/ttyUSB0", 250000)

        # Create main frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create the canvas
        self.canvas = tk.Canvas(self.main_frame, width=self.WIDTH, height=self.HEIGHT)
        self.canvas.pack(side=tk.RIGHT)

        # Create sidebar
        self.sidebar = tk.Frame(self.main_frame, width=200, bg="gray")
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)

        # Sidebar labels
        self.position_label = tk.Label(self.sidebar, text="Position:", bg="gray", font=("Helvetica", 16))
        self.position_label.pack(pady=10)

        self.x_label = tk.Label(self.sidebar, text="X: 0", bg="gray", font=("Helvetica", 14))
        self.x_label.pack(pady=5)

        self.y_label = tk.Label(self.sidebar, text="Y: 0", bg="gray", font=("Helvetica", 14))
        self.y_label.pack(pady=5)

        # Initial values of x and y
        self.x, self.y = 0, 0
        self.center_x, self.center_y = 0, 0
        self.mouse_x, self.mouse_y = self.WIDTH / 2, self.HEIGHT / 2
        self.mouse_down = False

        # Bind events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Motion>", self.on_mouse_move)

        self.devices = self.create_devices_with_tries()
        self.device = system.select_device(self.devices)
        self.num_channels = self.setup(self.device)
        self.device.start_stream()

        # Start the drawing loop
        self.draw()

    def create_devices_with_tries(self):
        tries = 0
        tries_max = 6
        sleep_time_secs = 10
        while tries < tries_max:
            devices = system.create_device()
            if not devices:
                print(f'Try {tries + 1} of {tries_max}: waiting for {sleep_time_secs} secs for a device to be connected!\n')
                for sec_count in range(sleep_time_secs):
                    time.sleep(1)
                    print(f'{sec_count + 1} seconds passed {"." * sec_count}\r')
                tries += 1
            else:
                print(f'Created device\n')
                return devices
        else:
            raise Exception(f'No device found! Please connect a device and run the example again.')

    def setup(self, device):
        nodemap = device.nodemap
        nodes = nodemap.get_node(['PixelFormat'])
        nodes['PixelFormat'].value = 'Mono8'
        tl_stream_nodemap = device.tl_stream_nodemap
        nodemap.get_node('DecimationHorizontal').value = 2
        nodemap.get_node('DecimationVertical').value = 2
        nodemap.get_node('AcquisitionFrameRateEnable').value = True
        nodemap.get_node('AcquisitionFrameRate').value = 15.0
        nodemap.get_node("AcquisitionMode").value = "Continuous"
        nodemap.get_node('ExposureAuto').value = "Once"
        nodemap.get_node('Gain').value = 10.0
        tl_stream_nodemap["StreamBufferHandlingMode"].value = "NewestOnly"
        tl_stream_nodemap['StreamAutoNegotiatePacketSize'].value = True
        tl_stream_nodemap['StreamPacketResendEnable'].value = True
        num_channels = 1
        return num_channels

    def on_mouse_down(self, event):
        self.mouse_x, self.mouse_y = event.x, event.y
        self.mouse_down = True

    def on_mouse_up(self, event):
        if event.num == 1:  # Left mouse button release
            self.center_x, self.center_y = self.x, -self.y
            self.mouse_x, self.mouse_y = self.WIDTH / 2, self.HEIGHT / 2  # Reset to center
            print("New center set to:", self.center_x, self.center_y)
            self.mouse_down = False

    def on_mouse_move(self, event):
        if self.mouse_down:
            self.mouse_x, self.mouse_y = event.x, event.y

    def update_position(self):
        if self.mouse_down:
            off_x, off_y = self.mouse_x - self.WIDTH / 2, self.mouse_y - self.HEIGHT / 2
            off_x_scaled, off_y_scaled = off_x / 10, off_y / 5
            self.x = max(-50, min(off_x_scaled, 50)) + self.center_x
            self.y = max(-50, min(off_y_scaled, 50)) + self.center_y

            self.y = -self.y
            orden = f"G1 X{self.x} Y{self.y} F3600\r\n"
            print(orden)
            self.ser.write(str.encode(orden))

            # Update sidebar labels
            self.x_label.config(text=f"X: {round(self.x,3)}")
            self.y_label.config(text=f"Y: {round(self.y,3)}")

    def draw(self):
        self.canvas.delete("all")
        buffer = self.device.get_buffer()
        item = BufferFactory.copy(buffer)
        self.device.requeue_buffer(buffer)
        buffer_bytes_per_pixel = int(len(item.data) / (item.width * item.height))
        array = (ctypes.c_ubyte * self.num_channels * item.width * item.height).from_address(ctypes.addressof(item.pbytes))
        frame = np.ndarray(buffer=array, dtype=np.uint8, shape=(item.height, item.width))
        # Capture frame-by-frame
        img = cv2.resize(frame, (self.WIDTH, self.HEIGHT))
        img = Image.fromarray(img)
        imgtk = ImageTk.PhotoImage(image=img)

        # Add the image to the canvas
        self.canvas.create_image(0, 0, anchor=tk.NW, image=imgtk)
        self.canvas.image = imgtk

        # Draw a crosshair in the middle of the screen
        self.canvas.create_line(self.WIDTH // 2 - 20, self.HEIGHT // 2, self.WIDTH // 2 + 20, self.HEIGHT // 2, fill="red", width=2)
        self.canvas.create_line(self.WIDTH // 2, self.HEIGHT // 2 - 20, self.WIDTH // 2, self.HEIGHT // 2 + 20, fill="red", width=2)
        
        # Draw a circle at the current (mouse_x, mouse_y) position
        self.canvas.create_oval(self.mouse_x - 5, self.mouse_y - 5, self.mouse_x + 5, self.mouse_y + 5, fill="green")

        # Update position if mouse is down
        self.update_position()
        BufferFactory.destroy(item)
        self.root.after(20, self.draw)

    def on_closing(self):
        orden = f"G1 X0 Y0 F3600\r\n"
        print(orden)
        self.ser.write(str.encode(orden))
        self.device.stop_stream()
        system.destroy_device()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = MouseControlApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()
    sys.exit()
