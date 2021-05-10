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

import pathlib

from oslo_config import cfg
from oslo_log import log

orchestrator_opts = [
    cfg.URIOpt(
        'url',
        required=True,
        schemes=["http", "https"],
        help="""
DEEP orchestrator endpoint.
"""),
    cfg.StrOpt(
        'tosca-dir',
        default="./tosca-templates",
        help="""
Path to the directory where to store all the orchestrator TOSCA templates.
"""),
    cfg.StrOpt(
        'deep-templates-dir',
        default="deep-oc",
        help="""
Directory relative to $tosca_dir where the DEEP TOSCA templates are stored.
"""),
    cfg.StrOpt(
        'tosca-parameters-dir',
        default="./",
        help="""
Path to the directory where the additional TOSCA parameters are stored.
"""),
    cfg.URIOpt(
        'tosca-repo',
        default="https://github.com/indigo-dc/tosca-templates/",
        schemes=["http", "https", "git"],
        help="""
URL of the DEEP tosca templates repository.
"""),
    cfg.DictOpt(
        "common-toscas",
        default={
            "default": "deep-oc-marathon-webdav.yml",
            "minimal": "deep-oc-marathon.yml",
        },
    ),
]

opts = [
    cfg.StrOpt(
        "github-secret",
        secret=True,
        help="""
GitHub secret to trigger reloading of modules
"""),
    cfg.URIOpt(
        'deep-oc-modules',
        default=("https://raw.githubusercontent.com/deephdc/deep-oc/"
                 "master/MODULES.yml"),
        schemes=["http", "https"],
        help="""
URL of the DEEP OC modules YAML file.
"""),
    cfg.StrOpt(
        "static-path",
        default=(pathlib.Path(__file__).parent / "static").as_posix(),
        help="""
Path where the static files are stored.
"""),
]

cli_opts = [
    cfg.StrOpt('listen-ip',
               help="""
IP address on which the DEEP Dashboard will listen.

The DEEP dashboard service will listen on this IP address.
"""),
    cfg.PortOpt('listen-port',
                help="""
Port on which the DEEP Dashboard will liste,.

The DEEP dashboard service will listen on this port.
"""),
    cfg.StrOpt('listen-path',
               help="""
Path to the UNIX socket where the DEEP dashboard will listen.
"""),
]

CONF = cfg.CONF
CONF.register_cli_opts(cli_opts)
CONF.register_opts(opts)
CONF.register_opts(orchestrator_opts, group="orchestrator")


def parse_args(args, default_config_files=None):
    cfg.CONF(args,
             project='deep_dashboard',
             default_config_files=default_config_files)


def prepare_logging():
    log.register_options(CONF)
    log.set_defaults(default_log_levels=log.get_default_log_levels())


def configure(argv, default_config_files=None):
    prepare_logging()
    parse_args(argv, default_config_files=default_config_files)
    log.setup(CONF, "deep_dashboard")
