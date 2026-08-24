class LEDController:
    """Manage all LED functionalities of APC40MK2."""

    CLIP_ROWS = 5
    CLIP_COLS = 8

    def __init__(self, midiout):
        self.midiout = midiout

        # Named colors
        self.color_map = {
            "black": 0, "dark gray": 1, "gray": 2, "white": 3,
            "red": 5, "orange": 9, "yellow": 13, "green": 21,
            "cyan": 37, "blue": 45, "purple": 49,
            "magenta": 53, "pink": 57
        }

        # All 128 MIDI color codes with hex for closest match
        self.color_codes = [
            (0, "#000000"), (1, "#1E1E1E"), (2, "#7F7F7F"), (3, "#FFFFFF"),
            (5, "#FF0000"), (9, "#FF5400"), (13, "#FFFF00"),
            (21, "#00FF00"), (37, "#00A9FF"), (45, "#0000FF"),
            (49, "#5400FF"), (53, "#FF00FF"), (57, "#FF0054")
        ]

    def _find_closest_color(self, hex_color):
        """Return the closest MIDI color index for a hex color."""
        def hex_to_rgb(h):
            h = h.lstrip("#")
            return [int(h[i:i+2], 16) for i in (0, 2, 4)]

        target = hex_to_rgb(hex_color)
        best = (0, float("inf"))

        for idx, code in self.color_codes:
            rgb = hex_to_rgb(code)
            dist = sum((a - b) ** 2 for a, b in zip(target, rgb))
            if dist < best[1]:
                best = (idx, dist)
        return best[0]

    def _resolve_color(self, color):
        if isinstance(color, str):
            if color.startswith("#"):
                color = self._find_closest_color(color)
            else:
                color = self.color_map.get(color.lower())
        if not isinstance(color, int) or not 0 <= color <= 127:
            raise ValueError(f"Invalid color: {color}")
        return color

    # ---------------------------
    # CLIP GRID
    # ---------------------------
    def set_clip_launch(self, row, column, color, led_type=0):
        if row not in range(1, 6):
            raise ValueError("row must be 1–5")
        if column not in range(1, 9):
            raise ValueError("column must be 1–8")
        if led_type not in range(16):
            raise ValueError("led_type must be 0–15")

        color = self._resolve_color(color)
        note = (self.CLIP_ROWS - row) * self.CLIP_COLS + (column - 1)

        self.midiout.sendNoteOn(
            led_type + 1,
            note,
            color / 127.0
        )

    # ---------------------------
    # TRACK BUTTONS
    # ---------------------------
    def _track_button(self, track, note, value):
        if track not in range(1, 9):
            raise ValueError("track must be 1–8")
        
        velocity = value
        if isinstance(value, bool):
            velocity = 127 if value else 0
        self.midiout.sendNoteOn(track, note, int(velocity))

    def set_track_record(self, track, state):
        self._track_button(track, 0x30, state)

    def set_track_solo(self, track, state):
        self._track_button(track, 0x31, state)

    def set_track_number(self, track, state):
        self._track_button(track, 0x32, state)

    def set_track_select(self, track, state):
        self._track_button(track, 0x33, state)

    def set_track_clip_stop(self, track, state):
        if state not in range(3):
            raise ValueError("state must be 0–2")
        self.midiout.sendNoteOn(track, 0x34 + 1, state / 127.0)

    # ---------------------------
    # SCENE LAUNCH
    # ---------------------------
    def set_scene_launch(self, scene, color, led_type=0):
        if scene not in range(1, 6):
            raise ValueError("scene must be 1–5")
        if led_type not in range(16):
            raise ValueError("led_type must be 0–15")
        color = self._resolve_color(color)
        self.midiout.sendNoteOn(led_type + 1, 0x52 + scene, color / 127.0)


# ---------------------------
# KNOB CONTROLLER
# ---------------------------
class KnobController:
    def __init__(self, midiout):
        self.midiout = midiout

    def set_track_knob_type(self, index, type):
        if index not in range(1, 9):
            raise ValueError("index must be 1–8")
        if type not in range(128):
            raise ValueError("type must be 0–127")
        self.midiout.send(0xB0, 0x38 + index - 1, type)

    def set_track_knob_value(self, index, value):
        if index not in range(1, 9):
            raise ValueError("index must be 1–8")
        if value not in range(128):
            raise ValueError("value must be 0–127")
        self.midiout.send(0xB0, 0x30 + index - 1, value)


# ---------------------------
# DEVICE MODE CONTROLLER
# ---------------------------
class DeviceModeController:
    def __init__(self, midiout):
        self.midiout = midiout

    def set_device_mode(self, mode):
        if mode not in (0, 1, 2):
            raise ValueError("mode must be 0, 1, or 2")
        self.midiout.sendExclusive(
            0x47, 0x7F, 0x29, 0x60,
            0x00, 0x04, 0x40 + mode,
            0x01, 0x00, 0x00
        )


# ---------------------------
# MAIN APC40MK2 CLASS
# ---------------------------
class APC40MK2:
    def __init__(self, midiout):
        self.midiout = midiout
        self.led = LEDController(midiout)
        self.knob = KnobController(midiout)
        self.mode = DeviceModeController(midiout)
