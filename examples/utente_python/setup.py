# Copyright 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------

from __future__ import print_function

import os
import subprocess

from setuptools import setup, find_packages

conf_dir = "/etc/sawtooth"

data_files = [
    (conf_dir, ['packaging/utente.toml.example'])
]

if os.path.exists("/etc/default"):
    data_files.append(
        ('/etc/default', ['packaging/systemd/sawtooth-utente-tp-python']))

if os.path.exists("/lib/systemd/system"):
    data_files.append(('/lib/systemd/system',
                       ['packaging/systemd/sawtooth-utente-tp-python']))

setup(
    name='sawtooth-utente',
    version=subprocess.check_output(
        ['../../bin/get_version']).decode('utf-8').strip(),
    description='Transactor Family per utenti di cessione del credito',
    author='Giacomo Giuliani, Mattia Luzi',
    url='https://github.com/mattialuzi/sawtooth-sdk-python',
    packages=find_packages(),
    install_requires=[
        'aiohttp',
        'colorlog',
        'protobuf',
        'sawtooth-sdk',
        'PyYAML',
    ],
    data_files=data_files,
    entry_points={
        'console_scripts': [
            # 'xo = sawtooth_xo.xo_cli:main_wrapper',
            'utente-tp-python = sawtooth_utente.processor.main:main',
        ]
    })
