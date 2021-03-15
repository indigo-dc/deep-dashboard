# -*- coding: utf-8 -*-

# Copyright 2019 Spanish National Research Council (CSIC)
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

from aiohttp import web
import aiohttp_session_flash as flash
import aiohttp_jinja2
import aiohttp_session
import aiohttp_session.cookie_storage
import orpy.exceptions
import requests

from deep_dashboard import config
from deep_dashboard import orchestrator
from deep_dashboard import utils

CONF = config.CONF

routes = web.RouteTableDef()


@routes.get("/deployments", name="deployments")
@aiohttp_jinja2.template('deployments/index.html')
async def get_deployments(request):
    context = await utils._get_context(request)
    context["deployments"] = []

    if not context["current_user"].get("authenticated"):
        session = await aiohttp_session.get_session(request)
        session["next"] = "deployments"
        return web.HTTPFound("/")

    cli = await orchestrator.get_client(
        CONF.orchestrator_url,
        request
    )

    try:
        context["deployments"] = cli.deployments.list()
    except orpy.exceptions.ClientException as e:
        flash.flash(
            request,
            ("danger", f"Error retrieving deployment list: {e.message}"),
        )
    finally:
        return context


@routes.get("/deployments/{uuid}/template", name="deployments.template")
@aiohttp_jinja2.template('deployments/template.html')
async def get_deployment_template(request):
    context = await utils._get_context(request)
    context["deployments"] = []

    if not context["current_user"].get("authenticated"):
        session = await aiohttp_session.get_session(request)
        session["next"] = "deployments"
        return web.HTTPFound("/")

    uuid = request.match_info['uuid']

    cli = await orchestrator.get_client(
        CONF.orchestrator_url,
        request
    )

    try:
        template = cli.deployments.get_template(uuid).template
        context["template"] = template
    except orpy.exceptions.ClientException as e:
        flash.flash(
            request,
            ("danger", f"Error retrieving deployment {uuid} template: "
                       f"{e.message}"),
        )
        return web.HTTPFound("/deployments")
    else:
        return context


# FIXME(aloga): this is not correct, we should not use a GET but a DELETE
@routes.get("/deployments/{uuid}/delete", name="deployments.delete")
async def delete_deployment(request):
    context = await utils._get_context(request)

    if not context["current_user"].get("authenticated"):
        session = await aiohttp_session.get_session(request)
        session["next"] = "deployments"
        return web.HTTPFound("/")

    uuid = request.match_info['uuid']

    cli = await orchestrator.get_client(
        CONF.orchestrator_url,
        request
    )

    try:
        cli.deployments.delete(uuid)
    except orpy.exceptions.ClientException as e:
        flash.flash(
            request,
            ("danger", f"Error deleting deployment {uuid}: {e.message}")
        )
    finally:
        request["context"] = context
        return web.HTTPFound("/deployments")


# FIXME(aloga): this is not correct, we should not use a GET but a DELETE
@routes.get("/deployments/{uuid}/history", name="deployments.history")
@aiohttp_jinja2.template('deployments/summary.html')
async def show_deployment_history(request):
    context = await utils._get_context(request)

    if not context["current_user"].get("authenticated"):
        session = await aiohttp_session.get_session(request)
        session["next"] = "deployments"
        return web.HTTPFound("/")

    uuid = request.match_info['uuid']

    cli = await orchestrator.get_client(
        CONF.orchestrator_url,
        request
    )

    try:
        deployment = cli.deployments.show(uuid)
    except orpy.exceptions.ClientException as e:
        flash.flash(
            request,
            ("danger", f'Error getting deployment {uuid}: {e.message}')
        )
        return web.HTTPFound("/deployments")

    # Check if deployment is still in 'create_in_progress'
    if 'deepaas_endpoint' not in deployment.outputs:
        flash.flash(
            request,
            ("warning",
             'Wait until creation is completed before you access the '
             'training history.')
        )
        return web.HTTPFound("/deployments")

    # Check if deployment has DEEPaaS V2
    deepaas_url = deployment.outputs['deepaas_endpoint']
    try:
        versions = requests.get(deepaas_url, verify=False).json()['versions']
        if 'v2' not in [v['id'] for v in versions]:
            raise Exception
    except Exception:
        flash.flash(
            request,
            ("warning",
             "You need to be running DEEPaaS V2 inside the deployment "
             "to be able to access the training history.")
        )
        return web.HTTPFound("/deployments")

    # Get info
    r = requests.get(deepaas_url + '/v2/models', verify=False).json()
    training_info = {}
    for model in r['models']:
        r = requests.get(
            '{}/v2/models/{}/train/'.format(deepaas_url, model['id']),
            verify=False
        )
        training_info[model['id']] = r.json()

    context["deployment"] = deployment
    context["training_info"] = training_info
    return context
