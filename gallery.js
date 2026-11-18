/* 두근두근러닝 그림 모음 — catalog.json을 읽어 그리드 · 문서 보기, 크게 보기, 소리 듣기, 묶어 받기(ZIP) */
(function () {
  "use strict";
  var KINDS = ["배경", "소품", "캐릭터", "아이콘", "재질", "효과", "음악", "효과음"];
  var all = [], shown = [], kind = "전체", view = "grid", cur = -1;
  var selected = new Set();
  var $ = function (id) { return document.getElementById(id); };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function base(e) { return e.file.split("/").pop(); }
  function thumb(e) { return "thumbs/" + e.id + ".webp"; }
  function mb(b) { return b >= 1048576 ? (b / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(b / 1024)) + " KB"; }
  function hay(e) { return [e.title, (e.tags || []).join(" "), e.id, e.kind, e.situation, e.mood, (e.used_in || []).join(" ")].join(" ").toLowerCase(); }
  function isSnd(e) { return e.kind === "음악" || e.kind === "효과음"; }
  function secs(s) { s = Number(s) || 0; if (s < 10) return s.toFixed(1) + "초"; var m = Math.floor(s / 60), r = Math.round(s % 60); return m ? m + "분 " + (r ? r + "초" : "") : r + "초"; }
  function used(e) { return (e.used_in || []).length ? e.used_in.join(", ") : "아직 쓰인 영상 없음"; }
  function sndDl(e, cls) {
    return '<a class="' + cls + '" href="' + esc(e.files.m4a) + '" download="' + esc(e.files.m4a.split("/").pop()) + '">M4A 받기</a>' +
      '<a class="' + cls + '" href="' + esc(e.files.mp3) + '" download="' + esc(e.files.mp3.split("/").pop()) + '">MP3 받기</a>';
  }
  /* 소리는 한 번에 하나만 */
  var player = new Audio(); player.preload = "none"; var playing = null;
  function setBtns() {
    document.querySelectorAll("button.play").forEach(function (b) {
      var on = b.dataset.id === playing;
      b.setAttribute("aria-pressed", on); b.textContent = on ? "❚❚" : "▶";
      b.setAttribute("aria-label", (on ? "멈추기: " : "듣기: ") + b.dataset.title);
    });
  }
  function playToggle(id) {
    var e = all.find(function (x) { return x.id === id; }); if (!e) return;
    if (playing === id) { player.pause(); playing = null; setBtns(); return; }
    player.pause(); player.src = e.files.m4a; playing = id; setBtns();
    var pr = player.play(); if (pr && pr.catch) pr.catch(function () { playing = null; setBtns(); });
  }
  player.addEventListener("ended", function () { playing = null; setBtns(); });
  function playBtn(e) { return '<button type="button" class="play" data-id="' + esc(e.id) + '" data-title="' + esc(e.title) + '" aria-pressed="false" aria-label="듣기: ' + esc(e.title) + '">▶</button>'; }

  fetch("catalog.json").then(function (r) { return r.json(); }).then(function (d) {
    all = d;
    all.forEach(function (e) { e._h = hay(e); });
    buildKinds();
    render();
    var h = decodeURIComponent(location.hash.slice(1));
    if (h) { var i = shown.findIndex(function (e) { return e.id === h; }); if (i >= 0 && !isSnd(shown[i])) open(i); }
  }).catch(function () { $("stats").textContent = "목록을 불러오지 못했어요."; });

  function buildKinds() {
    var n = $("kinds");
    var items = [["전체", all.length]].concat(KINDS.map(function (k) {
      return [k, all.filter(function (e) { return e.kind === k; }).length];
    }).filter(function (x) { return x[1] > 0; }));
    n.innerHTML = items.map(function (x) {
      return '<button type="button" data-k="' + x[0] + '" aria-pressed="' + (x[0] === kind) + '">' + x[0] + "<small>" + x[1] + "</small></button>";
    }).join("");
    n.onclick = function (ev) {
      var b = ev.target.closest("button"); if (!b) return;
      kind = b.dataset.k;
      n.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x.dataset.k === kind); });
      render();
    };
  }

  $("q").addEventListener("input", render);
  document.querySelector(".seg").onclick = function (ev) {
    var b = ev.target.closest("button"); if (!b) return;
    view = b.dataset.v;
    document.querySelectorAll(".seg button").forEach(function (x) { x.setAttribute("aria-pressed", x.dataset.v === view); });
    render();
  };

  function filter() {
    var words = $("q").value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return all.filter(function (e) {
      if (kind !== "전체" && e.kind !== kind) return false;
      return words.every(function (w) { return e._h.indexOf(w) >= 0; });
    });
  }

  function render() {
    shown = filter();
    $("stats").textContent = shown.length === all.length ? "총 " + all.length + "개" : shown.length + " / " + all.length + "개";
    $("empty").hidden = shown.length > 0;
    var kz = $("kindZip");
    if (kind === "전체") kz.hidden = true;
    else {
      var ks = all.filter(function (e) { return e.kind === kind; });
      var bytes = ks.reduce(function (s, e) { return s + e.size.bytes; }, 0);
      kz.hidden = false;
      kz.textContent = kind + " " + ks.length + (isSnd(ks[0]) ? "개" : "장") + " 다운로드 (ZIP, " + mb(bytes) + ")";
    }
    if (view === "grid") {
      $("tableWrap").hidden = true; $("grid").hidden = false;
      $("grid").classList.toggle("snd-only", shown.length > 0 && shown.every(isSnd));
      $("grid").innerHTML = shown.map(function (e, i) {
        var s = selected.has(e.id);
        if (isSnd(e)) return '<li class="card snd' + (s ? " sel" : "") + '" data-i="' + i + '">' +
          '<label class="chk" title="선택에 담기"><input type="checkbox" aria-label="' + esc(e.title) + ' 고르기"' + (s ? " checked" : "") + "></label>" +
          '<div class="snd-top">' + playBtn(e) + '<div class="snd-name">' + esc(e.title) +
          '<span class="k">' + esc(e.kind) + " · " + secs(e.length) + (e.status === "후보" ? ' · <span class="cand">후보</span>' : "") + "</span></div></div>" +
          '<dl class="snd-meta"><dt>쓰인 영상</dt><dd>' + esc(used(e)) + '</dd><dt>상황</dt><dd>' + esc(e.situation) + '</dd><dt>분위기</dt><dd>' + esc(e.mood) + "</dd></dl>" +
          '<div class="snd-dl">' + sndDl(e, "pill") + "</div></li>";
        return '<li class="card' + (s ? " sel" : "") + '" data-i="' + i + '">' +
          '<label class="chk" title="선택에 담기"><input type="checkbox" aria-label="' + esc(e.title) + ' 고르기"' + (s ? " checked" : "") + "></label>" +
          '<a class="mini" href="' + esc(e.file) + '" download="' + esc(base(e)) + '" title="바로 다운로드" aria-label="' + esc(e.title) + ' 바로 다운로드">⬇</a>' +
          '<button type="button" class="open"><span class="ph"><img src="' + thumb(e) + '" alt="' + esc(e.title) + '" loading="lazy" width="480" height="360"></span>' +
          '<span class="t">' + esc(e.title) + '<span class="k">' + esc(e.kind) + " · " + e.size.w + "×" + e.size.h + "</span></span></button></li>";
      }).join("");
    } else {
      $("grid").hidden = true; $("tableWrap").hidden = false;
      $("docBody").innerHTML = shown.map(function (e, i) {
        var s = selected.has(e.id);
        if (isSnd(e)) return '<tr data-i="' + i + '"' + (s ? ' class="sel"' : "") + '>' +
          '<td><div class="im"><input type="checkbox" aria-label="' + esc(e.title) + ' 고르기"' + (s ? " checked" : "") + '>' + playBtn(e) + "</div></td>" +
          '<td class="nm">' + esc(e.title) + '<span class="k">' + secs(e.length) + (e.status === "후보" ? " · 후보" : "") + '</span></td><td class="fn">' + esc(e.file) + '</td>' +
          '<td><span class="badge">' + esc(e.kind) + '</span></td>' +
          '<td class="tg">' + esc((e.tags || []).join(", ")) + '</td>' +
          '<td class="tg">' + esc(used(e)) + '</td><td class="tg">' + esc(e.situation) + '</td><td class="tg">' + esc(e.mood) + '</td>' +
          '<td><div class="dl2">' + sndDl(e, "pill rowdl") + '</div></td></tr>';
        return '<tr data-i="' + i + '"' + (s ? ' class="sel"' : "") + '>' +
          '<td><div class="im"><input type="checkbox" aria-label="' + esc(e.title) + ' 고르기"' + (s ? " checked" : "") + '>' +
          '<button type="button" class="open" aria-label="' + esc(e.title) + ' 크게 보기"><img src="' + thumb(e) + '" alt="" loading="lazy"></button></div></td>' +
          '<td class="nm">' + esc(e.title) + '</td><td class="fn">' + esc(e.file) + '</td>' +
          '<td><span class="badge">' + esc(e.kind) + '</span></td>' +
          '<td class="tg">' + esc((e.tags || []).join(", ")) + '</td>' +
          '<td class="tg">' + esc((e.used_in || []).join(", ")) + '</td><td></td><td></td>' +
          '<td><a class="pill rowdl" href="' + esc(e.file) + '" download="' + esc(base(e)) + '">다운로드</a></td></tr>';
      }).join("");
    }
    setBtns();
    updateSel();
  }

  function onListClick(ev) {
    var row = ev.target.closest("[data-i]"); if (!row) return;
    var i = +row.dataset.i;
    if (ev.target.matches('input[type="checkbox"]')) { toggle(shown[i].id, ev.target.checked); return; }
    var pb = ev.target.closest("button.play"); if (pb) { playToggle(pb.dataset.id); return; }
    if (ev.target.closest(".open")) open(i);
  }
  $("grid").addEventListener("click", onListClick);
  $("docBody").addEventListener("click", onListClick);

  function toggle(id, on) {
    if (on) selected.add(id); else selected.delete(id);
    var i = shown.findIndex(function (e) { return e.id === id; });
    if (i >= 0) {
      var el = document.querySelector((view === "grid" ? "#grid" : "#docBody") + ' [data-i="' + i + '"]');
      if (el) { el.classList.toggle("sel", on); var c = el.querySelector('input[type="checkbox"]'); if (c) c.checked = on; }
    }
    updateSel();
  }
  function updateSel() {
    $("selCount").textContent = selected.size + "개 선택";
    $("selZip").disabled = selected.size === 0;
    $("selClear").disabled = selected.size === 0;
  }
  $("selAll").onclick = function () { shown.forEach(function (e) { selected.add(e.id); }); render(); };
  $("selClear").onclick = function () { selected.clear(); render(); };
  $("selZip").onclick = function () {
    var es = all.filter(function (e) { return selected.has(e.id); });
    if (es.length > 80 && !confirm(es.length + "개는 용량이 커서 오래 걸릴 수 있어요. 계속할까요?")) return;
    zip(es, "dugun-assets-선택-" + es.length + "개.zip");
  };
  $("kindZip").onclick = function () {
    var es = all.filter(function (e) { return e.kind === kind; });
    zip(es, "dugun-assets-" + kind + ".zip");
  };

  function zip(es, name) {
    if (!es.length) return;
    if (typeof JSZip === "undefined") { alert("ZIP으로 묶지 못했어요. 한 장씩 다운로드해 주세요."); return; }
    var z = new JSZip(), done = 0, fail = 0;
    var box = $("progress");
    $("pTitle").textContent = "다운로드 준비 중… (" + es.length + "개)";
    $("pFill").style.width = "0%"; $("pText").textContent = "0 / " + es.length;
    box.hidden = false;
    z.file("출처_LICENSE.txt", "그림 · 소리: 두근두근러닝(greatsong), CC BY-NC 4.0 — https://github.com/greatsong/dugun-assets\n" +
      "비상업 목적으로 쓸 수 있고, 쓸 때는 위 출처를 밝혀 주세요.\nhttps://creativecommons.org/licenses/by-nc/4.0/deed.ko\n");
    var chain = Promise.resolve();
    es.forEach(function (e) {
      chain = chain.then(function () {
        return fetch(e.file).then(function (r) { if (!r.ok) throw 0; return r.blob(); })
          .then(function (b) { z.file(e.file, b); }, function () { fail++; })
          .then(function () {
            done++;
            $("pFill").style.width = Math.round(done / es.length * 100) + "%";
            $("pText").textContent = done + " / " + es.length;
          });
      });
    });
    chain.then(function () {
      $("pTitle").textContent = "ZIP 파일로 묶는 중…";
      return z.generateAsync({ type: "blob" });
    }).then(function (blob) {
      var a = document.createElement("a");
      a.href = URL.createObjectURL(blob); a.download = name;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(function () { URL.revokeObjectURL(a.href); }, 4000);
      box.hidden = true;
      if (fail) alert(fail + "개를 다운로드하지 못했어요. 잠시 뒤 다시 해 보세요.");
    }).catch(function () { box.hidden = true; alert("ZIP으로 묶지 못했어요."); });
  }

  /* 크게 보기 */
  var dlg = $("view");
  function open(i, dir) {
    dir = dir || 1;
    while (i >= 0 && i < shown.length && isSnd(shown[i])) i += dir;      // 소리는 카드에서 바로 듣는다(크게 보기 없음)
    if (i < 0 || i >= shown.length) return;
    cur = i;
    var e = shown[i];
    var img = $("v-img");
    img.src = thumb(e); img.alt = e.title;
    var full = new Image();
    full.onload = function () { if (shown[cur] === e) img.src = e.file; };
    full.src = e.file;
    $("v-title").textContent = e.title;
    var dl = $("v-dl");
    dl.href = e.file; dl.setAttribute("download", base(e));
    dl.textContent = "다운로드 (" + base(e).split(".").pop().toUpperCase() + ", " + mb(e.size.bytes) + ")";
    $("v-sel").checked = selected.has(e.id);
    $("v-kind").textContent = e.kind;
    $("v-tags").textContent = (e.tags || []).join(", ");
    $("v-size").textContent = e.size.w + " × " + e.size.h + " 픽셀 · " + mb(e.size.bytes);
    $("v-tool").textContent = e.tool || "기록 없음";
    $("v-used").textContent = (e.used_in || []).join(", ") || "—";
    $("v-file").textContent = e.file;
    var p = e.prompt || "기록 없음";
    $("v-prompt").textContent = p;
    $("v-pwrap").hidden = p === "기록 없음";
    $("v-copy").textContent = "복사";
    var vs = e.variant_of ? all.filter(function (x) { return x.variant_of === e.variant_of; }) : [];
    $("v-vars").hidden = vs.length < 2;
    $("v-varlist").innerHTML = vs.map(function (x) {
      return '<li><button type="button" data-id="' + esc(x.id) + '" aria-label="' + esc(x.title) + '"' + (x.id === e.id ? ' aria-current="true"' : "") +
        '><img src="' + thumb(x) + '" alt="" loading="lazy"></button></li>';
    }).join("");
    $("v-prev").hidden = i === 0; $("v-next").hidden = i === shown.length - 1;
    history.replaceState(null, "", "#" + e.id);
    if (!dlg.open) dlg.showModal();
  }
  function close() { dlg.close(); }
  dlg.addEventListener("close", function () { history.replaceState(null, "", location.pathname + location.search); });
  $("v-close").onclick = close;
  $("v-prev").onclick = function () { open(cur - 1, -1); };
  $("v-next").onclick = function () { open(cur + 1); };
  $("v-sel").onchange = function () { toggle(shown[cur].id, this.checked); };
  dlg.addEventListener("click", function (ev) { if (ev.target === dlg) close(); });
  dlg.addEventListener("keydown", function (ev) {
    if (ev.target.tagName === "INPUT" && ev.target.type !== "checkbox") return;
    if (ev.key === "ArrowLeft") { ev.preventDefault(); open(cur - 1, -1); }
    else if (ev.key === "ArrowRight") { ev.preventDefault(); open(cur + 1); }
  });
  $("v-varlist").onclick = function (ev) {
    var b = ev.target.closest("button"); if (!b) return;
    var i = shown.findIndex(function (e) { return e.id === b.dataset.id; });
    if (i < 0) { kind = "전체"; $("q").value = ""; buildKinds(); render(); i = shown.findIndex(function (e) { return e.id === b.dataset.id; }); }
    open(i);
  };
  $("v-copy").onclick = function () {
    var t = $("v-prompt").textContent, btn = this;
    var ok = function () { btn.textContent = "복사 완료"; };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(t).then(ok, fallback);
    else fallback();
    function fallback() {
      var ta = document.createElement("textarea"); ta.value = t; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); ok(); } catch (e) { btn.textContent = "복사하지 못했어요"; }
      ta.remove();
    }
  };
})();
