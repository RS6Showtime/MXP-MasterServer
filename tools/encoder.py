def encode_multiple_server_reply(servers):
    """
    Encodes a reply packet containing multiple servers.
    
    Args:
        servers (list of tuples): A list of servers, where each server is a tuple (IP, port).
                                  Example: [("93.114.82.24", 27015), ("192.168.0.1", 27016)]
    
    Returns:
        bytes: Encoded packet with all servers.
    """
    try:
        reply_packet = b""
        
        for server in servers:
            ip, port = server
            
            # Convert IP address to bytes
            ip_parts = ip.split('.')
            if len(ip_parts) != 4:
                raise ValueError(f"Invalid IP format: {ip}. Expected format: 'x.x.x.x'")
            ip_bytes = bytes(int(part) for part in ip_parts)
            
            # Convert port to bytes (big-endian)
            port_bytes = port.to_bytes(2, byteorder='big')
            
            # Append encoded server to the packet
            reply_packet += ip_bytes + port_bytes
        
        return reply_packet

    except Exception as e:
        print(f"Error while encoding servers: {e}")
        return b""

# servers = [
#     ("93.114.82.24", 27015),  # Server 1
#     ("192.168.0.1", 27016),   # Server 2
#     ("127.0.0.1", 27017)      # Server 3
# ]


# # Encodare
# encoded_packet = encode_multiple_server_reply(servers)

# # Afișare pachet
# print(f"Encoded packet: {encoded_packet}")