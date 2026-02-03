'use client';

import { Canvas, useThree } from '@react-three/fiber';
import { Html, OrbitControls } from '@react-three/drei';
import { Suspense, useEffect, useRef, useState } from 'react';
import { STLLoader } from 'three/examples/jsm/loaders/STLLoader.js';
import * as THREE from 'three';
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib';
import { Download, ChevronDown, FileBox, Box } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';

type Bounds = {
  center: THREE.Vector3;
  radius: number;
};

// Placeholder model shown when no user-generated model is loaded
const DEFAULT_STL_PATH = '/assets/render_3ea3f181-3b0d-48c8-804b-590aab5d0945.stl';

const STLModel = ({
  url,
  version,
  onGeometryLoaded,
}: {
  url: string | undefined;
  version?: number;
  onGeometryLoaded?: (bounds: Bounds) => void;
}) => {
  const { scene } = useThree();
  const meshRef = useRef<THREE.Mesh>(null);

  useEffect(() => {
    if (!url || url.trim() === '') {
      if (meshRef.current) {
        scene.remove(meshRef.current);
        if (meshRef.current.geometry) meshRef.current.geometry.dispose();
        if (Array.isArray(meshRef.current.material)) {
          meshRef.current.material.forEach((m) => m.dispose());
        } else if (meshRef.current.material) {
          meshRef.current.material.dispose();
        }
        meshRef.current = null;
      }
      return;
    }

    let isMounted = true;
    const loader = new STLLoader();

    const isValidUrl = url.startsWith('http') || url.startsWith('blob:') || url.startsWith('/');
    if (!isValidUrl) {
      console.warn(`STLModel: Invalid URL pattern skipped: [${url}]`);
      return;
    }

    try {
      loader.setCrossOrigin('anonymous');
      console.log(`STLModel: Requesting resource from [${url}]`);
      loader.load(
        url,
        (loadedGeometry) => {
          if (!isMounted) {
            loadedGeometry.dispose();
            return;
          }

          loadedGeometry.computeVertexNormals();
          loadedGeometry.center();

          // Notify parent of bounds
          loadedGeometry.computeBoundingSphere();
          const sphere = loadedGeometry.boundingSphere;
          if (sphere) {
            onGeometryLoaded?.({
              center: sphere.center.clone(),
              radius: Math.max(sphere.radius, 1),
            });
          }

          if (meshRef.current) {
            meshRef.current.geometry.dispose();
            meshRef.current.geometry = loadedGeometry;
          } else {
            const material = new THREE.MeshStandardMaterial({
              color: 0x909090,
              metalness: 0.1,
              roughness: 0.5,
            });
            const mesh = new THREE.Mesh(loadedGeometry, material);
            mesh.castShadow = true;
            mesh.receiveShadow = true;
            mesh.rotation.x = -Math.PI / 2;
            meshRef.current = mesh;
            scene.add(mesh);
          }
        },
        undefined,
        (error) => {
          if (isMounted) {
            console.warn('STLModel: Load interrupted or failed:', error);
          }
        },
      );
    } catch (err) {
      if (isMounted) console.error('STLModel: Critical load error:', err);
    }

    return () => {
      isMounted = false;
      if (meshRef.current) {
        scene.remove(meshRef.current);
        if (meshRef.current.geometry) meshRef.current.geometry.dispose();
        if (Array.isArray(meshRef.current.material)) {
          meshRef.current.material.forEach((m) => m.dispose());
        } else if (meshRef.current.material) {
          meshRef.current.material.dispose();
        }
        meshRef.current = null;
      }
    };
  }, [url, version, scene, onGeometryLoaded]);

  return null;
};

export type ViewPreset = 'top' | 'front' | 'right' | 'iso';

interface ModelViewerProps {
  stlPath?: string | undefined;
  stlVersion?: number;
  fileName?: string;
  viewPreset?: ViewPreset;
  onExport?: (format: 'stl' | 'step') => void;
  isMeasureMode?: boolean;
  onMeasureModeChange?: (mode: boolean) => void;
}

function AutoFrameControls({
  bounds,
  viewPreset = 'iso',
}: {
  bounds: Bounds | null;
  viewPreset?: string;
}) {
  const controlsRef = useRef<OrbitControlsImpl | null>(null);
  const { camera, set } = useThree();
  const lastFrameKeyRef = useRef<string | null>(null);

  useEffect(() => {
    if (!bounds) return;
    const { center, radius } = bounds;
    const offset = Math.max(radius * 2.5, 20);

    // Calculate new position based on preset
    const newPosition = center.clone();
    switch (viewPreset) {
      case 'top':
        newPosition.add(new THREE.Vector3(0, offset, 0));
        break;
      case 'front':
        newPosition.add(new THREE.Vector3(0, 0, offset));
        break;
      case 'right':
        newPosition.add(new THREE.Vector3(offset, 0, 0));
        break;
      case 'iso':
      default:
        newPosition.add(new THREE.Vector3(offset, offset * 0.8, offset));
        break;
    }

    const nextCamera = camera.clone();
    nextCamera.position.copy(newPosition);
    nextCamera.near = Math.max(radius / 100, 0.1);
    nextCamera.far = Math.max(radius * 50, 50000);
    nextCamera.updateProjectionMatrix();

    const frameKey = `${center.toArray().join(',')}:${radius}:${viewPreset}`;
    if (lastFrameKeyRef.current === frameKey) {
      return;
    }
    lastFrameKeyRef.current = frameKey;
    set({ camera: nextCamera });

    // Ensure orbit controls target the center
    if (controlsRef.current) {
      controlsRef.current.object = nextCamera;
      controlsRef.current.target.copy(center);
      controlsRef.current.update();
    }
  }, [bounds, camera, set, viewPreset]); // Re-run when viewPreset changes

  return <OrbitControls ref={controlsRef} enableDamping dampingFactor={0.05} />;
}

export function MeasureTool({
  isEnabled,
  onPointCountChange,
}: {
  isEnabled: boolean;
  onPointCountChange?: (count: number) => void;
}) {
  const { camera, scene, gl } = useThree();
  const [points, setPoints] = useState<THREE.Vector3[]>([]);
  const [hoverPoint, setHoverPoint] = useState<THREE.Vector3 | null>(null);

  useEffect(() => {
    onPointCountChange?.(points.length);
  }, [points.length, onPointCountChange]);

  const pointsRef = useRef<THREE.Vector3[]>([]);

  useEffect(() => {
    pointsRef.current = points;
  }, [points]);

  useEffect(() => {
    const getIntersections = (clientX: number, clientY: number) => {
      const rect = gl.domElement.getBoundingClientRect();
      const x = ((clientX - rect.left) / rect.width) * 2 - 1;
      const y = -((clientY - rect.top) / rect.height) * 2 + 1;

      const raycaster = new THREE.Raycaster();
      raycaster.setFromCamera(new THREE.Vector2(x, y), camera);
      return raycaster
        .intersectObjects(scene.children, true)
        .find((hit) => hit.object.type === 'Mesh');
    };

    const handlePointerDown = (e: PointerEvent) => {
      if (!isEnabled) return;
      const meshIntersect = getIntersections(e.clientX, e.clientY);

      if (meshIntersect) {
        setPoints((prev) => {
          if (prev.length >= 2) return [meshIntersect.point];
          return [...prev, meshIntersect.point];
        });
      }
    };

    const handlePointerMove = (e: PointerEvent) => {
      if (!isEnabled) return;

      if (pointsRef.current.length < 2) {
        const meshIntersect = getIntersections(e.clientX, e.clientY);
        setHoverPoint(meshIntersect ? meshIntersect.point : null);
      } else {
        setHoverPoint(null);
      }
    };

    if (isEnabled) {
      gl.domElement.addEventListener('pointerdown', handlePointerDown);
      gl.domElement.addEventListener('pointermove', handlePointerMove);
    }

    return () => {
      gl.domElement.removeEventListener('pointerdown', handlePointerDown);
      gl.domElement.removeEventListener('pointermove', handlePointerMove);
      gl.domElement.style.cursor = 'default';
    };
  }, [isEnabled, camera, scene, gl]);

  // Separate effect for clearing points to avoid cascading render lint error
  useEffect(() => {
    if (!isEnabled && (points.length > 0 || hoverPoint !== null)) {
      // Use timeout to delay state update until next tick, satisfying strict lint rules
      const timer = setTimeout(() => {
        setPoints([]);
        setHoverPoint(null);
      }, 0);
      return () => clearTimeout(timer);
    }
  }, [isEnabled, points.length, hoverPoint]);

  // Render logic
  const distance = points.length === 2 ? points[0].distanceTo(points[1]) : 0;
  const midPoint =
    points.length === 2 ? points[0].clone().add(points[1]).multiplyScalar(0.5) : null;

  return (
    <group>
      {/* Hover Ghost Marker */}
      {hoverPoint && points.length < 2 && (
        <mesh position={hoverPoint}>
          <sphereGeometry args={[0.2, 16, 16]} />
          <meshBasicMaterial color="#059669" transparent opacity={0.6} depthTest={false} />
          <mesh scale={[1.2, 1.2, 1.2]}>
            <sphereGeometry args={[0.2, 16, 16]} />
            <meshBasicMaterial
              color="#059669"
              transparent
              opacity={0.3}
              wireframe
              depthTest={false}
            />
          </mesh>
        </mesh>
      )}

      {/* Existing Points */}
      {points.map((p, i) => (
        <mesh key={i} position={p}>
          <sphereGeometry args={[0.3, 16, 16]} />
          <meshBasicMaterial color="#059669" depthTest={false} transparent opacity={1.0} />
          <mesh scale={[1.5, 1.5, 1.5]}>
            <sphereGeometry args={[0.3, 16, 16]} />
            <meshBasicMaterial
              color="#059669"
              depthTest={false}
              transparent
              opacity={0.4}
              wireframe
            />
          </mesh>
        </mesh>
      ))}

      {/* Line */}
      {points.length === 2 && (
        <>
          <line>
            <bufferGeometry>
              <float32BufferAttribute
                attach="attributes-position"
                args={[new Float32Array([...points[0].toArray(), ...points[1].toArray()]), 3]}
              />
            </bufferGeometry>
            <lineBasicMaterial
              color="#059669"
              linewidth={2}
              depthTest={false}
              transparent
              opacity={0.8}
            />
          </line>

          {midPoint && (
            <Html position={midPoint} center zIndexRange={[100, 0]}>
              <div className="bg-black/90 text-emerald-400 px-3 py-1.5 rounded-full text-xs border border-emerald-500/30 whitespace-nowrap backdrop-blur-md shadow-[0_0_15px_rgba(16,185,129,0.3)] flex flex-col items-center pointer-events-none select-none">
                <span className="font-bold tracking-wider">{distance.toFixed(2)}mm</span>
                <span className="text-[9px] text-emerald-400/60 font-medium">
                  {(distance / 25.4).toFixed(3)}&quot;
                </span>
              </div>
            </Html>
          )}
        </>
      )}
    </group>
  );
}

export function ModelViewer({
  stlPath,
  stlVersion,
  fileName,
  viewPreset,
  onExport,
  isMeasureMode = false,
}: ModelViewerProps) {
  const [bounds, setBounds] = useState<Bounds | null>(null);
  const [measurePointCount, setMeasurePointCount] = useState(0);
  const displayPath = stlPath || DEFAULT_STL_PATH;
  const effectiveBounds = displayPath ? bounds : null;

  return (
    <div
      className="h-full w-full relative bg-gradient-to-br from-gray-900 to-gray-800"
      style={{ cursor: isMeasureMode ? 'crosshair' : 'default' }}
    >
      {/* Measurement Instructions Overlay */}
      {isMeasureMode && (
        <div className="absolute top-[124px] left-1/2 -translate-x-1/2 z-20 pointer-events-none">
          <div className="bg-black/70 backdrop-blur-md text-white/90 text-[10px] font-medium px-4 py-1.5 rounded-full border border-white/10 shadow-lg flex items-center gap-2 animate-in fade-in slide-in-from-top-1">
            <div
              className={cn(
                'w-1.5 h-1.5 rounded-full animate-pulse',
                measurePointCount === 2 ? 'bg-emerald-500' : 'bg-blue-400',
              )}
            />
            {measurePointCount === 0 && 'Click model to place FIRST point'}
            {measurePointCount === 1 && 'Click model to place SECOND point'}
            {measurePointCount === 2 && 'Measurement complete. Click to reset.'}
          </div>
        </div>
      )}

      {/* File name label */}
      {fileName && (
        <div className="absolute top-[70px] left-2 z-10 bg-black/50 backdrop-blur-sm px-3 py-1 rounded-md text-xs text-white">
          {fileName.replace(/\.(scad|fge|py)$/i, '')}
        </div>
      )}

      {/* Premium Export Button */}
      {stlPath && (
        <div className="absolute top-[76px] right-4 z-20">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button className="relative h-10 gap-2 rounded-full border border-white/20 bg-white/10 px-5 text-sm font-semibold text-white backdrop-blur-md transition-all hover:bg-white/20 hover:scale-105 active:scale-95 shadow-[0_0_20px_rgba(255,255,255,0.1)] hover:shadow-[0_0_30px_rgba(255,255,255,0.2)] group overflow-visible">
                {/* Pulsing ring animation - bigger flash, stops after 8 pulses */}
                <div className="absolute -inset-1 rounded-full bg-emerald-500/40 animate-ping-limited" />

                {/* Badge showing file count */}
                <div className="absolute -top-1 -right-1 bg-emerald-500 text-white text-[9px] font-bold px-1.5 py-0.5 rounded-full shadow-lg z-10">
                  2
                </div>

                <div className="absolute inset-0 rounded-full ring-1 ring-white/30 group-hover:ring-white/50 transition-all" />
                <div className="absolute -inset-1 rounded-full bg-gradient-to-r from-blue-500/20 via-purple-500/20 to-blue-500/20 opacity-0 group-hover:opacity-100 blur-md transition-all duration-700 animate-pulse" />
                <div className="absolute inset-0 rounded-full bg-white/5 opacity-0 group-hover:opacity-100 transition-opacity" />

                <Download className="h-4 w-4 relative z-10" />
                <span className="relative z-10">Export</span>
                <ChevronDown className="h-3.5 w-3.5 relative z-10 opacity-70 group-data-[state=open]:rotate-180 transition-transform" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent
              align="end"
              className="w-48 rounded-xl border-border/50 bg-black/80 backdrop-blur-xl p-1.5 text-white shadow-2xl animate-in slide-in-from-top-2"
            >
              <DropdownMenuItem
                onClick={() => onExport?.('step')}
                className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium focus:bg-white/10 focus:text-white cursor-pointer transition-colors"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-blue-500/20 text-blue-400">
                  <Box className="h-4 w-4" />
                </div>
                <div className="flex flex-col gap-0.5">
                  <span>STEP File</span>
                  <span className="text-[10px] text-muted-foreground/80 font-normal">
                    Solid body (CAD)
                  </span>
                </div>
              </DropdownMenuItem>
              <DropdownMenuItem
                onClick={() => onExport?.('stl')}
                className="flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium focus:bg-white/10 focus:text-white cursor-pointer transition-colors"
              >
                <div className="flex h-8 w-8 items-center justify-center rounded-md bg-orange-500/20 text-orange-400">
                  <FileBox className="h-4 w-4" />
                </div>
                <div className="flex flex-col gap-0.5">
                  <span>STL File</span>
                  <span className="text-[10px] text-muted-foreground/80 font-normal">
                    Mesh (Printing)
                  </span>
                </div>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      )}

      {/* 3D Canvas */}
      <Canvas camera={{ position: [50, 50, 50], fov: 50 }} shadows gl={{ antialias: true }}>
        <Suspense fallback={null}>
          {/* Lighting */}
          <ambientLight intensity={0.7} />
          <directionalLight
            position={[10, 10, 5]}
            intensity={1.5}
            castShadow
            shadow-mapSize-width={1024}
            shadow-mapSize-height={1024}
          />
          <pointLight position={[-10, -10, -10]} intensity={1} />
          <pointLight position={[10, 20, 10]} intensity={1.5} />

          {/* Grid Helper */}
          <gridHelper args={[100, 20, '#444', '#222']} />

          {/* STL Model */}
          <STLModel
            key={`${displayPath}-${stlVersion}`}
            url={displayPath}
            version={stlVersion}
            onGeometryLoaded={setBounds}
          />

          {/* Camera Controls */}
          <AutoFrameControls bounds={effectiveBounds} viewPreset={viewPreset} />

          {/* Measurement Tool */}
          <MeasureTool isEnabled={isMeasureMode} onPointCountChange={setMeasurePointCount} />
        </Suspense>
      </Canvas>
    </div>
  );
}
