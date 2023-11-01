#ifndef SERIAL_UTIL_CPP
#define SERIAL_UTIL_CPP

#include <Arduino.h>

int serialOutputWriteIndex = 0;
int serialOutputSendIndex = 0;
char serialOutputBuffer[2000];

void sendOutput()
{
    if (serialOutputSendIndex == serialOutputWriteIndex)
    {
        return;
    }

    Serial.write(serialOutputBuffer[serialOutputSendIndex]);
    serialOutputSendIndex = (serialOutputSendIndex + 1) % sizeof(serialOutputBuffer);
}

/* chars */
void serialWrite(const char *output)
{
    while (*output)
    {
        serialOutputBuffer[serialOutputWriteIndex] = *output++;
        serialOutputWriteIndex = (serialOutputWriteIndex + 1) % sizeof(serialOutputBuffer);

        if (serialOutputWriteIndex == serialOutputSendIndex)
        {
            sendOutput();
        }
    }
}

void serialWriteln(const char *output)
{
    serialWrite(output);
    serialWrite("\n");
}

/* ints */
void serialWrite(int value)
{
    char buffer[12];
    snprintf(buffer, sizeof(buffer), "%d", value);
    serialWrite(buffer);
}

void serialWriteln(int value)
{
    char buffer[12]; // Enough to hold an int32_t
    snprintf(buffer, sizeof(buffer), "%d", value);
    serialWrite(buffer);
    serialWrite("\n");
}

/* floats */

void serialWrite(float value, int decimalPlaces = 2)
{
    char buffer[32];
    snprintf(buffer, sizeof(buffer), "%.*f", decimalPlaces, value);
    serialWrite(buffer);
}

void serialWriteln(float value, int decimalPlaces = 2)
{
    char buffer[32]; // Adjust size if needed
    snprintf(buffer, sizeof(buffer), "%.*f", decimalPlaces, value);
    serialWrite(buffer);
    serialWrite("\n");
}

/* longs */

void serialWrite(long value)
{
    char buffer[20];
    snprintf(buffer, sizeof(buffer), "%ld", value);
    serialWrite(buffer);
}

void serialWriteln(long value)
{
    char buffer[20]; // Enough to hold a long
    snprintf(buffer, sizeof(buffer), "%ld", value);
    serialWrite(buffer);
    serialWrite("\n");
}

/* int64_t */

void serialWrite(int64_t value)
{
    char buffer[32];
    snprintf(buffer, sizeof(buffer), "%" PRId64, value);
    serialWrite(buffer);
}

void serialWriteln(int64_t value)
{
    char buffer[32];
    snprintf(buffer, sizeof(buffer), "%" PRId64, value);
    serialWrite(buffer);
    serialWrite("\n");
}

#endif
