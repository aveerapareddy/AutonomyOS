"""Configured token subjects/roles; no credentials are stored in application databases."""
import hashlib
import hmac
import json
from dataclasses import dataclass
from typing import Annotated
from fastapi import Header,HTTPException
from backend.core.config import get_settings

@dataclass(frozen=True)
class Principal:
    name:str
    roles:frozenset[str]
    individual:bool=False
    def require(self,role):
        if role not in self.roles:raise HTTPException(403,'Role required: '+role)


def authenticate(authorization:Annotated[str|None,Header()]=None):
    settings=get_settings()
    if settings.public_demo:raise HTTPException(403,'Operator access is disabled on the public demo')
    if not authorization or not authorization.startswith('Bearer '):raise HTTPException(401,'Bearer token required',headers={'WWW-Authenticate':'Bearer'})
    token=authorization[7:]
    if len(token)>512:raise HTTPException(401,'Invalid token')
    hashed=hashlib.sha256(token.encode()).hexdigest()
    try:
        accounts=json.loads(settings.operator_accounts_json or '[]')
        if not isinstance(accounts,list) or len(accounts)>20:raise ValueError()
        for account in accounts:
            if hmac.compare_digest(hashed,str(account['token_sha256'])):
                roles=frozenset(account['roles'])
                if not roles<= {'read','review','execute','manage'} or not str(account['name']).strip():raise ValueError()
                return Principal(str(account['name'])[:100],roles,True)
    except (ValueError,KeyError,TypeError):raise HTTPException(503,'Operator account configuration invalid')
    if len(settings.operator_token)>=24 and hmac.compare_digest(token.encode(),settings.operator_token.encode()):
        return Principal('local-operator',frozenset({'read','review','execute','manage'}))
    raise HTTPException(401,'Invalid token',headers={'WWW-Authenticate':'Bearer'})
