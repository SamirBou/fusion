document.addEventListener('DOMContentLoaded', function () {
  function findGenButtons() {
    // Find tab elements rendered by Dash for generation-tabs
    return document.querySelectorAll('#generation-tabs [role="tab"], #generation-tabs button');
  }

  function normalizeTabLabelToGen(label) {
    if (!label) return 'all';
    label = label.trim().toLowerCase();
    if (label === 'all') return 'all';
    const m = label.match(/gen\s*(\d+)/i) || label.match(/^(\d+)$/);
    if (m) return 'gen' + m[1];
    return 'all';
  }

  function applyFilter(gen) {
    // gen: 'all' or 'gen1', 'gen2', etc. Convert to numeric token like '1'
    let want = null;
    if (!gen || gen === 'all') {
      want = null;
    } else if (gen.startsWith('gen')) {
      want = gen.replace('gen', '');
    } else {
      want = gen;
    }

    const grid = document.getElementById('pokemon-sprite-grid');
    if (!grid) return;
    const items = grid.querySelectorAll('[data-gen], .fusion-gen-1, .fusion-gen-2, .fusion-gen-3, .fusion-gen-4, .fusion-gen-5, .fusion-gen-6, .fusion-gen-7');
    items.forEach(item => {
      // prefer explicit data-gen attribute
      const g = item.getAttribute && item.getAttribute('data-gen');
      if (!want) {
        item.style.display = '';
        return;
      }
      if (g && g === String(want)) {
        item.style.display = '';
        return;
      }
      // fallback: check class name like 'fusion-gen-3'
      if (item.classList && item.classList.contains('fusion-gen-' + String(want))) {
        item.style.display = '';
        return;
      }
      item.style.display = 'none';
    });
  }

  function attach() {
    const tabs = findGenButtons();
    if (!tabs || tabs.length === 0) return;
    tabs.forEach(t => {
      if (t._fusion_filter_attached) return;
      t.addEventListener('click', function (ev) {
        const label = t.textContent || t.innerText || '';
        const v = normalizeTabLabelToGen(label);
        applyFilter(v);
      });
      t._fusion_filter_attached = true;
    });
  }

  // initial attach and apply active tab if present
  attach();
  // apply filter for active tab on load
  const active = Array.from(findGenButtons()).find(x => x.getAttribute('aria-selected') === 'true' || x.classList.contains('selected') || x.classList.contains('active'));
  if (active) {
    applyFilter(normalizeTabLabelToGen(active.textContent));
  }

  const obs = new MutationObserver((mutations) => {
    attach();
  });
  obs.observe(document.body, { childList: true, subtree: true });

  // also expose a global method to apply filter programmatically
  window.applyFusionGenFilter = applyFilter;
});
