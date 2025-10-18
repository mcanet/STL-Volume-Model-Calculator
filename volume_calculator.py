#!/usr/bin/env python3

'''
VOLUME CALCULATION STL MODELS
Author: Mar Canet (mar.canet@gmail.com) - August 2012-2025
Description: Calculate volume and mass of STL models (binary and ASCII), NIfTI, and DICOM files.
'''

from typing import Tuple, List
import struct
import sys
import re
import argparse
import json
import os
try:
    from tqdm import tqdm
except ImportError:
    print("tqdm is not installed. Please install it for table output: pip install tqdm")
    sys.exit(1)
    
try:
    from rich.console import Console
    from rich.table import Table
    import rich.box
except ImportError:
    print("Rich is not installed. Please install it for table output: pip install rich")
    sys.exit(1)

Point3D = Tuple[float, float, float]


class materialsFor3DPrinting:
    def __init__(self):
        # Materials are ordered from more to less common
        self.materials_dict = {
            1: {'name': 'PLA', 'mass': 1.25},
            2: {'name': 'PETG', 'mass': 1.27},
            3: {'name': 'ABS', 'mass': 1.02},
            4: {'name': 'Resin', 'mass': 1.2},
            5: {'name': 'TPU (Rubber-like)', 'mass': 1.2},
            6: {'name': 'Polyamide_SLS', 'mass': 0.95},
            7: {'name': 'Polyamide_MJF', 'mass': 1.01},
            8: {'name': 'Plexiglass', 'mass': 1.18},
            9: {'name': 'Alumide', 'mass': 1.36},
            10: {'name': 'Carbon Steel', 'mass': 7.80},
            11: {'name': 'Steel', 'mass': 7.86},
            12: {'name': 'Aluminum', 'mass': 2.698},
            13: {'name': 'Titanium', 'mass': 4.41},
            14: {'name': 'Brass', 'mass': 8.6},
            15: {'name': 'Bronze', 'mass': 9.0},
            16: {'name': 'Copper', 'mass': 9.0},
            17: {'name': 'Silver', 'mass': 10.26},
            18: {'name': 'Gold_14K', 'mass': 13.6},
            19: {'name': 'Gold_18K', 'mass': 15.6},
            20: {'name': '3k CFRP', 'mass': 1.79},
            21: {'name': 'Red Oak', 'mass': 5.70}
        }

    def get_material_info(self, material_id):
        return self.materials_dict.get(material_id)

    def list_materials(self, output_format='table'):
        if output_format == 'json':
            print(json.dumps(self.materials_dict, indent=4))
        else:
            console = Console()
            table = Table(title="Available 3D Printing Materials", show_header=True, header_style="bold magenta")
            table.add_column("ID", style="dim", width=6)
            table.add_column("Name")
            table.add_column("Density (g/cm³)", justify="right")

            for key, value in self.materials_dict.items():
                table.add_row(str(key), value['name'], f"{value['mass']:.3f}")
            console.print(table)

class STLUtils:
    def __init__(self):
        self.f = None
        self.is_binary_file = None
        self.triangles: List[Tuple[Point3D, Point3D, Point3D]] = []
        self.triangle_count = 0
        self.file_size = 0
        self.bounding_box_cm = None

    def is_binary(self, file):
        with open(file, 'rb') as f:
            header = f.read(80).decode(errors='replace')
            return not header.startswith('solid')

    def read_ascii_triangle(self, lines, index):
        p1 = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", lines[index + 1])))
        p2 = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", lines[index + 2])))
        p3 = list(map(float, re.findall(r"[-+]?\d*\.\d+|\d+", lines[index + 3])))
        return (p1, p2, p3)

    def signedVolumeOfTriangle(self, p1: Point3D, p2: Point3D, p3: Point3D) -> float:
        """
        Compute the signed volume of the tetrahedron formed by three 3D points (p1, p2, p3)
        and the origin (0, 0, 0).

        This method effectively computes one-sixth of the determinant of the matrix whose
        columns (or rows) are the position vectors of p1, p2, and p3. The determinant gives
        the *signed volume* of the parallelepiped defined by those three vectors. Dividing
        by 6 yields the volume of the tetrahedron.

        Geometrically:
            V_signed = (1/6) * det([p1, p2, p3])
                    = (1/6) * (p1 . (p2 * p3))

        - The *sign* of the result indicates the orientation (right- or left-handed) of
        the triangle relative to the origin.
        - The *magnitude* of the result gives the volume of the tetrahedron.

        Parameters
        ----------
        p1, p2, p3 : tuple[float, float, float]
            3D coordinates of the triangle's vertices.

        Returns
        -------
        float
            The signed volume of the tetrahedron (O, p1, p2, p3).

        Examples
        --------
        >>> STLUtils().signedVolumeOfTriangle((1, 0, 0), (0, 1, 0), (0, 0, 1))
        0.16666666666666666
        >>> STLUtils().signedVolumeOfTriangle((1, 0, 0), (0, 0, 1), (0, 1, 0))
        -0.16666666666666666
        """
        v321 = p3[0] * p2[1] * p1[2]
        v231 = p2[0] * p3[1] * p1[2]
        v312 = p3[0] * p1[1] * p2[2]
        v132 = p1[0] * p3[1] * p2[2]
        v213 = p2[0] * p1[1] * p3[2]
        v123 = p1[0] * p2[1] * p3[2]
        return (1.0 / 6.0) * (-v321 + v231 + v312 - v132 - v213 + v123)

    def unpack(self, sig, count):
        s = self.f.read(count)
        return struct.unpack(sig, s)

    def read_triangle_binary(self) -> Tuple[Point3D, Point3D, Point3D]:
        self.unpack("<3f", 12) # Normal
        p1 = self.unpack("<3f", 12)
        p2 = self.unpack("<3f", 12)
        p3 = self.unpack("<3f", 12)
        self.unpack("<h", 2) # Attribute byte count
        return (p1, p2, p3)

    def loadSTL(self, infilename):
        self.file_size = os.path.getsize(infilename)
        self.is_binary_file = self.is_binary(infilename)
        self.triangles = []
        try:
            if self.is_binary_file:
                with open(infilename, "rb") as self.f:
                    self.f.seek(80) # Skip header
                    self.triangle_count = struct.unpack("@i", self.f.read(4))[0]
                    for _ in tqdm(range(self.triangle_count), desc="Reading triangles"):
                        self.triangles.append(self.read_triangle_binary())
            else:
                with open(infilename, 'r') as f:
                    lines = f.readlines()
                i = 0
                ascii_triangles = []
                with tqdm(total=len(lines), desc="Reading triangles") as pbar:
                    while i < len(lines):
                        if lines[i].strip().startswith('facet'):
                            ascii_triangles.append(self.read_ascii_triangle(lines, i))
                            pbar.update(7)
                            i += 7
                        else:
                            pbar.update(1)
                            i += 1
                self.triangles = ascii_triangles
                self.triangle_count = len(self.triangles)
            
            self._calculate_bounding_box()

        except Exception as e:
            print(f"Error loading STL file: {e}")
            sys.exit(1)

    def _calculate_bounding_box(self):
        if not self.triangles:
            self.bounding_box_cm = {'width': 0, 'depth': 0, 'height': 0}
            return

        first_vertex = self.triangles[0][0]
        min_x, max_x = first_vertex[0], first_vertex[0]
        min_y, max_y = first_vertex[1], first_vertex[1]
        min_z, max_z = first_vertex[2], first_vertex[2]

        for triangle in self.triangles:
            for vertex in triangle:
                min_x, max_x = min(min_x, vertex[0]), max(max_x, vertex[0])
                min_y, max_y = min(min_y, vertex[1]), max(max_y, vertex[1])
                min_z, max_z = min(min_z, vertex[2]), max(max_z, vertex[2])

        width_cm = (max_x - min_x) / 10.0
        depth_cm = (max_y - min_y) / 10.0
        height_cm = (max_z - min_z) / 10.0

        self.bounding_box_cm = {'width': width_cm, 'depth': depth_cm, 'height': height_cm}

    def calculate_volume(self) -> float:
        """Computes the total volume of the loaded STL file, in cubed centimeters.

        Returns
        -------
        float
            Volume in cubed centimeters.
        """
        totalVolume = 0
        for p1, p2, p3 in tqdm(self.triangles, desc="Calculating volume"):
            totalVolume += self.signedVolumeOfTriangle(p1, p2, p3)
        return totalVolume / 1000 # Return in cm³

    def calculate_mass(self, volume_cm3, density_g_cm3):
        return volume_cm3 * density_g_cm3

    def calculate_surface_area(self) -> float:
        """Computes the surface area of the loaded STL file, in squared centimeters.

        Returns
        -------
        float
            Surface in squared centimeters.
        """
        area = 0
        for p1, p2, p3 in tqdm(self.triangles, desc="Calculating area  "):
            ax, ay, az = p2[0] - p1[0], p2[1] - p1[1], p2[2] - p1[2]
            bx, by, bz = p3[0] - p1[0], p3[1] - p1[1], p3[2] - p1[2]
            cx, cy, cz = ay * bz - az * by, az * bx - ax * bz, ax * by - ay * bx
            area += 0.5 * (cx * cx + cy * cy + cz * cz)**0.5
        return area / 100 # Return in cm²

    @staticmethod
    def cm3_to_inch3(v):
        return v * 0.0610237441

def main():
    parser = argparse.ArgumentParser(
        description='Calculate properties of 3D models. By default, calculates all properties for all materials.',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('filename', nargs='?', default=None, help='Path to the input file (STL, NIfTI, DICOM).')
    parser.add_argument(
        '--calculation', choices=['volume', 'area'], default=None,
        help='Optimize by running a single calculation.'
    )
    parser.add_argument('--unit', choices=['cm', 'inch'], default='cm', help='Unit for volume display (default: cm).')
    parser.add_argument(
        '--material', type=int, choices=range(1, 22), default=1,
        help='Material ID for specific mass calculation (default: 1, PLA).'
    )
    parser.add_argument(
        '--infill', type=float, default=20.0,
        help='Infill percentage for mass calculation (default: 20.0).'
    )
    parser.add_argument('--filetype', choices=['stl', 'nii', 'dcm'], default='stl', help='Type of the input file (default: stl).')
    parser.add_argument('--output-format', choices=['table', 'json'], default='table', help='Output format (default: table).')
    parser.add_argument('--list-materials', action='store_true', help='List all available materials and exit.')

    args = parser.parse_args()
    materials = materialsFor3DPrinting()

    if not 0.0 <= args.infill <= 100.0:
        parser.error("Infill percentage must be between 0 and 100.")

    if args.list_materials:
        materials.list_materials(args.output_format)
        sys.exit(0)

    if not args.filename:
        parser.error("A filename is required unless --list-materials is used.")

    is_full_analysis_mode = args.calculation is None

    if args.filetype == 'stl':
        mySTLUtils = STLUtils()
        mySTLUtils.loadSTL(args.filename)
        bbox = mySTLUtils.bounding_box_cm
        results = {}

        if is_full_analysis_mode:
            # --- FULL ANALYSIS MODE (DEFAULT) ---
            volume_cm3 = mySTLUtils.calculate_volume()
            area_cm2 = mySTLUtils.calculate_surface_area()
            
            adjusted_volume_cm3 = volume_cm3 * (args.infill / 100.0)

            results = {
                "file_information": {
                    "filename": os.path.basename(args.filename),
                    "file_size_kb": f"{mySTLUtils.file_size / 1024:.2f}"
                },
                "model_properties": {
                    "triangle_count": mySTLUtils.triangle_count,
                    "bounding_box_cm": {
                        "width": f"{bbox['width']:.2f}",
                        "depth": f"{bbox['depth']:.2f}",
                        "height": f"{bbox['height']:.2f}"
                    },
                    "surface_area_cm2": f"{area_cm2:.4f}",
                    "volume_cm3": f"{volume_cm3:.4f}",
                    "volume_inch3": f"{mySTLUtils.cm3_to_inch3(volume_cm3):.4f}"
                },
                "mass_estimates": []
            }
            
            for mat_id, mat_info in materials.materials_dict.items():
                mass_infill = mySTLUtils.calculate_mass(adjusted_volume_cm3, mat_info['mass'])
                mass_solid = mySTLUtils.calculate_mass(volume_cm3, mat_info['mass'])
                # MODIFIED: Changed to a more structured and explicit JSON format
                results["mass_estimates"].append({
                    "id": mat_id,
                    "name": mat_info['name'],
                    "density_g_cm3": mat_info['mass'],
                    "mass_at_infill": {
                        "infill_percent": args.infill,
                        "mass_g": f"{mass_infill:.3f}"
                    },
                    "mass_at_100_infill": {
                        "infill_percent": 100.0,
                        "mass_g": f"{mass_solid:.3f}"
                    }
                })

        else:
            # --- SPECIFIC CALCULATION MODE ---
            results = {"file": args.filename, "calculation": args.calculation, "bounding_box_cm": bbox}
            if args.calculation == 'volume':
                volume_cm3 = mySTLUtils.calculate_volume()
                adjusted_volume_cm3 = volume_cm3 * (args.infill / 100.0)
                material_info = materials.get_material_info(args.material)

                mass_g_infill = mySTLUtils.calculate_mass(adjusted_volume_cm3, material_info['mass'])
                mass_g_solid = mySTLUtils.calculate_mass(volume_cm3, material_info['mass'])
                
                # MODIFIED: Changed to a more structured and explicit JSON format
                results.update({
                    "volume_cm3": f"{volume_cm3:.4f}",
                    "volume_inch3": f"{mySTLUtils.cm3_to_inch3(volume_cm3):.4f}",
                    "material_name": material_info['name'],
                    "mass_at_infill": {
                        "infill_percent": args.infill,
                        "mass_g": f"{mass_g_infill:.3f}"
                    },
                    "mass_at_100_infill": {
                        "infill_percent": 100.0,
                        "mass_g": f"{mass_g_solid:.3f}"
                    }
                })
            elif args.calculation == 'area':
                area_cm2 = mySTLUtils.calculate_surface_area()
                results["surface_area_cm2"] = f"{area_cm2:.4f}"

        # --- OUTPUT HANDLING ---
        if args.output_format == 'json':
            print(json.dumps(results, indent=4))
        else:
            console = Console()
            if is_full_analysis_mode:
                props = results['model_properties']
                info_table = Table(title=f"Model Analysis: {results['file_information']['filename']}", show_header=False, header_style="bold cyan", box=rich.box.ROUNDED)
                info_table.add_column("Property", style="dim")
                info_table.add_column("Value")
                info_table.add_row("File Size", f"{results['file_information']['file_size_kb']} KB")
                info_table.add_row("Triangles", f"{props['triangle_count']:,}")
                bbox_str = f"W: {props['bounding_box_cm']['width']}, D: {props['bounding_box_cm']['depth']}, H: {props['bounding_box_cm']['height']}"
                info_table.add_row("Bounding Box (cm)", bbox_str)
                info_table.add_row("Surface Area", f"{props['surface_area_cm2']} cm²")
                volume_display = f"{props['volume_inch3']} inch³" if args.unit == 'inch' else f"{props['volume_cm3']} cm³"
                info_table.add_row("Volume (solid)", volume_display)
                console.print(info_table)

                mass_table = Table(title="Mass Estimates for All Materials With selected infill and 100% infill", show_header=True, header_style="bold magenta")
                mass_table.add_column("ID", style="dim", width=4)
                mass_table.add_column("Material Name")
                mass_table.add_column("Density", justify="right")
                mass_table.add_column(f"Mass @ {args.infill:.1f}% (g)", justify="right")
                mass_table.add_column("Mass @ 100% (g)", justify="right")
                
                # MODIFIED: Accessing data from the new structure for the table
                for item in results['mass_estimates']:
                    mass_table.add_row(
                        str(item['id']), 
                        item['name'], 
                        f"{item['density_g_cm3']:.3f}", 
                        item['mass_at_infill']['mass_g'],
                        item['mass_at_100_infill']['mass_g']
                    )
                console.print(mass_table)
            else: # Specific calculation table
                if args.calculation == 'volume':
                    table = Table(title="Volume & Mass Calculation", show_header=False, box=rich.box.ROUNDED)
                    table.add_column("Property", style="dim")
                    table.add_column("Value")
                    table.add_row("Bounding Box (cm)", f"W: {bbox['width']:.2f}, D: {bbox['depth']:.2f}, H: {bbox['height']:.2f}")
                    volume_display = f"{results['volume_inch3']} inch³" if args.unit == 'inch' else f"{results['volume_cm3']} cm³"
                    table.add_row("Volume (solid)", volume_display)
                    table.add_row("Material", f"{results['material_name']} (ID: {args.material})")
                    # MODIFIED: Accessing data from the new structure for the table
                    table.add_row(f"Mass ({args.infill:.1f}% Infill)", f"{results['mass_at_infill']['mass_g']} g")
                    table.add_row("Mass (100% Infill)", f"{results['mass_at_100_infill']['mass_g']} g")
                    console.print(table)
                elif args.calculation == 'area':
                    table = Table(title="Surface Area Calculation", show_header=False, box=rich.box.ROUNDED)
                    table.add_column("Property", style="dim")
                    table.add_column("Value")
                    table.add_row("Bounding Box (cm)", f"W: {bbox['width']:.2f}, D: {bbox['depth']:.2f}, H: {bbox['height']:.2f}")
                    table.add_row("Surface Area", f"{results['surface_area_cm2']} cm²")
                    console.print(table)

    elif args.filetype in ['nii', 'dcm']:
        console = Console()
        console.print("[yellow]Warning: NIfTI and DICOM support is limited to specific calculations only.[/yellow]")

if __name__ == '__main__':
    main()
