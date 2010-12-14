from setuptools import setup

setup(
    name='rhino',
    version='1.0',
    packages=['rhino'],
    include_package_data=True,

    #requires=['Django', 'south', 'celery', 'django_celery', 'httplib2', 'passogva', 'BeautifulSoup(<3.1)', 'jinja2'],
    #install_requires=['Django', 'south', 'celery', 'django_celery', 'httplib2', 'passogva', 'BeautifulSoup<3.1', 'jinja2'],
    requires=['Django', 'south', 'jinja2', 'oauth2', 'pytidylib', 'remoteobjects', 'mimeparse', 'BeautifulSoup(<3.1)', 'pycrypto'],
)
