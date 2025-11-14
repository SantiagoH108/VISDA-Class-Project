async function poll(){
  const r = await fetch('/status'); const j = await r.json();
  document.getElementById('fps').innerText = `FPS ${j.fps?.toFixed ? j.fps.toFixed(1) : j.fps}`;
  document.getElementById('wake').innerText = `Wakes ${j.wake_count}`;
  document.getElementById('muted').innerText = `Muted: ${j.muted ? 'yes' : 'no'}`;
  document.getElementById('spoken').innerText = j.last_spoken || '—';
  const tb = document.querySelector('#detTable tbody'); tb.innerHTML='';
  (j.dets || []).slice(0,8).forEach(d=>{
    const tr = document.createElement('tr');
    tr.innerHTML = `<td>${d[0]}</td><td>${(d[1]*100).toFixed(0)}%</td>`;
    tb.appendChild(tr);
  });
  document.getElementById('topdet').innerText = j.dets && j.dets[0]
    ? `Top: ${j.dets[0][0]} ${(j.dets[0][1]*100).toFixed(0)}%` : 'Top: --';
}
setInterval(poll, 600);
poll();

document.getElementById('btnSpeak').onclick = async ()=>{
  await fetch('/api/say',{method:'POST',headers:{'Content-Type':'application/json'},
    body: JSON.stringify({text: 'This is a VISDA test.'})});
};
document.getElementById('btnMute').onclick = async ()=>{
  await fetch('/api/mute',{method:'POST'});
  poll();
};
document.getElementById('btnWake').onclick = async ()=>{
  await fetch('/api/force_wake',{method:'POST'});
};
