import * as THREE from "three";
import { OrbitControls } from "https://unpkg.com/three@0.168.0/examples/jsm/controls/OrbitControls.js";
import { OBJLoader } from "https://unpkg.com/three@0.168.0/examples/jsm/loaders/OBJLoader.js";
import { STLLoader } from "https://unpkg.com/three@0.168.0/examples/jsm/loaders/STLLoader.js";

const SITE_BASE = new URL(".", window.location.href);
const SAMPLE_DATA_URL = assetUrl("assets/test_samples/sample-data.json");
const OPTION_KEYS = "ABCDEFGHIJ".split("");

function assetUrl(path) {
  return new URL(path, SITE_BASE).toString();
}

const MODEL_LIBRARY = {
  thermalCycler: {
    label: "Thermal cycler / Bio-Rad C1000",
    description:
      "Interactive 3D reference asset for PCR and incubation workflows. The real Level 1 sample also shows three rendered test views from the public dataset.",
    parts: [
      ["assets/models/thermal_cycler/body-visual-0.obj", "#d7cfb6"],
      ["assets/models/thermal_cycler/body-visual-1.obj", "#b8b29e"],
      ["assets/models/thermal_cycler/body-visual-2.obj", "#d5ccb0"],
      ["assets/models/thermal_cycler/body-visual-3.obj", "#857e6d"],
      ["assets/models/thermal_cycler/lid-visual-0.obj", "#cbc29f"],
      ["assets/models/thermal_cycler/lid-visual-1.obj", "#706c61"],
      ["assets/models/thermal_cycler/lid-lever-visual-0.obj", "#3b3b3b"],
      ["assets/models/thermal_cycler/lid-lever-visual-1.obj", "#3b3b3b"],
      ["assets/models/thermal_cycler/lid-force-knob-visual-0.obj", "#00c2a8"],
      ["assets/models/thermal_cycler/reaction-block-visual-0.obj", "#5d5d66"],
    ],
    rotation: [-Math.PI / 2, 0, Math.PI],
    targetSize: 3.4,
    tags: ["3D asset", "PCR", "Protocol-conditioned action prediction"],
  },
  centrifugeMini: {
    label: "Mini centrifuge / Tiangen Tgear",
    description:
      "Interactive 3D reference asset for spin, clarification, and transfer stages in protocol-conditioned planning tasks.",
    parts: [
      ["assets/models/centrifuge_mini/body-visual-0.obj", "#262626"],
      ["assets/models/centrifuge_mini/body-visual-1.obj", "#f0dd34"],
      ["assets/models/centrifuge_mini/body-visual-2.obj", "#232323"],
      ["assets/models/centrifuge_mini/body-visual-3.obj", "#3a3a3a"],
      ["assets/models/centrifuge_mini/body-visual-4.obj", "#f0dd34"],
      ["assets/models/centrifuge_mini/lid-visual-0.obj", "#292929"],
      ["assets/models/centrifuge_mini/rotor-visual-0.obj", "#101010"],
    ],
    rotation: [-Math.PI / 2, 0, Math.PI],
    targetSize: 3.2,
    tags: ["3D asset", "Centrifugation", "Long-horizon planning"],
  },
  thermalMixer: {
    label: "Thermal mixer / Eppendorf C",
    description:
      "Interactive 3D reference asset for heating, shaking, incubation, and protocol-stage control.",
    parts: [
      ["assets/models/thermal_mixer/body-visual-0.obj", "#c8c2ad"],
      ["assets/models/thermal_mixer/body-visual-1.obj", "#2f2f2f"],
      ["assets/models/thermal_mixer/body-visual-2.obj", "#c8c2ad"],
      ["assets/models/thermal_mixer/body-visual-3.obj", "#395e94"],
      ["assets/models/thermal_mixer/body-visual-4.obj", "#969184"],
    ],
    rotation: [-Math.PI / 2, 0, Math.PI],
    targetSize: 3.1,
    tags: ["3D asset", "Incubation", "Parameter-sensitive actions"],
  },
  tube15ml: {
    label: "15 mL centrifuge tube",
    description:
      "Interactive 3D reference object for transfers, aliquots, and intermediate experimental material states.",
    stl: [
      ["assets/models/tube_15ml/centrifuge_tube_15ml_body.STL", "#d1e95a"],
      ["assets/models/tube_15ml/centrifuge_tube_15ml_cap.STL", "#cdd0d4"],
    ],
    rotation: [-Math.PI / 2, 0, Math.PI],
    targetSize: 2.7,
    tags: ["3D asset", "Container", "Intermediate state"],
  },
};

class InstrumentViewer {
  constructor(container) {
    this.container = container;
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.container.appendChild(this.renderer.domElement);

    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color("#101111");

    this.camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
    this.camera.position.set(0, 1.3, 4.6);

    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    this.controls.enableDamping = true;
    this.controls.autoRotate = true;
    this.controls.autoRotateSpeed = 0.8;
    this.controls.minDistance = 1.5;
    this.controls.maxDistance = 10;

    this.root = new THREE.Group();
    this.scene.add(this.root);

    this.scene.add(new THREE.HemisphereLight(0xf5fff3, 0x0d0e0e, 1.2));
    const keyLight = new THREE.DirectionalLight(0xffffff, 1.35);
    keyLight.position.set(4, 6, 5);
    this.scene.add(keyLight);
    const fillLight = new THREE.DirectionalLight(0x96ffe7, 0.5);
    fillLight.position.set(-3, 2, -4);
    this.scene.add(fillLight);

    const grid = new THREE.GridHelper(12, 24, 0x2c2c2c, 0x1d1d1d);
    grid.position.y = -1.35;
    this.scene.add(grid);

    const floor = new THREE.Mesh(
      new THREE.CircleGeometry(4.5, 64),
      new THREE.MeshBasicMaterial({ color: 0x161818, opacity: 0.85, transparent: true })
    );
    floor.rotation.x = -Math.PI / 2;
    floor.position.y = -1.34;
    this.scene.add(floor);

    this.objLoader = new OBJLoader();
    this.stlLoader = new STLLoader();
    this.cache = new Map();
    this.clock = new THREE.Clock();
    this.loadVersion = 0;

    this.handleResize = this.handleResize.bind(this);
    window.addEventListener("resize", this.handleResize);
    this.handleResize();
    this.animate();
  }

  animate() {
    this.animationHandle = requestAnimationFrame(() => this.animate());
    this.controls.update(this.clock.getDelta());
    this.renderer.render(this.scene, this.camera);
  }

  handleResize() {
    const width = this.container.clientWidth || 1;
    const height = this.container.clientHeight || 460;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
  }

  async loadModel(modelKey) {
    const definition = MODEL_LIBRARY[modelKey];
    if (!definition) {
      throw new Error(`Unknown model key: ${modelKey}`);
    }

    const loadVersion = ++this.loadVersion;
    const model = await this.getModelClone(modelKey, definition);
    if (loadVersion !== this.loadVersion) {
      return false;
    }

    this.root.clear();
    this.root.add(model);
    this.fitCameraToRoot();
    return this.root.children.length > 0;
  }

  async getModelClone(modelKey, definition) {
    if (!this.cache.has(modelKey)) {
      const built = await this.buildModel(definition);
      this.cache.set(modelKey, built);
    }

    return this.cache.get(modelKey).clone(true);
  }

  async buildModel(definition) {
    const group = new THREE.Group();
    const partConfigs = definition.parts || definition.stl || [];
    const parts = await Promise.all(
      partConfigs.map(async ([path, color]) => {
        const extension = path.split(".").pop().toLowerCase();
        const resolvedPath = assetUrl(path);
        if (extension === "obj") {
          return this.loadObjPart(resolvedPath, color);
        }
        if (extension === "stl") {
          return this.loadStlPart(resolvedPath, color);
        }
        return null;
      })
    );

    parts.filter(Boolean).forEach((part) => group.add(part));
    if (!group.children.length) {
      throw new Error(`No geometry loaded for ${definition.label}`);
    }

    const [rx, ry, rz] = definition.rotation || [0, 0, 0];
    group.rotation.set(rx, ry, rz);
    this.normalizeGroup(group, definition.targetSize || 3);
    return group;
  }

  async loadObjPart(path, color) {
    const object = await this.objLoader.loadAsync(path);
    object.traverse((child) => {
      if (child.isMesh) {
        child.material = new THREE.MeshStandardMaterial({
          color,
          metalness: 0.16,
          roughness: 0.74,
        });
      }
    });
    return object;
  }

  async loadStlPart(path, color) {
    const geometry = await this.stlLoader.loadAsync(path);
    geometry.computeVertexNormals();
    return new THREE.Mesh(
      geometry,
      new THREE.MeshStandardMaterial({
        color,
        metalness: 0.12,
        roughness: 0.65,
      })
    );
  }

  normalizeGroup(group, targetSize) {
    const box = new THREE.Box3().setFromObject(group);
    const size = box.getSize(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    const scale = targetSize / maxDim;
    group.scale.setScalar(scale);

    const scaledBox = new THREE.Box3().setFromObject(group);
    const center = scaledBox.getCenter(new THREE.Vector3());
    group.position.sub(center);

    const groundedBox = new THREE.Box3().setFromObject(group);
    group.position.y -= groundedBox.min.y + 0.25;
  }

  fitCameraToRoot() {
    const box = new THREE.Box3().setFromObject(this.root);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const maxDim = Math.max(size.x, size.y, size.z) || 1;
    const distance = maxDim * 1.65;
    this.camera.position.set(distance * 0.95, distance * 0.75, distance * 1.15);
    this.controls.target.copy(center);
    this.controls.update();
  }

  resetView() {
    this.fitCameraToRoot();
  }
}

const dom = {
  sectionNav: document.getElementById("section-nav"),
  sectionKicker: document.getElementById("section-kicker"),
  sectionTitle: document.getElementById("section-title"),
  sectionSummary: document.getElementById("section-summary"),
  sampleTabs: document.getElementById("sample-tabs"),
  featureKicker: document.getElementById("feature-kicker"),
  featureTitle: document.getElementById("feature-title"),
  featureDescription: document.getElementById("feature-description"),
  featureTags: document.getElementById("feature-tags"),
  singleViewStage: document.getElementById("single-view-stage"),
  multiViewStage: document.getElementById("multi-view-stage"),
  videoStage: document.getElementById("video-stage"),
  viewerStatus: document.getElementById("viewer-status"),
  miniCards: Array.from(document.querySelectorAll(".mini-view-card")),
  miniTitles: [0, 1, 2].map((index) => document.getElementById(`mini-title-${index}`)),
  miniStatuses: [0, 1, 2].map((index) => document.getElementById(`mini-status-${index}`)),
  resetView: document.getElementById("reset-view"),
  viewer: document.getElementById("viewer"),
  itemKind: document.getElementById("item-kind"),
  itemTitle: document.getElementById("item-title"),
  itemBody: document.getElementById("item-body"),
};

const mainViewer = new InstrumentViewer(dom.viewer);
const miniViewers = [null, null, null];
let SECTIONS = [];
const state = { sectionId: "", sampleId: "" };

function getMiniViewer(index) {
  if (!miniViewers[index]) {
    miniViewers[index] = new InstrumentViewer(document.getElementById(`mini-viewer-${index}`));
  }
  return miniViewers[index];
}

function buildSections(data) {
  return [
    {
      id: "level-1",
      label: "Level 1",
      navTitle: "Laboratory 3D Asset Perception",
      navMeta: "Multi-view asset + historical actions + candidate next actions",
      kicker: "Level 1",
      title: "Laboratory 3D Asset Perception",
      summary:
        "Protocol-conditioned next-action prediction from three real asset views, historical actions, and candidate next actions.",
      note:
        "Level 1 keeps the left-side view focused on one interactive 3D laboratory asset while the right side shows the real public test sample and its three rendered dataset views.",
      samples: data.level1.map((row, index) => ({
        ...row,
        id: row.id,
        tabTitle: `Test ${index + 1}`,
        tabMeta: row.asset_name,
        kind: "Protocol-conditioned next action",
      })),
    },
    {
      id: "level-2",
      label: "Level 2",
      navTitle: "Long-Horizon Planning",
      navMeta: "Context + constraints + action pool -> structured action sequence",
      kicker: "Level 2",
      title: "Long-Horizon Protocol-Conditioned Planning",
      summary:
        "Protocol-conditioned long-horizon planning where the model produces a structured experimental action sequence from an action pool.",
      note:
        "Level 2 uses a multi-instrument 3D context because planning errors often come from action omissions, order swaps, parameter drift, and broken intermediate-state dependencies.",
      samples: data.level2.map((row, index) => ({
        ...row,
        id: row.id,
        tabTitle: `Test ${index + 1}`,
        tabMeta: row.title,
        kind: "Structured action sequence",
      })),
    },
  ];
}

function getSectionById(sectionId) {
  return SECTIONS.find((entry) => entry.id === sectionId) || SECTIONS[0];
}

function getSampleById(section, sampleId) {
  return section.samples.find((entry) => entry.id === sampleId) || section.samples[0];
}

function initializeState() {
  const params = new URLSearchParams(window.location.search);
  const section = getSectionById(params.get("section") || SECTIONS[0].id);
  const sample = getSampleById(section, params.get("item") || params.get("sample") || section.samples[0].id);
  state.sectionId = section.id;
  state.sampleId = sample.id;
}

function syncUrl(sectionId, sampleId) {
  const params = new URLSearchParams(window.location.search);
  params.set("section", sectionId);
  params.set("item", sampleId);
  window.history.replaceState({}, "", `${window.location.pathname}?${params.toString()}`);
}

function setStatus(node, text, visible) {
  node.textContent = text;
  node.classList.toggle("is-hidden", !visible);
}

function renderTags(tags) {
  dom.featureTags.innerHTML = "";
  tags.forEach((tag) => {
    const chip = document.createElement("span");
    chip.className = "feature-tag";
    chip.textContent = tag;
    dom.featureTags.appendChild(chip);
  });
}

function showFeatureMode(mode) {
  dom.singleViewStage.hidden = mode !== "single";
  dom.multiViewStage.hidden = mode !== "multi";
  dom.videoStage.hidden = true;
}

async function renderSingleAsset(sample) {
  const model = MODEL_LIBRARY[sample.modelKey];
  dom.featureKicker.textContent = "Interactive 3D Asset";
  dom.featureTitle.textContent = model.label;
  dom.featureDescription.textContent = `${model.description} Dataset sample: ${sample.id}.`;
  renderTags([sample.asset_family, sample.asset_name, ...model.tags]);
  dom.resetView.hidden = false;

  showFeatureMode("single");
  mainViewer.handleResize();
  setStatus(dom.viewerStatus, "Loading 3D asset...", true);

  try {
    const loaded = await mainViewer.loadModel(sample.modelKey);
    if (!loaded) {
      throw new Error("No model content was added to the scene.");
    }
    setStatus(dom.viewerStatus, "", false);
  } catch (error) {
    console.error(error);
    setStatus(dom.viewerStatus, "The 3D asset could not be rendered in this browser session.", true);
  }
}

async function renderInstrumentSet(sample) {
  dom.featureKicker.textContent = "3D Instrument Context";
  dom.featureTitle.textContent = sample.title;
  dom.featureDescription.textContent =
    "A compact 3D instrument set is retained to keep long-horizon protocol planning tied to laboratory assets and intermediate experimental states.";
  renderTags(["Action pool", "AST scoring", "Protocol-conditioned planning"]);
  dom.resetView.hidden = true;

  showFeatureMode("multi");
  setStatus(dom.viewerStatus, "", false);

  await Promise.all(
    dom.miniCards.map(async (card, index) => {
      const modelKey = sample.modelKeys[index];
      if (!modelKey) {
        card.hidden = true;
        return;
      }

      card.hidden = false;
      const model = MODEL_LIBRARY[modelKey];
      const viewer = getMiniViewer(index);
      dom.miniTitles[index].textContent = model.label;
      viewer.handleResize();
      setStatus(dom.miniStatuses[index], "Loading 3D asset...", true);

      try {
        const loaded = await viewer.loadModel(modelKey);
        if (!loaded) {
          throw new Error("No model content was added to the scene.");
        }
        setStatus(dom.miniStatuses[index], "", false);
      } catch (error) {
        console.error(error);
        setStatus(dom.miniStatuses[index], "The 3D asset failed to load.", true);
      }
    })
  );
}

async function renderFeature(section, sample) {
  if (section.id === "level-1") {
    await renderSingleAsset(sample);
    return;
  }
  await renderInstrumentSet(sample);
}

function createTextBlock(title, content) {
  const block = document.createElement("section");
  block.className = "detail-block";
  const heading = document.createElement("h4");
  heading.textContent = title;
  const paragraph = document.createElement("p");
  paragraph.textContent = content;
  block.append(heading, paragraph);
  return block;
}

function createListBlock(title, items, ordered = false) {
  const block = document.createElement("section");
  block.className = "detail-block";
  const heading = document.createElement("h4");
  heading.textContent = title;
  const list = document.createElement(ordered ? "ol" : "ul");
  items.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    list.appendChild(li);
  });
  block.append(heading, list);
  return block;
}

function createStepCardBlock(title, items, label = "Step") {
  const block = document.createElement("section");
  block.className = "detail-block";
  const heading = document.createElement("h4");
  heading.textContent = title;
  const grid = document.createElement("div");
  grid.className = "step-card-grid";

  items.forEach((item, index) => {
    const card = document.createElement("article");
    card.className = "step-card";
    const badge = document.createElement("span");
    badge.className = "step-card-badge";
    badge.textContent = `${label} ${index + 1}`;
    const text = document.createElement("p");
    text.textContent = item;
    card.append(badge, text);
    grid.appendChild(card);
  });

  block.append(heading, grid);
  return block;
}

function createCodeBlock(title, content) {
  const block = document.createElement("section");
  block.className = "detail-block";
  const heading = document.createElement("h4");
  heading.textContent = title;
  const pre = document.createElement("pre");
  pre.className = "detail-code";
  const code = document.createElement("code");
  code.textContent = content;
  pre.appendChild(code);
  block.append(heading, pre);
  return block;
}

function createImageGallery(sample) {
  const block = document.createElement("section");
  block.className = "detail-block";
  const heading = document.createElement("h4");
  heading.textContent = "Dataset asset views";
  const grid = document.createElement("div");
  grid.className = "asset-view-grid";

  sample.image_paths.forEach((path, index) => {
    const card = document.createElement("figure");
    card.className = "asset-view-card";
    const image = document.createElement("img");
    image.src = assetUrl(path);
    image.alt = `${sample.asset_name} view ${index + 1}`;
    const caption = document.createElement("figcaption");
    caption.textContent = `View ${index + 1}`;
    card.append(image, caption);
    grid.appendChild(card);
  });

  block.append(heading, grid);
  return block;
}

function createOptionBlock(options, goldAction = "") {
  const block = document.createElement("section");
  block.className = "detail-block";
  const heading = document.createElement("h4");
  heading.textContent = "Candidate next actions";
  const list = document.createElement("div");
  list.className = "option-list";

  options.forEach((text, index) => {
    const item = document.createElement("div");
    item.className = "option-item";
    if (goldAction && text.trim() === goldAction.trim()) {
      item.classList.add("is-gold");
    }
    const key = document.createElement("span");
    key.className = "option-key";
    key.textContent = OPTION_KEYS[index] || `${index + 1}`;
    const value = document.createElement("span");
    value.textContent = text;
    item.append(key, value);
    list.appendChild(item);
  });

  block.append(heading, list);
  return block;
}

function findGoldOptionKey(sample) {
  const gold = sample.next_action.trim();
  const index = sample.candidate_next_actions.findIndex((candidate) => candidate.trim() === gold);
  return index >= 0 ? OPTION_KEYS[index] || `${index + 1}` : "Unmatched";
}

function createGoldActionBlock(sample) {
  const block = document.createElement("section");
  block.className = "detail-block";
  const heading = document.createElement("h4");
  heading.textContent = "Gold next action";
  const box = document.createElement("div");
  box.className = "gold-action-box";
  const badge = document.createElement("span");
  badge.className = "gold-option-badge";
  badge.textContent = findGoldOptionKey(sample);
  const text = document.createElement("span");
  text.textContent = sample.next_action;
  box.append(badge, text);
  block.append(heading, box);
  return block;
}

function parseAvailableInputs(rawInputs) {
  try {
    const parsed = JSON.parse(rawInputs);
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.error(error);
    return [];
  }
}

function createInputCardsBlock(rawInputs) {
  const block = document.createElement("section");
  block.className = "detail-block";
  const heading = document.createElement("h4");
  heading.textContent = "Available inputs";
  const grid = document.createElement("div");
  grid.className = "input-card-grid";

  parseAvailableInputs(rawInputs).forEach((input) => {
    const card = document.createElement("article");
    card.className = "input-card";
    const name = document.createElement("h5");
    name.textContent = input.name || "input";
    const description = document.createElement("p");
    description.textContent = input.description || "No description provided.";
    card.append(name, description);
    grid.appendChild(card);
  });

  block.append(heading, grid);
  return block;
}

function parseDocstring(docstring) {
  const lines = docstring
    .replace(/\r/g, "")
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
  const description = [];
  const args = [];
  const returns = [];
  let mode = "description";

  lines.forEach((line) => {
    if (line === "Args:") {
      mode = "args";
      return;
    }
    if (line === "Returns:") {
      mode = "returns";
      return;
    }
    if (mode === "args") {
      const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*):\s*(.*)$/);
      if (match) {
        args.push({ name: match[1], description: match[2] });
      }
      return;
    }
    if (mode === "returns") {
      returns.push(line);
      return;
    }
    description.push(line);
  });

  return {
    description: description.join(" "),
    args,
    returns: returns.join(" "),
  };
}

function parseActionPool(actionPool) {
  const pattern = /def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(([^)]*)\)[^:]*:\s*[\r\n]+\s*"""([\s\S]*?)"""/g;
  const actions = [];
  let match = pattern.exec(actionPool);

  while (match) {
    const params = match[2]
      .split(",")
      .map((param) => param.trim().split(":")[0].trim())
      .filter(Boolean);
    actions.push({
      name: match[1],
      params,
      ...parseDocstring(match[3]),
    });
    match = pattern.exec(actionPool);
  }

  return actions;
}

function createActionPoolBlock(sample) {
  const block = document.createElement("section");
  block.className = "detail-block";
  const heading = document.createElement("h4");
  const actionNames = Array.isArray(sample.action_pool_names) ? sample.action_pool_names : [];
  const parsedActions = parseActionPool(sample.action_pool);
  const byName = new Map(parsedActions.map((action) => [action.name, action]));
  const actions = actionNames.map((name) => byName.get(name) || { name, params: [], description: "" });
  heading.textContent = `Action pool (${actions.length} available actions)`;
  const caption = document.createElement("p");
  caption.className = "block-caption";
  caption.textContent =
    "The pool lists all callable action types for this task; the gold sequence uses only the subset required by the current protocol segment.";
  const grid = document.createElement("div");
  grid.className = "action-pool-grid";

  actions.forEach((action) => {
    const card = document.createElement("details");
    card.className = "action-card";

    const summary = document.createElement("summary");
    summary.textContent = `${action.name} · ${action.params.length} inputs`;

    const detail = document.createElement("div");
    detail.className = "action-detail";
    const inner = document.createElement("div");
    inner.className = "action-detail-inner";

    const description = document.createElement("p");
    description.textContent = action.description || "No action description available.";
    inner.appendChild(description);

    if (action.args?.length) {
      const args = document.createElement("div");
      args.className = "arg-grid";
      action.args.forEach((arg) => {
        const chip = document.createElement("div");
        chip.className = "arg-chip";
        const argName = document.createElement("strong");
        argName.textContent = arg.name;
        const argDescription = document.createElement("span");
        argDescription.textContent = arg.description;
        chip.append(argName, argDescription);
        args.appendChild(chip);
      });
      inner.appendChild(args);
    }

    if (action.returns) {
      const returns = document.createElement("p");
      returns.className = "returns-line";
      returns.textContent = `Returns: ${action.returns}`;
      inner.appendChild(returns);
    }

    detail.appendChild(inner);
    card.append(summary, detail);
    grid.appendChild(card);
  });

  block.append(heading, caption, grid);
  return block;
}

function splitTopLevel(text) {
  const result = [];
  let current = "";
  let quote = "";
  let depth = 0;
  let escaped = false;

  for (const char of text) {
    if (quote) {
      current += char;
      if (escaped) {
        escaped = false;
      } else if (char === "\\") {
        escaped = true;
      } else if (char === quote) {
        quote = "";
      }
      continue;
    }
    if (char === "'" || char === '"') {
      quote = char;
      current += char;
      continue;
    }
    if (char === "(" || char === "[" || char === "{") {
      depth += 1;
    } else if (char === ")" || char === "]" || char === "}") {
      depth = Math.max(0, depth - 1);
    }
    if (char === "," && depth === 0) {
      result.push(current.trim());
      current = "";
      continue;
    }
    current += char;
  }

  if (current.trim()) {
    result.push(current.trim());
  }
  return result;
}

function parseActionSequence(sequence) {
  return sequence
    .split(/\n+/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line, index) => {
      const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\((.*)\)$/);
      if (!match) {
        return {
          index: index + 1,
          output: `step${index + 1}`,
          action: "unparsed_action",
          params: [{ key: "raw", value: line }],
        };
      }
      const params = splitTopLevel(match[3]).map((entry) => {
        const eqIndex = entry.indexOf("=");
        if (eqIndex < 0) {
          return { key: "arg", value: entry };
        }
        return {
          key: entry.slice(0, eqIndex).trim(),
          value: entry.slice(eqIndex + 1).trim(),
        };
      });
      return {
        index: index + 1,
        output: match[1],
        action: match[2],
        params,
      };
    });
}

function createGoldSequenceMap(sequence) {
  const block = document.createElement("section");
  block.className = "detail-block";
  const heading = document.createElement("h4");
  const map = document.createElement("div");
  map.className = "sequence-map";
  const steps = parseActionSequence(sequence);
  const uniqueActions = new Set(steps.map((step) => step.action));
  heading.textContent = `Gold action sequence (${steps.length} steps)`;
  const caption = document.createElement("p");
  caption.className = "block-caption";
  caption.textContent = `This target sequence uses ${uniqueActions.size} action types from the available pool and connects intermediate outputs through explicit dependencies.`;
  const outputToStep = new Map(steps.map((step) => [step.output, step.index]));

  steps.forEach((step) => {
    const node = document.createElement("article");
    node.className = "sequence-node";

    const index = document.createElement("div");
    index.className = "sequence-index";
    index.textContent = `Step ${step.index}`;

    const body = document.createElement("div");
    body.className = "sequence-body";
    const action = document.createElement("h5");
    action.textContent = step.action;
    const output = document.createElement("p");
    output.className = "sequence-output";
    output.textContent = `Output: ${step.output}`;

    const params = document.createElement("div");
    params.className = "param-grid";
    step.params.forEach((param) => {
      const chip = document.createElement("span");
      chip.className = "param-chip";
      chip.textContent = `${param.key} = ${param.value}`;
      params.appendChild(chip);
    });

    body.append(action, output, params);
    const dependencies = step.params
      .filter((param) => outputToStep.has(param.value))
      .map((param) => `${param.key} <- Step ${outputToStep.get(param.value)}`);
    if (dependencies.length) {
      const depGrid = document.createElement("div");
      depGrid.className = "dependency-grid";
      dependencies.forEach((dependency) => {
        const chip = document.createElement("span");
        chip.className = "dependency-chip";
        chip.textContent = dependency;
        depGrid.appendChild(chip);
      });
      body.appendChild(depGrid);
    }

    node.append(index, body);
    map.appendChild(node);
  });

  block.append(heading, caption, map);
  return block;
}

function createAnswerBox(title, text, className) {
  const block = document.createElement("section");
  block.className = "detail-block";
  const heading = document.createElement("h4");
  heading.textContent = title;
  const box = document.createElement("div");
  box.className = className;
  box.textContent = text;
  block.append(heading, box);
  return block;
}

function renderNav() {
  dom.sectionNav.innerHTML = "";
  SECTIONS.forEach((section) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `nav-button${state.sectionId === section.id ? " active" : ""}`;
    const label = document.createElement("span");
    label.className = "nav-label";
    label.textContent = `${section.label} · ${section.navTitle}`;
    const meta = document.createElement("span");
    meta.className = "nav-meta";
    meta.textContent = section.navMeta;
    button.append(label, meta);
    button.addEventListener("click", () => {
      state.sectionId = section.id;
      state.sampleId = section.samples[0].id;
      render();
    });
    dom.sectionNav.appendChild(button);
  });
}

function renderSampleTabs(section) {
  dom.sampleTabs.innerHTML = "";
  section.samples.forEach((sample) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = `sample-button${state.sampleId === sample.id ? " active" : ""}`;
    const title = document.createElement("span");
    title.className = "sample-title";
    title.textContent = sample.tabTitle;
    const meta = document.createElement("span");
    meta.className = "sample-meta";
    meta.textContent = `${sample.id} · ${sample.tabMeta}`;
    button.append(title, meta);
    button.addEventListener("click", () => {
      state.sampleId = sample.id;
      render();
    });
    dom.sampleTabs.appendChild(button);
  });
}

function renderItemBody(section, sample) {
  dom.itemKind.textContent = sample.kind;
  dom.itemTitle.textContent = sample.title;
  dom.itemBody.innerHTML = "";

  if (section.id === "level-1") {
    dom.itemBody.appendChild(createImageGallery(sample));
    dom.itemBody.appendChild(createTextBlock("Historical actions", sample.historical_actions));
    dom.itemBody.appendChild(createOptionBlock(sample.candidate_next_actions, sample.next_action));
    dom.itemBody.appendChild(createStepCardBlock("Reference reasoning", sample.reasoning, "Reason"));
    dom.itemBody.appendChild(createGoldActionBlock(sample));
    return;
  }

  const visibleInstruments = sample.modelKeys.map((modelKey) => MODEL_LIBRARY[modelKey].label);
  dom.itemBody.appendChild(createListBlock("Visible 3D instruments", visibleInstruments));
  dom.itemBody.appendChild(createTextBlock("Context", sample.context));
  dom.itemBody.appendChild(createTextBlock("Goal", sample.goal));
  dom.itemBody.appendChild(createStepCardBlock("Constraints", sample.constraints, "Constraint"));
  dom.itemBody.appendChild(createInputCardsBlock(sample.available_inputs));
  dom.itemBody.appendChild(createActionPoolBlock(sample));
  dom.itemBody.appendChild(createGoldSequenceMap(sample.gold_action_sequence));
}

async function render() {
  const section = getSectionById(state.sectionId);
  const sample = getSampleById(section, state.sampleId);
  state.sectionId = section.id;
  state.sampleId = sample.id;

  renderNav();
  renderSampleTabs(section);
  dom.sectionKicker.textContent = section.kicker;
  dom.sectionTitle.textContent = section.title;
  dom.sectionSummary.textContent = section.summary;

  renderItemBody(section, sample);
  await renderFeature(section, sample);
  syncUrl(section.id, sample.id);
}

async function init() {
  try {
    const response = await fetch(SAMPLE_DATA_URL);
    if (!response.ok) {
      throw new Error(`Failed to load sample data: ${response.status}`);
    }
    const data = await response.json();
    SECTIONS = buildSections(data);
    initializeState();
    await render();
  } catch (error) {
    console.error(error);
    dom.sectionKicker.textContent = "Load error";
    dom.sectionTitle.textContent = "Could not load LabHorizon samples";
    dom.sectionSummary.textContent = "The static sample-data.json file is missing or unavailable.";
    dom.itemBody.innerHTML = "";
    dom.itemBody.appendChild(createAnswerBox("Error", String(error.message || error), "answer-box"));
  }
}

dom.resetView.addEventListener("click", () => mainViewer.resetView());

init();
