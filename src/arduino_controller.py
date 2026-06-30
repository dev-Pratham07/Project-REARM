import serial
import serial.tools.list_ports
import time
import sys

# Connection state
connection_status = "OFFLINE" 
arduino = None

def connect():
    """Auto-detects and connects to Arduino."""
    global connection_status, arduino
    
    # If already connected, skip
    if is_connected():
        return True

    connection_status = "RECONNECTING"
    print("🔍 Scanning for Arduino...")
    
    # Get all available ports
    ports = serial.tools.list_ports.comports()
    target_port = None
    
    # Auto-detect logic: Look for "Arduino", "CH340", or "USB" keywords
    for p in ports:
        if "Arduino" in p.description or "CH340" in p.description or "USB" in p.description:
            target_port = p.device
            break
    
    # Fallback: If scan failed, try specific ports based on OS
    if not target_port:
        if sys.platform.startswith('win'):
            target_port = 'COM3' # Adjust for Windows
        else:
            target_port = '/dev/ttyUSB0' # Adjust for Linux
            
    try:
        if target_port:
            print(f"Attempting connection on {target_port}...")
            arduino = serial.Serial(target_port, 115200, timeout=1)
            
            connection_status = "ONLINE"
            print("✅ Arduino Connected Successfully!")
            list = [2,2,2,2,2]
            time.sleep(3)
            for i in range(5):
                list[i]=0
                send_to_arduino(list)
                time.sleep(0.5)
            time.sleep(1)
            send_to_arduino([2,2,2,2,2])
                
            return True
        else:
            print("❌ No Arduino found.")
            connection_status = "OFFLINE"
            return False
            
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        connection_status = "OFFLINE"
        arduino = None
        return False

def is_connected():
    """Checks if connection is still alive."""
    global arduino
    if arduino is None or not arduino.is_open:
        return False
        
    # Check if hardware is still plugged in
    try:
        active_ports = [p.device for p in serial.tools.list_ports.comports()]
        if arduino.port in active_ports:
            return True
        else:
            print("🔌 Device unplugged.")
            arduino.close()
            return False
    except:
        return False

def send_to_arduino(states):
    """Send finger states."""
    global connection_status
    if connection_status == "ONLINE" and arduino:
        try:
            # Format: 2,2,1,0,0\n
            data = ",".join(map(str, states)) + "\n"
            arduino.write(data.encode())
            #print(f"Sent: {data.strip()}")
        except Exception as e:
            print(f"⚠ Send Failed: {e}")
            connection_status = "OFFLINE"

def disconnect():
    global arduino, connection_status
    if arduino:
        arduino.close()
    connection_status = "OFFLINE"

def get_status():
    """Get current connection status."""
    return connection_status