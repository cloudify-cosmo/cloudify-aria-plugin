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

import aria
from aria.core import Core
from aria.orchestrator.plugin import PluginManager
from aria.storage.sql_mapi import SQLAlchemyModelAPI
from aria.storage.filesystem_rapi import FileSystemResourceAPI
from cloudify import ctx

from . import constants
from .exceptions import MissingServiceException


class Environment(object):

    MANAGER_RESOURCES_DIR = '/opt/manager/resources'
    BLUEPRINTS_DIR = os.path.join(MANAGER_RESOURCES_DIR, 'blueprints')
    CLOUDIFY_PLUGINS_DIR = os.path.join(MANAGER_RESOURCES_DIR, 'plugins')

    def __init__(self):

        self._mk_working_dir()

        self._to_clean = []

        # Initialized lazily:
        self._model_storage = None
        self._resource_storage = None
        self._plugin_manager = None
        self._core = None

    @property
    def workdir(self):
        return self._workdir

    @property
    def blueprint_dir(self):
        return os.path.join(self.BLUEPRINTS_DIR,
                            ctx.tenant_name,
                            ctx.blueprint.id)

    @property
    def model_storage(self):
        if not self._model_storage:
            initiator_kwargs = {'base_dir': self.model_storage_dir}
            self._model_storage = aria.application_model_storage(
                api=SQLAlchemyModelAPI, initiator_kwargs=initiator_kwargs)
        return self._model_storage

    @property
    def resource_storage(self):
        if not self._resource_storage:
            api_kwargs = {'directory': self.resource_storage_dir}
            self._resource_storage = aria.application_resource_storage(
                api=FileSystemResourceAPI, api_kwargs=api_kwargs)
        return self._resource_storage

    @property
    def plugin_manager(self):
        if not self._plugin_manager:
            self._plugin_manager = PluginManager(
                model=self.model_storage, plugins_dir=self.aria_plugins_dir)
        return self._plugin_manager

    @property
    def core(self):
        if not self._core:
            self._core = Core(model_storage=self.model_storage,
                              resource_storage=self.resource_storage,
                              plugin_manager=self.plugin_manager)
        return self._core

    @property
    def aria_plugins_dir(self):
        return os.path.join(self.workdir, 'plugins')

    @property
    def model_storage_dir(self):
        return os.path.join(self.workdir, 'models')

    @property
    def resource_storage_dir(self):
        return os.path.join(self.workdir, 'resources')

    def _mk_working_dir(self):
        dir_name = 'aria-{tenant_name}'.format(tenant_name=ctx.tenant_name)
        abs_path = os.path.join(self.CLOUDIFY_PLUGINS_DIR, dir_name)

        self._workdir = _create_if_not_existing(abs_path)

        # create subdirectories
        _create_if_not_existing(self.aria_plugins_dir)
        _create_if_not_existing(self.model_storage_dir)
        _create_if_not_existing(self.resource_storage_dir)

    @property
    def service_template_name(self):
        return constants.SERVICE_TEMPLATE_NAME_FORMAT.format(
            tenant=ctx.tenant_name, dep_id=ctx.deployment.id)

    @property
    def service(self):
        services = self.model_storage.service.list(
            filters={'service_template_name': self.service_template_name})
        if services:
            return services[0]
        else:
            raise MissingServiceException(
                'No services exist for service template {0}'
                .format(self.service_template_name))


def _create_if_not_existing(path):
    try:
        os.makedirs(path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    return path
