import random
from constants import RESOURCES, DICE_NUMBERS, TILE_DISTRIBUTION

class Hex:
    def __init__(self, resource_type, dice_number=None, node_ids = None):
        self.resource = resource_type
        self.dice_number = dice_number
        self.robber = (resource_type == 'desert')
        self.node_ids = []

    def __repr__(self):
        if self.robber:
            return f'[{self.resource} is blocked (robber)]'
        elif self.dice_number:
            return f'[{self.resource} ({self.dice_number})]'
        else: 
            return f'[{self.resource}]'
        
class Node:
    def __init__(self, id):
        self.id = id
        self.adj_hexes = []
        self.connected_nodes = set()
        self.owner = None
        self.building_type = None
        self.port = None

    def is_empty(self):
        return self.owner == None
    
    def settle(self, player_id):
        if self.is_empty():
            self.owner = player_id
            self.building_type = 'settlement'
            return True
        return False
    
    def city(self, player_id):
        if self.building_type == 'settlement' and self.owner == player_id:
            self.building_type = 'city'
            return True
        return False
    
    def __repr__(self):
        return f'node: {self.id}, owner: {self.owner}, building: {self.building_type}'

class Edge:
    def __init__(self, node1, node2):
        self.node1 = node1
        self.node2 = node2
        self.owner = None
   
    def connects(self, id):
        return id == self.node1.id or id == self.node2.id
    
    def road(self, player_id):
        if not self.owner: 
            self.owner = player_id
            return True
        return False
    
    def __repr__(self):
        show_owner = self.owner if self.owner else 'empty'
        return f'{self.node1.id} <--> {self.node2.id}, owner = {show_owner}'