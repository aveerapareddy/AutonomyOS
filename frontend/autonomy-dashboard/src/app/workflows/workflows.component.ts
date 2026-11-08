import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { finalize } from 'rxjs';
import { environment } from '../../environments/environment';

@Component({
 selector:'app-workflows', imports:[CommonModule,FormsModule],
 templateUrl:'./workflows.component.html',
})
export class WorkflowsComponent {
 private http=inject(HttpClient);
 private base=environment.apiUrl.replace(/\/$/,'')+'/workflows';
 reportText='';
 token=''; actor=''; reason=''; error=''; busy=false;
 entries: {id:string;status:string;created_at:number}[]=[];
 selected: any=null;
 get headers():HttpHeaders { return new HttpHeaders({Authorization:'Bearer '+this.token}); }
 request(method:string,path:string,body?:unknown):void {
   if(this.busy)return;
   this.busy=true;this.error='';
   this.http.request<any>(method,this.base+path,{body,headers:this.headers}).pipe(finalize(()=>this.busy=false)).subscribe({
    next:result=> {if(Array.isArray(result))this.entries=result;else this.selected=result;},
    error:e=>this.error=typeof e?.error?.detail==='string'?e.error.detail:'Request failed. Check the report and operator connection.',
   });
 }
 connect():void { this.request('GET',''); }
 open(id:string):void { this.request('GET','/'+id); }
 importText():void {
   try {
    if(new TextEncoder().encode(this.reportText).length>256000)throw new Error('Report must be smaller than 256 KB');
    this.request('POST','/import',JSON.parse(this.reportText));
   }catch(e){this.error=e instanceof Error?e.message:'Invalid report';}
 }
 async importFile(event:Event):Promise<void> {
   const input=event.target as HTMLInputElement; const file=input.files?.[0];
   if(!file)return;
   try {
    if(file.size>256000)throw new Error('Report must be smaller than 256 KB');
    const report=JSON.parse(await file.text());
    this.request('POST','/import',report);
   }catch(e){this.error=e instanceof Error?e.message:'Invalid report';}
   input.value='';
 }
 approve():void {this.request('POST','/'+this.selected.id+'/approve',{digest:this.selected.digest,actor:this.actor});}
 reject():void {this.request('POST','/'+this.selected.id+'/reject',{actor:this.actor,reason:this.reason});}
 execute():void {this.request('POST','/'+this.selected.id+'/execute',{});}
 download():void {
   const blob=new Blob([JSON.stringify(this.selected,null,2)],{type:'application/json'});
   const url=URL.createObjectURL(blob);const link=document.createElement('a');link.href=url;
   link.download='workflow-'+this.selected.id+'.json';link.click();URL.revokeObjectURL(url);
 }
}
