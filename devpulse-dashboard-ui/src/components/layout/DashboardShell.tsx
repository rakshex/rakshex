'use client';

import { ReactNode, useEffect, useRef, useState } from 'react';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

export default function DashboardShell({children}:{children:ReactNode}){
  const [open,setOpen]=useState(false);
  const [collapsed,setCollapsed]=useState(false);
  const drawer=useRef<HTMLDivElement>(null);
  const trigger=useRef<HTMLButtonElement>(null);
  useEffect(()=>{
    if(!open)return;
    const previous=document.body.style.overflow;document.body.style.overflow='hidden';
    const focusable=()=>Array.from(drawer.current?.querySelectorAll<HTMLElement>('a[href],button:not([disabled])')||[]).filter(el=>el.tabIndex>=0&&el.getClientRects().length>0);
    focusable()[0]?.focus();
    function keyboard(event:KeyboardEvent){
      if(event.key==='Escape'){event.preventDefault();setOpen(false);return;}
      if(event.key==='Tab'){
        const list=focusable();const first=list[0];const last=list[list.length-1];
        if(event.shiftKey&&document.activeElement===first){event.preventDefault();last?.focus();}
        else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first?.focus();}
      }
    }
    const media=window.matchMedia('(min-width: 768px)');const resized=()=>{if(media.matches)setOpen(false);};
    media.addEventListener('change',resized);document.addEventListener('keydown',keyboard);
    return()=>{document.body.style.overflow=previous;document.removeEventListener('keydown',keyboard);media.removeEventListener('change',resized);trigger.current?.focus();};
  },[open]);
  return <div className="min-h-screen bg-zinc-950">
    <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-4 focus:top-4 focus:z-[60] focus:rounded focus:bg-blue-600 focus:p-3">Skip to content</a>
    <div ref={drawer} id="primary-navigation" role={open?'dialog':undefined} aria-modal={open?true:undefined} aria-label={open?'Navigation menu':undefined} className={open?'fixed inset-0 z-50 md:static':'hidden md:block'}>
      {open&&<><button tabIndex={-1} aria-label="Close navigation backdrop" onClick={()=>setOpen(false)} className="fixed inset-0 bg-black/70 md:hidden"/>
        <button aria-label="Close navigation" className="fixed left-[248px] top-3 z-50 rounded-lg bg-zinc-800 px-3 py-2 text-white focus-visible:outline-2 focus-visible:outline-blue-300 md:hidden" onClick={()=>setOpen(false)}>✕</button></>}
      <Sidebar collapsed={open?false:collapsed} onCollapse={()=>setCollapsed(value=>!value)} onNavigate={()=>setOpen(false)}/>
    </div>
    <div inert={open} className={`min-w-0 transition-[padding] duration-200 motion-reduce:transition-none ${collapsed?'md:pl-[68px]':'md:pl-[240px]'}`}>
      <Topbar menuButton={<button ref={trigger} aria-label="Open navigation" aria-expanded={open} aria-controls="primary-navigation" className="rounded-lg border border-zinc-700 p-2 text-zinc-100 focus-visible:outline-2 focus-visible:outline-blue-300 md:hidden" onClick={()=>setOpen(true)}>☰</button>}/>
      <main id="main-content" tabIndex={-1} className="mx-auto min-w-0 max-w-[1400px] px-4 py-5 outline-none sm:px-6 lg:px-8">{children}</main>
    </div>
  </div>;
}
