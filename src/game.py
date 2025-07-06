import random
from constants import RESOURCES, COSTS_CARD, DEV_DECK
from bot_play import Bot
from collections import deque

class Player:
    def __init__(self, player_id):
        self.id = player_id
        self.resources = {r: 0 for r in ['wood', 'ore', 'sheep', 'brick', 'wheat']}
        self.dev_cards = []
        self.unplayable_dev_cards = []
        self.played_knights = 0
        self.settlements = set()
        self.cities = set()
        self.roads = set()
        self.points = 0
        self.played_dev_this_turn = False
    
    def __repr__(self):
        return f'Player {self.id}'

class Game:
    def __init__(self, board, num_players=4):
        self.board = board
        self.players = [Player(i) for i in range(num_players)]
        self.current_player_turn = 0
        self.turn = 0
        self.dev_deck = self.create_dev_deck(DEV_DECK)
        self.history = []
        self.setup_phase = True
        self.largest_army_player_id = None
        self.longest_road_player_id = None


    #POTENTIAL PLAYER ACTIONS

    def build_settlement(self, player, node_id):
        node = self.board.nodes.get(node_id)
        if len(player.settlements) == 5:
            return False, 'out of settlements'
        if not node or not node.is_empty():
           
            return False, 'cannot build here (already built in)'
        if not self.setup_phase and not self.has_required_resources(player, COSTS_CARD['settlement']):
            #print(f"[BUILD FAIL] Player {player.id} lacks resources for settlement.")
            return False, 'not enough resources'
        for neighbor_id in node.connected_nodes:
            neighbor = self.board.nodes[neighbor_id]
            if neighbor.owner is not None:
                #print(f"[BUILD FAIL] Node {node_id} is too close to another building.")
                return False, 'cannot build here (too close)'
        if not self.setup_phase:
            connected = False
            for road in player.roads:
                if node_id in road:
                    connected = True
                    break
            if not connected:
                #print(f"[BUILD FAIL] Node {node_id} not connected by road.")
                return False, 'settlement must be connected to a road'

        self.spend_resources(player, COSTS_CARD['settlement'])
        node.owner = player.id
        node.building_type = 'settlement'
        player.settlements.add(node_id)
        player.points += 1
        #print(f"[BUILD SUCCESS] Player {player.id} built settlement at {node_id}")
        return True, 'settlement built'
        
    def build_city(self, player, node_id):
        node = self.board.nodes.get(node_id)
        if not node:
            return False, 'node does not exist'
        if node.building_type != 'settlement':
            return False, 'cannot build here (no settlement)'
        if node.owner != player.id:
            return False, 'not your settlement'
        if not self.has_required_resources(player, COSTS_CARD['city']):
            return False, 'not enough resources'
        
        self.spend_resources(player, COSTS_CARD['city'])
        node.building_type = 'city'
        
        player.cities.add(node_id)
        player.settlements.remove(node_id)
        player.points += 1
        return True, 'city built'
    
    def build_road(self, player, node1_id, node2_id, free=False):
        edge = self.find_edge(node1_id, node2_id)
        #print(f"[DEBUG] Attempting to build road between {node1_id} and {node2_id}")
        if not edge:
            #print(f"[DEBUG] Edge not found between {node1_id} and {node2_id}")
            return False, 'invalid edge'
        if edge.owner is not None:
            return False, 'road already built'

        # collect all nodes in the player's existing network
        network_nodes = set(player.settlements) | set(player.cities)
        for r in player.roads:
            # each r is a tuple like ('node_12','node_13')
            network_nodes |= set(r)

        # must attach at least one end of the new road to the network
        if node1_id not in network_nodes and node2_id not in network_nodes:
            #print(f"[DEBUG] Neither {node1_id} nor {node2_id} is in network {network_nodes}")
            return False, 'road must connect to your existing network'

        if not free:
            if not self.has_required_resources(player, COSTS_CARD['road']):
                return False, 'not enough resources'
            self.spend_resources(player, COSTS_CARD['road'])

        edge.owner = player.id
        player.roads.add(tuple(sorted((node1_id, node2_id))))
        self.check_longest_road()
        #print(f"[DEBUG] Player {player.id} built road from {node1_id} to {node2_id}")
        return True, 'road built'

    
    def buy_dev_card(self, player):
        if not self.dev_deck:
            return False, 'no development cards left'
        if not self.has_required_resources(player, COSTS_CARD['dev_card']):
            return False, 'not enough resources'
        
        self.spend_resources(player, COSTS_CARD['dev_card'])
        card = self.dev_deck.pop()
        if card == 'victory_point':
            player.points += 1
        player.unplayable_dev_cards.append(card)
        #print(f"Player {player.id} bought dev card: {card}")
        return True, f'{card} card acquired'

    def play_dev_card(self, player, card_type):
        if card_type not in player.dev_cards:
            return False, "can't play a card you don't own"
        if card_type in player.unplayable_dev_cards:
            return False, 'unplayable- already played a dev this turn, or just bought dev'
        if card_type == 'victory_point':
            return False, 'cannot activate vp'
       
        if card_type == 'knight':
            player.played_knights += 1
            self.activate_robber(player)
            return True, f'{card_type} played, robber moved'
        elif card_type == 'monopoly':
            self.play_monopoly(player)
            return True, f'{card_type} played, cards stolen'
        elif card_type == 'year_of_plenty':
            self.play_yop_bot(player)
            return True, f'{card_type} played, gained 2 resources'
        elif card_type == 'road_building':
            self.play_rb_bot(player)
            return True, f'{card_type} played, 2 roads built'
    
    def play_dev_card_bot(self, player, card_type, mono_res = None, yop_res1 = None, yop_res2 = None, road_pair = None, hex_index = None, target_id = None):
        if card_type not in player.dev_cards:
            return False, "can't play a card you don't own"
        if card_type in player.unplayable_dev_cards:
            return False, 'unplayable- already played a dev this turn, or just bought dev'
        if card_type == 'victory_point':
            return False, 'cannot activate vp'
       
        if card_type == 'knight':
            player.played_knights += 1
            self.activate_robber_bot(player, hex_index, target_id)
            return True, f'{card_type} played, robber moved'
        elif card_type == 'monopoly':
            self.play_monopoly_bot(player, mono_res)
            return True, f'{card_type} played, cards stolen'
        elif card_type == 'year_of_plenty':
            self.play_yop_bot(player, yop_res1, yop_res2)
            return True, f'{card_type} played, gained {yop_res1, yop_res2}'
        elif card_type == 'road_building':
            self.play_rb_bot(player, road_pair)
            return True, f'{card_type} played, 2 roads built'


        player.dev_cards.remove(card_type)
        for card in player.dev_cards:
            player.unplayable_dev_cards.append(card)
        player.dev_cards.clear()
    
    def play_rb(self, player):
        #print('road building player')

        for i in range(2):
            #print(f'placing road {i+1}')
            node1 = input('first node id')
            node2 = input('second id')

            success, message = self.build_road(player, node1, node2, free = True)
            #print(message)
            if not success:
                #print('try again with valid road')
                pass
    
    def play_rb_bot(self, player, road_pair):
        if road_pair is None:
            return
        for node1, node2 in road_pair:
            self.build_road(player, node1, node2, free=True)

    def play_monopoly(self, player):
        #print('monopoly has been played')
        resource = input('enter resource:').strip().lower()
        if resource not in RESOURCES:
            return False, 'invalid resource'
        
        total_stolen = 0
        for other in self.players:
            if other.id == player.id:
                continue
            amount = other.resources.get(resource, 0)
            if amount > 0:
                player.resources[resource] += amount
                other.resources[resource] = 0
                total_stolen += amount
                #print(f'stole {amount} {resource} from Player {other.id}')
        
        
        return True, f'mono on {resource} successful'
    
    def play_monopoly_bot(self, player, resource):
        if resource not in RESOURCES:
            return

        total_stolen = 0
        for other in self.players:
            if other.id == player.id:
                continue
            amount = other.resources.get(resource, 0)
            if amount > 0:
                player.resources[resource] += amount
                other.resources[resource] = 0
                total_stolen += amount

        #print(f"Player {player.id} played Monopoly on {resource}, stole {total_stolen}")
        return True, f'Monopoly on {resource} complete'
    
    def play_yop(self, player):
        #print('choose 2 resources')
        res1 = input('first resource: ').strip().lower()
        res2 = input('second resource: ').strip().lower()

        if res1 not in RESOURCES or res2 not in RESOURCES:
            return False, 'invalid resource(s)'
        
        player.resources[res1] += 1
        player.resources[res2] += 1

        #print(f'you gained {res1} and {res2}')
        return True, 'Year of Plenty successful'
    
    def play_yop_bot(self, player, res1, res2):
        if res1 not in RESOURCES or res2 not in RESOURCES:
            return

        player.resources[res1] += 1
        player.resources[res2] += 1

        #print(f"Player {player.id} gained 1 {res1} and 1 {res2} (Year of Plenty)")
        return True, 'Year of Plenty played successfully'
    
    def trade_with_bank(self, player, give, get):
        if give not in RESOURCES or get not in RESOURCES:
            return False, 'invalid resource'
        if give == get:
            return False, 'cannot trade for same resource'
        rate = 4
        
        has_3to1 = False
        for node_id in player.settlements.union(player.cities):
            if self.board.nodes[node_id].port == '3:1':
                has_3to1 = True
                break
        if has_3to1:
            rate = 3
        specific_port = f'2:1_{give}'
        has_2to1 = False
        for node_id in player.settlements.union(player.cities):
            if self.board.nodes[node_id].port == specific_port:
                has_2to1 = True
                break
        if has_2to1:
            rate = 2
        
        if player.resources[give] < rate:
            return False, f'not engouh {give} (need {rate}) to trade'
        
        player.resources[give] -= rate
        player.resources[get] += 1

        return True, f'traded {rate} {give} for 1 {get}'

    def propose_trade(self, proposer, reciever, offer: dict, request: dict):
        for res, amt in offer.items():
            if proposer.resources.get(res, 0) < amt:
                return False, f'do not have enough {res} to offer'

        #print(f'player {proposer.id} if proposing trade: offering {offer}')
        #print(f'in exchange for {request}')

        accept = input(f'Player {reciever.id}, do you accept? y/n: ')
        if accept != 'y':
            return False, 'trade rejected'
        
        for res, amt in offer.items():
            proposer.resources[res] -= amt
            reciever.resources[res] += amt

        for res, amt in request.items():
            proposer.resources[res] -= amt
            reciever.resources[res] += amt
        
        return True, f'trade between player {proposer.id} and {reciever.id} of {offer} for {request} completed'







    #HELPER FUNCTIONS
    #Basically I suspect the bottom one is some ass so I'm putting this one in, unclear if it's like that
    def find_longest_road(self, player):
        board = self.board
        player_edges = set()

        # Collect all edges owned by the player
        for edge in board.edges:
            if edge.owner == player.id:
                player_edges.add((edge.node1.id, edge.node2.id))

        longest_path = []
        max_length = 0

        # DFS helper to explore paths
        def dfs(current, visited_edges, path):
            nonlocal longest_path, max_length

            if len(path) > max_length:
                max_length = len(path)
                longest_path = path[:]

            for neighbor in board.nodes[current].connected_nodes:
                edge = tuple(sorted((current, neighbor)))
                if edge in player_edges and edge not in visited_edges:
                    # Stop at enemy settlements
                    if board.nodes[neighbor].owner not in (None, player.id):
                        continue

                    visited_edges.add(edge)
                    path.append(neighbor)
                    dfs(neighbor, visited_edges, path)
                    path.pop()
                    visited_edges.remove(edge)

        # Try DFS starting from every node connected to a road
        nodes_in_roads = set()
        for edge in player_edges:
            nodes_in_roads.update(edge)

        for node in nodes_in_roads:
            dfs(node, set(), [node])

        return longest_path, max_length

    #DFS ALGORITHM
    def get_longest_road_length(self, player):
        max_length = 0

        def dfs(node_id, length, visited):
            nonlocal max_length
            max_length = max(max_length, length)

            for neighbor_id in self.board.nodes[node_id].connected_nodes:
                edge = tuple(sorted((node_id, neighbor_id)))
                if edge in player.roads and edge not in visited:
                    visited.add(edge)
                    dfs(neighbor_id, length + 1, visited)
                    visited.remove(edge)

        all_nodes = set()
        for road in player.roads:
            all_nodes.update(road)

        for start_node in all_nodes:
            dfs(start_node, 0, set())
        
        return max_length

    def check_longest_road(self):
        #  ── Debug snapshot ──
        #print(f"[DEBUG:Road] Current holder: {self.longest_road_player_id}")
        lengths = {}
        for p in self.players:
            length = self.get_longest_road_length(p)
            lengths[p.id] = length
            #print(f"[DEBUG:Road] Player {p.id} road length={length} pts={p.points}")

        # Must have at least 5 edges
        best_id, best_len = max(lengths.items(), key=lambda kv: kv[1])
        if best_len < 5:
            #print("[DEBUG:Road] No one has 5+ roads yet")
            return

        if best_id != self.longest_road_player_id:
            if self.longest_road_player_id is not None:
                old = next(pl for pl in self.players if pl.id == self.longest_road_player_id)
                old.points -= 2
                #print(f"[DEBUG:Road] Player {old.id} loses Longest Road (-2)")
            new = next(pl for pl in self.players if pl.id == best_id)
            new.points += 2
            self.longest_road_player_id = best_id
            #print(f"[DEBUG:Road] Player {best_id} takes Longest Road length={best_len} (+2)")

    def game_over(self):
        return any(player.points >= 10 for player in self.players)
    
    def check_largest_army(self):
        #  ── Debug snapshot ──
        #print(f"[DEBUG:Army] Current holder: {self.largest_army_player_id}")
        

        #  ── Find best candidate ──
        # Must have at least 3 knights
        best = None
        best_knights = 2
        for p in self.players:
            if p.played_knights > best_knights:
                best_knights = p.played_knights
                best = p

        if not best:
            #print("[DEBUG:Army] No one has 3+ knights yet")
            return

        #  ── Award if changed ──
        if best.id != self.largest_army_player_id:
            if self.largest_army_player_id is not None:
                old = next(pl for pl in self.players if pl.id == self.largest_army_player_id)
                old.points -= 2
                #print(f"[DEBUG:Army] Player {old.id} loses Largest Army (-2)")
            best.points += 2
            self.largest_army_player_id = best.id
            #print(f"[DEBUG:Army] Player {best.id} takes Largest Army (+2)")

    def handle_robber_roll(self, player):
        #print('7 rolled!')
        for player in self.players:
            total_cards = sum(player.resources.values())
            if total_cards > 7:
                to_discard = total_cards // 2
                #print(f'player {player.id} has {total_cards} cards and must discard {to_discard}.')
            
                while to_discard > 0:
                    #print(f'resources: {player.resources}')
                    res = input(f'pick resource to discard')
                    if res not in RESOURCES or player.resources.get(res,0) == 0:
                        #print('invalid')
                        continue
                    player.resources[res] -= 1
                    to_discard -= 1
                    #print(f'discarded 1 {res}')

        message = self.activate_robber(player)
        #print(message)

    def handle_robber_roll_bot(self, player):
        #print('7 rolled!')

        for p in self.players:
            total_cards = sum(p.resources.values())
            if total_cards > 7:
                to_discard = total_cards // 2
                #print(f'Bot {p.id} has {total_cards} cards and must discard {to_discard}.')

                # Discard highest-count resources first
                res_counts = sorted(p.resources.items(), key=lambda x: -x[1])
                for res, count in res_counts:
                    if to_discard == 0:
                        break
                    discard_amt = min(count, to_discard)
                    p.resources[res] -= discard_amt
                    to_discard -= discard_amt
                    #print(f'Bot {p.id} discarded {discard_amt} {res}')

        # Robber move: use bot's targeting function
        if hasattr(player, 'bot'):
            target_id, hex_index = player.bot.choose_rob_target(self.board, self, player)
            success, msg = self.activate_robber_bot(player, hex_index, target_id)
        else:
            success, msg = self.activate_robber(player)

        #print(msg)
        return success


    def activate_robber(self, player):
        #print('robber activating')
        try:
            hex_index = int(input('enter index of hex to move the robber to (0-18)'))
        except ValueError:
            return False, 'please insert a number'
        if hex_index < 0 or hex_index >= len(self.board.hexes):
                return False, 'invalid tile index'
        for hex in self.board.hexes:
            hex.robber = False
        self.board.hexes[hex_index].robber = True
        #print(f'robber now on tile {hex_index}: {self.board.hexes[hex_index]}')
        
        hex_tile = self.board.hexes[hex_index]
        targets = set()

        for node_id in hex_tile.node_ids:
            node = self.board.nodes[node_id]
            if node.owner is not None and node.owner != player.id:
                target_player = self.players[node.owner]
                if sum(target_player.resource.values()) > 0:
                    targets.add(target_player.id)

        if not targets:
            #print('no players to steal from')
            return True, 'robber moved, no steal possible'
        
        #print(f'players to steal from: {list(targets)}')
        try:
            target_id = int(input('enter ID of player to steal from'))
        except ValueError:
            return 'please enter number'
        if target_id not in targets:
            return False, 'invalid target'

        target = self.players[target_id]
        available_resources = [res for res, amt in target.resources.items() if amt > 0]
        if not available_resources:
            #print('target has no resources')
            return True, 'robber moved, nothing stolen (target nothing to steal)'
        
        stolen = random.choice(available_resources)
        target.resources[stolen] -= 1
        player.resources[stolen] += 1
        #print(f'stone 1 {stolen} from Player {target_id}')
        return True, f'robber moved and stole 1 {stolen} from Player {target_id}'
    
    def activate_robber_bot(self, player, hex_index, target_id=None):
        if hex_index < 0 or hex_index >= len(self.board.hexes):
            return False, 'Invalid tile index'

        # Remove the robber from all tiles
        for hex in self.board.hexes:
            hex.robber = False

        # Set robber on the new tile
        self.board.hexes[hex_index].robber = True
        #print(f'Robber now on tile {hex_index}: {self.board.hexes[hex_index]}')

        hex_tile = self.board.hexes[hex_index]
        targets = set()

        for node_id in hex_tile.node_ids:
            node = self.board.nodes[node_id]
            if node.owner is not None and node.owner != player.id:
                target_player = self.players[node.owner]
                if sum(target_player.resources.values()) > 0:
                    targets.add(target_player.id)

        if not targets:
            #print('No players to steal from')
            return True, 'Robber moved, no steal possible'

        # If a valid target_id was passed and is in the target list, use it. Otherwise, pick one randomly.
        if target_id not in targets:
            target_id = random.choice(list(targets))

        target = self.players[target_id]
        available_resources = [res for res, amt in target.resources.items() if amt > 0]
        if not available_resources:
            #print('Target has no resources')
            return True, 'Robber moved, but nothing stolen (target had nothing)'

        stolen = random.choice(available_resources)
        target.resources[stolen] -= 1
        player.resources[stolen] += 1
        #print(f'Stole 1 {stolen} from Player {target_id}')
        return True, f'Robber moved and stole 1 {stolen} from Player {target_id}'
    
    def has_required_resources(self, player, cost_dict):
        return all(player.resources.get(res,0) >= amt for res, amt in cost_dict.items())
    
    def spend_resources(self, player, cost_dict):
        for res, amt in cost_dict.items():
            player.resources[res] -= amt

    def find_edge(self, node1_id, node2_id):
        for edge in self.board.edges:
            if {edge.node1.id, edge.node2.id} == {node1_id, node2_id}:
                return edge
        return None

    def are_nodes_connected(self, node_id, road_tuple):
        return node_id in road_tuple
    
    def print_player_resources(self, player):
        print(f"Player {player.id} resources: {player.resources}")

    def manual_initial_placement(self, player):
        #print(f'place settlement and road for Player {player.id}')
        # will eventually connect to UI or bot strategy
        node_id = input('enter node_id for settlement: ')
        road_node = input('Enter adjacent node for road: ')
        self.place_initial_settle_and_road(player, node_id, road_node)

    def distribute_starting_resources(self, player):
        last_node = list(player.settlements)[-1]
        for hex_id, hex_tile in enumerate(self.board.hexes):
            if last_node in hex_tile.node_ids and hex_tile.resource:
                if hex_tile.resource not in RESOURCES:
                    continue
                else:
                    player.resources[hex_tile.resource] += 1

    #GAMEPLAY LOOP

    def roll_dice(self):
        d1 = random.randint(1,6)
        d2 = random.randint(1,6)
        return d1 + d2
    
    def distribute_resources(self, roll):
        for hex in self.board.hexes:
            if hex.dice_number != roll or hex.robber:
                continue

            for node_id in hex.node_ids:
                node = self.board.nodes[node_id]
                if node.owner is not None:
                    player = self.players[node.owner]
                    amount = 2 if node.building_type == 'city' else 1
                    player.resources[hex.resource] += amount


    def create_dev_deck(self, dev_deck):
        deck = dev_deck.copy()
        random.shuffle(deck)
        return deck
    
    def get_port_rate(self, player, resource):
        """
        Returns the best port rate for trading away `resource`:
          - 2 if player has a 2:1 port for that resource
          - 3 if player has any 3:1 port
          - None if neither (caller should treat that as 4)
        """
        # 1) First look for a specific 2:1 port
        for nid in player.settlements | player.cities:
            port = self.board.nodes[nid].port  # e.g. "2:wood", "3:1", or None
            if port and port.startswith(f"2:{resource}"):
                return 2

        # 2) Then look for any 3:1 port
        for nid in player.settlements | player.cities:
            port = self.board.nodes[nid].port
            if port == "3:1":
                return 3

        # 3) No special port—caller will use 4:1
        return None

    def start_placement_rounds(self):
        for player in self.players:
            self.manual_initial_placement(player)
        for player in reversed(self.players):
            self.manual_initial_placement(player)
            self.distribute_starting_resources(player)
        self.setup_phase = False

    def place_initial_settle_and_road(self, player, node_id, road_target_id):
        node = self.board.nodes.get(node_id)
        edge = self.find_edge(node_id, road_target_id)

        if not node or not node.is_empty():
            return False, 'settle already built'
        if not edge or edge.owner is not None:
            return False, 'invalid road location'
        
        node.owner = player.id
        node.building_type = 'settlement'
        edge.owner = player.id
        player.settlements.add(node_id)
        player.roads.add(tuple(sorted((node_id, road_target_id))))
        player.points += 1
        return True, 'first settle placed'
    

    def check_win(self):
        for player in self.players:
            if player.points >= 10:
                self.winner = player.id
                self.game_over = True
                return player
    
    def advance_turn(self):
        player = self.players[self.current_player_turn]
        player.dev_cards += player.unplayable_dev_cards
        player.unplayable_dev_cards = []
        self.current_player_turn = (self.current_player_turn + 1) % len(self.players)

    def get_edge(self, node1_id, node2_id):
        node_pair = tuple(sorted((node1_id, node2_id)))
        for edge in self.board.edges:
            if {edge.node1.id, edge.node2.id} == set(node_pair):
                return edge
        return None

    def find_available_nodes(self):
        available = []
        for node_id, node in self.board.nodes.items():
            if node.owner is not None:
                continue

            neighbors = self.board.nodes[node_id].connected_nodes
            if any(self.board.nodes[n_id].owner is not None for n_id in neighbors):
                continue

            available.append(node_id)

        return available
    
    def valid_node(self, node_id, player_id=None):
        """Returns True if the node is a valid place to build a settlement (unoccupied, and all neighbors are unoccupied)."""
        if node_id not in self.board.nodes:
            return False

        node = self.board.nodes[node_id]
        
        # Node must be empty
        if node.owner is not None:
            return False

        # All neighboring nodes must also be unoccupied
        for neighbor_id in node.connected_nodes:
            neighbor = self.board.nodes[neighbor_id]
            if neighbor.owner is not None:
                return False

        return True
    
    def distance_between_nodes(self, start_id, target_id, player_id=None):

        visited = set()
        queue = deque([(start_id, 0)])

        while queue:
            current, dist = queue.popleft()
            if current == target_id:
                return dist
            if current in visited:
                continue
            visited.add(current)

            for neighbor in self.board.nodes[current].connected_nodes:
                edge = tuple(sorted((current, neighbor)))
                edge_obj = next((e for e in self.board.edges if {e.node1.id, e.node2.id} == set(edge)), None)

                if edge_obj is None:
                    continue

                if edge_obj.owner is None or (player_id and edge_obj.owner != player_id):
                    continue

                queue.append((neighbor, dist + 1))

        return float('inf')  # unreachable
    
    def take_turn(self):
        player = self.players[self.current_player_turn]
        self.turn += 1

        roll = self.roll_dice()
        if roll == 7:
            self.handle_robber_roll(player)
        else:
            self.distribute_resources(roll)
        

        self.take_player_actions(player)

        self.check_win(player)
        self.advance_turn()

    def pick_random_settle(self, taken_nodes):
        all_node_list = [f'node_{i}' for i in range(54)]
        remaining_nodes = list(set(all_node_list) - set(taken_nodes))


        return random.choice(remaining_nodes)

        