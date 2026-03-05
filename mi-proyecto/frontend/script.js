/* ════════════════════════════════════════════
   AUTH — Login / Registro (frontend simulado)
   En producción: enviar al backend con fetch()
   y validar/hashear contraseñas en servidor.
   ════════════════════════════════════════════ */

// "Base de datos" simulada en memoria (en producción: backend + BD)
let usersDB = JSON.parse(sessionStorage.getItem('nxt_users') || '[]');
let currentUser = null;

function saveUsersDB() {
  // ⚠️ AVISO: sessionStorage es solo para demo.
  // NUNCA guardes contraseñas en texto plano en producción.
  // El backend debe hashear con bcrypt antes de persistir.
  sessionStorage.setItem('nxt_users', JSON.stringify(usersDB));
}

/* ── Tab switcher ── */
function switchTab(tab) {
  document.getElementById('loginForm').classList.toggle('hidden', tab !== 'login');
  document.getElementById('registerForm').classList.toggle('hidden', tab !== 'register');
  document.getElementById('tabLogin').classList.toggle('active', tab === 'login');
  document.getElementById('tabRegister').classList.toggle('active', tab === 'register');
  clearAuthErrors();
}

function clearAuthErrors() {
  ['loginEmail','loginPass','regUser','regEmail','regPass','regPassConfirm'].forEach(id => {
    const el = document.getElementById(id);
    const err = document.getElementById(id + '-err');
    if (el) el.classList.remove('error-field');
    if (err) err.classList.remove('visible');
  });
  ['loginError','registerError'].forEach(id => {
    const el = document.getElementById(id);
    if (el) { el.textContent = ''; el.classList.remove('visible'); }
  });
}

function showAuthError(bannerId, msg) {
  const el = document.getElementById(bannerId);
  if (!el) return;
  el.textContent = '⚠ ' + sanitizeInput(msg, 120);
  el.classList.add('visible');
}

function setAuthFieldError(id, show) {
  const input = document.getElementById(id);
  const err   = document.getElementById(id + '-err');
  if (input) input.classList.toggle('error-field', show);
  if (err)   err.classList.toggle('visible', show);
}

/* ── Mostrar/ocultar contraseña ── */
function togglePass(inputId, btn) {
  const input = document.getElementById(inputId);
  if (!input) return;
  const isText = input.type === 'text';
  input.type = isText ? 'password' : 'text';
  btn.textContent = isText ? '👁' : '🙈';
}

/* ── Indicador de fuerza de contraseña ── */
function checkPassStrength(val) {
  const bar   = document.getElementById('passStrengthBar');
  const label = document.getElementById('passStrengthLabel');
  if (!bar || !label) return;

  let score = 0;
  if (val.length >= 8)  score++;
  if (val.length >= 12) score++;
  if (/[A-Z]/.test(val)) score++;
  if (/[0-9]/.test(val)) score++;
  if (/[^A-Za-z0-9]/.test(val)) score++;

  const levels = [
    { pct: '20%', color: '#ff4060', text: '// MUY DÉBIL',  textColor: '#ff4060' },
    { pct: '40%', color: '#ff8c00', text: '// DÉBIL',      textColor: '#ff8c00' },
    { pct: '60%', color: '#ffd700', text: '// MEDIA',      textColor: '#ffd700' },
    { pct: '80%', color: '#00b8ff', text: '// FUERTE',     textColor: '#00b8ff' },
    { pct: '100%',color: '#00ffc8', text: '// MUY FUERTE', textColor: '#00ffc8' },
  ];
  const lvl = levels[Math.max(0, score - 1)] || levels[0];
  if (val.length === 0) {
    bar.style.width = '0'; label.textContent = '';
  } else {
    bar.style.width = lvl.pct;
    bar.style.background = lvl.color;
    label.textContent = lvl.text;
    label.style.color = lvl.textColor;
  }
}

/* ── Validaciones ── */
function validateUsername(u) {
  return /^[a-zA-Z0-9_]{3,30}$/.test(u);
}

/* ── LOGIN ── */
function handleLogin(e) {
  e.preventDefault();
  clearAuthErrors();

  const email = sanitizeInput(document.getElementById('loginEmail').value, 254).toLowerCase();
  const pass  = document.getElementById('loginPass').value; // no sanitizamos pass (puede tener chars especiales)

  let valid = true;
  if (!validateEmail(email)) { setAuthFieldError('loginEmail', true); valid = false; }
  if (pass.length < 8)       { setAuthFieldError('loginPass', true);  valid = false; }
  if (!valid) return;

  // Buscar usuario (en producción: POST /api/login con hash)
  const user = usersDB.find(u => u.email === email);
  if (!user || user.password !== pass) {
    // Mensaje genérico para no revelar si el email existe (evita enumeración)
    showAuthError('loginError', 'Credenciales incorrectas');
    return;
  }

  loginSuccess(user);
}

/* ── REGISTER ── */
function handleRegister(e) {
  e.preventDefault();
  clearAuthErrors();

  const username = sanitizeInput(document.getElementById('regUser').value, 30);
  const email    = sanitizeInput(document.getElementById('regEmail').value, 254).toLowerCase();
  const pass     = document.getElementById('regPass').value;
  const confirm  = document.getElementById('regPassConfirm').value;

  let valid = true;
  if (!validateUsername(username)) { setAuthFieldError('regUser', true);        valid = false; }
  if (!validateEmail(email))       { setAuthFieldError('regEmail', true);       valid = false; }
  if (pass.length < 8)             { setAuthFieldError('regPass', true);        valid = false; }
  if (pass !== confirm)            { setAuthFieldError('regPassConfirm', true); valid = false; }
  if (!valid) return;

  // Comprobar duplicados
  if (usersDB.find(u => u.email === email)) {
    showAuthError('registerError', 'Ese email ya está registrado');
    return;
  }
  if (usersDB.find(u => u.username.toLowerCase() === username.toLowerCase())) {
    showAuthError('registerError', 'Ese nombre de usuario ya existe');
    return;
  }

  // Crear usuario (en producción: POST /api/register, el backend hashea la pass)
  const newUser = { id: Date.now(), username, email, password: pass, createdAt: new Date().toISOString() };
  usersDB.push(newUser);
  saveUsersDB();

  loginSuccess(newUser);
}

/* ── Éxito de autenticación ── */
function loginSuccess(user) {
  currentUser = user;
  document.getElementById('headerUsername').textContent = user.username;
  const screen = document.getElementById('authScreen');
  screen.classList.add('hide');
  setTimeout(() => screen.style.display = 'none', 500);
  showToast(`✓ Bienvenido, ${escapeHtml(user.username)}`);
}

/* ── LOGOUT ── */
function handleLogout() {
  currentUser = null;
  cart = [];
  updateCartUI();
  renderProducts();
  // Cierra todos los modales
  document.getElementById('cartOverlay').classList.remove('open');
  document.getElementById('checkoutOverlay').classList.remove('open');
  // Vuelve a mostrar la pantalla de auth
  const screen = document.getElementById('authScreen');
  screen.style.display = 'flex';
  void screen.offsetWidth;
  screen.classList.remove('hide');
  // Reset formularios
  document.getElementById('loginForm').reset();
  document.getElementById('registerForm').reset();
  checkPassStrength('');
  switchTab('login');
}

/* ════════════════════════════════════════════
   SECURITY HELPERS — sanitización en frontend
   (la validación real ocurre en el backend)
   ════════════════════════════════════════════ */

/**
 * Escapa caracteres HTML para prevenir XSS.
 * NOTA: Esto es solo una medida de defensa en profundidad;
 * el backend SIEMPRE debe sanitizar también.
 */
function escapeHtml(str) {
  if (typeof str !== 'string') return '';
  return str
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#x27;')
    .replace(/\//g, '&#x2F;');
}

/**
 * Sanitiza texto de entrada: elimina scripts, tags HTML
 * y limita longitud. Solo texto plano.
 */
function sanitizeInput(val, maxLen = 200) {
  if (typeof val !== 'string') return '';
  return val
    .replace(/<[^>]*>/g, '')          // Elimina tags HTML
    .replace(/javascript:/gi, '')      // Elimina js: protocol
    .replace(/on\w+\s*=/gi, '')        // Elimina event handlers
    .trim()
    .substring(0, maxLen);
}

/** Solo dígitos para campos numéricos */
function onlyDigits(val) {
  return val.replace(/\D/g, '');
}

/* ════════════════════════════════════════════
   PRODUCTS DATA
   ════════════════════════════════════════════ */
const products = [
  { id: 1, name: 'Intel Core i9-14900K', category: 'cpu', price: 589.99, oldPrice: 649.99, desc: '24 núcleos (8P+16E), hasta 6.0 GHz, socket LGA1700', icon: '🔲', badge: 'sale', stock: 8 },
  { id: 2, name: 'AMD Ryzen 9 7950X', category: 'cpu', price: 549.99, desc: '16 núcleos / 32 hilos, hasta 5.7 GHz, AM5', icon: '🔲', badge: 'new', stock: 5 },
  { id: 3, name: 'RTX 4090 24GB GDDR6X', category: 'gpu', price: 1799.99, oldPrice: 1999.99, desc: 'DLSS 3, Ray Tracing, 16384 CUDA cores', icon: '🖥️', badge: 'sale', stock: 3 },
  { id: 4, name: 'RX 7900 XTX 24GB', category: 'gpu', price: 999.99, desc: 'RDNA3, DisplayPort 2.1, 96 CUs', icon: '🖥️', badge: null, stock: 6 },
  { id: 5, name: 'Corsair 32GB DDR5-6000', category: 'ram', price: 129.99, desc: 'Dual channel, XMP 3.0, CL30', icon: '💾', badge: null, stock: 20 },
  { id: 6, name: 'G.Skill Trident Z5 64GB', category: 'ram', price: 249.99, desc: 'DDR5-6400, RGB, XMP 3.0, CL32', icon: '💾', badge: 'new', stock: 12 },
  { id: 7, name: 'Samsung 990 Pro 2TB', category: 'storage', price: 189.99, oldPrice: 219.99, desc: 'NVMe PCIe 4.0, 7450/6900 MB/s', icon: '💿', badge: 'sale', stock: 15 },
  { id: 8, name: 'WD Black SN850X 4TB', category: 'storage', price: 299.99, desc: 'PCIe 4.0, 7300 MB/s lectura, PS5 compatible', icon: '💿', badge: null, stock: 9 },
  { id: 9, name: 'Logitech G Pro X Superlight 2', category: 'perifericos', price: 159.99, desc: 'Inalámbrico, 32K DPI, 60h batería, 60g', icon: '🖱️', badge: 'new', stock: 25 },
  { id: 10, name: 'Keychron Q3 Max', category: 'perifericos', price: 199.99, desc: 'TKL, QMK/VIA, Gateron G Pro, aluminio', icon: '⌨️', badge: null, stock: 18 },
  { id: 11, name: 'AMD Ryzen 5 7600X', category: 'cpu', price: 239.99, desc: '6 núcleos / 12 hilos, hasta 5.3 GHz, AM5', icon: '🔲', badge: null, stock: 30 },
  { id: 12, name: 'ASUS ROG Swift 4K 27"', category: 'perifericos', price: 699.99, oldPrice: 799.99, desc: '4K OLED, 240Hz, 0.03ms, HDMI 2.1', icon: '🖥️', badge: 'sale', stock: 7 },
];

/* ════════════════════════════════════════════
   CART STATE
   ════════════════════════════════════════════ */
let cart = [];
let currentFilter = 'all';
let currentSearch = '';

/* ════════════════════════════════════════════
   RENDER PRODUCTS
   ════════════════════════════════════════════ */
function renderProducts() {
  const grid = document.getElementById('productsGrid');
  const countEl = document.getElementById('productCount');

  let filtered = products.filter(p => {
    const matchCat = currentFilter === 'all' || p.category === currentFilter;
    // Sanitizamos la búsqueda antes de usarla
    const safeSearch = sanitizeInput(currentSearch, 100).toLowerCase();
    const matchSearch = !safeSearch ||
      p.name.toLowerCase().includes(safeSearch) ||
      p.desc.toLowerCase().includes(safeSearch) ||
      p.category.toLowerCase().includes(safeSearch);
    return matchCat && matchSearch;
  });

  countEl.textContent = `${filtered.length} producto${filtered.length !== 1 ? 's' : ''}`;

  if (filtered.length === 0) {
    grid.innerHTML = `
      <div class="no-results">
        <span class="no-icon">📦</span>
        // No se encontraron productos para tu búsqueda
      </div>`;
    return;
  }

  grid.innerHTML = filtered.map((p, i) => {
    const inCart = cart.find(c => c.id === p.id);
    // Usamos escapeHtml para todos los datos renderizados
    return `
    <article class="product-card" style="animation-delay: ${i * 0.05}s">
      <div class="card-glow"></div>
      ${p.badge ? `<span class="card-badge ${p.badge === 'new' ? 'new-badge' : 'sale-badge'}">${escapeHtml(p.badge === 'new' ? 'NUEVO' : 'OFERTA')}</span>` : ''}
      <div class="card-img">${escapeHtml(p.icon)}</div>
      <div class="card-body">
        <div class="card-category">// ${escapeHtml(p.category.toUpperCase())}</div>
        <div class="card-name">${escapeHtml(p.name)}</div>
        <div class="card-desc">${escapeHtml(p.desc)}</div>
        <div class="card-footer">
          <div>
            ${p.oldPrice ? `<span class="card-price-old">${formatPrice(p.oldPrice)}</span>` : ''}
            <span class="card-price">${formatPrice(p.price)}</span>
            ${p.stock <= 5 ? `<span class="stock-low">⚠ Solo ${p.stock} en stock</span>` : ''}
          </div>
          <button class="add-btn ${inCart ? 'added' : ''}"
            onclick="addToCart(${p.id})"
            ${inCart ? 'disabled' : ''}
            aria-label="Añadir ${escapeHtml(p.name)} al carrito">
            ${inCart ? '✓ EN CARRITO' : '+ AÑADIR'}
          </button>
        </div>
      </div>
    </article>`;
  }).join('');
}

function formatPrice(n) {
  return new Intl.NumberFormat('es-ES', { style: 'currency', currency: 'EUR' }).format(n);
}

/* ════════════════════════════════════════════
   FILTERS & SEARCH
   ════════════════════════════════════════════ */
function filterCategory(cat, btn) {
  currentFilter = cat;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  if (btn) btn.classList.add('active');
  renderProducts();
}

function handleSearch() {
  const raw = document.getElementById('searchInput').value;
  // Sanitizamos la búsqueda (limitamos longitud, quitamos tags)
  currentSearch = sanitizeInput(raw, 100);
  renderProducts();
}

/* ════════════════════════════════════════════
   CART LOGIC
   ════════════════════════════════════════════ */
function addToCart(productId) {
  // Validamos que el id sea un número entero válido
  const id = parseInt(productId, 10);
  if (!Number.isInteger(id) || id <= 0) return;

  const product = products.find(p => p.id === id);
  if (!product) return;

  const existing = cart.find(c => c.id === id);
  if (existing) {
    showToast('Ya está en tu carrito', 'error');
    return;
  }

  cart.push({ ...product, qty: 1 });
  updateCartUI();
  showToast(`✓ ${product.name} añadido`);
  renderProducts(); // Actualiza el botón
}

function removeFromCart(productId) {
  const id = parseInt(productId, 10);
  cart = cart.filter(c => c.id !== id);
  updateCartUI();
  renderProducts();
}

function changeQty(productId, delta) {
  const id = parseInt(productId, 10);
  const item = cart.find(c => c.id === id);
  if (!item) return;
  item.qty = Math.max(1, Math.min(99, item.qty + delta));
  updateCartUI();
}

function getCartTotal() {
  return cart.reduce((acc, item) => acc + item.price * item.qty, 0);
}

function getCartItemCount() {
  return cart.reduce((acc, item) => acc + item.qty, 0);
}

function updateCartUI() {
  const count = getCartItemCount();
  const countEl = document.getElementById('cartCount');
  countEl.textContent = count;
  countEl.classList.remove('bump');
  void countEl.offsetWidth;
  if (count > 0) countEl.classList.add('bump');

  renderCartItems();
}

function renderCartItems() {
  const container = document.getElementById('cartItems');
  const summary = document.getElementById('cartSummary');

  if (cart.length === 0) {
    container.innerHTML = `
      <div class="cart-empty">
        <span class="empty-icon">🛒</span>
        // CARRITO VACÍO<br>Añade componentes para empezar
      </div>`;
    summary.style.display = 'none';
    return;
  }

  container.innerHTML = cart.map(item => `
    <div class="cart-item">
      <div class="cart-item-icon">${escapeHtml(item.icon)}</div>
      <div class="cart-item-info">
        <div class="cart-item-name">${escapeHtml(item.name)}</div>
        <div class="cart-item-price">${formatPrice(item.price * item.qty)}</div>
        <div class="cart-item-controls">
          <button class="qty-btn" onclick="changeQty(${item.id}, -1)" aria-label="Reducir cantidad">−</button>
          <span class="qty-display">${item.qty}</span>
          <button class="qty-btn" onclick="changeQty(${item.id}, 1)" aria-label="Aumentar cantidad">+</button>
          <button class="remove-btn" onclick="removeFromCart(${item.id})" aria-label="Eliminar ${escapeHtml(item.name)}">🗑</button>
        </div>
      </div>
    </div>
  `).join('');

  const shipping = getCartTotal() >= 500 ? 0 : 9.99;
  const taxes = getCartTotal() * 0.21;

  document.getElementById('summaryRows').innerHTML = `
    <div class="summary-row"><span>Subtotal</span><span>${formatPrice(getCartTotal())}</span></div>
    <div class="summary-row"><span>Envío</span><span>${shipping === 0 ? '🆓 GRATIS' : formatPrice(shipping)}</span></div>
    <div class="summary-row"><span>IVA (21%)</span><span>${formatPrice(taxes)}</span></div>
    <div class="summary-row total"><span>TOTAL</span><span>${formatPrice(getCartTotal() + shipping + taxes)}</span></div>
  `;

  summary.style.display = 'block';
}

/* ════════════════════════════════════════════
   CART TOGGLE
   ════════════════════════════════════════════ */
function toggleCart() {
  const overlay = document.getElementById('cartOverlay');
  overlay.classList.toggle('open');
  if (overlay.classList.contains('open')) renderCartItems();
}

function handleOverlayClick(e) {
  if (e.target === document.getElementById('cartOverlay')) toggleCart();
}

/* ════════════════════════════════════════════
   CHECKOUT VALIDATION — Defensa en frontend
   (el backend DEBE validar igualmente)
   ════════════════════════════════════════════ */

function formatCard(input) {
  let val = onlyDigits(input.value).substring(0, 16);
  input.value = val.replace(/(.{4})/g, '$1 ').trim();
}

function formatExpiry(input) {
  let val = onlyDigits(input.value).substring(0, 4);
  if (val.length >= 2) val = val.substring(0, 2) + '/' + val.substring(2);
  input.value = val;
}

function validateEmail(email) {
  // Validación básica de formato; el backend hace la definitiva
  return /^[^\s@]{1,64}@[^\s@]{1,255}\.[^\s@]{2,}$/.test(email);
}

function validateZip(zip) {
  return /^\d{5}$/.test(zip);
}

function validateCard(num) {
  return onlyDigits(num).length === 16;
}

function validateExpiry(val) {
  if (!/^\d{2}\/\d{2}$/.test(val)) return false;
  const [mm, yy] = val.split('/').map(Number);
  if (mm < 1 || mm > 12) return false;
  const now = new Date();
  const yr = now.getFullYear() % 100;
  const mo = now.getMonth() + 1;
  return yy > yr || (yy === yr && mm >= mo);
}

function validateCvv(val) {
  return /^\d{3,4}$/.test(val);
}

function setFieldError(id, show) {
  const input = document.getElementById(id);
  const err = document.getElementById(id + '-err');
  if (input) input.classList.toggle('error-field', show);
  if (err) err.classList.toggle('visible', show);
}

function openCheckout() {
  if (cart.length === 0) return;
  toggleCart();
  // Renderizamos el resumen en el checkout
  const shipping = getCartTotal() >= 500 ? 0 : 9.99;
  const taxes = getCartTotal() * 0.21;
  const total = getCartTotal() + shipping + taxes;
  document.getElementById('checkoutOrderSummary').innerHTML = `
    <div style="border:1px solid var(--border); padding:1rem; margin-bottom:1rem; background:var(--surface2)">
      <div class="form-section-title" style="margin-bottom:0.75rem">// Resumen (${getCartItemCount()} artículos)</div>
      ${cart.map(i => `<div class="summary-row"><span>${escapeHtml(i.name)} ×${i.qty}</span><span>${formatPrice(i.price * i.qty)}</span></div>`).join('')}
      <div class="summary-row total" style="margin-top:0.5rem"><span>TOTAL</span><span>${formatPrice(total)}</span></div>
    </div>
  `;
  document.getElementById('checkoutOverlay').classList.add('open');
}

function closeCheckout() {
  document.getElementById('checkoutOverlay').classList.remove('open');
}

function handleCheckout(e) {
  e.preventDefault();

  // Recoger y sanitizar valores
  const fname    = sanitizeInput(document.getElementById('fname').value, 100);
  const lname    = sanitizeInput(document.getElementById('lname').value, 100);
  const email    = sanitizeInput(document.getElementById('email').value, 254);
  const address  = sanitizeInput(document.getElementById('address').value, 300);
  const city     = sanitizeInput(document.getElementById('city').value, 100);
  const zip      = onlyDigits(document.getElementById('zip').value).substring(0, 5);
  const cardnum  = onlyDigits(document.getElementById('cardnum').value).substring(0, 16);
  const expiry   = document.getElementById('expiry').value.trim();
  const cvv      = onlyDigits(document.getElementById('cvv').value).substring(0, 4);

  // Validar todos los campos
  let valid = true;

  const checks = [
    ['fname',   !fname,              'Campo requerido'],
    ['lname',   !lname,              'Campo requerido'],
    ['email',   !validateEmail(email), 'Email no válido'],
    ['address', !address,            'Campo requerido'],
    ['city',    !city,               'Campo requerido'],
    ['zip',     !validateZip(zip),   'CP inválido (5 dígitos)'],
    ['cardnum', !validateCard(cardnum), 'Número de tarjeta no válido'],
    ['expiry',  !validateExpiry(expiry), 'Fecha no válida'],
    ['cvv',     !validateCvv(cvv),   'CVV inválido'],
  ];

  checks.forEach(([id, hasError]) => {
    setFieldError(id, hasError);
    if (hasError) valid = false;
  });

  if (!valid) {
    showToast('Corrige los campos marcados', 'error');
    return;
  }

  // ⚠️ AVISO DE SEGURIDAD (para el hackathon):
  // En producción real, NUNCA envíes datos de tarjeta al backend propio.
  // Usar pasarelas seguras (Stripe, Redsys) que manejan el tokenizado.
  // Aquí simulamos el pedido sin enviar datos sensibles.

  closeCheckout();
  confirmOrder();
}

function confirmOrder() {
  const orderId = 'NXT-' + Date.now().toString(36).toUpperCase() + '-' + Math.random().toString(36).substring(2,6).toUpperCase();
  document.getElementById('orderId').textContent = `PEDIDO #${orderId}`;
  document.getElementById('successOverlay').classList.add('open');
}

function closeSuccess() {
  document.getElementById('successOverlay').classList.remove('open');
  cart = [];
  updateCartUI();
  renderProducts();
  // Limpiamos el formulario
  document.getElementById('checkoutForm').reset();
}

/* ════════════════════════════════════════════
   TOAST
   ════════════════════════════════════════════ */
function showToast(msg, type = 'success') {
  const container = document.getElementById('toastContainer');
  const toast = document.createElement('div');
  toast.className = `toast ${type === 'error' ? 'error' : ''}`;
  // Sanitizamos el mensaje del toast también
  toast.textContent = sanitizeInput(msg, 100);
  container.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

/* ════════════════════════════════════════════
   KEYBOARD NAVIGATION
   ════════════════════════════════════════════ */
document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    document.getElementById('cartOverlay').classList.remove('open');
    document.getElementById('checkoutOverlay').classList.remove('open');
  }
});

// Protege el carrito: solo accesible si hay sesión activa
const _toggleCart = toggleCart;
toggleCart = function() {
  if (!currentUser) { showToast('Inicia sesión para usar el carrito', 'error'); return; }
  _toggleCart();
};

/* ════════════════════════════════════════════
   INIT
   ════════════════════════════════════════════ */
renderProducts();
updateCartUI();