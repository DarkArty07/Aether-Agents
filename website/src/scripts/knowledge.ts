import { gsap } from 'gsap';
import { MotionPathPlugin } from 'gsap/MotionPathPlugin';

/** An authored illustration, never a connection to the project's real graph. */
export function initKnowledgeGraphs() {
  const figures = document.querySelectorAll<HTMLElement>('[data-knowledge-graph]');
  if (!figures.length) return;
  gsap.registerPlugin(MotionPathPlugin);
  figures.forEach(initGraph);
}

function initGraph(figure: HTMLElement) {
  if (figure.dataset.ready) return;
  const stage = figure.querySelector<HTMLElement>('.knowledge-stage');
  const panel = figure.querySelector<HTMLElement>('.knowledge-detail');
  const title = panel?.querySelector<HTMLElement>('[data-knowledge-title]');
  const description = panel?.querySelector<HTMLElement>('[data-knowledge-description]');
  const reset = figure.querySelector<HTMLButtonElement>('[data-knowledge-reset]');
  const spotlight = figure.querySelector<HTMLElement>('.knowledge-spotlight');
  const packets = [...figure.querySelectorAll<SVGGElement>('[data-knowledge-packet]')];
  const edges = [...figure.querySelectorAll<SVGPathElement>('[data-illuminate]')];
  const buttons = [...figure.querySelectorAll<HTMLButtonElement>('[data-knowledge-node]')];
  if (!stage || !panel || !title || !description || !reset || !spotlight || packets.length !== 2) return;

  const reduce = matchMedia('(prefers-reduced-motion: reduce)');
  const fine = matchMedia('(hover: hover) and (pointer: fine)');
  let visible = false;
  let selected = '';
  let preview = '';
  const controller = new AbortController();
  const opts = { signal: controller.signal };
  const sequence = gsap.timeline({ paused: true, repeat: -1, repeatDelay: 1.2 });
  const halo = figure.querySelector('[data-core-halo]');

  gsap.set(packets, { opacity: 0 });
  edges.forEach((edge, i) => {
    const d = edge.getAttribute('d');
    if (!d) return;
    const t = i * 4.4;
    const light = figure.querySelector(`[data-node-light="${edge.dataset.illuminate}"]`);
    sequence.call(() => { figure.dataset.traversal = `${edge.dataset.illuminate}:in`; }, [], t)
      .to(edge, { opacity: .95, duration: .5 }, t)
      .set(packets[0], { opacity: 1 }, t)
      .fromTo(packets[0], { motionPath: { path:d, start:1, end:1 } }, {
        motionPath: { path:d, start:1, end:0 }, duration: 1.7,
        ease:'power1.inOut', immediateRender:false,
      }, t)
      .to(packets[0], { opacity:0, duration:.2 }, t+1.7)
      .to(halo, { attr: { r:43, opacity:.7 }, duration:.55, ease:'sine.out' }, t+1.6)
      .to(halo, { attr: { r:29, opacity:.35 }, duration:1.1 }, t+2.15)
      .call(() => { figure.dataset.traversal = `${edge.dataset.illuminate}:out`; }, [], t+2.1)
      .set(packets[1], { opacity:1 }, t+2.1)
      .fromTo(packets[1], { motionPath: { path:d, start:0, end:0 } }, {
        motionPath: { path:d, start:0, end:1 }, duration:1.6,
        ease:'power1.inOut', immediateRender:false,
      }, t+2.1)
      .to(packets[1], { opacity:0, duration:.2 }, t+3.7)
      .to(light, { opacity:1, duration:.25 }, t+3.45)
      .to(light, { opacity:.45, duration:.65 }, t+3.7)
      .to(edge, { opacity:0, duration:.6 }, t+3.8);
  });

  gsap.set(spotlight, { xPercent:-50, yPercent:-50, opacity:0 });
  const moveX = gsap.quickTo(spotlight, 'x', { duration:.55, ease:'power2.out' });
  const moveY = gsap.quickTo(spotlight, 'y', { duration:.55, ease:'power2.out' });
  function allowed() {
    return visible && !document.hidden && !reduce.matches && document.documentElement.dataset.motion === 'running';
  }
  function sync() {
    const running = allowed() && !selected;
    sequence.paused(!running);
    figure.dataset.animating = String(running);
    if (!allowed()) {
      moveX.tween.pause(); moveY.tween.pause();
      gsap.killTweensOf(spotlight, 'opacity');
      gsap.set(spotlight, { opacity:0 });
    }
  }
  function highlight() {
    const active = preview || selected;
    figure.dataset.selected = active;
    figure.querySelectorAll<HTMLElement | SVGElement>('[data-cluster],[data-relationship]').forEach(el => {
      el.classList.toggle('is-selected', (el.dataset.cluster || el.dataset.relationship) === active);
    });
    buttons.forEach(button => {
      button.classList.toggle('is-highlighted', button.dataset.knowledgeNode === active);
      button.setAttribute('aria-pressed', String(button.dataset.knowledgeNode === selected));
    });
  }
  const choose = (button?: HTMLButtonElement) => {
    selected = button?.dataset.knowledgeNode || '';
    preview = '';
    title.textContent = button?.dataset.title || panel.dataset.defaultTitle || '';
    description.textContent = button?.dataset.description || panel.dataset.defaultDescription || '';
    reset.hidden = !selected;
    highlight(); sync();
  };
  buttons.forEach(button => {
    button.disabled = false;
    button.addEventListener('click', () => choose(selected === button.dataset.knowledgeNode ? undefined : button), opts);
    button.addEventListener('pointerenter', () => { if (fine.matches) { preview = button.dataset.knowledgeNode || ''; highlight(); } }, opts);
    button.addEventListener('pointerleave', () => { preview=''; highlight(); }, opts);
    button.addEventListener('focus', () => { preview=button.dataset.knowledgeNode || ''; highlight(); }, opts);
    button.addEventListener('blur', () => { preview=''; highlight(); }, opts);
  });
  reset.addEventListener('click', () => {
    const previous = buttons.find(b => b.dataset.knowledgeNode === selected);
    choose(); previous?.focus(); preview=''; highlight();
  }, opts);
  figure.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      const previous = buttons.find(b => b.dataset.knowledgeNode === selected);
      choose(); previous?.focus(); preview=''; highlight();
    }
  }, opts);
  stage.addEventListener('pointermove', event => {
    if (!allowed() || !fine.matches || event.pointerType === 'touch') return;
    const bounds = stage.getBoundingClientRect();
    moveX(event.clientX - bounds.left); moveY(event.clientY - bounds.top);
    gsap.to(spotlight, { opacity:1, duration:.35, overwrite:'auto' });
  }, opts);
  stage.addEventListener('pointerleave', () => {
    if (allowed()) gsap.to(spotlight, { opacity:0, duration:.4, overwrite:'auto' });
    else gsap.set(spotlight, { opacity:0 });
  }, opts);

  const visibility = new IntersectionObserver(entries => {
    visible = entries[0].isIntersecting;
    sync();
  }, { threshold:.12 });
  visibility.observe(stage);
  const motion = new MutationObserver(sync);
  motion.observe(document.documentElement, { attributes:true, attributeFilter:['data-motion'] });
  reduce.addEventListener('change', sync, opts);
  document.addEventListener('visibilitychange', sync, opts);
  figure.dataset.ready = 'true';
  choose();
  // Ordinary navigation tears down our timelines and observers, including bfcache.
  window.addEventListener('pagehide', () => {
    sequence.kill(); moveX.tween.kill(); moveY.tween.kill();
    gsap.killTweensOf(spotlight); visibility.disconnect(); motion.disconnect(); controller.abort();
    delete figure.dataset.ready;
  }, { once:true });
}

// Keep this listener after the initial pageshow, so back/forward cache restoration
// rebuilds the timelines and controls torn down at pagehide without duplicate handlers.
window.addEventListener('pageshow', event => { if (event.persisted) initKnowledgeGraphs(); });
