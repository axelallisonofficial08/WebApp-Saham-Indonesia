let demoPortfolio = null;
let tradeStock = null;
let tradeSide = 'BUY';
const walletMoney = value => value == null || !Number.isFinite(Number(value)) ? '—' : 'Rp ' + new Intl.NumberFormat('id-ID').format(Math.round(value));
const staticPages = document.documentElement.dataset.staticMode === 'true';
const walletStorageKey = 'pasar-hari-ini-demo-wallet-v1';
function readBrowserWallet() {
  try {
    const value = JSON.parse(localStorage.getItem(walletStorageKey));
    if (value && Number.isFinite(value.cash) && value.positions && Array.isArray(value.trades)) return value;
  } catch (_) {}
  return { cash: 100_000_000, positions: {}, trades: [] };
}
function saveBrowserWallet(value) { localStorage.setItem(walletStorageKey, JSON.stringify(value)); }
function browserPortfolioSnapshot() {
  const state = readBrowserWallet();
  const positions = Object.entries(state.positions).map(([symbol, holding]) => {
    const quote = market?.stocks.find(item => item.symbol === symbol);
    const available = Boolean(quote?.is_available && quote.price != null);
    const price = available ? quote.price : null;
    return { symbol, name: quote?.name || symbol, lots: holding.lots, avg_price: holding.avg_price,
      price, market_value: available ? Math.round(price * holding.lots * 100) : null,
      unrealized: available ? Math.round((price - holding.avg_price) * holding.lots * 100) : null,
      is_available: available };
  });
  const markAvailable = positions.every(position => position.is_available);
  return { cash: state.cash, initial_cash: 100_000_000,
    market_value: markAvailable ? positions.reduce((sum, position) => sum + (position.market_value || 0), 0) : null,
    mark_available: markAvailable, positions, trades: state.trades.slice(0, 100), market_status: market?.status || 'unavailable' };
}
function executeBrowserTrade({ symbol, side, lots }) {
  symbol = String(symbol || '').toUpperCase(); side = String(side || '').toUpperCase(); lots = Number(lots);
  if (!Number.isInteger(lots) || lots < 1 || lots > 1_000_000) throw new Error('Jumlah lot harus bilangan bulat minimal 1.');
  const quote = market?.stocks.find(item => item.symbol === symbol);
  if (!quote?.is_available || !(quote.price > 0)) throw new Error('Kutipan harga nyata tidak tersedia.');
  if (side !== 'BUY' && side !== 'SELL') throw new Error('Pilih beli atau jual.');
  const state = readBrowserWallet(), holding = state.positions[symbol], price = Number(quote.price);
  const total = Math.round(price * lots * 100);
  if (side === 'BUY') {
    if (total > state.cash) throw new Error(`Saldo tidak cukup. Dibutuhkan ${walletMoney(total)}, saldo ${walletMoney(state.cash)}.`);
    const owned = holding?.lots || 0, newLots = owned + lots;
    state.positions[symbol] = { lots: newLots, avg_price: holding ? (owned * holding.avg_price + lots * price) / newLots : price };
    state.cash -= total;
  } else {
    if (!holding || lots > holding.lots) throw new Error(`Lot tidak cukup untuk dijual. Anda memiliki ${holding?.lots || 0} lot ${symbol}.`);
    state.cash += total;
    if (lots === holding.lots) delete state.positions[symbol]; else holding.lots -= lots;
  }
  const trade = { symbol, side, lots, price, total, created_at: new Date().toISOString() };
  state.trades.unshift(trade); state.trades = state.trades.slice(0, 100); saveBrowserWallet(state);
  return { trade, portfolio: browserPortfolioSnapshot() };
}
function executeBrowserSellAll() {
  const state = readBrowserWallet(), holdings = Object.entries(state.positions);
  if (!holdings.length) throw new Error('Tidak ada saham di dompet untuk dijual.');
  const sales = holdings.map(([symbol, holding]) => {
    const quote = market?.stocks.find(item => item.symbol === symbol);
    if (!quote?.is_available || !(quote.price > 0)) throw new Error(`Kutipan nyata untuk ${symbol} tidak tersedia.`);
    const price = Number(quote.price);
    return { symbol, lots: holding.lots, price, total: Math.round(price * holding.lots * 100) };
  });
  const createdAt = new Date().toISOString();
  state.cash += sales.reduce((sum, sale) => sum + sale.total, 0);
  state.trades = [...sales.map(sale => ({ ...sale, side: 'SELL', created_at: createdAt })), ...state.trades].slice(0, 100);
  state.positions = {}; saveBrowserWallet(state);
  return { proceeds: sales.reduce((sum, sale) => sum + sale.total, 0), portfolio: browserPortfolioSnapshot() };
}

function renderWallet(data) {
  demoPortfolio = data;
  document.querySelector('#wallet-cash').textContent = walletMoney(data.cash);
  document.querySelector('#wallet-invested').textContent = walletMoney(data.market_value);
  document.querySelector('#wallet-total').textContent = data.market_value == null ? '—' : walletMoney(data.cash + data.market_value);
  document.querySelector('#wallet-position-count').textContent = `${data.positions.length} saham di portofolio`;
  document.querySelector('#holding-rows').innerHTML = data.positions.length ? data.positions.map(p => `<tr><td><b>${p.symbol}</b><small class="portfolio-name">${p.name}</small></td><td>${p.lots}</td><td>${walletMoney(p.avg_price)}</td><td>${walletMoney(p.price)}</td><td>${walletMoney(p.market_value)}<small class="${p.unrealized == null ? '' : p.unrealized >= 0 ? 'positive' : 'negative'} portfolio-pnl">${p.unrealized == null ? '—' : `${p.unrealized >= 0 ? '+' : ''}${walletMoney(p.unrealized)}`}</small></td><td><button class="small-sell" data-sell-holding="${p.symbol}">Jual</button></td></tr>`).join('') : '<tr><td colspan="6" class="empty">Dompet masih kosong. Klik saham lalu pilih Beli saham untuk memulai.</td></tr>';
  const sellAll = document.querySelector('#sell-all-holdings');
  sellAll.disabled = !data.positions.length || !data.positions.every(p => p.is_available);
  sellAll.title = !data.positions.length ? 'Belum ada saham untuk dijual.' : sellAll.disabled ? 'Semua posisi harus memiliki kutipan nyata agar dapat dijual sekaligus.' : '';
  document.querySelector('#trade-rows').innerHTML = data.trades.length ? data.trades.map(t => `<tr><td>${new Intl.DateTimeFormat('id-ID', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Jakarta' }).format(new Date(t.created_at))}</td><td><b>${t.symbol}</b></td><td class="${t.side === 'BUY' ? 'positive' : 'negative'}">${t.side === 'BUY' ? 'BELI' : 'JUAL'}</td><td>${t.lots}</td><td>${walletMoney(t.price)}</td></tr>`).join('') : '<tr><td colspan="5" class="empty">Belum ada transaksi.</td></tr>';
  updateTradePreview();
}

async function loadWallet() {
  if (staticPages) {
    if (market) renderWallet(browserPortfolioSnapshot());
    return;
  }
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
  const total = tradeStock.price * 100 * lots;
  document.querySelector('#trade-estimate').textContent = walletMoney(total);
  document.querySelector('#trade-current-price').textContent = `${walletMoney(tradeStock.price)} per saham · harga kutipan`;
  const holding = demoPortfolio?.positions.find(p => p.symbol === tradeStock.symbol);
  const unavailable = !tradeStock.is_available;
  document.querySelectorAll('[data-trade-side]').forEach(button => {
    button.disabled = unavailable || (button.dataset.tradeSide === 'SELL' && (!holding || !holding.is_available)) || (button.dataset.tradeSide === 'BUY' && total > (demoPortfolio?.cash || 0));
  });
  const message = document.querySelector('#trade-message');
  if (unavailable) message.textContent = 'Kutipan harga nyata tidak tersedia; transaksi dinonaktifkan.';
  else if (tradeSide === 'BUY' && total > (demoPortfolio?.cash || 0)) message.textContent = 'Saldo tunai tidak cukup untuk jumlah lot ini.';
  else if (tradeSide === 'SELL' && (!holding || !holding.is_available)) message.textContent = 'Posisi atau kutipan nyata untuk saham ini tidak tersedia.';
  else message.textContent = '';
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
document.querySelector('#max-buy-lots').addEventListener('click', () => {
  if (!tradeStock) return;
  showTradeForm('BUY');
  const cash = demoPortfolio?.cash || 0;
  const lots = tradeStock.price > 0 ? Math.floor(cash / (tradeStock.price * 100)) : 0;
  document.querySelector('#trade-lots').value = lots;
  document.querySelector('#trade-message').textContent = lots ? `Saldo dipakai semaksimal mungkin; sisa tunai sekitar ${walletMoney(cash - lots * tradeStock.price * 100)}.` : 'Saldo tunai belum cukup untuk membeli 1 lot.';
  updateTradePreview();
  document.querySelector('#trade-message').textContent = lots ? `Maksimal ${lots} lot; sisa tunai sekitar ${walletMoney(cash - lots * tradeStock.price * 100)}.` : 'Saldo tunai belum cukup untuk membeli 1 lot.';
});
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
    let data;
    if (staticPages) {
      data = executeBrowserTrade({ symbol: tradeStock.symbol, side: tradeSide, lots: document.querySelector('#trade-lots').value });
    } else {
      const response = await fetch('/api/trade', {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ symbol: tradeStock.symbol, side: tradeSide, lots: document.querySelector('#trade-lots').value })
      });
      data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Transaksi gagal.');
    }
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

document.querySelector('#sell-all-holdings').addEventListener('click', async event => {
  const button = event.currentTarget;
  if (!demoPortfolio?.positions.length || button.disabled) return;
  const summary = demoPortfolio.positions.map(p => `${p.symbol} ${p.lots} lot`).join(', ');
  if (!window.confirm(`Jual semua posisi berikut dengan kutipan nyata yang tersedia?\n\n${summary}`)) return;
  button.disabled = true;
  try {
    let data;
    if (staticPages) {
      data = executeBrowserSellAll();
    } else {
      const response = await fetch('/api/trade/sell-all', { method: 'POST' });
      data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Gagal menjual semua posisi.');
    }
    renderWallet(data.portfolio);
    window.alert(`Semua posisi berhasil dijual. Dana masuk: ${walletMoney(data.result?.proceeds ?? data.proceeds)}.`);
  } catch (error) {
    window.alert(error.message);
  } finally {
    await loadWallet();
  }
});

window.addEventListener('market:updated', loadWallet);
