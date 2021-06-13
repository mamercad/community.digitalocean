#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright: (c) 2018, Ansible Project
# Copyright: (c) 2018, Abhijeet Kasurde <akasurde@redhat.com>
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function

__metaclass__ = type


DOCUMENTATION = r"""
---
module: digital_ocean_snapshot
short_description: Create and delete DigitalOcean snapshots
description:
  - This module can be used to create and delete DigitalOcean Droplet and volume snapshots.
author: "Mark Mercado (@mamercad)"
options:
  state:
    description:
      - Whether the snapshot should be present (created) or absent (deleted).
    default: present
    choices:
      - present
      - absent
    type: str
  snapshot_type:
    description:
      - Specifies the type of snapshot information to be create or delete.
      - If set to C(droplet), then a Droplet snapshot is created.
      - If set to C(volume), then a volume snapshot is created.
    choices:
      - droplet
      - volume
    default: droplet
    required: false
    type: str
  snapshot_name:
    description:
      - Name of the snapshot to create.
    required: false
    type: str
  droplet_id:
    description:
      - Droplet ID to snapshot.
    required: false
    type: str
  volume_id:
    description:
      - Volume ID to snapshot.
    required: false
    type: str
  snapshot_id:
    description:
      - Snapshot ID to delete.
    required: false
    type: str
  wait:
    description:
      - Wait for the snapshot to be created before returning.
    required: False
    default: True
    type: bool
  wait_timeout:
    description:
      - How long before wait gives up, in seconds, when creating a snapshot.
    default: 120
    type: int
extends_documentation_fragment:
- community.digitalocean.digital_ocean.documentation

"""


EXAMPLES = r"""
- name: Snapshot a Droplet
  community.digitalocean.digital_ocean_snapshot:
    state: present
    snapshot_type: droplet
    snapshot_name: mysnapshot1
    droplet_id: 250329179
  register: result

- name: Delete a Droplet snapshot
  community.digitalocean.digital_ocean_snapshot:
    state: absent
    snapshot_type: droplet
    snapshot_id: 85905825
  register: result

- name: Snapshot a Volume
  community.digitalocean.digital_ocean_snapshot:
    state: present
    snapshot_type: volume
    snapshot_name: mysnapshot2
    volume_id: 9db5e329-cc68-11eb-b027-0a58ac144f91

- name: Delete a Volume snapshot
  community.digitalocean.digital_ocean_snapshot:
    state: absent
    snapshot_type: volume
    snapshot_id: a902cdba-cc68-11eb-a701-0a58ac145708
"""


RETURN = r"""
result:
  description: Snapshot creation or deletion result (resource ID for Droplets, snapshot ID for volumes).
  returned: success
  type: dict
  sample:
    changed: true
    failed: false
    msg: Created snapshot, resource 250329179
  sample:
    changed: true
    failed: false
    msg: Created snapshot, snapshot 1ef3915a-cc73-11eb-b13c-0a58ac145472
"""


import time
from traceback import format_exc
from ansible.module_utils.basic import AnsibleModule
from ansible_collections.community.digitalocean.plugins.module_utils.digital_ocean import (
    DigitalOceanHelper,
)


class DOSnapshot(object):
    def __init__(self, module):
        self.rest = DigitalOceanHelper(module)
        self.module = module
        self.wait = self.module.params.pop("wait", True)
        self.wait_timeout = self.module.params.pop("wait_timeout", 120)
        # pop the oauth token so we don't include it in the POST data
        self.module.params.pop("oauth_token")
        self.snapshot_type = module.params["snapshot_type"]
        self.snapshot_name = module.params["snapshot_name"]
        self.snapshot_id = module.params["snapshot_id"]
        self.volume_id = module.params["volume_id"]

    def wait_finished(self):
        end_time = time.monotonic() + self.wait_timeout
        while time.monotonic() < end_time:
            response = self.rest.get("actions/{0}".format(str(self.action_id)))
            status = response.status_code
            if status != 200:
                self.module.fail_json(
                    msg="Unable to find action {0}, please file a bug".format(
                        str(self.action_id)
                    )
                )
            json = response.json
            if json["action"]["status"] == "completed":
                return json
            time.sleep(min(10, end_time - time.monotonic()))
        self.module.fail_json(
            msg="Timed out waiting for snapshot, action {0}".format(str(self.action_id))
        )

    def create(self):
        if self.snapshot_type == "droplet":
            droplet_id = self.module.params["droplet_id"]
            data = {
                "type": "snapshot",
                "name": self.snapshot_name,
            }
            response = self.rest.post(
                "droplets/{0}/actions".format(str(droplet_id)), data=data
            )
            status = response.status_code
            json = response.json
            if status == 201:
                self.action_id = json["action"]["id"]
                if self.wait:
                    json = self.wait_finished()
                    raise Exception(str(json))
                    self.module.exit_json(
                        changed=True,
                        msg="Created snapshot, snapshot {0}".format(
                            json["action"]["resource_id"]
                        ),
                    )
                self.module.exit_json(
                    changed=True,
                    msg="Created snapshot, action {0}".format(self.action_id),
                )
            else:
                self.module.fail_json(
                    changed=False,
                    msg="Failed to create snapshot: {0}".format(json["message"]),
                )
        elif self.snapshot_type == "volume":
            data = {
                "name": self.snapshot_name,
            }
            response = self.rest.post(
                "volumes/{0}/snapshots".format(str(self.volume_id)), data=data
            )
            status = response.status_code
            json = response.json
            if status == 201:
                self.module.exit_json(
                    changed=True,
                    msg="Created snapshot, snapshot {0}".format(json["snapshot"]["id"]),
                )
            else:
                self.module.fail_json(
                    changed=False,
                    msg="Failed to create snapshot: {0}".format(json["message"]),
                )

    def delete(self):
        response = self.rest.delete("snapshots/{0}".format(str(self.snapshot_id)))
        status = response.status_code
        if status == 204:
            self.module.exit_json(
                changed=True,
                msg="Deleted snapshot {0}".format(str(self.snapshot_id)),
            )
        else:
            json = response.json
            self.module.fail_json(
                changed=False,
                msg="Failed to delete snapshot {0}: {1}".format(
                    self.snapshot_id, json["message"]
                ),
            )


def run(module):
    state = module.params.pop("state")
    snapshot = DOSnapshot(module)
    if state == "present":
        snapshot.create()
    elif state == "absent":
        snapshot.delete()


def main():
    argument_spec = DigitalOceanHelper.digital_ocean_argument_spec()
    argument_spec.update(
        state=dict(choices=["present", "absent"], default="present"),
        snapshot_type=dict(
            type="str", required=False, choices=["droplet", "volume"], default="droplet"
        ),
        snapshot_name=dict(type="str"),
        droplet_id=dict(type="str"),
        volume_id=dict(type="str"),
        snapshot_id=dict(type="str"),
        wait=dict(type="bool", default=True),
        wait_timeout=dict(default=120, type="int"),
    )
    module = AnsibleModule(
        argument_spec=argument_spec,
        required_if=[
            ("state", "present", ["snapshot_name"]),
            ("state", "absent", ["snapshot_id"]),
            ("snapshot_type", "droplet", ["droplet_id"]),
            ("snapshot_type", "volume", ["volume_id"]),
        ],
    )

    run(module)


if __name__ == "__main__":
    main()
