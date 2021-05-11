# -*- coding: utf-8 -*-

# Copyright 2021 Spanish National Research Council (CSIC)
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
import shutil
import yaml

import git
import git.cmd
import git.exc
from oslo_concurrency import lockutils

from deep_dashboard import config
from deep_dashboard import log

CONF = config.CONF
LOG = log.getLogger("deep_dashboard.tosca")

tosca_info_defaults = {
    "valid": False,
    "description": "TOSCA Template",
    "metadata": {
        "icon": "https://cdn4.iconfinder.com/data/icons/"
        "mosaicon-04/512/websettings-512.png"
    },
    "enable_config_form": False,
    "inputs": {},
    "tabs": {},
}


@lockutils.synchronized("tosca-templates.lock", external=True)
async def load_tosca_templates():
    """Load DEEP-OC related TOSCA templates from configured repository."""

    LOG.debug("Loading TOSCA templates")

    tosca_dir = pathlib.Path(CONF.orchestrator.tosca_dir)

    try:
        git.Repo(tosca_dir)
    except git.exc.NoSuchPathError:
        tosca_dir.mkdir(parents=True)
        git.Repo.clone_from(CONF.orchestrator.tosca_repo, tosca_dir)
    except (git.exc.InvalidGitRepositoryError, git.exc.GitCommandError):
        if CONF.orchestrator.purge_tosca_directory:
            shutil.rmtree(tosca_dir)
            tosca_dir.mkdir(parents=True)
            git.Repo.clone_from(CONF.orchestrator.tosca_repo, tosca_dir)
        else:
            raise

    g = git.cmd.Git(tosca_dir)
    g.pull()

    toscas = {}
    deep_tpl_dir = tosca_dir / CONF.orchestrator.deep_templates_dir
    for tosca_file in deep_tpl_dir.rglob("*y*ml"):
        with open(tosca_file, "r") as tpl:
            tpl = yaml.full_load(tpl)

        if not tpl:
            continue

        tosca_info = tosca_info_defaults.copy()
        if 'topology_template' not in tpl:
            continue

        tosca_info["valid"] = True

        # Update meta with sub dict
        meta = tpl.pop("metadata", {})
        tosca_info["metadata"].update(meta)

        # Update description if it exists
        tosca_info["description"] = tpl.get("description",
                                            tosca_info["description"])

        # Update deployment type
        topology = tpl.pop("topology_template", {})
        node_templates = topology.get("node_templates", {})
        tosca_info['deployment_type'] = get_deployment_type(node_templates)

        # Update inputs
        inputs = topology.pop("inputs", {})
        tosca_info["inputs"] = inputs

        # Add parameters code here
        if CONF.orchestrator.tosca_parameters_dir:
            params_dir = pathlib.Path(CONF.orchestrator.tosca_parameters_dir)
            tosca_name = tosca_file.stem

            for f in params_dir.glob(f"{tosca_name}.parameters.y*ml"):
                with open(f) as f:
                    params = yaml.full_load(f)
                if not params:
                    continue

                tosca_info['enable_config_form'] = True
                tosca_info['inputs'].update(params.get("inputs", {}))
                tosca_info['tabs'].update(params.get("tabs", {}))

        toscas[tosca_file.name] = tosca_info

    return toscas


def get_deployment_type(nodes):
    deployment_type = ""
    type_map = {
        "tosca.nodes.indigo.Compute": "CLOUD",
        "tosca.nodes.indigo.Container.Application.Docker.Marathon": "MARATHON",
        "tosca.nodes.indigo.Container.Application.Docker.Chronos": "CHRONOS",
        "tosca.nodes.indigo.Qcg.Job": "QCG",
    }
    for (j, u) in nodes.items():
        for (k, v) in u.items():
            if k == "type":
                deployment_type = type_map.get(v, "")
            if deployment_type:
                return deployment_type
    return deployment_type
