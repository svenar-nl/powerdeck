#include <Arduino.h>
#include <FastLED.h>

#define NAME "MacroKeyboard"
#define VERSION "v1.0"

#define KX0 32
#define KX1 33
#define KX2 12
#define KX3 13
#define KY0 25
#define KY1 26
#define KY2 27
#define KP1 14

#define BTNDEBOUNCE     150
#define LEDREQUESTTIME  5000 

#define NUM_LEDS_KEYS 12
#define NUM_LEDS_PROFILE 1
#define LED_TYPE SK6812
#define COLOR_ORDER GRB
#define DATA_PIN_KEYS 23
#define DATA_PIN_PROFILE 22

CRGB leds_keys[NUM_LEDS_KEYS];
CRGB leds_profile[NUM_LEDS_PROFILE];
CRGB startupColors[4] = {CRGB::Red, CRGB::Green, CRGB::Blue, CRGB::Black};
CRGB keyColors[13] = {CRGB::Black, CRGB::Black, CRGB::Black, CRGB::Black, CRGB::Black, CRGB::Black, CRGB::Black, CRGB::Black, CRGB::Black, CRGB::Black, CRGB::Black, CRGB::Black, CRGB::Black};

bool anyButtonPressed = false;
ulong ledRequestMillis = 0L;

void handleSerial(void);
void updateLeds(void);
void handleButtonInput(void);
void checkKeypad(uint8_t *pressedKeys);
void nblendU8TowardU8(uint8_t& cur, const uint8_t target, uint8_t amount);
CRGB fadeTowardColor(CRGB& cur, const CRGB& target, uint8_t amount);

/// @brief Initialize the MCU
/// @param None
/// @return None
void setup() {
    Serial.begin(115200);
    while (!Serial)
        ;
    Serial.println(String(NAME) + " " + String(VERSION));

    pinMode(KX0, INPUT_PULLDOWN);
    pinMode(KX1, INPUT_PULLDOWN);
    pinMode(KX2, INPUT_PULLDOWN);
    pinMode(KX3, INPUT_PULLDOWN);
    pinMode(KY0, INPUT_PULLDOWN);
    pinMode(KY1, INPUT_PULLDOWN);
    pinMode(KY2, INPUT_PULLDOWN);
    pinMode(KP1, INPUT_PULLDOWN);

    FastLED.addLeds<LED_TYPE, DATA_PIN_KEYS, COLOR_ORDER>(leds_keys, NUM_LEDS_KEYS).setCorrection(TypicalLEDStrip);
    FastLED.addLeds<LED_TYPE, DATA_PIN_PROFILE, COLOR_ORDER>(leds_profile, NUM_LEDS_PROFILE).setCorrection(TypicalLEDStrip);

    for (int i = 0; i < 4; i++) {
        for (int j = 0; j < NUM_LEDS_KEYS; j++) {
            leds_keys[j] = startupColors[i];
        }
        leds_profile[0] = startupColors[i];
        FastLED.show();
        delay(150);
    }
}

/// @brief Main loop
/// @param None
/// @return None
void loop() {
    handleSerial();
    updateLeds();
    handleButtonInput();
}

/// @brief Checks the keypad for a button press
/// @param None
/// @return None
void handleSerial(void) {
    if (millis() - ledRequestMillis > LEDREQUESTTIME) {
        ledRequestMillis = millis();
        Serial.println("C");
    }

    if (Serial.available()) {
        String input = Serial.readStringUntil('\0');
        input.toUpperCase();

        if (input == "R") {
            Serial.println("OK");
            ESP.restart();
        }

        if (input == "V") {
            Serial.println(String(NAME) + " " + String(VERSION));
            ledRequestMillis = millis() - LEDREQUESTTIME / 2;
        }

        if (input.startsWith("L")) {
            ledRequestMillis = millis();
            // L0:FFFFFF;1:FFFFFF;2:FFFFFF;3:FFFFFF;4:FFFFFF;5:FFFFFF;6:FFFFFF;7:FFFFFF;8:FFFFFF;9:FFFFFF;10:FFFFFF;11:FFFFFF;12:FFFFFF
            bool hasError = false;
            int startIndex = 1;  // Start at index 1 to skip the 'L' character

            if (!input.endsWith(";")) {
                input += ";";  // Append a semicolon to the end of the string if it doesn't already have one
            }

            while (startIndex < input.length()) {
                int colonIndex = input.indexOf(':', startIndex);
                int semicolonIndex = input.indexOf(';', colonIndex);
                if (colonIndex == -1 || semicolonIndex == -1) {
                    break;  // Exit the loop if either index is not found
                }

                int ledIndex = input.substring(startIndex, colonIndex).toInt();
                String colorHex = input.substring(colonIndex + 1, semicolonIndex);

                Serial.print(ledIndex);
                Serial.print(" > ");
                Serial.print(colorHex);

                uint8_t red = strtol(colorHex.substring(0, 2).c_str(), 0, 16);
                uint8_t green = strtol(colorHex.substring(3, 5).c_str(), 0, 16);
                uint8_t blue = strtol(colorHex.substring(6, 8).c_str(), 0, 16);

                startIndex = semicolonIndex + 1;  // Move the start index to the next segment

                if (ledIndex >= 0 && ledIndex < NUM_LEDS_KEYS + 1) {
                    keyColors[ledIndex] = CRGB(red, green, blue);
                } else if (ledIndex == 13) {
                    leds_profile[0] = CRGB(red, green, blue);
                } else {
                    hasError = true;
                }
            }

            if (!hasError) {
                Serial.println("OK");
            } else {
                Serial.println("ERR");
            }
        }
    }
}

/// @brief Handle LED animations
/// @param None
/// @return None
void updateLeds(void) {
    EVERY_N_MILLISECONDS(20) {
        for (int i = 0; i < NUM_LEDS_KEYS; i++) {
            leds_keys[i] = fadeTowardColor(leds_keys[i], keyColors[i], 50);
        }
        leds_profile[0] = fadeTowardColor(leds_profile[0], keyColors[12], 50);
        FastLED.show();
    }
}

/// @brief Check if any button is pressed and send the keypress to the host
/// @param None
/// @return None
void handleButtonInput(void) {
    static uint8_t prevPressedKeypadButtons[13] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    uint8_t pressedKeypadButtons[13] = {0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
    checkKeypad(pressedKeypadButtons);

    for (int i = 0; i < 13; i++) {
        if (pressedKeypadButtons[i] == 1 && prevPressedKeypadButtons[i] != 1) {
            Serial.print("K");
            Serial.print(i);
            Serial.println();

            if (i != 12) {
                leds_keys[i] = CRGB::White;
            } else {
                leds_profile[0] = CRGB::White;
            }
        }

        prevPressedKeypadButtons[i] = pressedKeypadButtons[i];
    }
}

/// @brief check the keypad for a button press
/// @param none
/// @return the button pressed, or -1 if no button is pressed
void checkKeypad(uint8_t *pressedKeys) {
    pinMode(KX0, OUTPUT);
    digitalWrite(KX0, HIGH);
    if (digitalRead(KY0)) {
        pressedKeys[0] = 1;
    }
    if (digitalRead(KY1)) {
        pressedKeys[4] = 1;
    }
    if (digitalRead(KY2)) {
        pressedKeys[8] = 1;
    }

    digitalWrite(KX0, LOW);
    pinMode(KX0, INPUT_PULLDOWN);
    pinMode(KX1, OUTPUT);
    digitalWrite(KX1, HIGH);
    if (digitalRead(KY0)) {
        pressedKeys[1] = 1;
    }
    if (digitalRead(KY1)) {
        pressedKeys[5] = 1;
    }
    if (digitalRead(KY2)) {
        pressedKeys[9] = 1;
    }

    digitalWrite(KX1, LOW);
    pinMode(KX1, INPUT_PULLDOWN);
    pinMode(KX2, OUTPUT);
    digitalWrite(KX2, HIGH);
    if (digitalRead(KY0)) {
        pressedKeys[2] = 1;
    }
    if (digitalRead(KY1)) {
        pressedKeys[6] = 1;
    }
    if (digitalRead(KY2)) {
        pressedKeys[10] = 1;
    }

    digitalWrite(KX2, LOW);
    pinMode(KX2, INPUT_PULLDOWN);
    pinMode(KX3, OUTPUT);
    digitalWrite(KX3, HIGH);
    if (digitalRead(KY0)) {
        pressedKeys[3] = 1;
    }
    if (digitalRead(KY1)) {
        pressedKeys[7] = 1;
    }
    if (digitalRead(KY2)) {
        pressedKeys[11] = 1;
    }
    digitalWrite(KX3, LOW);
    pinMode(KX3, INPUT_PULLDOWN);

    if (digitalRead(KP1)) {
        pressedKeys[12] = 1;
    }
}

/// @brief Function that blends one CRGB color toward another CRGB color by a given amount.
/// @param cur The current color, will be modified in place.
/// @param target The target color to blend toward.
/// @param amount How much to blend, a value from 0 to 255.
///               0 is no blending (current color is left unchanged).
///               255 is complete blending (current color is set to target color).
/// @return Returns the current color after blending
void nblendU8TowardU8(uint8_t& cur, const uint8_t target, uint8_t amount) {
    if (cur == target) return;

    if (cur < target) {
        uint8_t delta = target - cur;
        delta = scale8_video(delta, amount);
        cur += delta;
    } else {
        uint8_t delta = cur - target;
        delta = scale8_video(delta, amount);
        cur -= delta;
    }
}

/// @brief Function that blends one CRGB color toward another CRGB color by a given amount.
/// @param cur The current color, will be modified in place.
/// @param target The target color to blend toward.
/// @param amount How much to blend, a value from 0 to 255.
///               0 is no blending (current color is left unchanged).
///               255 is complete blending (current color is set to target color).
/// @return Returns the current color after blending.
CRGB fadeTowardColor(CRGB& cur, const CRGB& target, uint8_t amount) {
    nblendU8TowardU8(cur.red, target.red, amount);
    nblendU8TowardU8(cur.green, target.green, amount);
    nblendU8TowardU8(cur.blue, target.blue, amount);
    return cur;
}