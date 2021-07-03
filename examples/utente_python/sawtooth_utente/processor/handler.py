# Copyright 2016-2018 Intel Corporation
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

import logging
import hashlib

from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError

from sawtooth_sdk.protobuf.cessione_credito_pb2 import Utente


LOGGER = logging.getLogger(__name__)


class UtenteTransactionHandler(TransactionHandler):
    # Disable invalid-overridden-method. The sawtooth-sdk expects these to be
    # properties.
    # pylint: disable=invalid-overridden-method
    @property
    def family_name(self):
        return 'utente'

    @property
    def family_versions(self):
        return ['1.0']

    UTENTE_NAMESPACE = hashlib.sha512('utente'.encode("utf-8")).hexdigest()[0:6]

    @property
    def namespaces(self):
        return [self.UTENTE_NAMESPACE]
    
    def apply(self, transaction, context):
        
        self._context = context
        # header = transaction.header
        # signer = header.signer_public_key

        nuovo_utente = Utente()
        try:
            nuovo_utente.ParseFromString(transaction.payload)
        except Exception:
            raise InvalidTransaction("Invalid payload serialization")

        self.set_utente_state(nuovo_utente)

    def get_utente_address(self, public_key):
        return self.UTENTE_NAMESPACE + hashlib.sha512(str(public_key).encode("utf-8")).hexdigest()[0:64]
    
    def get_utente_state(self, public_key):
        address = self.get_utente_address(public_key)
        utente = Utente()
        try:
            utente.ParseFromString(self._context.get_state([address])[0].data)
            return utente
        except IndexError:
            raise InvalidTransaction('No data at address: {}'.format(address))
    
    def set_utente_state(self, utente):
        # TODO: aggiungere try catch 
        address = self.get_utente_address(utente.public_key)
        addresses = self._context.set_state({address: utente.SerializeToString()})
        if not addresses:
            raise InternalError('State error')
