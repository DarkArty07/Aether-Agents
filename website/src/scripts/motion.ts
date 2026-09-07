/** Decorative, deterministic illustrations only. No network or runtime data. */
export function initSite() {
  const root = document.documentElement;
  const toggle = document.querySelector<HTMLButtonElement>('[data-motion-toggle]');
  const preference = window.matchMedia('(prefers-reduced-motion: reduce)');
  let paused = preference.matches;
  try { paused ||= localStorage.getItem('aether-motion') === 'paused'; } catch { /* Private browsing: keep the system preference. */ }
  const scenes = [...document.querySelectorAll<HTMLElement>('[data-scene]')];
  const visible = new Set<HTMLElement>();
  const times = new Map<HTMLElement, number>();
  let raf = 0;
  let last = 0;

  function updateControl() {
    root.dataset.motion = paused ? 'paused' : 'running';
    if (!toggle) return;
    toggle.hidden = false;
    toggle.setAttribute('aria-pressed', String(paused));
    const label = (paused ? toggle.dataset.play : toggle.dataset.pause) || '';
    toggle.setAttribute('aria-label', label);
    const text = toggle.querySelector('[data-motion-label]');
    const icon = toggle.querySelector('.motion-icon');
    if (text) text.textContent = label;
    if (icon) icon.textContent = paused ? '▷' : 'Ⅱ';
  }
  function schedule() {
    if (!raf && !paused && !document.hidden && visible.size) {
      last = performance.now(); raf = requestAnimationFrame(tick);
    }
  }
  function tick(now: number) {
    raf = 0;
    if (paused || document.hidden || !visible.size) return;
    const dt = Math.min((now - last) / 1000, .1); last = now;
    for (const scene of visible) {
      const time = (times.get(scene) || 0) + dt;
      times.set(scene, time);
      draw(scene, time);
    }
    raf = requestAnimationFrame(tick);
  }
  const observer = new IntersectionObserver(entries => {
    for (const entry of entries) {
      const el = entry.target as HTMLElement;
      if (entry.isIntersecting) visible.add(el); else visible.delete(el);
    }
    schedule();
  }, { threshold: .08 });
  scenes.forEach(scene => { observer.observe(scene); draw(scene, 0); });
  toggle?.addEventListener('click', () => {
    paused = !paused; updateControl();
    try { localStorage.setItem('aether-motion', paused ? 'paused' : 'running'); } catch { /* No persistence available. */ }
    schedule();
  });
  preference.addEventListener('change', e => { paused = e.matches; updateControl(); schedule(); });
  document.addEventListener('visibilitychange', schedule);
  updateControl();

  // Preserve the reader's section when moving between languages.
  document.querySelectorAll<HTMLAnchorElement>('[data-language]').forEach(link => {
    link.addEventListener('click', () => { if (location.hash) link.hash = location.hash; });
  });
  document.querySelectorAll<HTMLDetailsElement>('.mobile-nav').forEach(menu => {
    menu.querySelectorAll('a').forEach(a => a.addEventListener('click', () => { menu.open = false; }));
    document.addEventListener('keydown', e => {
      if (e.key === 'Escape' && menu.open) { menu.open = false; menu.querySelector('summary')?.focus(); }
    });
    document.addEventListener('click', e => { if (!menu.contains(e.target as Node)) menu.open = false; });
  });
}

const pathCache = new WeakMap<SVGPathElement, number>();
function point(scene: HTMLElement, selector: string, progress: number) {
  const path = scene.querySelector<SVGPathElement>(selector);
  if (!path) return null;
  let length = pathCache.get(path);
  if (length === undefined) { length = path.getTotalLength(); pathCache.set(path, length); }
  return path.getPointAtLength(Math.max(0, Math.min(1, progress)) * length);
}
function putPacket(scene: HTMLElement, index: number, path: string, progress: number) {
  const packet = scene.querySelector<SVGGElement>(`[data-packet='${index}']`);
  const p = point(scene, path, progress);
  if (packet && p) { packet.setAttribute('opacity','1'); packet.setAttribute('transform',`translate(${p.x} ${p.y})`); }
}

function draw(scene: HTMLElement, time: number) {
  if (scene.dataset.scene === 'astrolabe') {
    scene.querySelectorAll<SVGGElement>('[data-rotate]').forEach(g => {
      g.setAttribute('transform', `rotate(${time * Number(g.dataset.rotate)} 280 280)`);
    });
  } else if (scene.dataset.scene === 'team') {
    const t = time % 28;
    scene.querySelectorAll('[data-packet]').forEach(p => p.setAttribute('opacity','0'));
    let label = 0; let active = 'owner';
    if (t < 3) { putPacket(scene,0,'#team-owner',t/3); active='morfeo'; }
    else if (t < 6) { putPacket(scene,0,'#team-morfeo',(t-3)/3); active='supervisor'; label=1; }
    else if (t < 9) { ['a','b','c'].forEach((id,i) => putPacket(scene,i,`#team-${id}`,(t-6)/3)); active='a,b,c'; label=2; }
    else if (t < 11) { ['a','b','c'].forEach((id,i) => putPacket(scene,i,`#team-${id}`,1)); active='a,b,c'; label=2; }
    else if (t < 14) { ['a','b','c'].forEach((id,i) => putPacket(scene,i,`#team-${id}`,1-(t-11)/3)); active='supervisor'; label=3; }
    else if (t < 16) { putPacket(scene,0,'#team-b',(t-14)/2); active='b'; label=4; }
    else if (t < 18) { putPacket(scene,0,'#team-b',1-(t-16)/2); active='supervisor'; label=3; }
    else if (t < 20) { putPacket(scene,0,'#team-morfeo',1-(t-18)/2); active='morfeo'; label=5; }
    else if (t < 22) { putPacket(scene,0,'#team-morfeo',0); active='morfeo'; label=5; }
    else if (t < 24) { putPacket(scene,0,'#team-morfeo',(t-22)/2); active='supervisor'; label=6; }
    else if (t < 26) { putPacket(scene,0,'#team-morfeo',1-(t-24)/2); active='morfeo'; label=6; }
    else { putPacket(scene,0,'#team-owner',1-(t-26)/2); active='owner'; label=6; }
    scene.querySelectorAll<SVGGElement>('[data-node]').forEach(n => n.classList.toggle('is-active', active.split(',').includes(n.dataset.node || '')));
    if (scene.dataset.phase !== String(label)) {
      scene.dataset.phase = String(label);
      const labels = JSON.parse(scene.dataset.labels || '[]');
      const caption = scene.querySelector('[data-flow-label]');
      if (caption) caption.textContent = labels[label] || '';
    }
  } else if (scene.dataset.scene === 'process') {
    const sequence = [0,1,2,3,4,3,4,5,5];
    const t = time % 27; const slot = Math.floor(t/3);
    const from = sequence[slot]; const to = sequence[Math.min(slot+1,8)];
    const f = Math.min((t % 3)/2.2,1);
    scene.querySelectorAll<HTMLElement>('[data-stage]').forEach(el => el.classList.toggle('is-active', Number(el.dataset.stage) === from));
    scene.dataset.stage = String(from);
    const p = from === 4 && to === 3 ? point(scene,'#process-return',f) : point(scene,'#process-path',(from+(to-from)*f)/5);
    const packet = scene.querySelector<SVGGElement>('[data-process-packet]');
    if (packet && p) packet.setAttribute('transform',`translate(${p.x} ${p.y})`);
  }
}
