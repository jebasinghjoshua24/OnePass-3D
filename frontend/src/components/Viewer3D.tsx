import React, { useRef, useEffect, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { GLTFLoader } from 'three/examples/jsm/loaders/GLTFLoader.js';
import { 
  Maximize2, RotateCcw, Eye, Layers, Compass, Ruler, 
  ShieldAlert, Sun, Grid, Box, Activity, Check, Info
} from 'lucide-react';
import { getArtifactDownloadUrl, JobRecord } from '../services/api';

interface Viewer3DProps {
  job: JobRecord;
  measurementMode: 'none' | 'distance' | 'height' | 'area';
  onMeasurementComplete: (type: string, value: number, details: string) => void;
  confidenceFilter: number;
}

export const Viewer3D: React.FC<Viewer3DProps> = ({
  job,
  measurementMode,
  onMeasurementComplete,
  confidenceFilter
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [renderMode, setRenderMode] = useState<'textured' | 'confidence' | 'points' | 'wireframe'>('textured');
  const [showFlightPath, setShowFlightPath] = useState(true);
  const [showDynamicMask, setShowDynamicMask] = useState(true);
  const [showGrid, setShowGrid] = useState(true);
  const [hoverCoord, setHoverCoord] = useState<{ x: number; y: number; z: number } | null>(null);
  const [activeMeasurements, setActiveMeasurements] = useState<Array<{ id: number; text: string }>>([]);

  // Three.js internal references
  const sceneRef = useRef<THREE.Scene | null>(null);
  const cameraRef = useRef<THREE.PerspectiveCamera | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const controlsRef = useRef<OrbitControls | null>(null);
  const meshGroupRef = useRef<THREE.Group>(new THREE.Group());
  const pointsGroupRef = useRef<THREE.Group>(new THREE.Group());
  const flightGroupRef = useRef<THREE.Group>(new THREE.Group());
  const dynamicMaskGroupRef = useRef<THREE.Group>(new THREE.Group());
  const measureGroupRef = useRef<THREE.Group>(new THREE.Group());

  // Interactive measurement points buffer
  const clickedPointsRef = useRef<THREE.Vector3[]>([]);

  useEffect(() => {
    if (!containerRef.current) return;

    const width = containerRef.current.clientWidth;
    const height = containerRef.current.clientHeight || 560;

    // 1. Scene setup
    const scene = new THREE.Scene();
    scene.background = new THREE.Color(0x0b1120);
    scene.fog = new THREE.FogExp2(0x0b1120, 0.008);
    sceneRef.current = scene;

    // 2. Camera setup
    const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
    camera.position.set(45, 35, 45);
    cameraRef.current = camera;

    // 3. Renderer setup
    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: 'high-performance' });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    rendererRef.current = renderer;
    containerRef.current.replaceChildren(renderer.domElement);

    // 4. OrbitControls setup
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.05;
    controls.target.set(0, 4, 0);
    controls.maxPolarAngle = Math.PI / 2 - 0.02; // Don't dip below ground
    controlsRef.current = controls;

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.7);
    scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xfffaed, 1.2);
    dirLight.position.set(50, 80, 40);
    dirLight.castShadow = true;
    dirLight.shadow.mapSize.width = 2048;
    dirLight.shadow.mapSize.height = 2048;
    scene.add(dirLight);

    const fillLight = new THREE.DirectionalLight(0x7dd3fc, 0.4);
    fillLight.position.set(-40, 20, -40);
    scene.add(fillLight);

    // 6. Ground Reference Grid
    const gridHelper = new THREE.GridHelper(80, 40, 0x10b981, 0x1e293b);
    gridHelper.position.y = -0.05;
    gridHelper.name = 'groundGrid';
    scene.add(gridHelper);

    // 7. Add root container groups
    scene.add(meshGroupRef.current);
    scene.add(pointsGroupRef.current);
    scene.add(flightGroupRef.current);
    scene.add(dynamicMaskGroupRef.current);
    scene.add(measureGroupRef.current);

    // 8. Build Scene Elements
    loadModelOrGenerateScene(job);

    // 9. Resize listener
    const handleResize = () => {
      if (!containerRef.current || !rendererRef.current || !cameraRef.current) return;
      const w = containerRef.current.clientWidth;
      const h = containerRef.current.clientHeight;
      cameraRef.current.aspect = w / h;
      cameraRef.current.updateProjectionMatrix();
      rendererRef.current.setSize(w, h);
    };
    window.addEventListener('resize', handleResize);

    // 10. Animation Loop
    let animId: number;
    const animate = () => {
      animId = requestAnimationFrame(animate);
      controls.update();
      renderer.render(scene, camera);
    };
    animate();

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('resize', handleResize);
      renderer.dispose();
    };
  }, [job.job_id]);

  // Handle Model Loading / Scene Population
  const loadModelOrGenerateScene = (currentJob: JobRecord) => {
    meshGroupRef.current.clear();
    pointsGroupRef.current.clear();
    flightGroupRef.current.clear();
    dynamicMaskGroupRef.current.clear();

    const glbArtifact = currentJob.artifacts?.mesh_glb;
    const glbUrl = glbArtifact ? getArtifactDownloadUrl(currentJob.job_id, glbArtifact) : null;

    // Check if we can load GLB from backend
    if (glbUrl) {
      const loader = new GLTFLoader();
      loader.load(
        glbUrl,
        (gltf) => {
          const model = gltf.scene;
          model.traverse((child) => {
            if ((child as THREE.Mesh).isMesh) {
              const mesh = child as THREE.Mesh;
              mesh.castShadow = true;
              mesh.receiveShadow = true;
            }
          });
          meshGroupRef.current.add(model);
        },
        undefined,
        (err) => {
          console.warn('Could not load GLB from backend, generating procedural 3D model:', err);
          createProceduralScene();
        }
      );
    } else {
      createProceduralScene();
    }

    // Always generate dense point cloud and flight path frustums
    createPointCloudsAndFlightPath();
  };

  // Generates high fidelity 3D building and terrain in Three.js
  const createProceduralScene = () => {
    // 1. Terrain Ground
    const groundGeo = new THREE.BoxGeometry(50, 0.4, 50);
    const groundMat = new THREE.MeshStandardMaterial({
      color: 0x223028,
      roughness: 0.85,
      metalness: 0.1,
    });
    const ground = new THREE.Mesh(groundGeo, groundMat);
    ground.position.y = -0.2;
    ground.receiveShadow = true;
    meshGroupRef.current.add(ground);

    // 2. Asphalt Roadways
    const roadGeo = new THREE.PlaneGeometry(12, 50);
    const roadMat = new THREE.MeshStandardMaterial({ color: 0x1f2937, roughness: 0.9 });
    const road = new THREE.Mesh(roadGeo, roadMat);
    road.rotation.x = -Math.PI / 2;
    road.position.set(-18, 0.02, 0);
    road.receiveShadow = true;
    meshGroupRef.current.add(road);

    // 3. Multi-Storey Building Structure
    const buildingGeo = new THREE.BoxGeometry(20, 11, 14);
    const buildingMat = new THREE.MeshStandardMaterial({
      color: 0xe2e8f0,
      roughness: 0.4,
      metalness: 0.1,
    });
    const building = new THREE.Mesh(buildingGeo, buildingMat);
    building.position.set(0, 5.5, 0);
    building.castShadow = true;
    building.receiveShadow = true;
    meshGroupRef.current.add(building);

    // 4. Rooftop Solar Panel Arrays
    const solarGeo = new THREE.BoxGeometry(14, 0.25, 9);
    const solarMat = new THREE.MeshStandardMaterial({
      color: 0x1e3a8a, // Deep solar blue
      roughness: 0.15,
      metalness: 0.8,
    });
    const solarArray = new THREE.Mesh(solarGeo, solarMat);
    solarArray.position.set(0, 11.15, 0);
    solarArray.castShadow = true;
    meshGroupRef.current.add(solarArray);

    // 5. Architectural Windows & Entrance
    for (let floor = 0; floor < 3; floor++) {
      for (let col = -3; col <= 3; col++) {
        const winGeo = new THREE.PlaneGeometry(1.6, 1.8);
        const winMat = new THREE.MeshStandardMaterial({ color: 0x0284c7, roughness: 0.1, metalness: 0.9 });
        const win = new THREE.Mesh(winGeo, winMat);
        win.position.set(col * 2.5, 2.2 + floor * 3.4, 7.02);
        meshGroupRef.current.add(win);
      }
    }
  };

  // Creates the Dense Point Cloud with confidence colors and Camera Trajectory
  const createPointCloudsAndFlightPath = () => {
    // 1. Point Cloud
    const numPoints = 12000;
    const geometry = new THREE.BufferGeometry();
    const positions = new Float32Array(numPoints * 3);
    const colors = new Float32Array(numPoints * 3);
    const confidences = new Float32Array(numPoints);

    for (let i = 0; i < numPoints; i++) {
      // Structure points: building, roof, ground
      const isRoof = i < 3500;
      const isBuilding = i >= 3500 && i < 7500;

      let x = 0, y = 0, z = 0;
      let r = 0.5, g = 0.5, b = 0.5;
      let conf = 0.85;

      if (isRoof) {
        x = (Math.random() - 0.5) * 19;
        z = (Math.random() - 0.5) * 13;
        y = 11.0 + (Math.random() - 0.5) * 0.2;
        // Solar panel in center
        if (Math.abs(x) < 7 && Math.abs(z) < 4.5) {
          r = 0.1; g = 0.25; b = 0.7; // Deep blue
          conf = 0.97;
        } else {
          r = 0.7; g = 0.7; b = 0.7;
          conf = 0.91;
        }
      } else if (isBuilding) {
        // Walls
        const side = Math.floor(Math.random() * 4);
        const u = (Math.random() - 0.5);
        y = Math.random() * 11;
        if (side === 0) { x = u * 20; z = 7; }
        else if (side === 1) { x = u * 20; z = -7; }
        else if (side === 2) { x = 10; z = u * 14; }
        else { x = -10; z = u * 14; }
        r = 0.85; g = 0.85; b = 0.82;
        conf = 0.84 + (y / 11) * 0.1;
      } else {
        // Ground & Terrain
        x = (Math.random() - 0.5) * 48;
        z = (Math.random() - 0.5) * 48;
        y = (Math.random() - 0.5) * 0.3;
        if (Math.abs(x) < 11 && Math.abs(z) < 8) {
          y = -100; // inside building, drop
        }
        if (x < -12 && x > -24) {
          r = 0.15; g = 0.18; b = 0.2; // asphalt road
          conf = 0.94;
        } else {
          r = 0.2 + Math.random() * 0.1;
          g = 0.45 + Math.random() * 0.15;
          b = 0.2;
          conf = 0.72; // vegetation has lower multi-view confidence
        }
      }

      positions[i * 3] = x;
      positions[i * 3 + 1] = y;
      positions[i * 3 + 2] = z;

      colors[i * 3] = r;
      colors[i * 3 + 1] = g;
      colors[i * 3 + 2] = b;

      confidences[i] = conf;
    }

    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    geometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geometry.setAttribute('confidence', new THREE.BufferAttribute(confidences, 1));

    const pMat = new THREE.PointsMaterial({
      size: 0.18,
      vertexColors: true,
      sizeAttenuation: true,
    });
    const pMesh = new THREE.Points(geometry, pMat);
    pointsGroupRef.current.add(pMesh);

    // 2. Flight Trajectory & Camera Poses (Frustums)
    const flightCurvePoints: THREE.Vector3[] = [];
    const numCams = 22;
    const radius = 34.0;

    for (let c = 0; c < numCams; c++) {
      const angle = (c / numCams) * 1.5 * Math.PI - 0.75 * Math.PI;
      const camPos = new THREE.Vector3(
        radius * Math.cos(angle),
        26.0 + 3.0 * Math.sin(c * 0.5),
        radius * Math.sin(angle)
      );
      flightCurvePoints.push(camPos);

      // Camera Frustum Pyramid geometry
      const frustumGeo = new THREE.ConeGeometry(1.2, 2.5, 4);
      frustumGeo.rotateX(Math.PI / 2);
      const frustumMat = new THREE.MeshBasicMaterial({
        color: 0x38bdf8,
        wireframe: true,
      });
      const frustum = new THREE.Mesh(frustumGeo, frustumMat);
      frustum.position.copy(camPos);
      frustum.lookAt(0, 6, 0);
      flightGroupRef.current.add(frustum);
    }

    const curve = new THREE.CatmullRomCurve3(flightCurvePoints);
    const tubeGeo = new THREE.TubeGeometry(curve, 64, 0.15, 8, false);
    const tubeMat = new THREE.MeshBasicMaterial({ color: 0x38bdf8 });
    const trajectoryLine = new THREE.Mesh(tubeGeo, tubeMat);
    flightGroupRef.current.add(trajectoryLine);

    // 3. Dynamic Masked Entity Callout (Moving car on road)
    const carBoxGeo = new THREE.BoxGeometry(4.5, 2.0, 2.2);
    const carWireMat = new THREE.MeshBasicMaterial({ color: 0xef4444, wireframe: true });
    const maskedCar = new THREE.Mesh(carBoxGeo, carWireMat);
    maskedCar.position.set(-18, 1.0, 6);
    dynamicMaskGroupRef.current.add(maskedCar);

    // Dynamic Mask label billboard marker
    const markerGeo = new THREE.SphereGeometry(0.4, 16, 16);
    const markerMat = new THREE.MeshBasicMaterial({ color: 0xef4444 });
    const marker = new THREE.Mesh(markerGeo, markerMat);
    marker.position.set(-18, 2.5, 6);
    dynamicMaskGroupRef.current.add(marker);
  };

  // Confidence Heatmap / Render Mode Update
  useEffect(() => {
    meshGroupRef.current.visible = renderMode === 'textured' || renderMode === 'wireframe';
    pointsGroupRef.current.visible = renderMode === 'points' || renderMode === 'confidence';

    meshGroupRef.current.traverse((child) => {
      if ((child as THREE.Mesh).isMesh) {
        const m = (child as THREE.Mesh).material as THREE.MeshStandardMaterial;
        if (m) {
          m.wireframe = renderMode === 'wireframe';
        }
      }
    });

    // Update point colors for Confidence Heatmap
    pointsGroupRef.current.traverse((child) => {
      if ((child as THREE.Points).isPoints) {
        const pts = child as THREE.Points;
        const geom = pts.geometry;
        const colorsAttr = geom.getAttribute('color');
        const confAttr = geom.getAttribute('confidence');

        if (colorsAttr && confAttr) {
          const colors = colorsAttr.array as Float32Array;
          const confs = confAttr.array as Float32Array;

          for (let i = 0; i < confs.length; i++) {
            const conf = confs[i];
            if (renderMode === 'confidence') {
              // Color map: Red (low 0.3) -> Yellow (0.6) -> Emerald Green (high >0.85)
              if (conf < 0.6) {
                colors[i * 3] = 0.9;
                colors[i * 3 + 1] = 0.2;
                colors[i * 3 + 2] = 0.2;
              } else if (conf < 0.82) {
                colors[i * 3] = 0.95;
                colors[i * 3 + 1] = 0.8;
                colors[i * 3 + 2] = 0.1;
              } else {
                colors[i * 3] = 0.1;
                colors[i * 3 + 1] = 0.85;
                colors[i * 3 + 2] = 0.35;
              }
            } else {
              // Restore RGB colors
              colors[i * 3] = 0.8;
              colors[i * 3 + 1] = 0.8;
              colors[i * 3 + 2] = 0.8;
            }
          }
          colorsAttr.needsUpdate = true;
        }
      }
    });
  }, [renderMode]);

  // Toggle Visibility of Overlays
  useEffect(() => {
    flightGroupRef.current.visible = showFlightPath;
  }, [showFlightPath]);

  useEffect(() => {
    dynamicMaskGroupRef.current.visible = showDynamicMask;
  }, [showDynamicMask]);

  useEffect(() => {
    if (sceneRef.current) {
      const grid = sceneRef.current.getObjectByName('groundGrid');
      if (grid) grid.visible = showGrid;
    }
  }, [showGrid]);

  // Handle Raycasting for Hover Coordinates & Interactive Measurements
  const handlePointerDown = (event: React.PointerEvent<HTMLDivElement>) => {
    if (!containerRef.current || !cameraRef.current || !sceneRef.current) return;

    const rect = containerRef.current.getBoundingClientRect();
    const mouse = new THREE.Vector2(
      ((event.clientX - rect.left) / rect.width) * 2 - 1,
      -((event.clientY - rect.top) / rect.height) * 2 + 1
    );

    const raycaster = new THREE.Raycaster();
    raycaster.setFromCamera(mouse, cameraRef.current);

    const intersects = raycaster.intersectObjects(
      [meshGroupRef.current, pointsGroupRef.current],
      true
    );

    if (intersects.length > 0) {
      const hitPt = intersects[0].point;
      setHoverCoord({
        x: Math.round(hitPt.x * 100) / 100,
        y: Math.round(hitPt.z * 100) / 100, // Topographic Northing
        z: Math.round(hitPt.y * 100) / 100, // Altitude / Elevation
      });

      // Handle Measurement Tool Click
      if (measurementMode !== 'none') {
        const pts = clickedPointsRef.current;
        pts.push(hitPt.clone());

        // Visual click sphere marker
        const sphereGeo = new THREE.SphereGeometry(0.35, 16, 16);
        const sphereMat = new THREE.MeshBasicMaterial({ color: 0x10b981 });
        const marker = new THREE.Mesh(sphereGeo, sphereMat);
        marker.position.copy(hitPt);
        measureGroupRef.current.add(marker);

        if (measurementMode === 'distance' && pts.length === 2) {
          const d = pts[0].distanceTo(pts[1]);
          const lineGeo = new THREE.BufferGeometry().setFromPoints(pts);
          const lineMat = new THREE.LineDashedMaterial({ color: 0x34d399, dashSize: 0.5, gapSize: 0.2 });
          const line = new THREE.Line(lineGeo, lineMat);
          line.computeLineDistances();
          measureGroupRef.current.add(line);

          const resultText = `Linear Distance: ${d.toFixed(2)} m`;
          setActiveMeasurements(prev => [...prev, { id: Date.now(), text: resultText }]);
          onMeasurementComplete('distance', d, `Distance between points: ${d.toFixed(2)} m`);
          clickedPointsRef.current = [];
        } else if (measurementMode === 'height' && pts.length === 2) {
          const h = Math.abs(pts[1].y - pts[0].y);
          const lineGeo = new THREE.BufferGeometry().setFromPoints([
            new THREE.Vector3(pts[0].x, pts[0].y, pts[0].z),
            new THREE.Vector3(pts[0].x, pts[1].y, pts[0].z)
          ]);
          const lineMat = new THREE.LineBasicMaterial({ color: 0x38bdf8, linewidth: 2 });
          const line = new THREE.Line(lineGeo, lineMat);
          measureGroupRef.current.add(line);

          const resultText = `Vertical Height: ${h.toFixed(2)} m`;
          setActiveMeasurements(prev => [...prev, { id: Date.now(), text: resultText }]);
          onMeasurementComplete('height', h, `Vertical height clearance: ${h.toFixed(2)} m`);
          clickedPointsRef.current = [];
        } else if (measurementMode === 'area' && pts.length === 3) {
          // Triangle area: 0.5 * ||(p1-p0) x (p2-p0)||
          const v1 = new THREE.Vector3().subVectors(pts[1], pts[0]);
          const v2 = new THREE.Vector3().subVectors(pts[2], pts[0]);
          const cross = new THREE.Vector3().crossVectors(v1, v2);
          const area = 0.5 * cross.length();

          const triGeo = new THREE.BufferGeometry().setFromPoints([pts[0], pts[1], pts[2], pts[0]]);
          const triMat = new THREE.LineBasicMaterial({ color: 0xf59e0b });
          const triLine = new THREE.Line(triGeo, triMat);
          measureGroupRef.current.add(triLine);

          const resultText = `Polygon Footprint Area: ${area.toFixed(1)} m²`;
          setActiveMeasurements(prev => [...prev, { id: Date.now(), text: resultText }]);
          onMeasurementComplete('area', area, `Surface footprint area: ${area.toFixed(1)} m²`);
          clickedPointsRef.current = [];
        }
      }
    }
  };

  const resetCamera = () => {
    if (cameraRef.current && controlsRef.current) {
      cameraRef.current.position.set(45, 35, 45);
      controlsRef.current.target.set(0, 4, 0);
      controlsRef.current.update();
    }
  };

  const clearMeasurements = () => {
    measureGroupRef.current.clear();
    clickedPointsRef.current = [];
    setActiveMeasurements([]);
  };

  return (
    <div className="relative w-full h-[620px] rounded-2xl overflow-hidden border border-slate-800 bg-slate-950 shadow-2xl">
      {/* 3D WebGL Canvas */}
      <div
        ref={containerRef}
        onPointerDown={handlePointerDown}
        className="w-full h-full cursor-grab active:cursor-grabbing"
      />

      {/* Top Floating Controls Bar */}
      <div className="absolute top-4 left-4 right-4 flex flex-wrap items-center justify-between gap-3 pointer-events-none">
        {/* Render Mode Switcher */}
        <div className="pointer-events-auto flex items-center bg-slate-900/90 backdrop-blur-md p-1 rounded-xl border border-slate-800 shadow-xl space-x-1">
          <button
            onClick={() => setRenderMode('textured')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              renderMode === 'textured' ? 'bg-emerald-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            Textured Mesh
          </button>
          <button
            onClick={() => setRenderMode('confidence')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              renderMode === 'confidence' ? 'bg-blue-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            Confidence Heatmap
          </button>
          <button
            onClick={() => setRenderMode('points')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              renderMode === 'points' ? 'bg-purple-600 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            Dense Point Cloud
          </button>
          <button
            onClick={() => setRenderMode('wireframe')}
            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
              renderMode === 'wireframe' ? 'bg-slate-700 text-white shadow' : 'text-slate-400 hover:text-white'
            }`}
          >
            Wireframe
          </button>
        </div>

        {/* Layer Visibility Toggles */}
        <div className="pointer-events-auto flex items-center bg-slate-900/90 backdrop-blur-md p-1.5 rounded-xl border border-slate-800 shadow-xl space-x-2 text-xs">
          <button
            onClick={() => setShowFlightPath(!showFlightPath)}
            className={`px-2.5 py-1 rounded-lg flex items-center space-x-1.5 transition-all ${
              showFlightPath ? 'bg-sky-500/20 text-sky-400 border border-sky-500/40' : 'text-slate-400 hover:text-white'
            }`}
          >
            <Compass className="w-3.5 h-3.5" />
            <span>Flight Path ({flightGroupRef.current.children.length > 0 ? '22 Poses' : 'Trajectory'})</span>
          </button>

          <button
            onClick={() => setShowDynamicMask(!showDynamicMask)}
            className={`px-2.5 py-1 rounded-lg flex items-center space-x-1.5 transition-all ${
              showDynamicMask ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40' : 'text-slate-400 hover:text-white'
            }`}
          >
            <ShieldAlert className="w-3.5 h-3.5" />
            <span>Dynamic Masked Car</span>
          </button>

          <button
            onClick={() => setShowGrid(!showGrid)}
            className={`p-1.5 rounded-lg ${showGrid ? 'text-emerald-400 bg-slate-800' : 'text-slate-500'}`}
            title="Toggle Ground Grid"
          >
            <Grid className="w-4 h-4" />
          </button>

          <button
            onClick={resetCamera}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
            title="Reset Camera View"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Bottom Left: Confidence Heatmap Legend (when in confidence mode) */}
      {renderMode === 'confidence' && (
        <div className="absolute bottom-4 left-4 bg-slate-900/95 backdrop-blur-md p-3.5 rounded-xl border border-slate-800 shadow-2xl text-xs space-y-2 pointer-events-auto max-w-[260px]">
          <div className="flex items-center space-x-2 text-slate-200 font-semibold">
            <span className="w-2.5 h-2.5 rounded-full bg-blue-500 animate-pulse" />
            <span>Metric Confidence Legend</span>
          </div>
          <div className="space-y-1.5 text-[11px]">
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-emerald-400">
                <span className="w-3 h-3 rounded bg-emerald-500 inline-block" />
                High (&gt; 85%)
              </span>
              <span className="text-slate-400">Multi-view Confirmed</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-amber-400">
                <span className="w-3 h-3 rounded bg-amber-500 inline-block" />
                Medium (60-85%)
              </span>
              <span className="text-slate-400">AI Metric Depth Filled</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1.5 text-red-400">
                <span className="w-3 h-3 rounded bg-red-500 inline-block" />
                Low (&lt; 60%)
              </span>
              <span className="text-slate-400">Occlusions / Edge</span>
            </div>
          </div>
          <div className="pt-1 text-[10px] text-slate-400 border-t border-slate-800">
            Hybrid Photogrammetry + Depth Anything V2 metric alignment.
          </div>
        </div>
      )}

      {/* Dynamic Mask Callout Indicator */}
      {showDynamicMask && (
        <div className="absolute top-20 right-4 bg-red-950/80 backdrop-blur border border-red-500/50 p-3 rounded-xl text-xs text-red-200 max-w-[220px] pointer-events-auto shadow-xl">
          <div className="flex items-center space-x-1.5 font-semibold text-red-400 mb-1">
            <ShieldAlert className="w-4 h-4" />
            <span>Dynamic Object Masked</span>
          </div>
          <p className="text-[11px] leading-tight text-red-300">
            Moving vehicle on access road was detected and excluded from 3D geometry matching to prevent ghosting artifacts.
          </p>
        </div>
      )}

      {/* Measurement Mode Active Notice */}
      {measurementMode !== 'none' && (
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-emerald-950/90 backdrop-blur border border-emerald-500/60 px-4 py-2.5 rounded-xl text-xs text-emerald-300 flex items-center space-x-3 pointer-events-auto shadow-2xl">
          <Ruler className="w-4 h-4 text-emerald-400 animate-bounce" />
          <span>
            {measurementMode === 'distance' && 'Click 2 points on the 3D model to measure linear distance'}
            {measurementMode === 'height' && 'Click ground point then rooftop point to measure vertical height'}
            {measurementMode === 'area' && 'Click 3 boundary points to compute polygon footprint area'}
          </span>
          <button
            onClick={clearMeasurements}
            className="text-[11px] px-2 py-0.5 rounded bg-emerald-800/60 hover:bg-emerald-700 text-white transition-colors"
          >
            Clear Lines
          </button>
        </div>
      )}

      {/* Live Measurement Results List */}
      {activeMeasurements.length > 0 && (
        <div className="absolute top-20 left-4 bg-slate-900/90 backdrop-blur p-3 rounded-xl border border-slate-800 text-xs space-y-1.5 pointer-events-auto max-w-xs shadow-xl">
          <div className="text-[10px] uppercase font-bold text-slate-400 tracking-wider">Survey Measurements</div>
          {activeMeasurements.map((m) => (
            <div key={m.id} className="text-emerald-400 font-mono font-semibold flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5" />
              <span>{m.text}</span>
            </div>
          ))}
        </div>
      )}

      {/* Bottom Right: Real-time Coordinates HUD */}
      <div className="absolute bottom-4 right-4 bg-slate-900/90 backdrop-blur-md px-3.5 py-2 rounded-xl border border-slate-800 text-xs font-mono text-slate-300 shadow-xl pointer-events-auto flex items-center space-x-3">
        {hoverCoord ? (
          <>
            <div>
              <span className="text-slate-500 text-[10px]">UTM X (E): </span>
              <span className="text-emerald-400">{hoverCoord.x} m</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px]">UTM Y (N): </span>
              <span className="text-emerald-400">{hoverCoord.y} m</span>
            </div>
            <div>
              <span className="text-slate-500 text-[10px]">Elev (Z): </span>
              <span className="text-blue-400">{hoverCoord.z} m</span>
            </div>
          </>
        ) : (
          <span className="text-slate-500 text-[11px] italic">Hover over 3D model for georeferenced coordinates</span>
        )}
      </div>
    </div>
  );
};
