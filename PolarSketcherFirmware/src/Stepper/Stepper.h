#ifndef STEPPER_H
#define STEPPER_H

class Stepper
{
private:
    int stepPin;
    int dirPin;
    bool goingForward = true;
    long currentPosition = 0;
    int targetPosition;
    int currentSpeed;              // current set speed for stepper in steps per second
    int maxSpeed = 50000;          // max speed of this stepper is 500 steps per second
    int stepsPerRevolution = 200;  // total number of steps per revolution
    unsigned long lastStepTimestampMicros;
    unsigned long timeBetweenStepsMicros;


    void setDir(bool dir);
public:
    Stepper(int stepPin=0, int dirPin=0);
    ~Stepper();

    long getPosition() { return currentPosition; }
    long getTargetPosition() { return targetPosition; }

    void setPosition(long position);
    int setSpeed(int speed);
    int getCurrentSpeed();

    bool stepTowardTarget();
    void singleStepTowardTarget();
    void singleStep(bool forward);
    bool singleStepAtSpeed(bool forward);
    void setTargetPosition(long position);
};

#endif
