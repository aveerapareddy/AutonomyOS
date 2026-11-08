import {
  AfterViewInit,
  Component,
  ElementRef,
  HostListener,
  Input,
  OnChanges,
  OnDestroy,
  SimpleChanges,
  ViewChild,
} from '@angular/core';
import { layoutForBounds, paintSimulatorMap } from '../simulator/canvas-map';
import type { SimulatorScene } from '../simulator/simulator-scene.model';

@Component({
  selector: 'app-simulator-view',
  standalone: true,
  templateUrl: './simulator-view.component.html',
})
export class SimulatorViewComponent implements AfterViewInit, OnChanges, OnDestroy {
  @Input({ required: true }) scene!: SimulatorScene;

  @ViewChild('mapCanvas') private canvasRef?: ElementRef<HTMLCanvasElement>;

  @ViewChild('threeCanvas') private threeCanvasRef?: ElementRef<HTMLCanvasElement>;

  private viewReady = false;
  private industrial?: import('../simulator/industrial-view').IndustrialView;
  private destroyed = false;
  private viewGeneration = 0;
  viewMode: '2d' | '3d' = '2d';
  viewError = '';

  async setView(mode: '2d' | '3d'): Promise<void> {
    this.industrial?.dispose();
    this.industrial = undefined;
    const generation = ++this.viewGeneration;
    this.viewMode = mode;
    const fresh = this.threeCanvasRef?.nativeElement;
    if (!fresh) return;
    if (mode === '3d') {
      try {
        const { IndustrialView } = await import('../simulator/industrial-view');
        if (this.destroyed || generation !== this.viewGeneration) return;
        this.industrial = new IndustrialView(fresh);
        this.viewError = '';
      } catch {
        this.viewError = '3D rendering unavailable. Use the 2D view.';
        return;
      }
    }
    this.redraw();
  }

  ngOnDestroy(): void {
    this.destroyed = true;
    this.industrial?.dispose();
  }

  ngAfterViewInit(): void {
    this.viewReady = true;
    void this.setView('3d');
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['scene'] && this.viewReady) {
      this.redraw();
    }
  }

  @HostListener('window:resize')
  onResize(): void {
    if (this.viewReady) {
      this.redraw();
    }
  }

  private redraw(): void {
    const canvas = this.canvasRef?.nativeElement;
    if (!canvas || !this.scene) {
      return;
    }
    if (this.viewMode === '3d') {
      this.industrial?.update(this.scene);
      return;
    }
    const parent = canvas.parentElement;
    const rect = parent?.getBoundingClientRect();
    const cssW = rect?.width ?? 400;
    const cssH = rect?.height ?? 400;
    canvas.style.width = `${cssW}px`;
    canvas.style.height = `${cssH}px`;
    const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;
    const layout = layoutForBounds(cssW, cssH, dpr, this.scene.bounds, 0.07);
    canvas.width = layout.pixelWidth;
    canvas.height = layout.pixelHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) {
      return;
    }
    paintSimulatorMap(ctx, layout, this.scene);
  }
}
