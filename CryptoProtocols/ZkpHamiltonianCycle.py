import numpy as np
import os
import sys
import random
import struct
import json
import networkx as nx
from enum import Enum
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes, CipherContext
from Crypto.Random import get_random_bytes
from Ahc import \
    ComponentModel, Event, ConnectorTypes, ComponentRegistry, GenericMessagePayload, GenericMessageHeader, \
    GenericMessage, EventTypes
from LinkLayers.GenericLinkLayer import LinkLayer
from NetworkLayers.AllSeeingEyeNetworkLayer import AllSeingEyeNetworkLayer

sys.path.insert(0, os.getcwd())
registry = ComponentRegistry()


class PublicGraph:
    def __generate_graph_with_hamiltonian_cycle(self, graph_node_size, cycle_node_size):
        public_graph = nx.Graph()
        hamiltonian_cycle = nx.Graph()
        cycle_start_node = int(np.ceil((graph_node_size - cycle_node_size) / 2))
        public_graph.add_nodes_from(range(0, graph_node_size))
        hamiltonian_cycle.add_nodes_from(range(cycle_start_node, cycle_start_node + cycle_node_size))
        for i in range(cycle_start_node, cycle_start_node + cycle_node_size - 1):
            public_graph.add_edge(i, i + 1, attr=True)
            hamiltonian_cycle.add_edge(i, i + 1, attr=True)
        public_graph.add_edge(cycle_start_node + cycle_node_size - 1, cycle_start_node, attr=True)
        hamiltonian_cycle.add_edge(cycle_start_node + cycle_node_size - 1, cycle_start_node, attr=True)
        print(nx.to_numpy_matrix(hamiltonian_cycle,
                                 nodelist=[*range(cycle_start_node, cycle_start_node + cycle_node_size)]))
        print(nx.to_numpy_matrix(public_graph,
                                 nodelist=[*range(0, 0 + graph_node_size)]))
        print(hamiltonian_cycle.nodes)
        return public_graph, hamiltonian_cycle, cycle_start_node

    @staticmethod
    def get_graph():
        return PublicGraph.__GRAPH

    @staticmethod
    def get_hamiltonian_cycle(auth_keyword):
        # This method is abstract, it is used to give intuition that prover knows the cycle
        if auth_keyword == PublicGraph.__AUTH_KEYWORD:
            return PublicGraph.__HAMILTONIAN_CYCLE
        return None

    @staticmethod
    def get_graph_no_nodes():
        shape = nx.to_numpy_matrix(PublicGraph.__GRAPH).shape
        return shape[0]

    @staticmethod
    def get_graph_matrix_size():
        shape = nx.to_numpy_matrix(PublicGraph.__GRAPH).shape
        return shape[0] * shape[1]

    @staticmethod
    def get_hamiltonian_cycle_no_nodes(auth_keyword):
        # This method is abstract, it is used to give intuition that prover knows the cycle
        if auth_keyword == PublicGraph.__AUTH_KEYWORD:
            shape = nx.to_numpy_matrix(PublicGraph.__HAMILTONIAN_CYCLE).shape
            return shape[0]
        return None

    @staticmethod
    def get_hamiltonian_cycle_matrix_size(auth_keyword):
        # This method is abstract, it is used to give intuition that prover knows the cycle
        if auth_keyword == PublicGraph.__AUTH_KEYWORD:
            shape = nx.to_numpy_matrix(PublicGraph.__HAMILTONIAN_CYCLE).shape
            return shape[0] * shape[1]
        return None

    @staticmethod
    def get_hamiltonian_cycle_start_node(auth_keyword):
        # This method is abstract, it is used to give intuition that prover knows the cycle
        if auth_keyword == PublicGraph.__AUTH_KEYWORD:
            return PublicGraph.__CYCLE_START_NODE
        return None

    @staticmethod
    def convert_cypher_graph_to_bytes(graph):
        graph_bytes = b""
        for i in range(graph.shape[0]):
            for j in range(graph.shape[1]):
                graph_bytes += graph[i, j]
        print("Str graph", graph_bytes)
        return graph_bytes

    @staticmethod
    def convert_bytes_to_cypher_graph(graph_bytes):
        graph_no_nodes = PublicGraph.get_graph_no_nodes()
        matrix = np.asmatrix(np.zeros((graph_no_nodes, graph_no_nodes), dtype=CipherContext))
        tmp_graph_bytes = graph_bytes
        for i in range(matrix.shape[0]):
            for j in range(matrix.shape[1]):
                tmp_edge_bytes = tmp_graph_bytes[0:4]
                tmp_graph_bytes = tmp_graph_bytes[4:]
                matrix[i, j] = tmp_edge_bytes
        print("Graph Redesigned\n", matrix)
        return matrix

    __GRAPH, __HAMILTONIAN_CYCLE, __CYCLE_START_NODE = __generate_graph_with_hamiltonian_cycle(self=None,
                                                                                               graph_node_size=20,
                                                                                               cycle_node_size=10)
    # This keyword is abstract, it is used to give intuition that prover knows the cycle
    __AUTH_KEYWORD = "BearsBeetsBattleStarGalactica"


# define your own message types
class ApplicationLayerMessageTypes(Enum):
    COMMIT = "COMMIT"
    CHALLENGE = "CHALLENGE"
    RESPONSE = "RESPONSE"
    CORRECT_RESPONSE = "CORRECT_RESPONSE"
    ACCEPT = "ACCEPT"
    REJECT = "REJECT"


class ChallengeType(Enum):
    NONE = -1
    PROVE_GRAPH = 0
    SHOW_CYCLE = 1


# define your own message header structure
class ApplicationLayerMessageHeader(GenericMessageHeader):
    pass


# define your own message payload structure
class ApplicationLayerMessagePayload(GenericMessagePayload):
    pass


class BaseZkpAppLayerComponent(ComponentModel):
    def on_init(self, eventobj: Event):
        if self.componentinstancenumber == 0:
            print(f"Initializing {self.componentname}.{self.componentinstancenumber}")
            self.send_self(Event(self, "commit", None))
        else:
            pass

    def send_message(self, message_type, payload_data, destination):
        hdr = ApplicationLayerMessageHeader(message_type, self.componentinstancenumber, destination)
        payload = ApplicationLayerMessagePayload(payload_data)
        message = GenericMessage(hdr, payload)
        self.send_down(Event(self, EventTypes.MFRT, message))


class PeggyApplicationLayerComponent(BaseZkpAppLayerComponent):
    def on_message_from_bottom(self, eventobj: Event):
        try:
            app_message = eventobj.eventcontent
            hdr = app_message.header
            if hdr.messagetype == ApplicationLayerMessageTypes.CHALLENGE:
                print(
                    f"Node-{self.componentinstancenumber} says"
                    f"Node-{hdr.messagefrom} has sent {hdr.messagetype} message")
                print(f"Challenge-{app_message.payload.messagepayload}")
                self.send_self(Event(self, "challengereceived", app_message.payload.messagepayload))
            elif hdr.messagetype == ApplicationLayerMessageTypes.CORRECT_RESPONSE:
                self.send_self(Event(self, "commit", app_message.payload.messagepayload))
            elif hdr.messagetype == ApplicationLayerMessageTypes.ACCEPT:
                print(
                    f"Node-{self.componentinstancenumber} says"
                    f"Node-{hdr.messagefrom} has sent {hdr.messagetype} message")
            elif hdr.messagetype == ApplicationLayerMessageTypes.REJECT:
                print(
                    f"Node-{self.componentinstancenumber} says "
                    f"Node-{hdr.messagefrom} has sent {hdr.messagetype} message")
        except AttributeError:
            print("Attribute Error")

    def on_commit(self, eventobj: Event):
        # (re)initialize nonces and encryptors
        self.create_nonces_and_encryptors()
        # permute graph and get node mapping
        permuted_graph, self.graph["node_mapping"] = self.permute_graph()
        # encrypt permuted graph
        self.graph["committed_graph"] = self.encrypt_graph(permuted_graph)
        # send encrypted and permuted graph to verifier
        self.send_message(ApplicationLayerMessageTypes.COMMIT,
                          PublicGraph.convert_cypher_graph_to_bytes(self.graph["committed_graph"]),
                          self.destination)

    def on_challenge_received(self, eventobj: Event):
        challenge_type = eventobj.eventcontent
        if challenge_type == ChallengeType.PROVE_GRAPH:
            print("Recieved", challenge_type)
            self.send_message(ApplicationLayerMessageTypes.RESPONSE,
                              self.create_prove_graph_payload(), self.destination)
        elif challenge_type == ChallengeType.SHOW_CYCLE:
            print("Recieved", challenge_type)
            self.send_message(ApplicationLayerMessageTypes.RESPONSE,
                              self.create_show_cycle_payload(), self.destination)

    def on_timer_expired(self, eventobj: Event):
        pass

    def permute_graph(self):
        # get public graph
        public_graph = PublicGraph.get_graph()
        nodes = [*range(0, self.graph["graph_node_size"])]
        shuffled_nodes = random.sample(nodes, len(nodes))
        node_mapping = {}
        # form node mapping
        for i in range(len(nodes)):
            node_mapping[i] = shuffled_nodes[i]
        # return permuted graph with node mapping
        permuted_graph = nx.relabel_nodes(public_graph, node_mapping)
        return permuted_graph, node_mapping

    def encrypt_graph(self, graph):
        permuted_matrix = nx.to_numpy_matrix(graph, nodelist=[*range(0, self.graph["graph_node_size"])])
        print("Permuted Graph\n", permuted_matrix)
        encrypted_matrix = np.asmatrix(np.zeros_like(permuted_matrix, dtype=CipherContext))
        for i in range(permuted_matrix.shape[0]):
            for j in range(permuted_matrix.shape[1]):
                cipher_text = self.crypto["encryptor"][i * permuted_matrix.shape[1] + j] \
                    .update(struct.pack('f', permuted_matrix[i, j]))
                encrypted_matrix[i, j] = cipher_text
        print(encrypted_matrix)
        return encrypted_matrix

    def create_prove_graph_payload(self):
        payload = self.secrets["key"]
        for i in range(self.graph["graph_matrix_size"]):
            payload += self.secrets["nonces"][i]
        payload += json.dumps(self.graph["node_mapping"]).encode('utf-8')
        return payload

    def create_show_cycle_payload(self):
        cycle_nonces, index_list = self.get_cycle_nonces_indexes_as_bytes()
        payload = self.secrets["key"]
        payload += index_list
        payload += cycle_nonces
        print("payload", payload)
        return payload

    def get_cycle_nonces_indexes_as_bytes(self):
        hamiltonian_cycle = PublicGraph.get_hamiltonian_cycle(self.graph["graph_auth_keyword"])
        permuted_hamiltonian_cycle = nx.relabel_nodes(hamiltonian_cycle, self.graph["node_mapping"])
        cycle_nonces = b""
        index_list = b"{"
        for edge in list(permuted_hamiltonian_cycle.edges):
            cur_i = edge[0]
            cur_j = edge[1]
            # if part of the permuted hamiltonian cycle, add nonce with indexes
            cycle_nonces += self.secrets["nonces"][cur_i * self.graph["graph_node_size"] + cur_j]
            index_list += cur_i.to_bytes(2, "little") + cur_j.to_bytes(2, "little")
            # also add the symmetric edge
            cycle_nonces += self.secrets["nonces"][cur_j * self.graph["graph_node_size"] + cur_i]
            index_list += cur_j.to_bytes(2, "little") + cur_i.to_bytes(2, "little")
        index_list += b"}"
        return cycle_nonces, index_list

    def create_nonces_and_encryptors(self):
        if len(self.secrets["nonces"]) > 0 or len(self.crypto["encryptor"]) > 0:
            self.secrets["nonces"] = []
            self.crypto["encryptor"] = []
        for i in range(self.graph["graph_matrix_size"]):
            # add nonces for each
            self.secrets["nonces"].append(get_random_bytes(16))
            self.crypto["encryptor"].append(Cipher(algorithms.AES(self.secrets["key"]),
                                                   modes.CTR(self.secrets["nonces"][i]),
                                                   default_backend()).encryptor())

    def __init__(self, componentname, componentinstancenumber):
        super().__init__(componentname, componentinstancenumber)
        self.destination = 1
        # graph related info for prover
        self.graph = {
            # encrypted and permuted new graph
            "committed_graph": np.asmatrix([]),
            "node_mapping": {},
            "graph_node_size": PublicGraph.get_graph_no_nodes(),
            "graph_matrix_size": PublicGraph.get_graph_matrix_size(),
            # This keyword is abstract, it is used to give intuition that prover knows the cycle
            "graph_auth_keyword": "BearsBeetsBattleStarGalactica"
        }
        # secrets of component
        self.secrets = {
            # key is 32 byte as AES use 256 bits key - updated at each commit
            "key": get_random_bytes(32),
            # nonce is 16 byte as AES use 128 bits block - updated at each commit
            "nonces": []
        }
        # crypto tools
        self.crypto = {
            # AES has block size of 128 bits plain text block -> 128 bits cipher text block, holds list of encryptors
            "encryptor": []
        }
        self.eventhandlers["commit"] = self.on_commit
        self.eventhandlers["challengereceived"] = self.on_challenge_received
        self.eventhandlers["timerexpired"] = self.on_timer_expired


class VictorApplicationLayerComponent(BaseZkpAppLayerComponent):
    def on_message_from_bottom(self, eventobj: Event):
        try:
            app_message = eventobj.eventcontent
            hdr = app_message.header
            if hdr.messagetype == ApplicationLayerMessageTypes.COMMIT:
                print(
                    f"Node-{self.componentinstancenumber} says "
                    f"Node-{hdr.messagefrom} has sent {hdr.messagetype} message")
                print(f"Graph-\n{PublicGraph.convert_bytes_to_cypher_graph(app_message.payload.messagepayload)}")
                self.verification["committed_graph"] = \
                    PublicGraph.convert_bytes_to_cypher_graph(app_message.payload.messagepayload)
                self.send_self(Event(self, "challenge", None))
            elif hdr.messagetype == ApplicationLayerMessageTypes.RESPONSE:
                print(
                    f"Node-{self.componentinstancenumber} says "
                    f"Node-{hdr.messagefrom} has sent {hdr.messagetype} message")
                self.send_self(Event(self, "responsereceived", app_message.payload.messagepayload))
        except AttributeError:
            print("Attribute Error")

    def on_challenge(self, eventobj: Event):
        if random.uniform(0, 1) < 0.5:
            self.verification["current_challenge_mode"] = ChallengeType.PROVE_GRAPH
        else:
            self.verification["current_challenge_mode"] = ChallengeType.SHOW_CYCLE
        self.send_message(ApplicationLayerMessageTypes.CHALLENGE,
                          self.verification["current_challenge_mode"],
                          self.destination)

    def on_response_received(self, eventobj: Event):
        message_payload = eventobj.eventcontent
        if self.verification["current_challenge_mode"] == ChallengeType.PROVE_GRAPH:
            key, nonces, node_mapping = self.extract_prove_graph_reponse_payload(message_payload)
            if self.are_equal_graphs(self.decrypt_graph(key, nonces), node_mapping):
                self.send_self(Event(self, "correctresponse", None))
            else:
                self.send_self(Event(self, "wrongresponse", None))
        elif self.verification["current_challenge_mode"] == ChallengeType.SHOW_CYCLE:
            key, nonces, index_list = self.extract_show_cycle_reponse_payload(message_payload)
            if self.graph_has_cycle(self.decrypt_graph(key, nonces, index_list)):
                self.send_self(Event(self, "correctresponse", None))
            else:
                self.send_self(Event(self, "wrongresponse", None))

    def extract_prove_graph_reponse_payload(self, message_payload):
        key = message_payload[0:32]
        nonces = []
        for i in range(self.verification["graph_matrix_size"]):
            nonces.append(message_payload[i * 16 + 32: i * 16 + 48])
        node_mapping_json = json.loads(
            message_payload[self.verification["graph_matrix_size"] * 16 + 32:].decode('utf-8'))
        node_mapping = {}
        for k in node_mapping_json:
            node_mapping[int(k)] = node_mapping_json[k]
        return key, nonces, node_mapping

    def extract_show_cycle_reponse_payload(self, message_payload):
        key = message_payload[0:32]
        indices_start_index = message_payload[32:].find(b"{") + 1 + 32
        indices_end_index = message_payload[32:].find(b"}") + 32
        nonce_start_index = indices_end_index + 1
        index_list_bytes = message_payload[indices_start_index: indices_end_index]
        no_index = int((indices_end_index - indices_start_index) / 4)
        index_list = []
        nonces = []
        for i in range(no_index):
            current_i = int.from_bytes(index_list_bytes[i * 4: i * 4 + 2], "little")
            current_j = int.from_bytes(index_list_bytes[i * 4 + 2: i * 4 + 4], "little")
            index_list.append((current_i, current_j))
            nonces.append(message_payload[i * 16 + nonce_start_index: (i + 1) * 16 + nonce_start_index])
        return key, nonces, index_list

    def on_correct_response(self, eventobj: Event):
        print("Correct Response Recieved")
        self.verification["current_trial_no"] += 1
        if self.verification["current_trial_no"] == self.verification["max_trial_no"]:
            self.send_message(ApplicationLayerMessageTypes.ACCEPT, None, self.destination)
            return
        self.send_message(ApplicationLayerMessageTypes.CORRECT_RESPONSE, None, self.destination)

    def on_wrong_response(self, eventobj: Event):
        print("Wrong Response Recieved")
        self.send_message(ApplicationLayerMessageTypes.REJECT, None, self.destination)

    def on_timer_expired(self, eventobj: Event):
        pass

    def decrypt_graph(self, key, nonces, index_list=None):
        decrypted_matrix = np.asmatrix(np.zeros_like(self.verification["committed_graph"], dtype=float))
        if index_list is None:
            for i in range(decrypted_matrix.shape[0]):
                for j in range(decrypted_matrix.shape[1]):
                    decryptor = Cipher(algorithms.AES(key),
                                       modes.CTR(nonces[i * decrypted_matrix.shape[1] + j]),
                                       default_backend()).decryptor()
                    plain_text = struct.unpack('f', decryptor.update(self.verification["committed_graph"][i, j]))[0]
                    decrypted_matrix[i, j] = plain_text
        else:
            for i in range(len(index_list)):
                current_i, current_j = index_list[i]
                decryptor = Cipher(algorithms.AES(key),
                                   modes.CTR(nonces[i]),
                                   default_backend()).decryptor()
                plain_text = struct.unpack('f', decryptor.update(self.verification["committed_graph"]
                                                                 [current_i, current_j]))[0]
                decrypted_matrix[current_i, current_j] = plain_text
        print("Victor Decrypted Received Graph\n", decrypted_matrix)
        decrypted_graph = nx.from_numpy_matrix(decrypted_matrix)
        return decrypted_graph

    def are_equal_graphs(self, decrypted_graph, node_mapping):
        public_graph = PublicGraph.get_graph()
        permuted_graph = nx.relabel_nodes(public_graph, node_mapping)
        permuted_matrix = nx.to_numpy_matrix(permuted_graph, nodelist=[*range(0, 5)])
        decrypted_matrix = nx.to_numpy_matrix(decrypted_graph, nodelist=[*range(0, 5)])
        for i in range(permuted_matrix.shape[0]):
            for j in range(permuted_matrix.shape[1]):
                try:
                    if permuted_matrix[i, j] != decrypted_matrix[i, j]:
                        return False
                except IndexError:
                    return False
        return True

    def is_symetric_graph(self, decrypted_graph_matrix):
        no_nodes = decrypted_graph_matrix.shape[0]
        for i in range(no_nodes):
            for j in range(i, no_nodes):
                if decrypted_graph_matrix[i, j] != decrypted_graph_matrix[j, i]:
                    return False
        return True

    def graph_has_cycle(self, decrypted_graph):
        no_nodes = PublicGraph.get_graph_no_nodes()
        decrypted_graph_matrix = nx.to_numpy_matrix(decrypted_graph, nodelist=[*range(0, no_nodes)])
        if not self.is_symetric_graph(decrypted_graph_matrix):
            # first check if graph is symmetric, if not undirected return false
            return False
        no_nodes = len(decrypted_graph.nodes)
        visited_nodes = np.zeros((no_nodes,), dtype=bool)
        # nodes initialized to default value
        start_node = prev_node = current_node = -1
        # loop through to find the start node
        for i in range(no_nodes):
            for j in range(no_nodes):
                if decrypted_graph_matrix[i, j] == 1:
                    start_node = i
                    prev_node = i
                    current_node = j
                    visited_nodes[start_node] = True
                    break
            if start_node > -1:
                break
        if start_node == -1:
            # if no node is start node, then empty graph, no cycle
            return False
        # loop through to check cycle
        while True:
            for i in range(no_nodes):
                if i != prev_node and decrypted_graph_matrix[current_node, i] == 1:
                    # if edge found and not to the previous node
                    if start_node == i:
                        # if starting node reached we have cycle return true
                        return True
                    elif visited_nodes[i]:
                        # if already visited node and not start node return false
                        return False
                    else:
                        # if new node, update prev node and current node, mark as visited
                        prev_node = current_node
                        current_node = i
                        visited_nodes[current_node] = True
                        break

    def __init__(self, componentname, componentinstancenumber):
        super().__init__(componentname, componentinstancenumber)
        self.destination = 0
        # verification related data
        self.verification = {
            "current_trial_no": 0,
            "current_challenge_mode": ChallengeType.NONE,
            "max_trial_no": 10,
            "committed_graph": np.asmatrix([]),
            "graph_matrix_size": PublicGraph.get_graph_matrix_size()
        }
        self.eventhandlers["challenge"] = self.on_challenge
        self.eventhandlers["responsereceived"] = self.on_response_received
        self.eventhandlers["correctresponse"] = self.on_correct_response
        self.eventhandlers["wrongresponse"] = self.on_wrong_response
        self.eventhandlers["timerexpired"] = self.on_timer_expired


class PeggyAdHocNode(ComponentModel):

    def on_init(self, eventobj: Event):
        print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

    def on_message_from_top(self, eventobj: Event):
        self.send_down(Event(self, EventTypes.MFRT, eventobj.eventcontent))

    def on_message_from_bottom(self, eventobj: Event):
        self.send_up(Event(self, EventTypes.MFRB, eventobj.eventcontent))

    def __init__(self, componentname, componentid):
        # SUBCOMPONENTS
        self.appllayer = PeggyApplicationLayerComponent("PeggyApplicationLayer", componentid)
        self.netlayer = AllSeingEyeNetworkLayer("NetworkLayer", componentid)
        self.linklayer = LinkLayer("LinkLayer", componentid)

        # CONNECTIONS AMONG SUBCOMPONENTS
        self.appllayer.connect_me_to_component(ConnectorTypes.DOWN, self.netlayer)
        self.netlayer.connect_me_to_component(ConnectorTypes.UP, self.appllayer)
        self.netlayer.connect_me_to_component(ConnectorTypes.DOWN, self.linklayer)
        self.linklayer.connect_me_to_component(ConnectorTypes.UP, self.netlayer)

        # Connect the bottom component to the composite component....
        self.linklayer.connect_me_to_component(ConnectorTypes.DOWN, self)
        self.connect_me_to_component(ConnectorTypes.UP, self.linklayer)

        super().__init__(componentname, componentid)


class VictorAdHocNode(ComponentModel):

    def on_init(self, eventobj: Event):
        print(f"Initializing {self.componentname}.{self.componentinstancenumber}")

    def on_message_from_top(self, eventobj: Event):
        self.send_down(Event(self, EventTypes.MFRT, eventobj.eventcontent))

    def on_message_from_bottom(self, eventobj: Event):
        self.send_up(Event(self, EventTypes.MFRB, eventobj.eventcontent))

    def __init__(self, componentname, componentid):
        # SUBCOMPONENTS
        self.appllayer = VictorApplicationLayerComponent("VictorApplicationLayer", componentid)
        self.netlayer = AllSeingEyeNetworkLayer("NetworkLayer", componentid)
        self.linklayer = LinkLayer("LinkLayer", componentid)

        # CONNECTIONS AMONG SUBCOMPONENTS
        self.appllayer.connect_me_to_component(ConnectorTypes.DOWN, self.netlayer)
        self.netlayer.connect_me_to_component(ConnectorTypes.UP, self.appllayer)
        self.netlayer.connect_me_to_component(ConnectorTypes.DOWN, self.linklayer)
        self.linklayer.connect_me_to_component(ConnectorTypes.UP, self.netlayer)

        # Connect the bottom component to the composite component....
        self.linklayer.connect_me_to_component(ConnectorTypes.DOWN, self)
        self.connect_me_to_component(ConnectorTypes.UP, self.linklayer)

        super().__init__(componentname, componentid)
