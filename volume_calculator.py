#!/usr/bin/env python3

'''
VOLUME CALCULATION STL binary MODELS
Author: Mar Canet (mar.canet@gmail.com) - September 2012
Description: Calculate volume and mass of STL binary models.
Contributors: Saijin_Naib (Synper311@aol.com)
'''

import struct
import sys

MATERIALS = {
    1: {'name': 'ABS', 'mass': 1.04},
    2: {'name': 'PLA', 'mass': 1.25},
    3: {'name': '3k CFRP', 'mass': 1.79},
    4: {'name': 'Plexiglass', 'mass': 1.18},
    5: {'name': 'Alumide', 'mass': 1.36},
    6: {'name': 'Aluminum', 'mass': 2.68},
    7: {'name': 'Brass', 'mass': 8.6},
    8: {'name': 'Bronze', 'mass': 9.0},
    9: {'name': 'Copper', 'mass': 9.0},
    10: {'name': 'Gold_14K', 'mass': 13.6},
    11: {'name': 'Gold_18K', 'mass': 15.6},
    12: {'name': 'Polyamide_MJF', 'mass': 1.01},
    13: {'name': 'Polyamide_SLS', 'mass': 0.95},
    14: {'name': 'Rubber', 'mass': 1.2},
    15: {'name': 'Silver', 'mass': 10.26},
    16: {'name': 'Steel', 'mass': 7.86},
    17: {'name': 'Titanium', 'mass': 4.41},
    18: {'name': 'Resin', 'mass': 1.2}
}

def get_material_choice():
    while True:
        for key, value in MATERIALS.items():
            print(f"{key} = {value['name']}")
        try:
            choice = int(input('Enter the number corresponding to the desired print material: '))
            if 1 <= choice <= 18:
                return choice
            else:
                print("Invalid choice. Please choose a number between 1 and 18.")
        except ValueError:
            print("Invalid input. Please enter a number.")

class STLUtils:
    def __init__(self):
        self.f = None

    def signedVolumeOfTriangle(self, p1, p2, p3):
        v321 = p3[0] * p2[1] * p1[2]
        v231 = p2[0] * p3[1] * p1[2]
        v312 = p3[0] * p1[1] * p2[2]
        v132 = p1[0] * p3[1] * p2[2]
        v213 = p2[0] * p1[1] * p3[2]
        v123 = p1[0] * p2[1] * p3[2]
        return (1.0 / 6.0) * (-v321 + v231 + v312 - v132 - v213 + v123)

    def unpack(self, sig, l):
        s = self.f.read(l)
        return struct.unpack(sig, s)

    def read_triangle(self):
        n = self.unpack("<3f", 12)
        p1 = self.unpack("<3f", 12)
        p2 = self.unpack("<3f", 12)
        p3 = self.unpack("<3f", 12)
        self.unpack("<h", 2)
        return self.signedVolumeOfTriangle(p1, p2, p3)

    def read_length(self):
        length = struct.unpack("@i", self.f.read(4))
        return length[0]

    def read_header(self):
        self.f.seek(self.f.tell() + 80)

    def cm3_To_inch3Transform(self, v):
        return v * 0.0610237441

    def calculateMassCM3(self, totalVolume):
        if material in MATERIALS:
            material_mass = MATERIALS[material]['mass']
            return totalVolume * material_mass
        return 0

    def calculateVolume(self, infilename, unit):
        print(infilename)
        totalVolume = 0
        try:
            self.f = open(infilename, "rb")
            self.read_header()
            l = self.read_length()
            print("total triangles:", l)
            for _ in range(l):
                totalVolume += self.read_triangle()
            totalVolume = totalVolume / 1000
            totalMass = self.calculateMassCM3(totalVolume)

            if totalMass <= 0:
                print('Total mass could not be calculated')
            else:
                print('Total mass:', totalMass, 'g')

                if unit == "cm":
                    print("Total volume:", totalVolume, "cm^3")
                else:
                    totalVolume = self.cm3_To_inch3Transform(totalVolume)
                    print("Total volume:", totalVolume, "inch^3")
        except Exception as e:
            print(f"Error: {e}")

def main():
    if len(sys.argv) == 1:
        print("Define model to calculate volume, e.g.: python measure_volume.py torus.stl")
        return

    global material
    material = get_material_choice()

    mySTLUtils = STLUtils()
    unit = "inch" if len(sys.argv) > 2 and sys.argv[2] == "inch" else "cm"
    mySTLUtils.calculateVolume(sys.argv[1], unit)

if __name__ == '__main__':
    main()
