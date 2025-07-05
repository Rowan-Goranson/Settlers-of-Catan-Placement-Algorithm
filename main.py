from board import Board
from game import Game
from bot import Bot
from collections import Counter
import constants
import random
import pandas as pd
import optuna
import bot

#TODOS:
'''
- fix the 2nd settle road placement logic
- ore weighting for placement
- trading (AI)
- fix road building logic?
- fix future logic?
'''


tunable_weights = {
  'OWS': (0,2),
  'OWS_HYBRID': (0,2),
  'ROAD': (0,2),
  'CITIES&ROADS': (0,2),
  'BALANCED': (0, 2),
  'PORT': (0,2),
  'PRODUCTION': (0,2)
}

TRIALS = 5000 #for optuna testing and normal testing
NUM_OPTUNA_TRIALS = 50 #number of tested weights

#Simulation Logic
def simulate_one(seed=None, max_turns=200):
    if seed is not None:
        random.seed(seed)
    
    #setup
    board = Board(test_hexes = constants.TEST_BOARD)
    game = Game(board, 4)
    bots = [Bot(player_id = i, total_players=4) for i in range(4)]

    for i, player in enumerate(game.players):
        player.bot = bots[i]

    first_placements = []
    second_placements = []
    taken_nodes = set()
    smart_settlement_indicator = random.randint(0,3) #randomly choose smart bot

    # First placements
    for bot in bots:
        if bot.player_id == smart_settlement_indicator:
            node = bot.choose_first_placement(board, taken_nodes)
        else: 
            node = game.pick_random_settle(taken_nodes)
        taken_nodes.add(node)
        taken_nodes.update(board.nodes[node].connected_nodes)
        first_placements.append((bot.player_id, node))

        neighbor = bot.choose_road_after_settlement(board, node, bot.player_id)
        game.place_initial_settle_and_road(game.players[bot.player_id], node, neighbor)

    # Second placements
    for bot in reversed(bots):
        if bot.player_id == smart_settlement_indicator:
            node2 = bot.choose_second_placement(board, first_placements[bot.player_id][1], taken_nodes)
        else: 
            node2 = game.pick_random_settle(taken_nodes)
        taken_nodes.add(node2)
        taken_nodes.update(board.nodes[node2].connected_nodes)
        second_placements.append((bot.player_id, node2))

    
    for bot_id, node2 in second_placements:
        bot = bots[bot_id]
        road2 = bot.choose_road_after_settlement(board, node2, bot_id)
        success, msg = game.place_initial_settle_and_road(game.players[bot_id], node2, road2)

        if not success:
            for nb in board.nodes[node2].connected_nodes:
                ok, msg2 = game.place_initial_settle_and_road(game.players[bot_id], node2, nb)
                if ok:
                    break

        game.distribute_starting_resources(game.players[bot_id])

    MAX_TURNS = max_turns
    game.setup_phase = False
    turn_count = 0

    #game loop
    while not game.game_over() and turn_count < MAX_TURNS:
        current_player = game.players[game.current_player_turn]

        roll = game.roll_dice()

        if roll == 7:
            game.handle_robber_roll_bot(current_player)
        else:
            game.distribute_resources(roll)

        if hasattr(current_player, 'bot'):
            current_player.bot.attempt_play_dev_card(current_player, game.board, game)
            current_player.bot.attempt_build(game, current_player)
            current_player.bot.try_trade_to_build(current_player, game)
            current_player.bot.port_to_dump_excess(current_player, game)

        current_player.played_dev_this_turn = False
        game.check_largest_army()
        game.check_longest_road()
        game.advance_turn()
        turn_count += 1
        game.turn += 1

    # Game over
    winner = game.check_win()
    return {
        "winner": winner.id if winner else None,
        "turns": game.turn,
        "largest_army": game.largest_army_player_id,
        "longest_road": game.longest_road_player_id,
        **{f"points_{p.id}": p.points for p in game.players},
        'smart': smart_settlement_indicator
    }

#to run trials and append results to a dataframe
def run_trials(n):
    results = []
    for i in range(n):
        stats = simulate_one(seed=i)
        stats["trial"] = i
        results.append(stats)
    return pd.DataFrame(results)





#OPTUNA for tuning

'''
def objective(trial):
    # 1) Sample a candidate
    orig = bot.SCORING_WEIGHTS.copy()
    for name, (low, high) in tunable_weights.items():
        bot.SCORING_WEIGHTS[name] = trial.suggest_float(name, low, high)

    # 2) Run a simulation to estimate performance
    df = run_trials(TRIALS)   # your simulate_one + run_trials
    constants.SCORING_WEIGHTS = orig
    smart_wins = (df["winner"] == df["smart"]).sum()
    win_rate = smart_wins / len(df)

    # 3) Return the metric to maximize
    return win_rate

study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=NUM_OPTUNA_TRIALS) #number of differeint weights tested

print("Best win rate:", study.best_value)
print("Best weights:")
for k, v in study.best_params.items():
    print(f"  {k}: {v}")
'''




#normal test


df = run_trials(TRIALS)
#df.to_csv("catan_backtest.csv", index=False)

# Win rates:
print("Win rates:")
print(df["winner"].value_counts(normalize=True).sort_index())

# Average game length:
print("\nAvg turns per game:", df["turns"].mean())

# How often each player held the special awards at game end:
print("\n% Largest Army holders:")
print(df["largest_army"].value_counts(normalize=True).sort_index())

print("\n% Longest Road holders:")
print(df["longest_road"].value_counts(normalize=True).sort_index())

smart_wins = (df["winner"] == df["smart"]).sum()
print(f"\nSmart-bot win rate: {smart_wins}/{len(df)} = {smart_wins/len(df):.2%}")

# Mean points by player:
mean_pts = {pid: df[f"points_{pid}"].mean() for pid in range(4)}
print("\nAvg final points:", mean_pts)























'''
board = Board(test_hexes = constants.TEST_BOARD)
game = Game(board)
bots = [Bot(player_id = i, total_players=4) for i in range(4)]




first_placements = []
second_placements = []
taken_nodes = set()



# First placements
for bot in bots:
    node = bot.choose_first_placement(board, taken_nodes)
    taken_nodes.add(node)
    taken_nodes.update(board.nodes[node].connected_nodes)
    first_placements.append((bot.player_id, node))

    neighbor = bot.choose_road_after_settlement(board, node, bot.player_id)
    game.place_initial_settle_and_road(game.players[bot.player_id], node, neighbor)

print(f'{taken_nodes}')
# Second placements
for bot in reversed(bots):
    node2 = bot.choose_second_placement(board, first_placements[bot.player_id][1], taken_nodes)
    taken_nodes.add(node2)
    taken_nodes.update(board.nodes[node2].connected_nodes)
    second_placements.append((bot.player_id, node2))

   
for bot_id, node2 in second_placements:
    bot = bots[bot_id]
    road2 = bot.choose_road_after_settlement(board, node2, bot_id)
    game.place_initial_settle_and_road(game.players[bot_id], node2, road2)

    game.distribute_starting_resources(game.players[bot_id])

# Display placements
for pid, node in first_placements:
    print(f"Bot {pid} placed first settlement on {node}")
for pid, node in second_placements:
    print(f"Bot {pid} placed second settlement on {node}")


'''































#board.show_full_board()
#board.show_hexes()

#for turn in range(10):
   # game.take_turn()


'''
board.show_ports()

def test_dev_cards(game):
    p0 = game.players[0]
    p0.resources = {'wheat': 10, 'sheep': 10, 'ore': 10, 'wood': 0, 'brick': 0}
    
    for _ in range(5):
        success, msg = game.buy_dev_card(p0)
        print(f"Buy dev card: {msg}")

    for card in p0.unplayable_dev_cards[:]:
        print(f"Trying to play: {card}")
        game.play_dev_card(p0, card)

    game.advance_turn()
    print("Turn advanced. Dev cards restored:", p0.dev_cards)

def test_port_trade(game):
    p0 = game.players[0]
    game.board.nodes['node_0'].port = '3:1'
    p0.settlements.add('node_0')
    p0.resources = {'wood': 4, 'wheat': 0, 'brick': 0, 'sheep': 0, 'ore': 0}
    print("Before port trade:", p0.resources)
    success, msg = game.trade_with_bank(p0, 'wood', 'wheat')
    print("Port trade:", msg)
    print("After:", p0.resources)

def test_longest_road(game):
    print('longest road test')
    p0 = game.players[0]
    p0.roads = {
        tuple(sorted(('node_0', 'node_1'))),
        tuple(sorted(('node_1', 'node_2'))),
        tuple(sorted(('node_2', 'node_3'))),
        tuple(sorted(('node_3', 'node_4'))),
        tuple(sorted(('node_4', 'node_5')))
    }

    for road in p0.roads:
        edge = game.find_edge(*road)
        if edge:
            edge.owner = p0.id
    game.check_longest_road()
    print(f"Player 0 points: {p0.points}")

def test_largest_army(game):
    print("\n=== LARGEST ARMY TEST ===")
    p0 = game.players[0]
    p1 = game.players[1]

    p0.played_knights = 2
    p1.played_knights = 3  # should win it

    game.check_largest_army()
    print(f"Player 0 points: {p0.points}")
    print(f"Player 1 points: {p1.points}")

def run_all_tests():
    print("=== DEV CARD TEST ===")
    test_dev_cards(game)
    print("\n=== PORT TRADE TEST ===")
    test_port_trade(game)
    test_longest_road(game)
    test_largest_army(game)


run_all_tests()
'''