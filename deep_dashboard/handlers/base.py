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
import aiohttp_jinja2
import aiohttp_security
import aiohttp_session
import aiohttp_session.cookie_storage

from deep_dashboard import auth
from deep_dashboard import sla
from deep_dashboard import utils

routes = web.RouteTableDef()


@routes.get('/', name="home")
@aiohttp_jinja2.template('home.html')
async def home(request):
    session = await aiohttp_session.get_session(request)

    next_url = session.get("next")
    if next_url and request.context["current_user"]["authenticated"]:
        del session["next"]
        return web.HTTPFound(next_url)

    request.context["breadcrumbs"] = [
        ("Home", True, "/"),
    ]

    return request.context


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

    try:
        meta, userinfo = await auth.get_token_userinfo(request)
    except web.HTTPInternalServerError as e:
        raise e
    except Exception:
        return web.HTTPTemporaryRedirect(
            client.get_authorize_url(access_type='offline')
        )

    session = await aiohttp_session.get_session(request)
    session["userinfo"] = userinfo
    session["username"] = userinfo["name"]
    session["gravatar"] = utils.avatar(userinfo["email"], 26)
    session['organisation_name'] = userinfo['organisation_name']

    user_id = userinfo["sub"]

    redirect_response = web.HTTPFound("/")
    await aiohttp_security.remember(request, redirect_response, user_id)

    request.app.sla_loader = await sla.load_slas_as_task(request)

    return redirect_response
