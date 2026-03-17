"""
Regional configuration for the Tagout prediction model.
Focused on northern Idaho / Coeur d'Alene area (~100-mile radius).
"""

# CDA coordinates (center of focus area)
CDA_LAT = 47.6777
CDA_LON = -116.7805
FOCUS_RADIUS_MILES = 100

# IDFG Region 1 (Panhandle) — hunt units within ~100 miles of CDA
PANHANDLE_UNITS = ["1", "2", "3", "4", "4A", "5", "6", "7", "9"]

# Primary counties in range
FOCUS_COUNTIES = ["Boundary", "Bonner", "Kootenai", "Shoshone", "Benewah"]

# Target species for Phase 1 (highest data availability + relevance)
PRIMARY_SPECIES = [
    "Deer",       # Whitetail dominant in Panhandle
    "Elk",
    "Black Bear",
]

SECONDARY_SPECIES = [
    "Moose",
    "Mountain Lion",
    "Gray Wolf",
    "Pronghorn",  # Less common in Panhandle but available
]

ALL_SPECIES = PRIMARY_SPECIES + SECONDARY_SPECIES

# Data year range
YEAR_START = 2000
YEAR_END = 2024

# Notable: Whitetail is dominant deer species in Panhandle (vs mule deer in southern ID)
# Units 1, 2, 3, 5, 6 are top 10 statewide for whitetail harvest
# CWD management changes in 2025-26 season may affect future data

# NOAA weather stations near CDA for historical weather data
# (to be integrated in Phase 4)
NOAA_STATIONS = {
    "Coeur d'Alene Airport": "KCOE",
    "Sandpoint": "KSZT",
    "St. Maries": "KSZT",  # approximate
}
