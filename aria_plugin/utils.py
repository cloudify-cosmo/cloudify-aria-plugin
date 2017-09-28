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

import errno
import os
import shutil
import tempfile


from aria.cli import csar

from .constants import WAGON_EXTENSION
from .exceptions import MissingPluginsException


def extract_csar(csar_source, logger):
    csar_dest = tempfile.mkdtemp(prefix='tmp-csar-')
    return csar.read(source=csar_source, destination=csar_dest, logger=logger)


def generate_csar_source(csar_path, blueprint_dir):
    if '://' not in csar_path:
        # the csar_path property is relative to the blueprint's directory
        csar_path = os.path.join(blueprint_dir, csar_path)
    return csar_path


def store_service_template(core, service_template_path,
                           service_template_name):
    core.create_service_template(
        service_template_path,
        service_template_dir=os.path.dirname(service_template_path),
        service_template_name=service_template_name)
    return service_template_name


def create_service(core, service_template_name, inputs):
    service_template = core.model_storage.service_template.get_by_name(
        service_template_name)
    core.create_service(service_template.id, inputs)


def install_plugins(sources_dir, plugins_to_install, plugin_manager):
    prepared_plugins = _prepare_plugins_for_installation(
        sources_dir, plugins_to_install)
    for plugin_to_install in prepared_plugins:
        plugin_path = os.path.join(sources_dir, plugin_to_install)
        plugin_manager.validate_plugin(plugin_path)
        plugin_manager.install(plugin_path)


def log_unused_plugins(logger, sources_dir, installed_plugins):
    for file_ in os.listdir(sources_dir):
        if file_ not in installed_plugins:
            if file_.endswith(WAGON_EXTENSION):
                logger.debug('Unused plugin {plugin} in the csar '
                             'plugins directory'.format(plugin=file_))
            else:
                logger.debug('Non-plugin file {file} in the csar plugins '
                             'directory'.format(file=file_))


def cleanup_files(files_to_remove):
    for path in files_to_remove:
        _silent_remove(path)


def _prepare_plugins_for_installation(sources_dir, plugins_to_install):
    plugins = set(os.listdir(sources_dir))
    plugins_to_install = set(plugins_to_install)
    missing_plugins = plugins_to_install - plugins

    if missing_plugins:
        raise MissingPluginsException('Requested plugins {0} is not in the'
                                      ' csar `plugins` directory'
                                      .format(', '.join(missing_plugins)))
    return plugins_to_install


def _silent_remove(path):
    try:
        if os.path.isfile(path):
            os.remove(path)
        elif os.path.isdir(path):
            shutil.rmtree(path)
    except OSError as e:
        if e.errno != errno.ENOENT:
            raise
