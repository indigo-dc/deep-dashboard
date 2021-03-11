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

class Config(object):
    client_id = ""
    client_secret = ""

    base_url = "https://iam.deep-hybrid-datacloud.eu"
    authorize_url = base_url + '/authorize'
    access_token_url = base_url + '/token'
    user_info_url = base_url + '/userinfo'
    redirect_url = "http://127.0.0.1:8080/login/iam"

    orchestrator_url = "https://deep-paas.cloud.ba.infn.it/orchestrator"

    tosca_dir = "./tosca-templates"
    tosca_repo = "https://github.com/indigo-dc/tosca-templates/"
    tosca_parameters_dir = "./"

    deep_oc_modules = ("https://raw.githubusercontent.com/deephdc/deep-oc/"
                       "master/MODULES.yml")

    common_toscas = {
        "default": "deep-oc-marathon-webdav.yml",
        "minimal": "deep-oc-marathon.yml",
    }

    github_secret = ""


CONF = Config()
