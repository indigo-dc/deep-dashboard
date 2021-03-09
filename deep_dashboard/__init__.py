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

import base64
import pathlib

from cryptography import fernet
from aiohttp import web
import aiohttp_jinja2
import aiohttp_security
import aiohttp_session
import aiohttp_session.cookie_storage
import jinja2

from deep_dashboard import auth
from deep_dashboard import utils

routes = web.RouteTableDef()


@routes.get('/', name="home")
@aiohttp_jinja2.template('home.html')
async def hello(request):
    is_authenticated = not await aiohttp_security.is_anonymous(request)
    session = await aiohttp_session.get_session(request)
    context = {
        "current_user": {
            "authenticated": is_authenticated,
        }
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
    client = auth.get_iam_client()

    # Check if is not redirect from provider
    if client.shared_key not in request.query:

        print("VAMOSSS A ", client.get_authorize_url(access_type='offline'))
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


def init(args):

    app = web.Application(debug=True)

    tpl_path = pathlib.Path(__file__).parent / "templates"
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(tpl_path)
    )

    static_path = pathlib.Path(__file__).parent / "static"
    routes.static('/static', static_path, name="static")

    app.add_routes(routes)

    # secret_key must be 32 url-safe base64-encoded bytes
    fernet_key = fernet.Fernet.generate_key()
    secret_key = base64.urlsafe_b64decode(fernet_key)

    storage = aiohttp_session.cookie_storage.EncryptedCookieStorage(
        secret_key,
        cookie_name='API_SESSION'
    )
    aiohttp_session.setup(app, storage)

    policy = aiohttp_security.SessionIdentityPolicy()
    aiohttp_security.setup(app, policy, auth.IamAuthorizationPolicy())

    return app
