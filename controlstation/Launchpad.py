# -*- coding: utf-8 -*-
"""
Created on Tue Jul 16 21:46:24 2024

@author: Paul
"""

import tkinter as tk
import sys

class MouseControlApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Mouse Control")

        # Screen dimensions
        self.WIDTH, self.HEIGHT = 1000, 500

        # Create the canvas
        self.canvas = tk.Canvas(self.root, width=self.WIDTH, height=self.HEIGHT, bg="black")
        self.canvas.pack()

        # Initial values of x and y
        self.x, self.y = 0, 0
        self.center_x, self.center_y = 0, 0
        self.mouse_x, self.mouse_y = self.WIDTH / 2, self.HEIGHT / 2
        self.mouse_down = False

        # Bind events
        self.canvas.bind("<ButtonPress-1>", self.on_mouse_down)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)
        self.canvas.bind("<Motion>", self.on_mouse_move)

        # Start the drawing loop
        self.draw()

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
            off_x_scaled, off_y_scaled = off_x / 20, off_y / 10
            self.x = max(-30, min(off_x_scaled, 30)) + self.center_x
            self.y = max(-30, min(off_y_scaled, 30)) + self.center_y

            self.y = -self.y
            orden = f"G1 X{self.x} Y{self.y} F3600\r\n"
            print(orden)
            # ser.write(str.encode(orden))

    def draw(self):
        self.canvas.delete("all")
        
        # Draw a crosshair in the middle of the screen
        self.canvas.create_line(self.WIDTH // 2 - 20, self.HEIGHT // 2, self.WIDTH // 2 + 20, self.HEIGHT // 2, fill="red", width=2)
        self.canvas.create_line(self.WIDTH // 2, self.HEIGHT // 2 - 20, self.WIDTH // 2, self.HEIGHT // 2 + 20, fill="red", width=2)
        
        # Draw a circle at the current (mouse_x, mouse_y) position
        self.canvas.create_oval(self.mouse_x - 5, self.mouse_y - 5, self.mouse_x + 5, self.mouse_y + 5, fill="green")

        # Update position if mouse is down
        self.update_position()

        self.root.after(20, self.draw)

if __name__ == "__main__":
    root = tk.Tk()
    app = MouseControlApp(root)
    root.mainloop()
    sys.exit()
