import {
  AfterViewInit,
  Component,
  ElementRef,
  HostListener,
  Input,
  OnChanges,
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
export class SimulatorViewComponent implements AfterViewInit, OnChanges {
  @Input({ required: true }) scene!: SimulatorScene;

  @ViewChild('mapCanvas') private canvasRef?: ElementRef<HTMLCanvasElement>;

  private viewReady = false;

  ngAfterViewInit(): void {
    this.viewReady = true;
    this.redraw();
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
