# EPFL Industrial Automation Lecture (CS-487)
This repository contains sample code for the group project of the [Industrial Automation (CS-487)](https://edu.epfl.ch/coursebook/en/industrial-automation-CS-487) lecture at EPFL.

## Introduction
The project considers a paint production plant. A paint mixing station is composed of 5 paint tanks with unique colors (cyan, magenta, yellow, black and white color) and one mixing tank, as shown in the screenshot below. Each paint tank is controlled via an output valve, and the mixing tank can be emptied via a dedicated pump and output valve. Each tank has a level sensor measuring the level of the paint inside in a tank, as well as a flow meter measuring the paint outflow.

## Requirements
* Python 3.7 or higher
* [PyTango](https://pytango.readthedocs.io/)
* [Mixbox](https://github.com/scrtwpns/mixbox)
* [PyQt5](https://pypi.org/project/PyQt5/)

The PyTango and Mixbox libraries can be installed using `pip`:  
`pip3 install -r requirements.txt`

## User Guide

### Paint Mixing Station Simulator
The `simulator.py` file contains a Python-based simulator for a paint mixing station as described above. For each time interval, the simulator calculates the paint level and outgoing flow for each paint tank and the mixing tank based on the setting of the corresponding valve.

The stand-alone version of the simulator can be started as follows:  
`python3 simulator.py`

### Tango Device Server
The `PaintMixingStation.py` contains skeleton code for a [Tango](https://www.tango-controls.org/) device server instance. It implements the `TankDevice` device server class representing each tank as a separate device instance. Furthermore, the device server creates an instance of the simulator.

**Please note that the device server code only provides a dummy implementation of device attributes and commands. The goal of the project work is to link the device server attributes and commands with the simulation of the paint mixing station.**

The device server instance for Tango can be started as follows:  
`python3 PaintMixingStation.py <station_name>`

Note: The device server needs to be registered with Tango before it can be used. This can be achieved using the `Jive` tool provided by Tango or using the `register-server.py` script in this repository.

### Graphical User Interface
The user interface can be used to visualize the current state of the paint mixing station. It connects as a client to Tango and is polling attributes and sending commands to/from the device server. The GUI can be started as follows:  
`python3 gui.py`
