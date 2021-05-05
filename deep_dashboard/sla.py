# -*- coding: utf-8 -*-

# Copyright 2021 Spanish National Research Council (CSIC)
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import asyncio
import json

import aiohttp
import aiohttp_session

from deep_dashboard import config
from deep_dashboard import orchestrator

CONF = config.CONF


def is_enabling_services(deployment_type, service_type):
    if deployment_type == "CLOUD":
        return service_type in ["org.openstack.nova", "com.amazonaws.ec2"]
    elif deployment_type == "MARATHON":
        return service_type in ["eu.indigo-datacloud.marathon"]
    elif deployment_type == "CHRONOS":
        return service_type in ["eu.indigo-datacloud.chronos"]
    elif deployment_type == "QCG":
        return service_type in ["eu.deep.qcg"]
    else:
        return True


async def get_slas(request, deployment_type=""):
    cli = await orchestrator.get_client(
        CONF.orchestrator.url,
        request
    )
    orchestrator_config = cli.config.get()

    slam_url = orchestrator_config.slam_url
    cmdb_url = orchestrator_config.cmdb_url
    access_token = request.app.iam_client.access_token

    headers = {
        'Authorization': f'bearer {access_token}'
    }

    session = await aiohttp_session.get_session(request)
    url = slam_url + "/preferences/" + session['organisation_name']

    cli_session = aiohttp.ClientSession()
    async with cli_session.get(url,
                               headers=headers,
                               raise_for_status=True) as r:
        content = await r.json()

    slas = content['sla']

    filtered_slas = []
    for sla in slas:
        service_id = sla['services'][0]['service_id']
        url = cmdb_url + "/service/id/" + service_id
        async with cli_session.get(url,
                                   headers=headers,
                                   raise_for_status=True) as r:
            # Unfortunately we cannot use r.json() here as the CMDB does not
            # send a proper content-type for the file, as it is being sent
            # as plaintext
            content = await r.read()
        content = json.loads(content)

        data = content["data"]
        service_type = data['service_type']
        sitename = data['sitename']
        endpoint = data.get('endpoint')
        iam_enabled = data.get('iam_enabled')

        if iam_enabled is None:
            iam_enabled = "True"

        gpu_support = data.get("properties", {}).get("gpu_support", False)
        if gpu_support:
            service_type = f"{service_type} (gpu_support: {gpu_support})"

        if is_enabling_services(deployment_type, service_type):
            sla['service_id'] = sla['services'][0]['service_id']
            sla['service_type'] = service_type
            sla['sitename'] = sitename
            sla['endpoint'] = endpoint
            sla['iam_enabled'] = iam_enabled

            filtered_slas.append(sla)

    return filtered_slas


async def load_slas(request):
    if not hasattr(request.app, "slas"):
        request.app.slas = []
    slas = await get_slas(request)
    request.app.slas = slas


async def load_slas_as_task(request):
    return asyncio.create_task(load_slas(request))
