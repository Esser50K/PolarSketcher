#include <Arduino.h>
#include <Servo.h>
#include <ESP32Encoder.h>
#include "Stepper/Stepper.h"

// pins
const int enableStepper = 2;
const int angleStepPin = 19;
const int angleDirPin = 18;
const int amplitudeStepPin = 23;
const int amplitudeDirPin = 22;

const int zeroAnglePin = 32;
const int maxAnglePin = 33;
const int zeroAmplitudePin = 35;
const int maxAmplitudePin = 34;

const int encoderPhaseAPin = 27;
const int encoderPhaseBPin = 26;

const int penServoPin = 13;

const long BAUD_RATE = 921600;

// physical measurements
const int railLengthMm = 575;
const int penHolderRadiusMm = 12;
const int offsetMm = 25 + penHolderRadiusMm;
const int carriageLenghtMm = 84 - penHolderRadiusMm;
const int travelableDistanceMm = railLengthMm - offsetMm - carriageLenghtMm;

// max stepper positions
// will be filled by the controller and can be
// measured with the autoCalibrate function
long travelableDistanceSteps = 0;
float stepsPerMm = 0;
long minAmplitudePos = 0;
long maxAmplituePos = 0;
long maxAnglePos = 0;
long maxEncoderCount = 0;

// declare steppers
Stepper *amplitudeStepper;
Stepper *angleStepper;

// declare encoder
ESP32Encoder angleEncoder;

// pen servo
Servo penServo;

// modes
int currentMode = 0;
enum mode {
  idle,
  homing,
  autoCalibration,
  drawing
};

bool home() {
  penServo.write(0);

  bool zeroAmplitudePressed = digitalRead(zeroAmplitudePin) == 1 ? false : true;
  bool zeroAnglePressed = digitalRead(zeroAnglePin) == 1 ? false : true;

  if(zeroAmplitudePressed) {
    amplitudeStepper->setPosition(minAmplitudePos);
    amplitudeStepper->setTargetPosition(minAmplitudePos);
  } else {
    amplitudeStepper->singleStepAtSpeed(false);
  }

  if(zeroAnglePressed) {
    angleStepper->setPosition(0);
    angleStepper->setTargetPosition(0);

    // also reset encoder
    angleEncoder.setCount(0);
  } else {
    angleStepper->singleStepAtSpeed(false);
  }

  return zeroAmplitudePressed && zeroAnglePressed;
}

bool calibrated = false;
bool calibrating = false;
bool autoCalibrate() {
  if(calibrated){
    calibrated = false;
    travelableDistanceSteps = 0;
    stepsPerMm = 0;
    minAmplitudePos = 0;
    maxAmplituePos = 0;
    maxAnglePos = 0;
    maxEncoderCount = 0;
  }

  if(!calibrated && !calibrating && home()) {
    calibrating = true;
  }

  if(!calibrating){
    return false;
  }

  bool maxAmplitudePressed = digitalRead(maxAmplitudePin) == 1 ? false : true;
  bool maxAnglePressed = digitalRead(maxAnglePin) == 1 ? false : true;

  if(!maxAmplitudePressed)
    amplitudeStepper->singleStepAtSpeed(true);

  if(!maxAnglePressed)
    angleStepper->singleStepAtSpeed(true);

  // also check if stepsPerMm is 0, otherwise it has been calibrated already
  if(maxAmplitudePressed && stepsPerMm == 0) {
    travelableDistanceSteps = amplitudeStepper->getPosition();
    stepsPerMm = float(travelableDistanceSteps) / float(travelableDistanceMm);
    minAmplitudePos = long(offsetMm) * long(stepsPerMm);
    maxAmplituePos = travelableDistanceSteps + minAmplitudePos;

    amplitudeStepper->setPosition(maxAmplituePos);
    amplitudeStepper->setTargetPosition(maxAmplituePos);
  }

  if(maxAnglePressed) {
    maxAnglePos = angleStepper->getPosition();
    angleStepper->setPosition(maxAnglePos);
    angleStepper->setTargetPosition(maxAnglePos);
    // also set the encoder max
    maxEncoderCount = angleEncoder.getCount();
  }

  if(maxAmplitudePressed && maxAnglePressed){
    maxAmplituePos = amplitudeStepper->getPosition();
    maxAnglePos = angleStepper->getPosition();
    maxEncoderCount = angleEncoder.getCount();
    calibrating = false;
    calibrated = true;
    return true;
  }

  return false;
}

int encoderPosToAnglePos() {
  return map(angleEncoder.getCount(), 0, maxEncoderCount, 0, maxAnglePos);
}

struct position {
  int amplitudePosition;
  int anglePosition;
  int penPosition;
  int amplitudeVelocity;
  int angleVelocity;
};

const int futurePositionsLength = 100;
int previousPosition = 0;
int nextPositionToPlace = 1;
int nextPositionToGo = 0;
position futurePositions[futurePositionsLength];

// TODO play around with the logic
// could only correct after angle stepper moved a lot
int positionsSinceCorrection = 0;
const int correctAfterNPositions = 10;
bool draw() {
  // step toward target
  if (amplitudeStepper->getPosition() != amplitudeStepper->getTargetPosition() ||
      angleStepper->getPosition() != angleStepper->getTargetPosition()){
    amplitudeStepper->stepTowardTarget();
    angleStepper->stepTowardTarget();
  } else {
    // check if we have a new position to go to
    int potentialNextPositionToGo = (nextPositionToGo+1) % futurePositionsLength;
    if(potentialNextPositionToGo == nextPositionToPlace){
      return false;
    }

    // correct angle position
    positionsSinceCorrection = (positionsSinceCorrection+1) % correctAfterNPositions;
    if(positionsSinceCorrection == 0) {
      int realAnglePos = encoderPosToAnglePos();
      angleStepper->setPosition(encoderPosToAnglePos());
      // int errorThreshold = maxAnglePos * 0.0001;
      // if(abs(realAnglePos - angleStepper->getPosition()) > errorThreshold){
      //   angleStepper->setPosition(encoderPosToAnglePos());
      // }
    }

    // set new target
    nextPositionToGo = potentialNextPositionToGo;
    position nextPosition = futurePositions[nextPositionToGo];
    amplitudeStepper->setTargetPosition(nextPosition.amplitudePosition);
    angleStepper->setTargetPosition(nextPosition.anglePosition);
    amplitudeStepper->setSpeed(nextPosition.amplitudeVelocity);
    angleStepper->setSpeed(nextPosition.angleVelocity);

    // put pen in position
    // the +1 is just because the .read()
    // returns the last value we wrote -1 ¯\_(ツ)_/¯
    if(penServo.read()+1 != nextPosition.penPosition){
      penServo.write(nextPosition.penPosition);
      // without this delay the plotter starts
      // moving before the pen has reached the bottom
      delay(150);
    }
  }

  return false;
}

enum command {
  none,
  getStatus,
  setMode,
  calibrate,
  addPosition,
};

int readInt() {
  return Serial.read() + (Serial.read() << 8) + (Serial.read() << 16) + (Serial.read() << 24);
}

float readFloat() {
  float f;
  Serial.readBytes((char*)&f, 4);
  return f;
}

int commandBufferIdx = 0;
int commandBuffer[50]; 
bool parseCommand(int cmd){
  switch (cmd) {
  case setMode:
    if(Serial.available() < sizeof(int)) {
      return false;
    }

    commandBuffer[commandBufferIdx] = readInt();
    commandBufferIdx++;
    currentMode = commandBuffer[commandBufferIdx-1];
    return true;
  case getStatus:
    Serial.println(currentMode);
    Serial.println(calibrated);
    Serial.println(calibrating);

    Serial.println(amplitudeStepper->getPosition());
    Serial.println(amplitudeStepper->getTargetPosition());
    Serial.println(amplitudeStepper->getCurrentSpeed());

    Serial.println(angleStepper->getPosition());
    Serial.println(angleStepper->getTargetPosition());
    Serial.println(angleStepper->getCurrentSpeed());

    Serial.println(travelableDistanceSteps);
    Serial.println(stepsPerMm);
    Serial.println(minAmplitudePos);
    Serial.println(maxAmplituePos);
    Serial.println(maxAnglePos);
    Serial.println(angleEncoder.getCount());
    Serial.println(maxEncoderCount);
    Serial.println(nextPositionToPlace);
    Serial.println(nextPositionToGo);

    Serial.println(digitalRead(zeroAmplitudePin));
    Serial.println(digitalRead(maxAmplitudePin));
    Serial.println(digitalRead(zeroAnglePin));
    Serial.println(digitalRead(maxAnglePin));
    return true;
  case calibrate:
    // check if all the values are in the buffer
    if(Serial.available() < sizeof(int) * 6) {
      return false;
    }

    travelableDistanceSteps = readInt();
    stepsPerMm = readFloat();
    minAmplitudePos = readInt();
    maxAmplituePos = readInt();
    maxAnglePos = readInt();
    maxEncoderCount = readInt();
    amplitudeStepper->setPosition(minAmplitudePos);
    amplitudeStepper->setTargetPosition(minAmplitudePos);
    calibrated = true;
    return true;
  case addPosition:
    if(Serial.available() < sizeof(int)) {
      return false;
    }

    // check if we can read the next position
    // without overwriting a position the sketcher hasn't reached yet
    // TODO this triggers a bug because no new commands can be read until the stepper
    // moves to the desired position, the next commands will then overflow
    // the serial input buffer and make commands be misinterpreted
    // for now this is fixed on the sender side by getting the status
    // after writing a new position and holding on for new positions
    if(nextPositionToGo == nextPositionToPlace){
      return false;
    }

    // read parts of position until we have all the data
    commandBuffer[commandBufferIdx] = readInt();
    commandBufferIdx++;
    if(commandBufferIdx < 5){
      return false;
    }

    position p;
    p.amplitudePosition = commandBuffer[0];
    p.anglePosition = commandBuffer[1];
    p.penPosition = commandBuffer[2];
    p.amplitudeVelocity = commandBuffer[3];
    p.angleVelocity = commandBuffer[4];

    futurePositions[nextPositionToPlace] = p;
    nextPositionToPlace = (nextPositionToPlace+1) % futurePositionsLength;
    Serial.write(1);  // ack position added
    return true;
  default:
    return true;
  }

  // should never go here
  return true;
}

int currentCommand = 0;
void readInput() {
  // read command type
  if(currentCommand == 0){
    if(Serial.available() < sizeof(int)){
      return;
    }

    currentCommand = readInt();
    // let the command be read in the next loop iteration
  } else if(parseCommand(currentCommand)) {
    commandBufferIdx = 0;
    currentCommand = 0;
  }
}

void setup()
{
  Serial.setTxBufferSize(1024);
  Serial.setRxBufferSize(1024);
  Serial.begin(BAUD_RATE);

  // configure output pins
  pinMode(enableStepper, OUTPUT);
  pinMode(amplitudeStepPin, OUTPUT);
  pinMode(amplitudeDirPin, OUTPUT);
  pinMode(angleStepPin, OUTPUT);
  pinMode(angleDirPin, OUTPUT);

  // configure limit switches
  pinMode(zeroAmplitudePin, INPUT);
  pinMode(maxAmplitudePin, INPUT);
  pinMode(zeroAnglePin, INPUT);
  pinMode(maxAnglePin, INPUT);

  // enable and create steppers
  digitalWrite(enableStepper, LOW);  // enable is LOW for a4988 driver
  amplitudeStepper = new Stepper(amplitudeStepPin, amplitudeDirPin);
  angleStepper = new Stepper(angleStepPin, angleDirPin);

  // configure encoder
  ESP32Encoder::useInternalWeakPullResistors=UP;
	angleEncoder.attachHalfQuad(encoderPhaseAPin, encoderPhaseBPin);
	angleEncoder.setCount(0);

  // attach servo
  penServo.attach(penServoPin);
  penServo.write(0);
}

void loop()
{
  readInput();

  switch (currentMode) {
  case idle:
    break;
  case homing:
    amplitudeStepper->setSpeed(3500);
    angleStepper->setSpeed(1200);
    if(home())
      currentMode = idle;
    break;
  case autoCalibration:
    if(!calibrating)
      stepsPerMm = 0;
    amplitudeStepper->setSpeed(3500);
    angleStepper->setSpeed(1200);
    if(autoCalibrate())
      currentMode = homing;

    break;
  case drawing:
    if(draw())
      currentMode = idle;
    break;
  default:
    currentMode = idle;
    break;
  }
}
