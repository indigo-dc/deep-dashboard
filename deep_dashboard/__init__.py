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

from aiohttp import web
import aiohttp_jinja2
import aiohttp_security
import aiohttp_session
import aiohttp_session.cookie_storage
from cryptography import fernet
import jinja2

from deep_dashboard import auth
from deep_dashboard import handlers


def init(args):

    app = web.Application(debug=True)

    tpl_path = pathlib.Path(__file__).parent / "templates"
    aiohttp_jinja2.setup(
        app,
        loader=jinja2.FileSystemLoader(tpl_path)
    )

    static_path = pathlib.Path(__file__).parent / "static"
    handlers.routes.static('/static', static_path, name="static")

    app.add_routes(handlers.routes)

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
