class mtOrder():
    TOTAL_GROUPS = 6
    MAX_GROUP = 1000
    MAJOR_MULT = 100
    value: int
    groups: 'list[int]'
    level: int
    
    def __init__(self, value: int):
        self.value = value
        self.groups = self._splitGroups(value)
        self.level = len(self.groups)

    @classmethod
    def fromGroups(cls, groups: 'list[int]'):
        myOrder=mtOrder(1)
        myOrder.setGroups(groups=groups)
        return myOrder

    def _splitGroups(self, value: int) -> 'list[int]':
        groups = []

        while value > 0:
            groups.append(value % self.MAX_GROUP)
            value //= self.MAX_GROUP

        # Remove zero groups from the least-significant side
        while groups and groups[0] == 0:
            groups.pop(0)

        return groups[::-1] if groups else []

    def _cleanGroups(self):
        while self.groups and self.groups[-1]==0:
            self.groups.pop(-1)

    def toInt(self) -> int|None:
       
        if len(self.groups)==0:
            return None
        # Pad missing groups on the right with zeros
        padded = self.groups + [0] * (self.TOTAL_GROUPS - len(self.groups))

        result = 0

        for group in padded[:-1]:
            result += group
            result *= self.MAX_GROUP
        
        # last group added without multiplying after
        result += padded[-1]
        return result
    
    def setGroups(self,groups: 'list[int]'):
        assert len(groups)<=self.TOTAL_GROUPS
        self.groups=groups
        self._cleanGroups()
        self.level=len(groups)
        self.value=self.toInt()
        return self

    def getGroupAtLevel(self, level:int ):
        assert 0<= level <=self.level
        if level==0:
            return 0
        else:
            return self.groups[level-1]
    
    def setOrderFromDelimString(self, myStrOrder: str, delim: str="."):
        strList=myStrOrder.split(delim)
        myGroups=[int(x)+self.MAJOR_MULT for x in strList]
        assert len(myGroups)<=self.TOTAL_GROUPS
        assert all( 0 <= n < self.MAX_GROUP for n in myGroups)
        self.setGroups(myGroups)
        return self

    def getFirstOrder(self) -> int:
        if self.level>0:
            return self.groups[0]
        else:
            return 0
        
    def getLastOrder(self) -> int:
        if self.level>0:
            return self.groups[-1]
        else:
            return 0

    @classmethod
    def getMajorOrder(cls, groupVal:int) ->int:
        return int(groupVal/(cls.MAJOR_MULT))
    
    @classmethod
    def getMinorOrder(cls, groupVal:int) ->int:
        return int(groupVal%(cls.MAJOR_MULT))

    def getFirstMajorOrder(self) ->int:
        #devuelte los digitos del MajorOrder (los mas significativos) del ultimo grupo
        return mtOrder.getMajorOrder(self.getFirstOrder())
    
    def getFirstMinorOrder(self) ->int:
        #devuelte los digitos del Minororder (los menos significativos) del ultimo grupo
        return mtOrder.getMinorOrder(self.getFirstOrder())
    
    def getLastMajorOrder(self) ->int:
        #devuelte los digitos del MajorOrder (los mas significativos) del ultimo grupo
        return mtOrder.getMajorOrder(self.getLastOrder())
   
    def getLastMinorOrder(self) ->int:
        #devuelte los digitos del Minororder (los menos significativos) del ultimo grupo
        return mtOrder.getMinorOrder(self.getLastOrder())

    def setLastOrder(self, newOrder: int=1):
        assert 0 <= newOrder < self.MAX_GROUP
        self.groups[-1]=newOrder
        self.setGroups(self.groups)
        return self

    def parentOrder(self) -> 'mtOrder':
        return mtOrder.fromGroups(self.groups[:-1])
    
    def appendOrder(self,newOrder: int=1):
        assert self.level<self.TOTAL_GROUPS and 0 <= newOrder < self.MAX_GROUP, f"{self} - {newOrder}"
        if newOrder>0:
            self.groups.append(newOrder)
        self.setGroups(self.groups)
        return self
    
    def getName(self) -> 'str':
        myStr=".".join([str(x-self.MAJOR_MULT) for x in self.groups])
        return myStr

    def clearOrder(self):
        self.value=None
        self.groups=[]
        self.level=0
        return self

    def __repr__(self):
        return f"Order={self.groups} - value {self.value} - {self.level})"
