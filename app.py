import csv
import numpy as np
import cv2
from cv2 import aruco
from controlstation import Printer, EDM, MouseControlApp
from transform import Helmert
from arena_api.system import system
from arena_api.buffer import BufferFactory
import time
import ctypes
import tkinter as tk
from tkinter import scrolledtext
from PIL import Image, ImageTk

class App:
    def __init__(self, master):
        self.data_y = [1024,988.25,962.25,941.75,926.75,915.75,908,899.75,894,888.5,888.5,884,880.5,877.75,873.75,871,869.25,
             866.5,865,863,861.25,859.75,859,857.5,855.5,855.25,853.25,852.5,851.25,850.75,849,848.5,848,847.5,830.5]
        
        self.data_dist = [0.9643,1.1884,1.4208,1.6667,1.918,2.1509,2.3877,2.6337,2.8796,3.1149,3.115,3.3526,3.5916,3.8396,4.0767,4.3259,4.5668,
             4.8044,5.0484,5.2957,5.5318,5.7694,6.0164,6.2626,6.5009,6.7531,7.2202,7.4646,7.7897,8.0302,8.4383,8.6779,8.9205,9.1663,20.7122]
        
        self.data_x = [1026,1019.25,1016.5,1015.25,1013.75,1013.5,1012,1011.25,1010.75,1010.5,1010.75,1010.75,
                        1009,1009.5,1009.5,1009.25,1009,1008.5,1008.75,1008.75,1008.5,1008,1007.5,1007.5,1007.5,1007.75,1008,1007,1007,1007.25,1006.75,1006.75,1007,1006.5,1003]

        self.master = master
        self.master.title("OpenTS - Tachymeter Control")

        # Create frames for better layout management
        self.left_frame = tk.Frame(master)
        self.left_frame.pack(side=tk.LEFT, padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.right_frame = tk.Frame(master)
        self.right_frame.pack(side=tk.RIGHT, padx=10, pady=10, fill=tk.BOTH, expand=True)

        # Left frame elements
        self.text_output = scrolledtext.ScrolledText(self.left_frame, width=50, height=20)
        self.text_output.pack(pady=5, fill=tk.BOTH, expand=True)

        self.move_buttons_frame = tk.Frame(self.left_frame)
        self.move_buttons_frame.pack(pady=5)

        # Joystick
        #self.joystick_frame = tk.Frame(self.left_frame)  # Frame for the joystick
        #self.joystick_frame.pack(pady=10)
        
        #self.joystick = VirtualJoystick(self.joystick_frame)  # Initialize the joystick

        self.capture_button = tk.Button(self.left_frame, text="Capture Data", command=self.capture_data)
        self.capture_button.pack(pady=5)

        self.display_button = tk.Button(self.left_frame, text="Display Corners", command=self.display_corners)
        self.display_button.pack(pady=5)

        self.laser_detection_button = tk.Button(self.left_frame, text="Marker Detection: OFF", command=self.toggle_laser_detection)
        self.laser_detection_button.pack(pady=5)
        
        self.loc_button = tk.Button(self.left_frame, text="Loc: 1", command=self.switch_loc)
        self.loc_button.pack(pady=5)
        
        # G-code input
        self.gcode_input_label = tk.Label(self.left_frame, text="G-code Command:")
        self.gcode_input_label.pack(pady=5)
        self.gcode_input = tk.Entry(self.left_frame, width=40)
        self.gcode_input.pack(pady=5)
        self.send_gcode_button = tk.Button(self.left_frame, text="Send G-code", command=self.send_gcode_command)
        self.send_gcode_button.pack(pady=5)

        self.quit_button = tk.Button(self.left_frame, text="Quit", command=self.quit)
        self.quit_button.pack(pady=5)

        # Right frame elements
        self.canvas = tk.Label(self.right_frame)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.printer = Printer("/dev/ttyUSB0", 250000)
        self.edm = EDM("/dev/ttyUSB1", 19200)

        # Initialize printer and EDM devices
        self.initialize_devices()

        # Set up camera and ArUco detector
        self.devices = self.create_devices_with_tries()
        self.device = system.select_device(self.devices)
        self.num_channels = self.setup(self.device)
        self.dictionary = aruco.getPredefinedDictionary(cv2.aruco.DICT_4X4_100)
        self.parameters = aruco.DetectorParameters()
        self.detector = aruco.ArucoDetector(self.dictionary, self.parameters)

        self.corners = None  # Initialize variable to store corners
        self.marker_coords = None
        
        self.marker_detection_enabled = False  # Laser detection state variable
        self.loc_position = True
        # Start the stream
        self.device.start_stream()

        # Start video loop
        self.master.after(100, self.video_loop)
        
        
        # Bind WASD and space key events
        self.master.bind('<w>', lambda event: self.move('up'))
        self.master.bind('<a>', lambda event: self.move('left'))
        self.master.bind('<s>', lambda event: self.move('down'))
        self.master.bind('<d>', lambda event: self.move('right'))
        self.master.bind('<r>', lambda event: self.capture_data())
        self.master.bind('<t>', lambda event: self.toggle_laser_detection())

    def create_move_button(self, frame, text, row, column, direction):
        button = tk.Button(frame, text=text, command=lambda: self.move(direction))
        button.grid(row=row, column=column, padx=5, pady=5)

    def initialize_devices(self):
        if self.printer.connect():
            self.text_output.insert(tk.END, "Connected to the printer.\n")
        else:
            self.text_output.insert(tk.END, "No Connection to printer\n")

        if self.edm.connect():
            self.text_output.insert(tk.END, "Connected to the EDM.\n")
        else:
            self.text_output.insert(tk.END, "No Connection to EDM\n")

    def create_devices_with_tries(self):
        tries = 0
        tries_max = 6
        sleep_time_secs = 10
        while tries < tries_max:
            devices = system.create_device()
            if not devices:
                self.text_output.insert(
                    tk.END,
                    f'Try {tries + 1} of {tries_max}: waiting for {sleep_time_secs} secs for a device to be connected!\n')
                for sec_count in range(sleep_time_secs):
                    time.sleep(1)
                    self.text_output.insert(tk.END, f'{sec_count + 1} seconds passed {"." * sec_count}\r')
                tries += 1
            else:
                self.text_output.insert(tk.END, f'Created {len(devices)} device(s)\n')
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

    def detect_laser(self, image, brightness_threshold=114, radius=11):
        blur = cv2.GaussianBlur(image, (radius, radius), 0)
        _, maxVal, _, maxLoc = cv2.minMaxLoc(blur)
        if maxVal > brightness_threshold:
            return maxLoc
        return None

    def move(self, direction):
        if direction == 'up':
            self.printer.send_command('G0 Y0.01')
        elif direction == 'left':
            self.printer.send_command('G0 X-0.01')
        elif direction == 'down':
            self.printer.send_command('G0 Y-0.01')
        elif direction == 'right':
            self.printer.send_command('G0 X0.01')
        self.text_output.insert(tk.END, f"Sent move command: {direction}\n")

    def capture_data(self):
        if self.printer and self.edm:
            current_position = self.printer.capture_position()
            current_distance = self.edm.capture_distance()
            #current_corners = self.get_corners_data()  # Get detected corners data
            self.text_output.insert(tk.END, f"Position: {current_position}\n")
            self.text_output.insert(tk.END, f"Distance: {current_distance}\n")
            #self.text_output.insert(tk.END, f"Corners: {current_corners}\n")
            self.save_to_csv( current_position, current_distance)

    def get_corners_data(self):
        if self.corners is not None:
            markers_coords_data = []
            for marker_coord in self.marker_coords:
                markers_coords_data.append(marker_coord)
            return markers_coords_data
        return []

    def save_to_csv(self, position, distance):
        timestr = time.strftime("%Y%m%d")
        with open(f"data_{timestr}.csv", mode="a", newline="") as file:
            writer = csv.writer(file)
            writer.writerow([position, distance])
            self.text_output.insert(tk.END, "Data saved to CSV file.\n")
            
    def display_corners(self):
        if self.corners is not None:
            self.text_output.insert(tk.END, "Detected Corners:\n")
            for i, corner in enumerate(self.corners):
                self.marker_coords = corner[0][0]
                x_sum = corner[0][0][0] + corner[0][1][0] + corner[0][2][0] + corner[0][3][0]
                y_sum = corner[0][0][1] + corner[0][1][1] + corner[0][2][1] + corner[0][3][1]
                center_coords = (x_sum * 0.25, y_sum * 0.25)
                self.text_output.insert(tk.END, f"Corner {i+1}: {center_coords}\n")
        else:
            self.text_output.insert(tk.END, "No corners detected.\n")

    def toggle_laser_detection(self):
        self.marker_detection_enabled = not self.marker_detection_enabled
        state = "ON" if self.marker_detection_enabled else "OFF"
        self.laser_detection_button.config(text=f"Marker Detection: {state}")
        self.text_output.insert(tk.END, f"Marker detection turned {state}.\n")
        
    def switch_loc(self):
        self.loc_position = not self.loc_position
        state = 1 if self.loc_position else 2
        self.loc_button.config(text=f"Loc: {state}")
        self.text_output.insert(tk.END, f"Loc state switched to {state}.\n")
    
    def calc_offset(self, distance):
        if distance is not None:
            offset_y = np.interp(distance, self.data_dist, self.data_y)
            offset_x = np.interp(distance, self.data_dist, self.data_x)
            return offset_x, offset_y
        return None

    def send_gcode_command(self):
        gcode_command = self.gcode_input.get()
        if gcode_command:
            self.printer.send_command(gcode_command)
            self.text_output.insert(tk.END, f"Sent G-code command: {gcode_command}\n")

    def quit(self):
        # Stop the stream before quitting
        self.device.stop_stream()
        self.master.quit()

   

    def video_loop(self):
        buffer = self.device.get_buffer()
        item = BufferFactory.copy(buffer)
        self.device.requeue_buffer(buffer)
        buffer_bytes_per_pixel = int(len(item.data) / (item.width * item.height))
        array = (ctypes.c_ubyte * self.num_channels * item.width * item.height).from_address(ctypes.addressof(item.pbytes))
        frame = np.ndarray(buffer=array, dtype=np.uint8, shape=(item.height, item.width))
        self.corners, ids, _ = self.detector.detectMarkers(frame)
        frame_markers = aruco.drawDetectedMarkers(frame.copy(), self.corners, ids)

        height, width = frame.shape
        
        # Implement target detection and laser control if enabled
        if self.marker_detection_enabled and ids is not None:
            for i, corner in enumerate(self.corners):
                # Calculate marker properties and ROI
                marker_id = ids[i][0]
                x_sum = self.corners[0][0][0][0] + self.corners[0][0][1][0] + self.corners[0][0][2][0] + self.corners[0][0][3][0]
                y_sum = self.corners[0][0][0][1] + self.corners[0][0][1][1] + self.corners[0][0][2][1] + self.corners[0][0][3][1]
                self.marker_coords = (x_sum * 0.25, y_sum * 0.25)

                
                offset_x, offset_y = -18, 120
                center_x, center_y = width // 2 + offset_x, height // 2 + offset_y
                
                
                roi_x, roi_y = 100, 140
                x1, y1 = max(center_x - roi_x, 0), max(center_y - roi_y, 0)
                x2, y2 = min(center_x + roi_x, width), min(center_y + roi_y, height)
                
                if x1 <= self.marker_coords[0] <= x2 and y1 <= self.marker_coords[1] <= y2:
                    distance = self.edm.capture_distance()
                    center_x_fine, center_y_fine = self.calc_offset(distance)
                    #print(f"Center_y: {center_y_fine}")
                    dist_x, dist_y = center_x_fine - self.marker_coords[0], center_y_fine - self.marker_coords[1]
                    
                else:
                    dist_x, dist_y = center_x - self.marker_coords[0], center_y - self.marker_coords[1]
                
                # # Define ROI
                # roi_x, roi_y = 100, 140
                # x1, y1 = max(center_x - roi_x, 0), max(center_y - roi_y, 0)
                # x2, y2 = min(center_x + roi_x, width), min(center_y + roi_y, height)
                # roi_laser = frame[y1:y2, x1:x2]
                
                # roi_a, roi_b = 70, 120
                # a1, b1 = max(center_x - roi_a, 0), max(center_y - roi_b, 0)
                # a2, b2 = min(center_x + roi_a, width), min(center_y + roi_b, height)
                
                # cv2.rectangle(frame_markers, (a1, b1), (a2, b2), (255, 0, 0), 2)
                
                # if a1 <= self.marker_coords[0] <= a2 and b1 <= self.marker_coords[1] <= b2:
                #     brightest_spot = self.detect_laser(roi_laser)
                    
                #     if brightest_spot:
                #         brightest_spot_x = x1 + brightest_spot[0]
                #         brightest_spot_y = y1 + brightest_spot[1]
                #         cv2.circle(frame_markers, (brightest_spot_x, brightest_spot_y), 7, (0, 255, 0), 2)
                #         text = f"Laserspot, Coords: ({int(brightest_spot_x)}, {int(brightest_spot_y)})"
                #         cv2.putText(frame_markers, text, (10, 90 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                        
                #         dist_x = brightest_spot_x - self.marker_coords[0]
                #         dist_y = brightest_spot_y - self.marker_coords[1]
                #         text_distance = f"Distance, Coords: ({int(dist_x)}, {int(dist_y)})"
                #     else:
                #         dist_x, dist_y = center_x - self.marker_coords[0], center_y - self.marker_coords[1]
                # else:
                #     dist_x, dist_y = center_x - self.marker_coords[0], center_y - self.marker_coords[1]
                    
                #dist_x, dist_y = center_x - self.marker_coords[0], center_y - self.marker_coords[1]
                #text_distance = f"Distance, Coords: ({int(dist_x)}, {int(dist_y)})"
                #cv2.putText(frame_markers, move_command, (10, 60 + i * 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2, cv2.LINE_AA)
                print(f"Loc: {self.loc_position}")
                if self.loc_position:
                    Kp_x = -0.01
                else:
                    Kp_x = 0.01
                    
                print(f"Kp_x: {Kp_x}") 
                Kp_y = 0.01
                #print(f"Dist: {dist_x,dist_y}")
                if abs(dist_x) > 1  or abs(dist_y) > 1:
                    move_x = f"{round((Kp_x * dist_x), 2):06.2f}"
                    move_y = f"{round((Kp_y * dist_y), 2):06.2f}"
                    move_command = f"G1 X{move_x} Y{move_y} F5000"
                    self.printer.send_command(move_command)

        # Convert the OpenCV frame to an image format compatible with tkinter
        #cv2.imshow("Frame", frame_markers)
        frame_markers = cv2.resize(frame_markers, (1024, 750))
        frame_rgb = cv2.cvtColor(frame_markers, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        imgtk = ImageTk.PhotoImage(image=img)
        
        # Update the tkinter label with the new image
        self.canvas.config(image=imgtk)
        self.canvas.image = imgtk

        BufferFactory.destroy(item)
        self.master.after(100, self.video_loop)

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()