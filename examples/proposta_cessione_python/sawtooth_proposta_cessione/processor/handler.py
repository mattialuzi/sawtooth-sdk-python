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
from sawtooth_sdk.protobuf.cessione_credito_pb2 import StatoOffertaProposta
from sawtooth_sdk.protobuf.cessione_credito_pb2 import Utente



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

    UTENTE_NAMESPACE = hashlib.sha512('utente'.encode("utf-8")).hexdigest()[0:6]

    @property
    def namespaces(self):
        return [self.PROPOSTA_CESSIONE_NAMESPACE]
    
    STATI_PROPOSTA_RUOLI = {
        PropostaCessioneState.PREPARAZIONE: [Utente.CEDENTE],
        PropostaCessioneState.PROPOSTA: [Utente.CEDENTE],
        PropostaCessioneState.PRESA_IN_CARICO: [Utente.ACQUIRENTE],
        PropostaCessioneState.VALIDATA: [Utente.ACQUIRENTE, Utente.REVISORE_FISCALE],
        PropostaCessioneState.INVALIDATA: [Utente.ACQUIRENTE, Utente.REVISORE_FISCALE],
        PropostaCessioneState.VALIDATA: [Utente.ACQUIRENTE, Utente.REVISORE_FISCALE],
        PropostaCessioneState.CONTRATTO_DA_FIRMARE: [Utente.ACQUIRENTE],
        PropostaCessioneState.CONTRATTO_FIRMATO: [Utente.CEDENTE],
    }

    STATI_OFFERTA_RUOLI = {
        StatoOffertaProposta.PROPOSTA_CEDENTE: [Utente.CEDENTE],
        StatoOffertaProposta.PROPOSTA_ACQUIRENTE: [Utente.ACQUIRENTE],
        StatoOffertaProposta.ACETTATA: [Utente.CEDENTE],
        StatoOffertaProposta.RIFIUTATA: [Utente.CEDENTE],
        StatoOffertaProposta.CANCELLATA: [Utente.CEDENTE]
    }
    
    def apply(self, transaction, context):
        
        self._context = context
        header = transaction.header
        signer = header.signer_public_key

        payload = PropostaCessionePayload()
        try:
            payload.ParseFromString(transaction.payload)
        except Exception:
            raise InvalidTransaction("Invalid payload serialization")

        # ottiene le informazioni dell'utente che sta eseguendo la transazione 
        utente = self.get_utente_state(signer)

        # Nuova proposta
        if payload.payload_type == PropostaCessionePayload.NUOVA_PROPOSTA:
            if payload.HasField('nuova_proposta'):
                action_payload = payload.nuova_proposta
                self.check_utente_authorization(utente, [Utente.CEDENTE], id=action_payload.id_cedente)
                self.set_proposta_cessione_state(action_payload)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(PropostaCessionePayload.PayloadType.Name(payload.payload_type)))

        # aggiornamento stato proposta    
        elif payload.payload_type == PropostaCessionePayload.AGGIORNAMENTO_STATO:
            if payload.HasField('aggiornamento_stato'):
                action_payload = payload.aggiornamento_stato
                proposta = self.get_proposta_cessione_state(action_payload.id_proposta)
                id = proposta.id_cedente if utente.ruolo == Utente.CEDENTE else None
                id_gruppo_acquirente = None
                if any(utente.ruolo == ruolo for ruolo in [Utente.ACQUIRENTE, Utente.REVISORE_FISCALE]): 
                    id_gruppo_acquirente = proposta.id_gruppo_acquirente
                self.check_utente_authorization(utente, self.STATI_PROPOSTA_RUOLI[action_payload.nuovo_stato], id, id_gruppo_acquirente) 
                proposta.stato = action_payload.nuovo_stato
                proposta.note = action_payload.note
                # TODO: aggiungere l'id gruppo acquirente da aggiornare quando uno gruppo si aggiudica la proposta 
                self.set_proposta_cessione_state(proposta)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(PropostaCessionePayload.PayloadType.Name(payload.payload_type)))
        
        # aggiornamento offerte proposta
        elif payload.payload_type == PropostaCessionePayload.AGGIORNAMENTO_OFFERTE:
            if payload.HasField('aggiornamento_offerte'):
                action_payload = payload.aggiornamento_offerte
                proposta = self.get_proposta_cessione_state(action_payload.id_proposta)
                
                # TODO: cambiare il nome dello stato in cui si trova la proposta durante l'assegnazione della proposta (asta)
                if proposta.stato != PropostaCessioneState.PREPARAZIONE:
                    raise InvalidTransaction("Le offerte possono essere modficate solo quando la proposta è nello stato PREPARAZIONE")
 
                is_cedente = utente.ruolo == Utente.CEDENTE
                is_gruppo_acquirente = any(utente.ruolo == ruolo for ruolo in [Utente.ACQUIRENTE, Utente.REVISORE_FISCALE])

                for offerta in action_payload.offerte_aggiornate:
                    id = proposta.id_cedente if is_cedente else None
                    id_gruppo_acquirente = offerta.id_gruppo_acquirente if is_gruppo_acquirente else None
                    self.check_utente_authorization(utente, self.STATI_OFFERTA_RUOLI[offerta.stato], id, id_gruppo_acquirente)
                    entry = proposta.offerte[offerta.id]
                    entry.Clear()
                    entry.CopyFrom(offerta)

                self.set_proposta_cessione_state(proposta)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(PropostaCessionePayload.PayloadType.Name(payload.payload_type)))

        # aggiornamento documenti proposta
        elif payload.payload_type == PropostaCessionePayload.AGGIORNAMENTO_DOCUMENTI:
            if payload.HasField('aggiornamento_documenti'):
                action_payload = payload.aggiornamento_documenti
                proposta = self.get_proposta_cessione_state(action_payload.id_proposta)

                # TODO: considera il caso del bonifico (che carica l'acquirente)
                self.check_utente_authorization(utente, [Utente.CEDENTE], id=proposta.id_cedente)
                
                for doc in action_payload.documenti_aggiornati:
                    entry = proposta.documenti[doc.id]
                    entry.Clear()
                    entry.CopyFrom(doc)

                self.set_proposta_cessione_state(proposta)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(PropostaCessionePayload.PayloadType.Name(payload.payload_type)))
        
        # aggiornamento contratti proposta
        elif payload.payload_type == PropostaCessionePayload.AGGIORNAMENTO_CONTRATTI:
            if payload.HasField('aggiornamento_contratti'):
                action_payload = payload.aggiornamento_contratti
                proposta = self.get_proposta_cessione_state(action_payload.id_proposta)
                self.check_utente_authorization(utente, [Utente.CEDENTE], id=proposta.id_cedente)

                for contratto in action_payload.contratti_aggiornati:
                    entry = proposta.contratti[contratto.id]
                    entry.Clear()
                    entry.CopyFrom(contratto)

                self.set_proposta_cessione_state(proposta)
            else: 
                raise InvalidTransaction("Payload for {} not set".format(PropostaCessionePayload.PayloadType.Name(payload.payload_type)))

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
        address = self.get_proposta_cessione_address(proposta.id)
        addresses = self._context.set_state({address: proposta.SerializeToString()})
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
