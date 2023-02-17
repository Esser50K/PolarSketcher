#include <Arduino.h>
#include "Stepper/Stepper.h"
#include <ESP32Encoder.h>

// pins
const int enableStepper = 9;
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

const long BAUD_RATE = 115200;

// physical measurements
const int railLengthMm = 599;
const int penHolderRadiusMm = 12;
const int offsetMm = 25 + penHolderRadiusMm;
const int carriageLenghtMm = 84 - penHolderRadiusMm;
const int travelableDistanceMm = railLengthMm - offsetMm - carriageLenghtMm;

// limit switch states
bool zeroAmplitudePressed = false;
bool maxAmplitudePressed = false;
bool zeroAnglePressed = false;
bool maxAnglePressed = false;

// max stepper positions
// will be filled by the controller and can be
// measured with the autoCalibrate function
long travelableDistanceSteps = 0;
double stepsPerMm = 0;
long minAmplitudePos = 0;
long maxAmplituePos = 0;
long maxAnglePos = 0;
long maxEncoderCount = 0;

// declare steppers
Stepper *amplitudeStepper;
Stepper *angleStepper;

// declare encoder
ESP32Encoder angleEncoder;

// modes
int currentMode = 0;
enum mode {
  idle,
  info,
  homing,
  autoCalibration,
  drawing,
};


// limit switch interrupts
void zeroAmplitudeInterrupt() {
  zeroAmplitudePressed = digitalRead(zeroAmplitudePin) == 1 ? false : true;
}

void maxAmplitudeInterrupt() {
  maxAmplitudePressed = digitalRead(maxAmplitudePin) == 1 ? false : true;
}

void zeroAngleInterrupt() {
  zeroAnglePressed = digitalRead(zeroAnglePin) == 1 ? false : true;
}

void maxAngleInterrupt() {
  maxAnglePressed = digitalRead(maxAnglePin) == 1 ? false : true;
}

bool home() {
  if(zeroAmplitudePressed) {
    amplitudeStepper->setPosition(minAmplitudePos);
    amplitudeStepper->setTargetPosition(minAmplitudePos);
  }

  if(zeroAnglePressed) {
    angleStepper->setPosition(0);
    angleStepper->setTargetPosition(0);

    // also reset encoder
    angleEncoder.setCount(0);
  }
  
  if(!zeroAmplitudePressed) {
    amplitudeStepper->singleStepAtSpeed(false);
  }

  if(!zeroAnglePressed) {
    angleStepper->singleStepAtSpeed(false);
  }

  if(zeroAmplitudePressed && zeroAnglePressed){
    return true;
  }

  return false;
}

bool calibrated = false;
bool calibrating = false;
bool autoCalibrate() {
  if(!calibrated && !calibrating && home()) {
    calibrating = true;
  }

  if(!calibrating){
    return false;
  }

  if(!maxAmplitudePressed)
    amplitudeStepper->singleStepAtSpeed(true);

  if(!maxAnglePressed)
    angleStepper->singleStepAtSpeed(true);

  // also check if stepsPerMm is 0, otherwise it has been calibrated already
  if(maxAmplitudePressed && stepsPerMm == 0) {
    travelableDistanceSteps = amplitudeStepper->getPosition();
    stepsPerMm = double(travelableDistanceSteps) / double(travelableDistanceMm);
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

    // TODO send these values back to controller in order to calibrate it
    Serial.println("Travel distance steps is: " + String(travelableDistanceSteps));
    Serial.println("Steps per mm is: " + String(stepsPerMm));
    Serial.println("Min Amplitude Pos is: " + String(minAmplitudePos));
    Serial.println("Max Amplitude Pos is: " + String(maxAmplituePos));
    Serial.println("Max Angle Pos is: " + String(maxAnglePos));
    Serial.println("Max Encoder Count is: " + String(maxEncoderCount));
    calibrating = false;
    calibrated = true;
    return true;
  }

  return false;
}

struct position {
  int amplitudePosition;
  int anglePosition;
  int maxVelocity;
};

const int futurePositionsLength = 20;
int previousPosition = 0;
int nextPositionToPlace = 0;
int nextPositionToGo = 0;
position futurePositions[futurePositionsLength];
bool draw() {
  // read next positions in case we got space for it
  if(Serial.available() && nextPositionToGo != nextPositionToPlace){
    position p;
    p.amplitudePosition = Serial.parseInt();
    p.anglePosition = Serial.parseInt();
    p.maxVelocity = Serial.parseInt();
    futurePositions[nextPositionToPlace] = p;
    nextPositionToPlace = (nextPositionToPlace+1) % futurePositionsLength;
  }

  // step toward target
  if (amplitudeStepper->getPosition() != amplitudeStepper->getTargetPosition() ||
      angleStepper->getPosition() != angleStepper->getTargetPosition()){
    amplitudeStepper->stepTowardTarget();
    angleStepper->stepTowardTarget();
  } else {
    // set new target
    position nextPosition = futurePositions[nextPositionToGo];
    amplitudeStepper->setTargetPosition(nextPosition.amplitudePosition);
    angleStepper->setTargetPosition(nextPosition.anglePosition);
    amplitudeStepper->setSpeed(nextPosition.maxVelocity);
    angleStepper->setSpeed(nextPosition.maxVelocity);
    nextPositionToGo = (nextPositionToGo+1) % futurePositionsLength;
  }

  return false;
}

void setup()
{
  Serial.begin(BAUD_RATE);

  // configure output pins
  pinMode(enableStepper, OUTPUT);
  pinMode(amplitudeStepPin, OUTPUT);
  pinMode(amplitudeDirPin, OUTPUT);
  pinMode(angleStepPin, OUTPUT);
  pinMode(angleDirPin, OUTPUT);

  // configure limit switches
  pinMode(zeroAmplitudePin, INPUT_PULLUP);
  pinMode(maxAmplitudePin, INPUT_PULLUP);
  pinMode(zeroAnglePin, INPUT_PULLUP);
  pinMode(maxAmplitudePin, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(zeroAmplitudePin), zeroAmplitudeInterrupt, CHANGE);
  attachInterrupt(digitalPinToInterrupt(maxAmplitudePin), maxAmplitudeInterrupt, CHANGE);
  attachInterrupt(digitalPinToInterrupt(zeroAnglePin), zeroAngleInterrupt, CHANGE);
  attachInterrupt(digitalPinToInterrupt(maxAnglePin), maxAngleInterrupt, CHANGE);

  // enable and create steppers
  digitalWrite(enableStepper, HIGH);
  amplitudeStepper = new Stepper(amplitudeStepPin, amplitudeDirPin);
  angleStepper = new Stepper(angleStepPin, angleDirPin);

  // configure encoder
  ESP32Encoder::useInternalWeakPullResistors=UP;
	angleEncoder.attachHalfQuad(encoderPhaseAPin, encoderPhaseBPin);
	angleEncoder.setCount(0);

  // check if it is already homed
  zeroAmplitudePressed = digitalRead(zeroAmplitudePin) == 1 ? false : true;
  zeroAnglePressed = digitalRead(zeroAnglePin) == 1 ? false : true;
}

long loop_counter = 0;
void loop()
{
  switch (currentMode) {
  case idle:
    break;
  case info:
    Serial.println("Amplitude Stepper position is: " + String(amplitudeStepper->getPosition()));
    Serial.println("Angle Stepper position is: " + String(angleStepper->getPosition()));
    Serial.println("Travel distance steps is: " + String(travelableDistanceSteps));
    Serial.println("Steps per mm is: " + String(stepsPerMm));
    Serial.println("Min Amplitude Pos is: " + String(minAmplitudePos));
    Serial.println("Max Amplitude Pos is: " + String(maxAmplituePos));
    Serial.println("Max Angle Pos is: " + String(maxAnglePos));
    Serial.println("Max Encoder Count is: " + String(maxEncoderCount));
    currentMode = idle;
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
    break;
  }

  if(currentMode != drawing && Serial.available()){
    String newMode = Serial.readStringUntil('\n');
    currentMode = newMode.toInt();
    Serial.println("Set new mode to " + newMode);
  }

  if(loop_counter == 100000){
    Serial.println("Current mode " + String(currentMode));
    loop_counter = 0;
  }

  loop_counter++;
}

/*
Max Amplitude Pos is: 38465
Max Angle Pos is: 15829
Max Encoder Count is: 1218

Max Amplitude Pos is: 38464
Max Angle Pos is: 14894
Max Encoder Count is: 1219

Max Amplitude Pos is: 38472
Max Angle Pos is: 14827
Max Encoder Count is: 1218

Max Amplitude Pos is: 38475
Max Angle Pos is: 14838
Max Encoder Count is: 1219
*/