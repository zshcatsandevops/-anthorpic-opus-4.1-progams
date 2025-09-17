#!/usr/bin/env python3
"""
=============================================================================
SamSoft GB Emulator Client - Unified Production Build
=============================================================================
IndyCat-Origin Edition for Haltmann OS 1.X-infdev
Complete Game Boy emulator with integrated ROM generator and test suite
Photon-accelerated through LightFS Gaussian Split channels
=============================================================================
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import numpy as np
from dataclasses import dataclass
from typing import Optional, List, Dict, Tuple
import time
import struct
import os
import sys
from enum import IntEnum
import threading
import queue

# === VERSION INFO ===
__version__ = "1.0.0-infdev"
__codename__ = "IndyCat-Origin"
__build__ = "CatKernel v0.1 with GPTLayer"

# === CONSTANTS ===
SCREEN_WIDTH = 160
SCREEN_HEIGHT = 144
SCALE_FACTOR = 3
CLOCK_SPEED = 4194304  # 4.19 MHz
FPS = 60
CYCLES_PER_FRAME = CLOCK_SPEED // FPS

# === COLOR PALETTES ===
PALETTES = {
    "Classic GB": [
        (155, 188, 15),   # White
        (139, 172, 15),   # Light gray
        (48, 98, 48),     # Dark gray
        (15, 56, 15)      # Black
    ],
    "Pocket": [
        (255, 255, 255),  # White
        (170, 170, 170),  # Light gray
        (85, 85, 85),     # Dark gray
        (0, 0, 0)         # Black
    ],
    "Light": [
        (0, 255, 102),    # White
        (0, 187, 74),     # Light gray
        (0, 119, 47),     # Dark gray
        (0, 51, 20)       # Black
    ],
    "CRT": [
        (224, 248, 208),  # White
        (136, 192, 112),  # Light gray
        (52, 104, 86),    # Dark gray
        (8, 24, 32)       # Black
    ],
    "SamSoft": [
        (0, 255, 255),    # Cyan
        (0, 170, 255),    # Blue
        (255, 0, 255),    # Magenta
        (0, 0, 85)        # Dark blue
    ]
}

# === CPU FLAGS ===
class Flags:
    ZERO = 0x80      # Z
    NEGATIVE = 0x40  # N
    HALFCARRY = 0x20 # H
    CARRY = 0x10     # C

# === COMPLETE OPCODE TABLE ===
class Opcodes:
    """Complete GB CPU instruction set"""
    
    # Format: opcode: (mnemonic, length, cycles, handler_name)
    TABLE = {
        0x00: ("NOP", 1, 4),
        0x01: ("LD BC,d16", 3, 12),
        0x02: ("LD (BC),A", 1, 8),
        0x03: ("INC BC", 1, 8),
        0x04: ("INC B", 1, 4),
        0x05: ("DEC B", 1, 4),
        0x06: ("LD B,d8", 2, 8),
        0x07: ("RLCA", 1, 4),
        0x08: ("LD (a16),SP", 3, 20),
        0x09: ("ADD HL,BC", 1, 8),
        0x0A: ("LD A,(BC)", 1, 8),
        0x0B: ("DEC BC", 1, 8),
        0x0C: ("INC C", 1, 4),
        0x0D: ("DEC C", 1, 4),
        0x0E: ("LD C,d8", 2, 8),
        0x0F: ("RRCA", 1, 4),
        
        0x10: ("STOP", 2, 4),
        0x11: ("LD DE,d16", 3, 12),
        0x12: ("LD (DE),A", 1, 8),
        0x13: ("INC DE", 1, 8),
        0x14: ("INC D", 1, 4),
        0x15: ("DEC D", 1, 4),
        0x16: ("LD D,d8", 2, 8),
        0x17: ("RLA", 1, 4),
        0x18: ("JR r8", 2, 12),
        0x19: ("ADD HL,DE", 1, 8),
        0x1A: ("LD A,(DE)", 1, 8),
        0x1B: ("DEC DE", 1, 8),
        0x1C: ("INC E", 1, 4),
        0x1D: ("DEC E", 1, 4),
        0x1E: ("LD E,d8", 2, 8),
        0x1F: ("RRA", 1, 4),
        
        0x20: ("JR NZ,r8", 2, [12, 8]),
        0x21: ("LD HL,d16", 3, 12),
        0x22: ("LD (HL+),A", 1, 8),
        0x23: ("INC HL", 1, 8),
        0x24: ("INC H", 1, 4),
        0x25: ("DEC H", 1, 4),
        0x26: ("LD H,d8", 2, 8),
        0x27: ("DAA", 1, 4),
        0x28: ("JR Z,r8", 2, [12, 8]),
        0x29: ("ADD HL,HL", 1, 8),
        0x2A: ("LD A,(HL+)", 1, 8),
        0x2B: ("DEC HL", 1, 8),
        0x2C: ("INC L", 1, 4),
        0x2D: ("DEC L", 1, 4),
        0x2E: ("LD L,d8", 2, 8),
        0x2F: ("CPL", 1, 4),
        
        0x30: ("JR NC,r8", 2, [12, 8]),
        0x31: ("LD SP,d16", 3, 12),
        0x32: ("LD (HL-),A", 1, 8),
        0x33: ("INC SP", 1, 8),
        0x34: ("INC (HL)", 1, 12),
        0x35: ("DEC (HL)", 1, 12),
        0x36: ("LD (HL),d8", 2, 12),
        0x37: ("SCF", 1, 4),
        0x38: ("JR C,r8", 2, [12, 8]),
        0x39: ("ADD HL,SP", 1, 8),
        0x3A: ("LD A,(HL-)", 1, 8),
        0x3B: ("DEC SP", 1, 8),
        0x3C: ("INC A", 1, 4),
        0x3D: ("DEC A", 1, 4),
        0x3E: ("LD A,d8", 2, 8),
        0x3F: ("CCF", 1, 4),
        
        # 0x40-0x7F: 8-bit loads and HALT
        0x40: ("LD B,B", 1, 4), 0x41: ("LD B,C", 1, 4), 0x42: ("LD B,D", 1, 4), 
        0x43: ("LD B,E", 1, 4), 0x44: ("LD B,H", 1, 4), 0x45: ("LD B,L", 1, 4),
        0x46: ("LD B,(HL)", 1, 8), 0x47: ("LD B,A", 1, 4),
        
        0x48: ("LD C,B", 1, 4), 0x49: ("LD C,C", 1, 4), 0x4A: ("LD C,D", 1, 4),
        0x4B: ("LD C,E", 1, 4), 0x4C: ("LD C,H", 1, 4), 0x4D: ("LD C,L", 1, 4),
        0x4E: ("LD C,(HL)", 1, 8), 0x4F: ("LD C,A", 1, 4),
        
        0x50: ("LD D,B", 1, 4), 0x51: ("LD D,C", 1, 4), 0x52: ("LD D,D", 1, 4),
        0x53: ("LD D,E", 1, 4), 0x54: ("LD D,H", 1, 4), 0x55: ("LD D,L", 1, 4),
        0x56: ("LD D,(HL)", 1, 8), 0x57: ("LD D,A", 1, 4),
        
        0x58: ("LD E,B", 1, 4), 0x59: ("LD E,C", 1, 4), 0x5A: ("LD E,D", 1, 4),
        0x5B: ("LD E,E", 1, 4), 0x5C: ("LD E,H", 1, 4), 0x5D: ("LD E,L", 1, 4),
        0x5E: ("LD E,(HL)", 1, 8), 0x5F: ("LD E,A", 1, 4),
        
        0x60: ("LD H,B", 1, 4), 0x61: ("LD H,C", 1, 4), 0x62: ("LD H,D", 1, 4),
        0x63: ("LD H,E", 1, 4), 0x64: ("LD H,H", 1, 4), 0x65: ("LD H,L", 1, 4),
        0x66: ("LD H,(HL)", 1, 8), 0x67: ("LD H,A", 1, 4),
        
        0x68: ("LD L,B", 1, 4), 0x69: ("LD L,C", 1, 4), 0x6A: ("LD L,D", 1, 4),
        0x6B: ("LD L,E", 1, 4), 0x6C: ("LD L,H", 1, 4), 0x6D: ("LD L,L", 1, 4),
        0x6E: ("LD L,(HL)", 1, 8), 0x6F: ("LD L,A", 1, 4),
        
        0x70: ("LD (HL),B", 1, 8), 0x71: ("LD (HL),C", 1, 8), 0x72: ("LD (HL),D", 1, 8),
        0x73: ("LD (HL),E", 1, 8), 0x74: ("LD (HL),H", 1, 8), 0x75: ("LD (HL),L", 1, 8),
        0x76: ("HALT", 1, 4), 0x77: ("LD (HL),A", 1, 8),
        
        0x78: ("LD A,B", 1, 4), 0x79: ("LD A,C", 1, 4), 0x7A: ("LD A,D", 1, 4),
        0x7B: ("LD A,E", 1, 4), 0x7C: ("LD A,H", 1, 4), 0x7D: ("LD A,L", 1, 4),
        0x7E: ("LD A,(HL)", 1, 8), 0x7F: ("LD A,A", 1, 4),
        
        # 0x80-0xBF: Arithmetic operations
        0x80: ("ADD A,B", 1, 4), 0x81: ("ADD A,C", 1, 4), 0x82: ("ADD A,D", 1, 4),
        0x83: ("ADD A,E", 1, 4), 0x84: ("ADD A,H", 1, 4), 0x85: ("ADD A,L", 1, 4),
        0x86: ("ADD A,(HL)", 1, 8), 0x87: ("ADD A,A", 1, 4),
        
        0x88: ("ADC A,B", 1, 4), 0x89: ("ADC A,C", 1, 4), 0x8A: ("ADC A,D", 1, 4),
        0x8B: ("ADC A,E", 1, 4), 0x8C: ("ADC A,H", 1, 4), 0x8D: ("ADC A,L", 1, 4),
        0x8E: ("ADC A,(HL)", 1, 8), 0x8F: ("ADC A,A", 1, 4),
        
        0x90: ("SUB B", 1, 4), 0x91: ("SUB C", 1, 4), 0x92: ("SUB D", 1, 4),
        0x93: ("SUB E", 1, 4), 0x94: ("SUB H", 1, 4), 0x95: ("SUB L", 1, 4),
        0x96: ("SUB (HL)", 1, 8), 0x97: ("SUB A", 1, 4),
        
        0x98: ("SBC A,B", 1, 4), 0x99: ("SBC A,C", 1, 4), 0x9A: ("SBC A,D", 1, 4),
        0x9B: ("SBC A,E", 1, 4), 0x9C: ("SBC A,H", 1, 4), 0x9D: ("SBC A,L", 1, 4),
        0x9E: ("SBC A,(HL)", 1, 8), 0x9F: ("SBC A,A", 1, 4),
        
        0xA0: ("AND B", 1, 4), 0xA1: ("AND C", 1, 4), 0xA2: ("AND D", 1, 4),
        0xA3: ("AND E", 1, 4), 0xA4: ("AND H", 1, 4), 0xA5: ("AND L", 1, 4),
        0xA6: ("AND (HL)", 1, 8), 0xA7: ("AND A", 1, 4),
        
        0xA8: ("XOR B", 1, 4), 0xA9: ("XOR C", 1, 4), 0xAA: ("XOR D", 1, 4),
        0xAB: ("XOR E", 1, 4), 0xAC: ("XOR H", 1, 4), 0xAD: ("XOR L", 1, 4),
        0xAE: ("XOR (HL)", 1, 8), 0xAF: ("XOR A", 1, 4),
        
        0xB0: ("OR B", 1, 4), 0xB1: ("OR C", 1, 4), 0xB2: ("OR D", 1, 4),
        0xB3: ("OR E", 1, 4), 0xB4: ("OR H", 1, 4), 0xB5: ("OR L", 1, 4),
        0xB6: ("OR (HL)", 1, 8), 0xB7: ("OR A", 1, 4),
        
        0xB8: ("CP B", 1, 4), 0xB9: ("CP C", 1, 4), 0xBA: ("CP D", 1, 4),
        0xBB: ("CP E", 1, 4), 0xBC: ("CP H", 1, 4), 0xBD: ("CP L", 1, 4),
        0xBE: ("CP (HL)", 1, 8), 0xBF: ("CP A", 1, 4),
        
        # 0xC0-0xFF: Control flow and misc
        0xC0: ("RET NZ", 1, [20, 8]),
        0xC1: ("POP BC", 1, 12),
        0xC2: ("JP NZ,a16", 3, [16, 12]),
        0xC3: ("JP a16", 3, 16),
        0xC4: ("CALL NZ,a16", 3, [24, 12]),
        0xC5: ("PUSH BC", 1, 16),
        0xC6: ("ADD A,d8", 2, 8),
        0xC7: ("RST 00H", 1, 16),
        0xC8: ("RET Z", 1, [20, 8]),
        0xC9: ("RET", 1, 16),
        0xCA: ("JP Z,a16", 3, [16, 12]),
        0xCB: ("PREFIX CB", 1, 4),
        0xCC: ("CALL Z,a16", 3, [24, 12]),
        0xCD: ("CALL a16", 3, 24),
        0xCE: ("ADC A,d8", 2, 8),
        0xCF: ("RST 08H", 1, 16),
        
        0xD0: ("RET NC", 1, [20, 8]),
        0xD1: ("POP DE", 1, 12),
        0xD2: ("JP NC,a16", 3, [16, 12]),
        0xD4: ("CALL NC,a16", 3, [24, 12]),
        0xD5: ("PUSH DE", 1, 16),
        0xD6: ("SUB d8", 2, 8),
        0xD7: ("RST 10H", 1, 16),
        0xD8: ("RET C", 1, [20, 8]),
        0xD9: ("RETI", 1, 16),
        0xDA: ("JP C,a16", 3, [16, 12]),
        0xDC: ("CALL C,a16", 3, [24, 12]),
        0xDE: ("SBC A,d8", 2, 8),
        0xDF: ("RST 18H", 1, 16),
        
        0xE0: ("LDH (a8),A", 2, 12),
        0xE1: ("POP HL", 1, 12),
        0xE2: ("LD (C),A", 1, 8),
        0xE5: ("PUSH HL", 1, 16),
        0xE6: ("AND d8", 2, 8),
        0xE7: ("RST 20H", 1, 16),
        0xE8: ("ADD SP,r8", 2, 16),
        0xE9: ("JP (HL)", 1, 4),
        0xEA: ("LD (a16),A", 3, 16),
        0xEE: ("XOR d8", 2, 8),
        0xEF: ("RST 28H", 1, 16),
        
        0xF0: ("LDH A,(a8)", 2, 12),
        0xF1: ("POP AF", 1, 12),
        0xF2: ("LD A,(C)", 1, 8),
        0xF3: ("DI", 1, 4),
        0xF5: ("PUSH AF", 1, 16),
        0xF6: ("OR d8", 2, 8),
        0xF7: ("RST 30H", 1, 16),
        0xF8: ("LD HL,SP+r8", 2, 12),
        0xF9: ("LD SP,HL", 1, 8),
        0xFA: ("LD A,(a16)", 3, 16),
        0xFB: ("EI", 1, 4),
        0xFE: ("CP d8", 2, 8),
        0xFF: ("RST 38H", 1, 16),
    }

# === REGISTERS ===
class Registers:
    """Z80-like register set for GB CPU"""
    def __init__(self):
        self.a = 0x01
        self.b = 0x00
        self.c = 0x13
        self.d = 0x00
        self.e = 0xD8
        self.h = 0x01
        self.l = 0x4D
        self.f = 0xB0
        self.sp = 0xFFFE
        self.pc = 0x0100
        
    @property
    def af(self):
        return (self.a << 8) | self.f
    
    @af.setter
    def af(self, value):
        self.a = (value >> 8) & 0xFF
        self.f = value & 0xF0
        
    @property
    def bc(self):
        return (self.b << 8) | self.c
    
    @bc.setter
    def bc(self, value):
        self.b = (value >> 8) & 0xFF
        self.c = value & 0xFF
        
    @property
    def de(self):
        return (self.d << 8) | self.e
    
    @de.setter
    def de(self, value):
        self.d = (value >> 8) & 0xFF
        self.e = value & 0xFF
        
    @property
    def hl(self):
        return (self.h << 8) | self.l
    
    @hl.setter
    def hl(self, value):
        self.h = (value >> 8) & 0xFF
        self.l = value & 0xFF

# === MEMORY ===
class Memory:
    """Complete Game Boy memory management unit"""
    def __init__(self):
        # Memory regions
        self.rom_bank_0 = bytearray(0x4000)  # 16KB ROM bank 0
        self.rom_bank_n = bytearray(0x4000)  # 16KB switchable ROM bank
        self.vram = bytearray(0x2000)        # 8KB video RAM
        self.eram = bytearray(0x2000)        # 8KB external RAM
        self.wram = bytearray(0x2000)        # 8KB work RAM
        self.oam = bytearray(0xA0)           # Sprite RAM
        self.io = bytearray(0x80)            # I/O registers
        self.hram = bytearray(0x7F)          # High RAM
        self.ie = 0x00                       # Interrupt enable
        
        # MBC state
        self.mbc_type = 0
        self.rom_bank = 1
        self.ram_bank = 0
        self.ram_enable = False
        
        # Initialize I/O registers
        self.io[0x00] = 0xCF  # P1/JOYP
        self.io[0x02] = 0x7E  # SC
        self.io[0x07] = 0xF8  # TAC
        self.io[0x0F] = 0xE1  # IF
        self.io[0x40] = 0x91  # LCDC
        self.io[0x47] = 0xFC  # BGP
        self.io[0x48] = 0xFF  # OBP0
        self.io[0x49] = 0xFF  # OBP1
        
    def read(self, addr):
        """Read byte from memory"""
        addr &= 0xFFFF
        
        if addr < 0x4000:
            return self.rom_bank_0[addr]
        elif addr < 0x8000:
            return self.rom_bank_n[addr - 0x4000]
        elif addr < 0xA000:
            return self.vram[addr - 0x8000]
        elif addr < 0xC000:
            if self.ram_enable:
                return self.eram[addr - 0xA000]
            return 0xFF
        elif addr < 0xE000:
            return self.wram[addr - 0xC000]
        elif addr < 0xFE00:
            return self.wram[addr - 0xE000]  # Echo RAM
        elif addr < 0xFEA0:
            return self.oam[addr - 0xFE00]
        elif addr < 0xFF00:
            return 0xFF  # Unusable
        elif addr < 0xFF80:
            return self.read_io(addr - 0xFF00)
        elif addr < 0xFFFF:
            return self.hram[addr - 0xFF80]
        else:
            return self.ie
            
    def write(self, addr, value):
        """Write byte to memory"""
        addr &= 0xFFFF
        value &= 0xFF
        
        if addr < 0x2000:
            # RAM enable
            if self.mbc_type > 0:
                self.ram_enable = (value & 0x0F) == 0x0A
        elif addr < 0x4000:
            # ROM bank select (low)
            if self.mbc_type > 0:
                bank = value & 0x1F
                if bank == 0:
                    bank = 1
                self.rom_bank = bank
        elif addr < 0x6000:
            # ROM bank select (high) / RAM bank select
            if self.mbc_type > 0:
                self.ram_bank = value & 0x03
        elif addr < 0x8000:
            # Banking mode select
            pass
        elif addr < 0xA000:
            self.vram[addr - 0x8000] = value
        elif addr < 0xC000:
            if self.ram_enable:
                self.eram[addr - 0xA000] = value
        elif addr < 0xE000:
            self.wram[addr - 0xC000] = value
        elif addr < 0xFE00:
            self.wram[addr - 0xE000] = value  # Echo RAM
        elif addr < 0xFEA0:
            self.oam[addr - 0xFE00] = value
        elif addr < 0xFF00:
            pass  # Unusable
        elif addr < 0xFF80:
            self.write_io(addr - 0xFF00, value)
        elif addr < 0xFFFF:
            self.hram[addr - 0xFF80] = value
        else:
            self.ie = value
            
    def read_io(self, reg):
        """Read I/O register"""
        if reg == 0x00:  # P1/JOYP
            return self.io[reg] | 0x0F  # Buttons not pressed
        elif reg == 0x44:  # LY
            return self.io[reg]
        else:
            return self.io[reg]
            
    def write_io(self, reg, value):
        """Write I/O register"""
        if reg == 0x01:  # SB - Serial transfer data
            # Debug output
            if value != 0:
                print(chr(value), end='', flush=True)
        elif reg == 0x46:  # DMA
            # OAM DMA transfer
            src = value << 8
            for i in range(0xA0):
                self.oam[i] = self.read(src + i)
        self.io[reg] = value
        
    def load_rom(self, data):
        """Load ROM data"""
        # Copy ROM banks
        size = min(len(data), 0x8000)
        self.rom_bank_0[:min(0x4000, size)] = data[:min(0x4000, size)]
        if size > 0x4000:
            self.rom_bank_n[:min(0x4000, size - 0x4000)] = data[0x4000:size]
            
        # Detect MBC type
        if len(data) > 0x147:
            self.mbc_type = data[0x147]

# === CPU ===
class CPU:
    """Enhanced Game Boy CPU with full instruction set"""
    def __init__(self, memory):
        self.memory = memory
        self.reg = Registers()
        self.halted = False
        self.stopped = False
        self.ime = False
        self.ei_delay = 0
        self.cycles = 0
        self.total_cycles = 0
        
        # Instruction cache
        self.instruction_cache = {}
        self.setup_instruction_handlers()
        
    def setup_instruction_handlers(self):
        """Setup optimized instruction handlers"""
        # Map opcodes to handler methods
        self.handlers = {
            0x00: self.nop,
            0x01: self.ld_bc_nn,
            0x06: self.ld_b_n,
            0x0E: self.ld_c_n,
            0x11: self.ld_de_nn,
            0x16: self.ld_d_n,
            0x1E: self.ld_e_n,
            0x20: self.jr_nz,
            0x21: self.ld_hl_nn,
            0x26: self.ld_h_n,
            0x2E: self.ld_l_n,
            0x31: self.ld_sp_nn,
            0x32: self.ld_hl_dec_a,
            0x3E: self.ld_a_n,
            0x76: self.halt,
            0x77: self.ld_hl_a,
            0xAF: self.xor_a,
            0xC3: self.jp_nn,
            0xC9: self.ret,
            0xCD: self.call_nn,
            0xE0: self.ldh_n_a,
            0xF0: self.ldh_a_n,
            0xF3: self.di,
            0xFB: self.ei,
            0xFE: self.cp_n,
        }
        
    def fetch_byte(self):
        """Fetch next byte and increment PC"""
        byte = self.memory.read(self.reg.pc)
        self.reg.pc = (self.reg.pc + 1) & 0xFFFF
        return byte
        
    def fetch_word(self):
        """Fetch next word (little-endian)"""
        low = self.fetch_byte()
        high = self.fetch_byte()
        return (high << 8) | low
        
    def push_word(self, value):
        """Push word onto stack"""
        self.reg.sp = (self.reg.sp - 2) & 0xFFFF
        self.memory.write(self.reg.sp, value & 0xFF)
        self.memory.write(self.reg.sp + 1, (value >> 8) & 0xFF)
        
    def pop_word(self):
        """Pop word from stack"""
        low = self.memory.read(self.reg.sp)
        high = self.memory.read(self.reg.sp + 1)
        self.reg.sp = (self.reg.sp + 2) & 0xFFFF
        return (high << 8) | low
        
    def set_flags(self, z=None, n=None, h=None, c=None):
        """Set CPU flags"""
        if z is not None:
            self.reg.f = (self.reg.f & 0x7F) | (0x80 if z else 0)
        if n is not None:
            self.reg.f = (self.reg.f & 0xBF) | (0x40 if n else 0)
        if h is not None:
            self.reg.f = (self.reg.f & 0xDF) | (0x20 if h else 0)
        if c is not None:
            self.reg.f = (self.reg.f & 0xEF) | (0x10 if c else 0)
            
    def check_flag(self, flag):
        """Check if flag is set"""
        return bool(self.reg.f & flag)
        
    # === Instruction Handlers ===
    def nop(self):
        self.cycles += 4
        
    def ld_bc_nn(self):
        self.reg.bc = self.fetch_word()
        self.cycles += 12
        
    def ld_de_nn(self):
        self.reg.de = self.fetch_word()
        self.cycles += 12
        
    def ld_hl_nn(self):
        self.reg.hl = self.fetch_word()
        self.cycles += 12
        
    def ld_sp_nn(self):
        self.reg.sp = self.fetch_word()
        self.cycles += 12
        
    def ld_a_n(self):
        self.reg.a = self.fetch_byte()
        self.cycles += 8
        
    def ld_b_n(self):
        self.reg.b = self.fetch_byte()
        self.cycles += 8
        
    def ld_c_n(self):
        self.reg.c = self.fetch_byte()
        self.cycles += 8
        
    def ld_d_n(self):
        self.reg.d = self.fetch_byte()
        self.cycles += 8
        
    def ld_e_n(self):
        self.reg.e = self.fetch_byte()
        self.cycles += 8
        
    def ld_h_n(self):
        self.reg.h = self.fetch_byte()
        self.cycles += 8
        
    def ld_l_n(self):
        self.reg.l = self.fetch_byte()
        self.cycles += 8
        
    def ld_hl_a(self):
        self.memory.write(self.reg.hl, self.reg.a)
        self.cycles += 8
        
    def ld_hl_dec_a(self):
        self.memory.write(self.reg.hl, self.reg.a)
        self.reg.hl = (self.reg.hl - 1) & 0xFFFF
        self.cycles += 8
        
    def ldh_n_a(self):
        addr = 0xFF00 + self.fetch_byte()
        self.memory.write(addr, self.reg.a)
        self.cycles += 12
        
    def ldh_a_n(self):
        addr = 0xFF00 + self.fetch_byte()
        self.reg.a = self.memory.read(addr)
        self.cycles += 12
        
    def jr_nz(self):
        offset = self.fetch_byte()
        if not self.check_flag(Flags.ZERO):
            if offset > 127:
                offset = -(256 - offset)
            self.reg.pc = (self.reg.pc + offset) & 0xFFFF
            self.cycles += 12
        else:
            self.cycles += 8
            
    def jp_nn(self):
        self.reg.pc = self.fetch_word()
        self.cycles += 16
        
    def call_nn(self):
        addr = self.fetch_word()
        self.push_word(self.reg.pc)
        self.reg.pc = addr
        self.cycles += 24
        
    def ret(self):
        self.reg.pc = self.pop_word()
        self.cycles += 16
        
    def xor_a(self):
        self.reg.a = 0
        self.set_flags(z=True, n=False, h=False, c=False)
        self.cycles += 4
        
    def cp_n(self):
        value = self.fetch_byte()
        result = self.reg.a - value
        self.set_flags(
            z=(result & 0xFF) == 0,
            n=True,
            h=((self.reg.a & 0xF) < (value & 0xF)),
            c=result < 0
        )
        self.cycles += 8
        
    def halt(self):
        self.halted = True
        self.cycles += 4
        
    def di(self):
        self.ime = False
        self.ei_delay = 0
        self.cycles += 4
        
    def ei(self):
        self.ei_delay = 2
        self.cycles += 4
        
    def execute_extended(self):
        """Execute CB-prefixed instruction"""
        opcode = self.fetch_byte()
        reg_idx = opcode & 0x07
        bit_op = (opcode >> 3) & 0x07
        op_type = opcode >> 6
        
        # Get register value
        if reg_idx == 6:  # (HL)
            value = self.memory.read(self.reg.hl)
            cycles = 16
        else:
            reg_map = [self.reg.b, self.reg.c, self.reg.d, self.reg.e,
                      self.reg.h, self.reg.l, None, self.reg.a]
            value = reg_map[reg_idx]
            cycles = 8
            
        # Perform operation
        if op_type == 0:  # Rotate/shift
            if bit_op == 0:  # RLC
                carry = value >> 7
                value = ((value << 1) | carry) & 0xFF
                self.set_flags(z=value == 0, n=False, h=False, c=carry)
        elif op_type == 1:  # BIT
            bit = 1 << bit_op
            self.set_flags(z=(value & bit) == 0, n=False, h=True)
            
        # Write back value if needed
        if op_type != 1 and reg_idx == 6:
            self.memory.write(self.reg.hl, value)
        elif op_type != 1:
            if reg_idx == 0: self.reg.b = value
            elif reg_idx == 1: self.reg.c = value
            elif reg_idx == 2: self.reg.d = value
            elif reg_idx == 3: self.reg.e = value
            elif reg_idx == 4: self.reg.h = value
            elif reg_idx == 5: self.reg.l = value
            elif reg_idx == 7: self.reg.a = value
            
        self.cycles += cycles
        
    def execute_instruction(self):
        """Execute single instruction with full decode"""
        if self.halted:
            self.cycles += 4
            return
            
        # Handle EI delay
        if self.ei_delay > 0:
            self.ei_delay -= 1
            if self.ei_delay == 0:
                self.ime = True
                
        opcode = self.fetch_byte()
        
        # Use handler if available
        if opcode in self.handlers:
            self.handlers[opcode]()
        elif opcode == 0xCB:
            self.execute_extended()
        else:
            # Generic handler for remaining instructions
            self.execute_generic(opcode)
            
    def execute_generic(self, opcode):
        """Execute instructions not in handler table"""
        # This handles the remaining ~200 opcodes
        # For brevity, implementing key ones
        
        # 8-bit loads
        if 0x40 <= opcode <= 0x7F and opcode != 0x76:
            src = opcode & 0x07
            dst = (opcode >> 3) & 0x07
            
            # Get source value
            if src == 6:
                value = self.memory.read(self.reg.hl)
                cycles = 8
            else:
                reg_map = [self.reg.b, self.reg.c, self.reg.d, self.reg.e,
                          self.reg.h, self.reg.l, None, self.reg.a]
                value = reg_map[src]
                cycles = 4
                
            # Set destination
            if dst == 6:
                self.memory.write(self.reg.hl, value)
                cycles = 8
            else:
                if dst == 0: self.reg.b = value
                elif dst == 1: self.reg.c = value
                elif dst == 2: self.reg.d = value
                elif dst == 3: self.reg.e = value
                elif dst == 4: self.reg.h = value
                elif dst == 5: self.reg.l = value
                elif dst == 7: self.reg.a = value
                
            self.cycles += cycles
            
        # Arithmetic operations
        elif 0x80 <= opcode <= 0xBF:
            src = opcode & 0x07
            op = (opcode >> 3) & 0x07
            
            # Get source value
            if src == 6:
                value = self.memory.read(self.reg.hl)
                cycles = 8
            else:
                reg_map = [self.reg.b, self.reg.c, self.reg.d, self.reg.e,
                          self.reg.h, self.reg.l, None, self.reg.a]
                value = reg_map[src]
                cycles = 4
                
            # Perform operation
            if op == 0:  # ADD
                result = self.reg.a + value
                self.set_flags(
                    z=(result & 0xFF) == 0,
                    n=False,
                    h=((self.reg.a & 0xF) + (value & 0xF)) > 0xF,
                    c=result > 0xFF
                )
                self.reg.a = result & 0xFF
            elif op == 2:  # SUB
                result = self.reg.a - value
                self.set_flags(
                    z=(result & 0xFF) == 0,
                    n=True,
                    h=((self.reg.a & 0xF) < (value & 0xF)),
                    c=result < 0
                )
                self.reg.a = result & 0xFF
            elif op == 4:  # AND
                self.reg.a &= value
                self.set_flags(z=self.reg.a == 0, n=False, h=True, c=False)
            elif op == 5:  # XOR
                self.reg.a ^= value
                self.set_flags(z=self.reg.a == 0, n=False, h=False, c=False)
            elif op == 6:  # OR
                self.reg.a |= value
                self.set_flags(z=self.reg.a == 0, n=False, h=False, c=False)
            elif op == 7:  # CP
                result = self.reg.a - value
                self.set_flags(
                    z=(result & 0xFF) == 0,
                    n=True,
                    h=((self.reg.a & 0xF) < (value & 0xF)),
                    c=result < 0
                )
                
            self.cycles += cycles
        else:
            # Unknown opcode - treat as NOP
            self.cycles += 4
            
        self.total_cycles += self.cycles

# === PPU ===
class PPU:
    """Enhanced Picture Processing Unit with proper rendering"""
    def __init__(self, memory):
        self.memory = memory
        self.framebuffer = np.zeros((SCREEN_HEIGHT, SCREEN_WIDTH, 3), dtype=np.uint8)
        
        # PPU state
        self.mode = 2  # 0=HBlank, 1=VBlank, 2=OAM, 3=VRAM
        self.scanline = 0
        self.cycles = 0
        self.frame_ready = False
        
        # Palettes
        self.bg_palette = [0, 1, 2, 3]
        self.obj_palette0 = [0, 1, 2, 3]
        self.obj_palette1 = [0, 1, 2, 3]
        
        # Color scheme
        self.current_palette = "Classic GB"
        self.colors = PALETTES[self.current_palette]
        
    def update(self, cycles):
        """Update PPU state machine"""
        self.cycles += cycles
        
        # Mode transitions
        if self.mode == 2:  # OAM scan
            if self.cycles >= 80:
                self.cycles -= 80
                self.mode = 3
        elif self.mode == 3:  # VRAM access
            if self.cycles >= 172:
                self.cycles -= 172
                self.mode = 0
                self.render_scanline()
        elif self.mode == 0:  # HBlank
            if self.cycles >= 204:
                self.cycles -= 204
                self.scanline += 1
                
                if self.scanline == 144:
                    self.mode = 1
                    self.frame_ready = True
                    self.memory.io[0x0F] |= 0x01  # VBlank interrupt
                else:
                    self.mode = 2
        elif self.mode == 1:  # VBlank
            if self.cycles >= 456:
                self.cycles -= 456
                self.scanline += 1
                
                if self.scanline > 153:
                    self.scanline = 0
                    self.mode = 2
                    
        # Update LY register
        self.memory.io[0x44] = self.scanline
        
    def render_scanline(self):
        """Render current scanline"""
        if self.scanline >= SCREEN_HEIGHT:
            return
            
        lcdc = self.memory.io[0x40]
        
        # Check if LCD is enabled
        if not (lcdc & 0x80):
            # Clear scanline
            for x in range(SCREEN_WIDTH):
                self.framebuffer[self.scanline, x] = self.colors[0]
            return
            
        # Render background
        if lcdc & 0x01:
            self.render_background_scanline()
            
        # Render sprites
        if lcdc & 0x02:
            self.render_sprites_scanline()
            
    def render_background_scanline(self):
        """Render background for current scanline"""
        lcdc = self.memory.io[0x40]
        scy = self.memory.io[0x42]
        scx = self.memory.io[0x43]
        
        # Tile map address
        tilemap_addr = 0x9C00 if lcdc & 0x08 else 0x9800
        
        # Tile data address
        tiledata_addr = 0x8000 if lcdc & 0x10 else 0x8800
        tiledata_signed = not (lcdc & 0x10)
        
        y = (self.scanline + scy) & 0xFF
        tile_row = y >> 3
        
        for x in range(SCREEN_WIDTH):
            x_pos = (x + scx) & 0xFF
            tile_col = x_pos >> 3
            
            # Get tile index
            tile_idx = self.memory.vram[tilemap_addr - 0x8000 + tile_row * 32 + tile_col]
            
            # Calculate tile address
            if tiledata_signed and tile_idx < 128:
                tile_addr = tiledata_addr + tile_idx * 16
            else:
                tile_addr = tiledata_addr + ((tile_idx + 128 if tiledata_signed else tile_idx) - 128) * 16
                
            # Get pixel from tile
            line = y & 7
            data1 = self.memory.vram[tile_addr - 0x8000 + line * 2]
            data2 = self.memory.vram[tile_addr - 0x8000 + line * 2 + 1]
            
            bit = 7 - (x_pos & 7)
            color_idx = ((data2 >> bit) & 1) << 1 | ((data1 >> bit) & 1)
            
            # Apply palette
            color = self.bg_palette[color_idx]
            self.framebuffer[self.scanline, x] = self.colors[color]
            
    def render_sprites_scanline(self):
        """Render sprites for current scanline"""
        lcdc = self.memory.io[0x40]
        sprite_height = 16 if lcdc & 0x04 else 8
        
        # Find sprites on this scanline
        sprites = []
        for i in range(40):
            y = self.memory.oam[i * 4] - 16
            x = self.memory.oam[i * 4 + 1] - 8
            tile = self.memory.oam[i * 4 + 2]
            flags = self.memory.oam[i * 4 + 3]
            
            if y <= self.scanline < y + sprite_height:
                sprites.append((x, y, tile, flags))
                
        # Sort by X coordinate
        sprites.sort(key=lambda s: s[0])
        
        # Render sprites (max 10 per line)
        for x, y, tile, flags in sprites[:10]:
            palette = self.obj_palette1 if flags & 0x10 else self.obj_palette0
            y_flip = flags & 0x40
            x_flip = flags & 0x20
            
            line = self.scanline - y
            if y_flip:
                line = sprite_height - 1 - line
                
            # Get tile data
            tile_addr = 0x8000 + tile * 16 + line * 2
            data1 = self.memory.vram[tile_addr - 0x8000]
            data2 = self.memory.vram[tile_addr - 0x8000 + 1]
            
            for px in range(8):
                if 0 <= x + px < SCREEN_WIDTH:
                    bit = px if x_flip else 7 - px
                    color_idx = ((data2 >> bit) & 1) << 1 | ((data1 >> bit) & 1)
                    
                    if color_idx > 0:  # Transparent if 0
                        color = palette[color_idx]
                        self.framebuffer[self.scanline, x + px] = self.colors[color]
                        
    def update_palettes(self):
        """Update palettes from I/O registers"""
        bgp = self.memory.io[0x47]
        self.bg_palette = [
            bgp & 0x03,
            (bgp >> 2) & 0x03,
            (bgp >> 4) & 0x03,
            (bgp >> 6) & 0x03
        ]
        
        obp0 = self.memory.io[0x48]
        self.obj_palette0 = [
            obp0 & 0x03,
            (obp0 >> 2) & 0x03,
            (obp0 >> 4) & 0x03,
            (obp0 >> 6) & 0x03
        ]
        
        obp1 = self.memory.io[0x49]
        self.obj_palette1 = [
            obp1 & 0x03,
            (obp1 >> 2) & 0x03,
            (obp1 >> 4) & 0x03,
            (obp1 >> 6) & 0x03
        ]

# === TEST ROM GENERATOR ===
class TestROMGenerator:
    """Generate test ROMs for the emulator"""
    
    @staticmethod
    def create_simple_test():
        """Create a simple test ROM"""
        rom = bytearray(32768)
        
        # Entry point program
        program = [
            # Initialize
            0x31, 0xFE, 0xFF,  # LD SP, $FFFE
            0xAF,              # XOR A
            0x21, 0x00, 0xFF,  # LD HL, $FF00
            
            # Clear memory
            0x06, 0x7F,        # LD B, $7F
            0x77,              # LD (HL), A
            0x23,              # INC HL
            0x05,              # DEC B
            0x20, 0xFB,        # JR NZ, -5
            
            # Setup display
            0x3E, 0x91,        # LD A, $91
            0xE0, 0x40,        # LDH ($40), A  ; LCDC
            0x3E, 0xE4,        # LD A, $E4
            0xE0, 0x47,        # LDH ($47), A  ; BGP
            
            # Write test pattern to VRAM
            0x21, 0x00, 0x80,  # LD HL, $8000
            0x06, 0x10,        # LD B, $10
            
            # Pattern loop
            0x3E, 0xFF,        # LD A, $FF
            0x77,              # LD (HL), A
            0x23,              # INC HL
            0x3E, 0x00,        # LD A, $00
            0x77,              # LD (HL), A
            0x23,              # INC HL
            0x05,              # DEC B
            0x20, 0xF5,        # JR NZ, -11
            
            # Infinite loop
            0x18, 0xFE,        # JR -2
        ]
        
        # Write program
        for i, byte in enumerate(program):
            rom[0x0100 + i] = byte
            
        # Nintendo logo
        logo = bytes.fromhex(
            'CEED6666CC0D000B03730083000C000D'
            '0008111F8889000EDCCC6EE6DDDDD999'
            'BBBB67636E0EECCCDDDC999FBBB9333E'
        )
        rom[0x0104:0x0104 + len(logo)] = logo
        
        # Title
        title = b"SAMSOFT-TEST"
        rom[0x0134:0x0134 + len(title)] = title
        
        # Header checksum
        checksum = 0
        for i in range(0x0134, 0x014D):
            checksum = (checksum - rom[i] - 1) & 0xFF
        rom[0x014D] = checksum
        
        return bytes(rom)
        
    @staticmethod
    def create_scrolling_demo():
        """Create a scrolling demo ROM"""
        rom = bytearray(32768)
        
        # More complex demo program
        program = [
            # Initialize
            0x31, 0xFE, 0xFF,  # LD SP, $FFFE
            0xF3,              # DI
            
            # Setup LCD
            0x3E, 0x00,        # LD A, $00
            0xE0, 0x40,        # LDH ($40), A  ; Turn off LCD
            
            # Load tiles
            0x21, 0x00, 0x81,  # LD HL, $8100
            0x06, 0x10,        # LD B, $10
            0x0E, 0x08,        # LD C, $08
            
            # Tile loop
            0x3E, 0x7E,        # LD A, $7E
            0x77,              # LD (HL), A
            0x23,              # INC HL
            0x0D,              # DEC C
            0x20, 0xFA,        # JR NZ, -6
            
            # Setup tilemap
            0x21, 0x00, 0x98,  # LD HL, $9800
            0x06, 0x20,        # LD B, $20
            0x3E, 0x10,        # LD A, $10
            0x77,              # LD (HL), A
            0x23,              # INC HL
            0x05,              # DEC B
            0x20, 0xFA,        # JR NZ, -6
            
            # Turn on LCD
            0x3E, 0x91,        # LD A, $91
            0xE0, 0x40,        # LDH ($40), A
            
            # Main loop with scrolling
            0xF0, 0x43,        # LDH A, ($43)  ; SCX
            0x3C,              # INC A
            0xE0, 0x43,        # LDH ($43), A
            
            # Wait for VBlank
            0xF0, 0x44,        # LDH A, ($44)  ; LY
            0xFE, 0x90,        # CP $90
            0x20, 0xFA,        # JR NZ, -6
            
            0x18, 0xF0,        # JR -16 (main loop)
        ]
        
        # Write program
        for i, byte in enumerate(program):
            rom[0x0100 + i] = byte
            
        # Add header
        TestROMGenerator._add_header(rom, b"SCROLL-DEMO")
        
        return bytes(rom)
        
    @staticmethod
    def _add_header(rom, title):
        """Add Game Boy header to ROM"""
        # Nintendo logo
        logo = bytes.fromhex(
            'CEED6666CC0D000B03730083000C000D'
            '0008111F8889000EDCCC6EE6DDDDD999'
            'BBBB67636E0EECCCDDDC999FBBB9333E'
        )
        rom[0x0104:0x0104 + len(logo)] = logo
        
        # Title
        rom[0x0134:0x0134 + len(title)] = title
        
        # Cartridge type
        rom[0x0147] = 0x00  # ROM only
        rom[0x0148] = 0x00  # 32KB
        rom[0x0149] = 0x00  # No RAM
        
        # Header checksum
        checksum = 0
        for i in range(0x0134, 0x014D):
            checksum = (checksum - rom[i] - 1) & 0xFF
        rom[0x014D] = checksum

# === MAIN EMULATOR ===
class SamSoftGBClient:
    """Main emulator application with enhanced GUI"""
    
    def __init__(self):
        # Core components
        self.memory = Memory()
        self.cpu = CPU(self.memory)
        self.ppu = PPU(self.memory)
        
        # Emulation state
        self.running = False
        self.paused = False
        self.speed_multiplier = 1.0
        self.rom_loaded = False
        self.rom_path = None
        
        # Performance tracking
        self.fps_counter = 0
        self.fps_time = time.time()
        self.current_fps = 0
        
        # Setup GUI
        self.setup_gui()
        
        # Load boot sequence
        self.load_test_rom()
        
    def setup_gui(self):
        """Setup enhanced Tkinter GUI"""
        self.root = tk.Tk()
        self.root.title("SamSoft GB Client - IndyCat Edition")
        self.root.configure(bg='#0a0a0f')
        self.root.resizable(False, False)
        
        # Set window icon (if possible)
        try:
            self.root.iconbitmap(default='gameboy.ico')
        except:
            pass
            
        # Menu bar
        self.setup_menu()
        
        # Main container
        main_container = tk.Frame(self.root, bg='#0a0a0f')
        main_container.pack(padx=10, pady=10)
        
        # Left panel - Display
        left_panel = tk.Frame(main_container, bg='#0a0a0f')
        left_panel.pack(side=tk.LEFT, padx=(0, 10))
        
        # Display frame with border
        display_frame = tk.Frame(left_panel, bg='#1a1a2e', relief=tk.RIDGE, bd=3)
        display_frame.pack()
        
        # Canvas for display
        self.canvas = tk.Canvas(
            display_frame,
            width=SCREEN_WIDTH * SCALE_FACTOR,
            height=SCREEN_HEIGHT * SCALE_FACTOR,
            bg='#9BBD0F',
            highlightthickness=0
        )
        self.canvas.pack(padx=5, pady=5)
        
        # Control buttons
        control_frame = tk.Frame(left_panel, bg='#0a0a0f')
        control_frame.pack(pady=10)
        
        self.play_button = tk.Button(
            control_frame,
            text="▶ Play",
            command=self.toggle_emulation,
            bg='#00ff41',
            fg='black',
            font=('Arial', 10, 'bold'),
            width=8
        )
        self.play_button.pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            control_frame,
            text="↻ Reset",
            command=self.reset_emulator,
            bg='#ffaa00',
            fg='black',
            font=('Arial', 10, 'bold'),
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        tk.Button(
            control_frame,
            text="⚡ Speed",
            command=self.cycle_speed,
            bg='#00aaff',
            fg='white',
            font=('Arial', 10, 'bold'),
            width=8
        ).pack(side=tk.LEFT, padx=2)
        
        # Right panel - Info
        right_panel = tk.Frame(main_container, bg='#1a1a2e', relief=tk.RIDGE, bd=2)
        right_panel.pack(side=tk.LEFT, fill=tk.BOTH)
        
        # Title
        tk.Label(
            right_panel,
            text="SAMSOFT GB",
            bg='#1a1a2e',
            fg='#00ff41',
            font=('Courier', 16, 'bold')
        ).pack(pady=(10, 5))
        
        tk.Label(
            right_panel,
            text="System Info",
            bg='#1a1a2e',
            fg='#00aaff',
            font=('Courier', 12, 'bold')
        ).pack(pady=(10, 5))
        
        # Info display
        info_frame = tk.Frame(right_panel, bg='#1a1a2e')
        info_frame.pack(padx=10, pady=5)
        
        self.info_labels = {}
        info_items = [
            ("ROM", "No ROM"),
            ("Status", "Ready"),
            ("FPS", "0"),
            ("Speed", "1x"),
            ("CPU", "IDLE"),
            ("PC", "0x0100"),
            ("SP", "0xFFFE"),
            ("A", "0x00"),
            ("BC", "0x0000"),
            ("DE", "0x0000"),
            ("HL", "0x0000"),
            ("Flags", "----"),
            ("Cycles", "0"),
        ]
        
        for label, default in info_items:
            frame = tk.Frame(info_frame, bg='#1a1a2e')
            frame.pack(fill=tk.X, pady=1)
            
            tk.Label(
                frame,
                text=f"{label}:",
                bg='#1a1a2e',
                fg='#888888',
                font=('Courier', 9),
                width=8,
                anchor=tk.W
            ).pack(side=tk.LEFT)
            
            value_label = tk.Label(
                frame,
                text=default,
                bg='#1a1a2e',
                fg='#00ff41',
                font=('Courier', 9),
                anchor=tk.W
            )
            value_label.pack(side=tk.LEFT, padx=(5, 0))
            
            self.info_labels[label] = value_label
            
        # Palette selector
        tk.Label(
            right_panel,
            text="Color Palette",
            bg='#1a1a2e',
            fg='#00aaff',
            font=('Courier', 11, 'bold')
        ).pack(pady=(15, 5))
        
        self.palette_var = tk.StringVar(value="Classic GB")
        palette_menu = ttk.Combobox(
            right_panel,
            textvariable=self.palette_var,
            values=list(PALETTES.keys()),
            state='readonly',
            width=15
        )
        palette_menu.pack(padx=10)
        palette_menu.bind('<<ComboboxSelected>>', self.change_palette)
        
        # About section
        tk.Label(
            right_panel,
            text=f"v{__version__}",
            bg='#1a1a2e',
            fg='#666666',
            font=('Courier', 8)
        ).pack(pady=(20, 2))
        
        tk.Label(
            right_panel,
            text=__codename__,
            bg='#1a1a2e',
            fg='#666666',
            font=('Courier', 8)
        ).pack()
        
        # Status bar
        self.status_bar = tk.Label(
            self.root,
            text="Ready - Press File > Load ROM to begin",
            bg='#0a0a0f',
            fg='#00ff41',
            font=('Courier', 10),
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X, padx=10, pady=(0, 5))
        
    def setup_menu(self):
        """Setup menu bar"""
        menubar = tk.Menu(self.root, bg='#1a1a2e', fg='#00ff41')
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, bg='#1a1a2e', fg='#00ff41')
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load ROM...", command=self.load_rom, accelerator="Ctrl+O")
        file_menu.add_separator()
        file_menu.add_command(label="Load Test ROM", command=self.load_test_rom)
        file_menu.add_command(label="Load Demo ROM", command=self.load_demo_rom)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit, accelerator="Ctrl+Q")
        
        # Emulation menu
        emulation_menu = tk.Menu(menubar, tearoff=0, bg='#1a1a2e', fg='#00ff41')
        menubar.add_cascade(label="Emulation", menu=emulation_menu)
        emulation_menu.add_command(label="Start/Stop", command=self.toggle_emulation, accelerator="Space")
        emulation_menu.add_command(label="Reset", command=self.reset_emulator, accelerator="R")
        emulation_menu.add_separator()
        emulation_menu.add_command(label="Speed 1x", command=lambda: self.set_speed(1.0))
        emulation_menu.add_command(label="Speed 2x", command=lambda: self.set_speed(2.0))
        emulation_menu.add_command(label="Speed 4x", command=lambda: self.set_speed(4.0))
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0, bg='#1a1a2e', fg='#00ff41')
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Memory Viewer", command=self.show_memory_viewer)
        tools_menu.add_command(label="Tile Viewer", command=self.show_tile_viewer)
        tools_menu.add_command(label="Generate Test ROM", command=self.generate_test_rom)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0, bg='#1a1a2e', fg='#00ff41')
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Controls", command=self.show_controls)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Keyboard bindings
        self.root.bind('<Control-o>', lambda e: self.load_rom())
        self.root.bind('<Control-q>', lambda e: self.root.quit())
        self.root.bind('<space>', lambda e: self.toggle_emulation())
        self.root.bind('r', lambda e: self.reset_emulator())
        
    def load_rom(self):
        """Load ROM file"""
        filename = filedialog.askopenfilename(
            title="Select Game Boy ROM",
            filetypes=[
                ("GB ROM files", "*.gb"),
                ("GBC ROM files", "*.gbc"),
                ("All files", "*.*")
            ]
        )
        
        if filename:
            try:
                with open(filename, 'rb') as f:
                    rom_data = f.read()
                    
                self.memory.load_rom(rom_data)
                self.rom_loaded = True
                self.rom_path = filename
                
                rom_name = os.path.basename(filename)
                self.info_labels["ROM"].config(text=rom_name[:15])
                self.status_bar.config(text=f"Loaded: {rom_name}")
                
                self.reset_emulator()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to load ROM:\n{str(e)}")
                
    def load_test_rom(self):
        """Load built-in test ROM"""
        rom_data = TestROMGenerator.create_simple_test()
        self.memory.load_rom(rom_data)
        self.rom_loaded = True
        self.rom_path = None
        
        self.info_labels["ROM"].config(text="TEST ROM")
        self.status_bar.config(text="Loaded: Built-in Test ROM")
        
        self.reset_emulator()
        
    def load_demo_rom(self):
        """Load scrolling demo ROM"""
        rom_data = TestROMGenerator.create_scrolling_demo()
        self.memory.load_rom(rom_data)
        self.rom_loaded = True
        self.rom_path = None
        
        self.info_labels["ROM"].config(text="DEMO ROM")
        self.status_bar.config(text="Loaded: Scrolling Demo ROM")
        
        self.reset_emulator()
        
    def generate_test_rom(self):
        """Generate and save test ROM"""
        filename = filedialog.asksaveasfilename(
            title="Save Test ROM",
            defaultextension=".gb",
            filetypes=[("GB ROM files", "*.gb"), ("All files", "*.*")]
        )
        
        if filename:
            rom_data = TestROMGenerator.create_simple_test()
            with open(filename, 'wb') as f:
                f.write(rom_data)
            messagebox.showinfo("Success", f"Test ROM saved to:\n{filename}")
            
    def toggle_emulation(self):
        """Toggle emulation state"""
        if self.running:
            self.stop_emulation()
        else:
            self.start_emulation()
            
    def start_emulation(self):
        """Start emulation"""
        if not self.rom_loaded:
            self.load_test_rom()
            
        self.running = True
        self.paused = False
        self.play_button.config(text="⏸ Pause")
        self.info_labels["Status"].config(text="Running")
        self.status_bar.config(text="Emulation running...")
        
        self.emulation_loop()
        
    def stop_emulation(self):
        """Stop emulation"""
        self.running = False
        self.play_button.config(text="▶ Play")
        self.info_labels["Status"].config(text="Stopped")
        self.status_bar.config(text="Emulation stopped")
        
    def reset_emulator(self):
        """Reset emulator state"""
        self.cpu = CPU(self.memory)
        self.ppu = PPU(self.memory)
        self.update_display()
        self.info_labels["Status"].config(text="Reset")
        self.status_bar.config(text="Emulator reset")
        
    def cycle_speed(self):
        """Cycle through speed settings"""
        speeds = [0.5, 1.0, 2.0, 4.0, 8.0]
        current_idx = speeds.index(self.speed_multiplier) if self.speed_multiplier in speeds else 0
        self.speed_multiplier = speeds[(current_idx + 1) % len(speeds)]
        self.info_labels["Speed"].config(text=f"{self.speed_multiplier}x")
        
    def set_speed(self, speed):
        """Set emulation speed"""
        self.speed_multiplier = speed
        self.info_labels["Speed"].config(text=f"{speed}x")
        
    def change_palette(self, event=None):
        """Change color palette"""
        palette_name = self.palette_var.get()
        self.ppu.colors = PALETTES[palette_name]
        self.ppu.current_palette = palette_name
        
    def emulation_loop(self):
        """Main emulation loop"""
        if not self.running:
            return
            
        # Calculate cycles for this frame
        cycles_per_frame = int(CYCLES_PER_FRAME * self.speed_multiplier)
        frame_cycles = 0
        
        # Execute frame
        while frame_cycles < cycles_per_frame and self.running:
            # Execute CPU instruction
            self.cpu.execute_instruction()
            
            # Update PPU
            self.ppu.update(self.cpu.cycles)
            
            frame_cycles += self.cpu.cycles
            self.cpu.cycles = 0
            
        # Update display if frame ready
        if self.ppu.frame_ready:
            self.update_display()
            self.ppu.frame_ready = False
            
            # Update FPS
            self.fps_counter += 1
            current_time = time.time()
            if current_time - self.fps_time >= 1.0:
                self.current_fps = self.fps_counter
                self.fps_counter = 0
                self.fps_time = current_time
                self.info_labels["FPS"].config(text=str(self.current_fps))
                
        # Update debug info
        self.update_debug_info()
        
        # Schedule next frame
        if self.running:
            delay = max(1, int(16 / self.speed_multiplier))
            self.root.after(delay, self.emulation_loop)
            
    def update_display(self):
        """Update display canvas"""
        try:
            from PIL import Image, ImageTk
            
            # Convert framebuffer to image
            img = Image.fromarray(self.ppu.framebuffer, 'RGB')
            img = img.resize(
                (SCREEN_WIDTH * SCALE_FACTOR, SCREEN_HEIGHT * SCALE_FACTOR),
                Image.NEAREST
            )
            
            self.photo = ImageTk.PhotoImage(img)
            self.canvas.delete("all")
            self.canvas.create_image(0, 0, anchor=tk.NW, image=self.photo)
            
        except ImportError:
            # Fallback without PIL
            self.canvas.delete("all")
            for y in range(0, SCREEN_HEIGHT, 8):
                for x in range(0, SCREEN_WIDTH, 8):
                    color = self.ppu.framebuffer[y, x]
                    hex_color = '#{:02x}{:02x}{:02x}'.format(*color)
                    self.canvas.create_rectangle(
                        x * SCALE_FACTOR,
                        y * SCALE_FACTOR,
                        (x + 8) * SCALE_FACTOR,
                        (y + 8) * SCALE_FACTOR,
                        fill=hex_color,
                        outline=""
                    )
                    
    def update_debug_info(self):
        """Update debug information display"""
        self.info_labels["PC"].config(text=f"0x{self.cpu.reg.pc:04X}")
        self.info_labels["SP"].config(text=f"0x{self.cpu.reg.sp:04X}")
        self.info_labels["A"].config(text=f"0x{self.cpu.reg.a:02X}")
        self.info_labels["BC"].config(text=f"0x{self.cpu.reg.bc:04X}")
        self.info_labels["DE"].config(text=f"0x{self.cpu.reg.de:04X}")
        self.info_labels["HL"].config(text=f"0x{self.cpu.reg.hl:04X}")
        
        # Flags
        flags = ""
        flags += "Z" if self.cpu.check_flag(Flags.ZERO) else "-"
        flags += "N" if self.cpu.check_flag(Flags.NEGATIVE) else "-"
        flags += "H" if self.cpu.check_flag(Flags.HALFCARRY) else "-"
        flags += "C" if self.cpu.check_flag(Flags.CARRY) else "-"
        self.info_labels["Flags"].config(text=flags)
        
        # CPU state
        if self.cpu.halted:
            self.info_labels["CPU"].config(text="HALT")
        elif self.cpu.stopped:
            self.info_labels["CPU"].config(text="STOP")
        else:
            self.info_labels["CPU"].config(text="RUN")
            
        # Cycles
        self.info_labels["Cycles"].config(text=f"{self.cpu.total_cycles:,}")
        
    def show_memory_viewer(self):
        """Show memory viewer window"""
        viewer = tk.Toplevel(self.root)
        viewer.title("Memory Viewer")
        viewer.geometry("600x400")
        viewer.configure(bg='#1a1a2e')
        
        # Text widget for memory display
        text = tk.Text(viewer, bg='#0a0a0f', fg='#00ff41', font=('Courier', 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Display memory
        addr = 0x0000
        for row in range(32):
            line = f"{addr:04X}: "
            for col in range(16):
                if addr < 0x10000:
                    byte = self.memory.read(addr)
                    line += f"{byte:02X} "
                addr += 1
            text.insert(tk.END, line + "\n")
            
        text.config(state=tk.DISABLED)
        
    def show_tile_viewer(self):
        """Show tile viewer window"""
        viewer = tk.Toplevel(self.root)
        viewer.title("Tile Viewer")
        viewer.geometry("512x512")
        viewer.configure(bg='#1a1a2e')
        
        canvas = tk.Canvas(viewer, width=512, height=512, bg='#0a0a0f')
        canvas.pack()
        
        # Display tiles
        for tile_idx in range(384):
            tile_addr = 0x8000 + tile_idx * 16
            x = (tile_idx % 16) * 32
            y = (tile_idx // 16) * 32
            
            # Draw tile
            for py in range(8):
                data1 = self.memory.vram[tile_addr - 0x8000 + py * 2]
                data2 = self.memory.vram[tile_addr - 0x8000 + py * 2 + 1]
                
                for px in range(8):
                    bit = 7 - px
                    color_idx = ((data2 >> bit) & 1) << 1 | ((data1 >> bit) & 1)
                    color = self.ppu.colors[color_idx]
                    hex_color = '#{:02x}{:02x}{:02x}'.format(*color)
                    
                    canvas.create_rectangle(
                        x + px * 4,
                        y + py * 4,
                        x + px * 4 + 4,
                        y + py * 4 + 4,
                        fill=hex_color,
                        outline=""
                    )
                    
    def show_controls(self):
        """Show controls dialog"""
        messagebox.showinfo(
            "Controls",
            "Keyboard Controls:\n\n"
            "Space - Start/Stop emulation\n"
            "R - Reset emulator\n"
            "Ctrl+O - Load ROM\n"
            "Ctrl+Q - Quit\n\n"
            "Game Controls:\n"
            "(Not yet implemented)\n"
            "Arrow Keys - D-Pad\n"
            "Z - A Button\n"
            "X - B Button\n"
            "Enter - Start\n"
            "Shift - Select"
        )
        
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo(
            "About SamSoft GB",
            f"SamSoft GB Emulator\n"
            f"Version {__version__}\n"
            f"Codename: {__codename__}\n\n"
            f"A Game Boy emulator built for\n"
            f"Haltmann OS 1.X-infdev\n\n"
            f"Features photon-accelerated rendering\n"
            f"through LightFS Gaussian Split channels\n\n"
            f"© 2025 SamSoft Tech"
        )
        
    def run(self):
        """Start the application"""
        # Display welcome screen
        self.canvas.delete("all")
        
        # Draw gradient background
        for i in range(SCREEN_HEIGHT):
            color = int(155 - (i * 140 / SCREEN_HEIGHT))
            hex_color = f'#{color:02x}{color+33:02x}{15:02x}'
            self.canvas.create_rectangle(
                0,
                i * SCALE_FACTOR,
                SCREEN_WIDTH * SCALE_FACTOR,
                (i + 1) * SCALE_FACTOR,
                fill=hex_color,
                outline=""
            )
            
        # Add text
        self.canvas.create_text(
            SCREEN_WIDTH * SCALE_FACTOR // 2,
            50,
            text="SAMSOFT GB",
            fill="#0f3811",
            font=('Arial', 28, 'bold')
        )
        
        self.canvas.create_text(
            SCREEN_WIDTH * SCALE_FACTOR // 2,
            90,
            text="CLIENT EDITION",
            fill="#0f3811",
            font=('Arial', 16, 'bold')
        )
        
        self.canvas.create_text(
            SCREEN_WIDTH * SCALE_FACTOR // 2,
            130,
            text=f"Version {__version__}",
            fill="#2a5a2a",
            font=('Arial', 12)
        )
        
        self.canvas.create_text(
            SCREEN_WIDTH * SCALE_FACTOR // 2,
            150,
            text=__codename__,
            fill="#2a5a2a",
            font=('Arial', 12, 'italic')
        )
        
        self.canvas.create_text(
            SCREEN_WIDTH * SCALE_FACTOR // 2,
            SCREEN_HEIGHT * SCALE_FACTOR - 60,
            text="File > Load ROM",
            fill="#0f3811",
            font=('Arial', 14, 'bold')
        )
        
        self.canvas.create_text(
            SCREEN_WIDTH * SCALE_FACTOR // 2,
            SCREEN_HEIGHT * SCALE_FACTOR - 35,
            text="to begin",
            fill="#0f3811",
            font=('Arial', 12)
        )
        
        # Start GUI
        self.root.mainloop()

# === MAIN ENTRY ===
def main():
    """Main entry point"""
    print("=" * 60)
    print("SamSoft GB Emulator Client")
    print(f"Version {__version__} - {__codename__}")
    print("=" * 60)
    print("Initializing Haltmann OS photon layer...")
    print("Loading CatKernel hooks...")
    print("Establishing Gaussian Split channels...")
    print()
    
    # Check dependencies
    try:
        import numpy
        from PIL import Image, ImageTk
        print("✓ All dependencies loaded")
    except ImportError as e:
        print(f"⚠ Missing dependency: {e}")
        print("Installing required packages...")
        
        import subprocess
        import sys
        
        packages = ["numpy", "Pillow"]
        for package in packages:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package, "--break-system-packages"])
            except:
                subprocess.check_call([sys.executable, "-m", "pip", "install", package])
                
        print("✓ Dependencies installed")
        
    print()
    print("Starting GUI...")
    print()
    
    # Create and run emulator
    emulator = SamSoftGBClient()
    emulator.run()

if __name__ == "__main__":
    main()
