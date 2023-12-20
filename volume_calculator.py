#!/usr/bin/env python3

'''
VOLUME CALCULATION STL MODELS
Author: Mar Canet (mar.canet@gmail.com) - September 2012
Description: Calculate volume and mass of STL models (binary and ASCII).
'''

import struct
import sys
import re
import argparse

class materialsFor3DPrinting:
    def __init__(self):
        self.materials_dict = {
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
        
    def get_material_mass(self, material_identifier):
        if material_identifier is None:
            return 1  # Default mass (density) value if no material is specified
        elif isinstance(material_identifier, int) and material_identifier in self.materials_dict:
            return self.materials_dict[material_identifier]['mass']
        elif isinstance(material_identifier, str):
            for key, value in self.materials_dict.items():
                if value['name'].lower() == material_identifier.lower():
                    return value['mass']
            raise ValueError(f"Invalid material name: {material_identifier}")
        else:
            raise ValueError(f"Invalid material identifier: {material_identifier}")

    def list_materials(self):
        for key, value in self.materials_dict.items():
            print(f"{key} = {value['name']}")

class STLUtils:
    def __init__(self):
        self.f = None
        self.is_binary_file = None
        self.triangles = []

    def is_binary(self, file):
        with open(file, 'rb') as f:
            header = f.read(80).decode(errors='replace')
            return not header.startswith('solid')

    def read_ascii_triangle(self, lines, index):
        p1 = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", lines[index + 1])))
        p2 = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", lines[index + 2])))
        p3 = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", lines[index + 3])))
        return self.signedVolumeOfTriangle(p1, p2, p3)

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
        return (p1, p2, p3)

    def read_length(self):
        length = struct.unpack("@i", self.f.read(4))
        return length[0]

    def read_header(self):
        self.f.seek(self.f.tell() + 80)

    def cm3_To_inch3Transform(self, v):
        return v * 0.0610237441

    def loadSTL(self, infilename):
        self.is_binary_file = self.is_binary(infilename)
        self.triangles = []
        try:
            if self.is_binary_file:
                self.f = open(infilename, "rb")
                self.read_header()
                l = self.read_length()
                print("total triangles:", l)
                for _ in range(l):
                    self.triangles.append(self.read_triangle())
            else:
                with open(infilename, 'r') as f:
                    lines = f.readlines()
                i = 0
                while i < len(lines):
                    if lines[i].strip().startswith('facet'):
                        self.triangles.append(self.read_ascii_triangle(lines, i))
                        i += 7  # Skip to next facet
                    else:
                        i += 1
        except Exception as e:
            print(f"Error: {e}")
            self.triangles = []

    def calculateVolume(self, unit, material_mass):
        totalVolume = sum(self.signedVolumeOfTriangle(p1, p2, p3) for p1, p2, p3 in self.triangles) / 1000
        totalMass = totalVolume * material_mass

        if totalMass <= 0:
            print('Total mass could not be calculated')
        else:
            print('Total mass:', totalMass, 'g')

            if unit == "cm":
                print("Total volume:", totalVolume, "cm^3")
            else:
                totalVolume = self.cm3_To_inch3Transform(totalVolume)
                print("Total volume:", totalVolume, "inch^3")

    def surf_area(self):
        area = 0
        for p1, p2, p3 in self.triangles:
            ax, ay, az = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
            bx, by, bz = p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]
            cx, cy, cz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
            area += 0.5 * (cx * cx + cy * cy + cz * cz)**0.5
        areaCm2 = area / 100
        print("Total area:", areaCm2, "cm^2")
        return areaCm2

def main():
    parser = argparse.ArgumentParser(description='Calculate volume or surface area of STL models.')
    parser.add_argument('filename', help='Path to the STL file')
    parser.add_argument('calculation', choices=['volume', 'area'], help='Choose between calculating volume or surface area')
    parser.add_argument('--unit', choices=['cm', 'inch'], default='cm', help='Unit for the volume calculation (default: cm)')
    parser.add_argument('--material', type=int, choices=range(1, 19), help='Material ID for mass calculation')

    args = parser.parse_args()

    mat = materialsFor3DPrinting()
    material_mass = mat.get_material_mass(args.material)

    mySTLUtils = STLUtils()
    mySTLUtils.loadSTL(args.filename)

    if args.calculation == 'volume':
        mySTLUtils.calculateVolume(args.unit, material_mass)
    elif args.calculation == 'area':
        mySTLUtils.surf_area()

if __name__ == '__main__':
    main()
