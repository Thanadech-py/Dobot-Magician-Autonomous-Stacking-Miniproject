import os
from glob import glob
from setuptools import find_packages, setup

package_name = 'dobot_v2'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'),
            glob(os.path.join('launch', '*launch.[pxy][yma]*'))),
        (os.path.join('share', package_name, 'config'),
            glob(os.path.join('config', '*.yaml'))),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='thxncdzch',
    maintainer_email='Thanadech9834@hotmail.com',
    description='TODO: Package description',
    license='TODO: License declaration',
    extras_require={
        'test': [
            'pytest',
        ],
    },
    entry_points={
        'console_scripts': [
            'detection_node = dobot_v2.detection_node:main',
            'calibrate_grid = dobot_v2.calibrate_grid:main',
            'dobot_controller = dobot_v2.dobot_controller_node:main',
        ],
    },
)
