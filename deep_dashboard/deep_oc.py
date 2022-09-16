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

import asyncio
import collections
import json
import os.path
import pathlib
import shutil
import subprocess

import aiohttp
import git
import git.exc
from oslo_concurrency import lockutils

from deep_dashboard import config
from deep_dashboard import log
from deep_dashboard import tosca

CONF = config.CONF
LOG = log.getLogger("deep_dashboard.deep_oc")


@lockutils.synchronized("catalog.lock", external=True)
def download_deep_catalog():
    """Get and load modules in the DEEP marketplace as TOSCA files."""

    # FIXME(aloga): when using multiple backends this funcion is executed in
    # all of them on startup. This does not cause errors (it will try to
    # update git git repo, but this will delay startup time. We need to use
    # fasteners to get the lock and return if the repo is already locked.
    LOG.debug(f"Downloading DEEP OC from {CONF.deep_oc_repo}")

    deep_oc_dir = pathlib.Path(CONF.deep_oc_dir)

    try:
        git.Repo(deep_oc_dir)
    except git.exc.NoSuchPathError:
        deep_oc_dir.mkdir(parents=True)
        git.Repo.clone_from(CONF.deep_oc_repo, deep_oc_dir)
    except (git.exc.InvalidGitRepositoryError, git.exc.GitCommandError):
        if CONF.purge_deep_oc_directory:
            shutil.rmtree(deep_oc_dir)
            deep_oc_dir.mkdir(parents=True)
            git.Repo.clone_from(CONF.deep_oc_repo, deep_oc_dir)
        else:
            raise

    g = git.cmd.Git(deep_oc_dir)
    g.pull()
    # NOTE(aloga): we cannot rely on gitpython to update the submodules, as
    # it fails to update them if the branch is other than main
    subprocess.run(["git", "submodule", "init"],
                   cwd=deep_oc_dir)
    subprocess.run(["git", "submodule", "update", "--recursive"],
                   cwd=deep_oc_dir)


@lockutils.synchronized("catalog.lock", external=True)
async def load_modules_metadata():
    modules_meta = collections.OrderedDict()

    LOG.debug(f"Loading DEEP OC from {CONF.deep_oc_repo}")
    deep_oc_dir = pathlib.Path(CONF.deep_oc_dir)
    repo = git.Repo(deep_oc_dir)

    for sm in repo.submodules:
        meta_file = deep_oc_dir / deep_oc_dir / sm.name / "metadata.json"
        try:
            with open(meta_file, "r") as f:
                metadata = f.read()
            metadata = json.loads(metadata)
        except FileNotFoundError:
            LOG.error(f"Cannot find metadata file {meta_file}")
        except json.JSONDecodeError:
            LOG.error(f"Cannot decode JSON file {meta_file}")
            continue
        metadata["module_url"] = sm.url
        name = sm.name.lower().replace('_', '-')

        modules_meta[name] = metadata
        modules_meta[name]["original_name"] = sm.name
        modules_meta[name]["deepaas_name"] = sm.name.replace("DEEP-OC-", "", 1)

    modules_meta["external"] = {
        'title': 'Run your own module',
        'summary': 'Use your own external container hosted '
                   'in Dockerhub',
        'tosca': [],
        'keywords': [],
        'docker_tags': ['latest'],
        'sources': {
            'docker_registry_repo': ''
        },
        'module_url': "",
    }

    return modules_meta


async def get_dockerhub_tags(session, image):
    url = f'https://registry.hub.docker.com/v2/repositories/{image}/tags'
    try:
        async with session.get(url, raise_for_status=True) as r:
            aux = await r.json()
    except aiohttp.client_exceptions.ClientError:
        LOG.error(f"Cannot get tags from DockerHub {image}")
        return []
    return [i['name'] for i in aux["results"]]


@lockutils.synchronized("tosca-templates.lock", external=True)
@lockutils.synchronized("catalog.lock", external=True)
async def map_modules_to_tosca(modules_metadata, tosca_templates):
    session = aiohttp.ClientSession()

    tosca_dir = pathlib.Path(CONF.orchestrator.tosca_dir)
    common_toscas = CONF.orchestrator.common_toscas

    for module_name, metadata in modules_metadata.items():
        toscas = collections.OrderedDict()
        # Find tosca names from metadata
        for t in metadata['tosca']:
            tosca_name = os.path.basename(t['url'])
            if tosca_name in common_toscas.values():
                continue
            try:
                if tosca_name not in tosca_templates:
                    tosca_file = tosca_dir / tosca_name
                    async with session.get(t["url"],
                                           raise_for_status=True) as r:
                        with open(tosca_file, "w") as f:
                            f.write(await r.data())
                toscas[t['title'].lower()] = tosca_name
            except Exception as e:
                LOG.warning(f'Error processing TOSCA in module '
                            f'{module_name} from {t["url"]}: {e}')

        # Add always common TOSCAs
        for k, v in common_toscas.items():
            toscas[k] = v

        # Add Docker tags
        if metadata['sources']['docker_registry_repo']:
            dockerhub_tags = await get_dockerhub_tags(
                session,
                metadata['sources']['docker_registry_repo']
            )
            metadata.setdefault('docker_tags', [])
            if metadata['docker_tags']:
                # Check that the tags provided by the user are indeed
                # present in DockerHub
                aux = set(metadata['docker_tags'])
                aux = aux.intersection(set(dockerhub_tags))
                aux = sorted(list(aux))
                metadata['docker_tags'] = aux
            else:
                metadata['docker_tags'] = dockerhub_tags

        metadata["tosca_templates"] = toscas

    await session.close()
    return modules_metadata


async def download_catalog(app):
    loop = asyncio.get_event_loop()
    app.tosca_downloader = loop.run_in_executor(app.pool,
                                                tosca.download_tosca_templates)
    app.catalog_downloader = loop.run_in_executor(app.pool,
                                                  download_deep_catalog)


async def load_catalog(app):
    await app.scheduler.spawn(_load_catalog(app))


async def _load_catalog(app):
    async def inner():
        while True:
            if not all([app.tosca_downloader.done(),
                        app.catalog_downloader.done()]):
                await asyncio.sleep(5)
            else:
                break

        tosca_templates, modules_meta = await asyncio.gather(
            asyncio.create_task(tosca.load_tosca_templates()),
            asyncio.create_task(load_modules_metadata())
        )
        modules_meta = await map_modules_to_tosca(modules_meta,
                                                  tosca_templates)
        app.modules = modules_meta
        app.tosca_templates = tosca_templates
        await app.cache.modules.set_values(modules_meta)
        await app.cache.tosca_templates.set_values(tosca_templates)
    await inner()
