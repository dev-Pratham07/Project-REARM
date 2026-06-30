/**
 * REARM (Robotic Enhancement and Assistive Rehabilitation Mechanism)
 * Arduino Controller Sketch
 * 
 * Description:
 * Receives servo control commands from the Python GUI/Computer Vision interface
 * via Serial communication. Expects comma-separated values representing the 
 * state of the 5 fingers (Thumb, Index, Middle, Ring, Pinky):
 *   0 = Closed, 1 = Half-Open, 2 = Fully Open
 * Example command: "2,2,1,0,0\n"
 */

#include <Servo.h>

// Number of fingers/servos
const int NUM_SERVOS = 5;

// Define Servo Pins
const int SERVO_PINS[NUM_SERVOS] = {2, 3, 4, 5, 6}; // Thumb, Index, Middle, Ring, Pinky

// Create Servo instances
Servo fingerServos[NUM_SERVOS];

/**
 * CALIBRATION SECTION:
 * Physical servos can be mounted in different orientations. Adjust these angles
 * if some of your fingers operate in reverse or require a limited range of motion.
 */
// Angles corresponding to state 0 (Closed)
const int CLOSED_ANGLES[NUM_SERVOS] = { 10,  10,  10,  10,  10 }; 
// Angles corresponding to state 1 (Half-Open)
const int HALF_ANGLES[NUM_SERVOS]   = { 90,  90,  90,  90,  90 }; 
// Angles corresponding to state 2 (Fully Open)
const int OPEN_ANGLES[NUM_SERVOS]   = { 170, 170, 170, 170, 170 }; 

// Variable to store serial inputs
String inputString = "";
bool stringComplete = false;

void setup() {
  // Start Serial communication at 115200 baud
  Serial.begin(115200);
  
  // Reserve 50 bytes for the input buffer
  inputString.reserve(50);
  
  // Attach servos and move them to initial open positions
  for (int i = 0; i < NUM_SERVOS; i++) {
    fingerServos[i].attach(SERVO_PINS[i]);
    fingerServos[i].write(OPEN_ANGLES[i]); // Move to default open on boot
  }
  
  // Print status to indicate readiness
  Serial.println("REARM Arduino Controller Initialized.");
}

void loop() {
  // Check if a full line has been received from Python
  if (stringComplete) {
    parseAndExecuteCommand(inputString);
    
    // Clear the string for the next command
    inputString = "";
    stringComplete = false;
  }
}

/**
 * Parses a comma-separated string containing 5 integer states.
 * Expected Format: T,I,M,R,P (e.g., "2,2,1,0,0")
 */
void parseAndExecuteCommand(String command) {
  command.trim(); // Remove leading/trailing whitespaces or newlines
  
  int values[NUM_SERVOS];
  int currentIndex = 0;
  int lastCommaIndex = 0;
  
  // Parse comma-separated states
  for (int i = 0; i < command.length(); i++) {
    if (command.charAt(i) == ',' || i == command.length() - 1) {
      String segment = "";
      if (i == command.length() - 1 && command.charAt(i) != ',') {
        segment = command.substring(lastCommaIndex);
      } else {
        segment = command.substring(lastCommaIndex, i);
      }
      
      if (currentIndex < NUM_SERVOS) {
        values[currentIndex] = segment.toInt();
        currentIndex++;
      }
      
      lastCommaIndex = i + 1;
    }
  }
  
  // If we successfully parsed exactly 5 finger values, write to servos
  if (currentIndex == NUM_SERVOS) {
    for (int i = 0; i < NUM_SERVOS; i++) {
      int state = values[i];
      int targetAngle = OPEN_ANGLES[i]; // Fallback default
      
      if (state == 0) {
        targetAngle = CLOSED_ANGLES[i];
      } else if (state == 1) {
        targetAngle = HALF_ANGLES[i];
      } else if (state == 2) {
        targetAngle = OPEN_ANGLES[i];
      }
      
      // Write the mapped angle to the servo
      fingerServos[i].write(targetAngle);
    }
  }
}

/**
 * SerialEvent occurs whenever new data comes in the hardware serial RX.
 * This function reads characters until a newline character is encountered.
 */
void serialEvent() {
  while (Serial.available()) {
    char inChar = (char)Serial.read();
    
    // If the incoming character is a newline, set flag
    if (inChar == '\n') {
      stringComplete = true;
    } else {
      inputString += inChar;
    }
  }
}
