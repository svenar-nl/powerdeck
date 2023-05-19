import serial
import serial.tools.list_ports

MACRO_VID = 0x1A86
MACRO_PID = 0x7523

open_port = None


def find_macro_keyboard():
    global open_port

    ports = serial.tools.list_ports.comports()

    for port in ports:
        if port.vid == MACRO_VID and port.pid == MACRO_PID:
            try:
                ser = serial.Serial(
                    port.device, 115200, timeout=1, rtscts=True, dsrdtr=True
                )
                ser.write(b"V")
                response = ser.readline().decode(errors="ignore").strip()
                if "macrokeyboard" in response.lower():
                    ser.timeout = 0
                    open_port = ser
                    return port

                ser.close()

            except serial.SerialException:
                pass

    return None


def device_exists(device):
    ports = serial.tools.list_ports.comports()

    for port in ports:
        if port.device == device:
            return True

    return False


def get_open_port():
    global open_port
    return open_port

def send_colors(data):
    if get_open_port() is None:
        return
    
    cmd = "L"
    for index in data:
        # Split the input string by colons
        red, green, blue = data[index].split(":")

        # Convert each color component to hexadecimal format
        red_hex = format(int(red), "02X")
        green_hex = format(int(green), "02X")
        blue_hex = format(int(blue), "02X")

        # Create the output string
        color_output = f"{red_hex}:{green_hex}:{blue_hex}"
        cmd += str(index) + ":" + color_output + ";"
    
    open_port.timeout = 1
    open_port.write(cmd.encode())
    open_port.flush()
    response = open_port.readline().decode(errors="ignore").strip()
    open_port.timeout = 0

    return response.upper() == "OK"

# def send_color(id, color):
#     if get_open_port() is None:
#         return
    
#     cmd = "L" + str(id) + ":" + color
#     open_port.timeout = 1
#     open_port.write(cmd.encode())
#     open_port.flush()
    
#     print(cmd + ": " + open_port.readline().decode(errors="ignore").strip())
#     open_port.timeout = 0