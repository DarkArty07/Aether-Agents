import { gsap } from 'gsap';

/** Decorative depth only; respect the same pause contract as the diagrams. */
export function initAtmospheres() {
  document.querySelectorAll<HTMLElement>('[data-atmosphere]').forEach(scene => {
    if (scene.dataset.atmosphereReady) return;
    const art = scene.querySelector<HTMLElement>('[data-atmosphere-art]');
    const lights = [...scene.querySelectorAll<HTMLElement>('[data-ether-light]')];
    const motes = [...scene.querySelectorAll<HTMLElement>('[data-ether-mote]')];
    if (!art || lights.length < 2) return;
    const reduce = matchMedia('(prefers-reduced-motion: reduce)');
    const fine = matchMedia('(hover: hover) and (pointer: fine) and (min-width: 801px)');
    const events = new AbortController();
    let inView = false;
    const cycle = gsap.timeline({ paused:true, repeat:-1, yoyo:true, defaults:{ ease:'sine.inOut' } });
    cycle.to(lights[0], { x:22, y:-12, opacity:.65, duration:12 }, 0)
      .to(lights[1], { x:-20, y:15, opacity:.42, duration:15 }, 0);
    motes.forEach((mote,i) => {
      cycle.to(mote, { y:-(9+i%3*4), opacity:.25+i%3*.16, duration:8+i%5 }, i*.18);
    });
    const x=gsap.quickTo(art,'x',{duration:1.15,ease:'power2.out'});
    const y=gsap.quickTo(art,'y',{duration:1.15,ease:'power2.out'});
    const allowed=()=>inView && !document.hidden && !reduce.matches && document.documentElement.dataset.motion==='running';
    function sync() {
      const running=allowed();
      cycle.paused(!running);
      scene.dataset.atmosphereRunning=String(running);
      if (!running) { x.tween.pause(); y.tween.pause(); }
      if (reduce.matches || !fine.matches) gsap.set(art,{x:0,y:0});
    }
    scene.addEventListener('pointermove',event=>{
      if (!allowed() || !fine.matches || event.pointerType==='touch') return;
      const r=scene.getBoundingClientRect();
      x((event.clientX-r.left-r.width/2)/r.width*12);
      y((event.clientY-r.top-r.height/2)/r.height*9);
    },{signal:events.signal,passive:true});
    scene.addEventListener('pointerleave',()=>{
      if (allowed() && fine.matches) { x(0); y(0); }
    },{signal:events.signal});
    const visibility=new IntersectionObserver(entries=>{
      inView=entries[0].isIntersecting; sync();
    },{threshold:.04});
    visibility.observe(scene);
    const controls=new MutationObserver(sync);
    controls.observe(document.documentElement,{attributes:true,attributeFilter:['data-motion']});
    reduce.addEventListener('change',sync,{signal:events.signal});
    fine.addEventListener('change',sync,{signal:events.signal});
    document.addEventListener('visibilitychange',sync,{signal:events.signal});
    scene.dataset.atmosphereReady='true'; sync();
    window.addEventListener('pagehide',()=>{
      cycle.kill(); x.tween.kill(); y.tween.kill();
      gsap.set(art,{clearProps:'transform'});
      visibility.disconnect(); controls.disconnect(); events.abort();
      delete scene.dataset.atmosphereReady;
    },{once:true});
  });
}

window.addEventListener('pageshow',event=>{if(event.persisted) initAtmospheres();});
