#!/usr/bin/python

import tkinter as tk

config = {
    "background": "#333333",
    "background_alt": "#444444",
    "foreground": "#FFFFFF",
    "foreground_alt": "#AAAAAA",
    "window": {"width": 750, "height": 480},
}

buttons = {}

def create_window():
    window = tk.Tk()
    window.title("PowerDeck")
    window.geometry(f'{config["window"]["width"]}x{config["window"]["height"]}')
    window.resizable(False, False)
    window.configure(background=config["background"])
    return window


def draw(window):
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
            button = tk.Button(
                window,
                text=x + y * button_count_x + 1,
                bg=config["background_alt"],
                fg=config["foreground_alt"],
                highlightbackground=config["background"],
                highlightcolor=config["foreground"],
            )
            button.place(x=button_start_x + button_offset * x, y=button_start_y + button_offset * y, width=button_width, height=button_height, anchor=tk.NW)
            buttons[button] = x + y * button_count_x + 1
            button.bind("<Button-1>", button_event)
    
    button = tk.Button(
        window,
        text="profile",
        bg=config["background_alt"],
        fg=config["foreground_alt"],
        highlightbackground=config["background"],
        highlightcolor=config["foreground"],
    )
    button.place(x=button_start_x + button_offset * (button_count_x - 1), y=button_start_y + button_offset * -1 - 10, width=button_width, height=button_height, anchor=tk.NW)
    buttons[button] = button_count_x * button_count_y + 1
    button.bind("<Button-1>", button_event)
    
    button = tk.Button(
        window,
        text="+",
        bg="#007700",
        fg=config["foreground_alt"],
        highlightbackground=config["background"],
        highlightcolor=config["foreground"],
    )
    button.place(x=0, y=110, width=250, height=30, anchor=tk.NW)
    buttons[button] = "profile_add"
    button.bind("<Button-1>", button_event)

def button_event(event):
    print(buttons[event.widget])

if __name__ == "__main__":
    window = create_window()
    draw(window)
    window.mainloop()
