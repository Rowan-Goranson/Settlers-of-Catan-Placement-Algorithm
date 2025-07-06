import random
from constants import PORT_TYPES, PORT_LOCATION, DICE_NUMBERS, TILE_DISTRIBUTION, HEX_TO_NODE_MAP
from board_pieces import Hex, Node, Edge

        
class Board:
    def __init__(self, test_hexes = None):
        self.hexes = self.make_hexes(test_hexes) #list
        self.nodes = {}
        self.edges = []

        self.create_nodes_from_hex_map()
        self.assign_nodes_to_hexes()
        self.create_edges_from_nodes()
        self.assign_ports_to_nodes()

    def create_nodes_from_hex_map(self):
        node_ids = set()
        for node_list in HEX_TO_NODE_MAP.values():
            node_ids.update(node_list)
        self.nodes = {node_id: Node(node_id) for node_id in node_ids}
   
    def assign_nodes_to_hexes(self):
        for i, hex in enumerate(self.hexes):
            node_ids = HEX_TO_NODE_MAP[i]
            hex.node_ids = node_ids

            for node_id in node_ids:
                self.nodes[node_id].adj_hexes.append(i)
    
    def assign_ports_to_nodes(self):
        port_list = PORT_TYPES.copy()
        random.shuffle(port_list)

        for i in range(0,len(PORT_LOCATION), 2):
            port_type = port_list[i // 2]
            node_a = PORT_LOCATION[i]
            node_b = PORT_LOCATION[i+1]
            self.nodes[node_a].port = port_type
            self.nodes[node_b].port = port_type
  
    def create_edges_from_nodes(self):
        edge_pairs = set()
        for node_list in HEX_TO_NODE_MAP.values():
            for i in range(6):
                a = node_list[i]
                b = node_list[(i+1) % 6]
                edge = tuple(sorted((a,b)))
                edge_pairs.add(edge)
            
        for a,b in edge_pairs:
            node_a = self.nodes[a]
            node_b = self.nodes[b]

            edge = Edge(node_a, node_b)
            self.edges.append(edge)

            node_a.connected_nodes.add(b)
            node_b.connected_nodes.add(a)

    def make_hexes(self, test_hexes = None):
        hexes = []

        if test_hexes:
            for dice, resource in test_hexes:
                hex = Hex(resource, None if resource =='desert' else dice)
                hexes.append(hex)
            return hexes
    
        resource_pool = []
        for resource, count in TILE_DISTRIBUTION.items():
            resource_pool += [resource] * count
        random.shuffle(resource_pool)

        dice_pool = DICE_NUMBERS.copy()
        random.shuffle(dice_pool)

        for resource in resource_pool:
            if resource == 'desert':
                hex = Hex(resource, None)
            else:
                hex = Hex(resource, dice_pool.pop())
            hexes.append(hex)
        
        return hexes
    
    def show_board_tiles(self):
        for i, hex in enumerate(self.hexes):
            print(f'{i+1}, {hex}')

    def show_nodes_edges(self):
        print('nodes:')
        for node in self.nodes.values():
            print(node)
        print('\nEdges')
        for edge in self.edges:
            print(edge)

    def show_hexes(self):
        print("=== HEXES ===")
        for i, hex in enumerate(self.hexes):
            print(f'hex {i}, {hex}')
    
    def show_ports(self):
        print('===PORTS===')
        for node in self.nodes.values():
            if node.port is not None:
                print(f'{node.id} -> {node.port}')

    def show_full_board(self):
        print("=== HEX TILES ===")
        for i, hex in enumerate(self.hexes):
            print(f'hex {i}, {hex} -> Nodes: {hex.node_ids}')
        
        print('\n=== NODES ===')
        for node_id, node in self.nodes.items():
            print(f"{node_id}: connects to {sorted(node.connected_nodes)}, adjacent to hexes {node.adj_hexes}")
        
        print('\n=== EDGES ===')
        for edge in self.edges:
            print(edge)

        print('\n=== SUMMARY ===')
        print(f'total hexes: {len(self.hexes)}')
        print(f"total nodes: {len(self.nodes)}")
        print(f"Total Edge objects created: {len(self.edges)}")