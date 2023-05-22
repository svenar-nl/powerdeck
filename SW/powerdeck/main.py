#!/usr/bin/python

import tkinter as tk
from tkinter import simpledialog, messagebox
from tkinter.colorchooser import askcolor
import time
import threading
import serial
import serialHandler
import json
import os
import webbrowser
import pyautogui
import pystray
from pystray import MenuItem
from PIL import Image, ImageDraw

gui_thread = None
serial_thread = None
do_close = False
do_close_popup = False

window = None
canvas = None
popup_window = None
popup_window_color = "0:0:0"
serial_device = None
profile_list = None
systray_icon = None

last_button_pressed = -1

config = {
    "background": "#333333",
    "background_alt": "#444444",
    "foreground": "#FFFFFF",
    "foreground_alt": "#AAAAAA",
    "window": {"width": 750, "height": 480},
    "popup": {"width": 290, "height": 350},
}

data = {
    "currentprofile": "Default",
    "profiles": [
        {
            "name": "Default",
            "buttons": [],
        }
    ],
}

button_options = ["command", "website", "keyboard"]

buttons = {}


def load_data():
    global data

    if os.path.isfile("data.json"):
        with open("data.json", "r") as openfile:
            data = json.load(openfile)

    if not "profiles" in data:
        data["profiles"] = []

    if not "currentprofile" in data:
        data["currentprofile"] = "Default"


def save_data():
    global data

    json_object = json.dumps(data, indent=4)
    with open("data.json", "w") as outfile:
        outfile.write(json_object)


# def create_image(width, height, color1, color2):
#     # Generate an image and draw a pattern
#     image = Image.new("RGB", (width, height), color1)
#     dc = ImageDraw.Draw(image)
#     dc.rectangle((width // 2, 0, width, height // 2), fill=color2)
#     dc.rectangle((0, height // 2, width // 2, height), fill=color2)

#     return image

def hide_gui():
    global popup_window
    # if not messagebox.askokcancel("PowerDeck", "Do you want to quit?"):
    #     return
    if popup_window is not None:
        try:
            popup_window.destroy()
        except:
            pass
        popup_window = None
    # window.destroy()
    window.withdraw()

    if os.name.lower() != "nt":
        systray_icon.notify(title="PowerDeck", message="PowerDeck is running in the background.")
    else:
        messagebox.showinfo("PowerDeck", "PowerDeck is running in the background.")
    systray_icon.run()

def show_gui(icon, item):
    systray_icon.stop()
    setup_systray_icon()
    window.after(0, window.deiconify)

def quit_app(icon, item):
    systray_icon.stop()
    window.destroy()
    save_data()

def handle_gui():
    global do_close
    global window

    window = create_window()
    draw(window)
    window.protocol("WM_DELETE_WINDOW", hide_gui)
    window.mainloop()
    window = None

    # do_close = True


def update_colors():
    default_color = "0:0:0"
    profile_index = -1
    for profile in data["profiles"]:
        if data["currentprofile"] == profile["name"]:
            profile_index = data["profiles"].index(profile)
            break

    if profile_index < 0:
        return

    led_data = {}

    for i in range(13):
        button_id = -1
        try:
            for button_index in data["profiles"][profile_index]["buttons"]:
                if button_index["id"] == i:
                    button_id = data["profiles"][profile_index]["buttons"].index(
                        button_index
                    )
                    break
        except:
            pass

        if (
            button_id < 0
            or not "color" in data["profiles"][profile_index]["buttons"][button_id]
        ):
            led_data[i] = default_color
        else:
            led_data[i] = data["profiles"][profile_index]["buttons"][button_id]["color"]

    serialHandler.send_colors(led_data)

def parse_keyboard_actions(input):
    actions = [] # {type: "key", value: "enter"}, {type: "text", value: "hi"}
    current_action = {"type": "text", "value": ""}

    for char in input:
        if char == "<":
            if current_action["value"]:
                actions.append(current_action)
                current_action = {"type": "key", "value": ""}
        elif char == ">":
            actions.append(current_action)
            if ":" in current_action["value"]:
                current_action["type"] = "down" if current_action["value"].split(":")[0].lower() == "d" else "up"
                current_action["value"] = current_action["value"].split(":")[1]
            current_action = {"type": "text", "value": ""}
        else:
            current_action["value"] += char

    # Append the last action
    if current_action["value"]:
        if ":" in current_action["value"]:
            current_action["type"] = "down" if current_action["value"].split(":")[0].lower() == "d" else "up"
            current_action["value"] = current_action["value"].split(":")[1]
        actions.append(current_action)

    return actions


def handle_keypress(key_id):
    if key_id == 12:
        if len(data["currentprofile"]) == 0:
            data["currentprofile"] = profile_list.get(0)
        else:
            try:
                data["currentprofile"] = profile_list.get(
                    (profile_list.curselection()[0] + 1) % profile_list.size()
                )
            except:
                data["currentprofile"] = profile_list.get(0)
            profile_list.select_clear(0, tk.END)
            index = 0
            for profile in data["profiles"]:
                if data["currentprofile"] == profile["name"]:
                    profile_list.select_set(index)
                index += 1

        update_colors()
        return

    if len(data["currentprofile"]) == 0:
        return

    profile_id = -1
    index = 0
    for profile in data["profiles"]:
        if profile["name"] == data["currentprofile"]:
            profile_id = index
            break
        index += 1

    if profile_id < 0:
        return

    button_action = None
    for button in data["profiles"][profile_id]["buttons"]:
        if button["id"] == key_id:
            button_action = button

    if button_action is None:
        return

    if button_action["action"] == "command":
        os.system(button_action["value"])

    if button_action["action"] == "website":
        webbrowser.open(button_action["value"])

    if button_action["action"] == "keyboard":
        val = button_action["value"]
        action_list = parse_keyboard_actions(val)
        for action in action_list:
            if action["type"] == "key":
                pyautogui.press(action["value"])

            elif action["type"] == "down":
                pyautogui.keyDown(action["value"])

            elif action["type"] == "up":
                pyautogui.keyUp(action["value"])

            elif action["type"] == "text":
                pyautogui.write(action["value"])


def handle_serial():
    global do_close
    global window
    global serial_device
    global last_button_pressed
    global do_close_popup
    global popup_window

    while True:
        if do_close:
            break

        if serial_device is None:
            serial_device = serialHandler.find_macro_keyboard()
        else:
            if not serialHandler.device_exists(serial_device.device):
                serial_device = None

        if serialHandler.get_open_port() is not None:
            try:
                response = (
                    serialHandler.get_open_port()
                    .readline()
                    .decode(errors="ignore")
                    .strip()
                )
                if "K" in response.upper():
                    try:
                        last_button_pressed = int(response.upper().replace("K", ""))
                        handle_keypress(last_button_pressed)
                    except:
                        pass

                elif "C" in response.upper():
                    update_colors()

                else:
                    last_button_pressed = -1
            except serial.serialutil.SerialException:
                pass

        if window is not None and canvas is not None:
            try:
                last_current_profile = data["currentprofile"]
                data["currentprofile"] = profile_list.get(
                    (profile_list.curselection()[0]) % profile_list.size()
                )
                if last_current_profile != data["currentprofile"]:
                    update_colors()
            except:
                pass

            circle_pos = [260, 5]
            circle_size = 25
            canvas.create_oval(
                circle_pos[0],
                circle_pos[1],
                circle_pos[0] + circle_size,
                circle_pos[1] + circle_size,
                fill="#CC1010" if serial_device is None else "#10CC10",
            )

            _buttons = buttons.copy()
            for button in _buttons:
                try:
                    button_id = int(_buttons[button]) - 1
                    if button_id == last_button_pressed:
                        button.config(bg=config["foreground_alt"])
                        button.config(fg=config["background_alt"])
                    else:
                        button.config(bg=config["background_alt"])
                        button.config(fg=config["foreground_alt"])
                except:
                    pass

            if profile_list is not None:
                try:
                    data["currentprofile"] = profile_list.get(
                        profile_list.curselection()
                    )
                except:
                    pass

        if do_close_popup:
            do_close_popup = False
            if popup_window is not None:
                popup_window.destroy()
                popup_window = None
        if serial_device is None:
            time.sleep(1)


def create_window():
    window = tk.Tk()
    window.title("PowerDeck")
    window.resizable(False, False)
    window.configure(background=config["background"])

    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()

    x_cordinate = int((screen_width / 2) - (config["window"]["width"] / 2))
    y_cordinate = int((screen_height / 2) - (config["window"]["height"] / 2))

    window.geometry(
        "{}x{}+{}+{}".format(
            config["window"]["width"],
            config["window"]["height"],
            x_cordinate,
            y_cordinate,
        )
    )

    return window


def draw(window):
    global canvas
    global buttons
    global profile_list

    canvas = tk.Canvas(
        window, bg=config["background"], borderwidth=0, highlightthickness=0
    )

    canvas.create_line(
        250, 0, 250, config["window"]["height"], fill=config["foreground"]
    )
    canvas.create_line(
        255, 0, 255, config["window"]["height"], fill=config["foreground"]
    )
    canvas.create_line(0, 55, 250, 55, fill=config["foreground"])
    canvas.create_line(0, 58, 250, 58, fill=config["foreground"])
    canvas.create_line(50, 110, 200, 110, fill=config["foreground"])

    canvas.pack(fill=tk.BOTH, expand=1)

    labelTitle = tk.Label(
        window,
        text="PowerDeck",
        fg=config["foreground"],
        bg=config["background"],
        font=("Arial", 32),
    )
    labelTitle.place(x=10, y=0, anchor=tk.NW)

    labelProfiles = tk.Label(
        window,
        text="profiles",
        fg=config["foreground"],
        bg=config["background"],
        font=("Arial", 24),
    )
    labelProfiles.place(x=70, y=60, anchor=tk.NW)

    button_start_x = 280
    button_start_y = config["window"]["height"] - 330
    button_width = 100
    button_height = 100
    button_offset = 105
    button_count_x = 4
    button_count_y = 3
    for x in range(button_count_x):
        for y in range(button_count_y):
            button_id = x + y * button_count_x
            button = tk.Button(
                window,
                text=button_id + 1,
                bg=config["background_alt"],
                fg=config["foreground_alt"],
                highlightbackground=config["background"],
                highlightcolor=config["foreground"],
                cursor="hand1",
            )
            button.place(
                x=button_start_x + button_offset * x,
                y=button_start_y + button_offset * y,
                width=button_width,
                height=button_height,
                anchor=tk.NW,
            )
            buttons[button] = x + y * button_count_x + 1
            button.bind("<Button-1>", button_event)

    button = tk.Button(
        window,
        text="profile",
        bg=config["background_alt"],
        fg=config["foreground_alt"],
        highlightbackground=config["background"],
        highlightcolor=config["foreground"],
        cursor="hand1",
    )
    button.place(
        x=button_start_x + button_offset * (button_count_x - 1),
        y=button_start_y + button_offset * -1 - 10,
        width=button_width,
        height=button_height,
        anchor=tk.NW,
    )
    buttons[button] = button_count_x * button_count_y + 1
    button.bind("<Button-1>", button_event)

    button = tk.Button(
        window,
        text="+",
        bg="#007700",
        fg=config["foreground_alt"],
        highlightbackground=config["background"],
        highlightcolor=config["foreground"],
        cursor="hand1",
    )
    button.place(x=0, y=110, width=220, height=30, anchor=tk.NW)
    buttons[button] = "profile_add"
    button.bind("<Button-1>", button_event)

    button = tk.Button(
        window,
        text="-",
        bg="#770000",
        fg=config["foreground_alt"],
        highlightbackground=config["background"],
        highlightcolor=config["foreground"],
        cursor="hand1",
    )
    button.place(x=220, y=110, width=30, height=30, anchor=tk.NW)
    buttons[button] = "profile_del"
    button.bind("<Button-1>", button_event)

    profile_list = tk.Listbox(
        window,
        font=("Arial", 15),
        height=10,
        bg=config["background_alt"],
        width=34,
        fg=config["foreground"],
    )
    profile_list.place(
        x=0, y=150, width=250, height=config["window"]["height"] - 150, anchor=tk.NW
    )

    index = 0
    for profile in data["profiles"]:
        profile_list.insert(tk.END, profile["name"])
        if data["currentprofile"] == profile["name"]:
            profile_list.select_set(index)
        index += 1


def button_event(event):
    global do_close_popup

    id = str(buttons[event.widget])

    if id == "profile_add":
        profile_name = simpledialog.askstring(
            title="PowerDeck | Add profile", prompt="Enter a new profile name"
        )
        if profile_name is not None:
            data["profiles"].append({"name": profile_name, "buttons": []})
            data["currentprofile"] = profile_name

            profile_list.insert(tk.END, profile_name)
            profile_list.selection_clear(0, tk.END)
            profile_list.select_set(len(data["profiles"]) - 1)

    elif id == "profile_del":
        if profile_list is not None:
            if len(profile_list.curselection()) > 0:
                if data["currentprofile"] == profile_list.get(
                    profile_list.curselection()
                ):
                    data["currentprofile"] = ""
                for profile in data["profiles"]:
                    if profile["name"] == profile_list.get(profile_list.curselection()):
                        data["profiles"].remove(profile)
                        break
                profile_list.delete(profile_list.curselection())

    elif "button_" in id:
        if "save" in id:
            button_id = int(id.split("_")[2])
            action = ""
            value = ""

            for widget in popup_window.winfo_children():
                if widget.winfo_name().lower() == "!optionmenu":
                    action = widget.getvar(widget.cget("textvariable"))

                if widget.winfo_name().lower() == "input_value":
                    value = widget.get()

            if button_id != 12:
                profile_id = -1
                for profile in data["profiles"]:
                    if profile["name"] == data["currentprofile"]:
                        profile_id = data["profiles"].index(profile)
                        break

                if profile_id != -1:
                    target_button_id = -1
                    for button in data["profiles"][profile_id]["buttons"]:
                        if button["id"] == button_id:
                            target_button_id = data["profiles"][profile_id][
                                "buttons"
                            ].index(button)
                            break

                    if target_button_id != -1:
                        data["profiles"][profile_id]["buttons"][target_button_id][
                            "action"
                        ] = action
                        data["profiles"][profile_id]["buttons"][target_button_id][
                            "value"
                        ] = value
                        data["profiles"][profile_id]["buttons"][target_button_id][
                            "color"
                        ] = popup_window_color

                    else:
                        data["profiles"][profile_id]["buttons"].append(
                            {
                                "id": button_id,
                                "action": action,
                                "value": value,
                                "color": popup_window_color,
                            }
                        )
            else:
                profile_id = -1
                for profile in data["profiles"]:
                    if profile["name"] == data["currentprofile"]:
                        profile_id = data["profiles"].index(profile)
                        break
                
                target_button_id = -1
                for button in data["profiles"][profile_id]["buttons"]:
                    if button["id"] == 12:
                        target_button_id = data["profiles"][profile_id][
                            "buttons"
                        ].index(button)
                        break

                if target_button_id != -1:
                    data["profiles"][profile_id]["buttons"][target_button_id][
                        "color"
                    ] = popup_window_color

                else:
                    data["profiles"][profile_id]["buttons"].append({"id": 12, "color": popup_window_color})

        update_colors()
        if popup_window is not None:
            do_close_popup = True
    else:
        id = int(id) - 1
        show_window_edit_button(id)


def show_window_edit_button(id, new_color = None, new_action = None, new_value = None):
    global popup_window
    global popup_window_color

    if popup_window is not None:
        try:
            popup_window.destroy()
        except:
            pass

    popup_window = tk.Tk()
    popup_window.title(
        "PowerDeck | Edit " + ("button " + str(id + 1) if id != 12 else "Profile")
    )
    popup_window.resizable(False, False)
    popup_window.configure(background=config["background"])

    screen_width = popup_window.winfo_screenwidth()
    screen_height = popup_window.winfo_screenheight()

    x_cordinate = int((screen_width / 2) - (config["popup"]["width"] / 2))
    y_cordinate = int((screen_height / 2) - (config["popup"]["height"] / 2))

    popup_window.geometry(
        "{}x{}+{}+{}".format(
            config["popup"]["width"],
            config["popup"]["height"],
            x_cordinate,
            y_cordinate,
        )
    )

    popup_canvas = tk.Canvas(
        popup_window, bg=config["background"], borderwidth=0, highlightthickness=0
    )

    color_input = "0:0:0"
    try:
        for profile in data["profiles"]:
            if profile["name"] == data["currentprofile"]:
                for button in profile["buttons"]:
                    if button["id"] == id:
                        color_input = button["color"]
                        break
                break
    except:
        pass
    
    if new_color is not None:
        color_input = new_color

    red, green, blue = color_input.split(":")
    red_hex = format(int(red), "02X")
    green_hex = format(int(green), "02X")
    blue_hex = format(int(blue), "02X")
    color_output = "#" + red_hex + green_hex + blue_hex

    popup_window_color = color_input

    circle_pos = [80, 160]
    circle_size = 30
    if id == 12:
        circle_pos = [80, 0]
    popup_canvas.create_oval(
        circle_pos[0],
        circle_pos[1],
        circle_pos[0] + circle_size,
        circle_pos[1] + circle_size,
        fill=color_output,
    )

    popup_canvas.pack(fill=tk.BOTH, expand=1)

    if id != 12:
        action = ""
        value = ""
        try:
            for profile in data["profiles"]:
                if profile["name"] == data["currentprofile"]:
                    for button in profile["buttons"]:
                        if button["id"] == id:
                            action = button["action"]
                            value = button["value"]
                            break
                    break
        except:
            pass
        
        if new_action is not None:
            action = new_action

        if new_value is not None:
            value = new_value

        labelTitle = tk.Label(
            popup_window,
            text="Action",
            fg=config["foreground"],
            bg=config["background"],
            font=("Arial", 18),
        )
        labelTitle.place(x=10, y=0, anchor=tk.NW)

        default_dropdown_item = tk.StringVar(
            popup_window, button_options[0] if len(action) == 0 else action
        )
        dropdown = tk.OptionMenu(popup_window, default_dropdown_item, *button_options)
        dropdown.place(
            x=0, y=35, width=config["popup"]["width"], height=30, anchor=tk.NW
        )

        labelTarget = tk.Label(
            popup_window,
            text="Target",
            fg=config["foreground"],
            bg=config["background"],
            font=("Arial", 18),
        )
        labelTarget.place(x=10, y=80, anchor=tk.NW)

        entry = tk.Entry(popup_window, name="input_value")
        entry.place(x=0, y=115, width=config["popup"]["width"], height=30, anchor=tk.NW)
        entry.insert(0, value)

        labelColor = tk.Label(
            popup_window,
            text="Color",
            fg=config["foreground"],
            bg=config["background"],
            font=("Arial", 18),
        )
        labelColor.place(x=10, y=160, anchor=tk.NW)

        color_picker_button = tk.Button(
            popup_window,
            text="Select Color",
            command=popup_change_button_color
        )
        color_picker_button.place(x=130, y=160, width=100, height=30, anchor=tk.NW)

    else:
        labelColor = tk.Label(
            popup_window,
            text="Color",
            fg=config["foreground"],
            bg=config["background"],
            font=("Arial", 18),
        )
        labelColor.place(x=10, y=0, anchor=tk.NW)

        color_picker_button = tk.Button(
            popup_window,
            text="Select Color",
            command=popup_change_button_color
        )
        color_picker_button.place(x=130, y=0, width=100, height=30, anchor=tk.NW)

    button = tk.Button(
        popup_window,
        text="Save",
        bg="#007700",
        fg=config["foreground_alt"],
        highlightbackground=config["background"],
        highlightcolor=config["foreground"],
        cursor="hand1",
    )
    button.place(
        x=0,
        y=config["popup"]["height"] - 30,
        width=config["popup"]["width"] / 2,
        height=30,
        anchor=tk.NW,
    )
    buttons[button] = "button_save_" + str(id)
    button.bind("<Button-1>", button_event)

    button = tk.Button(
        popup_window,
        text="Cancel",
        bg="#000077",
        fg=config["foreground_alt"],
        highlightbackground=config["background"],
        highlightcolor=config["foreground"],
        cursor="hand1",
    )
    button.place(
        x=config["popup"]["width"] / 2,
        y=config["popup"]["height"] - 30,
        width=config["popup"]["width"] / 2,
        height=30,
        anchor=tk.NW,
    )
    buttons[button] = "button_cancel_" + str(id)
    button.bind("<Button-1>", button_event)

    popup_window.mainloop()

def popup_change_button_color():
    global popup_window_color

    try:
        popup_window_color = askcolor()
        if popup_window_color is not None and popup_window_color[0] is not None:
            red = int(popup_window_color[0][0])
            green = int(popup_window_color[0][1])
            blue = int(popup_window_color[0][2])

            if popup_window is not None:
                target_id = popup_window.title().split(" ")[-1]
                if target_id.lower() == "profile":
                    target_id = 13
                
                action = None
                value = None

                for widget in popup_window.winfo_children():
                    if widget.winfo_name().lower() == "!optionmenu":
                        action = widget.getvar(widget.cget("textvariable"))

                    if widget.winfo_name().lower() == "input_value":
                        value = widget.get()
                
                target_id = int(target_id) - 1
                show_window_edit_button(target_id, str(red) + ":" + str(green) + ":" + str(blue), action, value)
        else:
            if popup_window is not None:
                target_id = popup_window.title().split(" ")[-1]
                if target_id.lower() == "profile":
                    target_id = 13
                
                action = None
                value = None

                for widget in popup_window.winfo_children():
                    if widget.winfo_name().lower() == "!optionmenu":
                        action = widget.getvar(widget.cget("textvariable"))

                    if widget.winfo_name().lower() == "input_value":
                        value = widget.get()
                
                target_id = int(target_id) - 1
                show_window_edit_button(target_id, new_action=action, new_value=value)
    except:
        pass

def setup_systray_icon():
    global systray_icon

    menu=(MenuItem('Quit', quit_app), MenuItem('Show', show_gui))
    image=Image.open("favicon.ico")
    systray_icon = pystray.Icon(name="PowerDeck", icon=image, menu=menu)

if __name__ == "__main__":
    load_data()

    setup_systray_icon()

    serial_thread = threading.Thread(target=handle_serial)
    serial_thread.daemon = True
    serial_thread.start()

    handle_gui()
    save_data()
