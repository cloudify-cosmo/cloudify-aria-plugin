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
from aria.core import Core
from aria.orchestrator.plugin import PluginManager
from aria.storage.sql_mapi import SQLAlchemyModelAPI
from aria.storage.filesystem_rapi import FileSystemResourceAPI

from . import constants, utils
from .exceptions import MissingServiceException


class Environment(object):

    MANAGER_RESOURCES_DIR = '/opt/manager/resources'
    BLUEPRINTS_DIR = os.path.join(MANAGER_RESOURCES_DIR, 'blueprints')
    CLOUDIFY_PLUGINS_DIR = os.path.join(MANAGER_RESOURCES_DIR, 'plugins')

    def __init__(self, ctx):
        self._ctx = ctx
        self._workdir = self._mk_working_dir()
        utils.silent_create(self.aria_plugins_dir)
        utils.silent_create(self.model_storage_dir)
        utils.silent_create(self.resource_storage_dir)

        self._to_clean = []

        # Initialized lazily:
        self._model_storage = None
        self._resource_storage = None
        self._plugin_manager = None
        self._core = None

    @property
    def ctx_logger(self):
        return self._ctx.logger

    @property
    def workdir(self):
        return self._workdir

    @property
    def blueprint_dir(self):
        return os.path.join(self.BLUEPRINTS_DIR,
                            self._ctx.tenant_name,
                            self._ctx.blueprint.id)

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
        dir_name = 'aria-{tenant_name}'.format(
            tenant_name=self._ctx.tenant_name)
        abs_path = os.path.join(self.CLOUDIFY_PLUGINS_DIR, dir_name)

        workdir_path = utils.silent_create(abs_path)

        return workdir_path

    def rm_working_dir(self):
        utils.silent_remove(self.workdir)
        self._workdir = None

    @property
    def service_template_name(self):
        return constants.SERVICE_TEMPLATE_NAME_FORMAT.format(
            tenant=self._ctx.tenant_name, dep_id=self._ctx.deployment.id)

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
