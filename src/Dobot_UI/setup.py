import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'Dobot_UI'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name, 'resource/dobot_ui']),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        (os.path.join('share', package_name, 'config'),
            glob(os.path.join('config', '*.yaml'))),
    ],
    install_requires=['setuptools', 'PyYAML'],
    zip_safe=True,
    maintainer='thxncdzch',
    maintainer_email='Thanadech9834@hotmail.com',
    description='PyQt6 User Interface Node for Dobot Magician Mission Control and Stacking Visualizer',
    license='MIT',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'dobot_ui = Dobot_UI.app:main',
            'Dobot_UI = Dobot_UI.app:main',
        ],
    },
)
