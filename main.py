import socket
import configparser
import colorama
from colorama import Fore, Style
from tools import encoder
import sys
import signal
import select
import threading
import time

colorama.init(True)

global_socket = None

def signal_handler(sig, frame):
    global global_socket

    if global_socket:
        global_socket.close()

    print(f'\n{Fore.RED}[*]{Fore.GREEN} MasterServer Stopped...')
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

__CONFIG_NAME__     = "config.ini"
__SERVERS_VIP__     = "csservers_vip.txt"
__SERVERS_NORMAL__  = "csservers.txt"

config = configparser.ConfigParser()
config.read(__CONFIG_NAME__)

server_address            = config.get("Main", "ip")
server_port               = int(config.get("Main", "port"))

start_header = b'\xff\xff\xff\xfff\n'
end_header   = b'\x00\x00\x00\x00\x00\x00'

masterserver_message_vip = b''
masterserver_message = b''

# clients_delay_response = {}

def load_list_and_prepare_data():
    global masterserver_message, masterserver_message_vip
    # Load Servers

    try:
        with open(__SERVERS_VIP__, "r") as f:
            vip_servers = [line.strip() for line in f]
    except FileNotFoundError:
        print(f"{Fore.RED}[*]{Fore.GREEN} File{Fore.RED} {__SERVERS_VIP__}{Fore.GREEN} was not found")
        exit(1)

    try:
        with open(__SERVERS_NORMAL__, "r") as f:
            normal_servers = [line.strip() for line in f]
    except FileNotFoundError:
        print(f"{Fore.RED}[*]{Fore.GREEN} File{Fore.RED} {__SERVERS_NORMAL__}{Fore.GREEN} was not found")
        exit(1)

    # Appending all Servers by the best orders
    prepare_server_data = []
    prepare_server_data.clear()

    # VIP
    for server in vip_servers:
        if(len(server) <= 1): continue
        data = server.split(":")
        prepare_server_data.append((data[0], int(data[1])))

    masterserver_message_vip = encoder.encode_multiple_server_reply(prepare_server_data)

    # Normal
    for server in normal_servers:
        if(len(server) <= 1): continue
        data = server.split(":")
        prepare_server_data.append((data[0], int(data[1])))

    masterserver_message = start_header + encoder.encode_multiple_server_reply(prepare_server_data)
    

    print(f"\n{Fore.RED}----------------Loaded File----------------")
    print(f"{Fore.RED}[*]{Fore.GREEN} MasterServer Loaded{Fore.CYAN} {str(len(vip_servers))}{Fore.GREEN} VIP Servers")
    print(f"{Fore.RED}[*]{Fore.GREEN} MasterServer Loaded{Fore.CYAN} {str(len(normal_servers))}{Fore.GREEN} Normal Servers")

def start_main_server():
    global global_socket

    # Main
    delay_show_normal_servers = float(config.get("Automations", "delay_show_normal_servers"))
    hold_connexion_closed     = float(config.get("Automations", "hold_connexion_closed"))
    force_conexion_to_close   = float(config.get("Automations", "force_conexion_to_close"))
    whitelist_ips             = config.get('Whitelist', 'Whitelist_ips')

    # Extra WhiteList IPS
    ips_list = whitelist_ips.split() 

    socky = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socky.bind((server_address, server_port))

    global_socket = socky

    load_list_and_prepare_data()

    print(f"{Fore.RED}[*]{Fore.GREEN} MasterServer Started...")

    client_delay_force_close_connexion = {}
    clients_delay_response = {}
    client_delay_show_normal_servers = {}

    # Intern data
    intern_start_header = start_header
    intern_end_header   = end_header

    while True:
        try:
            # Check for incoming messages
            msg, client = socky.recvfrom(64)
            ip = client[0]

            # Save current Time
            new_current_time = time.time()

            # Check if it's the time to close the connexion with the client
            # We can't really close, but we can force counter-strike 1.6 to stop sending us messages.
            # Will send last header which is format with "\x00" * 6
            # So we won't receive anything from him
            if ip in client_delay_force_close_connexion:
                # Is it the time? Yep, it is :P
                if client_delay_force_close_connexion[ip] < new_current_time:
                    socky.sendto(end_header, client)
                    del client_delay_force_close_connexion[ip]
                    print(f"{Fore.RED}[*]{Fore.GREEN} Clossed Connexion With Client {Fore.CYAN}{client[0]}{Fore.GREEN} [Connected For To Much]")
                    continue # Ignore Incomming Packets

            # Delay Showing VIP + Normal Servers
            if ip in client_delay_show_normal_servers:
                # It's the time to re-send vip + normal servers
                # GoldSrc will cache first received servers and will keep it's position
                if client_delay_show_normal_servers[ip] < new_current_time:
                    socky.sendto(masterserver_message + masterserver_message_vip, client)
                    del client_delay_show_normal_servers[ip]
                    print(f"{Fore.RED}[*]{Fore.GREEN} Sent MasterServers Data To Client {Fore.CYAN}{client[0]}{Fore.GREEN} [Header Start + VIP Servers + Normal Servers]")
                    continue # Ignore Incomming Packets

            # Pending MasterServer. Ignore
            if ip in clients_delay_response:
                # User closed the connexion or stopped sending packets
                if clients_delay_response[ip] < new_current_time:
                    del clients_delay_response[ip]

                    # Reset Vars
                    if ip in client_delay_show_normal_servers:
                        del client_delay_show_normal_servers[ip]
                    if ip in client_delay_force_close_connexion:
                        del client_delay_force_close_connexion[ip]
                else:
                    # Client is still sending us packets
                    clients_delay_response[ip] = new_current_time + hold_connexion_closed
                    continue # Ignore Incomming Packets

            # Prevent Overflow
            if len(msg) > 64:
                continue # Ignore Incomming Packets

            data = msg.split(b"\x00")
            header = data[0].split(b"\xff")

            if header[0] != b'\x31':
                print(f"{Fore.RED}[*]{Fore.GREEN} Received Invalid Header From Client {Fore.CYAN}{client[0]}.")
                continue # Ignore Incomming Packets

            filters = data[1]
            if b'gamedir' not in filters or b'nap' not in filters or b"cstrike" not in filters or b"10" not in filters:
                print(f"{Fore.RED}[*]{Fore.GREEN} Client Sent A Non MasterServer Query {Fore.CYAN}{client[0]}")
                continue # Ignore Incomming Packets
            
            if client[0] not in ips_list:
                socky.sendto(intern_start_header + masterserver_message_vip, client)
                print(f"{Fore.RED}[*]{Fore.GREEN} Sent MasterServers Data To Client {Fore.CYAN}{client[0]}{Fore.GREEN} [Header Start + VIP Servers]")

                # Save client ip as a copy of his request. Counter-Strike will always ask for finish of the list.
                # So while client is flooding us, we will wait until we detect a delay from his requests.
                # This mean that user disconnected from our server and stopped sending MasterServer Requests Servers
                current_time = time.time()
                user_ip = client[0]
                clients_delay_response[user_ip] = current_time + hold_connexion_closed
                client_delay_show_normal_servers[user_ip] = current_time + delay_show_normal_servers
                client_delay_force_close_connexion[user_ip] = current_time + force_conexion_to_close
            else:
                # Fully sending all servers to whitelisted ips
                socky.sendto(masterserver_message + masterserver_message_vip + intern_end_header, client)
                print(f"{Fore.RED}[*]{Fore.GREEN} Sent MasterServers Data To Client {Fore.CYAN}{client[0]}{Fore.GREEN} [Header Start + Data + Header End] [WhiteList IP]")

        except socket.error:
            continue # Ignore Sockets errors


def handle_incomming_commands(cmd):
    match cmd:
        case "help":
            print(f"\n{Fore.GREEN}Available Commands")
            print(f"{Fore.GREEN}reload ->{Fore.CYAN} attempt to reload all servers from currents files.\n")
            pass
        case "reload":
            load_list_and_prepare_data()

def main():
    threading.Thread(target=start_main_server, daemon=True).start()

    reload = int(config.get("Automations", "reload_interval"))

    def f_reload_interval_for_master_list():
        while True:
            time.sleep(reload)
            load_list_and_prepare_data()

    thread = threading.Thread(target=f_reload_interval_for_master_list, daemon=True)
    thread.start()

    print(f"{Fore.GREEN}--------------------------------------")
    print(f"{Fore.RED}--------------MXP-MASTER--------------")
    print(f"{Fore.GREEN}--------------------------------------\n")

    # Do some delay before activating input listener from client
    time.sleep(1)
    
    while True:
        cmd = input(f"{Fore.GREEN}Enter a command:{Style.RESET_ALL} ")
        handle_incomming_commands(cmd)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
    except OSError as error:
        if 'Only one usage of each socket address' in str(error):
            print(f"\n{Fore.RED}[*]{Fore.GREEN} Port{Fore.CYAN} {server_port}{Fore.GREEN} Already In Use By Another Process")
        else:
            print(f"\n{Fore.RED}[*]{Fore.GREEN} Error: {error}")
