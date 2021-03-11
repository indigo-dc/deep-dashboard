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
import yaml

import aiohttp

from deep_dashboard import config
from deep_dashboard import tosca

CONF = config.CONF


async def get_deep_oc_modules_metadata():
    """Get and load modules in the DEEP marketplace as TOSCA files."""

    session = aiohttp.ClientSession()
    async with session.get(CONF.deep_oc_modules) as r:
        r.raise_for_status()
        content = await r.text()

    yml_list = yaml.safe_load(content)
    if not yml_list:
        raise Exception(f'No modules found in {CONF.deep_oc_modules}')
    modules_list = [m['module'] for m in list(yml_list)]

    modules_meta = collections.OrderedDict()
    for m_url in modules_list:
        m_name = os.path.basename(m_url).lower().replace('_', '-')

        if m_name in modules_meta:
            raise Exception('Two modules are sharing the same name: '
                            f'{m_name}')

        # Get module description from metadata.json
        m_url = m_url.replace(
            'https://github.com/',
            'https://raw.githubusercontent.com/'
        )
        meta_url = f'{m_url}/master/metadata.json'
        async with session.get(meta_url,
                               headers={"accept": "application/json"}) as r:
            # Unfortunately we cannot use r.json() here as GitHub does not
            # send a proper content-type for the file, as it is being sent
            # as plaintext
            metadata = await r.read()
        metadata = json.loads(metadata)

        metadata["module_url"] = m_url

        modules_meta[m_name] = metadata

    await session.close()

    modules_meta["external"] = {
        'title': 'Run your own module',
        'summary': 'Use your own external container hosted '
                   'in Dockerhub',
        'tosca': [],
        'docker_tags': ['latest'],
        'sources': {
            'docker_registry_repo': ''
        },
        'module_url': "",
    }

    return modules_meta


async def get_dockerhub_tags(session, image):
    url = f'https://registry.hub.docker.com/v1/repositories/{image}/tags'
    async with session.get(url) as r:
        aux = await r.json()
    return [i['name'] for i in aux]


async def map_modules_to_tosca(modules_metadata, tosca_templates):

    session = aiohttp.ClientSession()

    modules = collections.OrderedDict()

    tosca_dir = pathlib.Path(CONF.tosca_dir)
    common_toscas = CONF.common_toscas

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
                    async with session.get(t["url"]) as r:
                        with open(tosca_file, "w") as f:
                            f.write(await r.data())
                toscas[t['title'].lower()] = tosca_name
            except Exception as e:
                print(f'Error processing TOSCA in module {module_name} from '
                      f'{t["url"]}: {e}')

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
                # Check that the tags provided by the user are indeed present
                # in DockerHub
                aux = set(metadata['docker_tags'])
                aux = aux.intersection(set(dockerhub_tags))
                aux = sorted(list(aux))
                metadata['docker_tags'] = aux
            else:
                metadata['docker_tags'] = dockerhub_tags

        # Build the module dict
        modules[module_name] = {
            'toscas': toscas,
            'url': metadata["module_url"],
            'title': metadata['title'],
            'sources': metadata['sources'],
            'docker_tags': metadata['docker_tags'],
            'description': metadata['summary'],
            'metadata': {
                # FIXME(aloga): allow users to change this
                'icon': "https://cdn4.iconfinder.com/data/icons/mosaicon-04/"
                        "512/websettings-512.png",
                'display_name': metadata['title']
            }
        }
    await session.close()
    return modules


async def load_deep_oc(app):
    tosca_templates = await tosca.load_tosca_templates()
    modules_meta = await get_deep_oc_modules_metadata()
    modules = await map_modules_to_tosca(modules_meta, tosca_templates)
    app.modules = modules


async def load_deep_oc_as_task(app):
    return asyncio.create_task(load_deep_oc(app))