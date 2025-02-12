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

# Main
server_address = config.get("Main", "ip")
server_port    = int(config.get("Main", "port"))
reload         = int(config.get("Automations", "reload_interval"))

masterserver_message = b''

def load_list_and_prepare_data():
    global masterserver_message
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

    # VIP
    for server in vip_servers:
        if(len(server) <= 1): continue
        data = server.split(":")
        prepare_server_data.append((data[0], int(data[1])))

    # Normal
    for server in normal_servers:
        if(len(server) <= 1): continue
        data = server.split(":")
        prepare_server_data.append((data[0], int(data[1])))

    start_header = b'\xff\xff\xff\xfff\n'
    end_header   = b'\x00\x00\x00\x00\x00\x00'

    masterserver_message = start_header + encoder.encode_multiple_server_reply(prepare_server_data) + end_header

    print(f"\n{Fore.RED}----------------Loaded File----------------")
    print(f"{Fore.RED}[*]{Fore.GREEN} MasterServer Loaded{Fore.CYAN} {str(len(vip_servers))}{Fore.GREEN} VIP Servers")
    print(f"{Fore.RED}[*]{Fore.GREEN} MasterServer Loaded{Fore.CYAN} {str(len(normal_servers))}{Fore.GREEN} Normal Servers")


def start_main_server():
    global global_socket
    socky = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    socky.bind((server_address, server_port))

    global_socket = socky

    load_list_and_prepare_data()

    print(f"{Fore.RED}[*]{Fore.GREEN} MasterServer Started...")

    while True:
        try:
            # Check for incoming messages
            msg, client = socky.recvfrom(64)

            # Prevent Overflow
            if len(msg) > 64:
                continue

            data = msg.split(b"\x00")
            header = data[0].split(b"\xff")

            if header[0] != b'\x31':
                print(f"{Fore.RED}[*]{Fore.GREEN} Received Invalid Header From Client {Fore.CYAN}{client[0]}.")
                continue

            filters = data[1]
            if b'gamedir' not in filters or b'nap' not in filters or b"cstrike" not in filters or b"10" not in filters:
                print(f"{Fore.RED}[*]{Fore.GREEN} Client Sent A Non MasterServer Query {Fore.CYAN}{client[0]}")
                continue

            socky.sendto(masterserver_message, client)
            print(f"{Fore.RED}[*]{Fore.GREEN} Sent MasterServers Data To Client {Fore.CYAN}{client[0]}")

        except socket.error:
            continue


def handle_incomming_commands(cmd):
    if cmd == "help":
        print(f"\n{Fore.GREEN}Available Commands")
        print(f"{Fore.GREEN}reload ->{Fore.CYAN} attempt to reload all servers from currents files.\n")
        pass
    elif cmd == "reload":
        load_list_and_prepare_data()


def main():
    threading.Thread(target=start_main_server, daemon=True).start()

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
