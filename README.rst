# openregistry.buildout
Development Buildout of OpenRegistry (part of OpenProcurement)

Follow the instructions:

  1. Bootstrap the buildout with Python 2.7:

     ```
     $ python bootstrap.py
     ```

  2. Build the buildout:

      ```
      $ bin/buildout
      ```

System requirements (fedora >=25):

    dnf install gcc file git libevent-devel python-devel sqlite-devel zeromq-devel libffi-devel openssl-devel systemd-python

Local development environment also requires additional dependencies:

    dnf install couchdb

To start environment services:

    bin/circusd --daemon

To run openregistry.api instance:

    bin/pserve etc/openregistry.api.ini

Run the following command

    bin/python run_tests.py

to run all tests from all dependency packages.
