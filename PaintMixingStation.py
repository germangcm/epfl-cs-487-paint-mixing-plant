import sys
import argparse
from simulator import Simulator
from tango import AttrWriteType
from tango.server import Device, attribute, command, run


class PaintTank(Device):
    """
    Tango device server implementation representing a single paint tank
    """
    def init_device(self):
        super().init_device()
        print("Initializing class %s for device %s" % (self.__class__.__name__, self.get_name()))
        # extract the tank name from the full device name, e.g. "epfl/station1/cyan" -> "cyan"
        tank_name = self.get_name().split('/')[-1]
        # get a reference to the simulated tank
        self.tank = simulator.get_paint_tank_by_name(tank_name)
        if not self.tank:
            raise Exception(
                "Error: Can't find matching paint tank in the simulator with given name = %s" % self.get_name())

    @attribute(dtype=float)
    def level(self):
        """
        get level attribute
        range: 0 to 1
        """
        return self.tank.get_level()

    @attribute(dtype=float)
    def flow(self):
        """
        get flow attribute
        """
        return self.tank.get_outflow()

    valve = attribute(label="valve", dtype=float,
                      access=AttrWriteType.READ_WRITE,
                      min_value=0.0, max_value=1.0,
                      fget="get_valve", fset="set_valve")

    def set_valve(self, ratio):
        """
        set valve attribute
        :param ratio: 0 to 1
        """
        self.tank.set_valve(min(1, max(0, ratio)))

    def get_valve(self):
        """
        get valve attribute (range: 0 to 1)
        """
        return self.tank.get_valve()

    @attribute(dtype=str)
    def color(self):
        """
        get color attribute (hex string)
        """
        return self.tank.get_color_rgb()  # grey

    @command(dtype_out=float)
    def Fill(self):
        """
        command to fill up the tank with paint
        """
        self.tank.fill()
        return self.tank.get_level()

    @command(dtype_out=float)
    def Flush(self):
        """
        command to flush all paint
        """
        self.tank.flush()
        return self.tank.get_level()


if __name__ == "__main__":
    # Parse command line arguments for stations
    parser = argparse.ArgumentParser(
                    prog='PaintMixingStation.py',
                    description='Start Paint Mixing Station device servers')
    parser.add_argument('stations', nargs='+', help='List of paint mixing stations (e.g. station1 station2)')
    args = parser.parse_args()

    # Start the simulator as a background thread
    simulator = Simulator()
    simulator.start()

    # Dynamically create a device server for each station
    device_servers = []
    for station in args.stations:
        for device_name in ["cyan", "magenta", "yellow", "black", "white", "mixer"]:
            device_name_full = "epfl/%s/%s" % (station, device_name)
            device_servers.append((PaintTank, device_name_full))

    # Start the Tango device servers (blocking call)
    run(device_servers)
