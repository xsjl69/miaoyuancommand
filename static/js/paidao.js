/* 首日排刀页交互：用户跳转高亮、轴图放大、浮动导航、提示弹框 */
function jumpToUser(id) {
    if (!id) return;
    document.querySelectorAll('.highlight-row').forEach(function (e) { e.classList.remove('highlight-row'); });
    var row = document.getElementById(id);
    if (!row) return;
    row.classList.add('highlight-row');
    var next = row.nextElementSibling;
    if (next && next.tagName === 'TR') next.classList.add('highlight-row');
    row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    setTimeout(function () {
        row.classList.remove('highlight-row');
        if (next && next.tagName === 'TR') next.classList.remove('highlight-row');
    }, 2500);
}

function openImgModal(src) {
    document.getElementById('imgModalImg').src = src;
    document.getElementById('imgModal').classList.add('active');
}
function closeImgModal() { document.getElementById('imgModal').classList.remove('active'); }

/* ===== 出刀完成标记 ===== */
var _knifeTarget = null;

function onKnifeCellClick(cell) {
    var uk = cell.getAttribute('data-uk');
    var field = cell.getAttribute('data-field');
    if (!uk || !field) return;
    var done = cell.classList.contains('done');
    _knifeTarget = { cell: cell, uk: uk, field: field, next: done ? 0 : 1 };
    document.getElementById('kcTitle').textContent = done ? '取消完成标记' : '确认出刀';
    document.getElementById('kcText').textContent = done
        ? '取消该刀的已完成标记？'
        : '确认该刀已完成出刀？确认后该格显示为灰色。';
    document.getElementById('kcOk').textContent = done ? '取消标记' : '确认出刀';
    document.getElementById('knifeConfirm').classList.add('active');
}

function closeKnifeConfirm() {
    document.getElementById('knifeConfirm').classList.remove('active');
    _knifeTarget = null;
}

function confirmKnifeDone() {
    if (!_knifeTarget) return;
    var t = _knifeTarget;
    var btn = document.getElementById('kcOk');
    btn.disabled = true;
    fetch('/api/user_knife/' + t.uk + '/done', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field: t.field, done: t.next })
    }).then(function (r) { return r.json(); }).then(function (d) {
        btn.disabled = false;
        if (d.error) return;
        t.cell.classList.toggle('done', !!d.done);
        closeKnifeConfirm();
    }).catch(function () { btn.disabled = false; });
}

document.addEventListener('DOMContentLoaded', function () {
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { closeImgModal(); closeKnifeConfirm(); }
        if (e.key === 'Enter' && document.getElementById('knifeConfirm').classList.contains('active')) {
            e.preventDefault();
            confirmKnifeDone();
        }
    });

    /* 排刀表单元格点击 → 弹出确认出刀 */
    document.addEventListener('click', function (e) {
        var cell = e.target.closest ? e.target.closest('.knife-cell[data-uk]') : null;
        if (cell) onKnifeCellClick(cell);
    });
    var kcOk = document.getElementById('kcOk');
    if (kcOk) kcOk.addEventListener('click', confirmKnifeDone);
    document.querySelectorAll('.axis-icon').forEach(function (el) {
        el.addEventListener('click', function () { openImgModal(el.getAttribute('data-img')); });
    });

    var t = document.getElementById('navToggle'), p = document.getElementById('navPanel');
    if (t) {
        t.addEventListener('click', function (e) { e.stopPropagation(); p.classList.toggle('open'); });
        document.addEventListener('click', function (e) {
            if (!p.contains(e.target) && e.target !== t) p.classList.remove('open');
        });
    }

    var o = document.getElementById('tipsOverlay');
    if (o) {
        document.getElementById('tipsBtn').addEventListener('click', function () { o.classList.add('active'); });
        document.getElementById('tipsClose').addEventListener('click', function () { o.classList.remove('active'); });
        o.addEventListener('click', function (e) { if (e.target === o) o.classList.remove('active'); });
    }

    /* 浮动导航跳转到 B/C/D 区时，自动展开该折叠区 */
    document.querySelectorAll('.float-nav-panel a[href^="#sec-"]').forEach(function (a) {
        a.addEventListener('click', function () {
            var el = document.querySelector(a.getAttribute('href'));
            if (el && el.tagName === 'DETAILS') el.open = true;
        });
    });
});
