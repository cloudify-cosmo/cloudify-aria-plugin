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

from setuptools import setup

setup(

    name='cloudify-aria-plugin',
    author='cloudify',
    author_email='cosmo-admin@gigaspaces.com',

    version='1.0.0',
    description='Cloudify plugin for ARIA.',

    packages=['aria_plugin'],
    license='LICENSE',
    install_requires=[
        'apache-ariatosca[ssh]==0.1.1',
        'cloudify-plugins-common<=4.2',
        # Until wagon version is normalized, we hard-code the wagon version.
        'wagon==0.6.1',
        # Setuptools used by cloudify is fairly recent as opposed to ARIA.
        # The ARIA setuptools dependency should be updated in future releases.
        'setuptools>=36.5.0'
    ]
)
