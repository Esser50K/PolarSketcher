// SerialUtils.h

#ifndef SERIAL_UTILS_H
#define SERIAL_UTILS_H

#include <Arduino.h>

extern int serialOutputWriteIndex;
extern int serialOutputSendIndex;
extern char serialOutputBuffer[500];

// Function declarations for char*
void serialWriteln(const char *output);
void serialWrite(const char *output);

// Function declarations for int
void serialWriteln(int value);
void serialWrite(int value);

// Function declarations for int64_t
void serialWriteln(int64_t value);
void serialWrite(int64_t value);

// Function declarations for long
void serialWriteln(long value);
void serialWrite(long value);

// Function declarations for float
void serialWriteln(float value, int decimalPlaces = 2);
void serialWrite(float value, int decimalPlaces = 2);

// sendOutput function
void sendOutput();

#endif // SERIAL_UTILS_H
