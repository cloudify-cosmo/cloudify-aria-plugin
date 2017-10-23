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

import pytest

import aria
from aria.storage.filesystem_rapi import FileSystemResourceAPI
from aria.storage.sql_mapi import SQLAlchemyModelAPI
from aria_plugin import environment, constants, utils, exceptions


class TestEnvironment(object):

    @pytest.fixture
    def env(self, mocker):
        self._workdir = 'workdir_path'
        mocker.patch('aria_plugin.utils.silent_create',
                     return_value=self._workdir)
        mocked_ctx = mocker.MagicMock()
        return environment.Environment(mocked_ctx)

    def test_ctx_logger(self, env):
        env.ctx_logger.info('some info')
        env._ctx.logger.info.assert_called_once_with('some info')

    def test_workdir(self, env):
        assert env.workdir == self._workdir

    def test_blueprint_dir(self, env, mocker):
        env._ctx.tenant_name = 'tenant_name'
        env._ctx.blueprint.id = 'blueprint_id'

        assert env.blueprint_dir == os.path.join(env.BLUEPRINTS_DIR,
                                                 'tenant_name',
                                                 'blueprint_id')

    def test_model_storage_dir(self, env):
        assert env.model_storage_dir == os.path.join(self._workdir, 'models')

    def test_model_resource_storage_dir(self, env):
        assert env.resource_storage_dir == os.path.join(
            self._workdir, 'resources')

    def test_model_plugins_dir(self, env):
        assert env.aria_plugins_dir == os.path.join(self._workdir, 'plugins')

    def test_model_storage(self, env, mocker):
        mocker.patch('aria.application_model_storage')

        model_storage = env.model_storage

        aria.application_model_storage.assert_called_once_with(
            api=SQLAlchemyModelAPI,
            initiator_kwargs={
                'base_dir': os.path.join(self._workdir, 'models')
            }
        )

        # Check that the same model storage is being returned
        assert model_storage == env.model_storage

    def test_resource_storage(self, env, mocker):
        mocker.patch('aria.application_resource_storage')

        resource_storage = env.resource_storage

        aria.application_resource_storage.assert_called_once_with(
            api=FileSystemResourceAPI,
            api_kwargs={'directory': os.path.join(self._workdir, 'resources')}
        )

        # Check that the same resource storage is being returned
        assert resource_storage == env.resource_storage

    def test_core(self, env, mocker):
        env._model_storage = 'model_storage'
        env._resource_storage = 'resource_storage'
        env._plugin_manager = 'plugin_manager'

        core = env.core

        assert core.model_storage == 'model_storage'
        assert core.resource_storage == 'resource_storage'
        assert core.plugin_manager == 'plugin_manager'

        # Check that the same core is being returned
        assert core == env.core

    def test_plugin_manager(self, env):
        env._model_storage = 'model_storage'

        plugin_manager = env.plugin_manager

        assert plugin_manager._model == 'model_storage'
        assert plugin_manager._plugins_dir == os.path.join(
            self._workdir, 'plugins')

        # Check that the same plugin manager is being returned
        assert plugin_manager == env.plugin_manager

    def test_mk_working_dir(self, env):
        env._ctx.tenant_name = 'tenant_name'

        expected_workdir_path = os.path.join(
            env.CLOUDIFY_PLUGINS_DIR, 'aria-{0}'.format('tenant_name'))

        workdir = env._mk_working_dir()

        utils.silent_create.assert_called_with(expected_workdir_path)
        assert workdir == self._workdir

    def test_rm_working_dir(self, env, mocker):
        mocker.patch('aria_plugin.utils.silent_remove')
        env.rm_working_dir()

        utils.silent_remove.assert_called_once_with(self._workdir)
        assert env.workdir is None

    def test_service_template_name(self, env):
        env._ctx.tenant_name = 'tenant_name'
        env._ctx.deployment.id = 'deployment_id'

        assert constants.SERVICE_TEMPLATE_NAME_FORMAT.format(
            tenant='tenant_name', dep_id='deployment_id'
        ) == env.service_template_name

    def test_service(self, env, mocker):
        env._ctx.tenant_name = 'tenant_name'
        env._ctx.deployment.id = 'deployment_id'
        service_template_name = constants.SERVICE_TEMPLATE_NAME_FORMAT.format(
            tenant='tenant_name', dep_id='deployment_id'
        )

        mocker.patch.object(env, '_model_storage')
        mocker.patch.object(
            env._model_storage.service, 'list', return_value=['service1'])

        assert env.service == 'service1'

        env.model_storage.service.list.assert_called_once_with(
            filters={'service_template_name': service_template_name}
        )

        mocker.patch.object(
            env._model_storage.service, 'list', return_value=[])

        with pytest.raises(exceptions.MissingServiceException):
            env.service
