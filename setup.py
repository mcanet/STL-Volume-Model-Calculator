from setuptools import setup, find_packages

setup(
    name='stl-volume-calculator',
    version='1.0.0',
    author='Mar Canet',
    author_email='mar.canet@gmail.com',
    description='Calculate volume and mass of STL models (binary and ASCII), NIfTI, and DICOM files.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
    url='https://github.com/mcanet/STL-Volume-Model-Calculator',
    packages=find_packages(),
    install_requires=[
        'numpy>=1.19',
        'numpy-stl>=2.0',
        'nibabel>=3.0',
        'pydicom>=2.0',
        'scikit-image>=0.19',
        'tqdm>=4.0'
    ],
    entry_points={
        'console_scripts': [
            'volume_calculator=volume_calculator:main',
        ],
    },
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
)
