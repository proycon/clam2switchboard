CLAM2Switchboard
-----------------

Converts metadata from a live CLAM webservice to (one or multiple) JSON entry/entries for the `CLARIN language research switchboard <http://github.com/clarin-eric/switchboard>`_ registry.

Usage
------

Specify a URL and a task:

Example::

    clam2switchboard --url https://webservices-lst.science.ru.nl/ucto --task "Tokenisation"

Limitations
-------------

* Input language detection only works if the target clam service provides it and if it provides iso-639-3 or iso-639-1.
  Set ``--langparam`` to the parameter ID your CLAM service uses for input language (defaults to ``language``). You can
  also simply specify all languages as a comma separated list manually using the ``-l`` flag.
* Only works with CLAM v3.0 services and above.




