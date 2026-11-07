import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import type { SimulatorScene, Vec2 } from './simulator-scene.model';

/** Projects simulator metres into a Y-up render scene: (x, y) -> (x, height, -y). */
export class IndustrialView {
  private readonly renderer: THREE.WebGLRenderer;
  private readonly world = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(45, 1, 0.1, 500);
  private readonly controls: OrbitControls;
  private readonly content = new THREE.Group();
  private readonly resizeObserver: ResizeObserver;

  constructor(private readonly canvas: HTMLCanvasElement) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio || 1, 2));
    this.world.background = new THREE.Color('#101820');
    this.world.add(new THREE.HemisphereLight(0xc9e4ff, 0x283039, 2.5));
    const sun = new THREE.DirectionalLight(0xffffff, 3);
    sun.position.set(8, 16, 10);
    this.world.add(sun, this.content);
    this.controls = new OrbitControls(this.camera, canvas);
    this.controls.maxPolarAngle = Math.PI / 2.05;
    this.controls.minDistance = 3;
    this.controls.maxDistance = 120;
    this.controls.addEventListener('change', this.render);
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas.parentElement!);
  }

  update(scene: SimulatorScene): void {
    this.clear();
    const { minX, maxX, minY, maxY } = scene.bounds;
    const width = maxX - minX, depth = maxY - minY;
    const cx = (minX + maxX) / 2, cy = (minY + maxY) / 2;
    this.box(width, 0.12, depth, cx, -0.08, -cy, 0x273640);
    const grid = new THREE.GridHelper(Math.max(width, depth), 20, 0x52616b, 0x354650);
    grid.position.set(cx, 0, -cy);
    this.content.add(grid);
    for (const obstacle of scene.obstacles) {
      const size = scene.obstacleHalfExtent * 2;
      this.box(size, 1.2, size, obstacle.x, 0.6, -obstacle.y, 0x87949e);
      this.box(size + 0.04, 0.08, size + 0.04, obstacle.x, 1.24, -obstacle.y, 0xe6ae38);
    }
    this.path(scene.plannedPath, 0x37b7ef, 0.06);
    this.path(scene.executedPath, 0x7adea0, 0.09);
    if (scene.target) {
      const ring = new THREE.Mesh(new THREE.TorusGeometry(0.35, 0.045, 8, 40), new THREE.MeshBasicMaterial({ color: 0x7adea0 }));
      ring.rotation.x = -Math.PI / 2;
      ring.position.set(scene.target.x, 0.12, -scene.target.y);
      this.content.add(ring);
    }
    if (scene.robot) {
      const robot = new THREE.Group();
      const body = new THREE.Mesh(new THREE.BoxGeometry(0.65, 0.35, 0.48), new THREE.MeshStandardMaterial({ color: 0xf4bb40, metalness: 0.3, roughness: 0.5 }));
      body.position.y = 0.3;
      robot.add(body);
      const heading = new THREE.ArrowHelper(new THREE.Vector3(1, 0, 0), new THREE.Vector3(0, 0.55, 0), 0.7, 0xffffff);
      robot.add(heading);
      robot.position.set(scene.robot.x, 0, -scene.robot.y);
      robot.rotation.y = scene.robot.theta;
      this.content.add(robot);
    }
    if (!this.initialized) {
      const span = Math.max(width, depth, 5);
      this.camera.position.set(cx + span * 0.8, span * 0.85, -cy + span * 0.8);
      this.controls.target.set(cx, 0, -cy);
      this.controls.update();
      this.initialized = true;
    }
    this.resize();
  }

  private initialized = false;
  private box(w: number, h: number, d: number, x: number, y: number, z: number, color: number): void {
    const mesh = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), new THREE.MeshStandardMaterial({ color, roughness: 0.7 }));
    mesh.position.set(x, y, z);
    this.content.add(mesh);
  }
  private path(points: Vec2[], color: number, height: number): void {
    if (points.length < 2) return;
    const geometry = new THREE.BufferGeometry().setFromPoints(points.map(p => new THREE.Vector3(p.x, height, -p.y)));
    this.content.add(new THREE.Line(geometry, new THREE.LineBasicMaterial({ color })));
  }
  private resize(): void {
    const rect = this.canvas.parentElement!.getBoundingClientRect();
    this.renderer.setSize(Math.max(rect.width - 16, 1), Math.max(rect.height - 16, 320), false);
    this.camera.aspect = this.canvas.width / this.canvas.height;
    this.camera.updateProjectionMatrix();
    this.render();
  }
  private render = (): void => { this.renderer.render(this.world, this.camera); };
  private clear(): void {
    this.content.traverse(object => {
      if (object instanceof THREE.Mesh || object instanceof THREE.Line) {
        object.geometry.dispose();
        const materials = Array.isArray(object.material) ? object.material : [object.material];
        materials.forEach(material => material.dispose());
      }
    });
    this.content.clear();
  }
  dispose(): void {
    this.resizeObserver.disconnect();
    this.controls.dispose();
    this.clear();
    this.renderer.dispose();
  }
}
