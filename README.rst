nspawn-api
==========

This tool starts a gunicorn server as root to listen on /var/run/nspawn.sock
It exposes an API that makes it possible to manage nspawn containers.
At the moment it uses a mix of machinctl commands, dbus calls and nsenter to do what's needed.
I will try to port everything to dbus calls if possible.

This is how to run it:

.. code:: bash

    virtualenv sandbox
    echo "*" > sandbox/.gitignore
    . sandbox/bin/activate
    pip install -r requirements.txt
    sudo ./sandbox/bin/supervisord -c ./supervisord.conf

