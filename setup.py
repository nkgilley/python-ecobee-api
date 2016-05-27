from setuptools import setup

setup(name='python-ecobee',
      version='0.0.6',
      description='Python API for talking to Ecobee thermostats',
      url='https://github.com/nkgilley/python-ecobee-api',
      author='Nolan Gilley',
      license='GPLv2',
      install_requires=['requests>=2.0'],
      packages=['pyecobee'],
      zip_safe=True)
