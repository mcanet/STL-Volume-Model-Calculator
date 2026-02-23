#!/usr/bin/env python3

'''
VOLUME CALCULATION STL MODELS
Author: Mar Canet (mar.canet@gmail.com) - August 2012-2025
Description: Calculate volume and mass of STL models (binary and ASCII), NIfTI, and DICOM files.
'''

import struct
import sys
import re
import argparse
import json
import os

try:
    from tqdm import tqdm
except ImportError:
    print("tqdm is not installed. Please install it: pip install tqdm")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.table import Table
    import rich.box
except ImportError:
    print("Rich is not installed. Please install it: pip install rich")
    sys.exit(1)

console = Console()


class materialsFor3DPrinting:
    def __init__(self):
        # Materials are ordered from more to less common.
        # Densities in g/cm³.
        self.materials_dict = {
            1:  {'name': 'PLA',               'mass': 1.25},
            2:  {'name': 'PETG',              'mass': 1.27},
            3:  {'name': 'ABS',               'mass': 1.02},
            4:  {'name': 'Resin',             'mass': 1.20},
            5:  {'name': 'TPU (Rubber-like)',  'mass': 1.20},
            6:  {'name': 'Polyamide_SLS',     'mass': 0.95},
            7:  {'name': 'Polyamide_MJF',     'mass': 1.01},
            8:  {'name': 'Plexiglass',        'mass': 1.18},
            9:  {'name': 'Alumide',           'mass': 1.36},
            10: {'name': 'Carbon Steel',      'mass': 7.80},
            11: {'name': 'Steel',             'mass': 7.86},
            12: {'name': 'Aluminum',          'mass': 2.698},
            13: {'name': 'Titanium',          'mass': 4.41},
            14: {'name': 'Brass',             'mass': 8.60},
            15: {'name': 'Bronze',            'mass': 9.00},
            16: {'name': 'Copper',            'mass': 9.00},
            17: {'name': 'Silver',            'mass': 10.26},
            18: {'name': 'Gold_14K',          'mass': 13.60},
            19: {'name': 'Gold_18K',          'mass': 15.60},
            20: {'name': '3k CFRP',           'mass': 1.79},
            21: {'name': 'Red Oak',           'mass': 0.70},  # FIX #6: was 5.70 (typo); red oak ~0.70 g/cm³
        }

    def get_material_info(self, material_id):
        return self.materials_dict.get(material_id)

    def list_materials(self, output_format='table'):
        if output_format == 'json':
            print(json.dumps(self.materials_dict, indent=4))
        else:
            table = Table(title="Available 3D Printing Materials",
                          show_header=True, header_style="bold magenta")
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
        self.triangles = []
        self.triangle_count = 0
        self.file_size = 0
        self.bounding_box_cm = None
        self._bbox_min = (0.0, 0.0, 0.0)
        self.is_watertight = None  # populated after loadSTL

    # ------------------------------------------------------------------
    # FIX #1: Reliable binary vs ASCII detection
    # ------------------------------------------------------------------
    def is_binary(self, filepath):
        """
        Detect binary vs ASCII STL reliably.

        Checking only for a 'solid' header prefix is not enough — many binary
        STL exporters write a header beginning with 'solid'.  We additionally
        verify the expected file size against the triangle count stored in the
        binary header:
            expected = 80 (header) + 4 (count) + count * 50 (triangles)
        If the sizes match the file is binary regardless of the prefix.
        """
        with open(filepath, 'rb') as f:
            header = f.read(80).decode(errors='replace')
            if not header.lstrip().startswith('solid'):
                return True          # clearly binary
            raw = f.read(4)
            if len(raw) < 4:
                return False         # too small to be a valid binary STL
            triangle_count = struct.unpack('<I', raw)[0]
            expected_size = 80 + 4 + triangle_count * 50
            return os.path.getsize(filepath) == expected_size

    # ------------------------------------------------------------------
    # Triangle readers
    # ------------------------------------------------------------------
    def _parse_vertices(self, line):
        """Extract up to 3 floats from a vertex/normal line using a robust regex."""
        number_re = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")
        return list(map(float, number_re.findall(line)))[:3]

    def read_ascii_triangle(self, lines, index):
        """
        Parse one ASCII STL facet starting at *index* (the 'facet normal' line).

        FIX #4: Uses a robust float regex that handles scientific notation and
        variable whitespace.  Validates that all three vertices were parsed
        before returning, and returns None on any parse failure so the caller
        can skip bad facets rather than crash.
        """
        try:
            # 'facet normal' at index+0, 'outer loop' at index+1,
            # three 'vertex' lines at index+2,3,4, 'endloop' at index+5, 'endfacet' at index+6
            p1 = self._parse_vertices(lines[index + 2])
            p2 = self._parse_vertices(lines[index + 3])
            p3 = self._parse_vertices(lines[index + 4])
            if len(p1) < 3 or len(p2) < 3 or len(p3) < 3:
                return None
            return (p1, p2, p3)
        except (IndexError, ValueError):
            return None

    def unpack(self, sig, length):
        return struct.unpack(sig, self.f.read(length))

    def read_triangle_binary(self):
        self.unpack("<3f", 12)          # normal (discarded)
        p1 = list(self.unpack("<3f", 12))
        p2 = list(self.unpack("<3f", 12))
        p3 = list(self.unpack("<3f", 12))
        self.unpack("<h", 2)            # attribute byte count
        return (p1, p2, p3)

    # ------------------------------------------------------------------
    # File loading
    # ------------------------------------------------------------------
    def loadSTL(self, infilename):
        self.file_size = os.path.getsize(infilename)
        self.is_binary_file = self.is_binary(infilename)
        self.triangles = []
        try:
            if self.is_binary_file:
                with open(infilename, "rb") as self.f:
                    self.f.seek(80)
                    self.triangle_count = struct.unpack("@i", self.f.read(4))[0]
                    for _ in tqdm(range(self.triangle_count), desc="Reading triangles"):
                        self.triangles.append(self.read_triangle_binary())
            else:
                with open(infilename, 'r') as f:
                    lines = f.readlines()
                ascii_triangles = []
                i = 0
                with tqdm(total=len(lines), desc="Reading triangles") as pbar:
                    while i < len(lines):
                        if lines[i].strip().lower().startswith('facet'):
                            tri = self.read_ascii_triangle(lines, i)
                            if tri is not None:
                                ascii_triangles.append(tri)
                            pbar.update(7)
                            i += 7
                        else:
                            pbar.update(1)
                            i += 1
                self.triangles = ascii_triangles
                self.triangle_count = len(self.triangles)

            self._calculate_bounding_box()

            # FIX #3: watertight check — must run after _calculate_bounding_box
            self.is_watertight = self._check_watertight()
            if not self.is_watertight:
                console.print(
                    "[bold yellow]⚠  Warning:[/bold yellow] This mesh does not appear to be "
                    "watertight (not every edge is shared by exactly 2 triangles). "
                    "Volume calculations may be inaccurate for open or malformed meshes."
                )

        except Exception as e:
            print(f"Error loading STL file: {e}")
            sys.exit(1)

    # ------------------------------------------------------------------
    # Bounding box
    # ------------------------------------------------------------------
    def _calculate_bounding_box(self):
        if not self.triangles:
            self.bounding_box_cm = {'width': 0, 'depth': 0, 'height': 0}
            self._bbox_min = (0.0, 0.0, 0.0)
            return

        fv = self.triangles[0][0]
        min_x = max_x = fv[0]
        min_y = max_y = fv[1]
        min_z = max_z = fv[2]

        for tri in self.triangles:
            for v in tri:
                if v[0] < min_x: min_x = v[0]
                if v[0] > max_x: max_x = v[0]
                if v[1] < min_y: min_y = v[1]
                if v[1] > max_y: max_y = v[1]
                if v[2] < min_z: min_z = v[2]
                if v[2] > max_z: max_z = v[2]

        self.bounding_box_cm = {
            'width':  (max_x - min_x) / 10.0,
            'depth':  (max_y - min_y) / 10.0,
            'height': (max_z - min_z) / 10.0,
        }
        self._bbox_min = (min_x, min_y, min_z)

    # ------------------------------------------------------------------
    # FIX #3: Watertight / closed-mesh validation
    # ------------------------------------------------------------------
    def _check_watertight(self):
        """
        Verify the mesh is a closed manifold by checking that every undirected
        edge is shared by exactly 2 triangles.  An open mesh (surface scan,
        incomplete export, etc.) would have boundary edges that appear only once,
        and would produce a nonsense volume result from the divergence theorem.
        Vertex coordinates are rounded to 6 decimal places before comparison to
        absorb floating-point noise from the file format.
        """
        from collections import defaultdict
        edge_count = defaultdict(int)
        for p1, p2, p3 in self.triangles:
            v1 = tuple(round(c, 6) for c in p1)
            v2 = tuple(round(c, 6) for c in p2)
            v3 = tuple(round(c, 6) for c in p3)
            for a, b in ((v1, v2), (v2, v3), (v3, v1)):
                key = (min(a, b), max(a, b))
                edge_count[key] += 1
        return all(count == 2 for count in edge_count.values())

    # ------------------------------------------------------------------
    # FIX #1 (volume) + FIX #5 (memory): translate to origin — as a generator
    # ------------------------------------------------------------------
    def _translated_triangles(self):
        """
        Yield triangles translated so the mesh bounding-box minimum sits at the
        origin (0, 0, 0).

        WHY: The divergence-theorem signed-volume formula accumulates tetrahedron
        volumes relative to the world origin.  When the mesh is far from the
        origin (e.g. placed at large positive coordinates in the slicer), the
        individual terms become very large and largely cancel each other,
        causing catastrophic floating-point precision loss that can produce a
        negative — or otherwise wrong — result.  Translating to the origin first
        keeps all coordinates small and positive, giving a numerically stable
        answer regardless of where the model was placed in world space.

        This is implemented as a generator (FIX #5) so it never materialises a
        second full copy of all triangles in RAM — critical for large meshes.
        """
        ox, oy, oz = self._bbox_min
        for p1, p2, p3 in self.triangles:
            yield (
                (p1[0] - ox, p1[1] - oy, p1[2] - oz),
                (p2[0] - ox, p2[1] - oy, p2[2] - oz),
                (p3[0] - ox, p3[1] - oy, p3[2] - oz),
            )

    # ------------------------------------------------------------------
    # Core maths
    # ------------------------------------------------------------------
    @staticmethod
    def _signed_volume_of_triangle(p1, p2, p3):
        v321 = p3[0] * p2[1] * p1[2]
        v231 = p2[0] * p3[1] * p1[2]
        v312 = p3[0] * p1[1] * p2[2]
        v132 = p1[0] * p3[1] * p2[2]
        v213 = p2[0] * p1[1] * p3[2]
        v123 = p1[0] * p2[1] * p3[2]
        return (1.0 / 6.0) * (-v321 + v231 + v312 - v132 - v213 + v123)

    # ------------------------------------------------------------------
    # Public calculations
    # ------------------------------------------------------------------
    def calculate_volume(self):
        """
        Return volume in cm³.

        FIX #2: A negative raw sum means the mesh winding is reversed
        (inside-out normals).  We return abs() but emit a clear warning so the
        user knows their mesh has a problem rather than silently getting a
        'magically corrected' number.
        """
        total = 0.0
        for p1, p2, p3 in tqdm(self._translated_triangles(),
                                desc="Calculating volume",
                                total=self.triangle_count):
            total += self._signed_volume_of_triangle(p1, p2, p3)

        if total < 0:
            console.print(
                "[bold yellow]⚠  Warning:[/bold yellow] Raw signed volume is negative, "
                "indicating the mesh has reversed (inside-out) face normals. "
                "Returning the absolute value — please check your model's face orientation."
            )
        return abs(total) / 1000.0   # mm³ → cm³

    def calculate_mass(self, volume_cm3, density_g_cm3):
        return volume_cm3 * density_g_cm3

    def calculate_surface_area(self):
        """
        Surface area in cm².

        Uses edge vectors (differences between vertices) which are already
        translation-invariant, so no origin shift is needed here.
        Iterates self.triangles directly with no extra copy (FIX #5).
        """
        area = 0.0
        for p1, p2, p3 in tqdm(self.triangles, desc="Calculating area  "):
            ax = p2[0] - p1[0];  ay = p2[1] - p1[1];  az = p2[2] - p1[2]
            bx = p3[0] - p1[0];  by = p3[1] - p1[1];  bz = p3[2] - p1[2]
            cx = ay * bz - az * by
            cy = az * bx - ax * bz
            cz = ax * by - ay * bx
            area += 0.5 * (cx * cx + cy * cy + cz * cz) ** 0.5
        return area / 100.0   # mm² → cm²

    @staticmethod
    def cm3_to_inch3(v):
        return v * 0.0610237441


# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(
        description='Calculate properties of 3D models. By default, calculates all properties for all materials.',
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument('filename', nargs='?', default=None,
                        help='Path to the input STL file.')
    parser.add_argument('--calculation', choices=['volume', 'area'], default=None,
                        help='Run only one calculation instead of full analysis.')
    parser.add_argument('--unit', choices=['cm', 'inch'], default='cm',
                        help='Unit for volume display (default: cm).')
    parser.add_argument('--material', type=int, choices=range(1, 22), default=1,
                        help='Material ID for mass calculation (default: 1 = PLA).')
    parser.add_argument('--infill', type=float, default=20.0,
                        help='Infill %% for mass calculation (default: 20.0).')
    parser.add_argument('--filetype', choices=['stl', 'nii', 'dcm'], default='stl',
                        help='Input file type (default: stl).')
    parser.add_argument('--output-format', choices=['table', 'json'], default='table',
                        help='Output format (default: table).')
    parser.add_argument('--list-materials', action='store_true',
                        help='List all available materials and exit.')

    args = parser.parse_args()
    materials = materialsFor3DPrinting()

    if not 0.0 <= args.infill <= 100.0:
        parser.error("Infill percentage must be between 0 and 100.")

    if args.list_materials:
        materials.list_materials(args.output_format)
        sys.exit(0)

    if not args.filename:
        parser.error("A filename is required unless --list-materials is used.")

    is_full_analysis = args.calculation is None

    if args.filetype == 'stl':
        stl = STLUtils()
        stl.loadSTL(args.filename)
        bbox = stl.bounding_box_cm
        results = {}

        if is_full_analysis:
            volume_cm3 = stl.calculate_volume()
            area_cm2   = stl.calculate_surface_area()
            adjusted   = volume_cm3 * (args.infill / 100.0)

            results = {
                "file_information": {
                    "filename":      os.path.basename(args.filename),
                    "file_size_kb":  f"{stl.file_size / 1024:.2f}",
                    "is_watertight": stl.is_watertight,
                },
                "model_properties": {
                    "triangle_count":  stl.triangle_count,
                    "bounding_box_cm": {
                        "width":  f"{bbox['width']:.2f}",
                        "depth":  f"{bbox['depth']:.2f}",
                        "height": f"{bbox['height']:.2f}",
                    },
                    "surface_area_cm2": f"{area_cm2:.4f}",
                    "volume_cm3":       f"{volume_cm3:.4f}",
                    "volume_inch3":     f"{stl.cm3_to_inch3(volume_cm3):.4f}",
                },
                "mass_estimates": [],
            }

            for mat_id, mat_info in materials.materials_dict.items():
                results["mass_estimates"].append({
                    "id":            mat_id,
                    "name":          mat_info['name'],
                    "density_g_cm3": mat_info['mass'],
                    "mass_at_infill": {
                        "infill_percent": args.infill,
                        "mass_g": f"{stl.calculate_mass(adjusted, mat_info['mass']):.3f}",
                    },
                    "mass_at_100_infill": {
                        "infill_percent": 100.0,
                        "mass_g": f"{stl.calculate_mass(volume_cm3, mat_info['mass']):.3f}",
                    },
                })

        else:
            results = {
                "file":           args.filename,
                "calculation":    args.calculation,
                "bounding_box_cm": bbox,
                "is_watertight":  stl.is_watertight,
            }

            if args.calculation == 'volume':
                volume_cm3    = stl.calculate_volume()
                adjusted      = volume_cm3 * (args.infill / 100.0)
                material_info = materials.get_material_info(args.material)
                results.update({
                    "volume_cm3":    f"{volume_cm3:.4f}",
                    "volume_inch3":  f"{stl.cm3_to_inch3(volume_cm3):.4f}",
                    "material_name": material_info['name'],
                    "mass_at_infill": {
                        "infill_percent": args.infill,
                        "mass_g": f"{stl.calculate_mass(adjusted, material_info['mass']):.3f}",
                    },
                    "mass_at_100_infill": {
                        "infill_percent": 100.0,
                        "mass_g": f"{stl.calculate_mass(volume_cm3, material_info['mass']):.3f}",
                    },
                })

            elif args.calculation == 'area':
                area_cm2 = stl.calculate_surface_area()
                results["surface_area_cm2"] = f"{area_cm2:.4f}"

        # --- Output ---
        if args.output_format == 'json':
            print(json.dumps(results, indent=4))

        else:
            watertight_str = lambda w: "✔ Yes" if w else "✘ No  (open mesh — volume may be inaccurate)"

            if is_full_analysis:
                props = results['model_properties']
                info  = results['file_information']

                info_table = Table(
                    title=f"Model Analysis: {info['filename']}",
                    show_header=False, box=rich.box.ROUNDED
                )
                info_table.add_column("Property", style="dim")
                info_table.add_column("Value")
                info_table.add_row("File Size",         f"{info['file_size_kb']} KB")
                info_table.add_row("Watertight",        watertight_str(info['is_watertight']))
                info_table.add_row("Triangles",         f"{props['triangle_count']:,}")
                info_table.add_row("Bounding Box (cm)",
                    f"W: {props['bounding_box_cm']['width']}, "
                    f"D: {props['bounding_box_cm']['depth']}, "
                    f"H: {props['bounding_box_cm']['height']}")
                info_table.add_row("Surface Area",      f"{props['surface_area_cm2']} cm²")
                vol_display = (f"{props['volume_inch3']} inch³"
                               if args.unit == 'inch' else f"{props['volume_cm3']} cm³")
                info_table.add_row("Volume (solid)",    vol_display)
                console.print(info_table)

                mass_table = Table(
                    title=f"Mass Estimates — all materials, {args.infill:.1f}% and 100% infill",
                    show_header=True, header_style="bold magenta"
                )
                mass_table.add_column("ID",   style="dim", width=4)
                mass_table.add_column("Material Name")
                mass_table.add_column("Density",                  justify="right")
                mass_table.add_column(f"Mass @ {args.infill:.1f}% (g)", justify="right")
                mass_table.add_column("Mass @ 100% (g)",          justify="right")
                for item in results['mass_estimates']:
                    mass_table.add_row(
                        str(item['id']),
                        item['name'],
                        f"{item['density_g_cm3']:.3f}",
                        item['mass_at_infill']['mass_g'],
                        item['mass_at_100_infill']['mass_g'],
                    )
                console.print(mass_table)

            else:
                if args.calculation == 'volume':
                    table = Table(title="Volume & Mass Calculation",
                                  show_header=False, box=rich.box.ROUNDED)
                    table.add_column("Property", style="dim")
                    table.add_column("Value")
                    table.add_row("Watertight",        watertight_str(results['is_watertight']))
                    table.add_row("Bounding Box (cm)",
                                  f"W: {bbox['width']:.2f}, D: {bbox['depth']:.2f}, H: {bbox['height']:.2f}")
                    vol_display = (f"{results['volume_inch3']} inch³"
                                   if args.unit == 'inch' else f"{results['volume_cm3']} cm³")
                    table.add_row("Volume (solid)",    vol_display)
                    table.add_row("Material",          f"{results['material_name']} (ID: {args.material})")
                    table.add_row(f"Mass ({args.infill:.1f}% Infill)",
                                  f"{results['mass_at_infill']['mass_g']} g")
                    table.add_row("Mass (100% Infill)",
                                  f"{results['mass_at_100_infill']['mass_g']} g")
                    console.print(table)

                elif args.calculation == 'area':
                    table = Table(title="Surface Area Calculation",
                                  show_header=False, box=rich.box.ROUNDED)
                    table.add_column("Property", style="dim")
                    table.add_column("Value")
                    table.add_row("Watertight",        watertight_str(results['is_watertight']))
                    table.add_row("Bounding Box (cm)",
                                  f"W: {bbox['width']:.2f}, D: {bbox['depth']:.2f}, H: {bbox['height']:.2f}")
                    table.add_row("Surface Area",      f"{results['surface_area_cm2']} cm²")
                    console.print(table)

    elif args.filetype in ['nii', 'dcm']:
        console.print("[yellow]Warning: NIfTI and DICOM support is limited.[/yellow]")


if __name__ == '__main__':
    main()
