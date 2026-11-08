import { OperationsComponent } from './operations/operations.component';
import { WorkflowsComponent } from './workflows/workflows.component';
import { CommonModule } from '@angular/common';
import { Component, inject, OnDestroy } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SimulatorViewComponent } from './simulator-view/simulator-view.component';
import { buildSimulatorScene } from './simulator/simulator-scene.adapter';
import type { MissionExecutionSummary, TelemetryEvent } from './models/api.types';
import type { SimulatorScene } from './simulator/simulator-scene.model';
import { MissionApiService } from './services/mission-api.service';

type HeaderRunState = 'READY' | 'RUNNING' | 'COMPLETED' | 'FAILED';

@Component({
  selector: 'app-root',
  imports: [CommonModule, FormsModule, SimulatorViewComponent, WorkflowsComponent, OperationsComponent],
  templateUrl: './app.component.html',
})
export class AppComponent implements OnDestroy {
  private readonly api = inject(MissionApiService);
  publicDemo=false;
  constructor(){this.api.capabilities().subscribe({next:state=>this.publicDemo=state.public_demo,error:()=>{}});}

  replayIndex = -1;
  replayPlaying = false;
  private replayTimer?: ReturnType<typeof setInterval>;

  private liveTimer?: ReturnType<typeof setInterval>;
  private polling = false;
  private stream?:EventSource;
  private runCursor = 0;
  telemetryConnection = 'Idle';
  ngOnDestroy(): void { this.stopReplay(); this.stopLive(); }

  private stopLive(): void {
    if(this.liveTimer) clearInterval(this.liveTimer);
    this.liveTimer=undefined;
    this.stream?.close();this.stream=undefined;
  }

  private pollLive(): void {
    if(this.polling || !this.currentMissionId)return;
    this.polling=true; const id=this.currentMissionId;
    const cursor=this.telemetryEvents.at(-1)?.sequence ?? this.runCursor;
    this.api.getTelemetry(id,cursor).subscribe({
      next:res=>{
        this.polling=false; if(id!==this.currentMissionId)return;
        const events=new Map(this.telemetryEvents.map(e=>[e.sequence,e]));
        for(const event of res.events)events.set(event.sequence,event);
        this.telemetryEvents=[...events.values()].sort((a,b)=>a.sequence-b.sequence);
        this.telemetryConnection='Connected · incremental polling';
        this.refreshSimulatorScene();
      },
      error:()=>{this.polling=false;this.telemetryConnection='Reconnecting from last event…';},
    });
  }

  stopReplay(): void {
    if (this.replayTimer) clearInterval(this.replayTimer);
    this.replayTimer = undefined;
    this.replayPlaying = false;
  }

  seekReplay(value: number): void {
    this.stopReplay();
    this.replayIndex = Math.max(0, Math.min(Number(value), this.telemetryEvents.length - 1));
    this.refreshSimulatorScene();
  }

  playReplay(): void {
    if (this.replayPlaying) { this.stopReplay(); return; }
    if (!this.telemetryEvents.length) return;
    if (this.replayIndex < 0 || this.replayIndex >= this.telemetryEvents.length - 1) this.replayIndex = 0;
    this.replayPlaying = true;
    this.refreshSimulatorScene();
    this.scheduleReplay();
  }

  get replaySeconds():number {
    const events=this.replayIndex<0?this.telemetryEvents:this.telemetryEvents.slice(0,this.replayIndex+1);
    const last=[...events].reverse().find(e=>typeof e.payload['simulation_time_seconds']==='number');
    return Number(last?.payload['simulation_time_seconds'] ?? 0);
  }

  private scheduleReplay():void {
    if(this.replayIndex>=this.telemetryEvents.length-1){this.stopReplay();return;}
    const current=this.replaySeconds;
    const next=this.telemetryEvents[this.replayIndex+1];
    const nextTime=Number(next.payload['simulation_time_seconds'] ?? current);
    const delay=Math.max(0,(nextTime-current)*1000);
    this.replayTimer=setTimeout(()=>{
      this.replayIndex++;this.refreshSimulatorScene();this.scheduleReplay();
    },delay);
  }

  showResult(): void {
    this.stopReplay();
    this.replayIndex = -1;
    this.refreshSimulatorScene();
  }

  activePanel = 'mission';
  missionText = '';
  currentMissionId: string | null = null;
  runState: HeaderRunState = 'READY';
  plannerModeHeader = '—';
  apiError: string | null = null;

  plannerSnapshot: {
    planner_mode?: string | null;
    goal_type?: string | null;
    target_label?: string | null;
    constraints: string[];
    plan_steps: string[];
  } | null = null;

  execution: MissionExecutionSummary | null = null;
  telemetryEvents: TelemetryEvent[] = [];
  simulatorScene: SimulatorScene = buildSimulatorScene(null, []);

  get telemetryDisplay(): TelemetryEvent[] {
    return [...this.telemetryEvents].reverse();
  }

  createMission(): void {
    if(this.runState==='RUNNING')return;
    this.stopLive();
    this.showResult();
    this.apiError = null;
    const text = this.missionText.trim();
    if (!text) {
      this.apiError = 'Mission text required';
      return;
    }
    this.api.createMission(text).subscribe({
      next: (res) => {
        this.currentMissionId = res.mission_id;
        this.runState = 'READY';
        this.execution = null;
        this.plannerSnapshot = null;
        this.telemetryEvents = [];
        this.refreshSimulatorScene();
      },
      error: (e) => {
        this.apiError = e?.error?.detail ?? 'Create mission failed';
      },
    });
  }

  executeMission(): void {
    if(this.runState==='RUNNING')return;
    this.showResult();
    this.apiError = null;
    if (!this.currentMissionId) {
      this.apiError = 'Create a mission first';
      return;
    }
    this.runState = 'RUNNING';
    this.runCursor=this.telemetryEvents.at(-1)?.sequence ?? 0;
    this.execution=null; this.telemetryEvents=[];
    this.telemetryConnection='Connecting…';
    this.stream=this.api.telemetryStream(this.currentMissionId,this.runCursor);
    this.stream.addEventListener('telemetry',(event:MessageEvent)=>{
      const item=JSON.parse(event.data) as TelemetryEvent;
      const events=new Map(this.telemetryEvents.map(e=>[e.sequence,e]));events.set(item.sequence,item);
      this.telemetryEvents=[...events.values()].sort((a,b)=>a.sequence-b.sequence);
      this.telemetryConnection='Connected · live event stream';this.refreshSimulatorScene();
    });
    this.stream.addEventListener('terminal',()=>this.stopLive());
    this.stream.onerror=()=>{if(this.runState==='RUNNING')this.telemetryConnection='Reconnecting from last event…';};
    this.api.executeMission(this.currentMissionId).subscribe({
        next: (summary) => {
          this.stopLive();
          this.applyExecution(summary);
          this.runState =
            summary.status === 'completed'
              ? 'COMPLETED'
              : summary.status === 'failed'
                ? 'FAILED'
                : 'COMPLETED';
          this.loadTelemetry();
        },
        error: (e) => {
          this.stopLive();
          this.runState = 'FAILED';
          this.apiError =
            typeof e?.error?.detail === 'string'
              ? e.error.detail
              : 'Execute failed';
        },
      });
  }

  showSiteResult(result:any):void {
    this.activePanel='mission';
    this.stopLive();this.stopReplay();this.replayIndex=-1;
    this.currentMissionId=null;this.runState=result.summary.status==='completed'?'COMPLETED':'FAILED';
    this.telemetryEvents=result.telemetry;this.telemetryConnection='Saved isolated site execution';
    this.applyExecution(result.summary);
    window.scrollTo({top:0,behavior:'smooth'});
  }

  private applyExecution(summary: MissionExecutionSummary): void {
    this.execution = summary;
    this.plannerModeHeader = summary.planner_mode ?? '—';
    this.plannerSnapshot = {
      planner_mode: summary.planner_mode,
      goal_type: summary.goal_type,
      target_label: summary.target_label,
      constraints: summary.constraints ?? [],
      plan_steps: summary.plan_steps ?? [],
    };
    this.refreshSimulatorScene();
  }

  private loadTelemetry(): void {
    if (!this.currentMissionId) {
      return;
    }
    this.api.getTelemetry(this.currentMissionId).subscribe({
      next: (res) => {
        this.telemetryEvents = res.events.filter(e=>e.sequence>this.runCursor);
        this.refreshSimulatorScene();
      },
      error: () => {
        this.telemetryEvents = [];
        this.refreshSimulatorScene();
      },
    });
  }

  private refreshSimulatorScene(): void {
    const events = this.replayIndex < 0 ? this.telemetryEvents : this.telemetryEvents.slice(0, this.replayIndex + 1);
    this.simulatorScene = buildSimulatorScene(this.execution, events, this.replayIndex >= 0 || this.runState === 'RUNNING');
  }

  formatVal(v: string | number | boolean | null | undefined): string {
    if (v === null || v === undefined) {
      return '—';
    }
    return String(v);
  }
}
