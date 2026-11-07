import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';
import type {
  MissionExecutionSummary,
  MissionResponse,
  TelemetryQueryResponse,
} from '../models/api.types';

@Injectable({ providedIn: 'root' })
export class MissionApiService {
  private readonly http = inject(HttpClient);
  private readonly base = environment.apiUrl.replace(/\/$/, '');

  createMission(missionText: string, worldId?: string): Observable<MissionResponse> {
    const body: { mission_text: string; world_id?: string } = {
      mission_text: missionText,
    };
    if (worldId) {
      body.world_id = worldId;
    }
    return this.http.post<MissionResponse>(`${this.base}/missions`, body);
  }

  executeMission(missionId: string): Observable<MissionExecutionSummary> {
    return this.http.post<MissionExecutionSummary>(
      `${this.base}/missions/${encodeURIComponent(missionId)}/execute`,
      {},
    );
  }

  getTelemetry(missionId: string): Observable<TelemetryQueryResponse> {
    return this.http.get<TelemetryQueryResponse>(
      `${this.base}/missions/${encodeURIComponent(missionId)}/telemetry`,
    );
  }
}
