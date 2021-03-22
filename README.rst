certbot-dns-scaleway
=====================

Scaleway_ DNS Authenticator plugin for Certbot_

This plugin automates the process of completing a ``dns-01`` challenge by adding/removing TXT records using the Scaleway DNS API.

Configuration of Scaleway Certbot Plugin
----------------------------------------

Generate a Token for your Project at Scaleway Console (follow https://www.scaleway.com/en/docs/generate-api-keys/)

.. _Scaleway: https://scaleway.com
.. _Certbot: https://certbot.eff.org/

Installation
------------

::

    pip install certbot-dns-scaleway


Named Arguments
---------------

To start using DNS authentication for Scaleway, use the following arguments on certbot's command line:

=============================================== ===============================================
``--authenticator dns-scaleway``                select the authenticator plugin (Required)

``--dns-scaleway-credentials``                  Scaleway credentials INI file. (Required)

``--dns-scaleway-propagation-seconds``          waiting time for DNS to propagate before asking
                                                the ACME server to verify the DNS record.
                                                (Default: 60)
=============================================== ===============================================


Credentials
-----------

An example ``scaleway.ini`` file:

.. code-block:: ini

   dns_scaleway_application_token = b3a0b9a9-3814-4f12-95b0-a7473bf8b306


**CAUTION:** You should protect these API credentials as you would the
password to your Scaleway project. Users who can read this file can use these
credentials to issue arbitrary API calls on your behalf. Users who can cause
Certbot to run using these credentials can complete a ``dns-01`` challenge to
acquire new certificates or revoke existing certificates for associated
domains, even if those domains aren't being managed by this server.

Certbot will emit a warning if it detects that the credentials file can be
accessed by other users on your system. The warning reads "Unsafe permissions
on credentials configuration file", followed by the path to the credentials
file. This warning will be emitted each time Certbot uses the credentials file,
including for renewal, and cannot be silenced except by addressing the issue
(e.g., by using a command like ``chmod 600`` to restrict access to the file).


Examples
--------

To acquire a single certificate for both ``example.com`` and
``*.example.com``, waiting 900 seconds for DNS propagation:

.. code-block:: bash

   certbot certonly \
     --authenticator dns-scaleway \
     --dns-scaleway-credentials /etc/letsencrypt/.secrets/scaleway.ini \
     --dns-scaleway-propagation-seconds 900 \
     --server https://acme-v02.api.letsencrypt.org/directory \
     --agree-tos \
     --rsa-key-size 4096 \
     -d 'example.com' \
     -d '*.example.com'


Docker
------

In order to create a docker container with a certbot-dns-scaleway installation,
create an empty directory with the following ``Dockerfile``:

.. code-block:: docker

    FROM certbot/certbot
    RUN pip install certbot-dns-scaleway

Proceed to build the image::

    docker build -t certbot/dns-scaleway .

Once that's finished, the application can be run as follows::

    docker run --rm \
       -v /var/lib/letsencrypt:/var/lib/letsencrypt \
       -v /etc/letsencrypt:/etc/letsencrypt \
       --cap-drop=all \
       certbot/dns-scaleway certonly \
       --authenticator dns-scaleway \
       --dns-scaleway-propagation-seconds 900 \
       --dns-scaleway-credentials \
           /etc/letsencrypt/.secrets/scaleway.ini \
       --no-self-upgrade \
       --keep-until-expiring --non-interactive --expand \
       --server https://acme-v02.api.letsencrypt.org/directory \
       -d example.com -d '*.example.com'

It is suggested to secure the folder as follows:

chown root:root /etc/letsencrypt/.secrets
chmod 600 /etc/letsencrypt/.secrets
