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


from cloudify import ctx
from aria.orchestrator import workflow_runner
from aria.cli.logger import ModelLogIterator

from .environment import Environment


def execute(service, workflow_name, logger=ctx.logger):
    env = Environment()
    runner = workflow_runner.WorkflowRunner(
        env.model_storage, env.resource_storage, env.plugin_manager,
        service_id=service.id,
        workflow_name=workflow_name)

    # Since we want a live log feed, we need to execute the workflow
    # while simultaneously printing the logs into the CFY logger. This Thread
    # executes the workflow, while the main process thread writes the logs.
    thread = Thread(target=runner.execute)
    thread.daemon = True
    thread.start()

    log_iterator = ModelLogIterator(env.model_storage, runner.execution_id)

    while thread.is_alive():
        for log in log_iterator:
            getattr(logger, log.level.lower())(log)
        thread.join(1)
