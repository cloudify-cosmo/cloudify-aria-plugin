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

import time

import pytest

from aria.orchestrator import execution_preparer

from aria_plugin import executor
from aria_plugin.exceptions import AriaWorkflowError


@pytest.fixture
def mocked_env(mocker):
    mocked_env = mocker.MagicMock()
    mocked_env.model_storage = 'model_storage'
    mocked_env.resource_storage = 'resource_storage'
    mocked_env.plugin_manager = 'plugin_manager'
    mocked_env.service.id = 'service_id'
    mocked_env.ctx_logger = mocker.MagicMock()

    return mocked_env


def _patch_runner(mocker, success=True):
    mock_execution = mocker.MagicMock()
    mock_execution.SUCCEEDED = 'pass'
    mock_execution.status = 'pass' if success else 'fail'

    mock_ctx = mocker.MagicMock()
    mock_ctx.execution = mock_execution

    mock_preparer = mocker.MagicMock()
    mock_preparer.prepare = lambda: mock_ctx

    mocker.patch('aria.orchestrator.execution_preparer.ExecutionPreparer',
                 return_value=mock_preparer)

    return mock_preparer, mock_ctx


def test_successful_execute(mocked_env, mocker):
    mocker.patch('aria.cli.logger.ModelLogIterator', return_value=[])
    mock_runner, mock_ctx = _patch_runner(mocker)
    mock_execute = \
        mocker.patch('aria.orchestrator.workflows.core.engine.Engine.execute')

    executor.execute(mocked_env, 'workflow_name')

    execution_preparer.ExecutionPreparer.assert_called_once_with(
        'model_storage',
        'resource_storage',
        'plugin_manager',
        mocked_env.service,
        'workflow_name',
    )

    mock_execute.assert_called_once_with(ctx=mock_ctx)


def test_failed_execution(mocker, mocked_env):
    mocker.patch('aria.cli.logger.ModelLogIterator', return_value=[])
    mock_runner, mock_ctx = _patch_runner(mocker, success=False)
    mock_execute = \
        mocker.patch('aria.orchestrator.workflows.core.engine.Engine.execute')

    with pytest.raises(AriaWorkflowError):
        executor.execute(mocked_env, 'workflow_name')

    execution_preparer.ExecutionPreparer.assert_called_once_with(
        'model_storage',
        'resource_storage',
        'plugin_manager',
        mocked_env.service,
        'workflow_name',
    )

    mock_execute.assert_called_once_with(ctx=mock_ctx)


def test_execution_logging(mocker, mocked_env):
    _patch_runner(mocker)
    # The workflow runner executes a thread which does all the heavy lifting,
    # while the main process continues with printing the logs. While the
    # thread is alive, the logs are printed out, thus we need to give the
    # thread some time to run in order to test the logs.
    mocker.patch('aria.orchestrator.workflows.core.engine.Engine.execute',
                 side_effect=lambda *a, **kw: time.sleep(1))

    mocked_log = mocker.MagicMock()
    mocked_log.level = 'INFO'
    mocked_log.traceback = 'traceback'
    mocker.patch('aria.cli.logger.ModelLogIterator',
                 return_value=iter([mocked_log]))

    executor.execute(mocked_env, 'workflow_name')

    mocked_env.ctx_logger.info.assert_any_call(mocked_log)
    mocked_env.ctx_logger.info.assert_called_with('traceback')
    assert mocked_env.ctx_logger.info.call_count == 2
