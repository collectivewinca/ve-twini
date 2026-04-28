from setuptools import setup

setup(
    name="cli-anything-ve-twini",
    version="1.0.0",
    packages=["cli_anything.ve_twini"],
    package_data={
        "cli_anything.ve_twini": ["skills/*.md"],
    },
    include_package_data=True,
    install_requires=[
        "click>=8.0.0",
    ],
    entry_points={
        "console_scripts": [
            "cli-anything-ve-twini=cli_anything.ve_twini.__main__:main",
        ],
    },
    python_requires=">=3.10",
)
