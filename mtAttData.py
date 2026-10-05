class attData():
    US:float
    DS:float

    def __init__(self, US:float, DS:float):
        self.US=US
        self.DS=DS
    
    def __add__(self, operand:'attData'):
        return attData(self.US+operand.US,  self.DS+operand.DS)
   
    def getUS(self):
        return self.US
    
    def getDS(self):
        return self.DS
    
    def __mul__(self, operand:float):
        return attData(self.US * operand, self.DS*operand)
    
    def __rmul__(self,operand:float):
        return attData(self.US * operand, self.DS*operand)
    
    @classmethod
    def sameAtt(cls,val:float):
        return attData(val,val)