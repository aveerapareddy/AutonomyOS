"""Validated metric site/occupancy interchange. No arbitrary asset URLs or code."""
import math
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,model_validator
from backend.scenarios.scenario_config import ScenarioConfig
from backend.experiments.runner import digest

class Asset(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    id:str=Field(pattern=r'^[A-Za-z0-9_-]{1,40}$')
    kind:Literal['wall','block']='block'
    x:float
    y:float
    half_extents:tuple[float,float,float]=(.5,.5,.5)

class SiteSpec(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    name:str=Field(default='Imported site',min_length=1,max_length=80)
    units:Literal['meters']='meters'
    bounds:tuple[float,float,float,float]=(-10,10,-10,10)
    start:tuple[float,float,float]=(0,0,0)
    target:tuple[float,float]=(5,3)
    assets:list[Asset]=Field(default_factory=list,max_length=100)

    @model_validator(mode='after')
    def validate_geometry(self):
        a,b,c,d=self.bounds
        if not all(-50<=v<=50 for v in self.bounds) or not (2<=b-a<=40 and 2<=d-c<=40):
            raise ValueError('Bounds must describe a 2..40 meter site within ±50 meters')
        if len({x.id for x in self.assets})!=len(self.assets):raise ValueError('Duplicate asset IDs')
        for asset in self.assets:
            hx,hy,hz=asset.half_extents
            if not all(.05<=h<=10 for h in (hx,hy,hz)):raise ValueError('Asset half-extents outside .05..10m')
            if not (a<=asset.x-hx<asset.x+hx<=b and c<=asset.y-hy<asset.y+hy<=d):raise ValueError('Asset outside site')
        for x,y in [self.start[:2],self.target]:
            if not (a+.3<=x<=b-.3 and c+.3<=y<=d-.3):raise ValueError('Start/target outside navigable bounds')
            if any(abs(x-o.x)<=o.half_extents[0]+.3 and abs(y-o.y)<=o.half_extents[1]+.3 for o in self.assets):raise ValueError('Start/target intersects inflated obstacle')
        if math.dist(self.start[:2],self.target)<.5:raise ValueError('Start and target too close')
        return self

    def scenario(self):
        return ScenarioConfig(scenario_id=digest(self.model_dump())[:32],scenario_name=self.name,
            world_bounds=self.bounds,robot_start_position=self.start,target_position=self.target,
            obstacle_positions=[(a.x,a.y) for a in self.assets],obstacle_types=[a.kind for a in self.assets],
            obstacle_half_extents=[a.half_extents for a in self.assets])

class OccupancyImport(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
    name:str=Field(default='Occupancy import',max_length=80)
    resolution:float=Field(ge=.25,le=2)
    origin:tuple[float,float]=(0,0)
    cells:list[list[Literal[0,1]]]=Field(min_length=2,max_length=40)
    start:tuple[float,float,float]
    target:tuple[float,float]

    def to_site(self):
        cols=len(self.cells[0]);rows=len(self.cells)
        if not 2<=cols<=40 or any(len(row)!=cols for row in self.cells):raise ValueError('Occupancy grid must be rectangular, 2..40 cells per side')
        x,y=self.origin;r=self.resolution
        assets=[Asset(id=f'cell_{i}_{j}',x=x+(j+.5)*r,y=y+(i+.5)*r,half_extents=(r/2,r/2,.5))
                for i,row in enumerate(self.cells) for j,value in enumerate(row) if value]
        return SiteSpec(name=self.name,bounds=(x,x+cols*r,y,y+rows*r),start=self.start,target=self.target,assets=assets)
