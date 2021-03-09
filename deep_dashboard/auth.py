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
import aiohttp_security.abc

from deep_dashboard import config


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
    client_id = config.CONF.client_id
    client_secret = config.CONF.client_secret

    base_url = config.CONF.base_url
    authorize_url = base_url + '/authorize'
    access_token_url = base_url + '/token'
    user_info_url = base_url + '/userinfo'
    redirect_url = "http://127.0.0.1:8080/login/iam"

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
