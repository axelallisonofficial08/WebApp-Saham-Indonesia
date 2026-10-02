let demoPortfolio = null;
let tradeStock = null;
let tradeSide = 'BUY';
const walletMoney = value => value == null || !Number.isFinite(Number(value)) ? '—' : 'Rp ' + new Intl.NumberFormat('id-ID').format(Math.round(value));

function renderWallet(data) {
  demoPortfolio = data;
  document.querySelector('#wallet-cash').textContent = walletMoney(data.cash);
  document.querySelector('#wallet-invested').textContent = walletMoney(data.market_value);
  document.querySelector('#wallet-total').textContent = data.market_value == null ? '—' : walletMoney(data.cash + data.market_value);
  document.querySelector('#wallet-position-count').textContent = `${data.positions.length} saham di portofolio`;
  document.querySelector('#holding-rows').innerHTML = data.positions.length ? data.positions.map(p => `<tr><td><b>${p.symbol}</b><small class="portfolio-name">${p.name}</small></td><td>${p.lots}</td><td>${walletMoney(p.avg_price)}</td><td>${walletMoney(p.price)}</td><td>${walletMoney(p.market_value)}<small class="${p.unrealized == null ? '' : p.unrealized >= 0 ? 'positive' : 'negative'} portfolio-pnl">${p.unrealized == null ? '—' : `${p.unrealized >= 0 ? '+' : ''}${walletMoney(p.unrealized)}`}</small></td><td><button class="small-sell" data-sell-holding="${p.symbol}">Jual</button></td></tr>`).join('') : '<tr><td colspan="6" class="empty">Dompet masih kosong. Klik saham lalu pilih Beli saham untuk memulai.</td></tr>';
  document.querySelector('#trade-rows').innerHTML = data.trades.length ? data.trades.map(t => `<tr><td>${new Intl.DateTimeFormat('id-ID', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Jakarta' }).format(new Date(t.created_at))}</td><td><b>${t.symbol}</b></td><td class="${t.side === 'BUY' ? 'positive' : 'negative'}">${t.side === 'BUY' ? 'BELI' : 'JUAL'}</td><td>${t.lots}</td><td>${walletMoney(t.price)}</td></tr>`).join('') : '<tr><td colspan="5" class="empty">Belum ada transaksi.</td></tr>';
  updateTradePreview();
}

async function loadWallet() {
  try {
    const response = await fetch('/api/portfolio');
    if (!response.ok) throw new Error('Dompet belum dapat dimuat.');
    renderWallet(await response.json());
  } catch (_) {
    document.querySelector('#holding-rows').innerHTML = '<tr><td colspan="6" class="empty">Dompet belum dapat dimuat. Coba muat ulang.</td></tr>';
  }
}

function updateTradePreview() {
  if (!tradeStock) return;
  const lots = Math.max(0, Number(document.querySelector('#trade-lots').value) || 0);
  document.querySelector('#trade-estimate').textContent = walletMoney(tradeStock.price * 100 * lots);
  document.querySelector('#trade-current-price').textContent = `${walletMoney(tradeStock.price)} per saham · harga kutipan`;
  const holding = demoPortfolio?.positions.find(p => p.symbol === tradeStock.symbol);
  const unavailable = !tradeStock.is_available;
  document.querySelectorAll('[data-trade-side]').forEach(button => {
    button.disabled = unavailable || (button.dataset.tradeSide === 'SELL' && !holding);
  });
  document.querySelector('#trade-message').textContent = unavailable ? 'Kutipan harga nyata tidak tersedia; transaksi dinonaktifkan.' : '';
}

function showTradeForm(side) {
  if (!tradeStock) return;
  tradeSide = side;
  const form = document.querySelector('#trade-form');
  form.hidden = false;
  document.querySelector('#trade-form-heading').textContent = `${side === 'BUY' ? 'Beli' : 'Jual'} ${tradeStock.symbol}`;
  document.querySelector('#trade-lots').value = 1;
  document.querySelector('#trade-message').textContent = '';
  document.querySelector('.confirm-trade').textContent = side === 'BUY' ? 'Konfirmasi beli' : 'Konfirmasi jual';
  updateTradePreview();
  form.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
}

document.querySelector('#stock-rows').addEventListener('click', event => {
  const button = event.target.closest('[data-stock]');
  if (!button) return;
  tradeStock = market?.stocks.find(stock => stock.symbol === button.dataset.stock) || null;
  document.querySelector('#trade-form').hidden = true;
  updateTradePreview();
});
document.querySelectorAll('[data-trade-side]').forEach(button => button.addEventListener('click', () => showTradeForm(button.dataset.tradeSide)));
document.querySelector('#trade-lots').addEventListener('input', updateTradePreview);
document.querySelector('#holding-rows').addEventListener('click', event => {
  const button = event.target.closest('[data-sell-holding]');
  if (!button) return;
  const stock = market?.stocks.find(item => item.symbol === button.dataset.sellHolding);
  if (!stock) return;
  tradeStock = stock;
  renderDetail(stock.symbol);
  showTradeForm('SELL');
});
document.querySelector('#trade-form').addEventListener('submit', async event => {
  event.preventDefault();
  if (!tradeStock) return;
  const submit = event.currentTarget.querySelector('.confirm-trade');
  const message = document.querySelector('#trade-message');
  submit.disabled = true;
  message.textContent = 'Memproses transaksi…';
  try {
    const response = await fetch('/api/trade', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ symbol: tradeStock.symbol, side: tradeSide, lots: document.querySelector('#trade-lots').value })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Transaksi gagal.');
    renderWallet(data.portfolio);
    message.textContent = `Berhasil ${tradeSide === 'BUY' ? 'membeli' : 'menjual'} ${data.trade.lots} lot ${data.trade.symbol} pada ${walletMoney(data.trade.price)}.`;
    document.querySelector('#trade-lots').value = 1;
    updateTradePreview();
  } catch (error) {
    message.textContent = error.message;
  } finally {
    submit.disabled = false;
  }
});

window.addEventListener('market:updated', loadWallet);
