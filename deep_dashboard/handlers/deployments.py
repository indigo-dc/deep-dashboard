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

import pathlib

import aiohttp
from aiohttp import web
import aiohttp_jinja2
import aiohttp_session_flash as flash
import orpy.exceptions
import yaml

from deep_dashboard import config
from deep_dashboard import log
from deep_dashboard import orchestrator

CONF = config.CONF
LOG = log.LOG

CONF = config.CONF

routes = web.RouteTableDef()


@routes.get("/deployments", name="deployments")
@aiohttp_jinja2.template('deployments/index.html')
async def get_deployments(request):
    request.context["deployments"] = []

    cli = await orchestrator.get_client(
        CONF.orchestrator.url,
        request
    )

    request.context["breadcrumbs"] = [
        ("Home", False, "/"),
        ("Deployments", True, "/deployments"),  # FIXME(aloga): use url
    ]

    try:
        request.context["deployments"] = cli.deployments.list()
    except orpy.exceptions.ClientException as e:
        flash.flash(
            request,
            ("danger", f"Error retrieving deployment list: {e.message}"),
        )
    finally:
        return request.context


@routes.get("/deployments/{uuid}/template", name="deployments.template")
@aiohttp_jinja2.template('deployments/template.html')
async def get_deployment_template(request):
    request.context["deployments"] = []

    uuid = request.match_info['uuid']

    request.context["breadcrumbs"] = [
        ("Home", False, "/"),
        ("Deployments", False, "/deployments"),  # FIXME(aloga): use url
        (uuid, False, f"/deployments/{uuid}"),  # FIXME(aloga): use url
        ("template", True, f"/deployments/{uuid}/template"),  # FIXME(aloga)
    ]

    cli = await orchestrator.get_client(
        CONF.orchestrator.url,
        request
    )

    try:
        template = cli.deployments.get_template(uuid).template
        request.context["template"] = template
    except orpy.exceptions.ClientException as e:
        flash.flash(
            request,
            ("danger", f"Error retrieving deployment {uuid} template: "
                       f"{e.message}"),
        )
        return web.HTTPFound("/deployments")
    else:
        return request.context


# FIXME(aloga): this is not correct, we should not use a GET but a DELETE
@routes.get("/deployments/{uuid}/delete", name="deployments.delete")
async def delete_deployment(request):
    uuid = request.match_info['uuid']

    cli = await orchestrator.get_client(
        CONF.orchestrator.url,
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
        return web.HTTPFound("/deployments")


# FIXME(aloga): this is not correct, we should not use a GET but a DELETE
@routes.get("/deployments/{uuid}/history/{model}/{training_uuid}/delete",
            name="training.delete")
async def delete_training(request):
    dep_uuid = request.match_info["uuid"]
    model = request.match_info["model"]
    training_uuid = request.match_info["training_uuid"]

    cli = await orchestrator.get_client(
        CONF.orchestrator.url,
        request
    )

    try:
        deployment = cli.deployments.show(dep_uuid)
    except orpy.exceptions.ClientException as e:
        flash.flash(
            request,
            ("danger", f'Error getting deployment {dep_uuid}: {e.message}')
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
        return web.HTTPFound(f"/deployments/{dep_uuid}/history")

    # Check if deployment has DEEPaaS V2
    deepaas_url = deployment.outputs['deepaas_endpoint']
    training_url = f"{deepaas_url}/v2/models/{model}/train/{training_uuid}"

    session = aiohttp.ClientSession()

    try:
        async with session.delete(training_url,
                                  raise_for_status=True) as r:
            if r.status not in [200, 201]:
                raise Exception
    except Exception as e:
        flash.flash(
            request,
            ("warning", f"Could not delete training!! (reason: {e.message})")
        )
    finally:
        return web.HTTPFound(f"/deployments/{dep_uuid}/history")


@routes.get("/deployments/{uuid}/history", name="deployments.history")
@aiohttp_jinja2.template('deployments/summary.html')
async def show_deployment_history(request):
    uuid = request.match_info['uuid']

    request.context["breadcrumbs"] = [
        ("Home", False, "/"),
        ("Deployments", False, "/deployments"),  # FIXME(aloga): use url
        (uuid, False, f"/deployments/{uuid}"),  # FIXME(aloga): use url
        ("history", True, f"/deployments/{uuid}/history"),  # FIXME(aloga)
    ]

    cli = await orchestrator.get_client(
        CONF.orchestrator.url,
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

    session = aiohttp.ClientSession()

    # Check if deployment has DEEPaaS V2
    deepaas_url = deployment.outputs['deepaas_endpoint']
    try:
        async with session.get(deepaas_url,
                               raise_for_status=True) as r:
            data = await r.json()
        versions = data['versions']
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
    async with session.get(deepaas_url + '/v2/models',
                           raise_for_status=False) as r:
        r = await r.json()

    training_info = {}
    for model in r['models']:
        async with session.get(f'{deepaas_url}/v2/models/{model["id"]}/train/',
                               raise_for_status=False) as r:
            training_info[model['id']] = await r.json()

    request.context["deployment"] = deployment
    request.context["training_info"] = training_info
    return request.context


@routes.post("/deployments")
async def create_module_training(request):
    form_data = await request.post()
    LOG.debug(f"Received form data: {form_data}")

    template_name = form_data.get('template')
    LOG.debug(f"Selected template file: {template_name}")

    tosca_dir = pathlib.Path(CONF.orchestrator.tosca_dir)
    tosca_dir = tosca_dir / CONF.orchestrator.deep_templates_dir
    with open(tosca_dir / template_name, "r") as f:
        template = yaml.full_load(f)

    params = {}
    if 'extra_opts.keepLastAttempt' in form_data:
        params["keepLastAttempt"] = "true"
    else:
        params["keepLastAttempt"] = "false"

    if form_data['extra_opts.schedtype'] == "manual":
        if sla := form_data.get('extra_opts.selectedSLA', None):
            LOG.debug(f"Adding SLA to deployment request {sla}")
            template['topology_template']['policies'] = [{
                "deploy_on_specific_site": {
                    "type": "tosca.policies.indigo.SlaPlacement",
                    "properties": {
                        "sla_id": sla
                    }
                }
            }]
        else:
            flash.flash(
                request,
                ("danger", "SLA does not exist.")
            )

    inputs = {k: v for (k, v) in form_data.items()
              if not k.startswith("extra_opts.")}
    LOG.debug("Parameters:", inputs)

    template = yaml.dump(template,
                         default_flow_style=False,
                         sort_keys=False)
    LOG.debug(f"Final template generated {template}")

    # FIXME(aloga): Make this async
    cli = await orchestrator.get_client(
        CONF.orchestrator.url,
        request
    )

    cli.deployments.create(template, parameters=inputs)
    return web.HTTPFound("/deployments")
