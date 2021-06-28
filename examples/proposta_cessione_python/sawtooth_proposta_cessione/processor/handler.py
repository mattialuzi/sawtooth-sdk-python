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

# from sawtooth_xo.processor.xo_payload import XoPayload
# from sawtooth_xo.processor.xo_state import Game
# from sawtooth_xo.processor.xo_state import XoState
# from sawtooth_xo.processor.xo_state import XO_NAMESPACE

from sawtooth_sdk.processor.handler import TransactionHandler
from sawtooth_sdk.processor.exceptions import InvalidTransaction
from sawtooth_sdk.processor.exceptions import InternalError

from sawtooth_sdk.protobuf.cessione_credito_pb2 import PropostaCessionePayload
from sawtooth_sdk.protobuf.cessione_credito_pb2 import PropostaCessioneState


LOGGER = logging.getLogger(__name__)


class PropostaCessioneTransactionHandler(TransactionHandler):
    # Disable invalid-overridden-method. The sawtooth-sdk expects these to be
    # properties.
    # pylint: disable=invalid-overridden-method
    @property
    def family_name(self):
        return 'proposta_cessione'

    @property
    def family_versions(self):
        return ['1.0']

    PROPOSTA_CESSIONE_NAMESPACE = hashlib.sha512('proposta_cessione'.encode("utf-8")).hexdigest()[0:6]

    @property
    def namespaces(self):
        return [self.PROPOSTA_CESSIONE_NAMESPACE]
    
    def apply(self, transaction, context):
        
        self._context = context
        header = transaction.header
        # signer = header.signer_public_key

        payload = PropostaCessionePayload()
        try:
            payload.ParseFromString(transaction.payload)
        except Exception:
            raise InvalidTransaction("Invalid payload serialization")

        # TODO: controllare identità e permessi per le varie azioni 
        
        # Nuova proposta
        if payload.payload_type == PropostaCessionePayload.NUOVA_PROPOSTA:
            action_payload = payload.nuova_proposta
            if action_payload:
                self.set_proposta_cessione_state(action_payload)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(PropostaCessionePayload.Name(payload.payload_type)))

        # aggiornamento stato proposta    
        elif payload.payload_type == PropostaCessionePayload.AGGIORNAMENTO_STATO:
            action_payload = payload.aggiornamento_stato
            if action_payload:
                proposta = self.get_proposta_cessione_state(action_payload.id_proposta)
                proposta.stato = action_payload.nuovo_stato
                proposta.note = action_payload.note
                self.set_proposta_cessione_state(proposta)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(PropostaCessionePayload.Name(payload.payload_type)))
        
        # aggiornamento offerte proposta
        elif payload.payload_type == PropostaCessionePayload.AGGIORNAMENTO_OFFERTE:
            action_payload = payload.aggiornamento_offerte
            if action_payload:
                proposta = self.get_proposta_cessione_state(action_payload.id_proposta)
                for offerta in action_payload.offerte_aggiornate:
                    entry = proposta.offerte[offerta.id]
                    entry.Clear()
                    entry.CopyFrom(offerta)
                self.set_proposta_cessione_state(proposta)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(PropostaCessionePayload.Name(payload.payload_type)))

        # aggiornamento documenti proposta
        elif payload.payload_type == PropostaCessionePayload.AGGIORNAMENTO_DOCUMENTI:
            action_payload = payload.aggiornamento_documenti
            if action_payload:
                proposta = self.get_proposta_cessione_state(action_payload.id_proposta)
                for doc in action_payload.documenti_aggiornati:
                    entry = proposta.documenti[doc.id]
                    entry.Clear()
                    entry.CopyFrom(doc)
                self.set_proposta_cessione_state(proposta)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(PropostaCessionePayload.Name(payload.payload_type)))
        
        # aggiornamento contratti proposta
        elif payload.payload_type == PropostaCessionePayload.AGGIORNAMENTO_CONTRATTI:
            action_payload = payload.aggiornamento_contratti
            if action_payload:
                proposta = self.get_proposta_cessione_state(action_payload.id_proposta)
                for contratto in action_payload.contratti_aggiornati:
                    entry = proposta.contratti[contratto.id]
                    entry.Clear()
                    entry.CopyFrom(contratto)
                self.set_proposta_cessione_state(proposta)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(PropostaCessionePayload.Name(payload.payload_type)))

        else:
            raise InvalidTransaction("Unhandled payload type")
        

    def get_proposta_cessione_address(self, id):
        return self.PROPOSTA_CESSIONE_NAMESPACE + hashlib.sha512(str(id).encode("utf-8")).hexdigest()[0:64]
    
    def get_proposta_cessione_state(self, id):
        address = self.get_proposta_cessione_address(id)
        proposta = PropostaCessioneState()
        try:
            proposta.ParseFromString(self._context.get_state([address])[0].data)
            return proposta
        except IndexError:
            raise InvalidTransaction('No data at address: {}'.format(address))
        except Exception as e:
            raise InternalError('Failed to load state data') from e
    
    def set_proposta_cessione_state(self, proposta):
        # TODO: aggiungere try catch 
        address = self.get_proposta_cessione_address(proposta.id)
        addresses = self._context.set_state({address: proposta.SerializeToString()})
        if not addresses:
            raise InternalError('State error')
