#include "Stepper/Stepper.h"
#include "SerialUtils/SerialUtils.h"
#include <Arduino.h>
#include <ESP32Encoder.h>
#include <Servo.h>

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

const long BAUD_RATE = 115200;

// physical measurements
const int railLengthMm = 585;
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
enum mode
{
  idle,
  homing,
  autoCalibration,
  drawing
};

bool digitalReadCheck(int pin, int expected, int nChecks)
{
  int checks = 0;
  while (digitalRead(pin) == expected && checks < nChecks)
  {
    checks++;
  }

  // if it looped through it means that the result is consistently what we expect
  return checks == nChecks;
}

bool home()
{
  penServo.write(0);

  bool zeroAmplitudePressed = digitalRead(zeroAmplitudePin) == 1 ? false : true;
  bool zeroAnglePressed = digitalRead(zeroAnglePin) == 1 ? false : true;

  if (zeroAmplitudePressed)
  {
    amplitudeStepper->setPosition(minAmplitudePos);
    amplitudeStepper->setTargetPosition(minAmplitudePos);
  }
  else
  {
    amplitudeStepper->singleStepAtSpeed(false);
  }

  if (zeroAnglePressed)
  {
    angleStepper->setPosition(0);
    angleStepper->setTargetPosition(0);

    // also reset encoder
    angleEncoder.setCount(0);
  }
  else
  {
    angleStepper->singleStepAtSpeed(false);
  }

  // perform extra checks because of flaky reads
  int necessaryChecks = 5;
  return digitalReadCheck(zeroAmplitudePin, 0, necessaryChecks) && digitalReadCheck(zeroAnglePin, 0, necessaryChecks);
}

bool calibrated = false;
bool calibrating = false;
bool autoCalibrate()
{
  if (calibrated)
  {
    calibrated = false;
    travelableDistanceSteps = 0;
    stepsPerMm = 0;
    minAmplitudePos = 0;
    maxAmplituePos = 0;
    maxAnglePos = 0;
    maxEncoderCount = 0;
  }

  if (!calibrated && !calibrating && home())
  {
    calibrating = true;
  }

  if (!calibrating)
  {
    return false;
  }

  bool maxAmplitudePressed = digitalRead(maxAmplitudePin) == 1 ? false : true;
  bool maxAnglePressed = digitalRead(maxAnglePin) == 1 ? false : true;

  if (!maxAmplitudePressed)
    amplitudeStepper->singleStepAtSpeed(true);

  if (!maxAnglePressed)
    angleStepper->singleStepAtSpeed(true);

  // also check if stepsPerMm is 0, otherwise it has been calibrated already
  // do multi check here too, first check is for fastfail
  if (maxAmplitudePressed && digitalReadCheck(maxAmplitudePin, 0, 4) && stepsPerMm == 0)
  {
    travelableDistanceSteps = amplitudeStepper->getPosition();
    stepsPerMm = float(travelableDistanceSteps) / float(travelableDistanceMm);
    minAmplitudePos = long(offsetMm) * long(stepsPerMm);
    maxAmplituePos = travelableDistanceSteps + minAmplitudePos;

    amplitudeStepper->setPosition(maxAmplituePos);
    amplitudeStepper->setTargetPosition(maxAmplituePos);
  }

  if (maxAnglePressed && digitalReadCheck(maxAnglePin, 0, 4))
  {
    maxAnglePos = angleStepper->getPosition();
    angleStepper->setPosition(maxAnglePos);
    angleStepper->setTargetPosition(maxAnglePos);
    // also set the encoder max
    maxEncoderCount = angleEncoder.getCount();
  }

  if ((maxAmplitudePressed && maxAnglePressed) &&
      (digitalReadCheck(maxAnglePin, 0, 4) && digitalReadCheck(maxAmplitudePin, 0, 4)))
  {
    maxAmplituePos = amplitudeStepper->getPosition();
    maxAnglePos = angleStepper->getPosition();
    maxEncoderCount = angleEncoder.getCount();
    calibrating = false;
    calibrated = true;
    return true;
  }

  return false;
}

long encoderPosToAnglePos()
{
  return map(angleEncoder.getCount(), 0, maxEncoderCount, 0, maxAnglePos);
}

long anglePosToEncoderPos(long stepperPos)
{
  return map(stepperPos, 0, maxAnglePos, 0, maxEncoderCount);
}

struct position
{
  long amplitudePosition;
  long anglePosition;
  long penPosition;
  long amplitudeVelocity;
  long angleVelocity;
};

int ledVal = HIGH;
const int futurePositionsLength = 1000;
int previousPosition = 0;
int nextPositionToPlace = 1;
int nextPositionToGo = 0;
position futurePositions[futurePositionsLength];

int stepsSinceCorrection = 0;
int previousMove = 0;
const int stepsUntilCorrection = 50;
bool angleTargetReached = false;
bool adjustingAnglePos = false;
bool draw()
{
  // step toward target
  if ((amplitudeStepper->getPosition() != amplitudeStepper->getTargetPosition() ||
       angleStepper->getPosition() != angleStepper->getTargetPosition()) &&
      !adjustingAnglePos)
  {
    amplitudeStepper->stepTowardTarget();
    angleStepper->stepTowardTarget();
  }
  else if (!angleTargetReached)
  {
    // angle position correction routine
    long encoderAnglePos = encoderPosToAnglePos();
    if (!adjustingAnglePos)
    {
      float stepsPerEncoderUnit = maxAnglePos / float(maxEncoderCount);
      long positionDiff = encoderAnglePos - angleStepper->getPosition();
      if (positionDiff > stepsPerEncoderUnit)
      {
        // Uncomment to enable angle correction
        // adjustingAnglePos = true;
      }
      else
      {
        angleTargetReached = true;
      }
    }
    else
    {
      long encoderTargetPos = anglePosToEncoderPos(angleStepper->getTargetPosition());
      long encoderPosition = angleEncoder.getCount();
      // serialWriteln("CORRECTING POS " + String(encoderAnglePos) + " " + String(angleStepper->getPosition()));
      // serialWriteln("ENCODER POS " + String(encoderPosition) + " " + String(encoderTargetPos));

      if (encoderPosition != encoderTargetPos)
      {
        bool goingForward = encoderPosition < encoderTargetPos;
        bool stepped = angleStepper->singleStepAtSpeed(goingForward);
        // serialWriteln("STEPPED? " + String(stepped));
        // serialWriteln("NEW STEPPER POS? " + String(angleStepper->getPosition()));
      }
      else
      {
        angleTargetReached = true;
        adjustingAnglePos = false;
        encoderAnglePos = encoderPosToAnglePos();
        // serialWriteln("Setting stepper pos to: " + String(encoderAnglePos));
        angleStepper->setPosition(encoderAnglePos);
        angleStepper->setTargetPosition(encoderAnglePos);
      }
    }
  }
  else
  {
    // check if we have a new position to go to
    int potentialNextPositionToGo = (nextPositionToGo + 1) % futurePositionsLength;
    if (potentialNextPositionToGo == nextPositionToPlace)
    {
      return false;
    }

    // set new target
    nextPositionToGo = potentialNextPositionToGo;
    position nextPosition = futurePositions[nextPositionToGo];
    amplitudeStepper->setTargetPosition(nextPosition.amplitudePosition);
    angleStepper->setTargetPosition(nextPosition.anglePosition);
    amplitudeStepper->setSpeed(nextPosition.amplitudeVelocity);
    angleStepper->setSpeed(nextPosition.angleVelocity);

    angleTargetReached = false;
    adjustingAnglePos = false;

    // count angle steps
    previousMove = abs(angleStepper->getPosition() - angleStepper->getTargetPosition());

    // put pen in position
    // the +1 is just because the .read()
    // returns the last value we wrote -1 ¯\_(ツ)_/¯
    // if (penServo.read() + 1 != nextPosition.penPosition)
    if (abs(nextPosition.penPosition - penServo.read()) > 2)
    {
      penServo.write(nextPosition.penPosition);
      // without this delay the plotter starts
      // moving before the pen has reached the bottom
      delay(150);
    }
  }

  return false;
}

void printStatus()
{
  serialWriteln("STATUS START");
  serialWriteln(currentMode);
  serialWriteln(calibrated);
  serialWriteln(calibrating);

  serialWriteln(amplitudeStepper->getPosition());
  serialWriteln(amplitudeStepper->getTargetPosition());
  serialWriteln(amplitudeStepper->getCurrentSpeed());

  serialWriteln(angleStepper->getPosition());
  serialWriteln(angleStepper->getTargetPosition());
  serialWriteln(angleStepper->getCurrentSpeed());

  serialWriteln(travelableDistanceSteps);
  serialWriteln(stepsPerMm);
  serialWriteln(minAmplitudePos);
  serialWriteln(maxAmplituePos);
  serialWriteln(maxAnglePos);
  serialWriteln(angleEncoder.getCount());
  serialWriteln(maxEncoderCount);
  serialWriteln(nextPositionToPlace);
  serialWriteln(nextPositionToGo);

  serialWriteln(digitalRead(zeroAmplitudePin));
  serialWriteln(digitalRead(maxAmplitudePin));
  serialWriteln(digitalRead(zeroAnglePin));
  serialWriteln(digitalRead(maxAnglePin));
}

enum command
{
  none,
  getStatus,
  setMode,
  calibrate,
  addPosition,
};

int readInt()
{
  return Serial.read() + (Serial.read() << 8) + (Serial.read() << 16) + (Serial.read() << 24);
}

float readFloat()
{
  float f;
  Serial.readBytes((char *)&f, 4);
  return f;
}

int intFromBuffer(const char *buffer, int position)
{
  int value = 0;
  // for (int i = 0; i < 4; i++) {
  //     value += (buffer[position + i] << (i * 8));
  // }
  memcpy(&value, buffer + position, sizeof(int));
  return value;
}

float floatFromBuffer(const char *buffer, int position)
{
  float value = 0;
  memcpy(&value, buffer + position, sizeof(float));
  return value;
}

const int nMessageDelimiters = 3;
bool commandStarted = false;
bool commandComplete = false;

int commandDelimiterCounter = 0;
char commandStartChar = '<';
char commandEndChar = '>';

int commandBufferIdx = 0;
char currentCommand = 0;
char commandBuffer[100];

int received_checksum = 0;
int calculated_checksum = 0;
bool parseCommand()
{
  int readIdx = 0;
  int cmd = intFromBuffer(commandBuffer, readIdx);
  readIdx += sizeof(cmd);

  // serialWriteln("GOT COMMAND TYPE: " + String(cmd));

  switch (cmd)
  {
  case setMode:
    // serialWriteln("PROCESSING SET MODE COMMAND");
    currentMode = intFromBuffer(commandBuffer, readIdx);
    break;
  case getStatus:
    // serialWriteln("PROCESSING GET STATUS COMMAND");
    printStatus();
    break;
  case calibrate:
    // serialWriteln("PROCESSING CALIBRATE COMMAND");
    travelableDistanceSteps = intFromBuffer(commandBuffer, readIdx);
    stepsPerMm = floatFromBuffer(commandBuffer, readIdx + 4);
    minAmplitudePos = intFromBuffer(commandBuffer, readIdx + 8);
    maxAmplituePos = intFromBuffer(commandBuffer, readIdx + 12);
    maxAnglePos = intFromBuffer(commandBuffer, readIdx + 16);
    maxEncoderCount = intFromBuffer(commandBuffer, readIdx + 20);

    amplitudeStepper->setPosition(minAmplitudePos);
    amplitudeStepper->setTargetPosition(minAmplitudePos);
    calibrated = true;
    break;
  case addPosition:
    // serialWriteln("PROCESSING ADD POSITION");
    if (nextPositionToGo == nextPositionToPlace)
    {
      return false;
    }

    position p;
    p.amplitudePosition = intFromBuffer(commandBuffer, readIdx);
    p.anglePosition = intFromBuffer(commandBuffer, readIdx + 4);
    p.penPosition = intFromBuffer(commandBuffer, readIdx + 8);
    p.amplitudeVelocity = intFromBuffer(commandBuffer, readIdx + 12);
    p.angleVelocity = intFromBuffer(commandBuffer, readIdx + 16);

    received_checksum = intFromBuffer(commandBuffer, readIdx + 20);
    calculated_checksum += (p.amplitudePosition % 123);
    calculated_checksum += (p.anglePosition % 123);
    calculated_checksum += (p.penPosition % 123);
    calculated_checksum += (p.amplitudeVelocity % 123);
    calculated_checksum += (p.angleVelocity % 123);

    // Serial.print("GOT POS: ");
    // Serial.print(String(p.amplitudePosition) + " ");
    // Serial.print(String(p.anglePosition) + " ");
    // Serial.print(String(p.penPosition) + " ");
    // Serial.print(String(p.amplitudeVelocity) + " ");
    // serialWriteln(String(p.angleVelocity) + " ");
    if (received_checksum != calculated_checksum)
    {
      // serialWriteln("CHECKSUM MISMATCH " + String(received_checksum) + " != " + String(calculated_checksum));
      calculated_checksum = 0;
      return false;
    }

    futurePositions[nextPositionToPlace] = p;
    nextPositionToPlace = (nextPositionToPlace + 1) % futurePositionsLength;
    calculated_checksum = 0;
    break;
  default:
    serialWriteln("DID NOT RECOGNIZE COMMAND TYPE");
  }

  calculated_checksum = 0;
  return true;
}

void readInput()
{
  if (!Serial.available() && !commandComplete)
  {
    return;
  }

  char c = Serial.read();

  // look for start of message
  if (!commandStarted)
  {
    if (c == commandStartChar)
    {
      commandDelimiterCounter++;
      // serialWriteln("GOT START DELIMITER");
      if (commandDelimiterCounter == nMessageDelimiters)
      {
        commandStarted = true;
        commandDelimiterCounter = 0;
        // serialWriteln("COMMAND STARTED");
      }
    }
  }
  else if (commandStarted && !commandComplete)
  {
    // look for end of message
    if (c == commandEndChar)
    {
      commandDelimiterCounter++;
      if (commandDelimiterCounter == nMessageDelimiters)
      {
        commandComplete = true;
        // serialWriteln("COMMAND READ " + String(commandComplete));
      }
    }
    else
    {
      if (commandDelimiterCounter > 0)
      {
        // this means a previous byte was misinterpreted as an end delimiter
        for (int i = 0; i < commandDelimiterCounter; i++)
        {
          commandBuffer[commandBufferIdx + i] = commandEndChar;
          commandBufferIdx++;
        }
        commandDelimiterCounter = 0;
      }
      // serialWriteln("GOT COMMAND CHAR " + String(c));
      commandBuffer[commandBufferIdx] = c;
      commandBufferIdx++;
    }
  }
  else if (commandComplete)
  {
    // serialWriteln("PROCESSING CMD");
    if (parseCommand())
    {
      serialWriteln("OK");
    }
    else
    {
      serialWriteln("FAIL");
    }
    commandStarted = false;
    commandComplete = false;
    commandBufferIdx = 0;
    commandDelimiterCounter = 0;
  }
}

void setup()
{
  Serial.setTxBufferSize(2048);
  Serial.setRxBufferSize(2048);
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
  digitalWrite(enableStepper, LOW); // enable is LOW for a4988 driver
  amplitudeStepper = new Stepper(amplitudeStepPin, amplitudeDirPin);
  angleStepper = new Stepper(angleStepPin, angleDirPin);

  // configure encoder
  ESP32Encoder::useInternalWeakPullResistors = UP;
  angleEncoder.always_interrupt = true;
  angleEncoder.attachFullQuad(encoderPhaseAPin, encoderPhaseBPin);
  angleEncoder.setCount(0);

  // attach servo
  penServo.attach(penServoPin);
  penServo.write(0);

  serialWriteln("SETUP DONE");
}

void loop()
{
  readInput();
  sendOutput();

  switch (currentMode)
  {
  case idle:
    break;
  case homing:
    amplitudeStepper->setSpeed(3500);
    angleStepper->setSpeed(1200);
    if (home())
      currentMode = idle;
    break;
  case autoCalibration:
    if (!calibrating)
      stepsPerMm = 0;
    amplitudeStepper->setSpeed(3500);
    angleStepper->setSpeed(1200);
    if (autoCalibrate())
      currentMode = homing;
    break;
  case drawing:
    if (draw())
      currentMode = idle;
    break;
  default:
    currentMode = idle;
    break;
  }
}
