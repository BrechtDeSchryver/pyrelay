from Constants.Constants import Constants
class StatData:
    def __init__(self, statType=0, statValue=0, strStatValue="", secondaryValue=0):
        self.constants = Constants() # change this funky wunky malloc 
        self.statType = statType
        self.statValue = statValue
        self.strStatValue = strStatValue
        self.secondaryValue = secondaryValue

    def isStringStat(self):
        return self.statType in [self.constants.statTypesToInt.get("EXPSTAT"), self.constants.statTypesToInt.get("NAMESTAT"), self.constants.statTypesToInt.get("ACCOUNTIDSTAT"), self.constants.statTypesToInt.get("GUILDNAMESTAT"),
                                 self.constants.statTypesToInt.get("PETNAMESTAT"), self.constants.statTypesToInt.get("GRAVEACCOUNTID"), self.constants.statTypesToInt.get("OWNERACCOUNTIDSTAT"),
                                 self.constants.statTypesToInt.get("ENCHANTMENTS"), self.constants.statTypesToInt.get("UNKNOWN121"), self.constants.statTypesToInt.get("UNKNOWN127"), self.constants.statTypesToInt.get("UNKNOWN128"),
                                 self.constants.statTypesToInt.get("UNKNOWN147"), self.constants.statTypesToInt.get("DUSTAMOUNT"), self.constants.statTypesToInt.get("DUSTLIMIT")]
    def nameOf(self,statType):
        if statType in self.constants.statTypesToInt.values():
            for key in self.constants.statTypesToInt.keys():
                if statType == self.constants.statTypesToInt[key]:
                    return key
        return "UNKNOWNSTAT"

    def statToName(self, statType=None):
        if statType is None:
            return self.nameOf(self.statType)
        else:
            return self.nameOf(statType)   

    def read(self, reader):
        self.statType = reader.readUnsignedByte()
        if self.isStringStat():
            self.strStatValue = reader.readStr()
        else:
            self.statValue = reader.readCompressedInt()
        self.secondaryValue = reader.readCompressedInt()

    def write(self, writer):
        writer.writeUnsignedByte(self.statType)
        if self.isStringStat():
            writer.writeStr(self.strStatValue)
        else:
            writer.writeCompressedInt(self.statValue)
        writer.writeCompressedInt(self.secondaryValue)

    def clone(self):
        return StatData(self.statType, self.statValue, self.strStatValue, self.secondaryValue)

    def __str__(self):
        if self.isStringStat():
            return "statType: {}\nstrStatValue: {}\nsecondaryValue: {}".format(self.statType, self.strStatValue, self.secondaryValue)
        else:
            return "statType: {}\nstatValue: {}\nsecondaryValue: {}".format(self.statType, self.statValue, self.secondaryValue)

