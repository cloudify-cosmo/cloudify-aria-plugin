########
# Copyright (c) 2017 GigaSpaces Technologies Ltd. All rights reserved
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
#    * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    * See the License for the specific language governing permissions and
#    * limitations under the License.

import os

import aria
from cloudify import ctx
from cloudify.decorators import operation

from .constants import (CSAR_PATH_PROPERTY, INPUTS_PROPERTY, PLUGINS_PROPERTY)
from .environment import Environment
from .utils import (generate_csar_source, extract_csar, install_plugins,
                    store_service_template, create_service, cleanup_files)
from . import executor


@operation
def create(**_):
    env = Environment(ctx)
    # extract csar
    csar_path = ctx.node.properties[CSAR_PATH_PROPERTY]
    csar_source = generate_csar_source(csar_path, env.blueprint_dir)
    csar = extract_csar(csar_source, ctx.logger)
    files_to_remove = [csar.destination]
    csar_plugins_dir = os.path.join(csar.destination, 'plugins')

    # install plugins
    plugins_to_install = ctx.node.properties[PLUGINS_PROPERTY]
    ctx.logger.info('Installing required plugins for ARIA: {0}...'
                    .format(plugins_to_install))
    install_plugins(csar_plugins_dir, plugins_to_install,
                    env.plugin_manager, ctx.logger)
    ctx.logger.info('Successfully installed required plugins')

    # store service template
    aria.install_aria_extensions()
    service_template_path = os.path.join(csar.destination,
                                         csar.entry_definitions)
    ctx.logger.info('Storing service template {0}...'
                    .format(env.service_template_name))
    store_service_template(env.core, service_template_path,
                           env.service_template_name)
    ctx.logger.info('Successfully stored service template')

    # create service
    inputs = ctx.node.properties[INPUTS_PROPERTY]
    ctx.logger.info('Creating service {0} with inputs {1}...'
                    .format(env.service_template_name, inputs))
    create_service(env.core, env.service_template_name, inputs)
    ctx.logger.info('Successfully created service')

    cleanup_files(files_to_remove)


@operation
def start(**_):
    env = Environment(ctx)
    executor.execute(env, 'install')
    ctx.instance.runtime_properties.update(
        (k, o.value) for k, o in env.service.outputs.items())


@operation
def stop(**_):
    env = Environment(ctx)
    executor.execute(env, 'uninstall')


@operation
def delete(**_):
    env = Environment(ctx)

    # delete the service
    service_id = env.service.id
    ctx.logger.info('Deleting service {0}...'
                    .format(env.service_template_name))
    env.core.delete_service(service_id)
    ctx.logger.info('Successfully deleted service {0}...'
                    .format(env.service_template_name))

    # delete the service template
    service_template_id = env.model_storage.service_template.get_by_name(
        env.service_template_name).id
    ctx.logger.info('Deleting service template {0}...'
                    .format(env.service_template_name))
    env.core.delete_service_template(service_template_id)
    ctx.logger.info('Successfully deleted service template {0}...'
                    .format(env.service_template_name))

    # if there are no more stored service templates,
    # then remove the aria working dir
    service_templates = env.model_storage.service_template.list()
    if len(service_templates) == 0:
        env.rm_working_dir()
