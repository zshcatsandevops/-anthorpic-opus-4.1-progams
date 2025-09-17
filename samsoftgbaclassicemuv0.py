#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
progarm.py — CHIP‑8 emulator with Samsoft styling
-------------------------------------------------

Requirements:
  - Python 3.8+
  - PyQt5  (pip install PyQt5)

Run:
  python progarm.py [optional_rom.ch8]

This is a single‑file CHIP‑8 emulator. It implements the full classic
CHIP‑8 CPU (all documented opcodes) and a simple “PPU” (64×32 monochrome
display), plus timers and keypad.

Keyboard mapping (PC → CHIP‑8 hex keypad):

    1 2 3 4        →   1 2 3 C
    Q W E R        →   4 5 6 D
    A S D F        →   7 8 9 E
    Z X C V        →   A 0 B F
"""
from __future__ import annotations

import sys
import os
import time
import random
from dataclasses import dataclass
from typing import List, Optional

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
except ImportError as e:
    print("PyQt5 is required. Install with: pip install PyQt5", file=sys.stderr)
    raise

try:
    FAST_TRANSFORM_HINT = QtGui.QPainter.RenderHint.FastTransformation
except AttributeError:
    FAST_TRANSFORM_HINT = getattr(QtGui.QPainter, "FastTransformation", None)

# ---------------------------- CHIP‑8 Core ----------------------------------

FONT_SET = [
    0xF0, 0x90, 0x90, 0x90, 0xF0,  # 0
    0x20, 0x60, 0x20, 0x20, 0x70,  # 1
    0xF0, 0x10, 0xF0, 0x80, 0xF0,  # 2
    0xF0, 0x10, 0xF0, 0x10, 0xF0,  # 3
    0x90, 0x90, 0xF0, 0x10, 0x10,  # 4
    0xF0, 0x80, 0xF0, 0x10, 0xF0,  # 5
    0xF0, 0x80, 0xF0, 0x90, 0xF0,  # 6
    0xF0, 0x10, 0x20, 0x40, 0x40,  # 7
    0xF0, 0x90, 0xF0, 0x90, 0xF0,  # 8
    0xF0, 0x90, 0xF0, 0x10, 0xF0,  # 9
    0xF0, 0x90, 0xF0, 0x90, 0x90,  # A
    0xE0, 0x90, 0xE0, 0x90, 0xE0,  # B
    0xF0, 0x80, 0x80, 0x80, 0xF0,  # C
    0xE0, 0x90, 0x90, 0x90, 0xE0,  # D
    0xF0, 0x80, 0xF0, 0x80, 0xF0,  # E
    0xF0, 0x80, 0xF0, 0x80, 0x80,  # F
]

@dataclass
class Chip8State:
    V: List[int]
    I: int
    pc: int
    sp: int
    stack: List[int]
    delay_timer: int
    sound_timer: int
    keys: List[bool]
    waiting_for_key_reg: Optional[int]

class Chip8:
    WIDTH = 64
    HEIGHT = 32
    MEM_SIZE = 4096
    START_ADDR = 0x200
    FONT_ADDR = 0x50

    def __init__(self):
        self.memory = bytearray(self.MEM_SIZE)
        self.display = [[0] * self.WIDTH for _ in range(self.HEIGHT)]  # 0/1 pixels
        self.state = Chip8State(
            V=[0]*16, I=0, pc=self.START_ADDR, sp=0, stack=[0]*16,
            delay_timer=0, sound_timer=0, keys=[False]*16,
            waiting_for_key_reg=None
        )
        self.draw_flag = True  # force initial clear
        self._cycle_counter = 0  # total instructions executed
        self.reset()

    def reset(self):
        self.memory[:] = b"\x00" * self.MEM_SIZE
        # load fontset at 0x50
        for i, b in enumerate(FONT_SET):
            self.memory[self.FONT_ADDR + i] = b
        # clear display
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                self.display[y][x] = 0
        self.state = Chip8State(
            V=[0]*16,
            I=0,
            pc=self.START_ADDR,
            sp=0,
            stack=[0]*16,
            delay_timer=0,
            sound_timer=0,
            keys=[False]*16,
            waiting_for_key_reg=None
        )
        self.draw_flag = True
        self._cycle_counter = 0

    def load_rom_bytes(self, data: bytes):
        if len(data) > (self.MEM_SIZE - self.START_ADDR):
            raise ValueError("ROM too large for CHIP‑8 memory")
        self.reset()
        self.memory[self.START_ADDR:self.START_ADDR+len(data)] = data

    def press_key(self, key_index: int, pressed: bool):
        if 0 <= key_index <= 0xF:
            self.state.keys[key_index] = pressed
            if pressed and self.state.waiting_for_key_reg is not None:
                vx = self.state.waiting_for_key_reg
                self.state.V[vx] = key_index & 0xFF
                self.state.waiting_for_key_reg = None

    def _clear_display(self):
        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                self.display[y][x] = 0
        self.draw_flag = True

    def _draw_sprite(self, x: int, y: int, n: int) -> int:
        """Draw n bytes starting at I at (x,y). Returns 1 if any pixel unset (collision)."""
        collision = 0
        for row in range(n):
            sprite = self.memory[(self.state.I + row) & 0xFFF]
            py = (y + row) % self.HEIGHT
            for bit in range(8):
                px = (x + (7 - bit)) % self.WIDTH  # leftmost bit is bit7
                sprite_bit = (sprite >> bit) & 1
                if sprite_bit:
                    old = self.display[py][px]
                    self.display[py][px] ^= 1
                    if old == 1 and self.display[py][px] == 0:
                        collision = 1
        self.draw_flag = True
        return collision

    def tick_timers(self):
        if self.state.delay_timer > 0:
            self.state.delay_timer -= 1
        if self.state.sound_timer > 0:
            self.state.sound_timer -= 1

    @staticmethod
    def _bcd(value: int):
        value &= 0xFF
        return value / 100, (value / 10) % 10, value % 10

    def cycle(self):
        """Execute one instruction (2 bytes)."""
        # If waiting for key (Fx0A), stall
        if self.state.waiting_for_key_reg is not None:
            return

        pc = self.state.pc
        opcode = (self.memory[pc] << 8) | self.memory[pc + 1]
        self.state.pc = (pc + 2) & 0xFFF
        self._cycle_counter += 1

        nnn = opcode & 0x0FFF
        n = opcode & 0x000F
        x = (opcode >> 8) & 0x000F
        y = (opcode >> 4) & 0x000F
        kk = opcode & 0x00FF

        V = self.state.V

        op_high = opcode & 0xF000
        if op_high == 0x0000:
            if opcode == 0x00E0:
                self._clear_display()
            elif opcode == 0x00EE:
                # return from subroutine
                self.state.sp = (self.state.sp - 1) & 0xF
                self.state.pc = self.state.stack[self.state.sp]
            else:
                # 0nnn: SYS (ignored / not used)
                pass
        elif op_high == 0x1000:
            # 1nnn: JP addr
            self.state.pc = nnn
        elif op_high == 0x2000:
            # 2nnn: CALL addr
            self.state.stack[self.state.sp] = self.state.pc
            self.state.sp = (self.state.sp + 1) & 0xF
            self.state.pc = nnn
        elif op_high == 0x3000:
            # 3xkk: SE Vx, byte
            if V[x] == kk:
                self.state.pc = (self.state.pc + 2) & 0xFFF
        elif op_high == 0x4000:
            # 4xkk: SNE Vx, byte
            if V[x] != kk:
                self.state.pc = (self.state.pc + 2) & 0xFFF
        elif op_high == 0x5000:
            # 5xy0: SE Vx, Vy
            if n == 0 and V[x] == V[y]:
                self.state.pc = (self.state.pc + 2) & 0xFFF
        elif op_high == 0x6000:
            # 6xkk: LD Vx, byte
            V[x] = kk
        elif op_high == 0x7000:
            # 7xkk: ADD Vx, byte
            V[x] = (V[x] + kk) & 0xFF
        elif op_high == 0x8000:
            # 8xy*
            last = n
            if last == 0x0:
                V[x] = V[y]
            elif last == 0x1:
                V[x] = V[x] | V[y]
            elif last == 0x2:
                V[x] = V[x] & V[y]
            elif last == 0x3:
                V[x] = V[x] ^ V[y]
            elif last == 0x4:
                total = V[x] + V[y]
                V[0xF] = 1 if total > 0xFF else 0
                V[x] = total & 0xFF
            elif last == 0x5:
                V[0xF] = 1 if V[x] >= V[y] else 0
                V[x] = (V[x] - V[y]) & 0xFF
            elif last == 0x6:
                # SHIFT RIGHT — use Vx in modern interpreters
                V[0xF] = V[x] & 0x1
                V[x] = (V[x] >> 1) & 0xFF
            elif last == 0x7:
                V[0xF] = 1 if V[y] >= V[x] else 0
                V[x] = (V[y] - V[x]) & 0xFF
            elif last == 0xE:
                V[0xF] = (V[x] >> 7) & 0x1
                V[x] = (V[x] << 1) & 0xFF
            else:
                pass
        elif op_high == 0x9000:
            # 9xy0: SNE Vx, Vy
            if n == 0 and V[x] != V[y]:
                self.state.pc = (self.state.pc + 2) & 0xFFF
        elif op_high == 0xA000:
            # Annn: LD I, addr
            self.state.I = nnn
        elif op_high == 0xB000:
            # Bnnn: JP V0, addr
            self.state.pc = (nnn + V[0]) & 0xFFF
        elif op_high == 0xC000:
            # Cxkk: RND Vx, byte
            V[x] = random.getrandbits(8) & kk
        elif op_high == 0xD000:
            # Dxyn: DRW Vx,Vy,n
            vx = V[x] & 0xFF
            vy = V[y] & 0xFF
            V[0xF] = self._draw_sprite(vx, vy, n)
        elif op_high == 0xE000:
            # Ex9E / ExA1
            key = V[x] & 0xF
            if kk == 0x9E:
                if self.state.keys[key]:
                    self.state.pc = (self.state.pc + 2) & 0xFFF
            elif kk == 0xA1:
                if not self.state.keys[key]:
                    self.state.pc = (self.state.pc + 2) & 0xFFF
        elif op_high == 0xF000:
            if kk == 0x07:
                V[x] = self.state.delay_timer & 0xFF
            elif kk == 0x0A:
                # Wait for key press, store in Vx
                self.state.waiting_for_key_reg = x
            elif kk == 0x15:
                self.state.delay_timer = V[x] & 0xFF
            elif kk == 0x18:
                self.state.sound_timer = V[x] & 0xFF
            elif kk == 0x1E:
                total = self.state.I + V[x]
                V[0xF] = 1 if total > 0xFFF else 0
                self.state.I = total & 0xFFF
            elif kk == 0x29:
                # font sprite for 0-F at 0x50, 5 bytes each
                self.state.I = (Chip8.FONT_ADDR + (V[x] & 0xF) * 5) & 0xFFF
            elif kk == 0x33:
                b2, b1, b0 = self._bcd(V[x])
                self.memory[self.state.I] = b2
                self.memory[(self.state.I + 1) & 0xFFF] = b1
                self.memory[(self.state.I + 2) & 0xFFF] = b0
            elif kk == 0x55:
                # store V0..Vx at I..I+x (I increments)
                for i in range(x + 1):
                    self.memory[(self.state.I + i) & 0xFFF] = V[i] & 0xFF
                self.state.I = (self.state.I + x + 1) & 0xFFF
            elif kk == 0x65:
                # read V0..Vx from I..I+x (I increments)
                for i in range(x + 1):
                    V[i] = self.memory[(self.state.I + i) & 0xFFF] & 0xFF
                self.state.I = (self.state.I + x + 1) & 0xFFF
            else:
                pass
        else:
            pass

# ---------------------------- Qt GUI (Samsoft style) ---------------------------

class DisplayWidget(QtWidgets.QWidget):
    """Simple 64×32 display widget that scales to fit, draws from Chip8.display."""
    def __init__(self, chip8: Chip8, parent=None):
        super().__init__(parent)
        self.chip8 = chip8
        self.setMinimumSize(64*4, 32*4)
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        self._image = None
        self._rebuild_image()  # initial

    def sizeHint(self):
        return QtCore.QSize(64*8, 32*8)

    def _rebuild_image(self):
        img = QtGui.QImage(Chip8.WIDTH, Chip8.HEIGHT, QtGui.QImage.Format_RGB32)
        img.fill(QtGui.QColor(0, 0, 0))
        white = QtGui.qRgb(255, 255, 255)
        for y in range(Chip8.HEIGHT):
            row = self.chip8.display[y]
            for x in range(Chip8.WIDTH):
                if row[x]:
                    img.setPixel(x, y, white)
        self._image = img

    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(30, 30, 30))
        if self._image is None:
            return
        # Compute aspect‑preserving scale
        w = self.width()
        h = self.height()
        scale = min(w / Chip8.WIDTH, h / Chip8.HEIGHT)
        dest_w = int(Chip8.WIDTH * scale)
        dest_h = int(Chip8.HEIGHT * scale)
        left = (w - dest_w) / 2
        top = (h - dest_h) / 2
        target = QtCore.QRect(left, top, dest_w, dest_h)
        if FAST_TRANSFORM_HINT is not None:
            painter.setRenderHint(FAST_TRANSFORM_HINT, True)
        painter.drawImage(target, self._image)

    def refresh_if_needed(self):
        if self.chip8.draw_flag:
            self.chip8.draw_flag = False
            self._rebuild_image()
            self.update()

    # Keypad handling — map to CHIP‑8 keys
    KEYMAP = {
        QtCore.Qt.Key_1: 0x1, QtCore.Qt.Key_2: 0x2, QtCore.Qt.Key_3: 0x3, QtCore.Qt.Key_4: 0xC,
        QtCore.Qt.Key_Q: 0x4, QtCore.Qt.Key_W: 0x5, QtCore.Qt.Key_E: 0x6, QtCore.Qt.Key_R: 0xD,
        QtCore.Qt.Key_A: 0x7, QtCore.Qt.Key_S: 0x8, QtCore.Qt.Key_D: 0x9, QtCore.Qt.Key_F: 0xE,
        QtCore.Qt.Key_Z: 0xA, QtCore.Qt.Key_X: 0x0, QtCore.Qt.Key_C: 0xB, QtCore.Qt.Key_V: 0xF,
    }

    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if not e.isAutoRepeat():
            k = e.key()
            if k in self.KEYMAP:
                self.chip8.press_key(self.KEYMAP[k], True)
        super().keyPressEvent(e)

    def keyReleaseEvent(self, e: QtGui.QKeyEvent):
        if not e.isAutoRepeat():
            k = e.key()
            if k in self.KEYMAP:
                self.chip8.press_key(self.KEYMAP[k], False)
        super().keyReleaseEvent(e)

class RegistersDock(QtWidgets.QDockWidget):
    def __init__(self, chip8: Chip8, parent=None):
        super().__init__("Registers / State", parent)
        self.chip8 = chip8
        self.table = QtWidgets.QTableWidget(22, 2, self)
        self.table.setHorizontalHeaderLabels(["Register", "Value"])
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
        self.setWidget(self.table)
        self.populate()

    def populate(self):
        labels = [f"V{hex(i)[2:].upper()}" for i in range(16)] + ["I", "PC", "SP", "DT", "ST", "CYCLES"]
        for row, name in enumerate(labels):
            self.table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
            self.table.setItem(row, 1, QtWidgets.QTableWidgetItem(""))
        self.table.resizeColumnsToContents()

    def refresh(self):
        s = self.chip8.state
        values = [f"0x{s.V[i]:02X}" for i in range(16)] + [
            f"0x{s.I:03X}", f"0x{s.pc:03X}", f"0x{s.sp:X}", f"{s.delay_timer}", f"{s.sound_timer}", f"{self.chip8._cycle_counter}"
        ]
        for row, val in enumerate(values):
            item = self.table.item(row, 1)
            if item:
                item.setText(val)

class SamsoftMainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Samsoft chip-8 emu 1.0x [C] Samsoft 199X-20XX")
        self.resize(900, 600)

        self.chip8 = Chip8()
        self.display = DisplayWidget(self.chip8, self)
        self.setCentralWidget(self.display)

        self.registers_dock = RegistersDock(self.chip8, self)
        self.addDockWidget(QtCore.Qt.RightDockWidgetArea, self.registers_dock)

        # Emulation control
        self.running = False
        self.cycles_per_second = 700.0  # default speed
        self._cycle_accum = 0.0

        # 60Hz master timer
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._tick_60hz)
        self.timer.start(int(1000/60))

        # UI
        self._build_menus()
        self._build_toolbar()
        self._update_status()

        # If a ROM path was provided on CLI, try to load it after show
        QtCore.QTimer.singleShot(0, self._load_rom_from_cli)

    # ------------------- UI construction -------------------
    def _build_menus(self):
        bar = self.menuBar()

        file_menu = bar.addMenu("&File")
        act_open = file_menu.addAction("&Open ROM…")
        act_open.setShortcut("Ctrl+O")
        act_open.triggered.connect(self.action_open_rom)

        file_menu.addSeparator()
        act_reset = file_menu.addAction("&Reset")
        act_reset.setShortcut("Ctrl+R")
        act_reset.triggered.connect(self.action_reset)

        file_menu.addSeparator()
        act_exit = file_menu.addAction("E&xit")
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)

        emu_menu = bar.addMenu("&Emulation")
        self.act_pause = emu_menu.addAction("&Pause/Resume")
        self.act_pause.setShortcut("Space")
        self.act_pause.setCheckable(True)
        self.act_pause.triggered.connect(self.action_toggle_pause)

        act_step = emu_menu.addAction("&Step Instruction")
        act_step.setShortcut("F7")
        act_step.triggered.connect(self.action_step)

        view_menu = bar.addMenu("&View")
        self.act_show_regs = view_menu.addAction("Show &Registers")
        self.act_show_regs.setCheckable(True)
        self.act_show_regs.setChecked(True)
        self.act_show_regs.toggled.connect(self.registers_dock.setVisible)
        self.registers_dock.visibilityChanged.connect(self.act_show_regs.setChecked)

        help_menu = bar.addMenu("&Help")
        act_about = help_menu.addAction("&About")
        act_about.triggered.connect(self.action_about)

    def _build_toolbar(self):
        tb = QtWidgets.QToolBar("Controls", self)
        self.addToolBar(tb)

        btn_open = QtWidgets.QAction("Open", self)
        btn_open.triggered.connect(self.action_open_rom)
        tb.addAction(btn_open)

        btn_pause = QtWidgets.QAction("Pause", self)
        btn_pause.setCheckable(True)
        btn_pause.triggered.connect(self.action_toggle_pause)
        tb.addAction(btn_pause)
        self._toolbar_pause_action = btn_pause

        btn_step = QtWidgets.QAction("Step", self)
        btn_step.triggered.connect(self.action_step)
        tb.addAction(btn_step)

        tb.addSeparator()
        lbl = QtWidgets.QLabel("Speed (CPS): ")
        tb.addWidget(lbl)

        self.speed_box = QtWidgets.QSpinBox(self)
        self.speed_box.setRange(60, 3000)
        self.speed_box.setSingleStep(20)
        self.speed_box.setValue(int(self.cycles_per_second))
        self.speed_box.valueChanged.connect(self._set_speed_from_box)
        tb.addWidget(self.speed_box)

    # ------------------- Actions -------------------
    def action_open_rom(self):
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open CHIP‑8 ROM", "", "CHIP‑8 ROMs (*.ch8 *.c8 *.rom);;All Files (*)"
        )
        if path:
            try:
                with open(path, "rb") as f:
                    data = f.read()
                self.chip8.load_rom_bytes(data)
                self.running = True
                self.act_pause.setChecked(True)
                self._toolbar_pause_action.setChecked(True)
                self._update_status(rom=os.path.basename(path), message="ROM loaded")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load ROM:\n{e}")

    def action_reset(self):
        self.chip8.reset()
        self.display.refresh_if_needed()
        self.registers_dock.refresh()
        self._update_status(message="Reset")

    def action_toggle_pause(self, checked: bool):
        self.running = checked
        self._toolbar_pause_action.setChecked(checked)
        self.act_pause.setChecked(checked)
        self._update_status()

    def action_step(self):
        # Single step (always runs one instruction)
        self.chip8.cycle()
        self.display.refresh_if_needed()
        self.registers_dock.refresh()
        self._update_status(message="Step")

    def action_about(self):
        QtWidgets.QMessageBox.information(
            self, "About Samsoft CHIP-8 Emulator",
            "Samsoft chip-8 emu 1.0x\n\n"
            "• CPU: All classic CHIP‑8 opcodes\n"
            "• Display: 64×32 monochrome\n"
            "• Timers: 60 Hz delay & sound\n"
            "• Keypad: 16‑key hex mapped to 1‑4, Q‑R, A‑F, Z‑V\n\n"
            "[C] Samsoft 199X-20XX"
        )

    def _set_speed_from_box(self, val: int):
        self.cycles_per_second = float(val)
        self._update_status()

    def _load_rom_from_cli(self):
        if len(sys.argv) >= 2 and os.path.isfile(sys.argv[1]):
            try:
                with open(sys.argv[1], "rb") as f:
                    data = f.read()
                self.chip8.load_rom_bytes(data)
                self.running = True
                self.act_pause.setChecked(True)
                self._toolbar_pause_action.setChecked(True)
                self._update_status(rom=os.path.basename(sys.argv[1]), message="ROM loaded")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load ROM from CLI:\n{e}")

    # ------------------- Emulation loop -------------------
    def _tick_60hz(self):
        # Emulation step & timers
        if self.running:
            self._cycle_accum += (self.cycles_per_second / 60.0)
            ncycles = int(self._cycle_accum)
            self._cycle_accum -= ncycles
            for _ in range(ncycles):
                self.chip8.cycle()
        # Timers tick at 60Hz regardless of paused state? Typically they pause with emu.
        if self.running:
            self.chip8.tick_timers()
            if self.chip8.state.sound_timer > 0:
                # best‑effort bell; cross‑platform console BEL
                sys.stdout.write("\a")
                sys.stdout.flush()
        # Repaint if needed
        self.display.refresh_if_needed()
        self.registers_dock.refresh()
        self._update_status()

    def _update_status(self, rom: Optional[str] = None, message: Optional[str] = None):
        status = []
        status.append("Running" if self.running else "Paused")
        status.append(f"CPS: {int(self.cycles_per_second)}")
        if rom:
            status.append(f"ROM: {rom}")
        if message:
            status.append(message)
        self.statusBar().showMessage("  |  ".join(status))

# ---------------------------- Entry point -----------------------------------

def main():
    app = QtWidgets.QApplication(sys.argv)
    win = SamsoftMainWindow()
    win.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
