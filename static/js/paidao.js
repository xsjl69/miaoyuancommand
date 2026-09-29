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

document.addEventListener('DOMContentLoaded', function () {
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') closeImgModal(); });
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
