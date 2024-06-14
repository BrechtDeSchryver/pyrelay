import os
import sys
import importlib
import inspect
from Networking.PacketHelper import isValidPacket

def findClass(func):
    return getattr(inspect.getmodule(func), func.__qualname__.split(".<locals>", 1)[0].rsplit(".", 1)[0])

class PacketHookManager:
    def __init__(self):
        self._funcs = {}
        self._classes = []

    def addHook(self, packetType, func):
        if isValidPacket(packetType.upper()):
            if packetType in self._funcs:
                self._funcs[packetType].append(func)
            else:
                self._funcs[packetType] = [func]
        else:
            print("WARNING: hooked packet", packetType, "is not a valid packet type")

    def addClass(self, cls):
        self._classes.append(cls)

    def callHooks(self, client, packet):
        if packet.type in self._funcs:
            for func in self._funcs[packet.type]:
                for cls in self._classes:
                    if type(cls) == findClass(func):
                        if type(cls) == type(client):
                            func(client, packet)
                        else:
                            func(cls, client, packet)
    
    def resetPlugins(self):
        #Remove all plugin hooks and classes, but keep client hooks and classes
        new_funcs = {}
        for packetType in self._funcs:
            hooks = []
            for func in self._funcs[packetType]:
                if "Client." in str(func):
                    hooks.append(func)
            if len(hooks) > 0:
                new_funcs[packetType] = hooks
        self._funcs = new_funcs
            
        self._classes = [c for c in self._classes 
                         if "Client.Client" in str(type(c))]

