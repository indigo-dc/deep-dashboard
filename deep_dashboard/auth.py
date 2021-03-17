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

import aioauth_client
from aiohttp import web
from aiohttp import web_urldispatcher
import aiohttp_security.abc
import aiohttp_session
from oslo_config import cfg

from deep_dashboard import config

iam_opts = [
    cfg.StrOpt(
        'client-id',
        help="""
IAM Client ID to use for authentication
"""),
    cfg.StrOpt(
        'client-secret',
        secret=True,
        help="""
IAM Client Secret corresponding to the configured Client ID
"""),
    cfg.URIOpt(
        'base-url',
        schemes=["http", "https"],
        help="""
IAM Base URL.
"""),
    cfg.URIOpt(
        'authorize-url',
        default="$iam.base_url/authorize",
        schemes=["http", "https"],
        help="""
IAM Authorization endpoint URL.
"""),
    cfg.URIOpt(
        'access-token-url',
        default="$iam.base_url/token",
        schemes=["http", "https"],
        help="""
IAM Access Token endpoint URL.
"""),
    cfg.URIOpt(
        'user-info-url',
        default="$iam.base_url/userinfo",
        schemes=["http", "https"],
        help="""
IAM User Info endpoint URL.
"""),
    cfg.URIOpt(
        'redirect-uri',
        default="http://127.0.0.1:8080/login/iam",
        schemes=["http", "https"],
        help="""
Redirection endpoint. Configure this with your public IP, as configured in
the IAM Client configuration.
"""),
]

CONF = config.CONF
CONF.register_opts(iam_opts, group="iam")


class IamAuthorizationPolicy(aiohttp_security.abc.AbstractAuthorizationPolicy):
    def __init__(self, user_groups=None):
        super().__init__()
        self.user_groups = user_groups

    async def authorized_userid(self, identity):
        """Retrieve authorized user id.
        Return the user_id of the user identified by the identity
        or 'None' if no user exists related to the identity.
        """
        if self.user_groups:
            # Do something with groups FIXME
            pass
        return identity

    async def permits(self, identity, permission, context=None):
        """Check user permissions.
        Return True if the identity is allowed the permission
        in the current context, else return False.
        """
        return True


def get_iam_client():
    client_id = CONF.iam.client_id
    client_secret = CONF.iam.client_secret

    base_url = CONF.iam.base_url
    authorize_url = CONF.iam.authorize_url
    access_token_url = CONF.iam.access_token_url
    user_info_url = CONF.iam.user_info_url
    redirect_url = CONF.iam.redirect_uri

    iam = aioauth_client.OAuth2Client(
        client_id=client_id,
        client_secret=client_secret,
        base_url=base_url,
        authorize_url=authorize_url,
        access_token_url=access_token_url,
        redirect_uri=redirect_url,
        scope='openid email profile offline_access',
    )
    iam.user_info_url = user_info_url

    return iam


@web.middleware
async def auth_middleware(request, handler):
    is_authenticated = not await aiohttp_security.is_anonymous(request)
    session = await aiohttp_session.get_session(request)

    request.context = {
        "current_user": {
            "authenticated": is_authenticated,
        }
    }
    route_name = request.match_info.route.name
    if isinstance(request.match_info.route, web_urldispatcher.ResourceRoute):
        if route_name == "static":
            pass
        elif route_name == "login":
            pass
        elif not is_authenticated and (route_name != "home"):
            session["next"] = str(request.rel_url)
            return web.HTTPFound("/")

    if is_authenticated:
        request.context["current_user"]["username"] = session["username"]
        request.context["current_user"]["gravatar"] = session["gravatar"]
    response = await handler(request)
    return response
