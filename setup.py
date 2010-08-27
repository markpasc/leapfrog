from setuptools import setup

setup(
    name='giraffe',
    version='1.0',
    packages=['giraffe'],
    include_package_data=True,

    requires=['Django', 'south', 'celery', 'django-celery', 'httplib2', 'passogva'],
    install_requires=['Django', 'south', 'celery', 'django-celery', 'httplib2', 'passogva'],
)
