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
import pickle
import subprocess
import sys
import tempfile
from threading import Thread


# currently ARIA doesn't support providing a custom file to execute via the
# process executor, thus process executor module itself gets executed. This
# raises an issue with packages missing __init__.py file at the root dir (
# e.g. packages with multi top level packages, such as ruamel.yaml). In
# python 2.7 these packages fail to import when installed in non-standard
# location (i.e. via --target or --prefix installation).

# This was fixed in the __init__.py in the root of aria_plugin, (thus this
# issue isn't raised when using the plugin). However, when executing a task
# via the process executor, a new subprocess starts, and in this subprocess
# patching is needed as well.

# The solution provided here replaces the ProcessExecutor with an executor
# which causes *this* file to load instead of the ARIA process.py one.
import aria_plugin                                              # noqa: F401

from aria.orchestrator import workflow_runner
from aria.orchestrator.workflows.executor import process
from aria.cli.logger import ModelLogIterator


class ARIAPluginExecutor(process.ProcessExecutor):
    def _execute(self, ctx):
        self._check_closed()

        # Temporary file used to pass arguments to the started subprocess
        file_descriptor, arguments_json_path = tempfile.mkstemp(
            prefix='executor-',
            suffix='.json'
        )
        os.close(file_descriptor)
        with open(arguments_json_path, 'wb') as f:
            f.write(pickle.dumps(self._create_arguments_dict(ctx)))

        env = self._construct_subprocess_env(task=ctx.task)
        # Asynchronously start the operation in a subprocess
        proc = subprocess.Popen(
            [
                sys.executable,
                os.path.expanduser(os.path.expandvars(__file__)),
                os.path.expanduser(os.path.expandvars(arguments_json_path))
            ],
            env=env)

        self._tasks[ctx.task.id] = process._Task(ctx=ctx, proc=proc)


def execute(env, workflow_name):
    runner = workflow_runner.WorkflowRunner(
        env.model_storage, env.resource_storage, env.plugin_manager,
        service_id=env.service.id,
        workflow_name=workflow_name,
        executor=ARIAPluginExecutor(env.plugin_manager, sys.path)
    )

    # Since we want a live log feed, we need to execute the workflow
    # while simultaneously printing the logs into the CFY logger. This Thread
    # executes the workflow, while the main process thread writes the logs.
    thread = Thread(target=runner.execute)
    thread.daemon = True
    thread.start()

    log_iterator = ModelLogIterator(env.model_storage, runner.execution_id)

    while thread.is_alive():
        for log in log_iterator:
            leveled_log = getattr(env.ctx_logger, log.level.lower())
            leveled_log(log)
            if log.traceback:
                leveled_log(log.traceback)
        thread.join(0.1)


if __name__ == '__main__':
    process._main()
