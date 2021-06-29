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

from sawtooth_sdk.protobuf.cessione_credito_pb2 import RichiestaAccreditamentoPayload
from sawtooth_sdk.protobuf.cessione_credito_pb2 import RichiestaAccreditamentoState


LOGGER = logging.getLogger(__name__)


class RichiestaAccreditamentoTransactionHandler(TransactionHandler):
    # Disable invalid-overridden-method. The sawtooth-sdk expects these to be
    # properties.
    # pylint: disable=invalid-overridden-method
    @property
    def family_name(self):
        return 'richiesta_accreditamento'

    @property
    def family_versions(self):
        return ['1.0']

    RICHIESTA_ACCREDITAMENTO_NAMESPACE = hashlib.sha512('richiesta_accreditamento'.encode("utf-8")).hexdigest()[0:6]

    @property
    def namespaces(self):
        return [self.RICHIESTA_ACCREDITAMENTO_NAMESPACE]
    
    def apply(self, transaction, context):
        
        self._context = context
        header = transaction.header
        # signer = header.signer_public_key

        payload = RichiestaAccreditamentoPayload()
        try:
            payload.ParseFromString(transaction.payload)
        except Exception:
            raise InvalidTransaction("Invalid payload serialization")

        # TODO: controllare identità e permessi per le varie azioni 
        
        # Nuova richiesta
        if payload.payload_type == RichiestaAccreditamentoPayload.NUOVA_RICHIESTA:
            action_payload = payload.nuova_richiesta
            if action_payload:
                self.set_richiesta_accreditamento_state(action_payload)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(RichiestaAccreditamentoPayload.Name(payload.payload_type)))

        # aggiornamento stato proposta    
        elif payload.payload_type == RichiestaAccreditamentoPayload.AGGIORNAMENTO_STATO:
            action_payload = payload.aggiornamento_stato
            if action_payload:
                richiesta = self.get_richiesta_accreditamento_state(action_payload.id_richiesta)
                richiesta.stato = action_payload.nuovo_stato
                richiesta.note = action_payload.note
                self.set_richiesta_accreditamento_state(richiesta)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(RichiestaAccreditamentoPayload.Name(payload.payload_type)))
        
        # aggiornamento documenti proposta
        elif payload.payload_type == RichiestaAccreditamentoPayload.AGGIORNAMENTO_DOCUMENTI:
            action_payload = payload.aggiornamento_documenti
            if action_payload:
                richiesta = self.get_richiesta_accreditamento_state(action_payload.id_richiesta)
                for doc in action_payload.documenti_aggiornati:
                    entry = richiesta.documenti[doc.id]
                    entry.Clear()
                    entry.CopyFrom(doc)
                self.set_richiesta_accreditamento_state(richiesta)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(RichiestaAccreditamentoPayload.Name(payload.payload_type)))

        else:
            raise InvalidTransaction("Unhandled payload type")
        

    def get_richiesta_accreditamento_address(self, id):
        return self.RICHIESTA_ACCREDITAMENTO_NAMESPACE + hashlib.sha512(str(id).encode("utf-8")).hexdigest()[0:64]
    
    def get_richiesta_accreditamento_state(self, id):
        address = self.get_richiesta_accreditamento_address(id)
        richiesta = RichiestaAccreditamentoState()
        try:
            richiesta.ParseFromString(self._context.get_state([address])[0].data)
            return richiesta
        except IndexError:
            raise InvalidTransaction('No data at address: {}'.format(address))
        except Exception as e:
            raise InternalError('Failed to load state data') from e
    
    def set_richiesta_accreditamento_state(self, richiesta):
        # TODO: aggiungere try catch 
        address = self.get_richiesta_accreditamento_address(richiesta.id)
        addresses = self._context.set_state({address: richiesta.SerializeToString()})
        if not addresses:
            raise InternalError('State error')
