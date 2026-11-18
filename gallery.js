/* 두근두근러닝 그림 · 소리 모음 — catalog.json을 읽어 그리드 · 문서 보기, 크게 보기, 소리 듣기(길이 · 판 고르기, 반복용은 끊김 없이 되풀이), 묶어 받기(ZIP) */
(function () {
  "use strict";
  var IMG_KINDS = ["배경", "소품", "캐릭터", "아이콘", "재질", "효과"];
  var SND_KINDS = ["음악", "효과음"];
  var KCLS = { "전체": "k-all", "배경": "k-bg", "소품": "k-prop", "캐릭터": "k-char", "아이콘": "k-icon", "재질": "k-tex", "효과": "k-fx",
    "음악": "k-music", "효과음": "k-sfx", "반복용": "k-loop", "교실": "k-class", "예능": "k-show", "게임": "k-game" };
  /* 소리만 거르는 칩: 이름 → 거르는 법 */
  var SND_FILTERS = {
    "반복용": function (e) { return e.loop === true || (e.versions || []).some(function (v) { return v.loop; }); },
    "교실": function (e) { return e.style === "교실"; },
    "예능": function (e) { return e.style === "예능"; },
    "게임": function (e) { return e.style === "게임"; }
  };
  var all = [], byId = {}, shown = [], kind = "전체", view = "grid", cur = -1, waves = {};
  var selected = new Set(), verSel = {};
  var $ = function (id) { return document.getElementById(id); };

  var ICON = {
    play: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M8 5.5v13a1 1 0 0 0 1.5.86l10.4-6.5a1 1 0 0 0 0-1.72L9.5 4.64A1 1 0 0 0 8 5.5z"/></svg>',
    pause: '<svg viewBox="0 0 24 24" aria-hidden="true"><rect x="6" y="5" width="4.2" height="14" rx="1.2"/><rect x="13.8" y="5" width="4.2" height="14" rx="1.2"/></svg>',
    load: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3a9 9 0 1 0 9 9"/></svg>',
    loop: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M7 7h9a4 4 0 0 1 0 8h-1"/><path d="M17 17H8a4 4 0 0 1 0-8h1"/><path d="m14 4 3 3-3 3"/><path d="m10 20-3-3 3-3"/></svg>',
    dl: '<svg class="ico" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 4v11"/><path d="m7 10 5 5 5-5"/><path d="M5 20h14"/></svg>'
  };

  function esc(s) {
    return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c];
    });
  }
  function base(p) { return String(p).split("/").pop(); }
  function thumb(e) { return "thumbs/" + e.id + ".webp"; }
  function mb(b) { return b >= 1048576 ? (b / 1048576).toFixed(1) + " MB" : Math.max(1, Math.round(b / 1024)) + " KB"; }
  function isSnd(e) { return SND_KINDS.indexOf(e.kind) >= 0; }
  function secs(s) { s = Number(s) || 0; if (s < 10) return s.toFixed(1) + "초"; var m = Math.floor(s / 60), r = Math.round(s % 60); return m ? m + "분" + (r ? " " + r + "초" : "") : r + "초"; }
  function used(e) { return (e.used_in || []).length ? e.used_in.join(", ") : "아직 쓰인 영상 없음"; }
  function hay(e) {
    var v = (e.versions || []).map(function (x) { return [x.label, x.title, x.desc].join(" "); }).join(" ");
    return [e.title, (e.tags || []).join(" "), e.id, e.kind, e.style, e.situation, e.mood, (e.used_in || []).join(" "), e.loop ? "반복용" : "", v].join(" ").toLowerCase();
  }
  function kcls(k) { return KCLS[k] || "k-all"; }
  /* 반복용 판처럼 원곡 카드의 판(versions)으로 들어간 항목은 원곡 카드에서 고른다(따로 카드를 만들지 않음). '반복용'으로 거르면 카드마다 반복용 판이 먼저 골라진다 */
  function folded(e) {
    var p = e.loop_of && byId[e.loop_of];
    return !!p && (p.versions || []).some(function (v) { return v.id === e.id; });
  }

  /* ── 판(길이 · 1 · 2 · 3번) ── */
  function vers(e) { return e.versions && e.versions.length ? e.versions : null; }
  function curVer(e) {
    var vs = vers(e); if (!vs) return { id: e.id, label: "", file: e.file, files: e.files || { m4a: e.file }, length: e.length, loop: e.loop === true,
      bytes: e.size && e.size.bytes, mp3_bytes: e.size && e.size.mp3_bytes };
    var li = vs.findIndex(function (v) { return v.loop; });
    var i = Math.min(verSel[e.id] != null ? verSel[e.id] : (kind === "반복용" && li >= 0 ? li : (e.version_default || 0)), vs.length - 1), v = vs[i];
    var ent = v.id && v.id !== e.id ? byId[v.id] : null;      // 판이 목록의 다른 항목이면(반복용 판 등) 그 항목의 정보를 쓴다
    return { id: v.id || e.id + "#" + i, label: v.label, title: v.title, desc: v.desc, file: v.file, files: v.files || { m4a: v.file }, length: v.length,
      loop: v.loop === true || (!!ent && ent.loop === true), made_by: v.made_by, ent: ent, i: i,
      bytes: v.bytes || (ent ? ent.size.bytes : v.id === e.id ? e.size.bytes : 0), mp3_bytes: v.mp3_bytes || (ent ? ent.size.mp3_bytes : v.id === e.id ? e.size.mp3_bytes : 0) };
  }
  function verKindLabel(vs) { return vs.some(function (v) { return /번$/.test(v.label); }) ? "버전" : "길이"; }
  function versHTML(e) {
    var vs = vers(e); if (!vs) return "";
    var c = curVer(e);
    return '<div class="vers" role="group" aria-label="' + verKindLabel(vs) + ' 고르기"><span class="vl">' + verKindLabel(vs) + "</span>" + vs.map(function (v, i) {
      var lp = v.loop === true;
      return '<button type="button" data-ver="' + i + '" data-id="' + esc(e.id) + '" aria-pressed="' + (i === c.i) + '"' + (v.title ? ' title="' + esc(v.title) + '"' : "") + ">" +
        (lp ? ICON.loop : "") + esc(v.label) + "</button>";
    }).join("") + "</div>";
  }
  function verNote(e) {
    var vs = vers(e); if (!vs) return "";
    var c = curVer(e);
    return c.title ? '<p class="ver-note">' + esc(c.label) + " 버전 · " + esc(c.title) + "</p>" : "";
  }
  function sndDl(e, cls) {
    var c = curVer(e), f = c.files;
    return '<a class="' + cls + '" href="' + esc(f.m4a) + '" download="' + esc(base(f.m4a)) + '">' + ICON.dl + "M4A 받기</a>" +
      (f.mp3 ? '<a class="' + cls + '" href="' + esc(f.mp3) + '" download="' + esc(base(f.mp3)) + '">' + ICON.dl + "MP3 받기</a>" : "");
  }
  function statusChip(e) {
    var c = curVer(e), s = (c.ent || e).status || ""; if (!s) return "";
    var c = s === "쓰임" ? "st-used" : s.indexOf("후보") === 0 ? "st-cand" : "st-new";
    return '<span class="st ' + c + '">' + esc(s) + "</span>";
  }
  function waveHTML(id, big) {
    var w = waves[id] || [], bars = "";
    if (!w.length) for (var k = 0; k < 40; k++) w.push(30);
    for (var i = 0; i < w.length; i++) bars += '<span style="height:' + w[i] + '%"></span>';
    return '<div class="wb">' + bars + '</div><div class="wf"><div class="wb">' + bars + "</div></div>";
  }

  /* ── 소리 재생: 한 번에 하나. 반복용은 웹 오디오로 끊김 없이 되풀이(안 되면 audio loop) ── */
  var player = new Audio(); player.preload = "none";
  var AC = window.AudioContext || window.webkitAudioContext, actx = null, src = null, t0 = 0, bufs = {};
  var playing = null;   // { eid, vid, loop, len, mode: 'html'|'wa', state: 'load'|'on' }
  function stopAll() {
    player.pause(); player.loop = false;
    if (src) { try { src.stop(); } catch (x) {} try { src.disconnect(); } catch (x) {} src = null; }
    playing = null; setBtns(); setProgress(0, true);
  }
  function setBtns() {
    document.querySelectorAll("button.play").forEach(function (b) {
      var id = b.dataset.id || (b.id === "v-play" && shown[cur] ? shown[cur].id : ""), on = !!playing && playing.eid === id;
      var ld = on && playing.state === "load";
      b.classList.toggle("loading", ld);
      b.setAttribute("aria-pressed", on);
      b.innerHTML = ld ? ICON.load : on ? ICON.pause : ICON.play;
      var e = byId[id];
      if (e) b.setAttribute("aria-label", (on ? "멈추기: " : "듣기: ") + e.title);
    });
  }
  function decode(ab) {
    return new Promise(function (ok, no) { var p = actx.decodeAudioData(ab, ok, no); if (p && p.then) p.then(ok, no); });
  }
  /* 압축 파일은 처음 · 끝 몇 표본을 조금 다르게 복원해 이음매에 작은 턱이 남을 수 있다 → 이음매 앞뒤 16표본(0.7 ms)을 곧게 이어 준다 */
  function smoothSeam(buf, n) {
    var K = 16; if (n < 4 * K) return;
    for (var c = 0; c < buf.numberOfChannels; c++) {
      var d = buf.getChannelData(c), a = d[n - K - 1], b = d[K];
      for (var k = 0; k < 2 * K; k++) {
        var t = (k + 1) / (2 * K + 1), v = a + (b - a) * t;
        if (k < K) d[n - K + k] = v; else d[k - K] = v;
      }
    }
  }
  function playHtml(v, loop) {
    player.pause(); player.src = v.files.m4a; player.loop = !!loop;
    playing.mode = "html";
    var pr = player.play();
    var started = function () { if (playing && playing.vid === v.id) { playing.state = "on"; setBtns(); tick(); } };
    if (pr && pr.then) pr.then(started, function () { stopAll(); }); else started();
  }
  function playLoop(v) {
    try { actx = actx || new AC(); if (actx.state === "suspended") actx.resume(); } catch (x) { return playHtml(v, true); }
    var url = v.files.m4a;
    bufs[url] = bufs[url] || fetch(url).then(function (r) { if (!r.ok) throw 0; return r.arrayBuffer(); }).then(decode);
    bufs[url].then(function (buf) {
      if (!playing || playing.vid !== v.id) return;
      var want = Number(v.length) || buf.duration;
      if (Math.abs(buf.duration - want) > 0.02) return playHtml(v, true);     // 앞뒤에 빈 소리가 붙은 채 풀리면 audio 반복으로
      /* 풀린 길이가 목록의 길이와 0.02초 안에서 같으면 앞뒤 빈 소리 없이 풀린 것 → 풀린 길이 그대로 한 바퀴로 쓴다(목록 길이는 반올림 값) */
      if (!buf._smooth) { smoothSeam(buf, buf.length); buf._smooth = true; }
      src = actx.createBufferSource(); src.buffer = buf; src.loop = true; src.loopStart = 0; src.loopEnd = buf.duration;
      playing.len = buf.duration;
      src.connect(actx.destination); src.start(); t0 = actx.currentTime;
      playing.mode = "wa"; playing.state = "on"; setBtns(); tick();
    }).catch(function () { delete bufs[url]; if (playing && playing.vid === v.id) playHtml(v, true); });
  }
  function playToggle(id) {
    var e = byId[id]; if (!e) return;
    var v = curVer(e);
    if (playing && playing.eid === id && playing.vid === v.id) { stopAll(); return; }
    stopAll();
    playing = { eid: id, vid: v.id, loop: v.loop, len: Number(v.length) || 0, state: "load" };
    setBtns();
    if (v.loop && AC && window.fetch) playLoop(v); else playHtml(v, v.loop);
  }
  player.addEventListener("ended", function () { if (playing && playing.mode === "html" && !player.loop) stopAll(); });
  function setProgress(p, reset) {
    document.querySelectorAll(".wave").forEach(function (w) {
      var mine = playing && (w.dataset.id === playing.eid || (w.id === "v-wave" && shown[cur] && shown[cur].id === playing.eid));
      w.style.setProperty("--p", (reset || !mine ? 0 : Math.max(0, Math.min(1, p)) * 100) + "%");
    });
  }
  function tick() {
    if (!playing || playing.state !== "on") return;
    var p = 0;
    if (playing.mode === "wa") p = ((actx.currentTime - t0) % playing.len) / playing.len;
    else p = player.duration ? player.currentTime / player.duration : 0;
    setProgress(p);
    requestAnimationFrame(tick);
  }
  function playBtn(e) { return '<button type="button" class="play" data-id="' + esc(e.id) + '" aria-pressed="false" aria-label="듣기: ' + esc(e.title) + '">' + ICON.play + "</button>"; }

  /* ── 불러오기 ── */
  Promise.all([
    fetch("catalog.json").then(function (r) { return r.json(); }),
    fetch("audio/waves.json").then(function (r) { return r.ok ? r.json() : {}; }).catch(function () { return {}; })
  ]).then(function (d) {
    all = d[0]; waves = d[1] || {};
    all.forEach(function (e) { e._h = hay(e); byId[e.id] = e; });
    var ni = all.filter(function (e) { return !isSnd(e); }).length, nm = count("음악"), ns = count("효과음"), nl = count("반복용");
    $("countImg").innerHTML = "<b>그림</b> " + ni + "장";
    $("countSnd").innerHTML = "<b>음악</b> " + nm + "곡 · <b>효과음</b> " + ns + "개" + (nl ? " · <b>반복용</b> " + nl + "개" : "");
    buildKinds();
    render();
    var h = decodeURIComponent(location.hash.slice(1));
    if (h) {
      var i = shown.findIndex(function (e) { return e.id === h; });
      if (i < 0 && byId[h] && folded(byId[h])) {          // 원곡 카드에 들어간 판이면 원곡을 그 판으로 연다
        var p = byId[byId[h].loop_of]; verSel[p.id] = p.versions.findIndex(function (v) { return v.id === h; }); render();
        i = shown.indexOf(p);
      }
      if (i >= 0) open(i);
    }
  }).catch(function () { $("stats").textContent = "목록을 불러오지 못했어요."; });

  function count(k) {
    return all.filter(function (e) { return !folded(e) && inKind(e, k); }).length;
  }
  function buildKinds() {
    var n = $("kinds");
    var chip = function (k) {
      var c = count(k); if (!c) return "";
      return '<button type="button" class="kchip-btn ' + kcls(k) + '" data-k="' + k + '" aria-pressed="' + (k === kind) + '">' +
        (k === "반복용" ? ICON.loop.replace('class="ico"', 'class="ico" style="width:16px;height:16px;color:var(--c)"') : "<i></i>") + k + "<small>" + c + "</small></button>";
    };
    n.innerHTML = chip("전체") + '<span class="grp">그림</span>' + IMG_KINDS.map(chip).join("") +
      '<span class="grp">소리</span>' + SND_KINDS.map(chip).join("") + Object.keys(SND_FILTERS).map(chip).join("");
    n.onclick = function (ev) {
      var b = ev.target.closest("button"); if (!b) return;
      kind = b.dataset.k;
      n.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x.dataset.k === kind); });
      render();
    };
  }

  $("q").addEventListener("input", render);
  if (window.matchMedia && matchMedia("(max-width: 760px)").matches) $("q").placeholder = "낱말로 찾기 (예: 교실, 별, 반복용)";
  document.querySelector(".seg").onclick = function (ev) {
    var b = ev.target.closest("button"); if (!b) return;
    view = b.dataset.v;
    document.querySelectorAll(".seg button").forEach(function (x) { x.setAttribute("aria-pressed", x.dataset.v === view); });
    render();
  };

  function inKind(e, k) {
    if (k === "전체") return true;
    if (SND_FILTERS[k]) return SND_FILTERS[k](e);
    return e.kind === k;
  }
  function filter() {
    var words = $("q").value.trim().toLowerCase().split(/\s+/).filter(Boolean);
    return all.filter(function (e) {
      if (!inKind(e, kind)) return false;
      if (folded(e)) return false;
      return words.every(function (w) { return e._h.indexOf(w) >= 0; });
    });
  }

  /* 받을 파일: 판이 있으면 모든 판 */
  function filesOf(e) { var vs = vers(e); return vs ? vs.map(function (v) { return v.file; }) : [e.file]; }
  function sizeOf(path) {
    for (var i = 0; i < all.length; i++) {
      var e = all[i];
      if (e.file === path) return (e.size && e.size.bytes) || 0;
      var vs = e.versions || [];
      for (var j = 0; j < vs.length; j++) if (vs[j].file === path && vs[j].bytes) return vs[j].bytes;
    }
    return 0;
  }
  function uniqFiles(es) { var s = new Set(); es.forEach(function (e) { filesOf(e).forEach(function (f) { s.add(f); }); }); return Array.from(s); }

  function sndCard(e, i, s) {
    var c = curVer(e);
    return '<li class="card snd' + (s ? " sel" : "") + (c.loop ? " loop" : "") + '" data-i="' + i + '">' +
      '<label class="chk" title="고르기"><input type="checkbox" aria-label="' + esc(e.title) + ' 고르기"' + (s ? " checked" : "") + "></label>" +
      '<div class="snd-head">' + playBtn(e) + '<div class="snd-tt"><button type="button" class="snd-name open">' + esc(e.title) + "</button>" +
      '<div class="snd-sub"><span class="kchip ' + kcls(e.kind) + '">' + esc(e.kind) + (e.style ? " · " + esc(e.style) : "") + "</span><span class=\"len\">" + secs(c.length) + "</span>" +
      statusChip(e) + (c.loop ? '<span class="loopb">' + ICON.loop + "반복용</span>" : "") + "</div></div></div>" +
      versHTML(e) + verNote(e) +
      '<div class="wave" data-id="' + esc(e.id) + '">' + waveHTML(c.id) + "</div>" +
      '<dl class="snd-meta"><div><dt>쓰인 영상</dt><dd>' + esc(used(e)) + "</dd></div><div><dt>상황</dt><dd>" + esc(e.situation) +
      "</dd></div><div><dt>분위기</dt><dd>" + esc(e.mood) + "</dd></div></dl>" +
      '<div class="snd-foot">' + sndDl(e, "btn sm line-blue") + '<button type="button" class="btn sm vi open">자세히 보기</button></div></li>';
  }
  function imgCard(e, i, s) {
    var cover = e.kind === "배경" || e.kind === "재질";
    return '<li class="card' + (s ? " sel" : "") + '" data-i="' + i + '">' +
      '<label class="chk" title="고르기"><input type="checkbox" aria-label="' + esc(e.title) + ' 고르기"' + (s ? " checked" : "") + "></label>" +
      '<a class="mini" href="' + esc(e.file) + '" download="' + esc(base(e.file)) + '" title="바로 받기" aria-label="' + esc(e.title) + ' 바로 받기">' + ICON.dl + "</a>" +
      '<button type="button" class="open"><span class="ph' + (cover ? " cover" : "") + '"><img src="' + thumb(e) + '" alt="' + esc(e.title) + '" loading="lazy" width="480" height="360"></span>' +
      '<span class="t"><span class="tt">' + esc(e.title) + '</span><span class="k"><span class="kchip ' + kcls(e.kind) + '">' + esc(e.kind) + "</span>" + e.size.w + " × " + e.size.h + "</span></span></button></li>";
  }
  function sndRow(e, i, s) {
    var c = curVer(e);
    return '<tr data-i="' + i + '"' + (s ? ' class="sel"' : "") + ">" +
      '<td><div class="im"><input type="checkbox" aria-label="' + esc(e.title) + ' 고르기"' + (s ? " checked" : "") + ">" + playBtn(e) + "</div></td>" +
      '<td class="nm">' + esc(e.title) + '<span class="k">' + secs(c.length) + (e.status ? " · " + esc(e.status) : "") + (c.loop ? " · 반복용" : "") + "</span>" + versHTML(e) + "</td>" +
      '<td class="fn">' + esc(c.file) + "</td>" +
      '<td><span class="kchip ' + kcls(e.kind) + '">' + esc(e.kind) + "</span></td>" +
      '<td class="tg">' + esc((e.tags || []).join(", ")) + "</td>" +
      '<td class="tg">' + esc(used(e)) + '</td><td class="tg">' + esc(e.situation) + '</td><td class="tg">' + esc(e.mood) + "</td>" +
      '<td><div class="dl2">' + sndDl(e, "btn sm") + "</div></td></tr>";
  }
  function imgRow(e, i, s) {
    return '<tr data-i="' + i + '"' + (s ? ' class="sel"' : "") + ">" +
      '<td><div class="im"><input type="checkbox" aria-label="' + esc(e.title) + ' 고르기"' + (s ? " checked" : "") + ">" +
      '<button type="button" class="open" aria-label="' + esc(e.title) + ' 크게 보기"><img src="' + thumb(e) + '" alt="" loading="lazy"></button></div></td>' +
      '<td class="nm">' + esc(e.title) + '</td><td class="fn">' + esc(e.file) + "</td>" +
      '<td><span class="kchip ' + kcls(e.kind) + '">' + esc(e.kind) + "</span></td>" +
      '<td class="tg">' + esc((e.tags || []).join(", ")) + "</td>" +
      '<td class="tg">' + esc((e.used_in || []).join(", ")) + "</td><td></td><td></td>" +
      '<td><a class="btn sm" href="' + esc(e.file) + '" download="' + esc(base(e.file)) + '">' + ICON.dl + "받기</a></td></tr>";
  }

  function render() {
    shown = filter();
    var tot = count("전체");
    $("stats").textContent = shown.length === tot ? "모두 " + tot + "개" : shown.length + " / " + tot + "개";
    $("empty").hidden = shown.length > 0;
    var kz = $("kindZip");
    if (kind === "전체") kz.hidden = true;
    else {
      var ks = all.filter(function (e) { return inKind(e, kind) && !folded(e); });
      var bytes = uniqFiles(ks).reduce(function (s, f) { return s + sizeOf(f); }, 0);
      kz.hidden = false;
      kz.textContent = kind + " " + ks.length + (ks.every(function (x) { return x.kind === "음악"; }) && kind !== "반복용" ? "곡" : isSnd(ks[0]) ? "개" : "장") + " 받기 (ZIP, " + mb(bytes) + ")";
    }
    if (view === "grid") {
      $("tableWrap").hidden = true; $("grid").hidden = false;
      $("grid").classList.toggle("snd-only", shown.length > 0 && shown.every(isSnd));
      $("grid").innerHTML = shown.map(function (e, i) { var s = selected.has(e.id); return isSnd(e) ? sndCard(e, i, s) : imgCard(e, i, s); }).join("");
    } else {
      $("grid").hidden = true; $("tableWrap").hidden = false;
      $("docBody").innerHTML = shown.map(function (e, i) { var s = selected.has(e.id); return isSnd(e) ? sndRow(e, i, s) : imgRow(e, i, s); }).join("");
    }
    setBtns();
    updateSel();
  }
  function rerenderOne(i) {
    var e = shown[i]; if (!e) return;
    var el = document.querySelector((view === "grid" ? "#grid" : "#docBody") + ' [data-i="' + i + '"]'); if (!el) return;
    var s = selected.has(e.id), tmp = document.createElement(view === "grid" ? "ul" : "tbody");
    tmp.innerHTML = view === "grid" ? sndCard(e, i, s) : sndRow(e, i, s);
    el.replaceWith(tmp.firstChild);
    setBtns();
  }
  function chooseVer(id, vi) {
    var e = byId[id]; if (!e) return;
    var wasPlaying = playing && playing.eid === id;
    verSel[id] = vi;
    if (wasPlaying) stopAll();
    var i = shown.indexOf(e); if (i >= 0) rerenderOne(i);
    if (dlg.open && shown[cur] === e) fillSnd(e);
    if (wasPlaying) playToggle(id);
  }

  function onListClick(ev) {
    var row = ev.target.closest("[data-i]"); if (!row) return;
    var i = +row.dataset.i;
    if (ev.target.matches('input[type="checkbox"]')) { toggle(shown[i].id, ev.target.checked); return; }
    var vb = ev.target.closest(".vers button"); if (vb) { chooseVer(vb.dataset.id, +vb.dataset.ver); return; }
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
    var n = selected.size;
    $("selCount").textContent = n + "개 고름";
    $("selZip").disabled = n === 0;
    $("selClear").disabled = n === 0;
    $("selbar").hidden = n === 0;
    $("selbarCount").textContent = n + "개 고름";
  }
  $("selAll").onclick = function () { shown.forEach(function (e) { selected.add(e.id); }); render(); };
  $("selClear").onclick = $("selClear2").onclick = function () { selected.clear(); render(); };
  $("selZip").onclick = $("selZip2").onclick = function () {
    var es = all.filter(function (e) { return selected.has(e.id); });
    if (es.length > 80 && !confirm(es.length + "개는 용량이 커서 오래 걸릴 수 있어요. 계속할까요?")) return;
    zip(es, "dugun-assets-선택-" + es.length + "개.zip");
  };
  $("kindZip").onclick = function () {
    var es = all.filter(function (e) { return inKind(e, kind) && !folded(e); });
    zip(es, "dugun-assets-" + kind + ".zip");
  };

  function zip(es, name) {
    if (!es.length) return;
    if (typeof JSZip === "undefined") { alert("ZIP으로 묶지 못했어요. 하나씩 받아 주세요."); return; }
    var files = uniqFiles(es);
    var z = new JSZip(), done = 0, fail = 0;
    var box = $("progress");
    $("pTitle").textContent = "받을 준비 중… (파일 " + files.length + "개)";
    $("pFill").style.width = "0%"; $("pText").textContent = "0 / " + files.length;
    box.hidden = false;
    z.file("출처_LICENSE.txt", "그림 · 소리: 두근두근러닝(greatsong), CC BY-NC 4.0 — https://github.com/greatsong/dugun-assets\n" +
      "비상업 목적으로 쓸 수 있고, 쓸 때는 위 출처를 밝혀 주세요.\nhttps://creativecommons.org/licenses/by-nc/4.0/deed.ko\n");
    var chain = Promise.resolve();
    files.forEach(function (f) {
      chain = chain.then(function () {
        return fetch(f).then(function (r) { if (!r.ok) throw 0; return r.blob(); })
          .then(function (b) { z.file(f, b); }, function () { fail++; })
          .then(function () {
            done++;
            $("pFill").style.width = Math.round(done / files.length * 100) + "%";
            $("pText").textContent = done + " / " + files.length;
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
      if (fail) alert(fail + "개를 받지 못했어요. 잠시 뒤 다시 해 보세요.");
    }).catch(function () { box.hidden = true; alert("ZIP으로 묶지 못했어요."); });
  }

  /* ── 크게 보기 ── */
  var dlg = $("view");
  function metaHTML(rows) {
    return rows.filter(function (r) { return r[1] !== "" && r[1] != null; }).map(function (r) {
      var more = r[3] ? '<details class="more"><summary>잰 값 보기</summary><p>' + esc(r[3]) + "</p></details>" : "";
      return "<dt>" + r[0] + "</dt><dd" + (r[2] ? ' class="' + r[2] + '"' : "") + ">" + esc(r[1]) + more + "</dd>";
    }).join("");
  }
  /* 이어 틀기: 쉬운 한 줄 + 잰 값(목록의 loop_note)은 접어 둔다 */
  function loopLine(e, c) {
    if (c.loop) return "끝없이 이어 틀어도 이음매가 매끄러워요.";
    if ((e.versions || []).some(function (v) { return v.loop; })) return "한 번 듣고 끝나는 곡이에요. 계속 틀려면 '반복용'을 고르세요.";
    return e.kind === "효과음" ? "한 번 울리고 끝나요." : "한 번 듣고 끝나는 곡이에요.";
  }
  function fillSnd(e) {
    var c = curVer(e), f = c.files;
    $("v-imgpane").hidden = true; $("v-sndpane").hidden = false;
    $("v-sndkind").textContent = e.kind + (e.style ? " · " + e.style : "") + (c.label ? " · " + c.label : "");
    $("v-sndlen").textContent = secs(c.length);
    var vs = vers(e);
    $("v-vers").hidden = !vs; $("v-vers").innerHTML = vs ? versHTML(e).replace(/^<div class="vers"[^>]*>/, "").replace(/<\/div>$/, "") : "";
    $("v-vernote").hidden = !c.title; $("v-vernote").textContent = c.title ? c.label + " 버전 · " + c.title + (c.desc && c.desc !== c.title ? " — " + c.desc : "") : "";
    var w = $("v-wave"); w.innerHTML = waveHTML(c.id); w.dataset.id = e.id;
    $("v-loopcall").hidden = !c.loop;
    var longer = all.find(function (x) { return (x.source_ids || []).indexOf(e.id) >= 0; });
    var jump = e.loop_of ? ["원곡 보기 →", e.loop_of] : (e.source_ids && e.source_ids.length && byId[e.source_ids[0]]) ? ["원래 곡 보기 →", e.source_ids[0]]
      : longer ? ["늘린 판(길이별 · 반복용) 보기 →", longer.id] : (e.loop_version && !vs ? ["끊김 없이 되풀이하는 반복용 버전 보기 →", e.loop_version] : null);
    $("v-jump").hidden = !jump;
    if (jump) { $("v-jump").textContent = jump[0]; $("v-jump").dataset.id = jump[1]; }
    var dl = $("v-dl"); dl.href = f.m4a; dl.setAttribute("download", base(f.m4a));
    dl.innerHTML = ICON.dl + "M4A 받기" + (c.bytes ? " · " + mb(c.bytes) : "");
    var d2 = $("v-dl2"); d2.hidden = !f.mp3;
    if (f.mp3) { d2.href = f.mp3; d2.setAttribute("download", base(f.mp3)); d2.innerHTML = ICON.dl + "MP3 받기" + (c.mp3_bytes ? " · " + mb(c.mp3_bytes) : ""); }
    var sr = c.ent || e;
    $("v-meta").innerHTML = metaHTML([
      ["종류", e.kind + (e.style ? " · " + e.style : "")],
      ["길이", secs(c.length) + (vs ? " (" + vs.map(function (v) { return v.label + " " + secs(v.length); }).join(" · ") + ")" : "")],
      ["빠르기 · 조", [e.tempo ? "♩=" + e.tempo : "", e.key || ""].filter(Boolean).join(" · ")],
      ["상태", sr.status || ""],
      ["쓰인 영상", used(e)],
      ["상황", e.situation || ""],
      ["분위기", e.mood || ""],
      ["소리 섞기", e.mix_db != null ? "목소리와 함께 쓸 때는 소리를 " + Math.abs(e.mix_db) + " dB쯤 줄이면 알맞아요." : ""],
      ["이어 틀기", loopLine(e, c), "", sr.loop_note && sr.loop_note.length > 40 ? sr.loop_note : ""],
      ["만든 방법", c.made_by || sr.made_by || ""],
      ["파일 이름", c.file, "mono"]
    ]);
    $("v-pwrap").hidden = true; $("v-vars").hidden = true;
    setBtns(); setProgress(0, !(playing && playing.eid === e.id));
  }
  function fillImg(e) {
    $("v-sndpane").hidden = true; $("v-imgpane").hidden = false;
    var img = $("v-img");
    img.src = thumb(e); img.alt = e.title;
    var full = new Image();
    full.onload = function () { if (shown[cur] === e) img.src = e.file; };
    full.src = e.file;
    var dl = $("v-dl");
    dl.href = e.file; dl.setAttribute("download", base(e.file));
    dl.innerHTML = ICON.dl + "다운로드 · " + base(e.file).split(".").pop().toUpperCase() + " · " + mb(e.size.bytes);
    $("v-dl2").hidden = true;
    $("v-meta").innerHTML = metaHTML([
      ["종류", e.kind], ["찾는 낱말", (e.tags || []).join(", ")], ["크기", e.size.w + " × " + e.size.h + " 픽셀 · " + mb(e.size.bytes)],
      ["그린 도구", e.tool || "기록 없음"], ["쓰인 영상", (e.used_in || []).join(", ") || "—"], ["파일 이름", e.file, "mono"]
    ]);
    var p = e.prompt || "기록 없음";
    $("v-prompt").textContent = p;
    $("v-pwrap").hidden = p === "기록 없음"; $("v-pwrap").open = false;
    $("v-copy").textContent = "복사";
    var vs = e.variant_of ? all.filter(function (x) { return x.variant_of === e.variant_of; }) : [];
    $("v-vars").hidden = vs.length < 2;
    $("v-varlist").innerHTML = vs.map(function (x) {
      return '<li><button type="button" data-id="' + esc(x.id) + '" aria-label="' + esc(x.title) + '"' + (x.id === e.id ? ' aria-current="true"' : "") +
        '><img src="' + thumb(x) + '" alt="" loading="lazy"></button></li>';
    }).join("");
  }
  function open(i) {
    if (i < 0 || i >= shown.length) return;
    cur = i;
    var e = shown[i];
    $("v-title").textContent = e.title;
    var kc = $("v-kindchip"); kc.className = "kchip " + kcls(e.kind); kc.textContent = e.kind + (e.style ? " · " + e.style : "");
    $("v-sel").checked = selected.has(e.id);
    if (isSnd(e)) fillSnd(e); else fillImg(e);
    $("v-prev").hidden = i === 0; $("v-next").hidden = i === shown.length - 1;
    history.replaceState(null, "", "#" + e.id);
    if (!dlg.open) { dlg.showModal(); try { $("v-close").focus({ preventScroll: true }); } catch (x) {} }
    dlg.querySelector(".v-in").scrollTop = 0; dlg.querySelector(".v-info").scrollTop = 0;
  }
  function close() { dlg.close(); }
  dlg.addEventListener("close", function () { history.replaceState(null, "", location.pathname + location.search); });
  $("v-close").onclick = close;
  $("v-prev").onclick = function () { open(cur - 1); };
  $("v-next").onclick = function () { open(cur + 1); };
  $("v-sel").onchange = function () { toggle(shown[cur].id, this.checked); };
  $("v-play").onclick = function () { if (shown[cur]) playToggle(shown[cur].id); };
  $("v-vers").onclick = function (ev) { var b = ev.target.closest("button"); if (b) chooseVer(b.dataset.id, +b.dataset.ver); };
  $("v-jump").onclick = function () {
    var id = this.dataset.id, i = shown.findIndex(function (e) { return e.id === id; });
    if (i < 0) { kind = "전체"; $("q").value = ""; buildKinds(); render(); i = shown.findIndex(function (e) { return e.id === id; }); }
    open(i);
  };
  dlg.addEventListener("click", function (ev) { if (ev.target === dlg) close(); });
  dlg.addEventListener("keydown", function (ev) {
    if (ev.target.tagName === "INPUT" && ev.target.type !== "checkbox") return;
    if (ev.key === "ArrowLeft") { ev.preventDefault(); open(cur - 1); }
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
    var ok = function () { btn.textContent = "복사했어요"; };
    if (navigator.clipboard && window.isSecureContext) navigator.clipboard.writeText(t).then(ok, fallback);
    else fallback();
    function fallback() {
      var ta = document.createElement("textarea"); ta.value = t; document.body.appendChild(ta); ta.select();
      try { document.execCommand("copy"); ok(); } catch (e) { btn.textContent = "복사하지 못했어요"; }
      ta.remove();
    }
  };
})();
