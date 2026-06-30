import cv2
import time
import HandTrackingModule as htm
import arduino_controller as ac
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="google.protobuf")

wCam, hCam = 640, 480
pTime = 0
finger_state = [0, 0, 0, 0, 0]  # [Thumb, index, middle, ring, pinky] default open hand (0 closed, 1 half, 2 open)
hand = False
temp = 0

cap = None
detector = None
0, 0, 0, 0, 
            
def UI_setup():
    cv2.rectangle(img, (0,0), (wCam, 75), (225, 136, 0), cv2.FILLED)
    cv2.rectangle(img, (5,0), (wCam-5,70), (32,32,32), cv2.FILLED)
    
    cv2.putText(img, 'Robotic Hand Controller', (100, 45), cv2.FONT_HERSHEY_COMPLEX, 1, (225, 136, 0), 1)
    cv2.putText(img, f'FPS: {fps():.1f}', (wCam -100, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    online_txt(ac.get_status())
    
    #Finger status box
    cv2.rectangle(img, (8,78), (162, 222), (225, 136, 0), 2)
    cv2.rectangle(img, (10, 80), (160, 220), (32,32,32), cv2.FILLED)
    cv2.putText(img, 'Finger Status', (32, 95), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    finger_status(25,100, finger_state[0], "THB")
    finger_status(50,100, finger_state[1], "IDX")
    finger_status(75,100, finger_state[2], "MID")
    finger_status(100,100, finger_state[3], "RNG") 
    finger_status(125,100, finger_state[4], "PNK")
    
    #gusture box
    cv2.rectangle(img, (8, hCam-25), (162, hCam-60), (225,136,0), 2)
    cv2.rectangle(img, (10, hCam-25), (160, hCam-60), (32,32,32), cv2.FILLED)
    cv2.putText(img, f'Gesture: {gesture(finger_state)}', (13,hCam-37), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    #controls
    cv2.putText(img, 'R to Reconnect', (wCam-150,hCam-60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (225,136,0), 1)
    cv2.putText(img, 'Q to Exit', (wCam-150,hCam-40), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (225,136,0), 1)
    
def finger_status(x, y, status, finger=""):
    cv2.rectangle(img, (x-2, y-2), (x+22, y+102), (255,255,255), 1)
    if status==2:
        cv2.rectangle(img, (x, y), (x+20, y+100), (0,255,0), cv2.FILLED)
    elif status==1:
        cv2.rectangle(img, (x, y+50), (x+20, y+100), (0, 184, 255), cv2.FILLED)
    else:
        cv2.rectangle(img, (x, y+90), (x+20, y+100), (0,0,255), cv2.FILLED)   
    cv2.putText(img, finger, (x, y+115), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

def fps():
    global pTime
    cTime= time.time()
    fps= 1 / (cTime - pTime) if cTime>pTime else 0
    pTime= cTime
    return fps
    
def online_txt(status):
    if status == "ONLINE":
        cv2.circle(img, (wCam - 95, 45), 5, (0, 255, 0), cv2.FILLED)
        cv2.putText(img, "ONLINE", (wCam-80, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)
    elif status == "RECONNECTING":
        cv2.circle(img, (wCam - 115, 45), 5, (0, 165, 255), cv2.FILLED)
        cv2.putText(img, "CONNECTING", (wCam-100, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 165, 255), 1)
    else:
        cv2.circle(img, (wCam - 95, 45), 5, (0, 0, 255), cv2.FILLED)
        cv2.putText(img, "OFFLINE", (wCam-80, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 1)
    
def finger_state_update(lmList):
    global finger_state
    lms = lmList[0]["lmList"]

    fingers = [
        (1, 8, 7, 5),   # Index
        (2, 12, 11, 9),  # Middle
        (3, 16, 15, 13), # Ring
        (4, 20, 19, 17)  # Pinky
    ]

    for state_idx, tip, mid, base in fingers:
        if lms[tip][2] > lms[base][2]:
            finger_state[state_idx] = 0
        elif lms[tip][2] > lms[mid][2]:
            finger_state[state_idx] = 1
        else:
            finger_state[state_idx] = 2

    if lms[4][1] > lms[2][1]:
        finger_state[0] = 0
    elif lms[4][1] > lms[3][1]:
        finger_state[0] = 1
    else:
        finger_state[0] = 2

def open_():
    global finger_state
    finger_state=[2,2,2,2,2]
    ac.send_to_arduino(finger_state)
    
def gesture(finger_state):
    patterns = {
        # --- Basic Forms ---
        (2, 2, 2, 2, 2): "PALM",
        (0, 0, 0, 0, 0): "FIST",
        (1, 1, 1, 1, 1): "CLAW",
        
        # --- Numbers ---
        (0, 2, 0, 0, 0): "Point",
        (0, 2, 2, 2, 0): "THREE",
        (0, 2, 2, 2, 2): "FOUR",
        
        # --- Directional / Pointing ---
        (2, 0, 0, 0, 0): "THUMBS UP",
        (2, 2, 0, 0, 0): "L-SHAPE",
        (0, 0, 0, 0, 2): "PINKY POINT",
        
        # --- Common Signs ---
        (0, 2, 0, 0, 2): "ROCK",
        (2, 0, 0, 0, 2): "LOOSE",
        (2, 2, 0, 0, 2): "YO YO",
        (0, 2, 2, 0, 0): "PEACE",
        (0, 0, 2, 0, 0): "BRUH",
        
        # --- Precision / Grips ---
        (1, 0, 2, 2, 2): "OK SIGN", # Thumb/Index touching (0,0) or (1,1)
        (2, 1, 0, 0, 0): "PINCH"
    }
    return patterns.get(tuple(finger_state), "UNKNOWN")

def main():
    global hand, pTime, finger_state, temp, img, cap, detector
    
    # Initialize camera and detector
    cap = cv2.VideoCapture(0)
    detector = htm.handDetector(detectionCon=0.9, maxHands=1)
    
    # Only connect if not already connected
    if not ac.is_connected():
        ac.connect()    
    while True:
        success, img = cap.read()
        img = cv2.flip(img, 1)
        img = detector.findHands(img, draw=hand)
        lmList = detector.findPosition(img, draw=hand)
        UI_setup()
        
        if len(lmList) != 0:
            if lmList[0]['handedness'] != "Right":
                cv2.putText(img, "Use Right Hand", (wCam-150, hCam-25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
                hand = False
            else:
                hand= True
                finger_state_update(lmList)
                #print(finger_state)
                # print(lmList[0]["lmList"][0][2])
                ac.send_to_arduino(finger_state)
                
        else:
            cv2.putText(img, "No Hand Detected", (wCam-150, hCam-25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        

        if temp == 0:
            print("Starting REARM wait a few moments.")
            temp= temp +1
            print("""
        =========================================================
                    ROBOTIC HAND CONTROLLER
                Controls:'Q' Quit | 'R' Reconnect
        =========================================================
        """)
        cv2.imshow("Project REARM", img)
        
        key = cv2.waitKey(1) & 0xFF
        if key == ord('r'):
            ac.connect()
        if key == ord('q'):
            print("Shutting Down REARM...")
            break
    
    if cap:
        cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()