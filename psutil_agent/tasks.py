#########
# Copyright (c) 2015 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#  * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  * See the License for the specific language governing permissions and
#  * limitations under the License.
#

import json
import os
import subprocess
import sys
import tempfile

from cloudify import broker_config
from cloudify import utils
from cloudify.decorators import operation
from cloudify_agent.api.utils import get_absolute_resource_path

NSSM_EXE = get_absolute_resource_path(os.path.join('pm', 'nssm', 'nssm.exe'))
PSUTIL_SERVICE = 'cloudify-psutil'
LOOP_FILE = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                         'loop.py')


@operation
def start(ctx, psutil_config, **kwargs):
    broker_user, broker_pass, _ = utils.internal.get_broker_credentials(
            ctx.bootstrap_context.cloudify_agent)

    broker_port, ssl_options = utils.internal.get_broker_ssl_and_port(
            ssl_enabled=broker_config.broker_ssl_enabled,
            cert_path=broker_config.broker_cert_path)

    rabbit_config_dict = {
        'broker_user': broker_user,
        'broker_pass': broker_pass,
        'broker_ssl_enabled': broker_config.broker_ssl_enabled,
        'broker_hostname': broker_config.broker_hostname,
        'broker_port': broker_port,
        'ssl_options': ssl_options,
        'vhost': '/',
        'node_id': ctx.node.id,
        'node_name': ctx.node.name,
        'deployment_id': ctx.deployment.id,
    }

    rabbit_config = ['"{0}"'.format(
            json.dumps(rabbit_config_dict).replace('"', '\\"'))]

    log_dir_string = os.getenv('CELERY_WORK_DIR') or tempfile.gettempdir()
    log_dir = ['"{0}"'.format(json.dumps(log_dir_string).replace('"', '\\"'))]

    psutil_config = ['"{0}"'.format(
            json.dumps(a).replace('"', '\\"')) for a in psutil_config]

    paths = ['"{0}"'.format(json.dumps(sys.path).replace('"', '\\"'))]

    nssm_args = [NSSM_EXE, 'install', PSUTIL_SERVICE, sys.executable,
                 LOOP_FILE]

    install_service_command = (nssm_args + rabbit_config + log_dir + paths +
                               psutil_config)

    subprocess.call(install_service_command)
    subprocess.call([NSSM_EXE, 'start', PSUTIL_SERVICE])


@operation
def stop(ctx, **kwargs):
    subprocess.call([NSSM_EXE, 'stop', PSUTIL_SERVICE])
    subprocess.call([NSSM_EXE, 'remove', PSUTIL_SERVICE, 'confirm'])
