# Polar Sketcher

The polar Sketcher is a somewhat compact robotic arm plotter.

The motivation is to have a somewhat simple and cheap design to create a 2D plotter.
It is also meant to not occupy a lot of space when idle as you don't need an entire XY CNC setup.

## Demo Video

Take a look a the journey of this build (without looking at commits)
https://youtu.be/corrBt9IMOM

## Upload PolarSketcherFirmware

The firmware of this project is designed to run on an esp32.
To upload the code from the command line run the following command from the `PolarSketcherFirmware` directory:
> platformio run --target upload --environment uno

You may want to change the `serial_port` option in the `platformio.ini` file. The current one is meant for the raspberrypi when using the GPIO serial connection.

To download platformio in the first place run:

`
curl -fsSL
     -o get-platformio.py
     https://raw.githubusercontent.com/platformio/platformio-core-installer/master/get-platformio.py
`

`python3 get-platformio.py`

## Optional software

There is a feature still in development to allow for the storing of drawings in order to pick up where you left off.
for this a local mongoDB is needed, for development se this to run mongodb locally:
> docker run -p 27017:27017 -v $PWD/mongodb:/data/db mongo:latest