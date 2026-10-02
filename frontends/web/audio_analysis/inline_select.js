// SPDX-FileCopyrightText: 2026 OpenRoadCode contributors
// SPDX-License-Identifier: MIT
// Page-rendered choices avoid Chromium native popup windows under X11 reparenting.
(()=>{
  const root=window.OpenRoadCodeWeb=window.OpenRoadCodeWeb||{};
  root.inlineSelect=select=>{
    if(!select||select.dataset.inlineSelect)return;
    select.dataset.inlineSelect='true';select.hidden=true;
    const button=document.createElement('button'),menu=document.createElement('div');
    button.type='button';button.id=`${select.id}-button`;
    button.setAttribute('aria-haspopup','listbox');button.setAttribute('aria-expanded','false');
    button.setAttribute('aria-label',select.getAttribute('aria-label')||'Visualization preset');
    menu.id=`${select.id}-choices`;menu.setAttribute('role','listbox');menu.hidden=true;
    menu.style.cssText='position:fixed;z-index:10000;overflow:auto;max-height:240px;padding:4px;border:1px solid #627384;border-radius:8px;background:#14212d;color:#edf2f5;box-shadow:0 4px 18px #0008';
    button.setAttribute('aria-controls',menu.id);select.after(button);document.body.append(menu);
    function close(){menu.hidden=true;button.setAttribute('aria-expanded','false')}
    let optionSignature=null;
    function sync(){
      button.textContent=select.selectedOptions[0]?.textContent||'Choose input';
      button.disabled=select.disabled;
      const signature=[...select.options].map(option=>[option.value,option.textContent]);
      const encoded=JSON.stringify(signature);
      if(encoded===optionSignature){
        for(const choice of menu.children)choice.setAttribute('aria-selected',String(choice.dataset.value===select.value));
        if(button.disabled)close();
        return;
      }
      optionSignature=encoded;
      menu.replaceChildren();
      for(const option of select.options){
        const choice=document.createElement('button');choice.type='button';choice.textContent=option.textContent;
        choice.dataset.value=option.value;choice.setAttribute('role','option');
        choice.setAttribute('aria-selected',String(option.selected));
        choice.style.cssText='display:block;width:100%;min-height:40px;text-align:left;background:transparent;color:inherit;border:0;padding:8px';
        choice.onclick=()=>{select.value=option.value;select.dispatchEvent(new Event('change',{bubbles:true}));sync();close();button.focus()};
        choice.onkeydown=event=>{
          const choices=[...menu.children],index=choices.indexOf(choice);
          if(event.key==='Escape'){event.preventDefault();close();button.focus()}
          if(event.key==='ArrowDown'||event.key==='ArrowUp'){
            event.preventDefault();choices[(index+(event.key==='ArrowDown'?1:-1)+choices.length)%choices.length].focus();
          }
        };
        menu.append(choice);
      }
    }
    function open(){
      sync();if(button.disabled)return;
      (document.fullscreenElement||document.body).append(menu);
      const rect=button.getBoundingClientRect(),width=Math.min(Math.max(rect.width,220),window.innerWidth-16);
      const below=window.innerHeight-rect.bottom-8,above=rect.top-8;
      menu.style.width=`${width}px`;menu.style.left=`${Math.max(8,Math.min(rect.left,window.innerWidth-width-8))}px`;
      const height=Math.min(240,Math.max(below,above));menu.style.maxHeight=`${height}px`;
      menu.style.top=below>=above?`${rect.bottom}px`:'auto';
      menu.style.bottom=below>=above?'auto':`${window.innerHeight-rect.top}px`;
      menu.hidden=false;button.setAttribute('aria-expanded','true');
      (menu.querySelector('[aria-selected="true"]')||menu.firstElementChild)?.focus();
    }
    button.onclick=()=>menu.hidden?open():close();
    button.onkeydown=event=>{if(event.key==='ArrowDown'){event.preventDefault();open()}};
    document.addEventListener('pointerdown',event=>{if(!menu.contains(event.target)&&event.target!==button)close()});
    document.addEventListener('keydown',event=>{if(event.key==='Escape')close()});
    window.addEventListener('resize',close);
    select.addEventListener('change',sync);
    new MutationObserver(sync).observe(select,{childList:true,subtree:true,attributes:true});sync();
  };
})();
