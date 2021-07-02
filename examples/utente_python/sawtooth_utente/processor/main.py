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

import sys
import os
import argparse
import pkg_resources

from sawtooth_utente.processor.handler import UtenteTransactionHandler
from sawtooth_utente.processor.config.utente import UtenteConfig
from sawtooth_utente.processor.config.utente import \
    load_default_utente_config
from sawtooth_utente.processor.config.utente import \
    load_toml_utente_config
from sawtooth_utente.processor.config.utente import \
    merge_utente_config

from sawtooth_sdk.processor.core import TransactionProcessor
from sawtooth_sdk.processor.log import init_console_logging
from sawtooth_sdk.processor.log import log_configuration
from sawtooth_sdk.processor.config import get_log_config
from sawtooth_sdk.processor.config import get_log_dir
from sawtooth_sdk.processor.config import get_config_dir


DISTRIBUTION_NAME = 'sawtooth-utente'


def parse_args(args):
    parser = argparse.ArgumentParser(
        formatter_class=argparse.RawTextHelpFormatter)

    parser.add_argument(
        '-C', '--connect',
        help='Endpoint for the validator connection')

    parser.add_argument('-v', '--verbose',
                        action='count',
                        default=0,
                        help='Increase output sent to stderr')

    try:
        version = pkg_resources.get_distribution(DISTRIBUTION_NAME).version
    except pkg_resources.DistributionNotFound:
        version = 'UNKNOWN'

    parser.add_argument(
        '-V', '--version',
        action='version',
        version=(DISTRIBUTION_NAME + ' (Hyperledger Sawtooth) version {}')
        .format(version),
        help='print version information')

    return parser.parse_args(args)


def load_utente_config(first_config):
    default_utente_config = \
        load_default_utente_config()
    conf_file = os.path.join(get_config_dir(), 'utente.toml')

    toml_config = load_toml_utente_config(conf_file)

    return merge_utente_config(
        configs=[first_config, toml_config, default_utente_config])


def create_utente_config(args):
    return UtenteConfig(connect=args.connect)


def main(args=None):
    if args is None:
        args = sys.argv[1:]
    opts = parse_args(args)
    processor = None
    try:
        arg_config = create_utente_config(opts)
        utente_config = load_utente_config(arg_config)
        processor = TransactionProcessor(url=utente_config.connect)
        log_config = get_log_config(filename="utente_log_config.toml")

        # If no toml, try loading yaml
        if log_config is None:
            log_config = get_log_config(filename="utente_log_config.yaml")

        if log_config is not None:
            log_configuration(log_config=log_config)
        else:
            log_dir = get_log_dir()
            # use the transaction processor zmq identity for filename
            log_configuration(
                log_dir=log_dir,
                name="utente-" + str(processor.zmq_id)[2:-1])

        init_console_logging(verbose_level=opts.verbose)

        handler = UtenteTransactionHandler()

        processor.add_handler(handler)
        processor.start()
    except KeyboardInterrupt:
        pass
    except Exception as e:  # pylint: disable=broad-except
        print("Error: {}".format(e))
    finally:
        if processor is not None:
            processor.stop()
