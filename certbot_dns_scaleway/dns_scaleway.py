"""DNS Authenticator for Scaleway DNS."""
import json
import logging
import requests

from certbot import errors
from certbot import interfaces
from certbot.plugins import dns_common

logger = logging.getLogger(__name__)

DEFAULT_ENDPOINT = 'https://api.scaleway.com'
DEFAULT_VERSION = 'v2beta1'
TOKEN_URL = 'https://cloud.scaleway.com/#/account'

class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for Scaleway

    This Authenticator uses the Scaleway API to fulfill a dns-01 challenge.
    """

    description = 'Obtain certificates using a DNS TXT record (if you are using Scaleway for DNS).'
    ttl = 60

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add):  # pylint: disable=arguments-differ
        super(Authenticator, cls).add_parser_arguments(add, default_propagation_seconds=60)
        add('credentials', help='Scaleway credentials INI file.')

    def more_info(self):  # pylint: disable=missing-docstring,no-self-use
        return 'This plugin configures a DNS TXT record to respond to a dns-01 challenge using ' + \
               'the Scaleway API.'

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            'credentials',
            'Scaleway credentials INI file',
            {
                'application_token': 'Token for Scaleway API, obtained from {0}'
                .format(TOKEN_URL),
            }
        )

    def _perform(self, domain, validation_name, validation):
        self._get_scaleway_client().add_txt_record(domain, validation_name, validation, self.ttl)

    def _cleanup(self, domain, validation_name, validation):
        self._get_scaleway_client().del_txt_record(domain, validation_name, validation)

    def _get_scaleway_client(self):
        return _ScalewayClient(
            self.credentials.conf('application-token')
        )


class _ScalewayClient(object):
    """
    Encapsulates all communication with Scaleway API.
    """

    def __init__(self, api_token):
        self.api_token = api_token

    def find_zone(self, domain_name):
        """
        Call the Scaleway Rest Api to find the zoneto use
        """
        headers = {
            "x-auth-token": self.api_token
        }

        url = "{}/domain/{}/dns-zones?" . format(DEFAULT_ENDPOINT, DEFAULT_VERSION)
        url += "page=1&page_size=10000"

        result = requests.get(url, headers=headers)

        if result.status_code != 200:
        # if error
            raise errors.PluginError('Error communicating with the Scaleway API : {0}'\
            .format(result.json()))

        # find the domain to use from the list
        while len(domain_name) > 0:
            for domain in result.json()['dns_zones']:
                if domain_name == domain["subdomain"]+"."+domain["domain"]:
                    return domain_name
                if domain_name == domain["domain"]:
                    return domain_name
            parts = domain_name.split('.', 1)
            logger.debug(parts)
            if len(parts) > 1:
                domain_name = parts[1]
            else:
                domain_name = ""

        raise errors.PluginError('Can''t found domain to use with the Scaleway API : {0}'\
        .format(result.json()))

    def update(self, args):
        """
        Call the Scaleway Rest Api to update/delete record
        """
        headers = {
            "x-auth-token": self.api_token
        }

        url = "{}/domain/{}/dns-zones/{}/records?page=1&page_size=10000"  .\
        format(DEFAULT_ENDPOINT, DEFAULT_VERSION, args['zone'])

        data = {
            "records": [
                {
                    "name": args['name'],
                    "type": args['type'],
                    "ttl": args['ttl'],
                    "data": args['content'],
                }
            ]
        }
        if args["type"] == "MX":
            data["records"][0]["priority"] = args['priority']

        if args['state'] == 'present':
            if args['unique']:
                action = 'set'
                data['name'] = args['name']
                data['type'] = args['type']
            else:
                action = 'add'

        else:
            action = 'delete'
            data = {}
            data['id_fields'] = {
                'name' : args['name'],
                'type' : args['type']
            }
            if args['content'] != '':
                data['id_fields']['data'] = args['content']

        data = {
            "return_all_records": False,
            "changes": [
                {
                    action: data
                }
            ]
        }

        result = requests.patch(url, json.dumps(data), headers=headers)

        if result.status_code != 200:
        # if error
            raise errors.PluginError('Error communicating with the Scaleway API : {0} calling {1}'\
            .format(result.json(),json.dumps(data)))


    def add_txt_record(self, domain, record_name, record_content, record_ttl):
        """
        Add a TXT record using the supplied information.
        :param str domain: The domain to use to look up the Scaleway zone.
        :param str record_name: The record name (typically beginning with '_acme-challenge.').
        :param str record_content: The record content (typically the challenge validation).
        :param int record_ttl: The record TTL (number of seconds that the record may be cached).
        :raises certbot.errors.PluginError: if an error occurs communicating with the Scaleway API
        """

        zone = self.find_zone(domain)

        data = {
            "name": record_name.replace('.' + zone, ''),
            "zone": zone,
            "type": "TXT",
            "ttl": record_ttl,
            "content": '"' + record_content + '"',
            "state": "present",
            "unique": False
        }

        try:
            logger.debug('Attempting to add record to domain and zone %s %s: %s',\
            domain, zone, record_name)
            self.update(data)

        except Exception as e:
            logger.error('Encountered Error adding TXT record: %s', e)
            raise errors.PluginError('Error communicating with the Scaleway API: {0}'.format(e))

        logger.debug('Successfully added TXT record')

    def del_txt_record(self, domain, record_name, record_content):
        """
        Delete a TXT record using the supplied information.
        Note that both the record's name and content are used to ensure that similar records
        created concurrently (e.g., due to concurrent invocations of this plugin) are not deleted.
        Failures are logged, but not raised.
        :param str domain: The domain to use to look up the Scaleway zone.
        :param str record_name: The record name (typically beginning with '_acme-challenge.').
        :param str record_content: The record content (typically the challenge validation).
        """

        zone = self.find_zone(domain)

        data = {
            "name": record_name.replace('.' + zone, ''),
            "zone": zone,
            "type": "TXT",
            "content": '"' + record_content + '"',
            "state": "absent",
            "ttl": 0
        }

        try:
            logger.debug('Attempting to delete record to domain and zone %s %s: %s',\
            domain, zone, record_name)
            self.update(data)
        except Exception as e:
            logger.error('Encountered Error deleting TXT record: %s', e)
            raise errors.PluginError('Error communicating with the Scaleway API: {0}'.format(e))

        logger.debug('Successfully deleted TXT record')

