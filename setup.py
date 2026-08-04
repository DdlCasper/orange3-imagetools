from setuptools import setup, find_packages

setup(
    name="orange3-imagetools",
    packages=find_packages(),
    entry_points={
        'orange.widgets': [
            # Name of the category
            'Image tools = orangecontrib.imagetools.widgets',
        ],
    },
)