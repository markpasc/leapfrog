# giraffe #

Giraffe is a personal "social network" node. It offers a "news feed" like activity reading and publishing system, using open protocols to integrate with other installations of Giraffe and similar software.

Giraffe isn't anywhere near done, but you can check out what's here, such as it is.


## Requirements ##

Giraffe is a Django application. To use it, you will need:

* Python 2.x (2.5 or greater)
* virtualenv and pip
* An AMQP server such as RabbitMQ


## Install ##

To install giraffe for easy development:

1. Check out `giraffe` to a place on disk.
2. Create a new [virtual environment][].
3. From the giraffe checkout, run: `pip install -e .`
4. Create a new Django project: `django-admin.py startproject website`
5. Configure some additional Django project settings, as shown in `example/settings.py`.
6. Configure your project's urlconf to include the giraffe apps' urlconfs, as shown in `example/urls.py`.

[virtual environment]: http://virtualenv.openplans.org/
