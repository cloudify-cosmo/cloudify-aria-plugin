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
from aria.orchestrator import exceptions as aria_exceptions
from aria.cli import csar

from aria_plugin import utils, exceptions


class TestInstallPlugins(object):

    @pytest.fixture(autouse=True)
    def mockup(self, mocker, tmpdir):
        self.workdir = tmpdir.strpath
        self.mock_plugin_name = 'plugin_to_install'
        mocker.spy(utils, 'install_plugins')
        mocker.spy(utils, '_log_unused_plugins')
        self.mocked_logger = mocker.MagicMock()
        self.mocked_plugin_manager = mocker.MagicMock()

    def test_install_plugin_without_exceptions(self, mocker):
        mocker.patch('aria_plugin.utils._prepare_plugins_for_installation',
                     return_value=[self.mock_plugin_name])
        mocker.patch('os.listdir', return_value=['plugin1', 'wagon.wgn'])

        utils.install_plugins(
            sources_dir=self.workdir,
            plugins_to_install=[self.mock_plugin_name],
            plugin_manager=self.mocked_plugin_manager,
            logger=self.mocked_logger
        )

        utils._prepare_plugins_for_installation.assert_called_once_with(
            self.workdir,
            [self.mock_plugin_name],
        )
        utils._log_unused_plugins.assert_called_once_with(
            self.mocked_logger,
            self.workdir,
            [self.mock_plugin_name],
        )
        self.mocked_plugin_manager.validate_plugin.assert_called_once_with(
            os.path.join(self.workdir, self.mock_plugin_name)
        )
        self.mocked_plugin_manager.install.assert_called_once_with(
            os.path.join(self.workdir, self.mock_plugin_name)
        )

        assert self.mocked_logger.debug.call_count == 2

    def test_install_existing_plugin(self, mocker):
        mocker.patch('aria_plugin.utils._prepare_plugins_for_installation',
                     return_value=[self.mock_plugin_name])

        self.mocked_plugin_manager.install.side_effect = \
            aria_exceptions.PluginAlreadyExistsError

        with pytest.raises(exceptions.PluginsAlreadyExistException):
            utils.install_plugins(
                sources_dir=self.workdir,
                plugins_to_install=[self.mock_plugin_name],
                plugin_manager=self.mocked_plugin_manager,
                logger=self.mocked_logger
            )

    def test_non_existing_plugins_dir(self):
        with pytest.raises(exceptions.MissingPluginsException):
            utils.install_plugins(
                sources_dir='non_existing_dir',
                plugins_to_install='[plugin_to_install]',
                plugin_manager='plugin_manager',
            )

    def test_prepare_plugins_for_installation(self, mocker):
        mocker.patch('os.listdir', return_value=['plugin1'])

        plugins_to_install = utils._prepare_plugins_for_installation(
            'mock_dir',
            ['plugin1']
        )
        assert plugins_to_install == set(['plugin1'])

        with pytest.raises(exceptions.MissingPluginsException):
            utils._prepare_plugins_for_installation('mock_dir', ['plugin2'])


def test_extract_csar(mocker):
    mocker.patch('aria.cli.csar.read')
    utils.extract_csar('mock_source', 'mock_logger')

    csar.read.assert_called_with(source='mock_source',
                                 logger='mock_logger',
                                 destination=mocker.ANY)


def test_generate_resource_path():
    local_resource = os.path.join('dir', 'some_path')
    assert local_resource == utils.generate_resource_path('some_path', 'dir')

    url_resource = 'http://some_resource'
    assert utils.generate_resource_path(url_resource, 'dir') == url_resource


def test_cleanup_files(tmpdir):

    def _touch_files(files):
        for f in files:
            f.write('content')

    # Create 2 top level files
    files = [tmpdir.join(f) for f in ('file1', 'file2')]
    _touch_files(files)
    files_path = [f.strpath for f in files]

    # Create a direcotry and create 2 additional files
    dir_ = tmpdir.mkdir("sub")
    dir_path = dir_.strpath
    sub_files = [dir_.join(f) for f in ('sub_file1', 'sub_file2')]
    _touch_files(sub_files)
    sub_files_paths = [f.strpath for f in sub_files]

    # assert all files were created
    assert all(os.path.exists(path) for path in files_path)
    assert all(os.path.exists(path) for path in sub_files_paths)

    # delete the dir and assert the two files inside the dir were deleted
    utils.cleanup_files([dir_path])

    assert not any(os.path.exists(path) for path in sub_files_paths)
    assert not os.path.exists(dir_path)

    assert all(os.path.exists(path) for path in files_path)

    # delete the 2 additional top level files
    utils.cleanup_files(files_path)
    assert not any(os.path.exists(path) for path in files_path)


def test_silent_remove(tmpdir):
    dir_to_remove = tmpdir.mkdir('subdir')
    subfile = dir_to_remove.join('subfile')
    file_to_remove = tmpdir.join('file_to_remove')
    non_existing_file = tmpdir.join('non_existing_file')

    file_to_remove.write('content')
    subfile.write('content')

    def assert_structure(exists=True):
        def _exists(statement):
            return statement if exists else not statement
        assert _exists(os.path.exists(str(file_to_remove)))
        assert _exists(os.path.exists(str(dir_to_remove)))
        assert _exists(os.path.exists(str(subfile)))
        assert not os.path.exists(str(non_existing_file))

    assert_structure()

    utils.silent_remove(dir_to_remove.strpath)
    utils.silent_remove(file_to_remove.strpath)
    utils.silent_remove(non_existing_file.strpath)

    assert_structure(exists=False)
