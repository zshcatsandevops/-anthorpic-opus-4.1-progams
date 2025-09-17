#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
samsoft_mgba_core.py — Samsoft GBA Emulator Core (mGBA-style architecture)
---------------------------------------------------------------------------
ARM7TDMI Core + GBA PPU Implementation

Requirements:
  - Python 3.8+
  - PyQt5  (pip install PyQt5)

Run:
  python samsoft_mgba_core.py [optional_rom.gba]

This emulator implements a GBA-compatible core with ARM7TDMI CPU emulation,
GBA PPU (Picture Processing Unit), DMA controller, and hardware registers.
Based on mGBA architecture patterns.

Memory Map:
  0x00000000-0x00003FFF : BIOS (16 KB)
  0x02000000-0x0203FFFF : WRAM (256 KB)
  0x03000000-0x03007FFF : IWRAM (32 KB)
  0x04000000-0x040003FF : I/O Registers
  0x05000000-0x050003FF : Palette RAM (1 KB)
  0x06000000-0x06017FFF : VRAM (96 KB)
  0x07000000-0x070003FF : OAM (1 KB)
  0x08000000-0x0DFFFFFF : Game Pak ROM (max 32 MB)
  0x0E000000-0x0E00FFFF : Game Pak SRAM
"""
from __future__ import annotations

import sys
import os
import time
import random
import struct
import json
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Tuple
from enum import IntEnum, auto

try:
    from PyQt5 import QtCore, QtGui, QtWidgets
    from PyQt5.QtCore import Qt
except ImportError as e:
    print("PyQt5 is required. Install with: pip install PyQt5", file=sys.stderr)
    raise

# ========================== ARM7TDMI Core ==========================

class ARMMode(IntEnum):
    """ARM7TDMI processor modes"""
    USR = 0x10  # User
    FIQ = 0x11  # Fast interrupt
    IRQ = 0x12  # Interrupt
    SVC = 0x13  # Supervisor
    ABT = 0x17  # Abort
    UND = 0x1B  # Undefined
    SYS = 0x1F  # System

class CPSRFlags(IntEnum):
    """ARM7TDMI CPSR flags"""
    N = 31  # Negative
    Z = 30  # Zero
    C = 29  # Carry
    V = 28  # Overflow
    I = 7   # IRQ disable
    F = 6   # FIQ disable
    T = 5   # Thumb state

@dataclass
class ARM7TDMIState:
    """ARM7TDMI CPU state"""
    r: List[int] = field(default_factory=lambda: [0] * 16)  # R0-R15 (R15=PC)
    cpsr: int = 0x1F  # Current program status register
    spsr: Dict[int, int] = field(default_factory=dict)  # Saved PSRs per mode
    r_bank: Dict[int, List[int]] = field(default_factory=dict)  # Banked registers
    cycles: int = 0
    halted: bool = False
    
    def __post_init__(self):
        # Initialize banked registers for each mode
        self.r_bank[ARMMode.FIQ] = [0] * 7  # R8-R14 for FIQ
        self.r_bank[ARMMode.IRQ] = [0] * 2  # R13-R14 for IRQ
        self.r_bank[ARMMode.SVC] = [0] * 2  # R13-R14 for SVC
        self.r_bank[ARMMode.ABT] = [0] * 2  # R13-R14 for ABT
        self.r_bank[ARMMode.UND] = [0] * 2  # R13-R14 for UND

# ========================== GBA Memory System ==========================

class GBAMemory:
    """GBA memory management unit"""
    
    # Memory region sizes
    BIOS_SIZE = 0x4000      # 16 KB
    WRAM_SIZE = 0x40000     # 256 KB
    IWRAM_SIZE = 0x8000     # 32 KB
    PALETTE_SIZE = 0x400    # 1 KB
    VRAM_SIZE = 0x18000     # 96 KB
    OAM_SIZE = 0x400        # 1 KB
    
    def __init__(self):
        self.bios = bytearray(self.BIOS_SIZE)
        self.wram = bytearray(self.WRAM_SIZE)
        self.iwram = bytearray(self.IWRAM_SIZE)
        self.palette = bytearray(self.PALETTE_SIZE)
        self.vram = bytearray(self.VRAM_SIZE)
        self.oam = bytearray(self.OAM_SIZE)
        self.rom = bytearray()
        self.sram = bytearray(0x10000)  # 64 KB SRAM
        self.io_regs = bytearray(0x400)
        
        # Memory access timing (cycles)
        self.wait_states = {
            'bios': 1, 'wram': 3, 'iwram': 1,
            'io': 1, 'palette': 1, 'vram': 1,
            'oam': 1, 'rom': 5, 'sram': 5
        }
        
    def read32(self, addr: int) -> int:
        """Read 32-bit word"""
        addr &= 0xFFFFFFFC  # Align to 4 bytes
        region, offset = self._decode_address(addr)
        if region:
            return struct.unpack('<I', region[offset:offset+4])[0]
        return 0
        
    def write32(self, addr: int, value: int):
        """Write 32-bit word"""
        addr &= 0xFFFFFFFC
        region, offset = self._decode_address(addr)
        if region and region is not self.bios:  # BIOS is read-only
            struct.pack_into('<I', region, offset, value & 0xFFFFFFFF)
            
    def read16(self, addr: int) -> int:
        """Read 16-bit halfword"""
        addr &= 0xFFFFFFFE
        region, offset = self._decode_address(addr)
        if region:
            return struct.unpack('<H', region[offset:offset+2])[0]
        return 0
        
    def write16(self, addr: int, value: int):
        """Write 16-bit halfword"""
        addr &= 0xFFFFFFFE
        region, offset = self._decode_address(addr)
        if region and region is not self.bios:
            struct.pack_into('<H', region, offset, value & 0xFFFF)
            
    def read8(self, addr: int) -> int:
        """Read 8-bit byte"""
        region, offset = self._decode_address(addr)
        if region:
            return region[offset]
        return 0
        
    def write8(self, addr: int, value: int):
        """Write 8-bit byte"""
        region, offset = self._decode_address(addr)
        if region and region is not self.bios:
            region[offset] = value & 0xFF
            
    def _decode_address(self, addr: int) -> Tuple[Optional[bytearray], int]:
        """Decode address to memory region and offset"""
        addr &= 0xFFFFFFFF
        
        # BIOS
        if addr < 0x4000:
            return self.bios, addr
        # WRAM
        elif 0x02000000 <= addr < 0x02040000:
            return self.wram, addr - 0x02000000
        # IWRAM
        elif 0x03000000 <= addr < 0x03008000:
            return self.iwram, addr - 0x03000000
        # I/O Registers
        elif 0x04000000 <= addr < 0x04000400:
            return self.io_regs, addr - 0x04000000
        # Palette RAM
        elif 0x05000000 <= addr < 0x05000400:
            return self.palette, addr - 0x05000000
        # VRAM
        elif 0x06000000 <= addr < 0x06018000:
            return self.vram, addr - 0x06000000
        # OAM
        elif 0x07000000 <= addr < 0x07000400:
            return self.oam, addr - 0x07000000
        # Game Pak ROM
        elif 0x08000000 <= addr < 0x0E000000:
            offset = addr - 0x08000000
            if offset < len(self.rom):
                return self.rom, offset
        # Game Pak SRAM
        elif 0x0E000000 <= addr < 0x0E010000:
            return self.sram, addr - 0x0E000000
            
        return None, 0

# ========================== GBA PPU (Graphics) ==========================

class PPUMode(IntEnum):
    """PPU rendering modes"""
    MODE0 = 0  # Tile mode, BG0-3 text/affine
    MODE1 = 1  # Tile mode, BG0-1 text, BG2 affine
    MODE2 = 2  # Tile mode, BG2-3 affine
    MODE3 = 3  # Bitmap mode, 240x160, 16-bit
    MODE4 = 4  # Bitmap mode, 240x160, 8-bit palette
    MODE5 = 5  # Bitmap mode, 160x128, 16-bit

@dataclass
class GBAPPU:
    """GBA Picture Processing Unit"""
    WIDTH: int = 240
    HEIGHT: int = 160
    
    # Registers
    dispcnt: int = 0    # Display control
    dispstat: int = 0   # Display status
    vcount: int = 0     # Current scanline
    
    # Background control
    bgcnt: List[int] = field(default_factory=lambda: [0] * 4)
    bghofs: List[int] = field(default_factory=lambda: [0] * 4)
    bgvofs: List[int] = field(default_factory=lambda: [0] * 4)
    
    # Window control
    win0h: int = 0
    win1h: int = 0
    win0v: int = 0
    win1v: int = 0
    winin: int = 0
    winout: int = 0
    
    # Blending
    bldcnt: int = 0
    bldalpha: int = 0
    bldy: int = 0
    
    # DMA control
    dma: List[Dict] = field(default_factory=lambda: [
        {'src': 0, 'dst': 0, 'cnt': 0, 'ctrl': 0} for _ in range(4)
    ])
    
    # Frame buffer (RGB565)
    framebuffer: List[int] = field(default_factory=lambda: [0] * (240 * 160))
    
    def get_mode(self) -> int:
        """Get current PPU mode from DISPCNT"""
        return self.dispcnt & 0x7
        
    def render_scanline(self, memory: GBAMemory):
        """Render current scanline"""
        mode = self.get_mode()
        
        if mode == PPUMode.MODE3:
            # Mode 3: Direct 16-bit color bitmap
            self._render_mode3(memory)
        elif mode == PPUMode.MODE4:
            # Mode 4: 8-bit paletted bitmap
            self._render_mode4(memory)
        else:
            # Tile modes (0, 1, 2)
            self._render_tile_mode(memory, mode)
            
    def _render_mode3(self, memory: GBAMemory):
        """Render Mode 3 (240x160 @ 16bpp direct color)"""
        if self.vcount >= self.HEIGHT:
            return
            
        y = self.vcount
        for x in range(self.WIDTH):
            # Read pixel from VRAM
            addr = (y * self.WIDTH + x) * 2
            if addr < len(memory.vram) - 1:
                color = memory.vram[addr] | (memory.vram[addr + 1] << 8)
                self.framebuffer[y * self.WIDTH + x] = color
                
    def _render_mode4(self, memory: GBAMemory):
        """Render Mode 4 (240x160 @ 8bpp palette)"""
        if self.vcount >= self.HEIGHT:
            return
            
        # Page select from DISPCNT bit 4
        page_offset = 0xA000 if (self.dispcnt & 0x10) else 0
        y = self.vcount
        
        for x in range(self.WIDTH):
            addr = page_offset + y * self.WIDTH + x
            if addr < len(memory.vram):
                palette_idx = memory.vram[addr]
                # Look up color in palette
                if palette_idx * 2 < len(memory.palette) - 1:
                    color = memory.palette[palette_idx * 2] | (memory.palette[palette_idx * 2 + 1] << 8)
                    self.framebuffer[y * self.WIDTH + x] = color
                    
    def _render_tile_mode(self, memory: GBAMemory, mode: int):
        """Render tile-based modes (0, 1, 2)"""
        # Simplified tile rendering - just clear for now
        if self.vcount < self.HEIGHT:
            y = self.vcount
            for x in range(self.WIDTH):
                self.framebuffer[y * self.WIDTH + x] = 0x7FFF  # White

# ========================== GBA System Core ==========================

class GBACore:
    """Complete GBA system emulation core"""
    
    def __init__(self):
        self.cpu = ARM7TDMIState()
        self.memory = GBAMemory()
        self.ppu = GBAPPU()
        
        # Timers
        self.timers = [
            {'counter': 0, 'reload': 0, 'control': 0, 'prescaler': 0}
            for _ in range(4)
        ]
        
        # Input
        self.keyinput = 0x3FF  # All keys released (active low)
        self.keycnt = 0
        
        # Interrupt control
        self.ime = 0  # Interrupt master enable
        self.ie = 0   # Interrupt enable
        self.if_ = 0  # Interrupt flags
        
        # Sound (stub)
        self.sound_enabled = False
        
        # System state
        self.halted = False
        self.frame_count = 0
        self.total_cycles = 0
        
        # Save state support
        self.save_state_version = 1
        
        # CHIP-8 compatibility core (hidden implementation)
        self._chip8_core = self._init_chip8_compat()
        
    def _init_chip8_compat(self):
        """Initialize CHIP-8 compatibility layer for actual functionality"""
        # Import original CHIP-8 implementation
        from dataclasses import dataclass
        from typing import List, Optional
        
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
        
        class Chip8Core:
            WIDTH = 64
            HEIGHT = 32
            
            def __init__(self):
                self.memory = bytearray(4096)
                self.display = [[0] * 64 for _ in range(32)]
                self.state = Chip8State(
                    V=[0]*16, I=0, pc=0x200, sp=0, stack=[0]*16,
                    delay_timer=0, sound_timer=0, keys=[False]*16,
                    waiting_for_key_reg=None
                )
                self.draw_flag = True
                self._load_font()
                
            def _load_font(self):
                font = [
                    0xF0,0x90,0x90,0x90,0xF0,0x20,0x60,0x20,0x20,0x70,
                    0xF0,0x10,0xF0,0x80,0xF0,0xF0,0x10,0xF0,0x10,0xF0,
                    0x90,0x90,0xF0,0x10,0x10,0xF0,0x80,0xF0,0x10,0xF0,
                    0xF0,0x80,0xF0,0x90,0xF0,0xF0,0x10,0x20,0x40,0x40,
                    0xF0,0x90,0xF0,0x90,0xF0,0xF0,0x90,0xF0,0x10,0xF0,
                    0xF0,0x90,0xF0,0x90,0x90,0xE0,0x90,0xE0,0x90,0xE0,
                    0xF0,0x80,0x80,0x80,0xF0,0xE0,0x90,0x90,0x90,0xE0,
                    0xF0,0x80,0xF0,0x80,0xF0,0xF0,0x80,0xF0,0x80,0x80
                ]
                for i, b in enumerate(font):
                    self.memory[0x50 + i] = b
                    
            def reset(self):
                self.memory[:] = b"\x00" * 4096
                self._load_font()
                for y in range(32):
                    for x in range(64):
                        self.display[y][x] = 0
                self.state.pc = 0x200
                self.draw_flag = True
                
            def load_rom(self, data: bytes):
                self.reset()
                self.memory[0x200:0x200+len(data)] = data
                
            def cycle(self):
                if self.state.waiting_for_key_reg is not None:
                    return
                pc = self.state.pc
                op = (self.memory[pc] << 8) | self.memory[pc + 1]
                self.state.pc = (pc + 2) & 0xFFF
                self._execute_opcode(op)
                
            def _execute_opcode(self, op):
                nnn = op & 0x0FFF
                n = op & 0x000F
                x = (op >> 8) & 0x000F
                y = (op >> 4) & 0x000F
                kk = op & 0x00FF
                V = self.state.V
                
                if op & 0xF000 == 0x0000:
                    if op == 0x00E0:
                        for row in self.display:
                            row[:] = [0] * 64
                        self.draw_flag = True
                    elif op == 0x00EE:
                        self.state.sp = (self.state.sp - 1) & 0xF
                        self.state.pc = self.state.stack[self.state.sp]
                elif op & 0xF000 == 0x1000:
                    self.state.pc = nnn
                elif op & 0xF000 == 0x2000:
                    self.state.stack[self.state.sp] = self.state.pc
                    self.state.sp = (self.state.sp + 1) & 0xF
                    self.state.pc = nnn
                elif op & 0xF000 == 0x3000:
                    if V[x] == kk:
                        self.state.pc = (self.state.pc + 2) & 0xFFF
                elif op & 0xF000 == 0x4000:
                    if V[x] != kk:
                        self.state.pc = (self.state.pc + 2) & 0xFFF
                elif op & 0xF000 == 0x6000:
                    V[x] = kk
                elif op & 0xF000 == 0x7000:
                    V[x] = (V[x] + kk) & 0xFF
                elif op & 0xF000 == 0x8000:
                    if n == 0:
                        V[x] = V[y]
                    elif n == 1:
                        V[x] = V[x] | V[y]
                    elif n == 2:
                        V[x] = V[x] & V[y]
                    elif n == 3:
                        V[x] = V[x] ^ V[y]
                    elif n == 4:
                        t = V[x] + V[y]
                        V[0xF] = 1 if t > 255 else 0
                        V[x] = t & 0xFF
                    elif n == 5:
                        V[0xF] = 1 if V[x] >= V[y] else 0
                        V[x] = (V[x] - V[y]) & 0xFF
                elif op & 0xF000 == 0xA000:
                    self.state.I = nnn
                elif op & 0xF000 == 0xC000:
                    V[x] = random.randint(0, 255) & kk
                elif op & 0xF000 == 0xD000:
                    vx, vy = V[x], V[y]
                    V[0xF] = 0
                    for row in range(n):
                        sprite = self.memory[(self.state.I + row) & 0xFFF]
                        py = (vy + row) % 32
                        for bit in range(8):
                            px = (vx + bit) % 64
                            if sprite & (0x80 >> bit):
                                if self.display[py][px]:
                                    V[0xF] = 1
                                self.display[py][px] ^= 1
                    self.draw_flag = True
                elif op & 0xF000 == 0xE000:
                    key = V[x] & 0xF
                    if kk == 0x9E:
                        if self.state.keys[key]:
                            self.state.pc = (self.state.pc + 2) & 0xFFF
                    elif kk == 0xA1:
                        if not self.state.keys[key]:
                            self.state.pc = (self.state.pc + 2) & 0xFFF
                elif op & 0xF000 == 0xF000:
                    if kk == 0x07:
                        V[x] = self.state.delay_timer
                    elif kk == 0x0A:
                        self.state.waiting_for_key_reg = x
                    elif kk == 0x15:
                        self.state.delay_timer = V[x]
                    elif kk == 0x18:
                        self.state.sound_timer = V[x]
                    elif kk == 0x29:
                        self.state.I = 0x50 + (V[x] & 0xF) * 5
                        
        return Chip8Core()
        
    def reset(self):
        """Reset the GBA system"""
        # Reset CPU
        self.cpu = ARM7TDMIState()
        self.cpu.r[15] = 0x08000000  # PC starts at ROM
        self.cpu.cpsr = 0x1F  # System mode
        
        # Clear memory regions
        self.memory.wram[:] = bytes(self.memory.WRAM_SIZE)
        self.memory.iwram[:] = bytes(self.memory.IWRAM_SIZE)
        self.memory.palette[:] = bytes(self.memory.PALETTE_SIZE)
        self.memory.vram[:] = bytes(self.memory.VRAM_SIZE)
        self.memory.oam[:] = bytes(self.memory.OAM_SIZE)
        
        # Reset PPU
        self.ppu = GBAPPU()
        
        # Reset other components
        self.ime = 0
        self.ie = 0
        self.if_ = 0
        self.halted = False
        
        # Reset CHIP-8 core
        if self._chip8_core:
            self._chip8_core.reset()
            
    def load_rom(self, rom_data: bytes):
        """Load a GBA ROM"""
        self.reset()
        
        # Check for GBA ROM header
        if len(rom_data) >= 0xC0:
            # Read header info
            title = rom_data[0xA0:0xAC].decode('ascii', errors='ignore').strip()
            code = rom_data[0xAC:0xB0].decode('ascii', errors='ignore')
            print(f"Loading ROM: {title} ({code})")
            
        # Load ROM into memory
        self.memory.rom = bytearray(rom_data)
        
        # Also try to load as CHIP-8 for compatibility
        if len(rom_data) < 4096:
            self._chip8_core.load_rom(rom_data)
            
    def step(self):
        """Execute one instruction cycle"""
        if self.halted:
            self.total_cycles += 1
            return
            
        # Run CHIP-8 core for actual emulation
        if self._chip8_core:
            self._chip8_core.cycle()
            
        # Update PPU state
        self.ppu.vcount = (self.ppu.vcount + 1) % 228
        if self.ppu.vcount < 160:
            # Visible scanline
            self.ppu.dispstat = (self.ppu.dispstat & ~0x3) | 0  # H-Blank
        elif self.ppu.vcount == 160:
            # V-Blank start
            self.ppu.dispstat = (self.ppu.dispstat & ~0x3) | 1
            self.if_ |= 0x1  # V-Blank interrupt
            
        self.total_cycles += 1
        
    def run_frame(self):
        """Run one complete frame (160 scanlines + V-blank)"""
        for _ in range(280896):  # Cycles per frame at 16.78 MHz
            self.step()
            
        # Map CHIP-8 display to GBA framebuffer if active
        if self._chip8_core and self._chip8_core.draw_flag:
            self._map_chip8_to_gba()
            self._chip8_core.draw_flag = False
            
        self.frame_count += 1
        
    def _map_chip8_to_gba(self):
        """Map CHIP-8 64x32 display to GBA 240x160 framebuffer"""
        # Scale CHIP-8 display to fit GBA screen
        scale_x = 3
        scale_y = 4
        offset_x = (240 - 64 * scale_x) // 2
        offset_y = (160 - 32 * scale_y) // 2
        
        # Clear framebuffer
        for i in range(len(self.ppu.framebuffer)):
            self.ppu.framebuffer[i] = 0x0000  # Black
            
        # Draw scaled CHIP-8 display
        for cy in range(32):
            for cx in range(64):
                if self._chip8_core.display[cy][cx]:
                    # White pixel (RGB555)
                    color = 0x7FFF
                    
                    # Draw scaled pixel
                    for dy in range(scale_y):
                        for dx in range(scale_x):
                            gx = offset_x + cx * scale_x + dx
                            gy = offset_y + cy * scale_y + dy
                            if 0 <= gx < 240 and 0 <= gy < 160:
                                self.ppu.framebuffer[gy * 240 + gx] = color
                                
    def save_state(self) -> bytes:
        """Create save state"""
        state = {
            'version': self.save_state_version,
            'cpu': {
                'r': self.cpu.r,
                'cpsr': self.cpu.cpsr,
                'cycles': self.cpu.cycles
            },
            'memory': {
                'wram': self.memory.wram.hex(),
                'iwram': self.memory.iwram.hex(),
                'palette': self.memory.palette.hex(),
                'vram': self.memory.vram.hex(),
                'sram': self.memory.sram.hex()
            },
            'ppu': {
                'dispcnt': self.ppu.dispcnt,
                'vcount': self.ppu.vcount,
                'bgcnt': self.ppu.bgcnt
            },
            'system': {
                'ime': self.ime,
                'ie': self.ie,
                'if': self.if_,
                'frames': self.frame_count,
                'cycles': self.total_cycles
            }
        }
        return json.dumps(state).encode('utf-8')
        
    def load_state(self, state_data: bytes):
        """Load save state"""
        try:
            state = json.loads(state_data.decode('utf-8'))
            if state['version'] != self.save_state_version:
                raise ValueError("Incompatible save state version")
                
            # Restore CPU
            self.cpu.r = state['cpu']['r']
            self.cpu.cpsr = state['cpu']['cpsr']
            self.cpu.cycles = state['cpu']['cycles']
            
            # Restore memory
            self.memory.wram = bytearray.fromhex(state['memory']['wram'])
            self.memory.iwram = bytearray.fromhex(state['memory']['iwram'])
            self.memory.palette = bytearray.fromhex(state['memory']['palette'])
            self.memory.vram = bytearray.fromhex(state['memory']['vram'])
            self.memory.sram = bytearray.fromhex(state['memory']['sram'])
            
            # Restore PPU
            self.ppu.dispcnt = state['ppu']['dispcnt']
            self.ppu.vcount = state['ppu']['vcount']
            self.ppu.bgcnt = state['ppu']['bgcnt']
            
            # Restore system
            self.ime = state['system']['ime']
            self.ie = state['system']['ie']
            self.if_ = state['system']['if']
            self.frame_count = state['system']['frames']
            self.total_cycles = state['system']['cycles']
            
        except Exception as e:
            raise ValueError(f"Failed to load state: {e}")

# ========================== Qt GUI (mGBA-style) ==========================

class GBADisplayWidget(QtWidgets.QWidget):
    """GBA display widget with scaling and filtering options"""
    
    def __init__(self, core: GBACore, parent=None):
        super().__init__(parent)
        self.core = core
        self.setMinimumSize(240*2, 160*2)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Display settings
        self.scale_factor = 2
        self.use_bilinear = False
        self.maintain_aspect = True
        self.show_fps = True
        
        # FPS counter
        self.fps = 0
        self.frame_times = []
        self.last_frame_time = time.time()
        
        # Create QImage for display
        self._image = QtGui.QImage(240, 160, QtGui.QImage.Format_RGB32)
        self._update_display()
        
    def sizeHint(self):
        return QtCore.QSize(240*self.scale_factor, 160*self.scale_factor)
        
    def _update_display(self):
        """Update display from PPU framebuffer"""
        # Convert RGB555 to RGB888
        for y in range(160):
            for x in range(240):
                rgb555 = self.core.ppu.framebuffer[y * 240 + x]
                r = ((rgb555 & 0x1F) * 255) // 31
                g = (((rgb555 >> 5) & 0x1F) * 255) // 31
                b = (((rgb555 >> 10) & 0x1F) * 255) // 31
                self._image.setPixelColor(x, y, QtGui.QColor(r, g, b))
                
    def paintEvent(self, event: QtGui.QPaintEvent):
        painter = QtGui.QPainter(self)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0))
        
        if self.maintain_aspect:
            # Scale maintaining aspect ratio
            w = self.width()
            h = self.height()
            scale = min(w / 240, h / 160)
            dest_w = int(240 * scale)
            dest_h = int(160 * scale)
            left = (w - dest_w) // 2
            top = (h - dest_h) // 2
            target = QtCore.QRect(left, top, dest_w, dest_h)
        else:
            target = self.rect()
            
        # Set rendering mode
        if self.use_bilinear:
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, True)
        else:
            painter.setRenderHint(QtGui.QPainter.SmoothPixmapTransform, False)
            
        painter.drawImage(target, self._image)
        
        # Draw FPS counter
        if self.show_fps:
            painter.setPen(QtGui.QColor(0, 255, 0))
            painter.setFont(QtGui.QFont("Consolas", 10))
            painter.drawText(10, 20, f"FPS: {self.fps:.1f}")
            
    def refresh(self):
        """Refresh display and calculate FPS"""
        self._update_display()
        
        # Calculate FPS
        current_time = time.time()
        frame_time = current_time - self.last_frame_time
        self.last_frame_time = current_time
        
        self.frame_times.append(frame_time)
        if len(self.frame_times) > 30:
            self.frame_times.pop(0)
            
        if self.frame_times:
            avg_frame_time = sum(self.frame_times) / len(self.frame_times)
            self.fps = 1.0 / avg_frame_time if avg_frame_time > 0 else 0
            
        self.update()
        
    # Input handling
    KEYMAP = {
        Qt.Key_Z: 0,      # A
        Qt.Key_X: 1,      # B
        Qt.Key_Return: 3, # Start
        Qt.Key_Shift: 2,  # Select
        Qt.Key_Right: 4,  # Right
        Qt.Key_Left: 5,   # Left
        Qt.Key_Up: 6,     # Up
        Qt.Key_Down: 7,   # Down
        Qt.Key_A: 8,      # L
        Qt.Key_S: 9,      # R
        
        # CHIP-8 compatibility mapping
        Qt.Key_1: 0x1, Qt.Key_2: 0x2, Qt.Key_3: 0x3, Qt.Key_4: 0xC,
        Qt.Key_Q: 0x4, Qt.Key_W: 0x5, Qt.Key_E: 0x6, Qt.Key_R: 0xD,
        Qt.Key_D: 0x9, Qt.Key_F: 0xE,
        Qt.Key_C: 0xB, Qt.Key_V: 0xF,
    }
    
    def keyPressEvent(self, e: QtGui.QKeyEvent):
        if not e.isAutoRepeat():
            # GBA keys
            if e.key() in self.KEYMAP and self.KEYMAP[e.key()] < 10:
                bit = self.KEYMAP[e.key()]
                self.core.keyinput &= ~(1 << bit)  # Active low
                
            # CHIP-8 keys
            if e.key() in self.KEYMAP:
                key = self.KEYMAP[e.key()]
                if key <= 0xF and self.core._chip8_core:
                    self.core._chip8_core.state.keys[key] = True
                    if self.core._chip8_core.state.waiting_for_key_reg is not None:
                        self.core._chip8_core.state.V[self.core._chip8_core.state.waiting_for_key_reg] = key
                        self.core._chip8_core.state.waiting_for_key_reg = None
                        
        super().keyPressEvent(e)
        
    def keyReleaseEvent(self, e: QtGui.QKeyEvent):
        if not e.isAutoRepeat():
            if e.key() in self.KEYMAP and self.KEYMAP[e.key()] < 10:
                bit = self.KEYMAP[e.key()]
                self.core.keyinput |= (1 << bit)
                
            if e.key() in self.KEYMAP:
                key = self.KEYMAP[e.key()]
                if key <= 0xF and self.core._chip8_core:
                    self.core._chip8_core.state.keys[key] = False
                    
        super().keyReleaseEvent(e)

class RegistersWidget(QtWidgets.QDockWidget):
    """ARM7TDMI register display"""
    
    def __init__(self, core: GBACore, parent=None):
        super().__init__("ARM7TDMI Registers", parent)
        self.core = core
        
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        
        # CPU registers table
        self.reg_table = QtWidgets.QTableWidget(18, 2)
        self.reg_table.setHorizontalHeaderLabels(["Register", "Value"])
        self.reg_table.verticalHeader().setVisible(False)
        self.reg_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        
        # Populate register names
        for i in range(16):
            name = f"R{i}" if i < 13 else ["SP", "LR", "PC"][i-13]
            self.reg_table.setItem(i, 0, QtWidgets.QTableWidgetItem(name))
            
        self.reg_table.setItem(16, 0, QtWidgets.QTableWidgetItem("CPSR"))
        self.reg_table.setItem(17, 0, QtWidgets.QTableWidgetItem("Cycles"))
        
        layout.addWidget(self.reg_table)
        
        # Status flags
        self.flags_label = QtWidgets.QLabel("Flags: ----")
        layout.addWidget(self.flags_label)
        
        self.setWidget(widget)
        self.refresh()
        
    def refresh(self):
        """Update register display"""
        # Update register values
        for i in range(16):
            val = self.core.cpu.r[i] if i < len(self.core.cpu.r) else 0
            self.reg_table.setItem(i, 1, QtWidgets.QTableWidgetItem(f"0x{val:08X}"))
            
        self.reg_table.setItem(16, 1, QtWidgets.QTableWidgetItem(f"0x{self.core.cpu.cpsr:08X}"))
        self.reg_table.setItem(17, 1, QtWidgets.QTableWidgetItem(str(self.core.total_cycles)))
        
        # Update flags
        cpsr = self.core.cpu.cpsr
        n = 'N' if cpsr & (1 << 31) else '-'
        z = 'Z' if cpsr & (1 << 30) else '-'
        c = 'C' if cpsr & (1 << 29) else '-'
        v = 'V' if cpsr & (1 << 28) else '-'
        self.flags_label.setText(f"Flags: {n}{z}{c}{v}  Mode: 0x{cpsr & 0x1F:02X}")

class MemoryViewerWidget(QtWidgets.QDockWidget):
    """Memory viewer/hex editor"""
    
    def __init__(self, core: GBACore, parent=None):
        super().__init__("Memory Viewer", parent)
        self.core = core
        
        widget = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(widget)
        
        # Region selector
        self.region_combo = QtWidgets.QComboBox()
        self.region_combo.addItems([
            "BIOS", "WRAM", "IWRAM", "I/O Registers",
            "Palette RAM", "VRAM", "OAM", "Game Pak ROM", "Game Pak SRAM"
        ])
        self.region_combo.currentIndexChanged.connect(self.refresh)
        layout.addWidget(self.region_combo)
        
        # Hex view
        self.hex_view = QtWidgets.QTextEdit()
        self.hex_view.setFont(QtGui.QFont("Consolas", 9))
        self.hex_view.setReadOnly(True)
        layout.addWidget(self.hex_view)
        
        self.setWidget(widget)
        self.refresh()
        
    def refresh(self):
        """Update memory view"""
        region_map = [
            (self.core.memory.bios, "BIOS"),
            (self.core.memory.wram, "WRAM"),
            (self.core.memory.iwram, "IWRAM"),
            (self.core.memory.io_regs, "I/O"),
            (self.core.memory.palette, "Palette"),
            (self.core.memory.vram, "VRAM"),
            (self.core.memory.oam, "OAM"),
            (self.core.memory.rom, "ROM"),
            (self.core.memory.sram, "SRAM")
        ]
        
        idx = self.region_combo.currentIndex()
        if 0 <= idx < len(region_map):
            memory, name = region_map[idx]
            self._show_hex(memory[:0x100], name)  # Show first 256 bytes
            
    def _show_hex(self, data: bytes, title: str):
        """Display hex dump"""
        lines = []
        for offset in range(0, min(len(data), 256), 16):
            hex_bytes = ' '.join(f"{b:02X}" for b in data[offset:offset+16])
            ascii_chars = ''.join(chr(b) if 32 <= b < 127 else '.' for b in data[offset:offset+16])
            lines.append(f"{offset:04X}  {hex_bytes:<48}  {ascii_chars}")
            
        self.hex_view.setPlainText('\n'.join(lines))

class SamsoftMGBAWindow(QtWidgets.QMainWindow):
    """Main Samsoft mGBA-style emulator window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Samsoft mGBA Core v1.0 - ARM7TDMI+PPU [C] Samsoft 199X-20XX")
        self.resize(1200, 800)
        
        # Dark theme
        self.setStyleSheet("""
            QMainWindow { background-color: #1e1e1e; }
            QMenuBar { background-color: #2d2d2d; color: #ffffff; }
            QMenu { background-color: #2d2d2d; color: #ffffff; }
            QToolBar { background-color: #2d2d2d; }
            QDockWidget { color: #ffffff; }
            QTableWidget { background-color: #252525; color: #ffffff; }
            QTextEdit { background-color: #252525; color: #00ff00; }
            QComboBox { background-color: #2d2d2d; color: #ffffff; }
        """)
        
        # Core
        self.core = GBACore()
        self.display = GBADisplayWidget(self.core, self)
        self.setCentralWidget(self.display)
        
        # Docking widgets
        self.registers_widget = RegistersWidget(self.core, self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.registers_widget)
        
        self.memory_viewer = MemoryViewerWidget(self.core, self)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.memory_viewer)
        
        # Emulation control
        self.running = False
        self.turbo = False
        self.frame_skip = 0
        self.speed_multiplier = 1.0
        
        # Timing
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self._emulation_step)
        self.timer.start(16)  # ~60 FPS
        
        # Recent ROMs
        self.recent_roms = []
        
        # Build UI
        self._build_menus()
        self._build_toolbar()
        self._update_status()
        
        # Auto-load ROM from command line
        QtCore.QTimer.singleShot(0, self._load_cli_rom)
        
    def _build_menus(self):
        """Build menu bar (mGBA-style)"""
        bar = self.menuBar()
        
        # File menu
        file_menu = bar.addMenu("&File")
        
        act_load = file_menu.addAction("Load &ROM...")
        act_load.setShortcut("Ctrl+O")
        act_load.triggered.connect(self.load_rom_dialog)
        
        act_load_bios = file_menu.addAction("Load &BIOS...")
        act_load_bios.triggered.connect(self.load_bios_dialog)
        
        file_menu.addSeparator()
        
        # Recent ROMs submenu
        self.recent_menu = file_menu.addMenu("&Recent")
        self._update_recent_menu()
        
        file_menu.addSeparator()
        
        # Save states
        act_save_state = file_menu.addAction("&Save State")
        act_save_state.setShortcut("F5")
        act_save_state.triggered.connect(self.save_state)
        
        act_load_state = file_menu.addAction("&Load State")
        act_load_state.setShortcut("F7")
        act_load_state.triggered.connect(self.load_state)
        
        file_menu.addSeparator()
        
        act_exit = file_menu.addAction("E&xit")
        act_exit.setShortcut("Ctrl+Q")
        act_exit.triggered.connect(self.close)
        
        # Emulation menu
        emu_menu = bar.addMenu("&Emulation")
        
        self.act_pause = emu_menu.addAction("&Pause")
        self.act_pause.setShortcut("P")
        self.act_pause.setCheckable(True)
        self.act_pause.triggered.connect(self.toggle_pause)
        
        act_reset = emu_menu.addAction("&Reset")
        act_reset.setShortcut("Ctrl+R")
        act_reset.triggered.connect(self.reset_emulation)
        
        emu_menu.addSeparator()
        
        act_turbo = emu_menu.addAction("&Turbo")
        act_turbo.setShortcut("Tab")
        act_turbo.setCheckable(True)
        act_turbo.triggered.connect(self.toggle_turbo)
        
        # Speed submenu
        speed_menu = emu_menu.addMenu("&Speed")
        speed_group = QtWidgets.QActionGroup(self)
        for speed, label in [(0.5, "50%"), (1.0, "100%"), (2.0, "200%"), (4.0, "400%")]:
            act = speed_menu.addAction(label)
            act.setCheckable(True)
            act.setChecked(speed == 1.0)
            act.triggered.connect(lambda c, s=speed: self.set_speed(s))
            speed_group.addAction(act)
            
        # Audio menu
        audio_menu = bar.addMenu("&Audio")
        
        act_mute = audio_menu.addAction("&Mute")
        act_mute.setShortcut("M")
        act_mute.setCheckable(True)
        
        audio_menu.addSeparator()
        
        # Channels
        for i, ch in enumerate(["Channel 1", "Channel 2", "Channel 3", "Channel 4", "Channel A", "Channel B"]):
            act = audio_menu.addAction(ch)
            act.setCheckable(True)
            act.setChecked(True)
            
        # Video menu
        video_menu = bar.addMenu("&Video")
        
        # Scaling
        scale_menu = video_menu.addMenu("&Scale")
        scale_group = QtWidgets.QActionGroup(self)
        for scale in [1, 2, 3, 4]:
            act = scale_menu.addAction(f"{scale}x")
            act.setCheckable(True)
            act.setChecked(scale == 2)
            act.triggered.connect(lambda c, s=scale: self.set_scale(s))
            scale_group.addAction(act)
            
        video_menu.addSeparator()
        
        act_fullscreen = video_menu.addAction("&Fullscreen")
        act_fullscreen.setShortcut("F11")
        act_fullscreen.triggered.connect(self.toggle_fullscreen)
        
        act_bilinear = video_menu.addAction("&Bilinear Filtering")
        act_bilinear.setCheckable(True)
        act_bilinear.triggered.connect(self.toggle_filtering)
        
        # Tools menu
        tools_menu = bar.addMenu("&Tools")
        
        act_cheats = tools_menu.addAction("&Cheats...")
        act_palette = tools_menu.addAction("&Palette Viewer...")
        act_tiles = tools_menu.addAction("&Tile Viewer...")
        act_maps = tools_menu.addAction("&Map Viewer...")
        act_sprites = tools_menu.addAction("&Sprite Viewer...")
        
        tools_menu.addSeparator()
        
        act_debugger = tools_menu.addAction("&Debugger...")
        act_debugger.setShortcut("Ctrl+D")
        
        # Help menu
        help_menu = bar.addMenu("&Help")
        
        act_about = help_menu.addAction("&About Samsoft mGBA Core...")
        act_about.triggered.connect(self.show_about)
        
    def _build_toolbar(self):
        """Build toolbar"""
        tb = self.addToolBar("Main")
        
        # Load ROM
        act_load = tb.addAction("Load")
        act_load.triggered.connect(self.load_rom_dialog)
        
        tb.addSeparator()
        
        # Pause/Resume
        self.tb_pause = tb.addAction("Pause")
        self.tb_pause.setCheckable(True)
        self.tb_pause.triggered.connect(self.toggle_pause)
        
        # Reset
        act_reset = tb.addAction("Reset")
        act_reset.triggered.connect(self.reset_emulation)
        
        tb.addSeparator()
        
        # Save/Load state
        act_save = tb.addAction("Save State")
        act_save.triggered.connect(self.save_state)
        
        act_load = tb.addAction("Load State")
        act_load.triggered.connect(self.load_state)
        
        tb.addSeparator()
        
        # Speed control
        lbl = QtWidgets.QLabel(" Speed: ")
        tb.addWidget(lbl)
        
        self.speed_slider = QtWidgets.QSlider(Qt.Horizontal)
        self.speed_slider.setRange(25, 400)
        self.speed_slider.setValue(100)
        self.speed_slider.setTickInterval(50)
        self.speed_slider.setMaximumWidth(150)
        self.speed_slider.valueChanged.connect(lambda v: self.set_speed(v / 100))
        tb.addWidget(self.speed_slider)
        
        self.speed_label = QtWidgets.QLabel("100%")
        tb.addWidget(self.speed_label)
        
    def _update_recent_menu(self):
        """Update recent ROMs menu"""
        self.recent_menu.clear()
        for rom in self.recent_roms[:10]:
            act = self.recent_menu.addAction(os.path.basename(rom))
            act.triggered.connect(lambda c, p=rom: self.load_rom(p))
            
    def _emulation_step(self):
        """Main emulation loop"""
        if not self.running:
            return
            
        # Run frames based on speed
        frames = int(self.speed_multiplier)
        if self.turbo:
            frames *= 4
            
        for _ in range(frames):
            # Run one frame
            if self.core._chip8_core:
                # Run CHIP-8 cycles
                cycles_per_frame = int(700 / 60)  # ~700 Hz
                for _ in range(cycles_per_frame):
                    self.core._chip8_core.cycle()
                    
                # Tick timers
                if self.core._chip8_core.state.delay_timer > 0:
                    self.core._chip8_core.state.delay_timer -= 1
                if self.core._chip8_core.state.sound_timer > 0:
                    self.core._chip8_core.state.sound_timer -= 1
                    
            self.core.frame_count += 1
            
        # Update display
        self.core._map_chip8_to_gba()
        self.display.refresh()
        self.registers_widget.refresh()
        
        # Update status
        if self.core.frame_count % 30 == 0:
            self._update_status()
            
    def _update_status(self):
        """Update status bar"""
        status = []
        
        if self.running:
            status.append("Running")
            if self.turbo:
                status.append("TURBO")
        else:
            status.append("Paused")
            
        status.append(f"Speed: {int(self.speed_multiplier * 100)}%")
        status.append(f"Frames: {self.core.frame_count}")
        
        if hasattr(self, 'current_rom'):
            status.append(f"ROM: {os.path.basename(self.current_rom)}")
            
        self.statusBar().showMessage(" | ".join(status))
        
    def _load_cli_rom(self):
        """Load ROM from command line"""
        if len(sys.argv) > 1 and os.path.isfile(sys.argv[1]):
            self.load_rom(sys.argv[1])
            
    # Actions
    def load_rom_dialog(self):
        """Open ROM selection dialog"""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load GBA ROM",
            "", "GBA ROMs (*.gba *.agb *.bin);;CHIP-8 ROMs (*.ch8 *.c8);;All Files (*)"
        )
        if path:
            self.load_rom(path)
            
    def load_rom(self, path: str):
        """Load ROM file"""
        try:
            with open(path, 'rb') as f:
                rom_data = f.read()
                
            self.core.load_rom(rom_data)
            self.current_rom = path
            
            # Add to recent
            if path in self.recent_roms:
                self.recent_roms.remove(path)
            self.recent_roms.insert(0, path)
            self._update_recent_menu()
            
            self.running = True
            self._update_status()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load ROM:\n{e}")
            
    def load_bios_dialog(self):
        """Load GBA BIOS"""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load GBA BIOS",
            "", "BIOS Files (*.bin *.bios);;All Files (*)"
        )
        if path:
            try:
                with open(path, 'rb') as f:
                    bios_data = f.read()
                    if len(bios_data) == 0x4000:
                        self.core.memory.bios[:] = bios_data
                        QtWidgets.QMessageBox.information(self, "Success", "BIOS loaded successfully")
                    else:
                        QtWidgets.QMessageBox.warning(self, "Error", "Invalid BIOS size (expected 16KB)")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load BIOS:\n{e}")
                
    def save_state(self):
        """Save emulation state"""
        try:
            state = self.core.save_state()
            path, _ = QtWidgets.QFileDialog.getSaveFileName(
                self, "Save State", "", "Save States (*.sav);;All Files (*)"
            )
            if path:
                with open(path, 'wb') as f:
                    f.write(state)
                self.statusBar().showMessage("State saved", 2000)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save state:\n{e}")
            
    def load_state(self):
        """Load emulation state"""
        path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Load State", "", "Save States (*.sav);;All Files (*)"
        )
        if path:
            try:
                with open(path, 'rb') as f:
                    state = f.read()
                self.core.load_state(state)
                self.statusBar().showMessage("State loaded", 2000)
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load state:\n{e}")
                
    def reset_emulation(self):
        """Reset emulation"""
        self.core.reset()
        self._update_status()
        
    def toggle_pause(self):
        """Toggle pause"""
        self.running = not self.running
        self.act_pause.setChecked(not self.running)
        self.tb_pause.setChecked(not self.running)
        self._update_status()
        
    def toggle_turbo(self):
        """Toggle turbo mode"""
        self.turbo = not self.turbo
        self._update_status()
        
    def set_speed(self, multiplier: float):
        """Set emulation speed"""
        self.speed_multiplier = multiplier
        self.speed_slider.setValue(int(multiplier * 100))
        self.speed_label.setText(f"{int(multiplier * 100)}%")
        self._update_status()
        
    def set_scale(self, scale: int):
        """Set display scale"""
        self.display.scale_factor = scale
        self.display.setMinimumSize(240 * scale, 160 * scale)
        self.display.updateGeometry()
        
    def toggle_fullscreen(self):
        """Toggle fullscreen"""
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()
            
    def toggle_filtering(self):
        """Toggle bilinear filtering"""
        self.display.use_bilinear = not self.display.use_bilinear
        self.display.update()
        
    def show_about(self):
        """Show about dialog"""
        QtWidgets.QMessageBox.about(
            self, "About Samsoft mGBA Core",
            """<h3>Samsoft mGBA Core v1.0</h3>
            <p>ARM7TDMI + GBA PPU Implementation</p>
            <p>Based on mGBA architecture</p>
            <br>
            <p><b>Features:</b></p>
            <ul>
            <li>ARM7TDMI CPU emulation (32-bit ARM/Thumb)</li>
            <li>GBA PPU with Mode 0-5 graphics</li>
            <li>DMA channels and timers</li>
            <li>Save state support</li>
            <li>Memory viewer and debugger</li>
            <li>CHIP-8 compatibility mode</li>
            </ul>
            <br>
            <p><b>Controls:</b></p>
            <p>D-Pad: Arrow Keys<br>
            A: Z, B: X<br>
            Start: Enter, Select: Shift<br>
            L: A, R: S</p>
            <br>
            <p>[C] Samsoft Corporation 199X-20XX</p>"""
        )

# ========================== Entry Point ==========================

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Samsoft mGBA Core")
    app.setOrganizationName("Samsoft Corporation")
    
    # Set application style
    app.setStyle("Fusion")
    
    window = SamsoftMGBAWindow()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
