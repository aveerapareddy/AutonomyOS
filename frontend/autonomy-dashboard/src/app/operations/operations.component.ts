import { CommonModule } from '@angular/common';
import { Component,EventEmitter,Output,OnDestroy,inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient,HttpHeaders } from '@angular/common/http';
import { finalize } from 'rxjs';
import { environment } from '../../environments/environment';
import { SimulatorViewComponent } from '../simulator-view/simulator-view.component';
import type { SimulatorScene } from '../simulator/simulator-scene.model';

@Component({selector:'app-operations',imports:[CommonModule,FormsModule,SimulatorViewComponent],templateUrl:'./operations.component.html'})
export class OperationsComponent implements OnDestroy {
 private http=inject(HttpClient);private base=environment.apiUrl.replace(/\/$/,'')+'/operations';
 @Output() sceneResult=new EventEmitter<any>();
 tab='experiments';token='';error='';busy=false;identity:any=null;
 count=5;seed=42;jobs:any[]=[];selected:any=null;knowledge:any=null;metrics:any=null;
 retrievalMethod='lexical';
 question='How are concurrent SQLite event sequence numbers allocated?';
 graph:any={nodes:[],edges:[]};focus:any=null;preview:SimulatorScene|null=null;
 siteText=JSON.stringify({name:'Warehouse transfer lane',units:'meters',bounds:[-10,10,-10,10],start:[0,-6,1.57079632679],target:[0,6],assets:[{id:'west-rack',kind:'wall',x:-3,y:0,half_extents:[.4,4,1.5]},{id:'east-rack',kind:'wall',x:3,y:0,half_extents:[.4,4,1.5]},{id:'pallet',kind:'block',x:6,y:-3,half_extents:[.6,.6,.5]}]},null,2);
 private timer?:ReturnType<typeof setTimeout>;
 ngOnDestroy():void{if(this.timer)clearTimeout(this.timer);}
 request(method:string,path:string,body:any,done:(data:any)=>void):void{
  if(this.busy)return;this.busy=true;this.error='';
  this.http.request<any>(method,this.base+path,{body,headers:new HttpHeaders({Authorization:'Bearer '+this.token})}).pipe(finalize(()=>this.busy=false)).subscribe({next:done,error:e=>this.error=typeof e?.error?.detail==='string'?e.error.detail:JSON.stringify(e?.error?.detail ?? 'Request failed')});
 }
 connect():void{this.request('GET','/identity',undefined,data=>{this.identity=data;});}
 history():void{this.request('GET','/jobs',undefined,data=>this.jobs=data);}
 open(id:string):void{
  if(this.timer)clearTimeout(this.timer);
  this.request('GET','/jobs/'+id,undefined,data=>{
   this.selected=data;
   if(data.status==='queued'||data.status==='running')this.timer=setTimeout(()=>this.open(id),1000);
  });
 }
 submit(kind:string):void{
  try{
   const request=kind==='site'?{kind,site:JSON.parse(this.siteText)}:{kind,experiment:{name:'Dashboard experiment',seed:this.seed,scenario_count:this.count,minimum_success_rate:.8}};
   this.request('POST','/jobs',{key:crypto.randomUUID(),request},data=>{this.selected=data;this.timer=setTimeout(()=>this.open(data.id),1000);});
  }catch(e){this.error='Invalid site JSON';}
 }
 cancel():void{this.request('POST','/jobs/'+this.selected.id+'/cancel',{},data=>this.selected=data);}
 blockedExample():void {
  this.siteText=JSON.stringify({name:'Blocked transfer lane',units:'meters',bounds:[-10,10,-10,10],start:[0,-6,1.57079632679],target:[0,6],assets:[{id:'closed-barrier',kind:'wall',x:0,y:0,half_extents:[10,.5,1]}]},null,2);
  this.preview=null;
 }
 validate():void{try{this.request('POST','/site/validate',JSON.parse(this.siteText),data=>{
  const site=data.site;
  this.preview={mode:'live',bounds:{minX:site.bounds[0],maxX:site.bounds[1],minY:site.bounds[2],maxY:site.bounds[3]},obstacles:site.assets.map((a:any)=>({x:a.x,y:a.y,halfExtents:a.half_extents})),obstacleHalfExtent:.5,target:{x:site.target[0],y:site.target[1]},robot:{x:site.start[0],y:site.start[1],theta:site.start[2]},plannedPath:[],executedPath:[]};
 });}catch(e){this.error='Invalid site JSON';}}
 ask():void{this.request('POST','/knowledge',{question:this.question,method:this.retrievalMethod},data=>this.knowledge=data);}
 relationships():void{this.request('GET','/graph',undefined,data=>{this.graph=data;this.focus=data.nodes[0]??null;});}
 inspectMetrics():void{this.request('GET','/metrics',undefined,data=>this.metrics=data);}
 get visibleNodes():any[]{return this.graph.nodes.slice(0,40);}
 position(id:string):{x:number;y:number}{const index=this.visibleNodes.findIndex(n=>n.id===id);const angle=index/Math.max(this.visibleNodes.length,1)*Math.PI*2;return {x:250+200*Math.cos(angle),y:230+180*Math.sin(angle)};}
 get visibleEdges():any[]{const ids=new Set(this.visibleNodes.map(n=>n.id));return this.graph.edges.filter((e:any)=>ids.has(e.source)&&ids.has(e.target));}
 get neighbors():any[]{return this.focus?this.graph.edges.filter((e:any)=>e.source===this.focus.id||e.target===this.focus.id):[];}
 viewResult():void{if(this.selected?.result?.kind==='site')this.sceneResult.emit(this.selected.result);}
 export():void{const u=URL.createObjectURL(new Blob([JSON.stringify(this.selected,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download='job-'+this.selected.id+'.json';a.click();URL.revokeObjectURL(u);}
}
