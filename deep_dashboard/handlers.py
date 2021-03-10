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
import aiohttp_security
import aiohttp_session
import aiohttp_session.cookie_storage
import orpy.exceptions

from deep_dashboard import config
from deep_dashboard import utils
from deep_dashboard import orchestrator

routes = web.RouteTableDef()


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
        config.CONF.orchestrator_url,
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


# FIXME(aloga): this is not correct, we should not use a GET but a DELETE
@routes.get("/deployments/{uuid}/delete", name="deployment.delete")
async def delete_deployment(request):
    context = await _get_context(request)

    if not context["current_user"].get("authenticated"):
        session = await aiohttp_session.get_session(request)
        session["next"] = "deployments"
        return web.HTTPFound("/")

    uuid = request.match_info['uuid']

    cli = await orchestrator.get_client(
        config.CONF.orchestrator_url,
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
