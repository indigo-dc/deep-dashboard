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

import asyncio
import base64
import pathlib

from aiohttp import web
import aiohttp_jinja2
import aiohttp_security
import aiohttp_session
import aiohttp_session.cookie_storage
import aiohttp_session.memcached_storage
import aiohttp_session_flash
import aiomcache
from cryptography import fernet
import jinja2
from oslo_concurrency import lockutils

from deep_dashboard import auth
from deep_dashboard import config
from deep_dashboard import deep_oc
from deep_dashboard.handlers import base
from deep_dashboard.handlers import deployments
from deep_dashboard.handlers import modules
from deep_dashboard import log
from deep_dashboard import version

__version__ = version.__version__

CONF = config.CONF
LOG = log.LOG


@web.middleware
async def error_middleware(request, handler):
    try:
        response = await handler(request)
        if response.status != 404:
            return response
        message = response.message
    except web.HTTPServerError as e:
        LOG.exception(e)
        message = "Internal server error. "
    except web.HTTPException as e:
        message = f"Error {e.status_code}: {e.reason}"
    aiohttp_session_flash.flash(request, ("danger", message))
    response = web.HTTPFound("/")
    return response


@web.middleware
async def meta_middleware(request, handler):
    request.context = {
        "meta": {
            "version": __version__,
        }
    }
    response = await handler(request)
    return response


async def init(args):
    LOG.info("Starting DEEP Dashboard...")

    runtime_dir = pathlib.Path(CONF.runtime_dir)

    runtime_dir.mkdir(parents=True, exist_ok=True)

    app = web.Application(debug=True)
    app.runtime_dir = runtime_dir
    lockutils.set_defaults(runtime_dir)

    tpl_path = pathlib.Path(__file__).parent / "templates"
    aiohttp_jinja2.setup(
        app,
        context_processors=[aiohttp_session_flash.context_processor],
        loader=jinja2.FileSystemLoader(tpl_path)
    )

    app.iam_client = auth.get_iam_client()

    base.routes.static('/static', CONF.static_path, name="static")
    app.add_routes(base.routes)
    app.add_routes(deployments.routes)
    app.add_routes(modules.routes)

    if CONF.cache.memcached_ip:
        loop = asyncio.get_event_loop()
        mc = aiomcache.Client(CONF.cache.memcached_ip,
                              CONF.cache.memcached_port,
                              loop=loop)
        sess_storage = aiohttp_session.memcached_storage.MemcachedStorage(
            mc,
            cookie_name='DEEPDASHBOARD'
        )
    else:
        LOG.warning("Not using memcached, unexpected behaviour when running "
                    "more than one worker!")

        # secret_key must be 32 url-safe base64-encoded bytes
        fernet_key = fernet.Fernet.generate_key()

        secret_key = base64.urlsafe_b64decode(fernet_key)

        sess_storage = aiohttp_session.cookie_storage.EncryptedCookieStorage(
            secret_key,
            cookie_name='DEEPDASHBOARD'
        )
    aiohttp_session.setup(app, sess_storage)

    policy = aiohttp_security.SessionIdentityPolicy()
    aiohttp_security.setup(app, policy, auth.IamAuthorizationPolicy())

    app.middlewares.append(meta_middleware)
    app.middlewares.append(aiohttp_session_flash.middleware)
    app.middlewares.append(auth.auth_middleware)
    app.middlewares.append(error_middleware)
    app.modules = {}

    app.on_startup.append(deep_oc.load_deep_oc_as_task)

    return app
