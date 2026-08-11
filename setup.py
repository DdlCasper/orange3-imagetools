from setuptools import setup, find_packages

setup(
    name="orange3-imagetools",
    version = "0.1.0"
    packages=find_packages(),
    entry_points={
        'orange.widgets': [
            # Name of the category
            'Image tools = orangecontrib.imagetools.widgets',
        ],
    },
)