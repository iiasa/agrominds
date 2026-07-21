from dataclasses import dataclass

@dataclass
class Crop:
    tbsc: float  # Minimum temperature for plant growth (°C)
    dlai: float  # Fraction of growing season when leaf area declines
    rlad: float  # Leaf area index decline paramter
    dmla: float  # Maximum potential leaf area index
    dlap1: float
    dlap2: float
    top: float  # Optimal growing temperature (°C)
    hmx: float  # Max height
    vpth: float
    vpd2: float
    gsi: float  # Maximum Stomatal Conductance [m/s]
    gmhu: float

maize = Crop(
    top = 25.000000, # to
    tbsc = 8.000000, # tb
    vpth = 0.500000, 
    vpd2 = 0.071000, 
    gsi = 0.007000, 
    hmx = 2.000000, 
    dmla = 6.000000, 
    dlap1 = 3.055136, 
    dlap2 = 13.385480, 
    dlai = 0.800000, 
    rlad = 1.000000, 
    gmhu = 100.000000, 
)

rice = Crop(
    top = 25.000000, 
    tbsc = 10.000000, 
    vpth = 0.500000, 
    vpd2 = 0.071000, 
    gsi = 0.008000, 
    hmx = 0.800000, 
    dmla = 6.000000, 
    dlap1 = 5.413224, 
    dlap2 = 18.101650, 
    dlai = 0.800000, 
    rlad = 0.500000, 
    gmhu = 100.000000, 
)

soy = Crop(
    top = 25.000000, 
    tbsc = 10.000000, 
    vpth = 0.500000, 
    vpd2 = 0.071000, 
    gsi = 0.007000, 
    hmx = 0.800000, 
    dmla = 5.000000, 
    dlap1 = 3.055136, 
    dlap2 = 13.385480, 
    dlai = 0.900000, 
    rlad = 0.100000, 
    gmhu = 100.000000, 
)

wheat_summer = Crop(
    top = 20.000000, 
    tbsc = 5.000000, 
    vpth = 0.500000, 
    vpd2 = 0.071000, 
    gsi = 0.007000, 
    hmx = 1.000000, 
    dmla = 6.000000, 
    dlap1 = 5.413224, 
    dlap2 = 18.101650, 
    dlai = 0.600000, 
    rlad = 1.000000, 
    gmhu = 100.000000, 
)

wheat_winter = Crop(
    top = 15.000000, 
    tbsc = 0.000000, 
    vpth = 0.500000, 
    vpd2 = 0.071000, 
    gsi = 0.007000, 
    hmx = 1.000000, 
    dmla = 6.000000, 
    dlap1 = 5.413224, 
    dlap2 = 18.101650, 
    dlai = 0.600000, 
    rlad = 1.000000, 
    gmhu = 100.000000, 
)