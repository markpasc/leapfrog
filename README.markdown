# leapfrog #

Leapfrog helps you read your internet neighborhood. It shows you what your friends are talking about on several community web sites.

Leapfrog isn't done, but you can check out what's here. You can also see it in action on the web at [leapf.org](http://leapf.org/).


## Requirements ##

Leapfrog is a Django application. To use it, you will need:

* Python 2.x (2.5 or greater)
* virtualenv and pip


## Install ##

To install leapfrog for easy development:

1. Check out this `leapfrog` project to a place on disk.
2. Create a new [virtual environment][].
3. From the `leapfrog` checkout, run: `pip install -e .` (with a period).
4. Create a new Django project: `django-admin.py startproject website`
5. Configure some additional Django project settings, as shown in `example/settings.py`.
6. Configure your project's urlconf to include the leapfrog app's urlconfs, as shown in `example/urls.py`.

[virtual environment]: http://virtualenv.openplans.org/
