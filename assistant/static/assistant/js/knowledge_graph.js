/**
 * Idle-state "visual knowledge graph" animation — a pulsing core with
 * orbiting nodes and connecting rings, echoing the reference UI's centre
 * radar visual. Runs on a <canvas> and pauses whenever the knowledge
 * panel (image lookups) is shown on top of it.
 */
(function () {
  const canvas = document.getElementById("mm-graph-canvas");
  if (!canvas) return;
  const ctx = canvas.getContext("2d");

  let width, height, cx, cy;
  let nodes = [];
  let frame = 0;
  let running = true;

  const NODE_COUNT = 22;
  const CYAN = "53, 230, 224";

  function resize() {
    const stage = canvas.parentElement;
    width = canvas.width = stage.clientWidth;
    height = canvas.height = stage.clientHeight;
    cx = width / 2;
    cy = height / 2;
  }

  function initNodes() {
    nodes = [];
    const baseRadius = Math.min(width, height) * 0.32;
    for (let i = 0; i < NODE_COUNT; i++) {
      const angle = (Math.PI * 2 * i) / NODE_COUNT;
      nodes.push({
        angle,
        radiusOffset: Math.random() * 30 - 15,
        baseRadius: baseRadius + (Math.random() * 40 - 20),
        speed: 0.0025 + Math.random() * 0.003,
        size: 1.5 + Math.random() * 2,
      });
    }
  }

  function draw() {
    if (!running) {
      requestAnimationFrame(draw);
      return;
    }
    frame++;
    ctx.clearRect(0, 0, width, height);

    // outer static rings
    [0.34, 0.24].forEach((frac, i) => {
      ctx.beginPath();
      ctx.arc(cx, cy, Math.min(width, height) * frac, 0, Math.PI * 2);
      ctx.strokeStyle = `rgba(${CYAN}, ${i === 0 ? 0.18 : 0.12})`;
      ctx.lineWidth = 1;
      ctx.stroke();
    });

    // pulsing core
    const pulse = 18 + Math.sin(frame * 0.05) * 6;
    const grad = ctx.createRadialGradient(cx, cy, 0, cx, cy, pulse * 2.2);
    grad.addColorStop(0, `rgba(${CYAN}, 0.9)`);
    grad.addColorStop(1, `rgba(${CYAN}, 0)`);
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.arc(cx, cy, pulse * 2.2, 0, Math.PI * 2);
    ctx.fill();

    ctx.beginPath();
    ctx.arc(cx, cy, 10, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(${CYAN}, 1)`;
    ctx.shadowColor = `rgba(${CYAN}, 0.9)`;
    ctx.shadowBlur = 20;
    ctx.fill();
    ctx.shadowBlur = 0;

    // orbiting nodes + connecting lines back to core
    nodes.forEach((node) => {
      node.angle += node.speed;
      const r = node.baseRadius + Math.sin(frame * 0.02 + node.radiusOffset) * 8;
      const x = cx + Math.cos(node.angle) * r;
      const y = cy + Math.sin(node.angle) * r * 0.55; // slight ellipse for a "radar" feel

      ctx.beginPath();
      ctx.moveTo(cx, cy);
      ctx.lineTo(x, y);
      ctx.strokeStyle = `rgba(${CYAN}, 0.06)`;
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.beginPath();
      ctx.arc(x, y, node.size, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(${CYAN}, 0.85)`;
      ctx.fill();
    });

    requestAnimationFrame(draw);
  }

  function pause() { running = false; }
  function resume() { running = true; }

  window.addEventListener("resize", () => {
    resize();
    initNodes();
  });

  resize();
  initNodes();
  requestAnimationFrame(draw);

  window.MindMeshGraph = { pause, resume };
})();
