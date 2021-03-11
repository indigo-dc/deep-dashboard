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

import hashlib
import hmac

from aiohttp import web
import aiohttp_session_flash as flash
import aiohttp_jinja2
import aiohttp_security
import aiohttp_session
import aiohttp_session.cookie_storage
import orpy.exceptions
import requests

from deep_dashboard import config
from deep_dashboard import deep_oc
from deep_dashboard import utils
from deep_dashboard import orchestrator

routes = web.RouteTableDef()

CONF = config.CONF


@routes.get('/', name="home")
@aiohttp_jinja2.template('home.html')
async def hello(request):
    is_authenticated = not await aiohttp_security.is_anonymous(request)
    session = await aiohttp_session.get_session(request)

    next_url = session.get("next")
    if next_url and is_authenticated:
        next_url = request.app.router.named_resources().get(next_url)
        del session["next"]
        if next_url:
            return web.HTTPFound(next_url.url_for())

    context = {
        "current_user": {
            "authenticated": is_authenticated,
        },
        "templates": {}
    }
    if is_authenticated:
        context["current_user"]["username"] = session["username"]
        context["current_user"]["gravatar"] = session["gravatar"]
        context["templates"] = request.app.modules
    return context


@routes.get('/logout', name='logout')
async def logout(request):
    redirect_response = web.HTTPFound('/')
    await aiohttp_security.forget(request, redirect_response)
    return redirect_response


@routes.get('/login/iam', name="login")
async def iam_login(request):
    client = request.app.iam_client

    # Check if is not redirect from provider
    if client.shared_key not in request.query:
        # Redirect client to provider
        return web.HTTPTemporaryRedirect(
            client.get_authorize_url(access_type='offline')
        )

    _, meta = await client.get_access_token(request.query)
    _, userinfo = await client.user_info()
    session = await aiohttp_session.get_session(request)
    session["userinfo"] = userinfo
    session["username"] = userinfo["name"]
    session["gravatar"] = utils.avatar(userinfo["email"], 26)

    user_id = userinfo["sub"]

    redirect_response = web.HTTPFound("/")
    await aiohttp_security.remember(request, redirect_response, user_id)
    return redirect_response


async def _get_context(request):
    is_authenticated = not await aiohttp_security.is_anonymous(request)

    session = await aiohttp_session.get_session(request)
    context = {
        "current_user": {
            "authenticated": is_authenticated,
        },
    }
    if is_authenticated:
        context["current_user"]["username"] = session["username"]
        context["current_user"]["gravatar"] = session["gravatar"]
    return context


@routes.get("/deployments", name="deployments")
@aiohttp_jinja2.template('deployments.html')
async def get_deployments(request):
    context = await _get_context(request)
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
@aiohttp_jinja2.template('deptemplate.html')
async def get_deployment_template(request):
    context = await _get_context(request)
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
    context = await _get_context(request)

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
@aiohttp_jinja2.template('deployment_summary.html')
async def show_deployment_history(request):
    context = await _get_context(request)

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


@routes.post("/reload", name="reload")
async def reload(request):
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
#    global toscaTemplates, toscaInfo, modules  # FIXME

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

    print('Reloading modules and TOSCA templates ...')
    await deep_oc.load_deep_oc_as_task(request.app)

    return web.Response(status=201)
