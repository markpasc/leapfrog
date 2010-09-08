from setuptools import setup

setup(
    name='giraffe',
    version='1.0',
    packages=['giraffe'],
    include_package_data=True,

    requires=['Django', 'south', 'celery', 'django_celery', 'httplib2', 'passogva', 'BeautifulSoup(<3.1)'],
    install_requires=['Django', 'south', 'celery', 'django_celery', 'httplib2', 'passogva', 'BeautifulSoup<3.1'],
)
