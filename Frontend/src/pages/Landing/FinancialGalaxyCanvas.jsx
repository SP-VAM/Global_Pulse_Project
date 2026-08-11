import { useEffect, useRef } from 'react';
import * as THREE from 'three';

export default function FinancialGalaxyCanvas() {
  const containerRef = useRef(null);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // --- Scene & Dark Blue Environment Setup ---
    const scene = new THREE.Scene();
    scene.fog = new THREE.FogExp2(0x080c1e, 0.0016);

    const camera = new THREE.PerspectiveCamera(
      45,
      window.innerWidth / window.innerHeight,
      0.1,
      1000
    );
    camera.position.set(0, 0, 24);

    const renderer = new THREE.WebGLRenderer({
      alpha: true,
      antialias: true,
      powerPreference: 'high-performance',
    });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.setClearColor(0x080c1e, 1);
    container.appendChild(renderer.domElement);

    // --- Mouse & Scroll Tracking (Camera Parallax Only, No Cursor Trail) ---
    const mouse = { x: 0, y: 0, targetX: 0, targetY: 0 };
    let scrollY = 0;

    const onMouseMove = (e) => {
      mouse.targetX = (e.clientX / window.innerWidth - 0.5) * 2;
      mouse.targetY = -(e.clientY / window.innerHeight - 0.5) * 2;
    };

    const onScroll = () => {
      scrollY = window.scrollY;
    };

    window.addEventListener('mousemove', onMouseMove, { passive: true });
    window.addEventListener('scroll', onScroll, { passive: true });

    // --- 1. CONTINUOUSLY MOVING BACKGROUND STARS ---
    const bgStarsCount = 1800;
    const bgGeo = new THREE.BufferGeometry();
    const bgPositions = new Float32Array(bgStarsCount * 3);
    const bgVelocities = new Float32Array(bgStarsCount * 3);
    const bgColors = new Float32Array(bgStarsCount * 3);

    const colorBlue = new THREE.Color(0x2f6bff);
    const colorCyan = new THREE.Color(0x4f83ff);
    const colorWhite = new THREE.Color(0xffffff);

    for (let i = 0; i < bgStarsCount; i++) {
      bgPositions[i * 3] = (Math.random() - 0.5) * 160;
      bgPositions[i * 3 + 1] = (Math.random() - 0.5) * 160;
      bgPositions[i * 3 + 2] = (Math.random() - 0.5) * 160 - 20;

      // Slow drift velocity
      bgVelocities[i * 3] = (Math.random() - 0.5) * 0.02;
      bgVelocities[i * 3 + 1] = 0.01 + Math.random() * 0.025; // Gentle upward drift
      bgVelocities[i * 3 + 2] = (Math.random() - 0.5) * 0.01;

      const randColor = Math.random();
      const chosenColor = randColor > 0.65 ? colorBlue : randColor > 0.35 ? colorCyan : colorWhite;
      bgColors[i * 3] = chosenColor.r;
      bgColors[i * 3 + 1] = chosenColor.g;
      bgColors[i * 3 + 2] = chosenColor.b;
    }

    bgGeo.setAttribute('position', new THREE.BufferAttribute(bgPositions, 3));
    bgGeo.setAttribute('color', new THREE.BufferAttribute(bgColors, 3));

    const bgMat = new THREE.PointsMaterial({
      size: 0.24,
      vertexColors: true,
      transparent: true,
      opacity: 0.7,
      sizeAttenuation: true,
    });
    const bgPoints = new THREE.Points(bgGeo, bgMat);
    scene.add(bgPoints);

    // --- 2. FLOATING BACKGROUND FINANCIAL DATA STREAMS ---
    const dataStreamCount = 240;
    const streamGeo = new THREE.BufferGeometry();
    const streamPositions = new Float32Array(dataStreamCount * 3);
    const streamVelocities = new Float32Array(dataStreamCount);

    for (let i = 0; i < dataStreamCount; i++) {
      streamPositions[i * 3] = (Math.random() - 0.5) * 120;
      streamPositions[i * 3 + 1] = (Math.random() - 0.5) * 120;
      streamPositions[i * 3 + 2] = (Math.random() - 0.5) * 80 - 10;
      streamVelocities[i] = 0.03 + Math.random() * 0.04;
    }

    streamGeo.setAttribute('position', new THREE.BufferAttribute(streamPositions, 3));

    const streamMat = new THREE.PointsMaterial({
      size: 0.32,
      color: 0x00f0ff,
      transparent: true,
      opacity: 0.45,
    });
    const streamPoints = new THREE.Points(streamGeo, streamMat);
    scene.add(streamPoints);

    // --- 3. CENTERED 3D DIGITAL EARTH GLOBE ---
    const globeGroup = new THREE.Group();
    globeGroup.position.set(0, 0.2, 0);

    const globeRadius = 5.6;
    const sphereGeo = new THREE.SphereGeometry(globeRadius, 48, 48);

    const wireMat = new THREE.MeshBasicMaterial({
      color: 0x2f6bff,
      wireframe: true,
      transparent: true,
      opacity: 0.1,
    });
    const globeWire = new THREE.Mesh(sphereGeo, wireMat);
    globeGroup.add(globeWire);

    const dotCount = 2000;
    const dotGeo = new THREE.BufferGeometry();
    const dotPos = new Float32Array(dotCount * 3);

    for (let i = 0; i < dotCount; i++) {
      const phi = Math.acos(-1 + (2 * i) / dotCount);
      const theta = Math.sqrt(dotCount * Math.PI) * phi;

      const x = globeRadius * Math.cos(theta) * Math.sin(phi);
      const y = globeRadius * Math.sin(theta) * Math.sin(phi);
      const z = globeRadius * Math.cos(phi);

      dotPos[i * 3] = x;
      dotPos[i * 3 + 1] = y;
      dotPos[i * 3 + 2] = z;
    }
    dotGeo.setAttribute('position', new THREE.BufferAttribute(dotPos, 3));

    const dotMat = new THREE.PointsMaterial({
      size: 0.11,
      color: 0x4f83ff,
      transparent: true,
      opacity: 0.8,
    });
    const globeDots = new THREE.Points(dotGeo, dotMat);
    globeGroup.add(globeDots);

    const coreGeo = new THREE.SphereGeometry(globeRadius * 0.95, 32, 32);
    const coreMat = new THREE.MeshBasicMaterial({
      color: 0x080c1e,
      transparent: true,
      opacity: 0.9,
    });
    const globeCore = new THREE.Mesh(coreGeo, coreMat);
    globeGroup.add(globeCore);

    const latLongToVector3 = (lat, lon, radius) => {
      const phi = (90 - lat) * (Math.PI / 180);
      const theta = (lon + 180) * (Math.PI / 180);
      const x = -(radius * Math.sin(phi) * Math.cos(theta));
      const z = radius * Math.sin(phi) * Math.sin(theta);
      const y = radius * Math.cos(phi);
      return new THREE.Vector3(x, y, z);
    };

    const nodes = {
      India: latLongToVector3(20.5937, 78.9629, globeRadius + 0.05),
      Europe: latLongToVector3(51.5074, -0.1278, globeRadius + 0.05),
      China: latLongToVector3(31.2304, 121.4737, globeRadius + 0.05),
      USA: latLongToVector3(40.7128, -74.006, globeRadius + 0.05),
    };

    Object.entries(nodes).forEach(([name, pos]) => {
      const isIndia = name === 'India';
      const nodeGeo = new THREE.SphereGeometry(isIndia ? 0.24 : 0.15, 16, 16);
      const nodeMat = new THREE.MeshBasicMaterial({
        color: isIndia ? 0x00f0ff : 0x4f83ff,
      });
      const nodeMesh = new THREE.Mesh(nodeGeo, nodeMat);
      nodeMesh.position.copy(pos);
      globeGroup.add(nodeMesh);

      if (isIndia) {
        const ringGeo = new THREE.RingGeometry(0.3, 0.45, 32);
        const ringMat = new THREE.MeshBasicMaterial({
          color: 0x00f0ff,
          side: THREE.DoubleSide,
          transparent: true,
          opacity: 0.85,
        });
        const beaconRing = new THREE.Mesh(ringGeo, ringMat);
        beaconRing.position.copy(pos);
        beaconRing.lookAt(globeGroup.position);
        globeGroup.add(beaconRing);
      }
    });

    const arcConnections = [
      { from: nodes.Europe, to: nodes.India },
      { from: nodes.China, to: nodes.India },
      { from: nodes.USA, to: nodes.India },
    ];

    const dataPackets = [];

    arcConnections.forEach(({ from, to }) => {
      const distance = from.distanceTo(to);
      const mid = from.clone().add(to).multiplyScalar(0.5);
      mid.normalize().multiplyScalar(globeRadius + distance * 0.38);

      const curve = new THREE.QuadraticBezierCurve3(from, mid, to);
      const curvePoints = curve.getPoints(50);
      const arcGeo = new THREE.BufferGeometry().setFromPoints(curvePoints);
      const arcMat = new THREE.LineBasicMaterial({
        color: 0x2f6bff,
        transparent: true,
        opacity: 0.5,
      });
      const arcLine = new THREE.Line(arcGeo, arcMat);
      globeGroup.add(arcLine);

      const packetGeo = new THREE.SphereGeometry(0.12, 12, 12);
      const packetMat = new THREE.MeshBasicMaterial({ color: 0x00f0ff });
      const packetMesh = new THREE.Mesh(packetGeo, packetMat);
      globeGroup.add(packetMesh);

      dataPackets.push({
        mesh: packetMesh,
        curve: curve,
        progress: Math.random(),
        speed: 0.005 + Math.random() * 0.005,
      });
    });

    scene.add(globeGroup);

    // --- Render Loop: Continuous Moving Background Stars & Data Streams ---
    let clock = new THREE.Clock();
    let animId;

    const animate = () => {
      animId = requestAnimationFrame(animate);
      const elapsedTime = clock.getElapsedTime();

      mouse.x += (mouse.targetX - mouse.x) * 0.05;
      mouse.y += (mouse.targetY - mouse.y) * 0.05;

      // 1. Move Background Stars continuously
      const bgPosArray = bgGeo.attributes.position.array;
      for (let i = 0; i < bgStarsCount; i++) {
        bgPosArray[i * 3] += bgVelocities[i * 3];
        bgPosArray[i * 3 + 1] += bgVelocities[i * 3 + 1];
        bgPosArray[i * 3 + 2] += bgVelocities[i * 3 + 2];

        // Wrap around when bounds exceeded
        if (bgPosArray[i * 3 + 1] > 80) bgPosArray[i * 3 + 1] = -80;
        if (bgPosArray[i * 3] > 80) bgPosArray[i * 3] = -80;
        if (bgPosArray[i * 3] < -80) bgPosArray[i * 3] = 80;
      }
      bgGeo.attributes.position.needsUpdate = true;

      // 2. Move Background Financial Data Streams
      const streamPosArray = streamGeo.attributes.position.array;
      for (let i = 0; i < dataStreamCount; i++) {
        streamPosArray[i * 3 + 1] += streamVelocities[i];
        if (streamPosArray[i * 3 + 1] > 60) streamPosArray[i * 3 + 1] = -60;
      }
      streamGeo.attributes.position.needsUpdate = true;

      // 3. Smooth Globe Rotation
      globeGroup.rotation.y = elapsedTime * 0.08 + mouse.x * 0.15;
      globeGroup.rotation.x = mouse.y * 0.1;
      bgPoints.rotation.y = elapsedTime * 0.005;

      dataPackets.forEach((packet) => {
        packet.progress += packet.speed;
        if (packet.progress > 1) packet.progress = 0;
        packet.mesh.position.copy(packet.curve.getPoint(packet.progress));
      });

      const scrollFactor = Math.min(scrollY / 1000, 1);
      globeGroup.position.y = 0.2 - scrollFactor * 4;
      globeGroup.position.z = -scrollFactor * 5;

      renderer.render(scene, camera);
    };

    animate();

    const onResize = () => {
      camera.aspect = window.innerWidth / window.innerHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(window.innerWidth, window.innerHeight);
    };

    window.addEventListener('resize', onResize);

    return () => {
      cancelAnimationFrame(animId);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('scroll', onScroll);
      window.removeEventListener('resize', onResize);
      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }
      renderer.dispose();
    };
  }, []);

  return <div ref={containerRef} className="gp-galaxy-canvas-container" aria-hidden="true" />;
}
