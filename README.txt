dj-cmdbuild
===========

Introduction
------------

This project aims to offer tools to integrate with Django, and possibly
Python at large, databases made with CMDBuild_.

.. _CMDBuild: http://www.cmdbuild.org

Usage
-----

Launch a Python shell for your project::

  $ python manage.py shell
  Type "help", "copyright", "credits" or "license" for more information.
  (InteractiveConsole)
  >>> import django_cmdbuild.inspection
  >>> django_cmdbuild.inspection.inspect()

and save the resulting output as the models.py file for your application.

You can also choose to launch inspection from the shell::

  $ DJANGO_SETTINGS_MODULE=myproject.settings python /path/to/dj-cmdbuild/django_cmdbuild/inspection.py > models.py

Then, you should edit your models.py file as you see fit. Many database 
models inevitably have cycles in their dependency graph. This does
not mean that they are not correct; rather, you should let Django find
the spots where they do and set the referenced class name in quotes.

For example::

  person = ForeignKey(Person, db_column='Person', blank=True)
  
will become::

  person = ForeignKey('Person', db_column='Person', blank=True)
  
