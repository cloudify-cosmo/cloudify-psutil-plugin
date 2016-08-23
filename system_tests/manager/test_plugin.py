########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import os
import time

from influxdb import InfluxDBClient
from influxdb.client import InfluxDBClientError

from cosmo_tester.framework.testenv import TestCase

import psutil_agent

PSUTIL_PLUGIN_URL = 'https://github.com/cloudify-cosmo/cloudify-psutil-plugin'


class PsutilPluginTest(TestCase):
    def setUp(self):
        super(PsutilPluginTest, self).setUp()
        self.repo_dir = os.path.dirname(os.path.dirname(psutil_agent.__file__))
        self.blueprint_yaml = os.path.join(self.repo_dir, 'samples',
                                           'blueprint.yaml')

    def test_psutil_plugin(self):

        try:
            self.upload_blueprint(self.test_id)
            self.create_deployment(self.test_id, self.test_id, self.inputs)
            self.execute_install(self.test_id)

            self.logger.info('Checking for monitoring data before reboot...')
            self._assert_monitoring_data_is_coming_before_reboot()

            self.logger.info('Rebooting...')

            instances = self.client.node_instances.list(self.test_id)
            instance = instances.items[0]
            aws_resource_id = instance.runtime_properties['aws_resource_id']

            c = self.env.handler.ec2_client()
            c.reboot_instances(aws_resource_id)

            self.logger.info('Checking for monitoring data after reboot...')
            self._assert_monitoring_data_is_coming_after_reboot()

        finally:
            self.cfy.execute_uninstall(self.test_id)
            self.cfy.delete_deployment(self.test_id)
            self.cfy.delete_blueprint(self.test_id)

    def _check_if_new_monitoring_data_appeared_recently(self):
        influx_client = InfluxDBClient(self.env.management_ip, 8086,
                                       'root', 'root', 'cloudify')
        try:
            results = influx_client.query(
                    'select * from /^{}\./i where time > now() - 10s'
                    .format(self.test_id))

            return len(results) > 0

        except InfluxDBClientError as e:
            self.fail('InfluxDBClient returned error: {}'.format(e.message))

    def _assert_monitoring_data_is_coming_before_reboot(self):
        for i in range(5):
            if i:
                time.sleep(60)

            if self._check_if_new_monitoring_data_appeared_recently():
                return

        self.fail('No new data came within 5 minutes.')

    def _assert_monitoring_data_is_coming_after_reboot(self):

        for _ in range(5):
            time.sleep(60)

            if self._check_if_new_monitoring_data_appeared_recently():
                return

        self.fail('No new data came within 5 minutes after reboot.')

    @property
    def inputs(self):
        return {
            'user': 'Administrator',
            'instance_type': self.env.medium_instance_type,
            'image_id': self.env.windows_server_2012_r2_image_id,
        }
