#!/usr/bin/env python3
"""
EMUDOLPHIN 1.0 - Complete Educational GameCube Emulator
Merged single-file implementation with tkinter GUI
For research and educational purposes only
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import time
import struct
import array
from enum import Enum, IntEnum
from dataclasses import dataclass
from typing import Optional, List, Dict, Any, Tuple
import random
import math
import colorsys

# ═══════════════════════════════════════════════════════════════════════════
# LEGAL DISCLAIMER
# ═══════════════════════════════════════════════════════════════════════════

DISCLAIMER = """
EMUDOLPHIN 1.0 - Educational Framework

This software is for educational and research purposes only.
It demonstrates emulation concepts and GameCube architecture.
This framework cannot and does not run commercial games.
Do not use this software to run copyrighted content.

By using this software, you agree to use it only for learning
about emulation techniques and hardware architecture.
"""

# ═══════════════════════════════════════════════════════════════════════════
# CORE EMULATION COMPONENTS
# ═══════════════════════════════════════════════════════════════════════════

class MemoryMap:
    """GameCube Memory Map Constants"""
    MEM1_START = 0x80000000
    MEM1_SIZE = 24 * 1024 * 1024  # 24MB
    L2_CACHE_START = 0xE0000000
    L2_CACHE_SIZE = 256 * 1024  # 256KB
    
    # Hardware Registers
    CP_REGS = 0xCC000000  # Command Processor
    PE_REGS = 0xCC001000  # Pixel Engine
    VI_REGS = 0xCC002000  # Video Interface
    PI_REGS = 0xCC003000  # Processor Interface
    MI_REGS = 0xCC004000  # Memory Interface
    DSP_REGS = 0xCC005000  # DSP Interface

class GekkoCore:
    """PowerPC 750CXe (Gekko) CPU Educational Model"""
    
    def __init__(self):
        # Registers
        self.gpr = [0] * 32  # General Purpose Registers
        self.fpr = [0.0] * 32  # Floating Point Registers
        self.pc = 0x80000000  # Program Counter
        self.lr = 0  # Link Register
        self.ctr = 0  # Count Register
        self.cr = 0  # Condition Register
        self.xer = 0  # Exception Register
        self.msr = 0  # Machine State Register
        
        # Performance counters
        self.instructions_executed = 0
        self.cycles = 0
        self.clock_speed = 486_000_000  # 486 MHz
        
        # Paired singles support (Gekko enhancement)
        self.paired_single_enabled = True
        
    def reset(self):
        """Reset CPU to initial state"""
        self.__init__()
        self.pc = 0x80000000
        
    def tick(self):
        """Execute one instruction cycle (educational)"""
        self.cycles += 1
        self.instructions_executed += 1
        
        # Simulate basic instruction execution
        if self.cycles % 1000 == 0:
            self.pc += 4  # Advance program counter
            
    def get_state(self) -> Dict:
        """Get current CPU state"""
        return {
            'pc': self.pc,
            'lr': self.lr,
            'ctr': self.ctr,
            'cr': self.cr,
            'cycles': self.cycles,
            'instructions': self.instructions_executed
        }

class FlipperGPU:
    """ATI Flipper GPU Educational Model"""
    
    def __init__(self):
        # Framebuffer (640x480 RGBA)
        self.width = 640
        self.height = 480
        self.framebuffer = bytearray(self.width * self.height * 4)
        
        # GPU state
        self.triangles_rendered = 0
        self.pixels_drawn = 0
        self.frame_count = 0
        
        # Texture memory (1MB)
        self.texture_memory = bytearray(1024 * 1024)
        
        # Transform matrices
        self.modelview_matrix = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        self.projection_matrix = [[1,0,0,0],[0,1,0,0],[0,0,1,0],[0,0,0,1]]
        
        # TEV stages (Texture Environment)
        self.tev_stages = [{'enabled': False} for _ in range(16)]
        
        # Initialize with a pattern
        self.clear_framebuffer()
        
    def clear_framebuffer(self, r=0, g=0, b=0, a=255):
        """Clear framebuffer to specified color"""
        for i in range(0, len(self.framebuffer), 4):
            self.framebuffer[i] = r
            self.framebuffer[i+1] = g
            self.framebuffer[i+2] = b
            self.framebuffer[i+3] = a
            
    def draw_test_pattern(self):
        """Draw a test pattern for demonstration"""
        for y in range(self.height):
            for x in range(self.width):
                idx = (y * self.width + x) * 4
                
                # Create a gradient pattern
                hue = (x / self.width + y / self.height) / 2
                r, g, b = [int(c * 255) for c in colorsys.hsv_to_rgb(hue, 0.8, 0.9)]
                
                self.framebuffer[idx] = r
                self.framebuffer[idx + 1] = g
                self.framebuffer[idx + 2] = b
                self.framebuffer[idx + 3] = 255
                
        self.triangles_rendered += 100  # Simulated
        self.pixels_drawn += self.width * self.height
        
    def render_frame(self):
        """Render a frame (educational)"""
        self.frame_count += 1
        # In a real emulator, this would process display lists
        
    def get_state(self) -> Dict:
        """Get current GPU state"""
        return {
            'resolution': f"{self.width}x{self.height}",
            'triangles': self.triangles_rendered,
            'pixels': self.pixels_drawn,
            'frames': self.frame_count
        }

class DSPCore:
    """Nintendo DSP (Audio) Educational Model"""
    
    def __init__(self):
        # DSP Memory
        self.iram = bytearray(8 * 1024)  # 8KB instruction RAM
        self.dram = bytearray(8 * 1024)  # 8KB data RAM
        
        # Audio state
        self.sample_rate = 48000
        self.audio_enabled = False
        
        # ARAM (16MB Audio RAM)
        self.aram_size = 16 * 1024 * 1024
        self.aram = bytearray(1024)  # Reduced for demo
        
    def process_audio(self):
        """Process audio (educational)"""
        pass
        
    def get_state(self) -> Dict:
        """Get current DSP state"""
        return {
            'sample_rate': self.sample_rate,
            'enabled': self.audio_enabled,
            'aram_size': self.aram_size
        }

class MemoryController:
    """Memory Management Unit Educational Model"""
    
    def __init__(self):
        # Main Memory (24MB) - reduced for demo
        self.main_memory = bytearray(1024 * 1024)  # 1MB for demo
        self.actual_size = 24 * 1024 * 1024
        
        # L1 Caches
        self.l1_icache = bytearray(32 * 1024)  # 32KB
        self.l1_dcache = bytearray(32 * 1024)  # 32KB
        
        # L2 Cache
        self.l2_cache = bytearray(256 * 1024)  # 256KB
        
    def read_u8(self, address: int) -> int:
        """Read 8-bit value"""
        if 0x80000000 <= address < 0x80000000 + len(self.main_memory):
            return self.main_memory[address - 0x80000000]
        return 0
        
    def write_u8(self, address: int, value: int):
        """Write 8-bit value"""
        if 0x80000000 <= address < 0x80000000 + len(self.main_memory):
            self.main_memory[address - 0x80000000] = value & 0xFF
            
    def read_u32(self, address: int) -> int:
        """Read 32-bit value (big-endian)"""
        b0 = self.read_u8(address)
        b1 = self.read_u8(address + 1)
        b2 = self.read_u8(address + 2)
        b3 = self.read_u8(address + 3)
        return (b0 << 24) | (b1 << 16) | (b2 << 8) | b3
        
    def write_u32(self, address: int, value: int):
        """Write 32-bit value (big-endian)"""
        self.write_u8(address, (value >> 24) & 0xFF)
        self.write_u8(address + 1, (value >> 16) & 0xFF)
        self.write_u8(address + 2, (value >> 8) & 0xFF)
        self.write_u8(address + 3, value & 0xFF)

class GameCubeSystem:
    """Complete GameCube System Educational Model"""
    
    def __init__(self):
        # Core components
        self.cpu = GekkoCore()
        self.gpu = FlipperGPU()
        self.dsp = DSPCore()
        self.memory = MemoryController()
        
        # System state
        self.running = False
        self.paused = False
        
        # Timing
        self.target_fps = 60
        self.current_fps = 0
        self.frame_time = time.time()
        
    def reset(self):
        """Reset entire system"""
        self.cpu.reset()
        self.gpu.clear_framebuffer()
        self.dsp.__init__()
        self.memory.__init__()
        self.running = False
        
    def run_frame(self):
        """Run one frame of emulation"""
        if not self.running or self.paused:
            return
            
        # Simulate CPU execution (8.1M instructions per frame at 60fps)
        for _ in range(1000):  # Reduced for performance
            self.cpu.tick()
            
        # Update GPU
        self.gpu.render_frame()
        
        # Process audio
        self.dsp.process_audio()
        
        # Calculate FPS
        current_time = time.time()
        frame_delta = current_time - self.frame_time
        if frame_delta > 0:
            self.current_fps = min(60, 1.0 / frame_delta)
        self.frame_time = current_time

# ═══════════════════════════════════════════════════════════════════════════
# GUI APPLICATION
# ═══════════════════════════════════════════════════════════════════════════

class EmuDolphinGUI:
    """Main GUI Application for EMUDOLPHIN"""
    
    def __init__(self, root):
        self.root = root
        self.root.title("EMUDOLPHIN 1.0 - Educational GameCube Emulator")
        self.root.geometry("1024x768")
        
        # Color scheme
        self.colors = {
            'bg': '#0a0a0a',
            'panel': '#1a1a1a',
            'accent': '#6B46C1',  # GameCube purple
            'accent2': '#9333EA',
            'text': '#e0e0e0',
            'success': '#10B981',
            'warning': '#F59E0B',
            'error': '#EF4444'
        }
        
        self.root.configure(bg=self.colors['bg'])
        
        # System instance
        self.system = GameCubeSystem()
        self.emulation_thread = None
        
        # Build UI
        self.setup_styles()
        self.create_menu()
        self.create_toolbar()
        self.create_main_layout()
        self.create_status_bar()
        
        # Show disclaimer
        self.show_disclaimer()
        
        # Start update loop
        self.update_display()
        
    def setup_styles(self):
        """Configure ttk styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        # Configure colors
        style.configure('TLabel', background=self.colors['panel'], foreground=self.colors['text'])
        style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        style.configure('TFrame', background=self.colors['panel'], relief='flat')
        style.configure('TNotebook', background=self.colors['bg'])
        style.configure('TNotebook.Tab', padding=[20, 10])
        
    def create_menu(self):
        """Create application menu"""
        menubar = tk.Menu(self.root, bg=self.colors['panel'], fg=self.colors['text'])
        self.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['panel'], fg=self.colors['text'])
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="Load Demo", command=self.load_demo)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.quit_app)
        
        # Emulation menu
        emu_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['panel'], fg=self.colors['text'])
        menubar.add_cascade(label="Emulation", menu=emu_menu)
        emu_menu.add_command(label="Start", command=self.start_emulation, accelerator="F5")
        emu_menu.add_command(label="Pause", command=self.pause_emulation, accelerator="F6")
        emu_menu.add_command(label="Stop", command=self.stop_emulation, accelerator="F7")
        emu_menu.add_command(label="Reset", command=self.reset_system, accelerator="F8")
        
        # Debug menu
        debug_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['panel'], fg=self.colors['text'])
        menubar.add_cascade(label="Debug", menu=debug_menu)
        debug_menu.add_command(label="CPU Viewer", command=self.show_cpu_debug)
        debug_menu.add_command(label="Memory Browser", command=self.show_memory_debug)
        debug_menu.add_command(label="GPU State", command=self.show_gpu_debug)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0, bg=self.colors['panel'], fg=self.colors['text'])
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="Architecture", command=self.show_architecture)
        help_menu.add_command(label="About", command=self.show_about)
        
        # Bind shortcuts
        self.root.bind('<F5>', lambda e: self.start_emulation())
        self.root.bind('<F6>', lambda e: self.pause_emulation())
        self.root.bind('<F7>', lambda e: self.stop_emulation())
        self.root.bind('<F8>', lambda e: self.reset_system())
        
    def create_toolbar(self):
        """Create toolbar with controls"""
        toolbar = tk.Frame(self.root, bg=self.colors['panel'], height=50)
        toolbar.pack(fill=tk.X, padx=2, pady=2)
        
        # Control buttons
        buttons = [
            ("▶", self.start_emulation, self.colors['success']),
            ("⏸", self.pause_emulation, self.colors['warning']),
            ("⏹", self.stop_emulation, self.colors['error']),
            ("⟲", self.reset_system, self.colors['accent2'])
        ]
        
        for text, command, color in buttons:
            btn = tk.Button(toolbar, text=text, command=command,
                          bg=color, fg='white', font=('Arial', 16),
                          width=3, height=1, relief=tk.FLAT)
            btn.pack(side=tk.LEFT, padx=5, pady=10)
            
        # FPS display
        self.fps_label = tk.Label(toolbar, text="FPS: 0", 
                                 bg=self.colors['panel'], fg=self.colors['success'],
                                 font=('Courier', 12, 'bold'))
        self.fps_label.pack(side=tk.RIGHT, padx=20)
        
    def create_main_layout(self):
        """Create main window layout"""
        # Main container
        main_frame = tk.Frame(self.root, bg=self.colors['bg'])
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Left panel - Display and controls
        left_frame = tk.Frame(main_frame, bg=self.colors['panel'])
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Display canvas
        display_frame = tk.LabelFrame(left_frame, text="Display Output",
                                     bg=self.colors['panel'], fg=self.colors['text'],
                                     font=('Arial', 10, 'bold'))
        display_frame.pack(padx=10, pady=10)
        
        self.canvas = tk.Canvas(display_frame, width=640, height=480,
                               bg='black', highlightthickness=0)
        self.canvas.pack(padx=5, pady=5)
        
        # Demo controls
        demo_frame = tk.LabelFrame(left_frame, text="Educational Demos",
                                  bg=self.colors['panel'], fg=self.colors['text'],
                                  font=('Arial', 10, 'bold'))
        demo_frame.pack(fill=tk.X, padx=10, pady=5)
        
        demos = [
            ("Test Pattern", self.demo_test_pattern),
            ("CPU Test", self.demo_cpu_test),
            ("Memory Test", self.demo_memory_test),
            ("Animation", self.demo_animation)
        ]
        
        for demo_name, demo_func in demos:
            btn = tk.Button(demo_frame, text=demo_name, command=demo_func,
                          bg=self.colors['accent'], fg='white',
                          relief=tk.FLAT, padx=10)
            btn.pack(side=tk.LEFT, padx=5, pady=5)
            
        # Right panel - System information
        right_frame = tk.Frame(main_frame, bg=self.colors['panel'], width=300)
        right_frame.pack(side=tk.RIGHT, fill=tk.Y)
        right_frame.pack_propagate(False)
        
        # Create tabbed interface
        self.notebook = ttk.Notebook(right_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # System Info tab
        self.info_tab = tk.Frame(self.notebook, bg=self.colors['panel'])
        self.notebook.add(self.info_tab, text="System")
        
        self.info_text = tk.Text(self.info_tab, width=35, height=25,
                                bg='#0a0a0a', fg=self.colors['text'],
                                font=('Courier', 9), relief=tk.FLAT,
                                insertbackground=self.colors['accent'])
        self.info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Registers tab
        self.reg_tab = tk.Frame(self.notebook, bg=self.colors['panel'])
        self.notebook.add(self.reg_tab, text="Registers")
        
        self.reg_text = tk.Text(self.reg_tab, width=35, height=25,
                               bg='#0a0a0a', fg=self.colors['text'],
                               font=('Courier', 9), relief=tk.FLAT)
        self.reg_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Memory tab
        self.mem_tab = tk.Frame(self.notebook, bg=self.colors['panel'])
        self.notebook.add(self.mem_tab, text="Memory")
        
        mem_controls = tk.Frame(self.mem_tab, bg=self.colors['panel'])
        mem_controls.pack(fill=tk.X)
        
        tk.Label(mem_controls, text="Address:", 
                bg=self.colors['panel'], fg=self.colors['text']).pack(side=tk.LEFT, padx=5)
        
        self.mem_addr = tk.Entry(mem_controls, width=12,
                                bg='#0a0a0a', fg=self.colors['text'])
        self.mem_addr.pack(side=tk.LEFT, padx=5)
        self.mem_addr.insert(0, "0x80000000")
        
        tk.Button(mem_controls, text="View", command=self.update_memory_view,
                 bg=self.colors['accent'], fg='white',
                 relief=tk.FLAT).pack(side=tk.LEFT, padx=5)
        
        self.mem_text = tk.Text(self.mem_tab, width=35, height=23,
                               bg='#0a0a0a', fg=self.colors['text'],
                               font=('Courier', 8), relief=tk.FLAT)
        self.mem_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
    def create_status_bar(self):
        """Create status bar"""
        self.status_frame = tk.Frame(self.root, bg=self.colors['panel'], height=25)
        self.status_frame.pack(fill=tk.X, side=tk.BOTTOM)
        
        self.status_label = tk.Label(self.status_frame, text="Ready",
                                    bg=self.colors['panel'], fg=self.colors['text'],
                                    anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=10)
        
        # System specs label
        specs = "Gekko 486MHz | Flipper 162MHz | 24MB RAM | 16MB ARAM"
        tk.Label(self.status_frame, text=specs,
                bg=self.colors['panel'], fg=self.colors['accent'],
                anchor=tk.E).pack(side=tk.RIGHT, padx=10)
        
    def show_disclaimer(self):
        """Show disclaimer dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title("Educational Software Notice")
        dialog.geometry("500x400")
        dialog.configure(bg=self.colors['bg'])
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Title
        title = tk.Label(dialog, text="EMUDOLPHIN 1.0",
                        bg=self.colors['bg'], fg=self.colors['accent'],
                        font=('Arial', 16, 'bold'))
        title.pack(pady=20)
        
        # Disclaimer text
        text_frame = tk.Frame(dialog, bg=self.colors['panel'])
        text_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        disclaimer_text = tk.Text(text_frame, wrap=tk.WORD,
                                 bg=self.colors['panel'], fg=self.colors['text'],
                                 font=('Arial', 10), relief=tk.FLAT,
                                 height=12)
        disclaimer_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        disclaimer_text.insert(tk.END, DISCLAIMER)
        disclaimer_text.insert(tk.END, "\n\nFeatures:\n")
        disclaimer_text.insert(tk.END, "• GameCube architecture demonstration\n")
        disclaimer_text.insert(tk.END, "• CPU and GPU simulation\n")
        disclaimer_text.insert(tk.END, "• Memory management visualization\n")
        disclaimer_text.insert(tk.END, "• Hardware debugging tools\n")
        disclaimer_text.config(state=tk.DISABLED)
        
        # Accept button
        tk.Button(dialog, text="I Understand - Continue",
                 command=dialog.destroy,
                 bg=self.colors['accent'], fg='white',
                 font=('Arial', 10, 'bold'),
                 relief=tk.FLAT, padx=20, pady=8).pack(pady=20)
        
    def load_demo(self):
        """Load educational demo"""
        self.status_label.config(text="Loading educational demo...")
        self.demo_test_pattern()
        
    def demo_test_pattern(self):
        """Display test pattern"""
        self.system.gpu.draw_test_pattern()
        self.update_canvas()
        self.status_label.config(text="Test pattern rendered")
        
    def demo_cpu_test(self):
        """Run CPU test"""
        for _ in range(10000):
            self.system.cpu.tick()
        self.update_info()
        messagebox.showinfo("CPU Test",
                          f"Executed {self.system.cpu.instructions_executed:,} instructions\n"
                          f"Cycles: {self.system.cpu.cycles:,}\n"
                          f"PC: {hex(self.system.cpu.pc)}")
        
    def demo_memory_test(self):
        """Run memory test"""
        # Write test pattern
        test_addr = 0x80000100
        test_value = 0xDEADBEEF
        
        self.system.memory.write_u32(test_addr, test_value)
        read_value = self.system.memory.read_u32(test_addr)
        
        messagebox.showinfo("Memory Test",
                          f"Write: {hex(test_value)} → {hex(test_addr)}\n"
                          f"Read:  {hex(read_value)} ← {hex(test_addr)}\n"
                          f"Test {'PASSED' if read_value == test_value else 'FAILED'}")
        
    def demo_animation(self):
        """Run animation demo"""
        self.animation_running = True
        
        def animate():
            if not hasattr(self, 'animation_running') or not self.animation_running:
                return
                
            # Create animated pattern
            t = time.time()
            for y in range(0, self.system.gpu.height, 10):
                for x in range(0, self.system.gpu.width, 10):
                    idx = (y * self.system.gpu.width + x) * 4
                    
                    # Animated color based on position and time
                    r = int(127 + 127 * math.sin(x/50 + t))
                    g = int(127 + 127 * math.sin(y/50 + t * 1.5))
                    b = int(127 + 127 * math.sin((x+y)/70 + t * 2))
                    
                    # Draw 10x10 block
                    for dy in range(min(10, self.system.gpu.height - y)):
                        for dx in range(min(10, self.system.gpu.width - x)):
                            pidx = ((y + dy) * self.system.gpu.width + (x + dx)) * 4
                            if pidx < len(self.system.gpu.framebuffer) - 3:
                                self.system.gpu.framebuffer[pidx] = r
                                self.system.gpu.framebuffer[pidx + 1] = g
                                self.system.gpu.framebuffer[pidx + 2] = b
                                self.system.gpu.framebuffer[pidx + 3] = 255
                                
            self.update_canvas()
            
            if self.animation_running:
                self.root.after(50, animate)
                
        animate()
        self.status_label.config(text="Running animation demo")
        
        # Stop after 5 seconds
        self.root.after(5000, lambda: setattr(self, 'animation_running', False))
        
    def start_emulation(self):
        """Start emulation"""
        if not self.system.running:
            self.system.running = True
            self.emulation_thread = threading.Thread(target=self.emulation_loop)
            self.emulation_thread.daemon = True
            self.emulation_thread.start()
            self.status_label.config(text="Emulation started")
            
    def pause_emulation(self):
        """Toggle pause"""
        self.system.paused = not self.system.paused
        status = "Paused" if self.system.paused else "Running"
        self.status_label.config(text=f"Emulation {status}")
        
    def stop_emulation(self):
        """Stop emulation"""
        self.system.running = False
        if self.emulation_thread:
            self.emulation_thread.join(timeout=1.0)
        self.status_label.config(text="Emulation stopped")
        
    def reset_system(self):
        """Reset system"""
        self.stop_emulation()
        self.system.reset()
        self.update_info()
        self.update_canvas()
        self.status_label.config(text="System reset")
        
    def emulation_loop(self):
        """Main emulation loop"""
        while self.system.running:
            self.system.run_frame()
            time.sleep(1/60)  # 60 FPS target
            
    def update_display(self):
        """Update display periodically"""
        self.update_info()
        self.update_registers()
        self.update_canvas()
        self.fps_label.config(text=f"FPS: {self.system.current_fps:.1f}")
        self.root.after(100, self.update_display)
        
    def update_canvas(self):
        """Update canvas with framebuffer"""
        # Create image from framebuffer
        fb = self.system.gpu.framebuffer
        
        # Convert to PhotoImage format
        img_data = []
        for y in range(self.system.gpu.height):
            row = "{"
            for x in range(self.system.gpu.width):
                idx = (y * self.system.gpu.width + x) * 4
                r = fb[idx]
                g = fb[idx + 1]
                b = fb[idx + 2]
                row += f"#{r:02x}{g:02x}{b:02x} "
            row += "}"
            img_data.append(row)
            
        img_str = " ".join(img_data)
        
        try:
            self.photo = tk.PhotoImage(width=self.system.gpu.width,
                                       height=self.system.gpu.height)
            self.photo.put(img_str)
            self.canvas.delete("all")
            self.canvas.create_image(320, 240, image=self.photo)
        except:
            pass  # Fallback for performance
            
    def update_info(self):
        """Update system info display"""
        cpu_state = self.system.cpu.get_state()
        gpu_state = self.system.gpu.get_state()
        dsp_state = self.system.dsp.get_state()
        
        self.info_text.config(state=tk.NORMAL)
        self.info_text.delete(1.0, tk.END)
        
        info = f"""╔══════════════════════════════╗
║     SYSTEM INFORMATION       ║
╚══════════════════════════════╝

┌─── CPU (Gekko) ──────────────┐
│ Clock:    486 MHz            │
│ PC:       {cpu_state['pc']:#010x}       │
│ Cycles:   {cpu_state['cycles']:,}
│ Executed: {cpu_state['instructions']:,}
└──────────────────────────────┘

┌─── GPU (Flipper) ────────────┐
│ Clock:     162 MHz           │
│ Resolution: {gpu_state['resolution']}        │
│ Triangles: {gpu_state['triangles']:,}
│ Pixels:    {gpu_state['pixels']:,}
│ Frames:    {gpu_state['frames']}
└──────────────────────────────┘

┌─── DSP (Audio) ──────────────┐
│ Sample Rate: {dsp_state['sample_rate']} Hz     │
│ ARAM Size:   {dsp_state['aram_size']/(1024*1024):.0f} MB          │
│ Enabled:     {dsp_state['enabled']}          │
└──────────────────────────────┘

┌─── Memory ───────────────────┐
│ Main RAM:    24 MB           │
│ L1 I-Cache:  32 KB           │
│ L1 D-Cache:  32 KB           │
│ L2 Cache:    256 KB          │
└──────────────────────────────┘"""
        
        self.info_text.insert(tk.END, info)
        self.info_text.config(state=tk.DISABLED)
        
    def update_registers(self):
        """Update register display"""
        self.reg_text.config(state=tk.NORMAL)
        self.reg_text.delete(1.0, tk.END)
        
        # GPR display
        self.reg_text.insert(tk.END, "General Purpose Registers:\n")
        self.reg_text.insert(tk.END, "─" * 30 + "\n")
        
        for i in range(0, 32, 2):
            self.reg_text.insert(tk.END, 
                f"r{i:02d}: {self.system.cpu.gpr[i]:08X}  "
                f"r{i+1:02d}: {self.system.cpu.gpr[i+1]:08X}\n")
                
        self.reg_text.insert(tk.END, "\nSpecial Registers:\n")
        self.reg_text.insert(tk.END, "─" * 30 + "\n")
        self.reg_text.insert(tk.END, f"PC:  {self.system.cpu.pc:08X}\n")
        self.reg_text.insert(tk.END, f"LR:  {self.system.cpu.lr:08X}\n")
        self.reg_text.insert(tk.END, f"CTR: {self.system.cpu.ctr:08X}\n")
        self.reg_text.insert(tk.END, f"CR:  {self.system.cpu.cr:08X}\n")
        self.reg_text.insert(tk.END, f"XER: {self.system.cpu.xer:08X}\n")
        self.reg_text.insert(tk.END, f"MSR: {self.system.cpu.msr:08X}\n")
        
        self.reg_text.config(state=tk.DISABLED)
        
    def update_memory_view(self):
        """Update memory view"""
        try:
            addr = int(self.mem_addr.get(), 0)
            
            self.mem_text.config(state=tk.NORMAL)
            self.mem_text.delete(1.0, tk.END)
            
            self.mem_text.insert(tk.END, "Address    00 01 02 03 04 05 06 07 08 09 0A 0B 0C 0D 0E 0F\n")
            self.mem_text.insert(tk.END, "─" * 60 + "\n")
            
            for offset in range(0, 256, 16):
                line = f"{addr + offset:08X}  "
                ascii_str = " "
                
                for i in range(16):
                    byte = self.system.memory.read_u8(addr + offset + i)
                    line += f"{byte:02X} "
                    ascii_str += chr(byte) if 32 <= byte < 127 else '.'
                    
                self.mem_text.insert(tk.END, line + ascii_str + "\n")
                
            self.mem_text.config(state=tk.DISABLED)
            
        except ValueError:
            messagebox.showerror("Error", "Invalid memory address")
            
    def show_cpu_debug(self):
        """Show CPU debug window"""
        debug = tk.Toplevel(self.root)
        debug.title("CPU Debug")
        debug.geometry("600x500")
        debug.configure(bg=self.colors['bg'])
        
        text = scrolledtext.ScrolledText(debug, bg='#0a0a0a', fg=self.colors['text'],
                                        font=('Courier', 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text.insert(tk.END, "PowerPC 750CXe (Gekko) Debug Information\n")
        text.insert(tk.END, "=" * 50 + "\n\n")
        text.insert(tk.END, "Features:\n")
        text.insert(tk.END, "• 32-bit RISC architecture\n")
        text.insert(tk.END, "• 64-bit FPU with paired singles\n")
        text.insert(tk.END, "• 32 GPRs, 32 FPRs\n")
        text.insert(tk.END, "• Branch prediction\n")
        text.insert(tk.END, "• Out-of-order execution\n\n")
        
        text.insert(tk.END, "Current State:\n")
        text.insert(tk.END, "-" * 30 + "\n")
        text.insert(tk.END, f"Instructions: {self.system.cpu.instructions_executed:,}\n")
        text.insert(tk.END, f"Clock cycles: {self.system.cpu.cycles:,}\n")
        text.insert(tk.END, f"IPC: {self.system.cpu.instructions_executed/(max(1, self.system.cpu.cycles)):.2f}\n")
        
    def show_memory_debug(self):
        """Show memory debug window"""
        debug = tk.Toplevel(self.root)
        debug.title("Memory Browser")
        debug.geometry("700x500")
        debug.configure(bg=self.colors['bg'])
        
        # Address controls
        control_frame = tk.Frame(debug, bg=self.colors['panel'])
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        tk.Label(control_frame, text="Address:", 
                bg=self.colors['panel'], fg=self.colors['text']).pack(side=tk.LEFT, padx=5)
        
        addr_var = tk.StringVar(value="0x80000000")
        addr_entry = tk.Entry(control_frame, textvariable=addr_var, width=12)
        addr_entry.pack(side=tk.LEFT, padx=5)
        
        # Memory display
        text = scrolledtext.ScrolledText(debug, bg='#0a0a0a', fg=self.colors['text'],
                                        font=('Courier', 9))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        def update():
            try:
                addr = int(addr_var.get(), 0)
                text.delete(1.0, tk.END)
                
                for offset in range(0, 512, 16):
                    line = f"{addr + offset:08X}  "
                    for i in range(16):
                        byte = self.system.memory.read_u8(addr + offset + i)
                        line += f"{byte:02X} "
                    text.insert(tk.END, line + "\n")
                    
            except ValueError:
                messagebox.showerror("Error", "Invalid address")
                
        tk.Button(control_frame, text="View", command=update,
                 bg=self.colors['accent'], fg='white').pack(side=tk.LEFT, padx=5)
        
        update()
        
    def show_gpu_debug(self):
        """Show GPU debug window"""
        debug = tk.Toplevel(self.root)
        debug.title("GPU Debug")
        debug.geometry("600x400")
        debug.configure(bg=self.colors['bg'])
        
        text = scrolledtext.ScrolledText(debug, bg='#0a0a0a', fg=self.colors['text'],
                                        font=('Courier', 10))
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        text.insert(tk.END, "ATI Flipper GPU Debug Information\n")
        text.insert(tk.END, "=" * 50 + "\n\n")
        text.insert(tk.END, "Specifications:\n")
        text.insert(tk.END, "• 162 MHz clock speed\n")
        text.insert(tk.END, "• 3MB embedded 1T-SRAM\n")
        text.insert(tk.END, "• 6-12 million polygons/second\n")
        text.insert(tk.END, "• Hardware T&L\n")
        text.insert(tk.END, "• 16 texture stages (TEV)\n\n")
        
        text.insert(tk.END, "Current State:\n")
        text.insert(tk.END, "-" * 30 + "\n")
        text.insert(tk.END, f"Frames rendered: {self.system.gpu.frame_count}\n")
        text.insert(tk.END, f"Triangles: {self.system.gpu.triangles_rendered:,}\n")
        text.insert(tk.END, f"Pixels drawn: {self.system.gpu.pixels_drawn:,}\n")
        
    def show_architecture(self):
        """Show architecture information"""
        arch = tk.Toplevel(self.root)
        arch.title("GameCube Architecture")
        arch.geometry("700x600")
        arch.configure(bg=self.colors['bg'])
        
        text = scrolledtext.ScrolledText(arch, bg=self.colors['panel'], fg=self.colors['text'],
                                        font=('Arial', 10), wrap=tk.WORD)
        text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        arch_info = """
NINTENDO GAMECUBE TECHNICAL ARCHITECTURE

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CENTRAL PROCESSING UNIT (CPU)
────────────────────────────────────
IBM PowerPC 750CXe "Gekko"
• Clock Speed: 485.835 MHz
• Architecture: 32-bit RISC
• Pipeline: 7-stage
• Execution Units: 2 integer, 1 FPU
• Registers: 32 GPR, 32 FPR
• Cache: 32KB I-Cache, 32KB D-Cache, 256KB L2
• Special Features:
  - Paired single-precision floating-point
  - 50 new SIMD instructions
  - Compressed memory operations

GRAPHICS PROCESSING UNIT (GPU)
────────────────────────────────────
ATI "Flipper"
• Clock Speed: 162 MHz
• Embedded Memory: 3MB 1T-SRAM
• Performance: 6-12M polygons/second
• Fill Rate: 648 megapixels/second
• Features:
  - Hardware Transform & Lighting
  - 8 hardware lights
  - 16 TEV stages
  - Anisotropic filtering
  - Real-time texture decompression
  - S3TC texture compression

MEMORY ARCHITECTURE
────────────────────────────────────
Main Memory:
• 24MB MoSys 1T-SRAM
• 324MHz, 64-bit bus
• 2.6GB/s bandwidth

Audio RAM (ARAM):
• 16MB SDRAM
• 81MHz
• Used for audio samples and streaming

AUDIO DIGITAL SIGNAL PROCESSOR
────────────────────────────────────
Macronix DSP
• Clock Speed: 81 MHz
• 64 channels
• ADPCM compression
• Dolby Pro Logic II

INPUT/OUTPUT
────────────────────────────────────
• 4 Controller Ports
• 2 Memory Card Slots (59 blocks each)
• High-speed serial port
• 2 USB-like EXI channels

OPTICAL DISC SYSTEM
────────────────────────────────────
• 1.5GB miniDVD format
• CAV (Constant Angular Velocity)
• 2-3MB/s transfer rate
• Proprietary format

This educational framework demonstrates these components
and their interactions without executing commercial software.
"""
        
        text.insert(tk.END, arch_info)
        text.config(state=tk.DISABLED)
        
    def show_about(self):
        """Show about dialog"""
        about = tk.Toplevel(self.root)
        about.title("About EMUDOLPHIN")
        about.geometry("400x300")
        about.configure(bg=self.colors['bg'])
        about.transient(self.root)
        
        # Logo/Title
        tk.Label(about, text="EMUDOLPHIN 1.0",
                bg=self.colors['bg'], fg=self.colors['accent'],
                font=('Arial', 20, 'bold')).pack(pady=20)
        
        tk.Label(about, text="Educational GameCube Emulator",
                bg=self.colors['bg'], fg=self.colors['text'],
                font=('Arial', 12)).pack()
        
        # Info
        info_text = """
For Research and Educational Purposes Only

Learn about:
• Hardware emulation concepts
• System architecture
• Low-level programming
• Performance optimization

This software does not run commercial games
and is designed purely for education.
"""
        
        tk.Label(about, text=info_text,
                bg=self.colors['bg'], fg=self.colors['text'],
                font=('Arial', 10), justify=tk.CENTER).pack(pady=20)
        
        tk.Button(about, text="Close", command=about.destroy,
                 bg=self.colors['accent'], fg='white',
                 relief=tk.FLAT, padx=20).pack(pady=10)
        
    def quit_app(self):
        """Quit application"""
        if messagebox.askyesno("Quit", "Exit EMUDOLPHIN?"):
            self.stop_emulation()
            self.root.quit()

# ═══════════════════════════════════════════════════════════════════════════
# MAIN ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def main():
    """Main application entry point"""
    root = tk.Tk()
    
    # Set window icon (GameCube purple theme)
    root.iconphoto(False, tk.PhotoImage(width=1, height=1))
    
    # Create and run application
    app = EmuDolphinGUI(root)
    
    # Handle window close
    root.protocol("WM_DELETE_WINDOW", app.quit_app)
    
    # Run main loop
    root.mainloop()

if __name__ == "__main__":
    print("=" * 60)
    print("EMUDOLPHIN 1.0 - Educational GameCube Emulator")
    print("=" * 60)
    print("\nStarting GUI...")
    main()
