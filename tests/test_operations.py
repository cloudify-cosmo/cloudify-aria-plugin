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

from aria_plugin import constants
from aria_plugin import operations, exceptions

CSAR_PATH = 'path'
PLUGINS = ['plugin1']
INPUTS = {'key1': 'value1'}
CSAR_DESTINATION = 'csar_destination'
ENTRY_DEFINITIONS = 'service_template.yaml'
BLUEPRINT_DIR = 'blueprint_dir'
PLUGIN_MANAGER = 'plugin_manager'
SERVICE_TEMPLATE_NAME = 'name'


@pytest.fixture
def mocked_env(mocker):
    mock_env = mocker.MagicMock()
    mock_env.blueprint_dir = BLUEPRINT_DIR
    mock_env.plugin_manager = PLUGIN_MANAGER
    mock_env.service_template_name = SERVICE_TEMPLATE_NAME
    mocker.patch('aria_plugin.operations.Environment', return_value=mock_env)
    return mock_env


@pytest.fixture
def mocked_ctx(mocker):
    mock_ctx = mocker.patch('aria_plugin.operations.ctx')
    mock_ctx.node.properties = {constants.CSAR_PATH_PROPERTY: CSAR_PATH,
                                constants.PLUGINS_PROPERTY: PLUGINS,
                                constants.INPUTS_PROPERTY: INPUTS}
    return mock_ctx


@pytest.fixture
def mocked_csar(mocker):
    mock_csar = mocker.patch('aria.cli.csar._CSARReader')
    mock_csar.destination = CSAR_DESTINATION
    mock_csar.entry_definitions = ENTRY_DEFINITIONS
    return mock_csar


def test_create_no_exception(mocker, mocked_env, mocked_csar, mocked_ctx):

    mocked_extract_csar = mocker.patch(
        'aria_plugin.operations.extract_csar', return_value=mocked_csar)
    mocked_install_plugins = mocker.patch(
        'aria_plugin.operations.install_plugins')
    mocked_cleanup_files = mocker.patch(
        'aria_plugin.operations.cleanup_files')
    mocked_aria_module = mocker.patch('aria_plugin.operations.aria')
    operations.create()

    mocked_extract_csar.assert_called_once_with(
        os.path.join(BLUEPRINT_DIR, CSAR_PATH), mocked_ctx.logger)

    mocked_install_plugins.assert_called_with(
        os.path.join(CSAR_DESTINATION, 'plugins'),
        PLUGINS,
        PLUGIN_MANAGER,
        mocked_ctx.logger
    )

    mocked_aria_module.install_aria_extensions.assert_called_once()

    mocked_env.core.create_service_template.assert_called_once_with(
        service_template_path=os.path.join(
            CSAR_DESTINATION, ENTRY_DEFINITIONS),
        service_template_dir=os.path.dirname(os.path.join(
            CSAR_DESTINATION, ENTRY_DEFINITIONS)),
        service_template_name=SERVICE_TEMPLATE_NAME
    )

    mocked_env.core.create_service.assert_called_once_with(
        mocker.ANY, INPUTS)

    mocked_cleanup_files.assert_called_once()


@pytest.mark.usefixtures('mocked_env', 'mocked_csar')
def test_create_raises_exception(mocker, mocked_ctx):
    mocker.patch('aria_plugin.operations.cleanup_files')
    mocker.patch('aria_plugin.operations.aria')
    mocker.patch('aria_plugin.operations.install_plugins',
                 side_effect=exceptions.PluginsAlreadyExistException)

    # We expect that this should not raise an exception, even if
    # install_plugins raises PluginsAlreadyExistException
    operations.create()
    mocked_ctx.logger.debug.assert_called_once()


def test_start(mocker, mocked_env, mocked_ctx):

    mocked_executor_module = mocker.patch('aria_plugin.operations.executor')

    mocked_outputs = mocker.MagicMock()
    mocked_output = mocker.MagicMock()
    mocked_output.value = 'value'
    mocked_outputs.items.return_value = [('output_name', mocked_output)]
    mocked_env.service.outputs = mocked_outputs
    mocked_ctx.instance.runtime_properties = {}

    operations.start()

    mocked_executor_module.execute.assert_called_once_with(mocked_env,
                                                           'install')
    assert mocked_ctx.instance.runtime_properties == {'output_name': 'value'}


def test_stop(mocker, mocked_env):
    mocked_executor_module = mocker.patch('aria_plugin.operations.executor')
    operations.stop()
    mocked_executor_module.execute.assert_called_once_with(mocked_env,
                                                           'uninstall')


class TestDelete(object):

    @pytest.fixture(autouse=True)
    def simple_ctx_mocking(self, mocker):
        mocker.patch('aria_plugin.operations.ctx')

    def test_delete_models(self, mocker, mocked_env):
        mocked_env.service.id = 'service_id'
        mocked_service_template = mocker.MagicMock()
        mocked_service_template.id = 'template_id'
        mocked_env.model_storage.service_template.get_by_name.return_value = \
            mocked_service_template

        operations.delete()

        mocked_env.core.delete_service.assert_called_once_with('service_id')
        mocked_env.core.delete_service_template.assert_called_once_with(
            'template_id')

    def test_delete_remove_working_dir(self, mocked_env):
        # we are expected to delete the working dir iff there are no more
        # service templates left in the storage
        mocked_env.model_storage.service_template.list.return_value = []

        operations.delete()

        mocked_env.rm_working_dir.assert_called_once()

    def test_delete_dont_remove_working_dir(self, mocked_env):
        mocked_env.model_storage.service_template.list.return_value = \
            ['service_template']

        operations.delete()

        mocked_env.rm_working_dir.assert_not_called()
