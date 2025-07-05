
from board_pieces import Hex, Node, Edge
from game import Player, Game
import constants
import random

class Tracker:
    def __init__(self):
        self.hexes = []
        self.nodes = {}
        self.players = [Player(i) for i in range(4)]
        self.setup_phase = False
        
        #self.input_hexes()
        self.make_test_hex()
        self.show_hexes()
        self.create_nodes_from_hex_map()
        self.assign_nodes_to_hexes()
        self.assign_ports_to_nodes()
        self.input_settlements()
        self.print_player_resources()
        self.distribute_resources_by_roll()
    
    def make_test_hex(self):
        test_list = constants.TEST_BOARD.copy()
        for num, resource in test_list:
            self.hexes.append(Hex(resource, num))
        
    def input_hexes(self):
        print('enter 19 hexes: resource, dice number ')
        for i in range(19):
            while True:
                try:
                    line = input(f'Hex {i}: ').strip()
                    num, res = line.split()
                    num = int(num)
                    if num not in range(0,13) or res not in constants.RESOURCES + ['desert']:
                        print('error')
                        continue
                    self.hexes.append(Hex(res, num))
                    break
                except:
                    print('invalid')

    def create_nodes_from_hex_map(self):
        node_ids = set()
        for node_list in constants.HEX_TO_NODE_MAP.values():
            node_ids.update(node_list)
        self.nodes = {node_id: Node(node_id) for node_id in node_ids}
   
    def assign_nodes_to_hexes(self):
        for i, hex in enumerate(self.hexes):
            node_ids = constants.HEX_TO_NODE_MAP[i]
            hex.node_ids = node_ids

            for node_id in node_ids:
                self.nodes[node_id].adj_hexes.append(i)
    
    def input_settlements(self):
        print('enter starting settlements, node_x player')
        print('done to finish')
        settle_counts = {i: 0 for i in range(4)}

        while True:
            line = input('>> ')
            if line.lower() == 'done':
                break
            try: 
                node_id, p_id = line.strip().split()
                p_id = int(p_id)
                if node_id not in self.nodes:
                    print(f'{node_id} not a valid node')
                    continue
                
                self.nodes[node_id].owner = p_id
                self.nodes[node_id].building_type = 'settlement'
                self.players[p_id].settlements.add(node_id)

                settle_counts[p_id] += 1

                if settle_counts[p_id] == 2:
                    self.grant_starting_resources(p_id, node_id)
            except:
                print('invalid')
            
    def assign_ports_to_nodes(self):
        port_list = constants.PORT_TYPES.copy()
        random.shuffle(port_list)

        for i in range(0,len(constants.PORT_LOCATION), 2):
            port_type = port_list[i // 2]
            node_a = constants.PORT_LOCATION[i]
            node_b = constants.PORT_LOCATION[i+1]
            self.nodes[node_a].port = port_type
            self.nodes[node_b].port = port_type

    def grant_starting_resources(self, player_id, node_id):
        for hex_tile in self.hexes:
            if node_id in hex_tile.node_ids and hex_tile.resource != 'desert':
                self.players[player_id].resources[hex_tile.resource] += 1
                print(f"Player {player_id} receives 1 {hex_tile.resource} from hex {hex_tile.dice_number}")

    def spend_resources(self, player, cost_dict):
        for res, amt in cost_dict.items():
            player.resources[res] -= amt

    def distribute_resources_by_roll(self):
        while True:
            roll = input('input roll: ')
            if roll == 'done':
                break
            if roll == 'trade':
                self.trade()
                continue
            roll = int(roll)
            if roll == 7:
                self.handle_robber_roll()
                self.activate_robber()
            for hex in self.hexes:
                if hex.dice_number != roll or hex.robber:
                    continue

                for node_id in hex.node_ids:
                    node = self.nodes[node_id]
                    if node.owner is not None:
                        player = self.players[node.owner]
                        amount = 2 if node.building_type == 'city' else 1
                        player.resources[hex.resource] += amount

                        print(f"Player {player.id} receives {amount} {hex.resource} from tile {hex}")
                        print('')
            self.print_player_resources()


    def print_player_resources(self):
        print('\n === PLAYER RESOURCE TOTALS ===')
        for player in self.players:
            print(f'Player {player.id}: {player.resources}')
            print('')

    def handle_robber_roll(self):
        print('7 rolled!')
        for player in self.players:
            total_cards = sum(player.resources.values())
            if total_cards > 7:
                to_discard = total_cards // 2
                print(f'player {player.id} has {total_cards} cards and must discard {to_discard}.')
            
                while to_discard > 0:
                    print(f'resources: {player.resources}')
                    res = input(f'pick resource to discard: ')
                    if res not in constants.RESOURCES or player.resources.get(res,0) == 0:
                        print('invalid')
                        continue
                    player.resources[res] -= 1
                    to_discard -= 1
                    print(f'discarded 1 {res}')

    def build_settlement(self):
        node_input = input('node settled: ')
        node = self.nodes.get(node_input)
        
        player = self.player[input('player id: ')]
        self.spend_resources(player, constants.COSTS_CARD['settlement'])
        node.owner = player.id
        node.building_type = 'settlement'
        player.settlements.add(node_input)
        return True, 'settlement built'
    
    def build_city(self):
        node_input = input('node citied: ')
        node = self.nodes.get(node_input)
        
        player = self.player[input('player id: ')]
        self.spend_resources(player, constants.COSTS_CARD['city'])
        node.owner = player.id
        player.settlements.remove(node_input)
        node.building_type = 'city'
        player.cities.add(node_input)
        return True, 'city built'
    
    def parse_resource_list(parts):
        resources = {}
        i = 0
        while i < len(parts):
            try:
                count = int(parts[i])
                resource = parts[i + 1]
                resources[resource] = resources.get(resource, 0) + count
                i += 2
            except:
                break
        return resources, i
    
    def trade(self):
        print('example: {player/bank} {player_id} gives X {resource} X {resource} ... gets X {resource}')
        line = input("Enter trade command: ").strip().lower()
        
        parts = line.split()

        if not parts:
            print("Invalid input.")
            return

        if parts[0] == 'bank':
            try:
                player_id = int(parts[1])
                player = self.players[player_id]
            except:
                print("Invalid bank trade syntax.")
                return

            try:
                gives_index = parts.index('gives')
                gets_index = parts.index('gets')
            except ValueError:
                print("Trade must include 'gives' and 'gets'.")
                return

            give_parts = parts[gives_index + 1 : gets_index]
            get_parts = parts[gets_index + 1 :]

            give_dict, _ = self.parse_resource_list(give_parts)
            get_dict, _ = self.parse_resource_list(get_parts)

            # Calculate effective rate
            total_given = sum(give_dict.values())
            total_gotten = sum(get_dict.values())
            if total_gotten != 1:
                print("Bank trades must result in exactly 1 resource.")
                return

            # Determine correct trade rate
            offered_resource = next(iter(give_dict))
            rate = 4  # default

            if any(self.nodes[n].port == '3:1' for n in player.settlements.union(player.cities)):
                rate = 3

            if any(self.nodes[n].port == f'2:1_{offered_resource}' for n in player.settlements.union(player.cities)):
                rate = 2

            if total_given != rate:
                print(f"Bank trade must give exactly {rate} of the same resource.")
                return

            if list(give_dict.keys()) != [offered_resource]:
                print("Bank trades must give one type of resource.")
                return

            if player.resources[offered_resource] < rate:
                print(f"Not enough {offered_resource}. Need {rate}.")
                return

            # Perform trade
            player.resources[offered_resource] -= rate
            received_resource = next(iter(get_dict))
            player.resources[received_resource] += 1

            print(f"Player {player_id} traded {rate} {offered_resource} for 1 {received_resource} with bank.")

        elif parts[0] == 'player':
            try:
                giver_id = int(parts[1])
                gives_index = parts.index('gives')
                gets_index = parts.index('gets')
                from_index = parts.index('from')
                receiver_id = int(parts[from_index + 1])

                giver = self.players[giver_id]
                receiver = self.players[receiver_id]
            except:
                print("Invalid player trade syntax.")
                return

            give_parts = parts[gives_index + 1 : gets_index]
            get_parts = parts[gets_index + 1 : from_index]

            give_dict, _ = self.parse_resource_list(give_parts)
            get_dict, _ = self.parse_resource_list(get_parts)

            # Check resource availability
            for res, amt in give_dict.items():
                if giver.resources[res] < amt:
                    print(f"Player {giver_id} lacks {amt} {res}.")
                    return
            for res, amt in get_dict.items():
                if receiver.resources[res] < amt:
                    print(f"Player {receiver_id} lacks {amt} {res}.")
                    return

            # Perform trade
            for res, amt in give_dict.items():
                giver.resources[res] -= amt
                receiver.resources[res] += amt
            for res, amt in get_dict.items():
                receiver.resources[res] -= amt
                giver.resources[res] += amt

            print(f"Player {giver_id} traded {give_dict} for {get_dict} from Player {receiver_id}.")

        else:
            print("Invalid trade command.")

    
    def show_hexes(self):
        print("=== HEXES ===")
        for i, hex in enumerate(self.hexes):
            print(f'hex {i}, {hex}')
    
    def activate_robber(self):
        print('robber activating')
        try:
            hex_index = int(input('enter index of hex to move the robber to (0-18): '))
        except ValueError:
            return False, 'please insert a number'
        if hex_index < 0 or hex_index >= len(self.hexes):
                return False, 'invalid tile index'
        for hex in self.hexes:
            hex.robber = False
        self.hexes[hex_index].robber = True
        print(f'robber now on tile {hex_index}: {self.hexes[hex_index]}')
        
        '''
        pick_player = int(input('player: '))
        player = self.player[pick_player]
        hex_tile = self.board.hexes[hex_index]
        targets = set()

        for node_id in hex_tile.node_ids:
            node = self.board.nodes[node_id]
            if node.owner is not None and node.owner != player.id:
                target_player = self.players[node.owner]
                if sum(target_player.resource.values()) > 0:
                    targets.add(target_player.id)

        if not targets:
            print('no players to steal from')
            return True, 'robber moved, no steal possible'
        
        print(f'players to steal from: {list(targets)}')
        try:
            target_id = int(input('enter ID of player to steal from'))
        except ValueError:
            return 'please enter number'
        if target_id not in targets:
            return False, 'invalid target'

        target = self.players[target_id]
        available_resources = [res for res, amt in target.resources.items() if amt > 0]
        if not available_resources:
            print('target has no resources')
            return True, 'robber moved, nothing stolen (target nothing to steal)'
        
        stolen = random.choice(available_resources)
        target.resources[stolen] -= 1
        player.resources[stolen] += 1
        print(f'stone 1 {stolen} from Player {target_id}')
        return True, f'robber moved and stole 1 {stolen} from Player {target_id}'
        '''

game1 = Tracker()