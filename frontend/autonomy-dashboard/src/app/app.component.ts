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
  standalone: true,
  imports: [CommonModule, FormsModule, SimulatorViewComponent],
  templateUrl: './app.component.html',
})
export class AppComponent implements OnDestroy {
  private readonly api = inject(MissionApiService);

  replayIndex = -1;
  replayPlaying = false;
  private replayTimer?: ReturnType<typeof setInterval>;

  ngOnDestroy(): void { this.stopReplay(); }

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
    // Recorded-event playback at 10 events/s, not wall-clock live simulation.
    this.replayTimer = setInterval(() => {
      if (this.replayIndex >= this.telemetryEvents.length - 1) { this.stopReplay(); return; }
      this.replayIndex++;
      this.refreshSimulatorScene();
    }, 100);
  }

  showResult(): void {
    this.stopReplay();
    this.replayIndex = -1;
    this.refreshSimulatorScene();
  }

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
    this.showResult();
    this.apiError = null;
    if (!this.currentMissionId) {
      this.apiError = 'Create a mission first';
      return;
    }
    this.runState = 'RUNNING';
    this.api.executeMission(this.currentMissionId).subscribe({
        next: (summary) => {
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
          this.runState = 'FAILED';
          this.apiError =
            typeof e?.error?.detail === 'string'
              ? e.error.detail
              : 'Execute failed';
        },
      });
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
        this.telemetryEvents = res.events;
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
    this.simulatorScene = buildSimulatorScene(this.execution, events, this.replayIndex >= 0);
  }

  formatVal(v: string | number | boolean | null | undefined): string {
    if (v === null || v === undefined) {
      return '—';
    }
    return String(v);
  }
}
