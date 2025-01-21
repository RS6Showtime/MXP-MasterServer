def encode_multiple_server_reply(servers):
    """
    Encodes a reply packet containing multiple servers.
    
    Args:
        servers (list of tuples): A list of servers, where each server is a tuple (IP, port).
                                  Example: [("192.168.0.0", 27015), ("192.168.0.1", 27016)]
    
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
