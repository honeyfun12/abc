(function () {
  "use strict";

  // ── DOM refs ──────────────────────────────────────────────────────────────
  const form          = document.getElementById("searchForm");
  const btnText       = document.getElementById("btnText");
  const btnSpinner    = document.getElementById("btnSpinner");
  const searchBtn     = document.getElementById("searchBtn");

  const resultSec     = document.getElementById("resultSection");
  const errorSec      = document.getElementById("errorSection");
  const errorMsg      = document.getElementById("errorMsg");

  const metaShow      = document.getElementById("metaShow");
  const metaCode      = document.getElementById("metaCode");
  const metaTitle     = document.getElementById("metaTitle");
  const scriptText    = document.getElementById("scriptText");
  const copyBtn       = document.getElementById("copyBtn");
  const sourceLink    = document.getElementById("sourceLink");

  const tabs          = document.querySelectorAll(".tab");
  const paneScript    = document.getElementById("paneScript");
  const paneAnalysis  = document.getElementById("paneAnalysis");

  const analyzeBtn         = document.getElementById("analyzeBtn");
  const analyzeBtnText     = document.getElementById("analyzeBtnText");
  const analyzeBtnSpinner  = document.getElementById("analyzeBtnSpinner");
  const analysisCount      = document.getElementById("analysisCount");
  const analysisStatus     = document.getElementById("analysisStatus");
  const analysisItems      = document.getElementById("analysisItems");

  // ── State ─────────────────────────────────────────────────────────────────
  let currentScript = "";
  let currentShow   = "";
  let analysisReady = false;   // true after analysis completes at least once

  // ── Type labels (Korean) ──────────────────────────────────────────────────
  const TYPE_LABELS = {
    slang:      "슬랭",
    idiom:      "숙어",
    culture:    "문화",
    person:     "인물",
    company:    "기업/기관",
    place:      "지명",
    vocabulary: "단어",
    social:     "계층/사회",
  };

  // ── Helpers ───────────────────────────────────────────────────────────────
  function setSearchLoading(on) {
    searchBtn.disabled = on;
    btnText.textContent = on ? "불러오는 중..." : "스크립트 가져오기";
    btnSpinner.classList.toggle("hidden", !on);
  }

  function showError(msg) {
    resultSec.classList.add("hidden");
    errorSec.classList.remove("hidden");
    errorMsg.textContent = msg;
  }

  function setTab(name) {
    tabs.forEach(function (t) {
      t.classList.toggle("tab--active", t.dataset.tab === name);
    });
    paneScript.classList.toggle("hidden",   name !== "script");
    paneAnalysis.classList.toggle("hidden", name !== "analysis");
  }

  function showResult(data) {
    errorSec.classList.add("hidden");

    metaShow.textContent  = data.show || "";
    metaCode.textContent  = data.episode_code || "";
    metaTitle.textContent = data.episode_title || "";

    sourceLink.style.display = data.source_url ? "" : "none";
    if (data.source_url) sourceLink.href = data.source_url;

    scriptText.textContent = data.script;
    currentScript = data.script;
    currentShow   = data.show || "";

    // Reset analysis pane for the new script
    analysisReady = false;
    analysisItems.innerHTML = "";
    analysisCount.classList.add("hidden");
    analysisStatus.classList.add("hidden");
    analyzeBtn.disabled = false;
    analyzeBtnText.textContent = "AI 분석 시작";
    analyzeBtnSpinner.classList.add("hidden");

    resultSec.classList.remove("hidden");
    setTab("script");
    resultSec.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  function buildCard(item) {
    const type = (item.type || "").toLowerCase();
    const label = TYPE_LABELS[type] || type;

    const card = document.createElement("div");
    card.className = "analysis-card";

    const top = document.createElement("div");
    top.className = "card-top";

    const term = document.createElement("span");
    term.className = "card-term";
    term.textContent = item.term || "";

    const badge = document.createElement("span");
    badge.className = "type-badge type-" + type;
    badge.textContent = label;

    top.appendChild(term);
    top.appendChild(badge);

    const orig = document.createElement("div");
    orig.className = "card-original";
    orig.textContent = item.original_line || "";

    const expl = document.createElement("div");
    expl.className = "card-explanation";
    expl.textContent = item.explanation || "";

    card.appendChild(top);
    card.appendChild(orig);
    card.appendChild(expl);
    return card;
  }

  function setAnalyzeLoading(on) {
    analyzeBtn.disabled = on;
    analyzeBtnText.textContent = on ? "분석 중..." : "AI 분석 시작";
    analyzeBtnSpinner.classList.toggle("hidden", !on);
  }

  function showAnalysisStatus(msg) {
    analysisStatus.textContent = msg;
    analysisStatus.classList.remove("hidden");
  }

  function hideAnalysisStatus() {
    analysisStatus.classList.add("hidden");
  }

  // ── SSE analysis stream ───────────────────────────────────────────────────
  function runAnalysis() {
    if (!currentScript) return;
    if (analyzeBtn.disabled) return;

    setAnalyzeLoading(true);
    analysisItems.innerHTML = "";
    analysisCount.classList.add("hidden");
    showAnalysisStatus("Claude가 스크립트를 분석 중입니다. 1~2분 소요될 수 있습니다...");

    fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ script: currentScript, show: currentShow }),
    }).then(function (resp) {
      if (!resp.ok) {
        return resp.json().then(function (d) {
          throw new Error(d.error || "서버 오류가 발생했습니다.");
        });
      }

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      function readChunk() {
        reader.read().then(function (result) {
          if (result.done) {
            setAnalyzeLoading(false);
            return;
          }

          buf += decoder.decode(result.value, { stream: true });

          // Process complete SSE lines
          const parts = buf.split("\n\n");
          buf = parts.pop(); // keep incomplete last part

          parts.forEach(function (part) {
            const line = part.trim();
            if (!line.startsWith("data: ")) return;
            const json_str = line.slice(6);
            let evt;
            try { evt = JSON.parse(json_str); } catch (e) { return; }

            if (evt.type === "progress") {
              showAnalysisStatus(evt.msg || "분석 중...");

            } else if (evt.type === "done") {
              hideAnalysisStatus();
              setAnalyzeLoading(false);
              analysisReady = true;

              const items = evt.items || [];
              if (items.length === 0) {
                showAnalysisStatus("영국식 표현을 찾지 못했습니다. (미국 드라마일 수 있습니다)");
                return;
              }
              items.forEach(function (item) {
                analysisItems.appendChild(buildCard(item));
              });
              analysisCount.textContent = "총 " + items.length + "개 항목";
              analysisCount.classList.remove("hidden");
              analyzeBtnText.textContent = "다시 분석";

            } else if (evt.type === "error") {
              hideAnalysisStatus();
              setAnalyzeLoading(false);
              showAnalysisStatus("오류: " + (evt.msg || "알 수 없는 오류"));
            }
          });

          readChunk();
        }).catch(function (err) {
          setAnalyzeLoading(false);
          showAnalysisStatus("연결 오류: " + err.message);
        });
      }

      readChunk();
    }).catch(function (err) {
      setAnalyzeLoading(false);
      showAnalysisStatus("오류: " + err.message);
    });
  }

  // ── Event listeners ───────────────────────────────────────────────────────
  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      setTab(tab.dataset.tab);
    });
  });

  analyzeBtn.addEventListener("click", runAnalysis);

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const show    = document.getElementById("show").value.trim();
    const season  = document.getElementById("season").value.trim();
    const episode = document.getElementById("episode").value.trim();
    if (!show || !episode) return;

    setSearchLoading(true);
    resultSec.classList.add("hidden");
    errorSec.classList.add("hidden");

    try {
      const resp = await fetch("/api/script", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ show, season, episode }),
      });
      const data = await resp.json();

      if (!resp.ok || data.error) {
        showError(data.error || "알 수 없는 오류가 발생했습니다.");
      } else if (!data.script) {
        showError("스크립트를 찾을 수 없습니다. 제목·시즌·에피소드를 확인해 보세요.");
      } else {
        showResult(data);
      }
    } catch (err) {
      showError("서버 연결에 실패했습니다: " + err.message);
    } finally {
      setSearchLoading(false);
    }
  });

  copyBtn.addEventListener("click", function () {
    const text = scriptText.textContent;
    if (!text) return;
    navigator.clipboard.writeText(text).then(function () {
      copyBtn.textContent = "복사됨!";
      setTimeout(function () { copyBtn.textContent = "복사"; }, 1800);
    }).catch(function () {
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      copyBtn.textContent = "복사됨!";
      setTimeout(function () { copyBtn.textContent = "복사"; }, 1800);
    });
  });
})();
