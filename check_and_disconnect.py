import socket, json

def cmd(method, params):
    s = socket.socket()
    s.connect(('localhost', 55556))
    s.sendall(json.dumps({'method': method, 'params': params}).encode())
    result = s.recv(4096).decode()
    s.close()
    return json.loads(result)

# Check status
print("Checking status...")
status = cmd('status', {'port': 'COM9'})
print(f"Status: {status}")

if status.get('connected'):
    print("\nDisconnecting...")
    result = cmd('disconnect', {'port': 'COM9'})
    print(f"Disconnect result: {result}")
