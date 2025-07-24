import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
// Renderer
const renderer = new THREE.WebGLRenderer({ alpha: true });
renderer.setClearColor(0x000000, 0);
renderer.setSize(window.innerWidth, window.innerHeight);
renderer.setPixelRatio(window.devicePixelRatio);
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
document.body.style = `
  margin: 0;
  overflow-y: auto;
  background: linear-gradient(to bottom, #510813, #181114);
`;
document.body.appendChild(renderer.domElement);
// Scene & Camera
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(45, window.innerWidth / window.innerHeight, 1, 1000);
camera.position.set(0, 1.7, 1.5);
camera.lookAt(0, 1.7, 1.5);
// Controls
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableZoom = false;
controls.enableRotate = false;
controls.enablePan = false;
controls.target.set(0, 1.4, 0);
controls.update();
// Lighting
const light = new THREE.SpotLight(0xffffff, 3000, 100, 0.22, 1);
light.position.set(15, 15, 15);
light.castShadow = true;
light.shadow.bias = -0.0001;
scene.add(light);
// Ground (optional visual reference)
const ground = new THREE.Mesh(
  new THREE.PlaneGeometry(50, 50).rotateX(-Math.PI / 2),
  new THREE.ShadowMaterial({ opacity: 0.0 })
);
ground.receiveShadow = true;
scene.add(ground);
// Viseme Mapping
const phonemeToIndex = {
  A: 68,
  B: 62,
  C: 60,
  D: 66,
  E: 64,
  F: 66,
  G: 65,
  H: 67,
  X: 8

};
let audio, mouthCues = [], modelMesh = null;
// Load GLTF Model
const loader = new GLTFLoader().setPath('frontend/public/millennium_falcon/');
loader.load('character.gltf', (gltf) => {
  console.log('Model loaded');
  modelMesh = gltf.scene;
  modelMesh.traverse((child) => {
    if (child.isMesh) {
      child.castShadow = true;
      child.receiveShadow = true;
    }
  });
  modelMesh.position.set(0, 0, 0);
  scene.add(modelMesh);
  document.getElementById('progress-container').style.display = 'none';
  blinkEyesEvery2Sec();
}, undefined, console.error);
// Audio playback
function playBase64Audio(base64) {
  console.log(base64);
  audio = new Audio("data:audio/wav;base64," + base64);
  audio.play().catch((e) => console.error(":mute: Audio playback failed:", e));
}
// Load viseme JSON
function loadVisemeCues(jsonUrl) {
  fetch(jsonUrl)
    .then((res) => res.json())
    .then((json) => {
      mouthCues = json.mouthCues || [];
    })
    .catch(console.error);
}
// Register socket if exists
function registerSocketEvents() {
  if (!window.socket) {
    setTimeout(registerSocketEvents, 100);
    return;
  }
  window.socket.on("response", (data) => {
    console.log(data);
    if (data.audio) playBase64Audio(data.audio);
    if (data.visemes) loadVisemeCues(data.visemes);
  });
}
registerSocketEvents();
// Main animation loop
function animate() {
  requestAnimationFrame(animate);
  if (audio && modelMesh && mouthCues.length > 0) {
    const currentTimeMs = audio.currentTime * 1000;
    modelMesh.traverse((child) => {
      if (!child.isMesh || !child.morphTargetInfluences) return;
      for (let i = 0; i < child.morphTargetInfluences.length; i++) {
        if (i === 5 || i === 34) continue; // Don't reset blink morphs
        child.morphTargetInfluences[i] = 0;
      }
      for (const cue of mouthCues) {
        const shapeIndex = phonemeToIndex[cue.value];
        if (shapeIndex === undefined) continue;
        const start = cue.start * 1000;
        const end = cue.end * 1000;
        if (currentTimeMs >= start && currentTimeMs < end) {
          child.morphTargetInfluences[shapeIndex] = 0.5;
        }
      }
    });
  }
  controls.update();
  renderer.render(scene, camera);
}
animate();
// Blink every 2–5 seconds
function blinkEyesEvery2Sec() {
  function doBlink() {
    let blinkProgress = 0;
    let blinkDirection = 1;
    let didLog = false;
    function animateBlink() {
      if (!modelMesh) return;
      modelMesh.traverse((child) => {
        if (child.isMesh && child.morphTargetInfluences) {
          const influence = blinkProgress;
          if (!didLog) {
            didLog = true;
          }
          child.morphTargetInfluences[5] = influence;
          child.morphTargetInfluences[34] = influence;
        }
      });
      blinkProgress += 0.1 * blinkDirection;
      if (blinkProgress >= 1) {
        blinkProgress = 1;
        blinkDirection = -1;
      }
      if (blinkProgress <= 0 && blinkDirection === -1) {
        return;
      }
      requestAnimationFrame(animateBlink);
    }
    animateBlink();
  }
  setInterval(() => {
    doBlink();
  }, Math.floor(Math.random() * 2000) + 1000);
}
// Resize handler
window.addEventListener('resize', () => {
  camera.aspect = window.innerWidth / window.innerHeight;
  camera.updateProjectionMatrix();
  renderer.setSize(window.innerWidth, window.innerHeight);
});

