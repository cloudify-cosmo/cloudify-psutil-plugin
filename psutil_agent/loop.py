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
import logging
import os
import sched
import sys
import time

import pika
import psutil
from pika.exceptions import AMQPError


def get_channel(rabbit_config):
    credentials = pika.PlainCredentials(rabbit_config['broker_user'],
                                        rabbit_config['broker_pass'])

    params = pika.ConnectionParameters(credentials=credentials,
                                       host=rabbit_config['broker_hostname'],
                                       virtual_host=rabbit_config['vhost'],
                                       port=rabbit_config['broker_port'])

    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.exchange_declare(exchange='cloudify-monitoring',
                             exchange_type="topic",
                             auto_delete=True,
                             durable=False,
                             internal=False)

    return channel


def prepare_data(rabbit_config, name, result):
    service_elements = [
        rabbit_config['deployment_id'],
        rabbit_config['node_name'],
        rabbit_config['node_id'],
        name
    ]

    return {
        'node_id': rabbit_config['node_id'],
        'node_name': rabbit_config['node_name'],
        'deployment_id': rabbit_config['deployment_id'],
        'name': name,
        'path': '',
        'metric': result,
        'unit': '',
        'type': 'GAUGE',
        'host': rabbit_config['node_id'],
        'service': '.'.join(service_elements),
        'time': int(time.time()),
    }


def publish_data(rabbit_config, alias, method, result):
    metric_data = prepare_data(rabbit_config, alias or method, result)
    channel = get_channel(rabbit_config)

    try:
        channel.basic_publish(
                exchange='cloudify-monitoring',
                routing_key=rabbit_config['deployment_id'],
                body=json.dumps(metric_data))
    except AMQPError as e:
        logging.error('Publishing metrics failed: {0} {1}'
                      .format(type(e).__name__, e))


def create_scheduled_fun(rabbit_config, scheduler, method, interval,
                         f_args, result_argument, alias):
    try:
        fun = getattr(psutil, method)
    except AttributeError as e:
        logging.error('Retrieving a psutil function failed: {0} {1}'
                      .format(type(e).__name__, e))
        return

    def scheduled_fun():
        try:
            result = fun(**f_args)
        except TypeError as e:
            logging.error(
                    'Invoking a psutil function failed: {0} {1}'
                    .format(type(e).__name__, e))
            return
        except Exception as e:
            logging.error(
                    'Invoking a psutil function failed: {0} {1}'
                    .format(type(e).__name__, e))
            result = None

        if result:
            if result_argument:
                try:
                    result = getattr(result, result_argument)
                except AttributeError as e:
                    logging.error('Retrieving an argument from '
                                  'result failed: {0} {1}'
                                  .format(type(e).__name__, e))
                    return

            publish_data(rabbit_config, alias, method, result)

        scheduler.enter(interval, 1, scheduled_fun, ())

    scheduled_fun()


def collect_metrics(rabbit_config, psutil_config):
    scheduler = sched.scheduler(time.time, time.sleep)

    for config in psutil_config:
        if 'method' not in config:
            logging.error("Method wasn't passed. Ignoring metric...")
            continue

        if 'interval' not in config:
            logging.error("Interval wasn't passed. Ignoring metric...")
            continue

        create_scheduled_fun(rabbit_config, scheduler,
                             config['method'], config['interval'],
                             config.get('args', {}),
                             config.get('result_argument', None),
                             config.get('alias', None))

    scheduler.run()


def main():
    args = [json.loads(a.replace('\\"', '"')) for a in sys.argv[1:]]
    rabbit_config, log_dir, psutil_config = args[0], args[1], args[2:]

    logging.basicConfig(filename=os.path.join(log_dir, 'psutil.log'))

    collect_metrics(rabbit_config, psutil_config)


if __name__ == '__main__':
    main()
