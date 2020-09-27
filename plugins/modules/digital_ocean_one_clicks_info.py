#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# Copyright: Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
from ansible.module_utils._text import to_native
from ansible_collections.community.digitalocean.plugins.module_utils.digital_ocean import DigitalOceanHelper
from ansible.module_utils.basic import AnsibleModule, env_fallback
from traceback import format_exc
import json
import time
__metaclass__ = type


DOCUMENTATION = r'''
---
module: digital_ocean_one_clicks_info
short_description: List all DigitalOcean 1-Click applications
description:
     - List all DigitalOcean 1-Click applications
author: "Mark Mercado (@mamercad)"
options:
  oauth_token:
    description:
      - DigitalOcean OAuth token. Can be specified in C(DO_API_KEY), C(DO_API_TOKEN), or C(DO_OAUTH_TOKEN) environment variables
    aliases: ['API_TOKEN']
    required: True
  type:
    description:
      - Type of 1-click application (e.g., "droplet" or "kubernetes")
    type: str
    required: False
requirements:
  - "python >= 2.6"
'''


EXAMPLES = r'''
- name: List all DigitalOcean 1-click applications
  community.digitalocean.digital_ocean_one_clicks_info:
    oauth_token: "{{ do_api_token }}"

- name: List all DigitalOcean 1-click (Droplet) applications
  community.digitalocean.digital_ocean_one_clicks_info:
    oauth_token: "{{ do_api_token }}"
    type: droplet

- name: List all DigitalOcean 1-click (Kubernetes) applications
  community.digitalocean.digital_ocean_one_clicks_info:
    oauth_token: "{{ do_api_token }}"
    type: kubernetes
'''

# Digital Ocean API info https://developers.digitalocean.com/documentation/v2/#1-click-applications
RETURN = r'''
data:
- slug: moon
  type: kubernetes
- slug: fyipe
  type: kubernetes
- slug: robomotion
  type: kubernetes
...
'''


class DOOneClicksInfo(object):
    def __init__(self, module):
        self.rest = DigitalOceanHelper(module)
        self.module = module
        self.unique_name = self.module.params.pop('unique_name', False)
        # Pop the oauth token so we don't include it in the POST data
        self.module.params.pop('oauth_token')
        self.type = self.module.params['type']

    def get_oneclicks(self):
        if self.type:
            response = self.rest.get('1-clicks?type={}'.format(self.type))
        else:
            response = self.rest.get('1-clicks?')
        json_data = response.json
        return json_data


def core(module):
    oneclicks = DOOneClicksInfo(module)
    module.exit_json(changed=False, data=oneclicks.get_oneclicks()["1_clicks"])


def main():
    module = AnsibleModule(
        argument_spec=dict(
            oauth_token=dict(
                aliases=['API_TOKEN'],
                no_log=True,
                fallback=(env_fallback, ['DO_API_TOKEN',
                                         'DO_API_KEY', 'DO_OAUTH_TOKEN'])
            ),
            type=dict(type=str, required=False),
        ),
    )
    try:
        core(module)
    except Exception as e:
        module.fail_json(msg=to_native(e), exception=format_exc())


if __name__ == '__main__':
    main()
