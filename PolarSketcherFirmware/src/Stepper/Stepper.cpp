#include "Arduino.h"
#include "Stepper.h"

Stepper::Stepper(int _stepPin, int _dirPin)
{
    stepPin = _stepPin;
    dirPin = _dirPin;
    currentPosition = 0;
    targetPosition = 0;

    pinMode(stepPin, OUTPUT);
    pinMode(dirPin, OUTPUT);
}

Stepper::~Stepper() {}

void Stepper::setPosition(long position)
{
    currentPosition = position;
}

// setSpeed sets the speed in steps per second
int Stepper::setSpeed(int speed)
{
    if (speed > maxSpeed)
    {
        speed = maxSpeed;
    }

    if (speed <= 0) {
        speed = 1;  // avoid division by zero
    }

    currentSpeed = speed;
    timeBetweenStepsMicros = (1.0 / currentSpeed) * 1000000;
    return currentSpeed;
}

int Stepper::getCurrentSpeed()
{
    return currentSpeed;
}

void Stepper::setTargetPosition(long position)
{
    targetPosition = position;
}

// stepTowardTarget is meant to be called once in every loop
// the function will check if it should actually take a step or not
bool Stepper::stepTowardTarget()
{
    if (currentPosition == targetPosition)
    {
        return false;
    }

    // check if stepper should make a step
    unsigned long nowMicros = micros();
    unsigned long elapsedTimeMicros = nowMicros - lastStepTimestampMicros;
    if (elapsedTimeMicros >= timeBetweenStepsMicros)
    {
        singleStepTowardTarget();
        lastStepTimestampMicros = nowMicros;
        return true;
    }

    return false;
}

void Stepper::singleStepTowardTarget()
{
    if (currentPosition < targetPosition && !goingForward){
        goingForward = true;
    } else if(currentPosition > targetPosition && goingForward){
        goingForward = false;
    }

    singleStep(goingForward);
}

bool Stepper::singleStepAtSpeed(bool forward)
{
    // check if stepper should make a step
    unsigned long nowMicros = micros();
    unsigned long elapsedTimeMicros = nowMicros - lastStepTimestampMicros;
    if (elapsedTimeMicros >= timeBetweenStepsMicros)
    {
        singleStep(forward);
        lastStepTimestampMicros = nowMicros;
        return true;
    }

    return false;
}

void Stepper::singleStep(bool forward)
{
    setDir(forward);
    digitalWrite(stepPin, HIGH);
    delayMicroseconds(50);
    digitalWrite(stepPin, LOW);
    delayMicroseconds(50);

    currentPosition += forward ? 1 : -1;
}

void Stepper::setDir(bool forward)
{
    digitalWrite(dirPin, forward ? HIGH : LOW);
    goingForward = forward;
}


/*
void Stepper::write(int a, int b, int c, int d)
{
    digitalWrite(a, a);
    digitalWrite(b, b);
    digitalWrite(c, c);
    digitalWrite(d, d);
}

void Stepper::forward()
{
    write(1, 1, 0, 0);
    delayMicroseconds(2000);
    write(0, 1, 1, 0);
    delayMicroseconds(2000);
    write(0, 0, 1, 1);
    delayMicroseconds(2000);
    write(1, 0, 0, 1);
    delayMicroseconds(2000);
}

void Stepper::backward()
{
    write(1, 0, 0, 1);
    delayMicroseconds(2000);
    write(0, 0, 1, 1);
    delayMicroseconds(2000);
    write(0, 1, 1, 0);
    delayMicroseconds(2000);
    write(1, 1, 0, 0);
    delayMicroseconds(2000);
}
*/