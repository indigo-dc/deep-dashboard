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

from deep_dashboard import version

opts = [
    cfg.StrOpt(
        "github-secret",
        secret=True,
        help="""
GitHub secret to trigger reloading of modules
"""),
    cfg.URIOpt(
        'deep-oc-modules',
        default=None,
        schemes=["http", "https"],
        deprecated_for_removal=True,
        help="""
URL of the DEEP OC modules YAML file. This option is marked for removal.
"""),
    cfg.URIOpt(
        'deep-oc-repo',
        default="https://github.com/deephdc/deep-oc/",
        schemes=["http", "https"],
        help="""
URL of the DEEP OC repository.
"""),
    cfg.StrOpt(
        'deep-oc-dir',
        default="$runtime_dir/deep-oc",
        help="""
Path to the directory where to store all the DEEP OC modules.
"""),
    cfg.BoolOpt(
        "purge-deep-oc-directory",
        default=False,
        help="""
Remove $deep_oc_dir in case it is not a valid Git repository.
"""),
    cfg.StrOpt(
        "runtime-dir",
        default="/var/run/deep-dashboard",
        help="""
Define the DEEP dashboard base runtime directory
"""),
    cfg.StrOpt(
        "static-path",
        default=(pathlib.Path(__file__).parent / "static").as_posix(),
        help="""
Path where the static files are stored.
"""),
]


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
        default="$runtime_dir/tosca-templates",
        help="""
Path to the directory where to store all the orchestrator TOSCA templates.
"""),
    cfg.StrOpt(
        'deep-templates-dir',
        default="deep-oc",
        help="""
Directory relative to $tosca_dir where the DEEP TOSCA templates are stored.
"""),
    cfg.BoolOpt(
        "purge-tosca-directory",
        default=False,
        help="""
Remove $tosca_dir in case it is not a valid Git repository.
"""),
    cfg.StrOpt(
        'tosca-parameters-dir',
        default="$runtime_dir/tosca-parameters-dir",
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

cache_opts = [
    cfg.StrOpt(
        "memcached-ip",
        help="""
IP of the memcached server to use.

If not set, we will not use memcached at all, therefore the DEEP dashboard
will not behave as expected when using several workers.
"""),
    cfg.PortOpt(
        "memcached-port",
        default=11211,
        help="""
Port of the memcached server to use.
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
CONF.register_opts(cache_opts, group="cache")


def parse_args(args, default_config_files=None):
    cfg.CONF(args,
             project='deep_dashboard',
             version=version.__version__,
             default_config_files=default_config_files)


def prepare_logging():
    log.register_options(CONF)
    log.set_defaults(default_log_levels=log.get_default_log_levels())


def configure(argv, default_config_files=None):
    prepare_logging()
    parse_args(argv, default_config_files=default_config_files)
    log.setup(CONF, "deep_dashboard")
