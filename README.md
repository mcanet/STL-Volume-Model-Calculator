# STL Volume Model Calculator

This script provides functionality to calculate the volume and surface area of 3D models stored in the STL file format, as well as estimate the weight of the model based on the selected material. It is implemented in Python and supports both binary and ASCII STL files.

## Installation

Make sure you have [Python 3](https://www.python.org/) installed. Then clone the repository and install the required Python libraries using:

```bash
pip install -r requirements.txt
```
## Usage

To use the script, navigate to the directory containing `volume_calculator.py` and your STL file in a terminal, then execute one of the following commands based on your needs:

### Volume and Mass Calculation

```bash
python volume_calculator.py <filename.stl> volume --material <material_id_or_name> [--unit cm|inch]
```
### Surface Area Calculation
```bash
python volume_calculator.py <filename.stl> area
```

### Arguments:

<filename.stl>: Replace with the path to your STL file.
<material_id_or_name>: Replace with the ID or name of the material you want to use for mass estimation (see the list of materials above).
Options:

--unit: (Optional) Specify the unit for volume calculation. Choices are cm (default) or inch.
Examples:

Calculate the volume and mass of torus.stl using ABS material:

```bash
python volume_calculator.py torus.stl volume --material ABS
```
Calculate the surface area of torus.stl:
```bash
python volume_calculator.py torus.stl area
```
## Materials Supported

The script comes with an extensive list of 3D printable materials each with its specified density which is used to calculate the mass of the model. The materials included are:
- ABS
- PLA
- 3k CFRP
- Plexiglass
- Alumide
- Aluminum
- Brass
- Bronze
- Copper
- Gold_14K
- Gold_18K
- Polyamide_MJF
- Polyamide_SLS
- Rubber
- Silver
- Steel
- Titanium
- Resin
- Carbon Steel
- Red Oak
- PETG

## Reporting Issues
Please report any error you may find to me (mar.canet@gmail.com).

## Author
Mar Canet Sola(http://var-mar.info) - Twitter: mcanet

If you want to make a donation you can do in our PayPal account: varvarag@gmail.com

## Additional Resources

If someone is looking for some explanation about volume calculator i recommend read this blog post: http://n-e-r-v-o-u-s.com/blog/?p=4415

