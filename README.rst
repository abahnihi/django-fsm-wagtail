django-fsm-wagtail
==================

Mixin to integrate django-fsm_ state transitions into the
Wagtail Admin.


Installation
------------

.. code:: sh

   $ pip install django-fsm-wagtail

Or from GitHub:

.. code:: sh

   $ pip install -e git://github.com/abahnihi/django-fsm-wagtail.git#egg=django-fsm-wagtail


Usage
-----

1. Add ``fsm_wagtail`` to your ``INSTALLED_APPS``.

.. code:: python

   from django.conf import settings

   TEMPLATE_CONTEXT_PROCESSORS = settings.TEMPLATE_CONTEXT_PROCESSORS + (
       "django.core.context_processors.request",
   )

2. In your ``admin.py`` file, use ``FsmWagtailAdminMixin`` to add behaviour to your
   ModelAdmin. You can remove ``ModelAdmin`` or ``FsmWagtailAdminMixin`` should be before ``ModelAdmin``, the order is
   important.

It assumes that your workflow state field is named ``state``, however you can
override it or add additional workflow state fields with the attribute
``fsm_field``.

.. code:: python

   from fsm_wagtail.admin import FsmWagtailAdminMixin

   class YourModelAdmin(FsmWagtailAdminMixin):
       # The name of one or more FSMFields on the model to transition
       fsm_field = ['wf_state',]


3. By adding ``custom=dict(admin=False)`` to the transition decorator, one can
   disallow a transition to show up in the admin interface. This specially is
   useful, if the transition method accepts parameters without default values,
   since in **django-fsm-admin** no arguments can be passed into the transition
   method.

.. code:: python

    @transition(
       field='state',
       source=['startstate'],
       target='finalstate',
       custom=dict(admin=False),
    )
    def do_something(self, param):
       # will not add a button "Do Something" to your admin model interface

By adding ``FSM_ADMIN_FORCE_PERMIT = True`` to your configuration settings, the
above restriction becomes the default. Then one must explicitly allow that a
transition method shows up in the admin interface.

.. code:: python

   @transition(
       field='state',
       source=['startstate'],
       target='finalstate',
       custom=dict(admin=True),
   )
   def proceed(self):
       # will add a button "Proceed" to your admin model interface

This is useful, if most of your state transitions are handled by other means,
such as external events communicating with the API of your application.

=======
Credits
=======


Special thanks to gadventures_ for the django-fsm-admin_ library where we used some of his code in this repo.


.. _django-fsm: https://github.com/kmmbvnr/django-fsm
.. _gadventures: https://github.com/gadventures
.. _django-fsm-admin: https://github.com/gadventures/django-fsm-admin