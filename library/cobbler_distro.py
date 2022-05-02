#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright: (c) 2018, Dag Wieers (dagwieers) <dag@wieers.com>
# Copyright: (c) 2022, Bruno Travouillon (btravouillon) <devel@travouillon.fr>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = r'''
---
module: cobbler_distro
short_description: Manage distro objects in Cobbler
description:
- Add, modify or remove distros in Cobbler
options:
  host:
    description:
    - The name or IP address of the Cobbler server.
    default: 127.0.0.1
    type: str
  port:
    description:
    - Port number to be used for REST connection.
    - The default value depends on parameter C(use_ssl).
    type: int
  username:
    description:
    - The username to log in to Cobbler.
    default: cobbler
    type: str
  password:
    description:
    - The password to log in to Cobbler.
    type: str
  use_ssl:
    description:
    - If C(no), an HTTP connection will be used instead of the default HTTPS connection.
    type: bool
    default: 'yes'
  validate_certs:
    description:
    - If C(no), SSL certificates will not be validated.
    - This should only set to C(no) when used on personally controlled sites using self-signed certificates.
    type: bool
    default: 'yes'
  name:
    description:
    - The distro name to manage.
    type: str
  properties:
    description:
    - A dictionary with distro properties.
    type: dict
  sync:
    description:
    - Sync on changes.
    - Concurrently syncing Cobbler is bound to fail.
    type: bool
    default: no
  state:
    description:
    - Whether the distro should be present, absent or a query is made.
    choices: [ absent, present, query ]
    default: present
    type: str
author:
- Bruno Travouillon (@btravouillon)
notes:
- Concurrently syncing Cobbler is bound to fail with weird errors.
- On python 2.7.8 and older (i.e. on RHEL7) you may need to tweak the python behaviour to disable certificate validation.
  More information at L(Certificate verification in Python standard library HTTP clients,https://access.redhat.com/articles/2039753).
'''

EXAMPLES = r'''
- name: Ensure the distro exists in Cobbler
  cobbler_distro:
    host: cobbler01
    username: cobbler
    password: MySuperSecureP4sswOrd
    name: debian-11
    properties:
      breed: debian
      initrd: /var/lib/tftpboot/debian/11.2/debian-installer/amd64/initrd.gz
      kernel: /var/lib/tftpboot/debian/11.2/debian-installer/amd64/kernel
  delegate_to: localhost

- name: Query all distros in Cobbler
  cobbler_distro:
    host: cobbler01
    username: cobbler
    password: MySuperSecureP4sswOrd
    state: query
  register: cobbler_distros
  delegate_to: localhost

- name: Query a specific distro in Cobbler
  cobbler_distro:
    host: cobbler01
    username: cobbler
    password: MySuperSecureP4sswOrd
    name: debian-11
    state: query
  register: cobbler_distro_properties
  delegate_to: localhost

- name: Ensure the distro does not exist in Cobbler
  cobbler_distro:
    host: cobbler01
    username: cobbler
    password: MySuperSecureP4sswOrd
    name: debian-11
    state: absent
  delegate_to: localhost
'''

RETURN = r'''
distros:
  description: List of distros
  returned: C(state=query) and C(name) is not provided
  type: list
distro:
  description: (Resulting) information about the distro we are working with
  returned: when C(name) is provided
  type: dict
'''

import datetime
import ssl

from ansible.module_utils.basic import AnsibleModule
from ansible.module_utils.six import iteritems
from ansible.module_utils.six.moves import xmlrpc_client
from ansible.module_utils.common.text.converters import to_text


def getdistro(conn, name, token):
    distro = dict()
    if name:
        distros = conn.find_distro(dict(name=name), token)
        if distros:
            distro = distros[0]
    return distro


def main():
    module = AnsibleModule(
        argument_spec=dict(
            host=dict(type='str', default='127.0.0.1'),
            port=dict(type='int'),
            username=dict(type='str', default='cobbler'),
            password=dict(type='str', no_log=True),
            use_ssl=dict(type='bool', default=True),
            validate_certs=dict(type='bool', default=True),
            name=dict(type='str'),
            properties=dict(type='dict'),
            sync=dict(type='bool', default=False),
            state=dict(type='str', default='present', choices=['absent', 'present', 'query']),
        ),
        supports_check_mode=True,
    )

    username = module.params['username']
    password = module.params['password']
    port = module.params['port']
    use_ssl = module.params['use_ssl']
    validate_certs = module.params['validate_certs']

    name = module.params['name']
    state = module.params['state']

    module.params['proto'] = 'https' if use_ssl else 'http'
    if not port:
        module.params['port'] = '443' if use_ssl else '80'

    result = dict(
        changed=False,
    )

    start = datetime.datetime.utcnow()

    ssl_context = None
    if not validate_certs:
        try:
            ssl_context = ssl._create_unverified_context()
        except AttributeError:
            # Legacy Python that doesn't verify HTTPS certificates by default
            pass
        else:
            # Handle target environment that doesn't support HTTPS verification
            ssl._create_default_https_context = ssl._create_unverified_context

    url = '{proto}://{host}:{port}/cobbler_api'.format(**module.params)
    if ssl_context:
        conn = xmlrpc_client.ServerProxy(url, context=ssl_context)
    else:
        conn = xmlrpc_client.Server(url)

    try:
        token = conn.login(username, password)
    except xmlrpc_client.Fault as e:
        module.fail_json(msg="Failed to log in to Cobbler '{url}' as '{username}'. {error}".format(url=url, error=to_text(e), **module.params))
    except Exception as e:
        module.fail_json(msg="Connection to '{url}' failed. {error}".format(url=url, error=to_text(e), **module.params))

    distro = getdistro(conn, name, token)

    if state == 'query':
        if name:
            result['distro'] = distro
        else:
            # Return a list of dictionaries
            result['distros'] = conn.get_distros()

    elif state == 'present':

        if distro:
            # Update existing entry
            distro_id = conn.get_distro_handle(name, token)

            for key, value in iteritems(module.params['properties']):
                if key not in distro:
                    module.warn("Property '{0}' is not a valid distro property.".format(key))
                if distro[key] != value:
                    try:
                        conn.modify_distro(distro_id, key, value, token)
                        result['changed'] = True
                    except Exception as e:
                        module.fail_json(msg="Unable to change '{0}' to '{1}'. {2}".format(key, value, e))

        else:
            # Create a new entry
            distro_id = conn.new_distro(token)
            conn.modify_distro(distro_id, 'name', name, token)
            result['changed'] = True

            if module.params['properties']:
                for key, value in iteritems(module.params['properties']):
                    try:
                        conn.modify_distro(distro_id, key, value, token)
                    except Exception as e:
                        module.fail_json(msg="Unable to change '{0}' to '{1}'. {2}".format(key, value, e))

        # Only save when the entry was changed
        if not module.check_mode and result['changed']:
            conn.save_distro(distro_id, token)

    elif state == 'absent':

        if distro:
            if not module.check_mode:
                conn.remove_distro(name, token)
            result['changed'] = True

    if not module.check_mode and module.params['sync'] and result['changed']:
        try:
            conn.sync(token)
        except Exception as e:
            module.fail_json(msg="Failed to sync Cobbler. {0}".format(to_text(e)))

    if state in ('absent', 'present'):
        result['distro'] = getdistro(conn, name, token)

        if module._diff:
            result['diff'] = dict(before=distro, after=result['distro'])

    elapsed = datetime.datetime.utcnow() - start
    module.exit_json(elapsed=elapsed.seconds, **result)


if __name__ == '__main__':
    main()
