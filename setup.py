from setuptools import setup, find_packages

setup(
    name="cloudmanager",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "boto3", 
        "jinja2" # Add other dependencies here
        # other dependencies...
    ],
    entry_points={
        "console_scripts": [
            "cloudmanager=cloudmanager.runner:main",  # This will create a `cloudmanager` command
        ],
    },
)
