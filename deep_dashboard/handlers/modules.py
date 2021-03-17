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
import aiohttp_jinja2

from deep_dashboard import config
from deep_dashboard import deep_oc

CONF = config.CONF

routes = web.RouteTableDef()


@routes.get('/modules', name="modules")
@aiohttp_jinja2.template('modules/index.html')
async def index(request):
    request.context["templates"] = request.app.modules
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
