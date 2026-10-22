const sampleChecks = [
  {method:'GET',path:'/health',status:200,detail:'Health · response schema valid'},
  {method:'POST',path:'/orders',status:201,detail:'Create order · response schema valid'},
  {method:'GET',path:'/orders/{orderId}',status:200,detail:'Read order · response schema valid'}
];
function renderSample(){
  const rows=document.getElementById('checks');
  rows.replaceChildren(...sampleChecks.map((item)=>{
    const row=document.createElement('article');row.className='check';
    row.innerHTML=`<span class="check-icon">✓</span><div><h3>${item.method} ${item.path}</h3><p>${item.detail} · expected ${item.status}, received ${item.status}</p></div><span class="status">PASS</span>`;
    return row;
  }));
  document.getElementById('passed').textContent=String(sampleChecks.length);
  document.getElementById('failed').textContent='0';
}
document.getElementById('rerun').addEventListener('click',renderSample);
renderSample();
