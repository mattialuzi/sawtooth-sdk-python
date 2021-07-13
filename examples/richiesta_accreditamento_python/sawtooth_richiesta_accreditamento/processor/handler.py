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
from sawtooth_sdk.protobuf.cessione_credito_pb2 import Utente

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
    
    UTENTE_NAMESPACE = hashlib.sha512('utente'.encode("utf-8")).hexdigest()[0:6]

    @property
    def namespaces(self):
        return [self.RICHIESTA_ACCREDITAMENTO_NAMESPACE]

    STATI_RICHIESTA_RUOLI = {
        RichiestaAccreditamentoState.PREPARAZIONE: [Utente.CEDENTE],
        RichiestaAccreditamentoState.DA_VALIDARE: [Utente.CEDENTE],
        RichiestaAccreditamentoState.ACCREDITATO: [Utente.ACQUIRENTE, Utente.VALIDATORE],
        RichiestaAccreditamentoState.NON_VALIDO: [Utente.ACQUIRENTE, Utente.VALIDATORE],
    }
    
    def apply(self, transaction, context):
        
        self._context = context
        header = transaction.header
        signer = header.signer_public_key

        payload = RichiestaAccreditamentoPayload()
        try:
            payload.ParseFromString(transaction.payload)
        except Exception:
            raise InvalidTransaction("Invalid payload serialization")

        # ottiene le informazioni dell'utente che sta eseguendo la transazione 
        utente = self.get_utente_state(signer) 
        
        # Nuova richiesta
        if payload.type == RichiestaAccreditamentoPayload.CREAZIONE_RICHIESTA:
            payload_data = RichiestaAccreditamentoState()
            try:
                payload_data.ParseFromString(payload.data)
                self.check_utente_authorization(utente, [Utente.CEDENTE], id=payload_data.id_cedente)
                self.set_richiesta_accreditamento_state(payload_data)
            except Exception:
                raise InvalidTransaction("Invalid Payload for {}".format(RichiestaAccreditamentoPayload.PayloadType.Name(payload.type)))

        # aggiornamento stato richiesta    
        elif payload.type == RichiestaAccreditamentoPayload.AGGIORNAMENTO_STATO:
            payload_data = RichiestaAccreditamentoPayload.AggiornamentoStato
            try:
                payload_data.ParseFromString(payload.data)
                richiesta = self.get_richiesta_accreditamento_state(payload_data.id_richiesta)

                id = richiesta.id_cedente if utente.ruolo == Utente.CEDENTE else None
                id_gruppo_acquirente = None
                if any(utente.ruolo == ruolo for ruolo in [Utente.ACQUIRENTE, Utente.VALIDATORE]): 
                    id_gruppo_acquirente = richiesta.id_gruppo_acquirente
                self.check_utente_authorization(utente, self.STATI_RICHIESTA_RUOLI[payload_data.nuovo_stato], id, id_gruppo_acquirente)

                richiesta.stato = payload_data.nuovo_stato
                richiesta.note = payload_data.note
                richiesta.data_accreditamento = payload_data.data_accreditamento
                self.set_richiesta_accreditamento_state(richiesta)
            except Exception:
                raise InvalidTransaction("Invalid Payload for {}".format(RichiestaAccreditamentoPayload.PayloadType.Name(payload.type)))
        
        # aggiornamento documenti richiesta
        elif payload.type == RichiestaAccreditamentoPayload.AGGIORNAMENTO_DOCUMENTI:
            payload_data = RichiestaAccreditamentoPayload.AggiornamentoFile()
            try:
                payload_data.ParseFromString(payload.data)
                richiesta = self.get_richiesta_accreditamento_state(payload_data.id_richiesta)

                self.check_utente_authorization(utente, [Utente.CEDENTE], id=richiesta.id_cedente)
            
                for doc in payload_data.file_aggiornati:
                    entry = richiesta.documenti[doc.id]
                    entry.Clear()
                    entry.CopyFrom(doc)
                self.set_richiesta_accreditamento_state(richiesta)
            except Exception:
                raise InvalidTransaction("Invalid Payload for {}".format(RichiestaAccreditamentoPayload.PayloadType.Name(payload.type)))

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
    
    def set_richiesta_accreditamento_state(self, richiesta):
        # TODO: aggiungere try catch 
        address = self.get_richiesta_accreditamento_address(richiesta.id)
        addresses = self._context.set_state({address: richiesta.SerializeToString()})
        if not addresses:
            raise InternalError('State error')
    
    def check_utente_authorization(self, utente, ruoli = None, id = None, id_gruppo_acquirente = None):
        if ruoli and not any(utente.ruolo == ruolo for ruolo in ruoli):
            raise InvalidTransaction("Ruolo utente {} non autorizzato a eseguire la transazione".format(Utente.Ruolo.Name(utente.ruolo)))
        if id and utente.id != id:
            raise InvalidTransaction("Utente non autorizzato a eseguire la transazione")
        if id_gruppo_acquirente and utente.id_gruppo_acquirente != id_gruppo_acquirente:
            raise InvalidTransaction("Il gruppo acquirente dell'utente non è autorizzato a eseguire la transazione")
        return utente

    def get_utente_address(self, public_key):
        return self.UTENTE_NAMESPACE + hashlib.sha512(str(public_key).encode("utf-8")).hexdigest()[0:64]
    
    def get_utente_state(self, public_key):
        address = self.get_utente_address(public_key)
        utente = Utente()
        try:
            utente.ParseFromString(self._context.get_state([address])[0].data)
            return utente
        except IndexError:
            raise InvalidTransaction("Utente non registrato")

