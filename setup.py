from setuptools import setup, find_packages

setup(
    name='VKinder',
    version='1.0',
    author='Roman Vlasenko',
    author_email='klavionik@gmail.com',
    url='https://github.com/Klavionik/python_coursework_2.git',
    packages=find_packages(),
    include_package_data=True,
    entry_points='''
        [console_scripts]
        vkinder=vkinder.scripts.cli:cli
    ''', install_requires=[
        'Click',
        'mechanize',
        'requests',
        'requests-oauthlib',
        'SQLAlchemy',
        'progressbar2',
    ],
    python_requires='>=3.8'
)
