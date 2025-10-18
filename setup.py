from setuptools import setup

# It's a good practice to read the long description from a file
with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name='stl-volume-calculator',
    version='1.0.2',  # Incremented version to reflect changes
    author='Mar Canet',
    author_email='mar.canet@gmail.com',
    description='Calculate volume, area, bounding box, and mass of STL, NIfTI, and DICOM files.',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/mcanet/STL-Volume-Model-Calculator',
    
    # Specify the single Python file that contains your application
    py_modules=["volume_calculator"],
    
    # List of dependencies needed for the project
    install_requires=[
        'tqdm>=4.0',
        'rich>=10.0'  # Added dependency for table formatting
    ],
    
    # This creates a command-line script that runs the `main` function
    entry_points={
        'console_scripts': [
            'volume-calculator=volume_calculator:main',
        ],
    },
    
    # Metadata for PyPI
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Intended Audience :: End Users/Desktop',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering',
        'Topic :: Multimedia :: Graphics :: 3D Modeling',
    ],
    
    python_requires='>=3.6',
)
