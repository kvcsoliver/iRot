import os
import sys
import customtkinter as ctk
from PIL import Image, ImageTk
import tkinter as tk
from tkinter import filedialog
import math
import pyautogui
import time

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")


def get_resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        # # Set the icon for the application
        # self.wm_iconbitmap('assets/icon.ico')

        icon_path = get_resource_path('icon.ico')
        # icon_image = tk.PhotoImage(file=icon_path)
        self.wm_iconbitmap(icon_path)

        # Set the icon for the application
        # self.wm_iconphoto(False, icon_image)

        # Configure window
        self.title("iRot")
        self.geometry(f"{1100}x{580}")
        self.my_font = ctk.CTkFont(family="Segoe UI", size=14)

        # Configure grid layout (2x1)
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=24)
        self.grid_rowconfigure(0, weight=1)

        # Create pic frame
        self.pic_frame = ctk.CTkFrame(self, corner_radius=10)
        self.pic_frame.grid(row=0, column=1, sticky="nsew", pady=10, padx=10)
        self.pic_frame.grid_columnconfigure(0, weight=1)
        self.pic_frame.grid_rowconfigure(0, weight=1)

        # Create canvas
        self.canvas = tk.Canvas(self.pic_frame, background='black', bd=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky='nsew')

        # Create buttons directly on the main window
        self.show_lines_button = ctk.CTkSwitch(self, text="Toggle Lines", command=self.toggle_lines, font=self.my_font)
        self.show_lines_button.grid(row=0, column=0, padx=5, pady=(15, 5), sticky="n")

        self.screenshot_button = ctk.CTkButton(self, text="Screenshot", command=self.screenshot, font=self.my_font)
        self.screenshot_button.grid(row=0, column=0, padx=5, pady=(55, 0), sticky="n")

        self.open_pictures_button = ctk.CTkButton(self, text="Open Pictures", command=self.prompt_select_files,
                                                  font=self.my_font)
        self.open_pictures_button.grid(row=0, column=0, padx=5, pady=110, sticky="n")

        # Create help text with a Text widget
        self.help_text = tk.Text(self, height=100, width=25, font=self.my_font, wrap='word', bg=self.cget('bg'), bd=0,
                                 padx=5, pady=5)

        # Define the text color using a tag
        self.help_text.tag_configure("colored", foreground="#FFFFFF")  # Set your desired color here

        # Insert text and apply the tag
        text_content = """
        Hotkeys:

        LMB drag:
        Rotate

        RMB, Space:
        Screenshot

        MMB:
        Toggle Lines

        Mouse Scroll, Arrows:
        Next/Previous

        CTRL + Mouse Scroll:
        Zoom
        """
        self.help_text.insert(tk.END, text_content, "colored")
        self.help_text.config(state=tk.DISABLED)  # Make the text widget read-only

        # Place the Text widget in the window
        self.help_text.grid(row=0, column=0, padx=5, pady=(165, 0), sticky="nw")

        # Initialize variables
        self.image_paths = []
        self.current_image_index = -1
        self.image_original = None
        self.image_rotated = None
        self.resized_tk = None

        # Rotation variables
        self.angle = 0
        self.start_angle = 0
        self.center_x = 0
        self.center_y = 0
        self.is_dragging = False

        # Line visibility
        self.show_lines = False

        # Zoom level
        self.zoom_level = 1.0
        self.zoom_factor = 1.1

        # Bind events
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        self.bind('<Left>', self.prev_image)
        self.bind('<Right>', self.next_image)
        self.bind('<space>', self.next_image)
        self.bind('<Button-3>', self.screenshot)
        self.bind('<Button-2>', self.mmb_lines)
        self.canvas.bind('<Button-1>', self.on_button_press)
        self.canvas.bind('<B1-Motion>', self.on_mouse_drag)
        self.canvas.bind('<ButtonRelease-1>', self.on_button_release)
        self.canvas.bind('<MouseWheel>', self.on_mouse_wheel)

    def mmb_lines(self, event=None):
        # Toggle the lines visibility
        self.toggle_lines()
        # Toggle the switch state
        if self.show_lines_button.get() == 1:
            self.show_lines_button.deselect()
        else:
            self.show_lines_button.select()

    def prompt_select_files(self):
        filetypes = (("Image files", "*.jpg *.jpeg *.png *.bmp *.gif"), ("All files", "*.*"))
        self.image_paths = filedialog.askopenfilenames(title="Select Images", filetypes=filetypes)
        if self.image_paths:
            self.current_image_index = 0
            self.load_image(self.current_image_index)

    def load_image(self, index):
        if 0 <= index < len(self.image_paths):
            try:
                self.image_original = Image.open(self.image_paths[index])
                self.angle = 0
                self.image_rotated = self.image_original
                if self.canvas.winfo_width() > 1 and self.canvas.winfo_height() > 1:
                    self.show_full_image(self.canvas.winfo_width(), self.canvas.winfo_height())
                else:
                    self.canvas.after(100, lambda: self.load_image(index))
            except Exception as e:
                print(f"Error loading image: {e}")

    def on_canvas_configure(self, event):
        if self.image_rotated:
            self.show_full_image(event.width, event.height)

    def show_full_image(self, width, height):
        if width <= 0 or height <= 0 or not self.image_rotated:
            return

        try:
            image_ratio = self.image_rotated.size[0] / self.image_rotated.size[1]
            canvas_ratio = width / height

            if canvas_ratio > image_ratio:
                new_width = int(height * image_ratio)
                new_height = height
            else:
                new_width = width
                new_height = int(width / image_ratio)

            # Apply zoom
            new_width = int(new_width * self.zoom_level)
            new_height = int(new_height * self.zoom_level)

            resized_image = self.image_rotated.resize((new_width, new_height), resample=Image.BICUBIC)
            self.resized_tk = ImageTk.PhotoImage(resized_image)

            self.canvas.delete(tk.ALL)

            self.canvas.create_image(width / 2, height / 2, anchor=tk.CENTER, image=self.resized_tk)
            if self.show_lines:
                self.draw_horizontal_lines(width, height)
        except Exception as e:
            print(f"Error displaying image: {e}")

    def draw_horizontal_lines(self, width, height):
        # Draw horizontal lines at intervals of 30 pixels
        line_spacing = 30
        self.canvas.delete("lines")
        for y in range(0, height, line_spacing):
            self.canvas.create_line(0, y, width, y, fill='#888888', width=1, tags="lines")

    def toggle_lines(self, event=None):
        self.show_lines = not self.show_lines
        if self.image_rotated:
            self.show_full_image(self.canvas.winfo_width(), self.canvas.winfo_height())

    def ensure_lines_visibility(self, state):
        if self.show_lines != state:
            self.toggle_lines()

    def screenshot(self, event=None):
        # Store the original state of line visibility
        original_show_lines = self.show_lines

        # Ensure lines are hidden
        self.ensure_lines_visibility(False)

        # Give some time for the canvas to update
        self.canvas.update()

        # Simulate Win + Shift + S to take a screenshot
        pyautogui.hotkey('win', 'shift', 's')

        # Give some time for the screenshot tool to open
        time.sleep(1)

        # Restore the original state of line visibility
        self.ensure_lines_visibility(original_show_lines)

    def prev_image(self, event=None):
        if self.image_paths and self.current_image_index > 0:
            self.current_image_index -= 1
            self.load_image(self.current_image_index)

    def next_image(self, event=None):
        if self.image_paths and self.current_image_index < len(self.image_paths) - 1:
            self.current_image_index += 1
            self.load_image(self.current_image_index)

    def on_mouse_wheel(self, event):
        if event.state & 0x4:  # Check if Ctrl key is pressed
            if event.delta > 0:
                self.zoom_level *= self.zoom_factor
            else:
                self.zoom_level /= self.zoom_factor

            # Clamp zoom level to avoid extreme values
            self.zoom_level = max(0.1, min(self.zoom_level, 10))

            self.show_full_image(self.canvas.winfo_width(), self.canvas.winfo_height())
        else:
            if event.delta > 0:
                self.prev_image()
            else:
                self.next_image()

    def on_button_press(self, event):
        self.center_x = self.canvas.winfo_width() / 2
        self.center_y = self.canvas.winfo_height() / 2
        self.start_angle = self.calculate_angle(event.x, event.y)
        self.is_dragging = True

    def on_mouse_drag(self, event):
        if self.is_dragging:
            current_angle = self.calculate_angle(event.x, event.y)
            angle_delta = current_angle - self.start_angle
            self.angle -= angle_delta
            self.start_angle = current_angle
            self.rotate_image(self.angle, high_quality=False)

    def on_button_release(self, event):
        if self.is_dragging:
            self.rotate_image(self.angle, high_quality=True)
            self.start_angle = 0
            self.is_dragging = False

    def calculate_angle(self, x, y):
        return math.degrees(math.atan2(y - self.center_y, x - self.center_x))

    def rotate_image(self, angle, high_quality):
        if self.image_original:
            try:
                resample_method = Image.BICUBIC if high_quality else Image.NEAREST
                self.image_rotated = self.image_original.rotate(angle, resample=resample_method, expand=True)
                self.show_full_image(self.canvas.winfo_width(), self.canvas.winfo_height())
            except Exception as e:
                print(f"Error rotating image: {e}")


if __name__ == "__main__":
    app = App()
    app.mainloop()
