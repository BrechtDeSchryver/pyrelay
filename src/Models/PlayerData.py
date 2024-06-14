from Constants.Constants import Constants

class PlayerData:
    def __init__(self,constants:Constants):
        self.constants=constants
        self.INV = [-1 for _ in range(20)]
        self.pos = None
        self.objectId = 0

    def parse(self, obj):
        self.characterClass = obj.objectType
        self.pos = obj.status.pos
        self.objectId = obj.status.objectId
        self.parseStats(obj.status.stats)

    def parseStats(self, stats):
        for stat in stats:
            attribute_key = self.constants.intToStatTypes.get(stat.statType)
            print(attribute_key)
            if attribute_key:
                if self.constants.statTypesToInt.get("INVENTORY0STAT") <= stat.statType <= self.constants.statTypesToInt.get("INVENTORY11STAT"):
                    index = stat.statType - self.constants.statTypesToInt.get("INVENTORY0STAT")
                    self.INV[index] = stat.statValue
                elif self.constants.statTypesToInt.get("BACKPACK0STAT") <= stat.statType <= self.constants.statTypesToInt.get("BACKPACK7STAT"):
                    index = stat.statType - self.constants.statTypesToInt.get("BACKPACK0STAT") + 12
                    self.INV[index] = stat.statValue
                elif attribute_key in ['HASBACKPACK', 'NAMECHOSEN', 'XPBOOSTED']:
                    setattr(self, attribute_key, bool(stat.statValue))
                elif attribute_key in ['PROJSPEEDMULT', 'PROJLIFEMULT', 'EXALTATIONBONUSDMG']:
                    setattr(self, attribute_key, stat.statValue / 1000)
                else:
                    setattr(self, attribute_key, stat.statValue)
    def __str__(self):
        out = ""
        for key in self.__dict__:
            out += "{}: {}\n".format(key, self.__dict__[key])
        return out[:-1]
