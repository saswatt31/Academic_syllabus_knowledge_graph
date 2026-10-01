/* ============================================================
   Syllabus Atlas — demo logic. Everything is driven by the REAL
   exported graph (frontend/data/graph.json), built by
   frontend/build_demo_data.py from results/nodes.csv + edges.csv.
   ============================================================ */

let G = null;            // graph.json bundle
let sim = null;          // main graph simulation state

const TYPE_COLORS = {
  COURSE: "#1E3A8A",       // University Cobalt
  PREREQUISITE: "#B45309", // Amber Ochre
  TOPIC: "#047857",        // Forest Green
  OUTCOME: "#0F766E",      // Teal
  INSTRUCTOR: "#BE123C",   // Crimson
  CREDITS: "#6B7280",      // Slate
};
const REL_COLORS = {
  PREREQUISITE_OF: "#B45309", CO_REQUISITE_OF: "#D97706",
};

async function loadJSON(url) {
  if (window.GRAPH_DATA) return window.GRAPH_DATA;
  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load " + url);
    return await res.json();
  } catch (err) {
    if (window.GRAPH_DATA) return window.GRAPH_DATA;
    throw err;
  }
}

const shortLabel = (label, n = 30) =>
  label.length > n ? label.slice(0, n - 1) + "…" : label;

/* ================= force simulation ================= */
function makeSim(nodes, edges, w, h) {
  const map = new Map();
  const count = Math.max(1, nodes.length);
  const R = Math.min(w, h) * 0.32;
  nodes.forEach((n, idx) => {
    const isMajor = n.type === "COURSE" || n.type === "PREREQUISITE";
    const rad = isMajor ? R * 0.55 : R * (0.85 + 0.15 * ((idx % 5) / 5));
    const angle = (idx / count) * 2 * Math.PI;
    map.set(n.id, {
      ...n,
      x: w / 2 + Math.cos(angle) * rad,
      y: h / 2 + Math.sin(angle) * rad,
      vx: 0,
      vy: 0,
    });
  });
  const links = edges
    .filter((e) => map.has(e.head) && map.has(e.tail))
    .map((e) => ({ s: map.get(e.head), t: map.get(e.tail), rel: e.relation }));
  return { nodes: [...map.values()], links, w, h };
}

function stepSim(sim, alpha) {
  if (alpha <= 0.0005) return;
  const { nodes, links, w, h } = sim;

  // 1. Repulsion (capped Coulomb with minimum distance floor)
  for (let i = 0; i < nodes.length; i++) {
    const a = nodes[i];
    for (let j = i + 1; j < nodes.length; j++) {
      const b = nodes[j];
      let dx = a.x - b.x;
      let dy = a.y - b.y;
      let d2 = dx * dx + dy * dy;
      if (d2 < 25) {
        d2 = 25;
        dx = (Math.random() - 0.5) * 2;
        dy = (Math.random() - 0.5) * 2;
      }
      if (d2 > 60000) continue;
      const d = Math.sqrt(d2);
      const f = Math.min(2.5, 750 / d2);
      const fx = (dx / d) * f;
      const fy = (dy / d) * f;
      a.vx += fx; a.vy += fy;
      b.vx -= fx; b.vy -= fy;
    }
  }

  // 2. Spring forces on links
  for (const l of links) {
    const dx = l.t.x - l.s.x;
    const dy = l.t.y - l.s.y;
    const d = Math.sqrt(dx * dx + dy * dy) || 1;
    const targetDist = 70;
    const f = Math.max(-2.5, Math.min(2.5, (d - targetDist) * 0.012));
    const fx = (dx / d) * f;
    const fy = (dy / d) * f;
    l.s.vx += fx; l.s.vy += fy;
    l.t.vx -= fx; l.t.vy -= fy;
  }

  // 3. Centering gravity, heavy damping, and velocity integration
  const maxDisplacement = 2.0;
  for (const n of nodes) {
    n.vx += (w / 2 - n.x) * 0.001;
    n.vy += (h / 2 - n.y) * 0.001;

    // Heavy friction/damping (0.58 = 42% kinetic dissipation per tick)
    n.vx *= 0.58;
    n.vy *= 0.58;

    const stepX = Math.max(-maxDisplacement, Math.min(maxDisplacement, n.vx * alpha));
    const stepY = Math.max(-maxDisplacement, Math.min(maxDisplacement, n.vy * alpha));
    n.x += stepX;
    n.y += stepY;

    n.x = Math.max(22, Math.min(w - 22, n.x));
    n.y = Math.max(22, Math.min(h - 22, n.y));
  }
}

function nodeRadius(t) {
  return { COURSE: 13, PREREQUISITE: 11, OUTCOME: 5.5, INSTRUCTOR: 7,
           CREDITS: 6, TOPIC: 4.5 }[t] || 5;
}

/* ================= hero mini-graph ================= */
function initHero() {
  const canvas = document.getElementById("heroGraph");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;

  // courses + direct neighbours
  const keep = new Set();
  for (const e of G.edges) {
    const hc = /^([A-Z]{2,4}\d{3})\b/.test(e.head);
    if (hc) { keep.add(e.head); keep.add(e.tail); }
  }
  for (const e of G.edges) {
    if (e.relation.includes("REQUISITE")) { keep.add(e.head); keep.add(e.tail); }
  }
  const nodes = G.nodes.filter((n) => keep.has(n.id));
  const edges = G.edges.filter((e) => keep.has(e.head) && keep.has(e.tail));
  const s = makeSim(nodes, edges, W, H);

  // Thorough pre-warmup: settle base equilibrium positions
  for (let i = 0; i < 260; i++) {
    stepSim(s, Math.max(0.1, 1 - i / 260));
  }

  // Anchor resting positions and configure unique harmonic drift for each node
  s.nodes.forEach((n, idx) => {
    n.baseX = n.x;
    n.baseY = n.y;
    // Distinct phase and frequency scaled to 0.8x of previous speed (1.2x baseline)
    n.phaseX = (idx * 1.618) % (Math.PI * 2);
    n.phaseY = (idx * 2.718) % (Math.PI * 2);
    n.speedX = (0.00065 + ((idx % 7) * 0.0001)) * 1.2; // 0.8x of previous (1.2x baseline, ~5.5-7.5s period)
    n.speedY = (0.00055 + ((idx % 5) * 0.0001)) * 1.2;
    // Calibrated amplitude
    n.ampX = 4.6 + (idx % 3) * 1.3;
    n.ampY = 4.0 + (idx % 4) * 1.1;
  });

  const prefersReduced = window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function renderHero(timestamp) {
    const t = timestamp || performance.now();

    // Update node positions with gentle continuous harmonic floating motion
    if (!prefersReduced) {
      for (const n of s.nodes) {
        n.x = n.baseX + Math.sin(t * n.speedX + n.phaseX) * n.ampX;
        n.y = n.baseY + Math.cos(t * n.speedY + n.phaseY) * n.ampY;
      }
    }

    ctx.fillStyle = "#FFFFFF";
    ctx.fillRect(0, 0, W, H);

    // Links
    ctx.lineWidth = 1;
    for (const l of s.links) {
      const relCol = REL_COLORS[l.rel];
      ctx.strokeStyle = relCol || "rgba(209, 213, 219, 0.85)";
      ctx.beginPath();
      ctx.moveTo(l.s.x, l.s.y);
      ctx.lineTo(l.t.x, l.t.y);
      ctx.stroke();
    }

    // Nodes
    for (const n of s.nodes) {
      const r = nodeRadius(n.type);
      ctx.fillStyle = TYPE_COLORS[n.type] || "#888";
      ctx.beginPath();
      ctx.arc(n.x, n.y, r, 0, 7);
      ctx.fill();
      if (n.type === "COURSE" || n.type === "PREREQUISITE") {
        ctx.fillStyle = "#111827";
        ctx.font = "600 11px 'IBM Plex Mono', monospace";
        ctx.fillText(n.code || n.label, n.x + r + 4, n.y + 3);
      }
    }

    if (!prefersReduced) {
      requestAnimationFrame(renderHero);
    }
  }

  requestAnimationFrame(renderHero);
}

/* ================= main explorer ================= */
function initMainGraph() {
  const canvas = document.getElementById("mainGraph");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");
  const W = canvas.width, H = canvas.height;
  sim = makeSim(G.nodes, G.edges, W, H);

  // Pre-warmup 350 steps so nodes are firmly settled in their positions
  for (let i = 0; i < 350; i++) {
    stepSim(sim, Math.max(0.1, 1 - i / 350));
  }

  const view = { k: 1, x: 0, y: 0 };
  let selected = null, highlight = null;
  let alpha = 0.05;
  let animating = false;

  function toWorld(px, py) {
    return { x: (px - view.x) / view.k, y: (py - view.y) / view.k };
  }

  function getCanvasCoords(e) {
    const rect = canvas.getBoundingClientRect();
    const mx = (e.clientX - rect.left) * (W / rect.width);
    const my = (e.clientY - rect.top) * (H / rect.height);
    return { mx, my };
  }

  function renderMain() {
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = "#FFFFFF";
    ctx.fillRect(0, 0, W, H);
    ctx.translate(view.x, view.y);
    ctx.scale(view.k, view.k);

    for (const l of sim.links) {
      const isSelected = selected && (l.s === selected || l.t === selected);
      const isHighlighted = highlight && (l.s === highlight.n || l.t === highlight.n);
      const hot = isSelected || isHighlighted;

      if (hot) {
        ctx.strokeStyle = REL_COLORS[l.rel] || "#1E3A8A";
        ctx.lineWidth = 2.4;
      } else {
        ctx.strokeStyle = selected ? "rgba(229, 231, 235, 0.45)" : (REL_COLORS[l.rel] || "rgba(229, 231, 235, 0.9)");
        ctx.lineWidth = 1;
      }
      ctx.beginPath(); ctx.moveTo(l.s.x, l.s.y); ctx.lineTo(l.t.x, l.t.y); ctx.stroke();
    }

    for (const n of sim.nodes) {
      const r = nodeRadius(n.type);
      const isSel = selected === n || (highlight && highlight.n === n);
      const isNeighbor = selected && sim.links.some((l) => (l.s === selected && l.t === n) || (l.t === selected && l.s === n));

      ctx.fillStyle = TYPE_COLORS[n.type] || "#888";
      ctx.beginPath();
      ctx.arc(n.x, n.y, isSel ? r + 3 : r, 0, 7);
      ctx.fill();

      if (isSel) {
        ctx.strokeStyle = "#1E3A8A";
        ctx.lineWidth = 3;
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 5, 0, 7);
        ctx.stroke();
      } else if (isNeighbor) {
        ctx.strokeStyle = "#B45309";
        ctx.lineWidth = 1.6;
        ctx.beginPath();
        ctx.arc(n.x, n.y, r + 3, 0, 7);
        ctx.stroke();
      }

      if (isSel || n.type === "COURSE" || n.type === "PREREQUISITE" || view.k > 1.5) {
        ctx.fillStyle = isSel ? "#1E3A8A" : "#111827";
        ctx.font = isSel ? "700 12px 'IBM Plex Mono', monospace" : "600 11px 'IBM Plex Mono', monospace";
        ctx.fillText(shortLabel(n.code || n.label, 28), n.x + r + 5, n.y + 4);
      }
    }
  }

  function requestDraw() {
    if (!animating) {
      animating = true;
      requestAnimationFrame(tick);
    }
  }

  function tick() {
    if (alpha > 0.001) {
      stepSim(sim, alpha);
      alpha *= 0.95;
    }

    renderMain();

    if (alpha > 0.001 || isPanning) {
      requestAnimationFrame(tick);
    } else {
      animating = false;
      renderMain();
    }
  }
  requestDraw();

  // ----- generous hit detection for clicking
  function hit(mx, my) {
    const p = toWorld(mx, my);
    for (const n of sim.nodes) {
      const dx = p.x - n.x, dy = p.y - n.y;
      const r = Math.max(15, nodeRadius(n.type) + 8);
      if (dx * dx + dy * dy < r * r) return n;
    }
    return null;
  }

  let isPanning = false;
  let pan = null;
  let downPos = null;

  canvas.addEventListener("mousedown", (e) => {
    downPos = { x: e.clientX, y: e.clientY };
    const { mx, my } = getCanvasCoords(e);
    const n = hit(mx, my);
    if (!n) {
      // Background click: initiate canvas pan
      isPanning = true;
      pan = { startX: e.clientX, startY: e.clientY, vx: view.x, vy: view.y };
      canvas.style.cursor = "grabbing";
    }
  });

  window.addEventListener("mousemove", (e) => {
    if (isPanning && pan) {
      view.x = pan.vx + (e.clientX - pan.startX);
      view.y = pan.vy + (e.clientY - pan.startY);
      requestDraw();
      return;
    }

    const rect = canvas.getBoundingClientRect();
    if (
      e.clientX >= rect.left &&
      e.clientX <= rect.right &&
      e.clientY >= rect.top &&
      e.clientY <= rect.bottom
    ) {
      const { mx, my } = getCanvasCoords(e);
      const n = hit(mx, my);
      canvas.style.cursor = n ? "pointer" : "grab";
    }
  });

  window.addEventListener("mouseup", () => {
    if (isPanning) {
      isPanning = false;
      pan = null;
      canvas.style.cursor = "grab";
    }
  });

  canvas.addEventListener("mouseleave", () => {
    if (isPanning) {
      isPanning = false;
      pan = null;
    }
    canvas.style.cursor = "default";
  });

  canvas.addEventListener("click", (e) => {
    if (downPos) {
      const dist = Math.hypot(e.clientX - downPos.x, e.clientY - downPos.y);
      if (dist > 6) return; // user dragged canvas to pan, ignore as node click
    }
    const { mx, my } = getCanvasCoords(e);
    const n = hit(mx, my);
    if (n) {
      select(n);
    }
  });

  canvas.addEventListener("wheel", (e) => {
    e.preventDefault();
    const { mx, my } = getCanvasCoords(e);
    const k = Math.min(3.5, Math.max(0.45, view.k * (e.deltaY < 0 ? 1.08 : 0.92)));
    view.x = mx - (mx - view.x) * (k / view.k);
    view.y = my - (my - view.y) * (k / view.k);
    view.k = k;
    requestDraw();
  }, { passive: false });

  document.getElementById("zoomIn").onclick = () => {
    view.k = Math.min(3.5, view.k * 1.2);
    requestDraw();
  };
  document.getElementById("zoomOut").onclick = () => {
    view.k = Math.max(0.45, view.k / 1.2);
    requestDraw();
  };
  document.getElementById("zoomFit").onclick = () => {
    view.k = 1;
    view.x = 0;
    view.y = 0;
    requestDraw();
  };

  function select(n) {
    selected = n;
    highlight = null;

    const body = document.querySelector(".inspector-content");
    const ph = document.querySelector(".inspector-prompt");
    if (ph) ph.style.display = "none";
    if (body) {
      body.hidden = false;
      body.removeAttribute("hidden");
      body.style.display = "block";
    }
    const t = document.getElementById("iType");
    if (t) {
      t.textContent = n.type;
      t.className = "node-badge " + n.type;
    }
    const nameEl = document.getElementById("iName");
    if (nameEl) nameEl.textContent = n.label;
    const statsEl = document.getElementById("iStats");
    if (statsEl) {
      statsEl.innerHTML = `<span><b>${n.out}</b> outgoing</span><span><b>${n["in"]}</b> incoming</span>`;
    }
    const rels = G.edges
      .map((e, i) => ({ e, i }))
      .filter(({ e }) => e.head === n.id || e.tail === n.id)
      .slice(0, 30);
    const relsEl = document.getElementById("iRels");
    if (relsEl) {
      if (rels.length === 0) {
        relsEl.innerHTML = `<div class="ans-empty">No direct relations recorded for this node</div>`;
      } else {
        relsEl.innerHTML = rels
          .map(({ e }) => {
            const outgoing = e.head === n.id;
            const other = outgoing ? e.tail : e.head;
            return `<div class="rel-row">
              <span class="rel-dir">${outgoing ? "→" : "←"}</span>
              <span class="rel-tag">${e.relation.replace("_OF", "")}</span>
              <span class="rel-other" title="${other}">${shortLabel(other, 30)}</span>
            </div>`;
          })
          .join("");
      }
    }
    requestDraw();
  }

  // highlight from course cards
  window.highlightCourse = function (label) {
    const n = sim.nodes.find((x) => x.label === label);
    if (!n) return;
    highlight = { n };
    select(n);
    requestDraw();
    setTimeout(() => {
      highlight = null;
      requestDraw();
    }, 2600);
  };
}

/* ================= course cards ================= */
function initCourses() {
  const grid = document.getElementById("courseGrid");
  grid.innerHTML = G.courses
    .map((c) => {
      const m = G.courseMeta[c] || { topics: [], outcomes: [] };
      const color = G.courseColors[c] || "#4E79A7";
      const code = m.code || c.split(" ")[0];
      const topics = (m.topics || []).slice(0, 6);
      return `
      <article class="course-card" style="--c:${color}" data-course="${c}">
        <span class="cc-code">${code}</span>
        <h3>${c.replace(/^[A-Z]{2,4}\d{3}\s+/, "")}</h3>
        <div class="cc-meta">
          ${m.instructor ? `<span>👨‍🏫 ${m.instructor}</span>` : ""}
          ${m.credits ? `<span>🎓 ${m.credits} credits</span>` : ""}
        </div>
        <div class="cc-topics">
          ${topics.map((t) => `<span class="cc-topic-chip">${t}</span>`).join("")}
          ${(m.topics || []).length > 6 ? `<span class="cc-topic-chip">+${m.topics.length - 6} more</span>` : ""}
        </div>
        <div class="cc-more">${(m.outcomes || []).length} learning outcomes · click to locate in graph</div>
      </article>`;
    })
    .join("");
  grid.querySelectorAll(".course-card").forEach((card) => {
    card.addEventListener("click", () => {
      document.getElementById("graph").scrollIntoView({ behavior: "smooth" });
      if (window.highlightCourse) window.highlightCourse(card.dataset.course);
    });
  });
}

/* ================= topics ================= */
function initTopics() {
  const grid = document.getElementById("topicGrid");
  const search = document.getElementById("topicSearch");

  function render(filter = "") {
    const f = filter.trim().toLowerCase();
    const items = G.topicIndex.filter((t) => !f || t.topic.includes(f));
    grid.innerHTML = items
      .map(
        (t) => `
      <div class="topic-card">
        <div class="t-name">${t.topic}</div>
        <div class="t-courses">
          ${t.courses
            .map((c) => {
              const code = c.split(" ")[0];
              return `<span class="t-course" style="background:${G.courseColors[c] || "#4E79A7"}">${code}</span>`;
            })
            .join("")}
        </div>
      </div>`
      )
      .join("");
    const counter = document.getElementById("topicCount");
    if (counter) counter.textContent = items.length;
  }
  render();
  search.addEventListener("input", () => render(search.value));
}

/* ================= query console ================= */
function initConsole() {
  const courseSel = document.getElementById("qCourse");
  const topicSel = document.getElementById("qTopic");
  const typeSel = document.getElementById("qType");
  const codeEl = document.getElementById("qCode");
  const ansEl = document.getElementById("qAnswer");

  courseSel.innerHTML = G.courses
    .map((c) => `<option>${c}</option>`)
    .join("");
  topicSel.innerHTML = G.topicIndex
    .map((t) => `<option>${t.topic}</option>`)
    .join("");
  courseSel.value = "CS301 Machine Learning";
  topicSel.value = "sql";

  function run() {
    const course = courseSel.value;
    const topic = topicSel.value;
    const type = typeSel.value;
    const code = course.split(" ")[0];

    if (type === "prereq") {
      codeEl.textContent = `MATCH (p)-[:PREREQUISITE_OF|CO_REQUISITE_OF]->(c {name:"${shortLabel(course, 40)}"}) RETURN p`;
      const rels = G.edges.filter(
        (e) => e.relation.includes("REQUISITE") && e.tail === course
      );
      ansEl.innerHTML = rels.length
        ? rels.map((e) => `<span class="ans-item">📘 ${e.head}</span>`).join("")
        : `<span class="ans-empty">no prerequisites recorded</span>`;
    } else if (type === "covers") {
      codeEl.textContent = `MATCH (c)-[:COVERS_TOPIC]->(t {name:"${topic}"}) RETURN c`;
      const cs = G.edges
        .filter((e) => e.relation === "COVERS_TOPIC" && e.tail.toLowerCase() === topic.toLowerCase())
        .map((e) => e.head);
      const uniq = [...new Set(cs)];
      ansEl.innerHTML = uniq.length
        ? uniq.map((c) => `<span class="ans-item">📗 ${c}</span>`).join("")
        : `<span class="ans-empty">no course covers “${topic}”</span>`;
    } else if (type === "outcomes") {
      codeEl.textContent = `MATCH (c {name:"${shortLabel(course, 40)}"})-[:HAS_OUTCOME]->(o) RETURN o`;
      const m = G.courseMeta[course];
      const outs = (m && m.outcomes) || [];
      ansEl.innerHTML = outs.length
        ? outs.map((o) => `<span class="ans-item">🎯 ${shortLabel(o, 64)}</span>`).join("")
        : `<span class="ans-empty">no outcomes extracted</span>`;
    } else {
      codeEl.textContent = `MATCH (c {name:"${shortLabel(course, 40)}"})-[:TAUGHT_BY]->(i) RETURN i`;
      const m = G.courseMeta[course];
      ansEl.innerHTML = m && m.instructor
        ? `<span class="ans-item">👨‍🏫 ${m.instructor}</span>`
        : `<span class="ans-empty">no instructor extracted</span>`;
    }
  }
  document.getElementById("qRun").addEventListener("click", run);
  [courseSel, topicSel, typeSel].forEach((el) => el.addEventListener("change", run));
  run();
}

/* ================= benchmark ================= */
function initBenchmark() {
  const body = document.getElementById("benchBody");
  body.innerHTML = G.benchmark
    .map((b) => {
      const f1 = parseFloat(b.f1);
      const cls = f1 === 1 ? "f1-1" : f1 === 0 ? "f1-0" : "";
      return `<tr>
        <td>${b.query}</td>
        <td>${b.found}</td><td>${b.expected}</td>
        <td>${(+b.precision).toFixed(2)}</td>
        <td>${(+b.recall).toFixed(2)}</td>
        <td class="${cls}">${f1.toFixed(2)}</td>
      </tr>`;
    })
    .join("");
}

/* ================= counters ================= */
function initCounters() {
  document.querySelectorAll(".metric-value, .stat-n").forEach((el) => {
    const target = parseFloat(el.dataset.count || el.textContent);
    if (isNaN(target)) return;
    const t0 = performance.now(), dur = 900;
    (function tick(now) {
      const k = Math.min(1, (now - t0) / dur);
      const eased = 1 - Math.pow(1 - k, 3);
      el.textContent = Math.round(target * eased);
      if (k < 1) {
        requestAnimationFrame(tick);
      } else {
        el.textContent = target;
      }
    })(t0);
  });
}

/* ================= init ================= */
(async function init() {
  initCounters();
  try {
    G = await loadJSON("data/graph.json");
    if (G) {
      initHero();
      initMainGraph();
      initCourses();
      initTopics();
      initConsole();
      initBenchmark();
    }
  } catch (err) {
    console.error("Failed to initialize graph data:", err);
  }
})();
