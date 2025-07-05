import constants
from itertools import combinations
import random
from collections import deque
from board import Board
from collections import defaultdict

random.seed(42)


SCORING_WEIGHTS = {
    'single_pips>11': .06,
    'single_pips<=11>=9': .04,
    'single_pips<=7_penalty': 1.365, 
    'scarce_res_bonus': .02, 
    'scarce_res_2pips': 0, 
    'scarce_res_2pips+corner': .05,
    'scarce_res_3pips':.05,
    'scarce_res_3pips+corner': .05, 
    'scarce_res>4pips': .1, 
    'scarce_res>4pips_corner': .05, 
    'no_ports': -.1, 
    '1_port':.075,
    '2_ports': .075,
    'port_synergy': .1,
    'number_diversity': .05,
    'resource_synergy': .1,
    'ore_check': .735, #fix this logic so its proportonal to amount of pre pips
    '3hexes': -1.31,

    '2spot_pips>10.3': .4,
    '2spot_pips<=10.3>=9': .3,
    '2spot_number_diversity=5': .1,
    '2spot_number_diversity=6': .2,
    '2spot_port_synergy': .15,
    '2spot_settle_spot': .1,

    'OWS': 1.14,
    'OWS_ratio_bonus_magnifier': .005,
    'OWS_HYBRID': 1.83,
    'ROAD': 1.1,
    'ROAD_settle_spot_magnifier': .005,
    'CITIES&ROADS': .5,
    'CITIES&ROADS_balance_score': .005,
    'BALANCED': 1.5,
    'PORT': .59, #want to add some kind of increase based on pips, maybe on possible pips too
    'PRODUCTION': .12

}



class Bot:
    def __init__(self, player_id, total_players):
        self.player_id = player_id
        self.total_players = total_players
        self.strategy = ''


    #this is going to be my 'evaluate nodes and pick' function, going to also dictate strategy for the actual game playing
    
    def choose_first_placement(self, board, taken_nodes):

        placement_scores = {}
        node_pairs = combinations(sorted(board.nodes.keys()), 2)

        for node1_id, node2_id in node_pairs:
            if not self.valid_settlement_pair(node1_id, node2_id, board):
                continue
            if node1_id in taken_nodes or node2_id in taken_nodes:
                continue
        

            score1 = self.score_node(node1_id, board)
            score2 = self.score_node(node2_id, board)
            synergy = self.score_node_synergy(node1_id, node2_id, board)
            total_score = score1 + score2 + synergy

            placement_scores[(node1_id, node2_id)] = (total_score, score1, score2)

        for (node1_id, node2_id), (total_score, score1, score2) in sorted(placement_scores.items(), key=lambda x: x[1][0], reverse=True):
            simulated = self.simulate_opponent_picks(board, taken_nodes={node1_id})
            if node2_id not in simulated:
                return node1_id if score1 >= score2 else node2_id

        # Fallback
        best_pair, (total_score, score1, score2) = max(placement_scores.items(), key=lambda x: x[1][0])
        return best_pair[0] if score1 >= score2 else best_pair[1]

    def choose_second_placement(self, board, first_node_id, taken_nodes):
        best_node2 = None
        best_score = float('-inf')

        for node2_id in board.nodes.keys():
            if not self.valid_settlement_pair(first_node_id, node2_id, board):
                
                continue
            if node2_id in taken_nodes:
                
                continue

            score1 = self.score_node(first_node_id, board)
            score2 = self.score_node(node2_id, board)
            synergy = self.score_node_synergy(first_node_id, node2_id, board)
            total_score = score1 + score2 + synergy
            
            if total_score > best_score:
                best_score = total_score
                best_node2 = node2_id

        
        return best_node2


    def choose_road_after_settlement(self, board, node_id, player_id):
        def get_nodes_within_distance(start_node, max_dist=2):
            visited = set()
            queue = deque([(start_node, 0)])
            nodes_within = set()

            while queue:
                current, dist = queue.popleft()
                if dist > max_dist or current in visited:
                    continue
                visited.add(current)
                nodes_within.add(current)
                for neighbor in board.nodes[current].connected_nodes:
                    queue.append((neighbor, dist + 1))
            nodes_within.discard(start_node)
            return nodes_within

        def get_port_resource(port_str):
            if '_' in port_str:
                return port_str.split('_')[1]
            return None

        def get_resource_synergy(resource, node_id):
            pip_total = 0
            node = board.nodes[node_id]
            for hex_idx in node.adj_hexes:
                hex_obj = board.hexes[hex_idx]
                if hex_obj.resource == resource and hex_obj.dice_number is not None:
                    pip_total += constants.PIP_WEIGHTS[hex_obj.dice_number]
            return pip_total

        def is_valid_future_settle(target_node):
            if board.nodes[target_node].owner is not None:
                return False
            for neighbor in board.nodes[target_node].connected_nodes:
                if board.nodes[neighbor].owner is not None:
                    return False
            return True

        neighbors = board.nodes[node_id].connected_nodes
        port_nodes = [n for n in get_nodes_within_distance(node_id, 2) if board.nodes[n].port is not None]

        if port_nodes:
            if len(port_nodes) == 1:
                # One reachable port: go toward it
                target = port_nodes[0]
            else:
                # Pick port with most synergy
                best_port = None
                best_score = -1
                for pn in port_nodes:
                    port = board.nodes[pn].port
                    res = get_port_resource(port)
                    if res:
                        score = get_resource_synergy(res, node_id)
                        if score > best_score:
                            best_score = score
                            best_port = pn
                target = best_port

            # Move one step toward the port
            for neighbor in neighbors:
                if target in get_nodes_within_distance(neighbor, 1):
                    return neighbor

        # No ports: expand toward best future settle
        best_neighbor = None
        best_score = -1
        for neighbor in neighbors:
            if not is_valid_future_settle(neighbor):
                continue
            score = self.score_node(neighbor, board)
            if score > best_score:
                best_score = score
                best_neighbor = neighbor

        return best_neighbor







    def score_node(self, node_id, board):
        node_score = 0
        resource_scores = self.analyze_resources(board)
        #for res in constants.RESOURCES:
            #print(f'{res} is {resource_scores[res]}')
        pipscore = self.score_pips(node_id, board)
        #print(f'pipscore = {pipscore}')
        
        #PIPSCORE: might have to put this as an average of the two spots, idk
        if pipscore > 11:
            node_score += SCORING_WEIGHTS['single_pips>11']
            #print(f'pips > 11: node_score + {SCORING_WEIGHTS['single_pips>11']} = {node_score}')
        elif pipscore <= 11 and pipscore >= 9:
            node_score += SCORING_WEIGHTS['single_pips<=11>=9']
        elif pipscore <= 7:
            node_score -= SCORING_WEIGHTS['single_pips<=7_penalty']
            #print(f'pips between 11 and 9: node_score + {SCORING_WEIGHTS['single_pips<=11>=9']} = {node_score}')
        
        #SCARCE RESOURCES
        scarce_resources_seen = set()
        for hex in board.nodes[node_id].adj_hexes:
            hex_obj = board.hexes[hex]
            corner_check = self.check_corner(hex_obj)
            if hex_obj.resource == 'desert':
                continue
            if resource_scores[hex_obj.resource] == 'scarce' and hex_obj.resource not in scarce_resources_seen:
                node_score += SCORING_WEIGHTS['scarce_res_bonus']
                scarce_resources_seen.add(hex_obj.resource)
                #print(f'scarce resource bonus: node_score + {SCORING_WEIGHTS['scarce_res_bonus']} = {node_score}')
                if constants.PIP_WEIGHTS[hex_obj.dice_number] == 2:
                    node_score += SCORING_WEIGHTS['scarce_res_2pips']
                    #print(f'scarce resource w/ small produc: node_score + {SCORING_WEIGHTS['scarce_res_2pips']} = {node_score}')
                    if corner_check:
                        node_score += SCORING_WEIGHTS['scarce_res_2pips+corner']
                        #print(f'also with corner: node_score + {SCORING_WEIGHTS['scarce_res_2pips+corner']} = {node_score}')
                if constants.PIP_WEIGHTS[hex_obj.dice_number] == 3:
                    node_score += SCORING_WEIGHTS['scarce_res_3pips']
                    #print(f'scarce w/ decent produc node_score + {SCORING_WEIGHTS['scarce_res_3pips']} = {node_score}')
                    if corner_check:
                        node_score += SCORING_WEIGHTS['scarce_res_3pips+corner']
                        #print(f'again with corner: node_score + {SCORING_WEIGHTS['scarce_res_3pips+corner']} = {node_score}')
                if constants.PIP_WEIGHTS[hex_obj.dice_number] >= 4:
                    node_score += SCORING_WEIGHTS['scarce_res>4pips']
                    #print(f'high production for scarce resource: node_score + {SCORING_WEIGHTS['scarce_res>4pips']} = {node_score}')
                    if corner_check:
                        node_score += SCORING_WEIGHTS['scarce_res>4pips+corner']
                        #print(f'again with corner: node_score + {SCORING_WEIGHTS['scarce_res>4pips+corner']} = {node_score}')

        #PORTS
        ports = self.check_port(node_id, board)
        #print(f'ports: {len(ports)}')
        #print(ports)
        if len(ports) == 0:
            node_score -= SCORING_WEIGHTS['no_ports']
            #print(f'no ports: score {SCORING_WEIGHTS['no_ports']} = {node_score}')
        if len(ports) == 1:
            node_score += SCORING_WEIGHTS['1_port']
            #print(f'1 port: + {SCORING_WEIGHTS['1_port']}= {node_score}')
        elif len(ports) == 2:
            node_score += SCORING_WEIGHTS['2_ports']
            #print(f'2 ports: node_score + {SCORING_WEIGHTS['2_ports']} = {node_score}')
        syn_check_ports = self.check_port_synergy(node_id, board)
        if syn_check_ports:
            node_score += SCORING_WEIGHTS['port_synergy']
            #print(f'syn port: node_score + {SCORING_WEIGHTS['port_synergy']} = {node_score}')

        #NUM DIVERSITY
        if self.check_num_diversity(node_id, board):
            node_score += SCORING_WEIGHTS['number_diversity']
            #print(f'number diversity: node_score + {SCORING_WEIGHTS['number_diversity']} = {node_score}')
        #print(f'node_score = {node_score}')
    
        #GENERAL SYNERGY CHECK
        if self.check_res_synergy(node_id, board):
            node_score += SCORING_WEIGHTS['resource_synergy']
            #print(f'resource synergy: node_score + {SCORING_WEIGHTS['resource_synergy']} = {node_score}')

        if self.ore_check(node_id, board) and resource_scores['wheat'] != 'scarce':
            node_score += SCORING_WEIGHTS['ore_check']
            #print(f'decent ore: node_score + {SCORING_WEIGHTS['ore_check']} = {node_score}')
        
        if self.threehex_check(node_id, board) == 3:
            node_score += SCORING_WEIGHTS['3hexes']
        
        return node_score
    
        


    def score_node_synergy(self, node1_id, node2_id, board):
        '''
        general: 
        - additional number diversity DONE
        - additional port synergy
        - additional pip check DONE

        strategy:
        - Port strategy?
        - Add a production + build to the spot where you round your setup out? (Hard)
        '''
        
        #PIPSCORE
        setup_score = 0

        pipscore = self.score_pips(node1_id, board, node2_id) / 2
        if pipscore > 10.3:
            setup_score += SCORING_WEIGHTS['2spot_pips>10.3']
            #print(f'pips > 11: node_score + {SCORING_WEIGHTS['2spot_pips>10.3']} = {setup_score}')
        elif pipscore <= 10.3 and pipscore >= 9:
            setup_score += SCORING_WEIGHTS['2spot_pips<=10.3>=9']
            #print(f'pips between 11 and 9: node_score + {SCORING_WEIGHTS['2spot_pips>10.3>=9']} = {setup_score}')
        
        #NUMBER DIVERSITY
        numbers = self.check_num_diversity(node1_id, board, node2_id)
        if numbers == 5:
            setup_score += SCORING_WEIGHTS['2spot_number_diversity=5']
            #print(f'setup pips: + {SCORING_WEIGHTS['2spot_number_diversity=5']} = {setup_score}')
        if numbers == 6:
            setup_score += SCORING_WEIGHTS['2spot_number_diversity=6']
            #print(f'setup pips: + {SCORING_WEIGHTS['2spot_number_diversity=6']} = {setup_score}')

        
        #Port Synergy Check
        port_synergy = self.check_port_synergy_dual(node1_id, node2_id, board)
        if port_synergy:
            setup_score += SCORING_WEIGHTS['2spot_port_synergy']
            #print(f'setup pips: + {SCORING_WEIGHTS['2spot_port_synergy']} = {setup_score}')
        
        #STRATEGIES
            
        #OWS:
        if self.is_ows_setup(node1_id, node2_id, board):
            self.strategy = 'OWS'
            setup_score += SCORING_WEIGHTS['OWS']
            setup_score += self.ows_pip_balance_score(node1_id, node2_id, board)
            if self.check_settle_spot(board, {node1_id, node2_id}):
                setup_score += SCORING_WEIGHTS['2spot_settle_spot']

        #OWS Hybrid
        elif self.is_ows_hybrid_setup(node1_id, node2_id, board):
            self.strategy = 'OWS_HYBRID'
            setup_score += SCORING_WEIGHTS['OWS_HYBRID']
            if self.check_settle_spot(board, {node1_id, node2_id}):
                setup_score += SCORING_WEIGHTS['2spot_settle_spot']

        #Road (figure out this settlement logic, also add bonus for ore close)
        elif self.is_road_setup(node1_id, node2_id, board):
            self.strategy = 'ROAD'
            setup_score += SCORING_WEIGHTS['ROAD']

            road_spots = self.find_accessible_settle_spots(board, [node1_id, node2_id])
            setup_score += len(road_spots) * SCORING_WEIGHTS['ROAD_settle_spot_magnifier']

        #cities and roads (add bonus for sheep close):
        elif self.is_city_and_roads_setup(node1_id, node2_id, board):
            self.strategy = 'CITIES&ROADS'
            setup_score += SCORING_WEIGHTS['CITIES&ROADS'] 
            setup_score += self.city_and_roads_balance_score(node1_id, node2_id, board)

        #balanced
        elif self.is_balanced_setup(node1_id, node2_id, board):
            self.strategy = 'BALANCED'
            setup_score += SCORING_WEIGHTS['BALANCED']
            if self.check_settle_spot(board, {node1_id, node2_id}):
                setup_score += SCORING_WEIGHTS['2spot_settle_spot']

        #port setup
        elif self.is_port_setup(node1_id, node2_id, board):
            self.strategy = 'PORT'
            setup_score += SCORING_WEIGHTS['PORT']
        
        else:
            self.strategy = 'PRODUCTION'
            setup_score += SCORING_WEIGHTS['PRODUCTION']
        
        return setup_score

    
    
    
    #these are functions to help determine picking order & nodes
    
    
    #add randomness to this function!
    def simulate_opponent_picks(self, board, taken_nodes, m=2):
        k = self.opponents_before_second_pick()
        open_nodes = self.generate_candidate_nodes(board, exclude_nodes=taken_nodes)
        # score every open node
        scored = [(n, self.score_node(n, board)) for n in open_nodes]
        # sort descending by score
        scored.sort(key=lambda x: (-x[1], x[0]))
        # take the top k+m candidates
        top_candidates = [n for n,_ in scored[: k + m]]
        # if there are fewer than k+m, we'll just sample from whatever we have:
        picks = set(random.sample(top_candidates, min(k, len(top_candidates))))
        return picks
    
    def opponents_before_second_pick(self):
        if self.player_id == 0:
            return 6
        elif self.player_id == 1:
            return 4
        elif self.player_id == 2:
            return 2
        elif self.player_id == 3:
            return 0
        else:
            raise ValueError("Invalid turn position")
            
    def generate_candidate_nodes(self, board, exclude_nodes = None):
        #allow for some nodes to be blocked off
        if exclude_nodes is None:
            exclude_nodes = set()
        
        valid_nodes = []

        for node_id, node in board.nodes.items():
            if node.owner is not None or node_id in exclude_nodes:
                continue
            
            neighbors = board.nodes[node_id].connected_nodes
            if any(board.nodes[n_id].owner is not None or n_id in exclude_nodes for n_id in neighbors):
                continue

            valid_nodes.append(node_id)
        
        return valid_nodes
    
    
    













    
    
    
    #These are helper functions for node scoring
    
    def check_num_diversity(self, node_id, board, node_id2 = None):
        dice_numbers = set()
        for hex in board.nodes[node_id].adj_hexes:
            hex_obj = board.hexes[hex]
            if hex_obj.resource != 'desert':
                dice_numbers.add(hex_obj.dice_number)
        if node_id2:
            for hex in board.nodes[node_id2].adj_hexes:
                hex_obj = board.hexes[hex]
                if hex_obj.resource != 'desert':
                    dice_numbers.add(hex_obj.dice_number)
            return len(dice_numbers)
        return len(dice_numbers) == 3
    

    def check_res_synergy(self, node_id, board):
        resources = set()
        for hex_index in board.nodes[node_id].adj_hexes:
            hex_obj = board.hexes[hex_index]
            resources.add(hex_obj.resource)

        for pair in constants.SYNERGY_RESOURCES:
            if all(res in resources for res in pair):
                return True
        return False

    def check_port(self, node_id, board):
        ports = set()
        for hex in board.nodes[node_id].adj_hexes:
            hex_obj = board.hexes[hex]
            for id in hex_obj.node_ids:
                node = board.nodes[id]
                if node.port:
                    ports.add(node.port)
        return ports

    def check_port_synergy(self, node_id, board):
        ports = self.check_port(node_id, board)
        for hex_index in board.nodes[node_id].adj_hexes:
            hex_obj = board.hexes[hex_index]
            for port in ports:
                if port in ['3:1']:
                    continue
                if '_' in port:
                    port_resource = port.split('_')[1]
                    if port_resource == hex_obj.resource and constants.PIP_WEIGHTS[hex_obj.dice_number] >= 3:
                        return True
        return False
    
    def check_port_synergy_dual(self, node1_id, node2_id, board):
        ports_1 = self.check_port(node1_id, board)
        ports_2 = self.check_port(node2_id, board)
        all_ports = ports_1 | ports_2

        # Combine hexes from both nodes (deduplicated)
        hex_indices = set(board.nodes[node1_id].adj_hexes + board.nodes[node2_id].adj_hexes)

        # Tally total pip weights per resource across the two nodes
        resource_pip_totals = {}

        for hex_index in hex_indices:
            hex_obj = board.hexes[hex_index]
            if hex_obj.dice_number is None:
                continue
            pip = constants.PIP_WEIGHTS[hex_obj.dice_number]
            res = hex_obj.resource
            resource_pip_totals[res] = resource_pip_totals.get(res, 0) + pip

        # Check each resource-specific port for pip synergy
        for port in all_ports:
            if '_' not in port:
                continue  # skip '3:1' ports or malformed entries
            port_resource = port.split('_')[1]
            if resource_pip_totals.get(port_resource, 0) >= 4:
                return True

        return False

    def analyze_resources(self, board):
        resource_scores = {}

        # Sort hexes deterministically by resource name and dice number (as fallback if no ID exists)
        sorted_hexes = sorted(
            board.hexes,
            key=lambda h: (h.resource or "", h.dice_number or 0)
        )

        for resource in constants.RESOURCES:
            resource_pipcount = 0
            for hex in sorted_hexes:
                if hex.resource != resource:
                    continue
                resource_pipcount += constants.PIP_WEIGHTS.get(hex.dice_number, 0)
            
            avg = resource_pipcount / constants.TILE_DISTRIBUTION[resource]
            if avg < 2.6:
                resource_scores[resource] = 'scarce'
            elif avg > 3.87:
                resource_scores[resource] = 'plentiful'
            else:
                resource_scores[resource] = 'normal'

        return resource_scores
                

    def score_pips(self, node_id, board, node_id2 = None):
        pip_score = 0
        for hex_index in board.nodes[node_id].adj_hexes:
            hex_obj = board.hexes[hex_index]
            if hex_obj.dice_number is not None:
                pip = constants.PIP_WEIGHTS[hex_obj.dice_number]
                pip_score += pip
        if not node_id2:
            return pip_score
        for hex_index in board.nodes[node_id2].adj_hexes:
                hex_obj = board.hexes[hex_index]
                if hex_obj.dice_number is not None:
                    pip = constants.PIP_WEIGHTS[hex_obj.dice_number]
                    pip_score += pip
        return pip_score
    
    def check_corner(self, hex):
        scanned_nodes = sorted(hex.node_ids)

        for corner_node_list in constants.CORNER_HEXES.values():
            if scanned_nodes == sorted(corner_node_list):
                return True
        return False

    def is_ows_setup(self, node1_id, node2_id, board):
        hex_indices = set(board.nodes[node1_id].adj_hexes + board.nodes[node2_id].adj_hexes)
        resources = {board.hexes[i].resource for i in hex_indices if board.hexes[i].resource != 'desert'}
        return resources.issubset({'ore', 'wheat', 'sheep'})
    
    def ows_pip_balance_score(self, node1_id, node2_id, board):
        hex_indices = set(board.nodes[node1_id].adj_hexes + board.nodes[node2_id].adj_hexes)
        pip_totals = {'ore': 0, 'wheat': 0, 'sheep': 0}

        for i in hex_indices:
            hex_obj = board.hexes[i]
            if hex_obj.resource in pip_totals and hex_obj.dice_number is not None:
                pip = constants.PIP_WEIGHTS[hex_obj.dice_number]
                pip_totals[hex_obj.resource] += pip

        # Ideal ratio is 4:4:2 or 6:6:3 (ore:wheat:sheep)
        target = [6, 6, 3]
        actual = [pip_totals['ore'], pip_totals['wheat'], pip_totals['sheep']]

        # Normalize and compute closeness score (lower is better)
        def normalize(vec):
            total = sum(vec)
            return [x / total if total else 0 for x in vec]

        norm_actual = normalize(actual)
        norm_target = normalize(target)

        # Score inversely to distance
        distance = sum(abs(a - b) for a, b in zip(norm_actual, norm_target))
        score = max(0, 1.5 - distance * SCORING_WEIGHTS['OWS_ratio_bonus_magnifier'])  # scale/tune as needed

        return score
    
    def check_settle_spot(self, board, taken_nodes):
        possible_nodes = self.generate_candidate_nodes(board, exclude_nodes=taken_nodes)
        return bool(possible_nodes)
    
    def is_ows_hybrid_setup(self, node1_id, node2_id, board):
        hex_indices = set(board.nodes[node1_id].adj_hexes + board.nodes[node2_id].adj_hexes)
        
        pip_totals = {'ore': 0, 'wheat': 0}
        other_resources = set()

        for i in hex_indices:
            hex_obj = board.hexes[i]
            res = hex_obj.resource
            if res in ['ore', 'wheat'] and hex_obj.dice_number is not None:
                pip = constants.PIP_WEIGHTS[hex_obj.dice_number]
                pip_totals[res] += pip
            elif res not in ['ore', 'wheat', 'sheep'] and res != 'desert':
                other_resources.add(res)

        # Must have decent ore and wheat
        if pip_totals['ore'] >= 3 and pip_totals['wheat'] >= 3:
            # Must have one non-OWS resource
            if other_resources:
                return True
        
        return False
    
    def is_road_setup(self, node1_id, node2_id, board):
        hex_indices = set(board.nodes[node1_id].adj_hexes + board.nodes[node2_id].adj_hexes)

        pip_totals = {'wood': 0, 'brick': 0, 'ore': 0, 'wheat': 0, 'sheep': 0}

        for i in hex_indices:
            hex_obj = board.hexes[i]
            res = hex_obj.resource
            if res in pip_totals and hex_obj.dice_number is not None:
                pip = constants.PIP_WEIGHTS[hex_obj.dice_number]
                pip_totals[res] += pip

        # Must have at least 3 pip production in both wood and brick
        if pip_totals['wood'] < 3 or pip_totals['brick'] < 3:
            return False

        # Must not have ore
        if pip_totals['ore'] > 0:
            return False
        
        if pip_totals['sheep'] == 0 or pip_totals['wheat'] == 0:
            return False

        # Check pip ratio closeness (wood/brick ~= 1:1)
        ratio = pip_totals['wood'] / pip_totals['brick']
        if 0.66 <= ratio <= 1.5:
            return True

        return False
        

    def is_city_and_roads_setup(self, node1_id, node2_id, board):
        hex_indices = set(board.nodes[node1_id].adj_hexes + board.nodes[node2_id].adj_hexes)

        pip_totals = {'ore': 0, 'wheat': 0, 'wood': 0, 'brick': 0}
        all_resources = set()

        for i in hex_indices:
            hex_obj = board.hexes[i]
            if hex_obj.dice_number is None:
                continue
            res = hex_obj.resource
            if res in pip_totals:
                pip = constants.PIP_WEIGHTS[hex_obj.dice_number]
                pip_totals[res] += pip
                all_resources.add(res)
            elif res != 'desert':
                return False  # disqualify if sheep is present

        # Must have only ore, wheat, wood, and brick
        if not all_resources.issubset({'ore', 'wheat', 'wood', 'brick'}):
            return False

        return True
    
    def city_and_roads_balance_score(self, node1_id, node2_id, board):
        hex_indices = set(board.nodes[node1_id].adj_hexes + board.nodes[node2_id].adj_hexes)

        pip_totals = {'ore': 0, 'wheat': 0, 'wood': 0, 'brick': 0}

        for i in hex_indices:
            hex_obj = board.hexes[i]
            if hex_obj.dice_number is None:
                continue
            res = hex_obj.resource
            if res in pip_totals:
                pip = constants.PIP_WEIGHTS[hex_obj.dice_number]
                pip_totals[res] += pip

        cities = pip_totals['ore'] + pip_totals['wheat']
        roads = pip_totals['wood'] + pip_totals['brick']

        if cities == 0 or roads == 0:
            return 0

        ratio = cities / roads
        # Closer to 1 is better
        distance = abs(ratio - 1)
        score = max(0, 1.5 - distance * SCORING_WEIGHTS['CITIES&ROADS_balance_score'])  # tune scale

        return score

    def is_balanced_setup(self, node1_id, node2_id, board):
        hex_indices = set(board.nodes[node1_id].adj_hexes + board.nodes[node2_id].adj_hexes)

        pip_totals = {'ore': 0, 'wheat': 0, 'sheep': 0, 'wood': 0, 'brick': 0}
        seen_resources = set()

        for i in hex_indices:
            hex_obj = board.hexes[i]
            res = hex_obj.resource
            if res in pip_totals and hex_obj.dice_number is not None:
                pip = constants.PIP_WEIGHTS[hex_obj.dice_number]
                pip_totals[res] += pip
                seen_resources.add(res)

        # Check all 5 resources are present
        if seen_resources != set(pip_totals.keys()):
            return False

        # Require wheat support
        if pip_totals['wheat'] < 3:
            return False

        return True
    
    def is_port_setup(self, node1_id, node2_id, board):
        hex_indices = set(board.nodes[node1_id].adj_hexes + board.nodes[node2_id].adj_hexes)

        pip_totals = {'ore': 0, 'wheat': 0, 'sheep': 0, 'wood': 0, 'brick': 0}

        for i in hex_indices:
            hex_obj = board.hexes[i]
            res = hex_obj.resource
            if res in pip_totals and hex_obj.dice_number is not None:
                pip = constants.PIP_WEIGHTS[hex_obj.dice_number]
                pip_totals[res] += pip
        
        total_ports = (self.check_port(node1_id, board) | self.check_port(node2_id, board))
        
        for port in total_ports:
            if port == '3:1':
                continue
            if '_' in port:
                port_resource = port.split('_')[1]
                for resource, pips in pip_totals.items():
                    if pip_totals.get(port_resource, 0) >= 9:
                        return True
        return False
    
    def threehex_check(self, node_id, board):
        seen = 0
        for hex in board.nodes[node_id].adj_hexes:
            hex_obj = board.hexes[hex]
            res = hex_obj.resource
            if res != 'desert':
                seen += 1
        return seen
    
    def ore_check(self, node_id, board):
        for hex_index in board.nodes[node_id].adj_hexes:
            hex_obj = board.hexes[hex_index]
            if hex_obj.resource == 'ore' and hex_obj.dice_number >= 3:
                return True
        return False

    def valid_settlement_pair(self, node1_id, node2_id, board):
        if node1_id == node2_id:
            return False
        if node1_id not in board.nodes or node2_id not in board.nodes:
            return False

        return True
        
    
    
    def find_accessible_settle_spots(self, board, start_node_ids, max_depth=4, exclude=None):
        if exclude is None:
            exclude = set(start_node_ids)

        visited = set(start_node_ids)
        queue = [(nid, 0) for nid in start_node_ids]
        valid_spots = set()

        while queue:
            current, depth = queue.pop(0)
            if depth >= max_depth:
                continue

            for neighbor in board.nodes[current].connected_nodes:
                if neighbor in visited:
                    continue
                visited.add(neighbor)
                queue.append((neighbor, depth + 1))
                if neighbor not in exclude and board.nodes[neighbor].owner is None:
                    # Check if neighbor is legally settleable
                    neighbors = board.nodes[neighbor].connected_nodes
                    if all(board.nodes[n].owner is None for n in neighbors):
                        valid_spots.add(neighbor)

        return valid_spots
    
    
    def get_next_road_towards_settlement(self, game, player, max_distance=4, top_n=5):
        board = game.board

        # 1) build a list of your top‐N settlement targets by score
        cands = []
        for nid in board.nodes:
            if not game.valid_node(nid, player.id):
                continue
            score = self.score_node(nid, board)  # or your pip‐based scoring
            cands.append((score, nid))
        cands.sort(reverse=True)
        cands = [nid for _, nid in cands[:top_n]]

        # 2) BFS helper
        def bfs_path_to(target):
            seen = set()
            # start from all your owned nodes & road endpoints
            frontier = set(player.settlements) | set(player.cities)
            for road in player.roads:
                frontier |= set(road)

            queue = deque([(s, []) for s in frontier])
            seen |= frontier

            while queue:
                node, path = queue.popleft()
                if node == target and path:
                    return path   # a list of edges [(u,v),…]
                if len(path) >= max_distance:
                    continue
                for nbr in board.nodes[node].connected_nodes:
                    edge = tuple(sorted((node, nbr)))
                    eobj = game.find_edge(node, nbr)
                    if eobj.owner is not None:      # already built
                        continue
                    if nbr in seen:
                        continue
                    seen.add(nbr)
                    queue.append((nbr, path + [edge]))
            return None

        # 3) try each candidate
        for target in cands:
            path = bfs_path_to(target)
            if path:
                # return the very first step on that path
                return path[0]

        # nothing reachable
        return None
    
    def attempt_build(self, game, player):
        """
        Attempt to build repeatedly until no further actions are possible.
        Returns a list of strings describing each build action, or ['No build action taken'] if none.
        """
        board = game.board

        def has_longest_road():
            return game.longest_road_player_id == player.id

        actions = []
        # Continue looping until no build action succeeds in a full pass
        while True:
            built_this_round = False

           

            # 1. Strategy-based early road priority
            if self.strategy in ("ROAD", "CITIES&ROADS") and player.points > 6:
                
                road_target = self.select_road_target_towards_best_settlement_within_range(game, player)
                if road_target:
                    n1, n2 = road_target
                    success, reason = game.build_road(player, n1, n2)
                    
                    if success:
                        actions.append(f"Built strategic road toward {n2}")
                        built_this_round = True
                        # Restart priority loop
                        continue
                

            # 2. Try to build city
            city_targets = [
                (node_id, sum(board.hexes[h].dice_number or 0 for h in board.nodes[node_id].adj_hexes))
                for node_id in player.settlements
            ]
            city_targets.sort(key=lambda x: -x[1])
            for node_id, _ in city_targets:
                
                success, reason = game.build_city(player, node_id)
                
                if success:
                    actions.append(f"Built city at {node_id}")
                    built_this_round = True
                    break
            if built_this_round:
                continue

            # 3. Try to build settlement
            best_settle = self.best_settlement_location(game, player)
            
            if best_settle:
                
                success, reason = game.build_settlement(player, best_settle)
                
                if success:
                    actions.append(f"Built settlement at {best_settle}")
                    built_this_round = True
                    continue

            # 4. Try to buy dev card (if not road-only strategy)
            total_cards = sum(player.resources.values())
            if self.strategy not in ["ROAD", 'CITIES&ROADS'] and total_cards > 7:
                success, reason = game.buy_dev_card(player)
                if success:
                    actions.append("Bought development card")
                    built_this_round = True
                    continue

            # 5. Try to extend road (Longest Road logic)
            road_chain = game.find_longest_road(player)
            if len(road_chain) >= 3 and not has_longest_road():
                road_target = self.select_road_target_towards_best_settlement_within_range(game, player)
                if road_target:
                    n1, n2 = road_target
                    success, reason = game.build_road(player, n1, n2)
                    if success:
                        actions.append(f"Extended road to {n2}")
                        built_this_round = True
                        continue

            connected = set(player.settlements) | set(player.cities)
            for edge in player.roads:
                connected |= set(edge)
            
            # Compute full and partial affordability for a settlement:
            settle_cost = constants.COSTS_CARD['settlement']    # e.g. {'wood':1,'brick':1,'sheep':1,'wheat':1}
            have_all = game.has_required_resources(player, settle_cost)

            # Count how many settlement resources you already hold:
            have_count = sum(
                min(player.resources.get(res, 0), req) 
                for res, req in settle_cost.items()
            )

            # 6. Default road build if resources allow
            if (best_settle is None or best_settle not in connected) \
                and game.has_required_resources(player, constants.COSTS_CARD['road']):
                    step = self.get_next_road_towards_settlement(game, player)
                    if step:
                        n1, n2 = step
                        success, reason = game.build_road(player, n1, n2)
                        if success:
                            actions.append(f"Built road from {n1} to {n2}")
                            built_this_round = True
                            continue

            # If no action succeeded in this loop, break
            if not built_this_round:
                break

        # If no actions were taken, indicate no build
        if not actions:
            return ["No build action taken"]
        return actions



    def best_settlement_location(self, game, player=None):
        board = game.board
        player = player or game.players[self.player_id]
        best_node = None
        best_score = float('-inf')

        # Gather all connected nodes (from roads + existing settlements/cities)
        connected_nodes = set()
        connected_nodes.update(player.settlements)
        connected_nodes.update(player.cities)
        for road in player.roads:
            connected_nodes.update(road)

        for node_id, node in board.nodes.items():
            if not game.valid_node(node_id, player.id):
                continue

            # Node must be connected to player’s network
            if not any(neighbor in connected_nodes for neighbor in node.connected_nodes):
                continue

            # Score the node
            pip_score = sum(
                board.hexes[h].dice_number or 0 for h in node.adj_hexes
            )
            if node.port:
                pip_score += 0.5  # Optional bonus

            if pip_score > best_score:
                best_score = pip_score
                best_node = node_id

        
        return best_node
    

    def choose_rob_target(self, board, game, player):
        players = [p for p in game.players if p.id != self.player_id]
        
        # Step 1: Check if any are >=7 points
        most_player = [p for p in players if p.points >= 7]

        if most_player:
            candidates = most_player

            # Tie-break: most points
            max_points = max(p.points for p in candidates)
            candidates = [p for p in candidates if p.points == max_points]

            # Tie-break: most cities
            max_cities = max(len(p.cities) for p in candidates)
            candidates = [p for p in candidates if len(p.cities) == max_cities]

            # Tie-break: most resources
            max_resources = max(sum(p.resources.values()) for p in candidates)
            candidates = [p for p in candidates if sum(p.resources.values()) == max_resources]


        else:
            # Step 2: Figure out what resource you produce least of (by pip sum)
            my_pips = defaultdict(int)
            for node in player.settlements | player.cities:
                for hex_id in board.nodes[node].adj_hexes:
                    hex = board.hexes[hex_id]
                    if hex.dice_number:
                        my_pips[hex.resource] += constants.PIP_WEIGHTS[hex.dice_number]

            least_produced = min(my_pips, key=my_pips.get)

            # Find player who produces most of this resource
            scores = []
            for p in players:
                pip_total = 0
                for node_id in p.settlements | p.cities:
                    for hex_idx in board.nodes[node_id].adj_hexes:
                        hex = board.hexes[hex_idx]
                        if hex.resource == least_produced and hex.dice_number:
                            pip_total += constants.PIP_WEIGHTS[hex.dice_number]
                scores.append((p, pip_total))

            max_score = max(pip for _, pip in scores)
            candidates = [p for p, pip in scores if pip == max_score]

        # Final fallback: random among candidates
        victim = random.choice(candidates)

        # Step 3: Find best hex of theirs to rob (most total pip value)
        hex_scores = []
        for hex_id, hex in enumerate(board.hexes):
            if hex.robber:
                continue
            owner_ids = {board.nodes[n].owner for n in hex.node_ids}
            if victim.id in owner_ids:
                total_pips = constants.PIP_WEIGHTS.get(hex.dice_number, 0)
                hex_scores.append((hex_id, total_pips))

        if not hex_scores:
            return victim.id, random.randint(0, len(board.hexes)-1)

        best_hex = max(hex_scores, key=lambda x: x[1])[0]
        return victim.id, best_hex
    
    
    def attempt_play_dev_card(self, player, board, game):
        if player.played_dev_this_turn:
            return False

        priority_order = ['monopoly', 'road_building', 'year_of_plenty', 'knight']

        for card in priority_order:
            if card in player.dev_cards and card not in player.unplayable_dev_cards:
                
                if card == 'monopoly':
                    should_mono, res = self.should_play_monopoly(player, game)
                    if should_mono:
                        success, msg = game.play_dev_card_bot(player, card, mono_res=res)
                        if success:
                            
                            player.played_dev_this_turn = True
                            return True
                    continue

                if card == 'year_of_plenty':
                    should_yop, res1, res2 = self.should_play_yop(player, game)
                    if should_yop:
                        success, msg = game.play_dev_card_bot(player, card, yop_res1=res1, yop_res2=res2)
                        if success:
                            
                            player.played_dev_this_turn = True
                            return True
                    continue

                if card == 'knight':
                    is_blocked = any(
                        board.hexes[h].robber for node in player.settlements for h in board.nodes[node].adj_hexes
                    )
                    if not is_blocked and player.played_knights < 2:
                        continue
                    target_id, hex_index = self.choose_rob_target(board, game, player)
                    success, msg = game.play_dev_card_bot(player, card, hex_index=hex_index, target_id=target_id)
                    if success:
                        
                        player.played_dev_this_turn = True
                        return True
                    continue

                if card == 'road_building':
                    road_target = self.select_road_target_towards_best_settlement_within_range(game, player)
                    if road_target:
                        road_pair = [road_target]
                        success, msg = game.play_dev_card_bot(player, card, road_pair=road_pair)
                        if success:
                            
                            player.played_dev_this_turn = True
                            return True
                    continue

        return False

    

    def select_road_target_towards_best_settlement_within_range(self, game, player, max_distance=4):
        board = game.board
        target_node = self.best_settlement_location(game, player)

        if target_node is None:
            return None

        # Step 1: Determine starting nodes (connected to player network)
        start_nodes = set()
        for edge in board.edges:
            if edge.owner == player.id:
                start_nodes.add(edge.node1.id)
                start_nodes.add(edge.node2.id)

        for node_id in player.settlements | player.cities:
            start_nodes.add(node_id)

        if not start_nodes:
            return None


        # Step 2: BFS from each start node to find a path to target_node
        for start in start_nodes:
            visited_edges = set()
            visited_nodes = set()
            queue = deque([(start, 0, [])])  # (current_node, depth, path)

            while queue:
                current, dist, path = queue.popleft()
                visited_nodes.add(current)

                if dist > max_distance:
                    continue

                if current == target_node and path:
                    return path[0]  # First road step

                for neighbor in board.nodes[current].connected_nodes:
                    edge = tuple(sorted((current, neighbor)))
                    if edge in visited_edges:
                        continue

                    visited_edges.add(edge)
                    edge_obj = game.get_edge(current, neighbor)
                    if not edge_obj:
                        continue

                    if edge_obj.owner is not None:
                        continue  # road already taken

                    queue.append((neighbor, dist + 1, path + [edge]))

        return None

    def should_play_yop(self, player, game):
        build_options = {
            "city": {"ore": 3, "wheat": 2},
            "settlement": {"brick": 1, "wood": 1, "wheat": 1, "sheep": 1},
            "dev_card": {"wheat": 1, "sheep": 1, "ore": 1},
            "road": {"wood": 1, "brick": 1}
        }

        def resources_needed(requirements):
            need = {}
            for res, amt in requirements.items():
                if player.resources[res] < amt:
                    need[res] = amt - player.resources[res]
            return need

        for build_type in ["city", "settlement", "dev_card", "road"]:
            if build_type == "settlement" and self.strategy == "road":
                continue
            if build_type == "dev_card" and self.strategy == "road":
                continue

            needed = resources_needed(build_options[build_type])
            if 1 <= sum(needed.values()) <= 2:
                res_list = list(needed.keys())
                # Pad with duplicates if only one resource needed
                if len(res_list) == 1:
                    res_list.append(res_list[0])
                elif len(res_list) == 0:
                    continue  # already have the resources, no need for YOP
                return True, res_list[0], res_list[1]

        return False, None, None


    def should_play_monopoly(self, player, game):
        if player.points < 6:
            return False, None  # too early to play

        # Count total resources held by other players
        total_by_resource = defaultdict(int)
        for other in game.players:
            if other.id == player.id:
                continue
            for res, count in other.resources.items():
                total_by_resource[res] += count

        # Find resource you produce the least of
        resource_production = defaultdict(int)
        for node_id in player.settlements | player.cities:
            for h in game.board.nodes[node_id].adj_hexes:
                hex = game.board.hexes[h]
                if not hex.robber:
                    resource_production[hex.resource] += hex.dice_number or 0

        if not resource_production:
            return False, None

        weakest_resource = min(resource_production, key=resource_production.get)
        total_available = total_by_resource[weakest_resource]

        if total_available >= 18:
            return True, weakest_resource

        return False, None
    
    
    def try_trade_to_build(self, player, game):
        resources = constants.RESOURCES
        board = game.board

        def can_build_structure():
            # 1) City on an existing settlement?
            for nid in player.settlements:
                node = board.nodes[nid]
                if node.owner == player.id and node.building_type == 'settlement':
                    if game.has_required_resources(player, constants.COSTS_CARD['city']):
                        return True

            # 2) New settlement?
            spot = self.best_settlement_location(game, player)
            if spot and game.has_required_resources(player, constants.COSTS_CARD['settlement']):
                return True

            return False

        # 0) Bail if already buildable
        if can_build_structure():
            return False, "Already able to build"

        # Helper to compute deficits for a given cost
        def calc_deficit(cost):
            return {r: max(0, cost.get(r, 0) - player.resources.get(r, 0)) for r in resources}

        # Decide whether to target settlement or city first based on smaller deficit
        settle_cost = constants.COSTS_CARD['settlement']
        city_cost = constants.COSTS_CARD['city']
        deficit_settle = calc_deficit(settle_cost)
        deficit_city = calc_deficit(city_cost)
        sum_def = lambda d: sum(d.values())
        cost_order = ['settlement', 'city'] if sum_def(deficit_settle) < sum_def(deficit_city) else ['city', 'settlement']

        # Pick first target we actually need to save for
        target_key = None
        target_cost = None
        deficit = {}
        for key in cost_order:
            cost = constants.COSTS_CARD[key]
            d = calc_deficit(cost)
            if any(d.values()):
                target_key = key
                target_cost = cost
                deficit = d
                break
        if target_cost is None:
            return False, "Nothing to save for"

        # 2) Loop: trade until buildable or no profitable trade
        trades_made = []
        while True:
            # Recompute deficit
            deficit = calc_deficit(target_cost)
            total_deficit = sum_def(deficit)
            # Check if now buildable
            if total_deficit == 0:
                msg = " and then ".join(trades_made) + " and now can build" if trades_made else "Now can build"
                return True, msg

            

            # Find best trade by maximum reduction in total deficit
            best_score = 0
            best_trade = None
            for give, have in player.resources.items():
                rate = game.get_port_rate(player, give) or 4
                if have < rate:
                    continue
                for need, miss_amt in deficit.items():
                    if need == give or miss_amt == 0:
                        continue
                    # simulate trade
                    new_res = player.resources.copy()
                    new_res[give] -= rate
                    new_res[need] += 1
                    new_def = {r: max(0, target_cost.get(r, 0) - new_res.get(r, 0)) for r in resources}
                    score = total_deficit - sum_def(new_def)
                    if score > best_score:
                        best_score = score
                        best_trade = (give, need, rate)

            if not best_trade:
                
                return False, "No beneficial trade found"

            give, need, rate = best_trade
            
            success, msg = game.trade_with_bank(player, give, need)
            

            trades_made.append(msg)
            # loop continues, will re-check buildable next iteration

            # unreachable
            return False, "No beneficial trade found"


    
    def port_to_dump_excess(self, player, game):
        total = sum(player.resources.values())
        if total <= 7:
            return False, "No need to dump resources"

        # Sort by most‐to‐fewest
        for res, amt in sorted(player.resources.items(), key=lambda x: -x[1]):
            # how many units to give up?
            rate = game.get_port_rate(player, res) or 4
            if amt < rate:
                # not enough to pay even a bank trade
                continue

            for gain in constants.RESOURCES:
                if gain == res:
                    continue
                
                success, msg = game.trade_with_bank(player, res, gain)
                
                if success:
                    return True, f"{msg} to reduce hand size"

        return False, "No viable port trade available"

    
    def take_turn(self, player, game):
        board = game.board

        # Step 1: Roll Dice
        roll = game.roll_dice()

        if roll == 7:
            # Discard if over 7 cards
            if sum(player.resources.values()) > 7:
                game.handle_robber_roll_bot(player)

        # Step 2: Try to play a development card
        self.attempt_play_dev_card(player, board, game)

        # Step 3: Try to port trade to dump excess if >7
        self.port_to_dump_excess(player)

        # Step 4: Try to trade to build
        self.try_trade_to_build(player)

        # Step 5: Attempt build
        build_msg = self.attempt_build(game, player)
        

        # Step 6: End Turn
        player.played_dev_this_turn = False
        player.unplayable_dev_cards.clear()
    





if __name__ == '__main__':
    from board import Board
    from bot import Bot
    import constants

    board = Board(test_hexes = constants.TEST_BOARD)
    bot = Bot(player_id = 0, total_players = 4)

    test_node_id = 'node_32'  # just pick the first node for now
    score = bot.score_node(test_node_id, board)

    print(f'\nTest score for node {test_node_id}: {score}')