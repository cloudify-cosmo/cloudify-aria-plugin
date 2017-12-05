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

from threading import Thread

from aria.orchestrator import execution_preparer
from aria.orchestrator.workflows.core import engine
from aria.orchestrator.workflows.executor import process
from aria.cli import logger

from .exceptions import AriaWorkflowError


def execute(env, workflow_name):

    ctx = execution_preparer.ExecutionPreparer(
        env.model_storage,
        env.resource_storage,
        env.plugin_manager,
        env.service,
        workflow_name
    ).prepare()
    eng = engine.Engine(
            process.ProcessExecutor(env.plugin_manager, strict_loading=False)
    )

    # Since we want a live log feed, we need to execute the workflow
    # while simultaneously printing the logs into the CFY logger. This Thread
    # executes the workflow, while the main process thread writes the logs.
    thread = Thread(target=eng.execute, kwargs=dict(ctx=ctx))
    thread.start()

    log_iterator = logger.ModelLogIterator(env.model_storage, ctx.execution.id)

    while thread.is_alive():
        for log in log_iterator:
            leveled_log = getattr(env.ctx_logger, log.level.lower())
            leveled_log(log)
            if log.traceback:
                leveled_log(log.traceback)
        thread.join(0.1)

    aria_execution = ctx.execution
    if aria_execution.status != aria_execution.SUCCEEDED:
        raise AriaWorkflowError(
            'ARIA workflow {aria_execution.workflow_name} was not successful\n'
            'status: {aria_execution.status}\n'
            'error message: {aria_execution.error}'
            .format(aria_execution=aria_execution))
