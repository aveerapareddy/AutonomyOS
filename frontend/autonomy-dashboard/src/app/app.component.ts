import { CommonModule } from '@angular/common';
import { Component, inject } from '@angular/core';
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
export class AppComponent {
  private readonly api = inject(MissionApiService);

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
    this.simulatorScene = buildSimulatorScene(this.execution, this.telemetryEvents);
  }

  formatVal(v: string | number | boolean | null | undefined): string {
    if (v === null || v === undefined) {
      return '—';
    }
    return String(v);
  }
}
