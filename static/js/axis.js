/* 轴区交互：列表加载、筛选排序、详情、评论、点赞、上传 */
var allAxes = [];

function escapeHtml(s) {
    return (s || '').replace(/[&<>"']/g, function (c) {
        return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
}

function debounce(fn, wait) {
    var t;
    return function () {
        clearTimeout(t);
        t = setTimeout(fn, wait);
    };
}

function loadAxes() {
    // 加时间戳 + no-store：避免浏览器缓存导致上传后列表不刷新
    var url = '/api/axis?period=' + encodeURIComponent(CURRENT_PERIOD) + '&_=' + Date.now();
    return fetch(url, { cache: 'no-store' })
        .then(function (r) { return r.json(); })
        .then(function (d) { allAxes = d.axes || []; applyFilters(); })
        .catch(function () { document.getElementById('axisEmpty').style.display = 'block'; });
}

function applyFilters() {
    var boss = document.getElementById('fBoss').value;
    var min = parseFloat(document.getElementById('fMin').value);
    var max = parseFloat(document.getElementById('fMax').value);
    var sort = document.getElementById('fSort').value;
    var list = allAxes.filter(function (a) {
        if (boss && a.boss !== boss) return false;
        if (!isNaN(min) && a.damage < min) return false;
        if (!isNaN(max) && a.damage > max) return false;
        return true;
    });
    list.sort(function (x, y) {
        if (sort === 'boss_asc') return x.boss.localeCompare(y.boss);
        if (sort === 'boss_desc') return y.boss.localeCompare(x.boss);
        if (sort === 'dmg_desc') return y.damage - x.damage;
        if (sort === 'dmg_asc') return x.damage - y.damage;
        return 0;
    });
    renderAxes(list);
}

function renderAxes(list) {
    var grid = document.getElementById('axisGrid');
    var empty = document.getElementById('axisEmpty');
    grid.innerHTML = '';
    if (list.length === 0) { empty.style.display = 'block'; return; }
    empty.style.display = 'none';
    list.forEach(function (a) {
        var card = document.createElement('div');
        card.className = 'axis-card';
        card.dataset.id = a.id;
        var img = a.image
            ? '<img src="' + a.image + '" alt="轴图" loading="lazy">'
            : '<div style="height:120px;background:#eee;"></div>';
        card.innerHTML = img +
            '<div class="meta"><span class="boss">' + a.boss + '</span>' +
            '<span class="dmg">' + a.damage + 'e</span>' +
            '<div style="font-size:12px;color:#666;margin-top:2px;">' + escapeHtml(a.summary) + '</div></div>';
        card.onclick = function () { openDetail(a.id); };
        grid.appendChild(card);
    });
}

/* 高亮并滚动到指定轴卡片；被当前筛选隐藏时返回 false */
function highlightNewAxis(id) {
    var el = document.querySelector('.axis-card[data-id="' + id + '"]');
    if (!el) return false;
    el.classList.add('flash');
    try { el.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
    catch (e) { el.scrollIntoView(); }
    setTimeout(function () { el.classList.remove('flash'); }, 2200);
    return true;
}

/* 重置筛选为默认值 */
function resetFilters() {
    document.getElementById('fBoss').value = '';
    document.getElementById('fMin').value = '';
    document.getElementById('fMax').value = '';
    document.getElementById('fSort').value = 'boss_asc';
}

/* 筛选自动生效：改下拉即时筛选，数字框输入时防抖筛选 */
function bindAutoFilters() {
    ['fBoss', 'fSort'].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.addEventListener('change', applyFilters);
    });
    var onType = debounce(applyFilters, 200);
    ['fMin', 'fMax'].forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.addEventListener('input', onType);
    });
    var reset = document.getElementById('fReset');
    if (reset) reset.addEventListener('click', function () {
        resetFilters();
        applyFilters();
    });
}

/* ===== 详情 ===== */
function openDetail(id) {
    window._curAxisId = id;
    fetch('/api/axis/' + id).then(function (r) { return r.json(); }).then(function (d) {
        window._curComments = d.comments || [];
        renderDetail(d.axis);
        document.getElementById('detailModal').classList.add('active');
    });
}
function closeDetail() { document.getElementById('detailModal').classList.remove('active'); }

/* ===== 图片放大查看 ===== */
function openImgViewer(src) {
    if (!src) return;
    document.getElementById('imgViewerImg').src = src;
    document.getElementById('imgViewer').classList.add('active');
}
function closeImgViewer() { document.getElementById('imgViewer').classList.remove('active'); }

function renderDetail(a) {
    var box = document.getElementById('detailBox');
    var img = a.image ? '<img class="zoomable" src="' + a.image + '" style="max-width:100%;border-radius:8px;">' : '';
    var html = '<div style="margin-bottom:10px;">' + img + '</div>';
    html += '<div class="detail-head">' +
        '<div class="dh-title">' + a.boss + '</div>' +
        '<div class="dh-right"><span class="dh-dmg">' + a.damage + 'e</span>' +
        '<button class="del-btn" onclick="deleteAxis(' + a.id + ')">删除轴</button></div></div>';
    html += '<div style="color:#555;margin:6px 0;white-space:pre-line;">' + escapeHtml(a.summary) + '</div>';
    var cCount = (window._curComments || []).length;
    html += '<hr><div class="cmt-head">' +
        '<b>评论区 <span class="cmt-count">' + cCount + '</span></b>' +
        '<div class="cmt-sort" id="cSort">' +
        '<button type="button" class="seg active" data-sort="time_desc">最新</button>' +
        '<button type="button" class="seg" data-sort="time_asc">最早</button>' +
        '<button type="button" class="seg" data-sort="like_desc">最热</button>' +
        '</div></div>';
    html += '<div id="commentList"></div>';
    html += '<div style="border-top:1px solid #eee;padding-top:10px;margin-top:8px;">' +
        '<div class="form-row"><label>上传人</label><input id="cUploader" placeholder="你的名字"></div>' +
        '<div class="form-row"><label>评论</label><textarea id="cContent" placeholder="说点什么…"></textarea></div>' +
        '<div class="form-row file-row"><label>图片</label>' +
        '<label class="file-drop" for="cImage" data-default-text="点击选择，或拖拽图片到此处" data-default-hint="支持 PNG / JPG / WEBP">' +
        '<input type="file" id="cImage" name="image" accept="image/png,image/jpeg,image/webp" hidden>' +
        '<span class="fd-icon">🖼️</span>' +
        '<span class="fd-text">点击选择，或拖拽图片到此处</span>' +
        '<span class="fd-hint">支持 PNG / JPG / WEBP</span>' +
        '</label></div>' +
        '<div class="file-name" id="cFileName" hidden></div>' +
        '<button class="btn" onclick="submitComment(' + a.id + ')">发表评论</button> ' +
        '<span id="cMsg" style="color:var(--red);"></span></div>';
    box.innerHTML = html;
    renderComments();
}

/* 当前评论排序方式（取自分段按钮的 active 项） */
function currentCommentSort() {
    var el = document.querySelector('#cSort .seg.active');
    return el ? el.getAttribute('data-sort') : 'time_desc';
}

function renderComments() {
    var list = (window._curComments || []).slice();
    var sort = currentCommentSort();
    if (sort === 'time_desc') list.sort(function (a, b) { return b.created_at.localeCompare(a.created_at); });
    else if (sort === 'time_asc') list.sort(function (a, b) { return a.created_at.localeCompare(b.created_at); });
    else if (sort === 'like_desc') list.sort(function (a, b) { return b.likes - a.likes; });
    var html = '';
    list.forEach(function (c) {
        var img = c.image ? '<img class="zoomable" src="' + c.image + '" style="max-width:100%;border-radius:6px;margin-top:4px;">' : '';
        html += '<div class="comment"><div class="head"><span class="uploader">' + escapeHtml(c.uploader) +
            '</span><span class="head-right"><span>' + c.created_at + '</span>' +
            '<button class="del-btn" onclick="deleteComment(' + c.id + ')">删除</button></span></div>' +
            '<div class="body">' + escapeHtml(c.content) + '</div>' + img +
            '<button class="like-btn' + (c.liked ? ' liked' : '') + '" onclick="toggleLike(' + c.id + ')">♥ <span id="lk' + c.id + '">' + c.likes + '</span></button></div>';
    });
    if (list.length === 0) html = '<div style="color:#999;padding:10px 0;">还没有评论，抢沙发～</div>';
    document.getElementById('commentList').innerHTML = html;
}

function toggleLike(id) {
    fetch('/api/comment/' + id + '/like', { method: 'POST' })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            var span = document.getElementById('lk' + id);
            if (!span) { renderComments(); return; }
            span.textContent = d.count;
            var btn = span.parentElement;
            btn.classList.toggle('liked', d.liked);
            var c = (window._curComments || []).find(function (x) { return x.id === id; });
            if (c) { c.likes = d.count; c.liked = !!d.liked; }
        });
}

function submitComment(axisId) {
    var uploader = document.getElementById('cUploader').value.trim();
    var content = document.getElementById('cContent').value.trim();
    var file = document.getElementById('cImage').files[0];
    var msg = document.getElementById('cMsg');
    if (!uploader) { msg.textContent = '请填写上传人'; return; }
    if (!content && !file) { msg.textContent = '评论文字或图片至少一项'; return; }
    var fd = new FormData();
    fd.append('uploader', uploader);
    fd.append('content', content);
    if (file) fd.append('image', file);
    fetch('/api/axis/' + axisId + '/comment', { method: 'POST', body: fd })
        .then(function (r) { return r.json(); })
        .then(function (d) {
            if (d.error) { msg.textContent = d.error; return; }
            msg.textContent = '';
            openDetail(axisId);
        });
}

/* ===== 管理员删除（需密码） ===== */
function askPassword(title, onConfirm) {
    window._pwdCb = onConfirm;
    document.getElementById('pwdTitle').textContent = title || '管理员验证';
    document.getElementById('pwdInput').value = '';
    document.getElementById('pwdMsg').textContent = '';
    document.getElementById('pwdModal').classList.add('active');
    setTimeout(function () {
        var i = document.getElementById('pwdInput');
        if (i) i.focus();
    }, 60);
}

function closePwd() {
    document.getElementById('pwdModal').classList.remove('active');
    window._pwdCb = null;
}

function confirmPwd() {
    var pw = document.getElementById('pwdInput').value;
    if (!pw) { document.getElementById('pwdMsg').textContent = '请输入密码'; return; }
    if (window._pwdCb) window._pwdCb(pw);
}

function _adminDelete(url, title, onDone) {
    askPassword(title, function (pw) {
        fetch(url, {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ password: pw })
        }).then(function (r) {
            return r.json().then(function (d) { return { ok: r.ok, d: d }; });
        }).then(function (res) {
            if (!res.ok) {
                document.getElementById('pwdMsg').textContent = (res.d && res.d.error) || '删除失败';
                return;
            }
            closePwd();
            onDone();
        }).catch(function () {
            document.getElementById('pwdMsg').textContent = '网络错误，请重试';
        });
    });
}

function deleteAxis(id) {
    _adminDelete('/api/axis/' + id, '删除轴', function () {
        closeDetail();
        loadAxes();
    });
}

function deleteComment(id) {
    _adminDelete('/api/comment/' + id, '删除评论', function () {
        openDetail(window._curAxisId);
    });
}

/* ===== 上传轴 ===== */
function toggleUpload() {
    var f = document.getElementById('uploadForm');
    var head = document.getElementById('uploadHead');
    var open = f.style.display === 'none';
    f.style.display = open ? 'block' : 'none';
    if (head) head.classList.toggle('open', open);
}

/* 文件拖拽区：通用处理（上传轴 + 评论图片共用） */
function setDropFile(drop, name) {
    if (!drop) return;
    var txt = drop.querySelector('.fd-text');
    var hint = drop.querySelector('.fd-hint');
    if (name) {
        drop.classList.add('has-file');
        if (txt) txt.textContent = '已选择：' + name;
        if (hint) hint.textContent = '点击可重新选择';
        var row = drop.closest('.form-row');
        var fn = row && row.nextElementSibling;
        if (fn && fn.classList.contains('file-name')) { fn.textContent = name; fn.hidden = false; }
    } else {
        drop.classList.remove('has-file');
        if (txt) txt.textContent = drop.dataset.defaultText || '点击选择文件';
        if (hint) hint.textContent = drop.dataset.defaultHint || '';
        var row2 = drop.closest('.form-row');
        var fn2 = row2 && row2.nextElementSibling;
        if (fn2 && fn2.classList.contains('file-name')) fn2.hidden = true;
    }
}

document.addEventListener('DOMContentLoaded', function () {
    loadAxes();
    bindAutoFilters();

    /* 点击详情轴图 / 评论图片 → 放大查看（事件委托，覆盖动态生成内容） */
    document.addEventListener('click', function (e) {
        var el = e.target.closest ? e.target.closest('.zoomable') : null;
        if (el) openImgViewer(el.getAttribute('src'));
    });
    document.addEventListener('keydown', function (e) {
        if (e.key === 'Escape') { closeImgViewer(); closePwd(); }
    });

    /* 评论区排序分段按钮：点击切换 active 并重排 */
    document.addEventListener('click', function (e) {
        var btn = e.target.closest ? e.target.closest('#cSort .seg') : null;
        if (!btn) return;
        document.querySelectorAll('#cSort .seg').forEach(function (b) { b.classList.remove('active'); });
        btn.classList.add('active');
        renderComments();
    });

    /* 管理员密码框支持回车确认 */
    var pwdInput = document.getElementById('pwdInput');
    if (pwdInput) {
        pwdInput.addEventListener('keydown', function (e) {
            if (e.key === 'Enter') { e.preventDefault(); confirmPwd(); }
        });
    }

    /* 文件选择 / 拖拽（事件委托，覆盖动态生成的评论图片区） */
    document.addEventListener('change', function (e) {
        if (e.target.matches('.file-drop input[type=file]')) {
            setDropFile(e.target.closest('.file-drop'), e.target.files[0] ? e.target.files[0].name : '');
        }
    });
    ['dragenter', 'dragover'].forEach(function (ev) {
        document.addEventListener(ev, function (e) {
            var drop = e.target.closest && e.target.closest('.file-drop');
            if (drop) { e.preventDefault(); drop.classList.add('dragover'); }
        });
    });
    ['dragleave', 'drop'].forEach(function (ev) {
        document.addEventListener(ev, function (e) {
            var drop = e.target.closest && e.target.closest('.file-drop');
            if (drop) { e.preventDefault(); drop.classList.remove('dragover'); }
        });
    });
    document.addEventListener('drop', function (e) {
        var drop = e.target.closest && e.target.closest('.file-drop');
        if (drop) {
            var inp = drop.querySelector('input[type=file]');
            if (e.dataTransfer.files && e.dataTransfer.files[0] && inp) {
                inp.files = e.dataTransfer.files;
                setDropFile(drop, inp.files[0].name);
            }
        }
    });

    var form = document.getElementById('uploadForm');
    form.addEventListener('submit', function (e) {
        e.preventDefault();
        var fd = new FormData(form);
        fetch('/api/axis', { method: 'POST', body: fd })
            .then(function (r) { return r.json(); })
            .then(function (d) {
                var m = document.getElementById('uploadMsg');
                if (d.error) { m.textContent = d.error; return; }
                m.textContent = '上传成功！';
                form.reset();
                var drop = document.getElementById('fileDrop');
                if (drop) setDropFile(drop, '');
                // 刷新下方轴列表，并高亮定位到刚上传的轴
                loadAxes().then(function () {
                    if (!highlightNewAxis(d.id)) {
                        // 新轴被当前筛选条件隐藏了 → 重置筛选后再刷新，确保能看到
                        resetFilters();
                        loadAxes().then(function () { highlightNewAxis(d.id); });
                    }
                });
            });
    });
});
