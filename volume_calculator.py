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

class 3DPrintingMaterials:
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

    def list_materials(self):
        for key, value in self.materials_dict.items():
            print(f"{key} = {value['name']}")

    def get_material_choice(self):
        while True:
            self.list_materials()
            try:
                choice = int(input('Enter the number corresponding to the desired print material: '))
                if 1 <= choice <= len(self.materials_dict):
                    return choice
                else:
                    print(f"Invalid choice. Please choose a number between 1 and {len(self.materials_dict)}.")
            except ValueError:
                print("Invalid input. Please enter a number.")

class STLUtils:
    def __init__(self):
        self.f = None

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
            is_binary = self.is_binary(infilename)
            if is_binary:
                self.f = open(infilename, "rb")
                self.read_header()
                l = self.read_length()
                print("total triangles:", l)
                for _ in range(l):
                    totalVolume += self.read_triangle()
            else:
                with open(infilename, 'r') as f:
                    lines = f.readlines()
                i = 0
                while i < len(lines):
                    if lines[i].strip().startswith('facet'):
                        totalVolume += self.read_ascii_triangle(lines, i)
                        i += 7  # Skip to next facet
                    else:
                        i += 1
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

    # surf_area method outputs the surface area in square centimeters (cm^2)
    def surf_area(self, vertices):
        area = 0
        size = len(vertices)
        for i in range(size):
            if (i + 1) % 9 == 0:
                ax = vertices[i - 5] - vertices[i - 2]
                ay = vertices[i - 4] - vertices[i - 1]
                az = vertices[i - 3] - vertices[i]
                bx = vertices[i - 8] - vertices[i - 2]
                by = vertices[i - 7] - vertices[i - 1]
                bz = vertices[i - 6] - vertices[i]
                cx = ay * bz - az * by
                cy = az * bx - ax * bz
                cz = ax * by - ay * bx
                area += 0.5 * (cx * cx + cy * cy + cz * cz)**0.5
        areaCm2 = area / 100        
        print("Total area:", areaCm2, "cm^2")
        return areaCm2

def main():
    parser = argparse.ArgumentParser(description='Calculate volume or surface area of STL models.')
    parser.add_argument('filename', help='Path to the STL file')
    parser.add_argument('calculation', choices=['volume', 'area'], help='Choose between calculating volume or surface area')
    parser.add_argument('--unit', choices=['cm', 'inch'], default='cm', help='Unit for the volume calculation (default: cm)')

    args = parser.parse_args()

    if not args.filename:
        print("Please provide a filename, e.g.: python measure_volume.py torus.stl")
        return

    mat = 3DPrintingMaterials()
    global material
    material = mat.get_material_choice()

    mySTLUtils = STLUtils()

    if args.calculation == 'volume':
        mySTLUtils.calculateVolume(args.filename, args.unit)
    elif args.calculation == 'area':
        # Assuming you have a method to calculate surface area similar to calculateVolume
        # and it's named calculateArea, you can call it like below:
        mySTLUtils.calculateArea(args.filename, args.unit)

if __name__ == '__main__':
    main()
