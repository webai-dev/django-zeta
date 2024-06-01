============
Installation
============

To install a development environment for ery.Backend on the current Ubuntu LTS release.

Clone the latest version of the code base by making sure that your SSH key is added to gitlab.com for your user with privileges to the ery-group.
Next, run::

    git clone git@gitlab.com:zetadelta/ery/ery_backend.git

Next enter the directory and run the install script::

    cd ery_backend
    make install

Now, setup a virtual Python environment for the ery_backend::

    mkvirtualenv ery

To enter the virtual Python environment from another shell or later, you only need to type::

    activate ery

You should now be able to setup your database environment (and its related migrations) by running::

    ./utility/full_jdorsett.sh

So, finally, we are ready to test the installation::

    ./manage.py runserver

Open a browser and checkout the landing page of the backend at http://localhost:8080/.
