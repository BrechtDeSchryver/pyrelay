from pydantic import BaseModel
from typing import List

class CharDataSchema(BaseModel):
    charIds: List[int]
    currentCharId: int
    nextCharId: int
    maxNumChars: int

        
