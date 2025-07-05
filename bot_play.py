
from board import Board
import constants
import random
from collections import defaultdict
from collections import deque


class Bot:
    def __init__(self, player_id, total_players):
        self.player_id = player_id
        self.total_players = total_players
        self.strategy = ''

    def attempt_build(self, game, player):
        board = game.board

        # Helper to check if player has longest road
        def has_longest_road():
            return game.longest_road_player_id == player.id

        # Find best available city spot (upgrade settlement)
        city_targets = [
            (node_id, sum(board.hexes[h].dice_number or 0 for h in board.nodes[node_id].adj_hexes))
            for node_id in player.settlements
        ]
        city_targets.sort(key=lambda x: -x[1])

        for node_id, _ in city_targets:
            if game.build_city(player, node_id):
                return f"Built city at {node_id}"

        # Best settlement spot available to player
        best_settle = self.best_settlement_location(game, player)
        if best_settle:
            if player.strategy in ("road", "cities&roads") and player.points > 6:
                # Prioritize road if strategy is road-heavy
                pass  # handled below
            elif game.build_settlement(player, best_settle):
                return f"Built settlement at {best_settle}"

        # Prioritize development cards unless settlement strategy
        if player.strategy != "road":
            if game.build_dev_card(player):
                return "Built development card"

        # ROAD LOGIC
        road_chain = self.find_longest_road(player, board)
        if len(road_chain) >= 3 and not has_longest_road():
            road_target = self.select_road_target(player, board, game)
            if road_target:
                n1, n2 = road_target
                if game.build_road(player, n1, n2):
                    return f"Extended road to {n2}"

        if player.strategy in ("road", "cities&roads") and player.points > 6:
            road_target = self.select_road_target(game, player)
            if road_target:
                n1, n2 = road_target
                if game.build_road(player, n1, n2):
                    return f"Built strategic road toward {n2}"

        return "No build action taken"

    def best_settlement_location(self, game):
        board = game.board
        player = game.players[self.player_id]
        best_node = None
        best_score = float('-inf')

        for node_id, node in board.nodes.items():
            if not game.valid_node(node_id, player.player_id):
                continue

            # Must be reachable by one of the player's roads
            reachable = any(
            edge.owner == player.player_id and (edge.node1.id == node_id or edge.node2.id == node_id)
            for edge in board.edges
            )
            if not reachable:
                continue

            # Score the node: sum of pips on adjacent hexes
            pip_score = sum(
                board.hexes[h].dice_number or 0 for h in node.adj_hexes
            )
            if node.port:
                pip_score += 0.5  # Optional port synergy bonus

            if pip_score > best_score:
                best_score = pip_score
                best_node = node_id

        return best_node
    
    def select_road_target(self, player, board, game):
        best_edge = None
        best_score = float('-inf')

        # First, find the ideal settlement location
        target_node = self.best_settlement_location(player, board, game)

        for edge in board.edges:
            # Skip taken roads
            if edge.owner is not None:
                continue

            # Must connect to something the player owns (settlement or road)
            connected = (
                edge.node1.owner == player.player_id or
                edge.node2.owner == player.player_id or
                any(e.owner == player.player_id and (e.node1 == edge.node1 or e.node2 == edge.node1 or e.node1 == edge.node2 or e.node2 == edge.node2)
                    for e in board.edges)
            )
            if not connected:
                continue

            # Score = proximity to target settlement
            dist = game.distance_between_nodes(edge.node1.id, target_node)
            score = -dist  # closer is better

            if score > best_score:
                best_score = score
                best_edge = (edge.node1.id, edge.node2.id)

        return best_edge
    
    def choose_rob_target(self, board, game):
        players = [p for p in game.players if p.player_id != self.player_id]
        
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
            for node in self.settlements + self.cities:
                for hex_id in board.nodes[node].adj_hexes:
                    hex = board.hexes[hex_id]
                    if hex.dice_number:
                        my_pips[hex.resource] += constants.PIP_WEIGHTS[hex.dice_number]

            least_produced = min(my_pips, key=my_pips.get)

            # Find player who produces most of this resource
            scores = []
            for p in players:
                pip_total = 0
                for node_id in p.settlements + p.cities:
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
            if victim.player_id in owner_ids:
                total_pips = constants.PIP_WEIGHTS.get(hex.dice_number, 0)
                hex_scores.append((hex_id, total_pips))

        if not hex_scores:
            return victim.player_id, random.randint(0, len(board.hexes)-1)

        best_hex = max(hex_scores, key=lambda x: x[1])[0]
        return victim.player_id, best_hex
    
    
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
                            print(f"Bot {player.id} played {card}: {msg}")
                            player.played_dev_this_turn = True
                            return True
                    continue

                if card == 'year_of_plenty':
                    should_yop, res1, res2 = self.should_play_yop(player, game)
                    if should_yop:
                        success, msg = game.play_dev_card_bot(player, card, yop_res1=res1, yop_res2=res2)
                        if success:
                            print(f"Bot {player.id} played {card}: {msg}")
                            player.played_dev_this_turn = True
                            return True
                    continue

                if card == 'knight':
                    is_blocked = any(
                        board.hexes[h].robber for node in player.settlements for h in board.nodes[node].adj_hexes
                    )
                    if not is_blocked and player.played_knights < 2:
                        continue
                    target_id, hex_index = self.choose_rob_target(board, game)
                    success, msg = game.play_dev_card_bot(player, card, hex_index=hex_index, target_id=target_id)
                    if success:
                        print(f"Bot {player.id} played {card}: {msg}")
                        player.played_dev_this_turn = True
                        return True
                    continue

                if card == 'road_building':
                    road_target = self.select_road_target_towards_best_settlement_within_range(game, player)
                    if road_target:
                        road_pair = [road_target]
                        success, msg = game.play_dev_card_bot(player, card, road_pair=road_pair)
                        if success:
                            print(f"Bot {player.id} played {card}: {msg}")
                            player.played_dev_this_turn = True
                            return True
                    continue

        return False

    
    def select_road_target_towards_best_settlement_within_range(self, game, player, max_distance=4):

        board = game.board
        target_node = self.best_settlement_location(game)
        if target_node is None:
            return None

        # Get starting points: nodes owned by player or at end of player's roads
        start_nodes = set()
        for edge in board.edges:
            if edge.owner == player.player_id:
                start_nodes.add(edge.node1.id)
                start_nodes.add(edge.node2.id)
        for node_id in player.settlements | player.cities:
            start_nodes.add(node_id)

        # BFS from each start node
        for start in start_nodes:
            visited = set()
            queue = deque([(start, 0, [])])  # (current_node, depth, path)

            while queue:
                current, dist, path = queue.popleft()
                if dist > max_distance:
                    continue
                if current == target_node and path:
                    return path[0]  # First road step toward goal

                for neighbor in board.nodes[current].connected_nodes:
                    edge = tuple(sorted((current, neighbor)))
                    if edge in visited or any(e.owner is not None for e in [game.get_edge(current, neighbor)]):
                        continue
                    visited.add(edge)
                    queue.append((neighbor, dist + 1, path + [(current, neighbor)]))

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
            if build_type == "settlement" and player.strategy == "road":
                continue
            if build_type == "dev_card" and player.strategy == "road":
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
    
    def get_trade_rate(self, player, resource):
        # Check for 2:1 port
        if f'2:1_{resource}' in player.ports:
            return 2
        # Check for generic 3:1
        if '3:1' in player.ports:
            return 3
        # Default to 4:1
        return 4
    
    def try_trade_to_build(self, player):
        resources = constants.RESOURCES

        def can_build_any():
            return (
                self.build_city(player) or
                self.buy_dev_card(player) or
                self.build_settlement(player) or
                self.build_road(player)
            )

        if can_build_any():
            return False, "Already able to build"

        for needed in resources:
            for give in resources:
                if give == needed:
                    continue
                rate = self.get_trade_rate(player, give)
                if player.resources[give] >= rate:
                    # Try trading
                    player.resources[give] -= rate
                    player.resources[needed] += 1

                    # If now able to build, success
                    if can_build_any():
                        return True, f"Traded {rate} {give} for 1 {needed} to build"
                    else:
                        # Undo trade if it didn’t help
                        player.resources[give] += rate
                        player.resources[needed] -= 1

        return False, "No beneficial trade found"
    
    def port_to_dump_excess(self, player):
        if sum(player.resources.values()) <= 7:
            return False, "No need to dump resources"

        resource_counts = sorted(player.resources.items(), key=lambda x: -x[1])
        for res, amt in resource_counts:
            rate = self.get_trade_rate(player, res)
            if amt >= rate:
                for gain in ['brick', 'lumber', 'wool', 'grain', 'ore']:
                    if gain == res:
                        continue
                    player.resources[res] -= rate
                    player.resources[gain] += 1
                    return True, f"Traded {rate} {res} for 1 {gain} to reduce hand size"

        return False, "No viable port trade available"
    
    def take_turn(self, player, game):
        board = game.board

        # Step 1: Roll Dice
        roll = game.roll_dice()
        print(f"Player {player.id} rolled a {roll}")

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
        print(build_msg)

        # Step 6: End Turn
        player.played_dev_this_turn = False
        player.unplayable_dev_cards.clear()