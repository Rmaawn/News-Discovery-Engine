/* ==========================================================================
   News Discovery Engine — Dashboard UI logic
   مدیریت تم (دارک/لایت)، منوی موبایل و رندر نمودارها
   ========================================================================== */

(function () {
  "use strict";

  /* ---------- مدیریت تم ---------- */
  const THEME_KEY = "nde-theme";

  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem(THEME_KEY, theme); } catch (e) {}
    const sun = document.getElementById("icon-sun");
    const moon = document.getElementById("icon-moon");
    if (sun && moon) {
      sun.style.display = theme === "dark" ? "block" : "none";
      moon.style.display = theme === "dark" ? "none" : "block";
    }
  }

  function initTheme() {
    let theme = "light";
    try { theme = localStorage.getItem(THEME_KEY) || "light"; } catch (e) {}
    applyTheme(theme);
    const btn = document.getElementById("theme-toggle");
    if (btn) {
      btn.addEventListener("click", function () {
        const current = document.documentElement.getAttribute("data-theme");
        applyTheme(current === "dark" ? "light" : "dark");
        // نمودارها را با رنگ‌های تم جدید دوباره بساز
        if (window.__renderCharts) window.__renderCharts();
      });
    }
  }

  /* ---------- منوی موبایل ---------- */
  function initSidebar() {
    const sidebar = document.getElementById("sidebar");
    const toggle = document.getElementById("menu-toggle");
    const backdrop = document.getElementById("sidebar-backdrop");
    if (!sidebar || !toggle) return;

    function open() { sidebar.classList.add("open"); backdrop.classList.add("show"); }
    function close() { sidebar.classList.remove("open"); backdrop.classList.remove("show"); }

    toggle.addEventListener("click", function () {
      sidebar.classList.contains("open") ? close() : open();
    });
    if (backdrop) backdrop.addEventListener("click", close);
  }

  /* ---------- ابزار رنگ برای نمودارها ---------- */
  function cssVar(name) {
    return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  }

  /* ---------- رندر نمودارها ---------- */
  let charts = [];

  function destroyCharts() {
    charts.forEach(function (c) { try { c.destroy(); } catch (e) {} });
    charts = [];
  }

  function commonOptions() {
    const grid = cssVar("--border");
    const text = cssVar("--muted");
    return {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          labels: { color: text, font: { family: "Vazirmatn", size: 12 }, usePointStyle: true, padding: 16 },
        },
        tooltip: {
          rtl: true,
          bodyFont: { family: "Vazirmatn" },
          titleFont: { family: "Vazirmatn" },
          backgroundColor: cssVar("--surface-2"),
          titleColor: cssVar("--text"),
          bodyColor: cssVar("--text-2"),
          borderColor: grid, borderWidth: 1, padding: 12, cornerRadius: 10,
        },
      },
      scales: {
        x: { grid: { color: grid, drawBorder: false }, ticks: { color: text, font: { family: "Vazirmatn", size: 11 } } },
        y: { grid: { color: grid, drawBorder: false }, ticks: { color: text, font: { family: "Vazirmatn", size: 11 }, precision: 0 }, beginAtZero: true },
      },
    };
  }

  function renderCharts() {
    const dataEl = document.getElementById("charts-data");
    if (!dataEl || typeof Chart === "undefined") return;

    let d;
    try { d = JSON.parse(dataEl.textContent); } catch (e) { return; }

    destroyCharts();

    const accent = cssVar("--accent") || "#4f46e5";
    const success = cssVar("--success") || "#10b981";
    const warning = cssVar("--warning") || "#f59e0b";
    const danger = cssVar("--danger") || "#ef4444";
    const info = cssVar("--info") || "#3b82f6";
    const purple = "#7c3aed";
    const palette = [accent, success, warning, info, purple, danger];
    const faLabels = d.labels.map(toFaDate);

    // ۱) انتشار روزانه (خطی)
    const c1 = document.getElementById("chart-daily");
    if (c1) {
      const ctx = c1.getContext("2d");
      const grad = ctx.createLinearGradient(0, 0, 0, 300);
      grad.addColorStop(0, hexA(accent, 0.35));
      grad.addColorStop(1, hexA(accent, 0));
      charts.push(new Chart(ctx, {
        type: "line",
        data: { labels: faLabels, datasets: [{
          label: "انتشار موفق", data: d.per_day, borderColor: accent,
          backgroundColor: grad, fill: true, tension: 0.4, borderWidth: 2.5,
          pointRadius: 3, pointBackgroundColor: accent, pointHoverRadius: 5,
        }] },
        options: commonOptions(),
      }));
    }

    // ۲) خبر هر خبرگزاری (میله‌ای)
    const c2 = document.getElementById("chart-sources");
    if (c2) {
      charts.push(new Chart(c2, {
        type: "bar",
        data: { labels: d.per_source.map(function (s) { return s.name; }),
          datasets: [{ label: "تعداد مقاله", data: d.per_source.map(function (s) { return s.value; }),
            backgroundColor: d.per_source.map(function (_, i) { return hexA(palette[i % palette.length], 0.85); }),
            borderRadius: 8, borderSkipped: false }] },
        options: Object.assign(commonOptions(), { plugins: { legend: { display: false }, tooltip: commonOptions().plugins.tooltip } }),
      }));
    }

    // ۳) نرخ موفقیت انتشار (دونات)
    const c3 = document.getElementById("chart-publish-rate");
    if (c3) {
      const p = d.publish_success_rate;
      charts.push(new Chart(c3, {
        type: "doughnut",
        data: { labels: ["موفق", "ناموفق", "در انتظار"],
          datasets: [{ data: [p.success, p.failed, p.pending],
            backgroundColor: [success, danger, warning], borderWidth: 0, hoverOffset: 6 }] },
        options: doughnutOptions(),
      }));
    }

    // ۴) نرخ موفقیت AI (دونات)
    const c4 = document.getElementById("chart-ai-rate");
    if (c4) {
      const a = d.ai_success_rate;
      charts.push(new Chart(c4, {
        type: "doughnut",
        data: { labels: ["بازنویسی‌شده", "در انتظار"],
          datasets: [{ data: [a.rewritten, a.pending],
            backgroundColor: [accent, warning], borderWidth: 0, hoverOffset: 6 }] },
        options: doughnutOptions(),
      }));
    }

    // ۵) انتشار هر پلتفرم (میله‌ای)
    const c5 = document.getElementById("chart-platforms");
    if (c5) {
      charts.push(new Chart(c5, {
        type: "bar",
        data: { labels: d.per_platform.map(function (p) { return p.name; }),
          datasets: [{ data: d.per_platform.map(function (p) { return p.value; }),
            backgroundColor: [hexA(info, 0.85), hexA(purple, 0.85), hexA(warning, 0.85)],
            borderRadius: 8, borderSkipped: false }] },
        options: Object.assign(commonOptions(), { plugins: { legend: { display: false }, tooltip: commonOptions().plugins.tooltip } }),
      }));
    }

    // ۶) روند رشد سیستم (خطی تجمعی)
    const c6 = document.getElementById("chart-growth");
    if (c6) {
      const ctx = c6.getContext("2d");
      const grad = ctx.createLinearGradient(0, 0, 0, 300);
      grad.addColorStop(0, hexA(purple, 0.3));
      grad.addColorStop(1, hexA(purple, 0));
      charts.push(new Chart(ctx, {
        type: "line",
        data: { labels: faLabels, datasets: [{
          label: "مجموع مقالات", data: d.cumulative, borderColor: purple,
          backgroundColor: grad, fill: true, tension: 0.4, borderWidth: 2.5,
          pointRadius: 0, pointHoverRadius: 5 }] },
        options: commonOptions(),
      }));
    }
  }

  function doughnutOptions() {
    const text = cssVar("--muted");
    return {
      responsive: true, maintainAspectRatio: false, cutout: "68%",
      plugins: {
        legend: { position: "bottom", labels: { color: text, font: { family: "Vazirmatn", size: 12 }, usePointStyle: true, padding: 14 } },
        tooltip: commonOptions().plugins.tooltip,
      },
    };
  }

  /* ---------- ابزارها ---------- */
  function hexA(hex, alpha) {
    hex = (hex || "").replace("#", "");
    if (hex.length === 3) hex = hex.split("").map(function (c) { return c + c; }).join("");
    const r = parseInt(hex.substr(0, 2), 16) || 0;
    const g = parseInt(hex.substr(2, 2), 16) || 0;
    const b = parseInt(hex.substr(4, 2), 16) || 0;
    return "rgba(" + r + "," + g + "," + b + "," + alpha + ")";
  }

  const FA_DIGITS = ["۰", "۱", "۲", "۳", "۴", "۵", "۶", "۷", "۸", "۹"];
  function toFa(str) { return String(str).replace(/[0-9]/g, function (d) { return FA_DIGITS[d]; }); }

  function toFaDate(iso) {
    // iso: YYYY-MM-DD → روز/ماه شمسی کوتاه
    const parts = String(iso).split("-");
    if (parts.length !== 3) return iso;
    const j = gregorianToJalali(+parts[0], +parts[1], +parts[2]);
    return toFa(j[2] + "/" + j[1]);
  }

  function gregorianToJalali(gy, gm, gd) {
    const g_d_m = [0, 31, 59, 90, 120, 151, 181, 212, 243, 273, 304, 334];
    let gy2 = gy - 1600, gm2 = gm - 1, gd2 = gd - 1;
    let gDayNo = 365 * gy2 + Math.floor((gy2 + 3) / 4) - Math.floor((gy2 + 99) / 100) + Math.floor((gy2 + 399) / 400);
    gDayNo += g_d_m[gm2] + gd2;
    if (gm2 > 1 && ((gy % 4 === 0 && gy % 100 !== 0) || gy % 400 === 0)) gDayNo += 1;
    let jDayNo = gDayNo - 79;
    const jNp = Math.floor(jDayNo / 12053);
    jDayNo %= 12053;
    let jy = 979 + 33 * jNp + 4 * Math.floor(jDayNo / 1461);
    jDayNo %= 1461;
    if (jDayNo >= 366) { jy += Math.floor((jDayNo - 1) / 365); jDayNo = (jDayNo - 1) % 365; }
    let jm, jd;
    if (jDayNo < 186) { jm = 1 + Math.floor(jDayNo / 31); jd = 1 + (jDayNo % 31); }
    else { jm = 7 + Math.floor((jDayNo - 186) / 30); jd = 1 + ((jDayNo - 186) % 30); }
    return [jy, jm, jd];
  }

  window.__renderCharts = renderCharts;

  document.addEventListener("DOMContentLoaded", function () {
    initTheme();
    initSidebar();
    renderCharts();
  });
})();
