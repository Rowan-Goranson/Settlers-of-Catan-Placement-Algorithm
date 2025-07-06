RESOURCES = ['wood', 'brick', 'sheep', 'ore', 'wheat']
SYNERGY_RESOURCES = [['wood', 'brick'], ['ore', 'wheat']]
DICE_NUMBERS = [2,3,3,4,4,5,5,6,6,8,8,9,9,10,10,11,11,12]
TILE_DISTRIBUTION = {
    'wood': 4,
    'brick': 3,
    'sheep': 4,
    'ore': 3,
    'wheat': 4,
    'desert': 1
}

HEX_TO_NODE_MAP = {
    0: ['node_0', 'node_1', 'node_2', 'node_3', 'node_4', 'node_5'],
    1: ['node_2', 'node_6', 'node_7', 'node_8', 'node_9', 'node_3'],
    2: ['node_7', 'node_10', 'node_11', 'node_12', 'node_13', 'node_8'],
    3: ['node_14', 'node_5', 'node_4', 'node_17', 'node_16', 'node_15'],
    4: ['node_4', 'node_3', 'node_9', 'node_19', 'node_18', 'node_17'],
    5: ['node_9', 'node_8', 'node_13', 'node_21', 'node_20', 'node_19'],
    6: ['node_13', 'node_12', 'node_51', 'node_22', 'node_52', 'node_21'],
    7: ['node_23', 'node_15', 'node_16', 'node_26', 'node_25', 'node_24'],
    8: ['node_16', 'node_17', 'node_18', 'node_28', 'node_27', 'node_26'],
    9: ['node_18', 'node_19', 'node_20', 'node_30', 'node_29', 'node_28'],
    10: ['node_20', 'node_21', 'node_52', 'node_32', 'node_31', 'node_30'],
    11: ['node_52', 'node_22', 'node_53', 'node_34', 'node_33', 'node_32'],
    12: ['node_25', 'node_26', 'node_27', 'node_37', 'node_36', 'node_35'],
    13: ['node_27', 'node_28', 'node_29', 'node_39', 'node_38', 'node_37'],
    14: ['node_29', 'node_30', 'node_31', 'node_41', 'node_40', 'node_39'],
    15: ['node_31', 'node_32', 'node_33', 'node_43', 'node_42', 'node_41'],
    16: ['node_36', 'node_37', 'node_38', 'node_46', 'node_45', 'node_44'],
    17: ['node_38', 'node_39', 'node_40', 'node_48', 'node_47', 'node_46'],
    18: ['node_40', 'node_41', 'node_42', 'node_50', 'node_49', 'node_48']    
}

CORNER_HEXES = {
    0: ['node_0', 'node_1', 'node_2', 'node_3', 'node_4', 'node_5'],
    1: ['node_7', 'node_10', 'node_11', 'node_12', 'node_13', 'node_8'],
    2: ['node_23', 'node_15', 'node_16', 'node_26', 'node_25', 'node_24'],
    3: ['node_52', 'node_22', 'node_53', 'node_34', 'node_33', 'node_32'],
    4: ['node_36', 'node_37', 'node_38', 'node_46', 'node_45', 'node_44'],
    5: ['node_40', 'node_41', 'node_42', 'node_50', 'node_49', 'node_48']
}   

COSTS_CARD = {
    'settlement': {'wood':1, 'sheep':1, 'wheat':1, 'brick':1},
    'city': {'wheat':2, 'ore':3},
    'road': {'wood':1, 'brick':1},
    'dev_card': {'wheat':1, 'ore':1, 'sheep':1}
}

DEV_DECK = ['knight'] * 14 + ['victory_point'] * 5 + ['road_building'] * 2 + ['monopoly'] * 2 + ['year_of_plenty'] * 2

PORT_TYPES = ['3:1'] * 4 + ['2:1_brick', '2:1_wood', '2:1_ore', '2:1_wheat', '2:1_sheep']

PORT_LOCATION = [
    'node_0','node_1',
    'node_6','node_7', 
    'node_12','node_51', 
    'node_53','node_34', 
    'node_42','node_43',
    'node_48', 'node_47',
    'node_45', 'node_44',
    'node_35', 'node_25',
    'node_15', 'node_14'
]

TEST_BOARD = [
    (10, 'ore'),
    (2, 'sheep'),
    (9, 'wood'),
    (12, 'wheat'),
    (6, 'brick'),
    (4, 'sheep'),
    (10, 'brick'),
    (9, 'wheat'),
    (11, 'wood'),
    (0, 'desert'),
    (3, 'wood'),
    (8, 'ore'),
    (8, 'wood'),
    (3, 'ore'),
    (4, 'wheat'),
    (5, 'sheep'),
    (5, 'brick'),
    (6, 'wheat'),
    (11, 'sheep')
]

PIP_WEIGHTS = {
    2: 1, 
    3: 2, 
    4: 3, 
    5: 4, 
    6: 5, 
    8: 5, 
    9: 4, 
    10: 3, 
    11: 2, 
    12: 1
}

STRATEGIES = ['ows, balanced, ows_hybrid']
