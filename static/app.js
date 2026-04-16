(function () {
  "use strict";

  const form        = document.getElementById("searchForm");
  const btnText     = document.getElementById("btnText");
  const btnSpinner  = document.getElementById("btnSpinner");
  const searchBtn   = document.getElementById("searchBtn");

  const resultSec   = document.getElementById("resultSection");
  const errorSec    = document.getElementById("errorSection");
  const errorMsg    = document.getElementById("errorMsg");

  const metaShow    = document.getElementById("metaShow");
  const metaCode    = document.getElementById("metaCode");
  const metaTitle   = document.getElementById("metaTitle");
  const scriptText  = document.getElementById("scriptText");
  const copyBtn     = document.getElementById("copyBtn");
  const sourceLink  = document.getElementById("sourceLink");

  function setLoading(on) {
    searchBtn.disabled = on;
    btnText.textContent = on ? "불러오는 중..." : "스크립트 가져오기";
    btnSpinner.classList.toggle("hidden", !on);
  }

  function showError(msg) {
    resultSec.classList.add("hidden");
    errorSec.classList.remove("hidden");
    errorMsg.textContent = msg;
  }

  function showResult(data) {
    errorSec.classList.add("hidden");

    metaShow.textContent  = data.show || "";
    metaCode.textContent  = data.episode_code || "";
    metaTitle.textContent = data.episode_title || "";

    if (data.source_url) {
      sourceLink.href = data.source_url;
      sourceLink.style.display = "";
    } else {
      sourceLink.style.display = "none";
    }

    scriptText.textContent = data.script;
    resultSec.classList.remove("hidden");

    // Scroll to result
    resultSec.scrollIntoView({ behavior: "smooth", block: "start" });
  }

  form.addEventListener("submit", async function (e) {
    e.preventDefault();

    const show    = document.getElementById("show").value.trim();
    const season  = document.getElementById("season").value.trim();
    const episode = document.getElementById("episode").value.trim();

    if (!show || !episode) return;

    setLoading(true);
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
      setLoading(false);
    }
  });

  copyBtn.addEventListener("click", function () {
    const text = scriptText.textContent;
    if (!text) return;

    navigator.clipboard.writeText(text).then(function () {
      copyBtn.textContent = "복사됨!";
      setTimeout(function () { copyBtn.textContent = "복사"; }, 1800);
    }).catch(function () {
      // Fallback for non-HTTPS
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
