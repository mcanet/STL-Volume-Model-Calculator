# STL Volume Model Calculator

A easy-to-use command-line tool to calculate the volume, surface area, bounding box, and mass of 3D STL models. It provides a comprehensive analysis by default and supports STL (ASCII and binary), NIfTI, and DICOM formats.

## Key Features

-   **Comprehensive Analysis by Default**: Run it with just a filename to get file size, triangle count, bounding box, surface area, and volume.
-   **Dual Infill Mass Comparison**: Automatically calculates and compares the model's mass at a specified infill percentage (defaulting to 20%) against a 100% solid version.
-   **Full Mass Estimation**: Automatically calculates the estimated mass for over 20 common and specialized 3D printing materials in one go.
-   **Rich Console Output**: Presents data in beautifully formatted and easy-to-read tables.
-   **JSON Output**: Supports JSON output for easy integration with other scripts and applications.
-   **Optimized Calculations**: Option to run specific, single calculations for faster results in automated workflows.
-   **Broad File Support**: Handles binary and ASCII STL files, as well as medical imaging formats like NIfTI and DICOM.

## Installation

Make sure you have [Python 3.6+](https://www.python.org/) installed. You can then install the tool directly from the source code.

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mcanet/STL-Volume-Model-Calculator.git
    cd STL-Volume-Model-Calculator
    ```
2.  **Install the package:**
    This command uses the `setup.py` file to handle all dependencies and install the `volume-calculator` command in your system.
    ```bash
    pip install .
    ```

## Usage

After installation, you can run the `volume-calculator` command from any directory.

### Default Full Analysis

This is the recommended and most common use case. Simply provide the path to your model.

```bash
volume-calculator YourModel.stl
```

## Command-Line Arguments

| Argument | Description |
| :--- | :--- |
| `filename` | Path to your model file (STL, NIfTI, DICOM). |
| `--calculation` | (Optional) Optimize by running a single calculation: `volume` or `area`. |
| `--infill <percentage>` | (Optional) The infill percentage used for the primary mass calculation. Defaults to 20.0. The secondary calculation is always 100%. |
| `--material <ID>` | (Optional) Use with `--calculation volume` to specify a material ID. |
| `--unit <unit>` | (Optional) Display volume in `cm` (default) or `inch`. |
| `--output-format` | (Optional) Choose output format: `table` (default) or `json`. |
| `--list-materials` | Display a table of all available materials and their IDs, then exit. |

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
Mar Canet Sola (http://var-mar.info) - Twitter: mcanet

If you want to make a donation you can do in our PayPal account: varvarag@gmail.com

## Additional Resources

If someone is looking for some explanation about volume calculator i recommend read this blog post: http://n-e-r-v-o-u-s.com/blog/?p=4415

