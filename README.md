# pypsse_public

This script is part of a larger pypsse project that does many other functions (this is why it might look incomplete).

The functionality of interest can be found in the get_ercot_bus_data function. Here we import the ercot data dictionary, parse the v35 raw file, and build the network diagram. The networkx diagram contains raw data and data dictionary data where mappable. The method returns a dict of the data. Other functions are included at the bottom in the 'if __name__..' portion to demonstrate common uses. 

This script was thrown together quickly for a very specific task, and was not intended for popular use. Use at your own risk :).
