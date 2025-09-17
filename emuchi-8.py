#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
progarm.py — CHIP‑8 emulator with Samsoft styling (Tkinter edition)
-------------------------------------------------------------------

Requirements:
  - Python 3.8+
  - tkinter (usually included with Python)

Run:
  python progarm.py [optional_rom.ch8]

This is a single‑file CHIP‑8 emulator. It implements the full classic
CHIP‑8 CPU (all documented opcodes) and a simple "PPU" (64×32 monochrome
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
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from dataclasses import dataclass
from typing import List, Optional

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
        return value // 100, (value // 10) % 10, value % 10

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
                self.memory[self.state.I] = int(b2)
                self.memory[(self.state.I + 1) & 0xFFF] = int(b1)
                self.memory[(self.state.I + 2) & 0xFFF] = int(b0)
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

# ---------------------------- Tkinter GUI (Samsoft style) ---------------------------

class SamsoftMainWindow:
    # Keypad mapping
    KEYMAP = {
        '1': 0x1, '2': 0x2, '3': 0x3, '4': 0xC,
        'q': 0x4, 'w': 0x5, 'e': 0x6, 'r': 0xD,
        'a': 0x7, 's': 0x8, 'd': 0x9, 'f': 0xE,
        'z': 0xA, 'x': 0x0, 'c': 0xB, 'v': 0xF,
    }
    
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Samsoft chip-8 emu 1.0x [C] Samsoft 199X-20XX")
        self.root.geometry("600x400")
        self.root.resizable(False, False)
        
        self.chip8 = Chip8()
        self.running = False
        self.cycles_per_second = 700
        self._cycle_accum = 0.0
        self.current_rom = None
        
        # Build GUI
        self._build_menu()
        self._build_interface()
        
        # Bind keyboard events
        self.root.bind('<KeyPress>', self._on_key_press)
        self.root.bind('<KeyRelease>', self._on_key_release)
        
        # Start the emulation loop
        self._tick_60hz()
        
        # Try to load ROM from command line
        if len(sys.argv) >= 2 and os.path.isfile(sys.argv[1]):
            self._load_rom_file(sys.argv[1])
    
    def _build_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Open ROM...", command=self.action_open_rom, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Reset", command=self.action_reset, accelerator="Ctrl+R")
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
        # Emulation menu
        emu_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Emulation", menu=emu_menu)
        emu_menu.add_command(label="Pause/Resume", command=self.action_toggle_pause, accelerator="Space")
        emu_menu.add_command(label="Step Instruction", command=self.action_step, accelerator="F7")
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.action_about)
        
        # Bind accelerators
        self.root.bind('<Control-o>', lambda e: self.action_open_rom())
        self.root.bind('<Control-r>', lambda e: self.action_reset())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<space>', lambda e: self.action_toggle_pause())
        self.root.bind('<F7>', lambda e: self.action_step())
    
    def _build_interface(self):
        # Main frame
        main_frame = tk.Frame(self.root, bg='#1e1e1e')
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Display
        left_frame = tk.Frame(main_frame, bg='#1e1e1e')
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas for display (64x32 scaled up)
        self.canvas = tk.Canvas(left_frame, width=384, height=192, bg='black', highlightthickness=0)
        self.canvas.pack(expand=True)
        
        # Control panel
        control_frame = tk.Frame(left_frame, bg='#1e1e1e')
        control_frame.pack(fill=tk.X, pady=5)
        
        self.pause_button = tk.Button(control_frame, text="Pause", command=self.action_toggle_pause, width=10)
        self.pause_button.pack(side=tk.LEFT, padx=2)
        
        tk.Button(control_frame, text="Step", command=self.action_step, width=10).pack(side=tk.LEFT, padx=2)
        tk.Button(control_frame, text="Reset", command=self.action_reset, width=10).pack(side=tk.LEFT, padx=2)
        
        # Speed control
        speed_frame = tk.Frame(control_frame, bg='#1e1e1e')
        speed_frame.pack(side=tk.LEFT, padx=10)
        tk.Label(speed_frame, text="Speed (CPS):", fg='white', bg='#1e1e1e').pack(side=tk.LEFT)
        self.speed_var = tk.IntVar(value=700)
        speed_spin = tk.Spinbox(speed_frame, from_=60, to=3000, increment=20, textvariable=self.speed_var, width=8,
                                command=self._update_speed)
        speed_spin.pack(side=tk.LEFT)
        
        # Right side - Registers
        right_frame = tk.Frame(main_frame, bg='#2a2a2a', width=180)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        right_frame.pack_propagate(False)
        
        tk.Label(right_frame, text="REGISTERS", fg='cyan', bg='#2a2a2a', font=('Courier', 10, 'bold')).pack(pady=5)
        
        # Register display
        self.reg_text = tk.Text(right_frame, width=20, height=24, bg='black', fg='lime',
                                font=('Courier', 9), state=tk.DISABLED)
        self.reg_text.pack(padx=5, pady=5)
        
        # Status bar
        self.status = tk.Label(self.root, text="Ready", bg='#333', fg='white', anchor=tk.W)
        self.status.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _update_display(self):
        """Redraw the display canvas based on chip8.display"""
        self.canvas.delete("all")
        scale = 6  # 384/64 = 6
        for y in range(32):
            for x in range(64):
                if self.chip8.display[y][x]:
                    self.canvas.create_rectangle(
                        x * scale, y * scale,
                        (x + 1) * scale, (y + 1) * scale,
                        fill='white', outline='white'
                    )
    
    def _update_registers(self):
        """Update the register display"""
        s = self.chip8.state
        text = []
        for i in range(16):
            text.append(f"V{i:X}: {s.V[i]:02X}")
        text.append(f"\nI:  {s.I:03X}")
        text.append(f"PC: {s.pc:03X}")
        text.append(f"SP: {s.sp:X}")
        text.append(f"DT: {s.delay_timer:02X}")
        text.append(f"ST: {s.sound_timer:02X}")
        text.append(f"\nCycles: {self.chip8._cycle_counter}")
        
        self.reg_text.config(state=tk.NORMAL)
        self.reg_text.delete(1.0, tk.END)
        self.reg_text.insert(1.0, '\n'.join(text))
        self.reg_text.config(state=tk.DISABLED)
    
    def _update_status(self, message=""):
        status_parts = []
        status_parts.append("Running" if self.running else "Paused")
        status_parts.append(f"CPS: {self.cycles_per_second}")
        if self.current_rom:
            status_parts.append(f"ROM: {self.current_rom}")
        if message:
            status_parts.append(message)
        self.status.config(text="  |  ".join(status_parts))
    
    def _update_speed(self):
        self.cycles_per_second = self.speed_var.get()
        self._update_status()
    
    def _on_key_press(self, event):
        key = event.char.lower()
        if key in self.KEYMAP:
            self.chip8.press_key(self.KEYMAP[key], True)
    
    def _on_key_release(self, event):
        key = event.char.lower()
        if key in self.KEYMAP:
            self.chip8.press_key(self.KEYMAP[key], False)
    
    def _tick_60hz(self):
        """Main emulation loop at 60Hz"""
        # Run cycles
        if self.running:
            self._cycle_accum += (self.cycles_per_second / 60.0)
            ncycles = int(self._cycle_accum)
            self._cycle_accum -= ncycles
            for _ in range(ncycles):
                self.chip8.cycle()
            
            # Tick timers
            self.chip8.tick_timers()
            
            # Sound beep (if needed)
            if self.chip8.state.sound_timer > 0:
                self.root.bell()
        
        # Update display if needed
        if self.chip8.draw_flag:
            self.chip8.draw_flag = False
            self._update_display()
        
        # Always update registers and status
        self._update_registers()
        self._update_status()
        
        # Schedule next tick (16.67ms for 60Hz)
        self.root.after(17, self._tick_60hz)
    
    def _load_rom_file(self, path):
        try:
            with open(path, "rb") as f:
                data = f.read()
            self.chip8.load_rom_bytes(data)
            self.current_rom = os.path.basename(path)
            self.running = True
            self.pause_button.config(text="Pause")
            self._update_status("ROM loaded")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load ROM:\n{e}")
    
    def action_open_rom(self):
        path = filedialog.askopenfilename(
            title="Open CHIP-8 ROM",
            filetypes=[("CHIP-8 ROMs", "*.ch8 *.c8 *.rom"), ("All Files", "*.*")]
        )
        if path:
            self._load_rom_file(path)
    
    def action_reset(self):
        self.chip8.reset()
        self._update_display()
        self._update_registers()
        self._update_status("Reset")
    
    def action_toggle_pause(self):
        self.running = not self.running
        self.pause_button.config(text="Resume" if not self.running else "Pause")
        self._update_status()
    
    def action_step(self):
        # Single step
        self.chip8.cycle()
        self.chip8.draw_flag = True  # Force redraw
        self._update_display()
        self._update_registers()
        self._update_status("Step")
    
    def action_about(self):
        messagebox.showinfo(
            "About Samsoft CHIP-8 Emulator",
            "Samsoft chip-8 emu 1.0x\n\n"
            "• CPU: All classic CHIP-8 opcodes\n"
            "• Display: 64×32 monochrome\n"
            "• Timers: 60 Hz delay & sound\n"
            "• Keypad: 16-key hex mapped to 1-4, Q-R, A-F, Z-V\n\n"
            "[C] Samsoft 199X-20XX"
        )

# ---------------------------- Entry point -----------------------------------

def main():
    root = tk.Tk()
    app = SamsoftMainWindow(root)
    root.mainloop()

if __name__ == "__main__":
    main()
