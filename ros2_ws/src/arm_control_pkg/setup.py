import os                                            # + 添加这行
from glob import glob                                # + 添加这行
from setuptools import find_packages, setup

package_name = 'arm_control_pkg'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        # + 添加下面这行：注册 models 文件夹，使其在安装后可被访问
        (os.path.join('share', package_name, 'models'), glob('models/*.onnx')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='your_name',
    maintainer_email='your_email@example.com',
    description='ROS 2 package for hand gesture arm control',
    license='Apache-2.0',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            # + 添加下面这两行：注册你的两个节点
            'vision_node = arm_control_pkg.vision_node:main',
            'inference_node = arm_control_pkg.inference_node:main',
        ],
    },
)