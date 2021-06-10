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

import copy
import hashlib
import hmac

from aiohttp import web
import aiohttp_jinja2
import aiohttp_session_flash as flash
import markdown

from deep_dashboard import config
from deep_dashboard import deep_oc
from deep_dashboard import log

CONF = config.CONF
LOG = log.LOG

routes = web.RouteTableDef()


@routes.get('/modules', name="modules")
@aiohttp_jinja2.template('modules/index.html')
async def index(request):
    request.context["templates"] = request.app.modules
    request.context["breadcrumbs"] = [
        ("Home", False, "/"),
        ("Modules", True, "/modules"),  # FIXME(aloga): use url
    ]
    return request.context


@routes.post("/reload", name="reload")
async def reload_all_modules(request):
    """Load TOSCA templates and map them to modules

    This function is used to refresh the TOSCA templates and the mapping
    between modules and TOSCA templates.  A webhook is set up so that when any
    of the repos [1][2] is updated, Github will POST to this method to refresh
    the Dashboard. The webhook's secret has to be the same has GITHUB_SECRET in
    the conf so that we can validate that the payload comes indeed from Github
    and the webhook has to be configured to deliver an 'application/json'.

    [1] https://github.com/deephdc/deep-oc
    [2] https://github.com/indigo-dc/tosca-templates/tree/master/deep-oc
    [3] https://gist.github.com/categulario/deeb41c402c800d1f6e6
    """

    # Check request comes indeed from Github
    if CONF.github_secret:
        if 'X-Hub-Signature' not in request.headers:
            return web.Response(
                text='Refresh petitions must be signed from Github.',
                status=403
            )
        # FIXME(aloga): this does not work
        signature = hmac.new(
            CONF.github_secret,
            request.data,
            hashlib.sha1
        ).hexdigest()
        if not hmac.compare_digest(
            signature,
            request.headers['X-Hub-Signature'].split('=')[1]
        ):
            return web.Response(
                text='Failed to verify the signature!',
                status=403
            )

    LOG.info('Reloading modules and TOSCA templates ...')
    await deep_oc.load_deep_oc_as_task(request.app)

    return web.Response(status=201)


@routes.get("/modules/{module}/train", name="module.train")
@aiohttp_jinja2.template('modules/train.html')
async def configure_module_training(request):
    module = request.match_info["module"].lower()

    if module not in request.app.modules:
        flash.flash(
            request,
            ("danger", f"Module does not exist: {module}.")
        )
        return web.HTTPFound("/modules")

    request.context["selected_module"] = module
    module_meta = request.app.modules.get(module)

    selected_tosca = request.query.get(
        "selected_tosca",
        list(module_meta["tosca_templates"].keys())[0]
    )
    template_name = module_meta["tosca_templates"][selected_tosca]
    hardware_configuration = request.query.get("hardware_configuration",
                                               "CPU").lower()
    docker_tag = request.query.get("docker_tag",
                                   module_meta["docker_tags"][0]).lower()
    run_command = request.query.get("run_command",
                                    "DEEPaaS")

    general_configuration = {
        "tosca_templates": {
            "available": module_meta["tosca_templates"].keys(),
            "selected": selected_tosca,
        },
        "docker_tags": {
            "available": module_meta["docker_tags"],
            "selected": docker_tag,
        },
        "hardware_configuration": {
            "available": ["CPU", "GPU"],
            "selected": hardware_configuration,
        },
        "run_command": {
            "available": ["DEEPaaS", "JupyterLab", "Custom command"],
            "selected": run_command,
        },
    }

    tosca_template = module_meta["tosca_templates"].get(selected_tosca)
    if tosca_template is None:
        flash.flash(
            request,
            ("danger", f"TOSCA template does not exist: {tosca_template}.")
        )
        return web.HTTPFound("/modules")

    inputs = copy.deepcopy(
        request.app.tosca_templates[tosca_template]["inputs"]
    )
    inputs['docker_image'].setdefault(
        'default',
        request.app.modules[module]['sources']['docker_registry_repo'])

    docker_tags = request.app.modules[module]['docker_tags']
    if docker_tag not in docker_tags:
        docker_tag = docker_tags[0]

    if run_command == 'deepaas':
        inputs['run_command']['default'] = 'deepaas-run --listen-ip=0.0.0.0'
        if hardware_configuration == 'gpu':
            inputs['run_command']['default'] += ' --listen-port=$PORT0'
    elif run_command == 'jupyterlab':
        flash.flash(
            request,
            ("warning", 'Remember to set a Jupyter password.')
        )
        inputs['run_command']['default'] = (
            '/srv/.jupyter/run_jupyter.sh --allow-root'
        )
        if hardware_configuration == 'gpu':
            inputs['run_command']['default'] = (
                "jupyterPORT=$PORT2 " + inputs['run_command']['default']
            )

    if hardware_configuration == 'cpu':
        inputs['num_cpus']['default'] = 1
        inputs['num_gpus']['default'] = 0
        inputs['run_command']['default'] = (
            "monitorPORT=6006 " + inputs['run_command']['default']
        )
    elif hardware_configuration == 'gpu':
        inputs['num_cpus']['default'] = 1
        inputs['num_gpus']['default'] = 1
        inputs['run_command']['default'] = (
            "monitorPORT=$PORT1 " + inputs['run_command']['default']
        )

    # FIXME(aloga): improve conditions here
    if run_command == "custom command":
        inputs['run_command']['default'] = ''

    inputs['docker_image']['default'] += ':{}'.format(docker_tag)

    grouped = {
        "docker": {},
        "jupyter": {},
        "storage": {},
        "hardware": {},
        "other": {},
    }

    for k, v in inputs.items():
        if k.startswith("docker_"):
            grouped["docker"][k] = v
        elif k.startswith("jupyter_"):
            grouped["jupyter"][k] = v
        elif any([k.startswith("rclone_"),
                  k.startswith("onedata_"),
                  k.startswith("oneclient_"),
                  k == "app_in_out_base_dir"]):
            grouped["storage"][k] = v
        elif k in ["mem_size", "num_cpus", "num_gpus"]:
            grouped["hardware"][k] = v
        else:
            grouped["other"][k] = v

    template_meta = {
        "inputs": inputs,
        "grouped": grouped,
    }

    request.context["general_configuration"] = general_configuration
    request.context["template_meta"] = template_meta
    request.context["template_name"] = template_name
    request.context["slas"] = request.app.slas
    request.context["module_meta"] = module_meta
    request.context["breadcrumbs"] = [
        ("Home", False, "/"),
        ("Modules", False, "/modules"),  # FIXME(aloga): use url
        (module, False, f"/modules/{module}"),  # FIXME(aloga): use url
        ("train", True, f"/modules/{module}/train"),  # FIXME(aloga): use url
    ]

    return request.context


@routes.get("/modules/{module}", name="module")
@aiohttp_jinja2.template('modules/module.html')
async def module_info(request):
    module = request.match_info["module"].lower()

    if module not in request.app.modules:
        flash.flash(
            request,
            ("danger", f"Module does not exist: {module}.")
        )
        return web.HTTPFound("/modules")

    module_meta = request.app.modules.get(module)

    request.context["modulename"] = module
    request.context["module_meta"] = copy.deepcopy(module_meta)
    description = "\n".join(request.context["module_meta"]["description"])
    description = markdown.markdown(description)
    request.context["module_meta"]["description"] = description

    request.context["breadcrumbs"] = [
        ("Home", False, "/"),
        ("Modules", False, "/modules"),  # FIXME(aloga): use url
        (module, True, f"/modules/{module}"),  # FIXME(aloga): use url
    ]

    return request.context
