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
        
        # header = transaction.header
        # signer = header.signer_public_key

        payload = PropostaCessionePayload()
        # aggiungere try catch deserializzazione
        try:
            payload.ParseFromString(transaction.payload)
            if payload.payload_type == PropostaCessionePayload.PayloadType.NUOVA_PROPOSTA:
                nuova_proposta = payload.nuova_proposta
                address = self.PROPOSTA_CESSIONE_NAMESPACE + hashlib.sha512(str(nuova_proposta.id).encode("utf-8")).hexdigest()[0:64]
                context.set_state({address: nuova_proposta.SerializeToString()})
            else:
                raise InvalidTransaction("Unhandled Payload Type")
        except Exception:
            raise InvalidTransaction("Invalid payload serialization")
        
# def _update_board(board, space, state):
#     if state == 'P1-NEXT':
#         mark = 'X'
#     elif state == 'P2-NEXT':
#         mark = 'O'

#     index = space - 1

#     # replace the index-th space with mark, leave everything else the same
#     return ''.join([
#         current if square != index else mark
#         for square, current in enumerate(board)
#     ])


# def _update_game_state(game_state, board):
#     x_wins = _is_win(board, 'X')
#     o_wins = _is_win(board, 'O')

#     if x_wins and o_wins:
#         raise InternalError('Two winners (there can be only one)')

#     if x_wins:
#         return 'P1-WIN'

#     if o_wins:
#         return 'P2-WIN'

#     if '-' not in board:
#         return 'TIE'

#     if game_state == 'P1-NEXT':
#         return 'P2-NEXT'

#     if game_state == 'P2-NEXT':
#         return 'P1-NEXT'

#     if game_state in ('P1-WINS', 'P2-WINS', 'TIE'):
#         return game_state

#     raise InternalError('Unhandled state: {}'.format(game_state))


# def _is_win(board, letter):
#     wins = ((1, 2, 3), (4, 5, 6), (7, 8, 9),
#             (1, 4, 7), (2, 5, 8), (3, 6, 9),
#             (1, 5, 9), (3, 5, 7))

#     for win in wins:
#         if (board[win[0] - 1] == letter
#                 and board[win[1] - 1] == letter
#                 and board[win[2] - 1] == letter):
#             return True
#     return False


# def _game_data_to_str(board, game_state, player1, player2, name):
#     board = list(board.replace("-", " "))
#     out = ""
#     out += "GAME: {}\n".format(name)
#     out += "PLAYER 1: {}\n".format(player1[:6])
#     out += "PLAYER 2: {}\n".format(player2[:6])
#     out += "STATE: {}\n".format(game_state)
#     out += "\n"
#     out += "{} | {} | {}\n".format(board[0], board[1], board[2])
#     out += "---|---|---\n"
#     out += "{} | {} | {}\n".format(board[3], board[4], board[5])
#     out += "---|---|---\n"
#     out += "{} | {} | {}".format(board[6], board[7], board[8])
#     return out


# def _display(msg):
#     n = msg.count("\n")

#     if n > 0:
#         msg = msg.split("\n")
#         length = max(len(line) for line in msg)
#     else:
#         length = len(msg)
#         msg = [msg]

#     # pylint: disable=logging-not-lazy
#     LOGGER.debug("+" + (length + 2) * "-" + "+")
#     for line in msg:
#         LOGGER.debug("+ " + line.center(length) + " +")
#     LOGGER.debug("+" + (length + 2) * "-" + "+")
