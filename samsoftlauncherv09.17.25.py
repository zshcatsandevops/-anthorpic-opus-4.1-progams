import os
import sys
import subprocess
import platform
import urllib.request
import zipfile
import json
import shutil
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import re
import hashlib
import configparser

# Define constants for directories and URLs
SAMSOFT_DIR = os.path.expanduser("~/.samsoft")
VERSIONS_DIR = os.path.join(SAMSOFT_DIR, "versions")
JAVA_DIR = os.path.join(SAMSOFT_DIR, "java")
VERSION_MANIFEST_URL = "https://launchermeta.mojang.com/mc/game/version_manifest.json"  # Keep original URL for compatibility

# Define theme colors
THEME = {
    'bg': '#1a1a1a',
    'sidebar': '#141414',
    'accent': '#2374e1',
    'text': '#ffffff',
    'text_secondary': '#808080',
    'button': '#1f1f1f',
    'button_hover': '#2d2d2d',
    'input_bg': '#242424'
}

class SamsoftLauncher(tk.Tk):
    def __init__(self):
        """Initialize the launcher window and UI."""
        super().__init__()
        self.title("Samsoft Launcher")
        self.geometry("1000x600")
        self.minsize(900, 500)
        self.configure(bg=THEME['bg'])
        self.versions = {}  # Dictionary to store version IDs and their URLs
        self.version_categories = {
            "Latest Release": [],
            "Latest Snapshot": [],
            "Release": [],
            "Snapshot": [],
            "Old Beta": [],
            "Old Alpha": []
        }
        
        # Configure styles
        self.style = ttk.Style()
        self.style.configure("TCombobox", 
                           fieldbackground=THEME['input_bg'],
                           background=THEME['input_bg'],
                           foreground=THEME['text'],
                           arrowcolor=THEME['text'])
        
        self.style.configure("Vertical.TScrollbar", 
                           background=THEME['accent'],
                           arrowcolor=THEME['text'])
        
        self.init_ui()

    def init_ui(self):
        """Set up the graphical user interface."""
        # Create main container
        main_container = tk.Frame(self, bg=THEME['bg'])
        main_container.pack(fill="both", expand=True, padx=20, pady=20)

        # Sidebar
        sidebar = tk.Frame(main_container, bg=THEME['sidebar'], width=250)
        sidebar.pack(side="left", fill="y", padx=(0, 20))
        sidebar.pack_propagate(False)

        # Logo and title
        logo_frame = tk.Frame(sidebar, bg=THEME['sidebar'])
        logo_frame.pack(fill="x", pady=(20, 30))
        
        logo = tk.Label(logo_frame, text="🚀", font=("Arial", 32), bg=THEME['sidebar'], fg=THEME['accent'])
        logo.pack()
        
        title = tk.Label(logo_frame, text="Samsoft", font=("Arial", 18, "bold"), bg=THEME['sidebar'], fg=THEME['text'])
        title.pack()

        # Version selection area
        version_frame = tk.LabelFrame(sidebar, text="GAME VERSION", bg=THEME['sidebar'], fg=THEME['text_secondary'],
                                    font=("Arial", 9, "bold"), bd=0)
        version_frame.pack(fill="x", padx=20, pady=(0, 20))

        self.category_combo = ttk.Combobox(version_frame, values=list(self.version_categories.keys()),
                                         state="readonly", font=("Arial", 10))
        self.category_combo.pack(fill="x", pady=(10, 5))
        self.category_combo.set("Latest Release")
        self.category_combo.bind("<<ComboboxSelected>>", self.update_version_list)

        self.version_combo = ttk.Combobox(version_frame, state="readonly", font=("Arial", 10))
        self.version_combo.pack(fill="x", pady=5)
        
        # Settings area
        settings_frame = tk.LabelFrame(sidebar, text="SETTINGS", bg=THEME['sidebar'], fg=THEME['text_secondary'],
                                     font=("Arial", 9, "bold"), bd=0)
        settings_frame.pack(fill="x", padx=20, pady=(0, 20))

        # Username input with modern styling
        username_frame = tk.Frame(settings_frame, bg=THEME['sidebar'])
        username_frame.pack(fill="x", pady=(10, 5))
        
        tk.Label(username_frame, text="USERNAME", font=("Arial", 8, "bold"), 
                bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(anchor="w")
        
        self.username_input = tk.Entry(username_frame, font=("Arial", 10), bg=THEME['input_bg'],
                                     fg=THEME['text'], insertbackground=THEME['text'], bd=0)
        self.username_input.pack(fill="x", pady=(5, 0))
        self.username_input.insert(0, "Enter Username")
        self.username_input.bind("<FocusIn>", lambda e: self.username_input.delete(0, tk.END) 
                               if self.username_input.get() == "Enter Username" else None)

        # RAM slider with modern styling
        ram_frame = tk.Frame(settings_frame, bg=THEME['sidebar'])
        ram_frame.pack(fill="x", pady=10)
        
        ram_label_frame = tk.Frame(ram_frame, bg=THEME['sidebar'])
        ram_label_frame.pack(fill="x")
        
        tk.Label(ram_label_frame, text="RAM ALLOCATION", font=("Arial", 8, "bold"),
                bg=THEME['sidebar'], fg=THEME['text_secondary']).pack(side="left")
        
        self.ram_value_label = tk.Label(ram_label_frame, text="4GB", font=("Arial", 8),
                                      bg=THEME['sidebar'], fg=THEME['text'])
        self.ram_value_label.pack(side="right")

        self.ram_scale = tk.Scale(ram_frame, from_=1, to=16, orient="horizontal",
                                bg=THEME['sidebar'], fg=THEME['text'],
                                activebackground=THEME['accent'],
                                highlightthickness=0, bd=0,
                                troughcolor=THEME['input_bg'],
                                command=lambda v: self.ram_value_label.config(text=f"{int(float(v))}GB"))
        self.ram_scale.set(4)
        self.ram_scale.pack(fill="x")

        # Buttons
        button_frame = tk.Frame(sidebar, bg=THEME['sidebar'])
        button_frame.pack(fill="x", padx=20, pady=(0, 20))

        def on_enter(e):
            e.widget.configure(bg=THEME['button_hover'])

        def on_leave(e):
            e.widget.configure(bg=THEME['button'])

        skin_button = tk.Button(button_frame, text="CHANGE SKIN", font=("Arial", 10, "bold"),
                              bg=THEME['button'], fg=THEME['text'],
                              bd=0, padx=20, pady=8, command=self.select_skin)
        skin_button.pack(fill="x", pady=(0, 10))
        skin_button.bind("<Enter>", on_enter)
        skin_button.bind("<Leave>", on_leave)

        launch_button = tk.Button(button_frame, text="PLAY", font=("Arial", 12, "bold"),
                                bg=THEME['accent'], fg=THEME['text'],
                                bd=0, padx=20, pady=10, command=self.prepare_and_launch)
        launch_button.pack(fill="x")

        # Main content area
        content_area = tk.Frame(main_container, bg=THEME['bg'])
        content_area.pack(side="left", fill="both", expand=True)

        # Changelog section
        changelog_label = tk.Label(content_area, text="SAMSOFT LAUNCHER - RECENT CHANGES", font=("Arial", 14, "bold"),
                            bg=THEME['bg'], fg=THEME['text'])
        changelog_label.pack(anchor="w", pady=(0, 20))

        # Updated changelog items
        changelog_items = [
            "🚀 Samsoft Launcher - Performance Optimized Edition",
            "⚡ FPS Limiter: Auto-configured maxFps=60 with VSync disabled",
            "🔧 Smart launch pipeline with pre-flight configuration",
            "🎨 Modern dark theme UI powered by Samsoft design system",
            "⚙️ Automatic Java 21 installation and management",
            "🖼️ Custom skin support with mod integration",
            "🌍 Full Samsoft version manifest support",
            "📁 All data stored in ~/.samsoft directory"
        ]

        for item in changelog_items:
            changelog_item_frame = tk.Frame(content_area, bg=THEME['sidebar'], padx=15, pady=10)
            changelog_item_frame.pack(fill="x", pady=(0, 10))
            tk.Label(changelog_item_frame, text=item, font=("Arial", 11),
                    bg=THEME['sidebar'], fg=THEME['text'], justify="left", anchor="w").pack(fill='x')

        # Load versions after UI is initialized
        self.load_version_manifest()

    def update_version_list(self, event=None):
        """Update the version list based on the selected category."""
        category = self.category_combo.get()
        self.version_combo['values'] = self.version_categories[category]
        if self.version_combo['values']:
            self.version_combo.current(0)

    def load_version_manifest(self):
        """Load the list of available Samsoft versions from servers."""
        try:
            with urllib.request.urlopen(VERSION_MANIFEST_URL) as url:
                manifest = json.loads(url.read().decode())
                
                # Clear existing categories
                for category in self.version_categories:
                    self.version_categories[category] = []
                
                # Categorize versions
                latest_release = None
                latest_snapshot = None
                
                for v in manifest["versions"]:
                    self.versions[v["id"]] = v["url"]
                    
                    # Track latest versions
                    if v["id"] == manifest["latest"]["release"]:
                        latest_release = v["id"]
                        self.version_categories["Latest Release"].append(v["id"])
                    elif v["id"] == manifest["latest"]["snapshot"]:
                        latest_snapshot = v["id"]
                        self.version_categories["Latest Snapshot"].append(v["id"])
                    
                    # Categorize by type
                    if v["type"] == "release":
                        if v["id"] != latest_release:
                            self.version_categories["Release"].append(v["id"])
                    elif v["type"] == "snapshot":
                        if v["id"] != latest_snapshot:
                            self.version_categories["Snapshot"].append(v["id"])
                    elif v["type"] == "old_beta":
                        self.version_categories["Old Beta"].append(v["id"])
                    elif v["type"] == "old_alpha":
                        self.version_categories["Old Alpha"].append(v["id"])
                
                # Update the version combo box
                self.update_version_list()
                
        except Exception as e:
            print(f"Error loading version manifest: {e}")
            messagebox.showerror("Error", "Failed to load version manifest. Check your internet connection.")

    def is_java_installed(self, required_version="21"):
        """Check if a compatible Java version (21 or higher) is installed."""
        try:
            result = subprocess.run(["java", "-version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            output = result.stderr
            match = re.search(r'version "(\d+)', output)
            if match:
                major_version = int(match.group(1))
                return major_version >= int(required_version)
            return False
        except Exception:
            return False

    def install_java_if_needed(self):
        """Install OpenJDK 21 if a compatible Java version is not found."""
        if self.is_java_installed():
            return
        print("Installing OpenJDK 21...")
        system = platform.system()
        if system == "Windows":
            java_url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_windows_hotspot_21.0.5_11.zip"
        elif system == "Linux":
            java_url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_linux_hotspot_21.0.5_11.tar.gz"
        elif system == "Darwin":
            java_url = "https://github.com/adoptium/temurin21-binaries/releases/download/jdk-21.0.5%2B11/OpenJDK21U-jdk_x64_mac_hotspot_21.0.5_11.tar.gz"
        else:
            messagebox.showerror("Error", "Unsupported OS")
            return

        archive_path = os.path.join(JAVA_DIR, "openjdk.zip" if system == "Windows" else "openjdk.tar.gz")
        os.makedirs(JAVA_DIR, exist_ok=True)

        try:
            urllib.request.urlretrieve(java_url, archive_path)
        except Exception as e:
            print(f"Failed to download Java: {e}")
            messagebox.showerror("Error", "Failed to download Java 21. Please check your internet connection or install Java manually.")
            return

        if system == "Windows":
            with zipfile.ZipFile(archive_path, "r") as zip_ref:
                zip_ref.extractall(JAVA_DIR)
        else:
            import tarfile
            with tarfile.open(archive_path, "r:gz") as tar_ref:
                tar_ref.extractall(JAVA_DIR)
            # Set execute permissions for Java binary on Linux and macOS
            java_bin = os.path.join(JAVA_DIR, "jdk-21.0.5+11", "bin", "java")
            os.chmod(java_bin, 0o755)  # Make Java executable
        os.remove(archive_path)
        print("Java 21 installed locally.")

    def select_skin(self):
        """Allow the user to select and apply a custom skin PNG file."""
        file_path = filedialog.askopenfilename(filetypes=[("PNG Files", "*.png")])
        if file_path:
            skin_dest = os.path.join(SAMSOFT_DIR, "skins")
            os.makedirs(skin_dest, exist_ok=True)
            shutil.copy(file_path, os.path.join(skin_dest, "custom_skin.png"))
            messagebox.showinfo("Skin Applied", "Skin applied successfully! Note: This may require a mod to apply in-game.")

    @staticmethod
    def verify_file(file_path, expected_sha1):
        """Verify the SHA1 checksum of a file."""
        with open(file_path, "rb") as f:
            file_hash = hashlib.sha1(f.read()).hexdigest()
        return file_hash == expected_sha1

    def download_version_files(self, version_id, version_url):
        """Download the version JSON, JAR, libraries, and natives with checksum verification."""
        print(f"⬇️ Downloading version files for {version_id}...")
        version_dir = os.path.join(VERSIONS_DIR, version_id)
        os.makedirs(version_dir, exist_ok=True)

        # Download version JSON
        version_json_path = os.path.join(version_dir, f"{version_id}.json")
        try:
            with urllib.request.urlopen(version_url) as url:
                data = json.loads(url.read().decode())
                with open(version_json_path, "w") as f:
                    json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Failed to download version JSON: {e}")
            messagebox.showerror("Error", f"Failed to download version {version_id} JSON.")
            return

        # Download and verify client JAR
        try:
            jar_url = data["downloads"]["client"]["url"]
            jar_path = os.path.join(version_dir, f"{version_id}.jar")
            expected_sha1 = data["downloads"]["client"]["sha1"]
            if not os.path.exists(jar_path) or not SamsoftLauncher.verify_file(jar_path, expected_sha1):
                urllib.request.urlretrieve(jar_url, jar_path)
                if not SamsoftLauncher.verify_file(jar_path, expected_sha1):
                    print(f"Checksum mismatch for {jar_path}")
                    messagebox.showerror("Error", f"Checksum mismatch for version {version_id} JAR.")
                    return
        except KeyError as e:
            print(f"Missing client JAR info in JSON: {e}")
            messagebox.showerror("Error", f"Version {version_id} is missing client JAR information.")
            return

        current_os = platform.system().lower()
        if current_os == "darwin":
            current_os = "osx"

        libraries_dir = os.path.join(SAMSOFT_DIR, "libraries")
        os.makedirs(libraries_dir, exist_ok=True)
        natives_dir = os.path.join(version_dir, "natives")
        os.makedirs(natives_dir, exist_ok=True)

        # Download libraries and natives
        for lib in data.get("libraries", []):
            if self.is_library_allowed(lib, current_os):
                # Download library artifact
                if "downloads" in lib and "artifact" in lib["downloads"]:
                    lib_url = lib["downloads"]["artifact"]["url"]
                    lib_path = os.path.join(libraries_dir, lib["downloads"]["artifact"]["path"])
                    os.makedirs(os.path.dirname(lib_path), exist_ok=True)
                    expected_sha1 = lib["downloads"]["artifact"]["sha1"]
                    if not os.path.exists(lib_path) or not SamsoftLauncher.verify_file(lib_path, expected_sha1):
                        try:
                            urllib.request.urlretrieve(lib_url, lib_path)
                            if not SamsoftLauncher.verify_file(lib_path, expected_sha1):
                                print(f"Checksum mismatch for {lib_path}")
                                messagebox.showerror("Error", f"Checksum mismatch for library {lib.get('name', 'unknown')}.")
                                return
                        except Exception as e:
                            print(f"Failed to download library {lib.get('name', 'unknown')}: {e}")

                # Download and extract natives
                if "natives" in lib and current_os in lib["natives"]:
                    classifier = lib["natives"][current_os]
                    if "downloads" in lib and "classifiers" in lib["downloads"] and classifier in lib["downloads"]["classifiers"]:
                        native_url = lib["downloads"]["classifiers"][classifier]["url"]
                        native_path = os.path.join(natives_dir, f"{classifier}.jar")
                        expected_sha1 = lib["downloads"]["classifiers"][classifier]["sha1"]
                        if not os.path.exists(native_path) or not SamsoftLauncher.verify_file(native_path, expected_sha1):
                            try:
                                urllib.request.urlretrieve(native_url, native_path)
                                if not SamsoftLauncher.verify_file(native_path, expected_sha1):
                                    print(f"Checksum mismatch for {native_path}")
                                    messagebox.showerror("Error", f"Checksum mismatch for native {lib.get('name', 'unknown')}.")
                                    return
                            except Exception as e:
                                print(f"Failed to download native {lib.get('name', 'unknown')}: {e}")
                                return
                        try:
                            with zipfile.ZipFile(native_path, "r") as zip_ref:
                                zip_ref.extractall(natives_dir)
                            os.remove(native_path)
                        except Exception as e:
                            print(f"Failed to extract native {lib.get('name', 'unknown')}: {e}")

        print("✅ Download complete!")

    def modify_options_txt(self, target_fps=60):
        """Modify options.txt to set maxFps and disable vsync."""
        options_path = os.path.join(SAMSOFT_DIR, "options.txt")
        options = {}
        if os.path.exists(options_path):
            try:
                with open(options_path, "r") as f:
                    for line in f:
                        parts = line.strip().split(":", 1)
                        if len(parts) == 2:
                            options[parts[0]] = parts[1]
            except Exception as e:
                print(f"Warning: Could not read options.txt: {e}")

        options['maxFps'] = str(target_fps)
        options['enableVsync'] = 'false'

        try:
            with open(options_path, "w") as f:
                for key, value in options.items():
                    f.write(f"{key}:{value}\n")
            print(f"⚙️ Set maxFps to {target_fps} and disabled vsync in options.txt.")
        except Exception as e:
            print(f"Warning: Could not write options.txt: {e}")

    def is_library_allowed(self, lib, current_os):
        """Check if a library is allowed on the current OS based on its rules."""
        if "rules" not in lib:
            return True
        allowed = False
        for rule in lib["rules"]:
            if rule["action"] == "allow":
                if "os" not in rule or (isinstance(rule.get("os"), dict) and rule["os"].get("name") == current_os):
                    allowed = True
            elif rule["action"] == "disallow":
                if "os" in rule and isinstance(rule.get("os"), dict) and rule["os"].get("name") == current_os:
                    allowed = False
        return allowed

    def evaluate_rules(self, rules, current_os):
        """Evaluate argument rules based on the current OS, ignoring feature-based rules."""
        if not rules:
            return True
        allowed = False
        for rule in rules:
            if "features" in rule:
                continue  # Skip feature-based rules
            if rule["action"] == "allow":
                if "os" not in rule or (isinstance(rule.get("os"), dict) and rule["os"].get("name") == current_os):
                    allowed = True
            elif rule["action"] == "disallow":
                if "os" in rule and isinstance(rule.get("os"), dict) and rule["os"].get("name") == current_os:
                    allowed = False
        return allowed

    def generate_offline_uuid(self, username):
        """Generate a UUID for offline mode based on the username."""
        offline_prefix = "OfflinePlayer:"  # Keep this for compatibility
        hash_value = hashlib.md5((offline_prefix + username).encode('utf-8')).hexdigest()
        uuid_str = f"{hash_value[:8]}-{hash_value[8:12]}-{hash_value[12:16]}-{hash_value[16:20]}-{hash_value[20:32]}"
        return uuid_str

    def build_launch_command(self, version, username, ram):
        """Construct the command to launch Samsoft."""
        version_dir = os.path.join(VERSIONS_DIR, version)
        json_path = os.path.join(version_dir, f"{version}.json")

        try:
            with open(json_path, "r") as f:
                version_data = json.load(f)
        except Exception as e:
            print(f"Failed to read version JSON: {e}")
            messagebox.showerror("Error", f"Cannot read version {version} JSON.")
            return []

        current_os = platform.system().lower()
        if current_os == "darwin":
            current_os = "osx"

        main_class = version_data.get("mainClass", "net.minecraft.client.main.Main")  # Keep original class for compatibility
        libraries_dir = os.path.join(SAMSOFT_DIR, "libraries")
        natives_dir = os.path.join(version_dir, "natives")
        jar_path = os.path.join(version_dir, f"{version}.jar")
        classpath = [jar_path]

        for lib in version_data.get("libraries", []):
            if "downloads" in lib and "artifact" in lib["downloads"]:
                lib_path = os.path.join(libraries_dir, lib["downloads"]["artifact"]["path"])
                if os.path.exists(lib_path):
                    classpath.append(lib_path)

        classpath_str = ";".join(classpath) if platform.system() == "Windows" else ":".join(classpath)
        java_path = "java" if self.is_java_installed() else os.path.join(JAVA_DIR, "jdk-21.0.5+11", "bin", "java.exe" if platform.system() == "Windows" else "java")

        command = [java_path, f"-Xmx{ram}G"]

        # JVM arguments
        jvm_args = []
        if "arguments" in version_data and "jvm" in version_data["arguments"]:
            for arg in version_data["arguments"]["jvm"]:
                if isinstance(arg, str):
                    jvm_args.append(arg)
                elif isinstance(arg, dict) and "rules" in arg and "value" in arg:
                    if self.evaluate_rules(arg["rules"], current_os):
                        if isinstance(arg["value"], list):
                            jvm_args.extend(arg["value"])
                        else:
                            jvm_args.append(arg["value"])

        if platform.system() == "Darwin" and "-XstartOnFirstThread" not in jvm_args:
            jvm_args.append("-XstartOnFirstThread")

        if not any("-Djava.library.path" in arg for arg in jvm_args):
            jvm_args.append(f"-Djava.library.path={natives_dir}")

        command.extend(jvm_args)

        # Game arguments
        game_args = []
        if "arguments" in version_data and "game" in version_data["arguments"]:
            for arg in version_data["arguments"]["game"]:
                if isinstance(arg, str):
                    game_args.append(arg)
                elif isinstance(arg, dict) and "rules" in arg and "value" in arg:
                    if self.evaluate_rules(arg["rules"], current_os):
                        if isinstance(arg["value"], list):
                            game_args.extend(arg["value"])
                        else:
                            game_args.append(arg["value"])
        elif "minecraftArguments" in version_data:
            game_args = version_data["minecraftArguments"].split()

        # Offline UUID
        uuid = self.generate_offline_uuid(username)

        # Placeholder replacements - KEEP ALL ORIGINAL VALUES FOR COMPATIBILITY
        replacements = {
            "${auth_player_name}": username,
            "${version_name}": version,
            "${game_directory}": SAMSOFT_DIR,  # Use Samsoft dir but game still sees it as game directory
            "${assets_root}": os.path.join(SAMSOFT_DIR, "assets"),
            "${assets_index_name}": version_data.get("assetIndex", {}).get("id", "legacy"),
            "${auth_uuid}": uuid,
            "${auth_access_token}": "0",
            "${user_type}": "legacy",
            "${version_type}": version_data.get("type", "release"),
            "${user_properties}": "{}",
            "${quickPlayRealms}": "",
        }

        def replace_placeholders(arg):
            for key, value in replacements.items():
                arg = arg.replace(key, value)
            return arg

        game_args = [replace_placeholders(arg) for arg in game_args]
        jvm_args = [replace_placeholders(arg) for arg in jvm_args]

        command.extend(["-cp", classpath_str, main_class] + game_args)
        return command

    def prepare_and_launch(self):
        """Wrapper function to handle setup before launching."""
        self.install_java_if_needed()
        self.modify_options_txt(target_fps=60)  # Set FPS limit before launch
        self.download_and_launch()  # Proceed with download/launch

    def download_and_launch(self):
        """Handle the download and launch process."""
        version = self.version_combo.get()
        if not version:
            messagebox.showerror("Error", "No version selected.")
            return

        username = self.username_input.get()
        if username == "Enter Username" or not username:
            username = "Steve"
        
        ram = int(self.ram_scale.get())
        version_url = self.versions.get(version)

        if not version_url:
            messagebox.showerror("Error", f"Version {version} URL not found.")
            return

        self.download_version_files(version, version_url)

        launch_cmd = self.build_launch_command(version, username, ram)
        if not launch_cmd:
            return

        print("🚀 Launching Samsoft:", " ".join(launch_cmd))
        try:
            subprocess.Popen(launch_cmd)
        except Exception as e:
            print(f"Failed to launch Samsoft: {e}")
            messagebox.showerror("Error", f"Failed to launch Samsoft: {e}")

if __name__ == "__main__":
    app = SamsoftLauncher()
    app.mainloop()
