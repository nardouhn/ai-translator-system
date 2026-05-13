/**
 * @file translation-dashboard.js
 * Domain pie chart (pure Canvas, no Chart.js) + log filter/search
 */
(function () {
  "use strict";

  // Bảng màu giống phong cách cũ
  const PALETTE = [
    "#00d4aa",
    "#3b82f6",
    "#f59e0b",
    "#a78bfa",
    "#ef4444",
    "#06b6d4",
    "#84cc16",
    "#f97316",
  ];

  // Biến lưu trạng thái hover (tùy chọn)
  let currentHoveredSlice = null;
  let canvas, ctx, chartData, chartLabels, chartColors;
  let centerX, centerY, radius, cutoutRadius;

  // =========================== PIE / DOUGHNUT RENDER ===========================

  /**
   * Vẽ doughnut chart với lỗ ở giữa (cutout)
   * @param {string} canvasId - id của canvas
   * @param {Array} labels - mảng nhãn
   * @param {Array} counts - mảng giá trị
   * @param {Array} colors - mảng màu (tùy chọn)
   */
  function drawDoughnutChart(canvasId, labels, counts, colors = PALETTE) {
    canvas = document.getElementById(canvasId);
    if (!canvas) return;
    ctx = canvas.getContext("2d");

    chartLabels = labels;
    chartData = counts;
    chartColors = colors.slice();

    // Kích thước canvas (responsive)
    const container = canvas.parentElement;
    const size = Math.min(container.clientWidth, 240);
    canvas.width = size;
    canvas.height = size;
    canvas.style.width = `${size}px`;
    canvas.style.height = `${size}px`;

    centerX = size / 2;
    centerY = size / 2;
    radius = size * 0.4; // 40% bán kính
    cutoutRadius = radius * 0.65; // lỗ giữa 65% (giống cutout:65%)

    drawSlices();

    // Thêm sự kiện hover (tùy chọn để hiển thị tooltip đơn giản)
    canvas.removeEventListener("mousemove", onCanvasMouseMove);
    canvas.addEventListener("mousemove", onCanvasMouseMove);
    canvas.removeEventListener("mouseleave", onCanvasMouseLeave);
    canvas.addEventListener("mouseleave", onCanvasMouseLeave);
  }

  // Vẽ tất cả các phần
  function drawSlices(hoverIndex = -1) {
    if (!ctx) return;
    const total = chartData.reduce((a, b) => a + b, 0);
    if (total === 0) return;

    let startAngle = -Math.PI / 2; // bắt đầu từ 12 giờ
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    for (let i = 0; i < chartData.length; i++) {
      const angle = (chartData[i] / total) * Math.PI * 2;
      const endAngle = startAngle + angle;

      // Chọn màu: nếu đang hover thì tô sáng hơn
      let fillColor = chartColors[i % chartColors.length];
      if (hoverIndex === i) {
        fillColor = lightenColor(fillColor, 20);
      }

      ctx.beginPath();
      ctx.fillStyle = fillColor;
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, startAngle, endAngle);
      ctx.fill();

      // Vẽ viền trắng phân cách
      ctx.save();
      ctx.strokeStyle = "#ffffff";
      ctx.lineWidth = 1.5;
      ctx.beginPath();
      ctx.moveTo(centerX, centerY);
      ctx.arc(centerX, centerY, radius, startAngle, endAngle);
      ctx.lineTo(centerX, centerY);
      ctx.stroke();
      ctx.restore();

      startAngle = endAngle;
    }

    // Vẽ lỗ tròn ở giữa (cutout)
    ctx.beginPath();
    ctx.fillStyle = "#ffffff"; // nền trắng *hoặc* màu nền card, tuỳ chỉnh
    ctx.arc(centerX, centerY, cutoutRadius, 0, Math.PI * 2);
    ctx.fill();

    // Vẽ viền trong cho lỗ
    ctx.beginPath();
    ctx.strokeStyle = "#e2e8f0";
    ctx.lineWidth = 1;
    ctx.arc(centerX, centerY, cutoutRadius, 0, Math.PI * 2);
    ctx.stroke();

    // Nếu muốn hiển thị tooltip tạm thời khi hover
    if (hoverIndex !== -1 && chartLabels[hoverIndex]) {
      showSimpleTooltip(
        hoverIndex,
        chartLabels[hoverIndex],
        chartData[hoverIndex],
      );
    } else {
      hideSimpleTooltip();
    }
  }

  // Làm sáng màu (cho hiệu ứng hover)
  function lightenColor(color, percent) {
    // Hỗ trợ hex ngắn/dài đơn giản
    const hex = color.replace("#", "");
    let r, g, b;
    if (hex.length === 3) {
      r = parseInt(hex[0] + hex[0], 16);
      g = parseInt(hex[1] + hex[1], 16);
      b = parseInt(hex[2] + hex[2], 16);
    } else {
      r = parseInt(hex.substring(0, 2), 16);
      g = parseInt(hex.substring(2, 4), 16);
      b = parseInt(hex.substring(4, 6), 16);
    }
    r = Math.min(255, r + (r * percent) / 100);
    g = Math.min(255, g + (g * percent) / 100);
    b = Math.min(255, b + (b * percent) / 100);
    return `rgb(${r}, ${g}, ${b})`;
  }

  // ======================== TOOLTIP ĐƠN GIẢN ========================
  let tooltipDiv = null;
  function ensureTooltipDiv() {
    if (!tooltipDiv) {
      tooltipDiv = document.createElement("div");
      tooltipDiv.className = "tdb-pie-tooltip";
      tooltipDiv.style.position = "fixed";
      tooltipDiv.style.backgroundColor = "#0d1220";
      tooltipDiv.style.border = "1px solid #1e2d45";
      tooltipDiv.style.color = "#e2e8f0";
      tooltipDiv.style.fontFamily = "'IBM Plex Mono', monospace";
      tooltipDiv.style.fontSize = "11px";
      tooltipDiv.style.padding = "6px 10px";
      tooltipDiv.style.borderRadius = "6px";
      tooltipDiv.style.pointerEvents = "none";
      tooltipDiv.style.zIndex = "1000";
      tooltipDiv.style.whiteSpace = "nowrap";
      document.body.appendChild(tooltipDiv);
    }
  }
  function showSimpleTooltip(index, label, value) {
    ensureTooltipDiv();
    tooltipDiv.textContent = `${label}: ${value} requests`;
    tooltipDiv.style.display = "block";
    // Vị trí sẽ được cập nhật trong sự kiện mousemove
  }
  function hideSimpleTooltip() {
    if (tooltipDiv) tooltipDiv.style.display = "none";
  }
  function updateTooltipPosition(e) {
    if (tooltipDiv && tooltipDiv.style.display === "block") {
      tooltipDiv.style.left = e.clientX + 15 + "px";
      tooltipDiv.style.top = e.clientY - 30 + "px";
    }
  }

  // Xử lý hover trên canvas
  function onCanvasMouseMove(e) {
    if (!canvas || !chartData) return;
    const rect = canvas.getBoundingClientRect();
    const scaleX = canvas.width / rect.width;
    const scaleY = canvas.height / rect.height;
    const mouseX = (e.clientX - rect.left) * scaleX;
    const mouseY = (e.clientY - rect.top) * scaleY;

    const angle = Math.atan2(mouseY - centerY, mouseX - centerX);
    let startAngle = -Math.PI / 2;
    const total = chartData.reduce((a, b) => a + b, 0);
    if (total === 0) return;

    let hovered = -1;
    for (let i = 0; i < chartData.length; i++) {
      const sliceAngle = (chartData[i] / total) * Math.PI * 2;
      const endAngle = startAngle + sliceAngle;
      // Kiểm tra xem mouse có nằm trong góc phần tư không
      // Và còn kiểm tra khoảng cách từ tâm (trong vòng radius và ngoài cutoutRadius)
      const dist = Math.hypot(mouseX - centerX, mouseY - centerY);
      if (dist >= cutoutRadius && dist <= radius) {
        if (angle >= startAngle && angle <= endAngle) {
          hovered = i;
          break;
        }
      }
      startAngle = endAngle;
    }

    if (hovered !== currentHoveredSlice) {
      currentHoveredSlice = hovered;
      drawSlices(currentHoveredSlice);
      if (hovered !== -1) {
        updateTooltipPosition(e);
      }
    } else if (hovered !== -1) {
      updateTooltipPosition(e);
    }
  }

  function onCanvasMouseLeave() {
    currentHoveredSlice = null;
    drawSlices(-1);
    hideSimpleTooltip();
  }

  // =========================== LOG FILTER (giữ nguyên) ===========================
  function initLogFilter() {
    const searchEl = document.getElementById("logSearch");
    const statusEl = document.getElementById("logStatusFilter");
    const typeEl = document.getElementById("logTypeFilter");
    const table = document.getElementById("logTable");
    if (!table) return;

    function filterRows() {
      const q = (searchEl?.value || "").toLowerCase();
      const status = (statusEl?.value || "").toLowerCase();
      const type = (typeEl?.value || "").toLowerCase();

      table.querySelectorAll("tbody .tdb-log-row").forEach((row) => {
        const text = row.textContent.toLowerCase();
        const rowSt = (row.dataset.status || "").toLowerCase();
        const rowType = (row.dataset.type || "").toLowerCase();

        const matchQ = !q || text.includes(q);
        const matchSt = !status || rowSt === status;
        const matchTy = !type || rowType === type;

        row.style.display = matchQ && matchSt && matchTy ? "" : "none";
      });
    }

    searchEl?.addEventListener("input", filterRows);
    statusEl?.addEventListener("change", filterRows);
    typeEl?.addEventListener("change", filterRows);
  }

  // =========================== KHỞI TẠO ===========================
  document.addEventListener("DOMContentLoaded", function () {
    initLogFilter();

    const d = window.tdbChartData;
    if (!d || !d.domain_labels || !d.domain_counts) return;

    // Vẽ doughnut chart thủ công
    drawDoughnutChart("chartDomain", d.domain_labels, d.domain_counts, PALETTE);

    // Xử lý resize (tuỳ chọn, đơn giản)
    window.addEventListener("resize", function () {
      if (canvas && chartData) {
        drawDoughnutChart("chartDomain", chartLabels, chartData, PALETTE);
      }
    });
  });

  // =========================== MODAL ERROR (giữ nguyên) ===========================
  window.tdbShowError = function (msg) {
    const modalBody = document.getElementById("tdbModalBody");
    const modal = document.getElementById("tdbModal");
    if (modalBody) modalBody.textContent = msg;
    if (modal) modal.style.display = "flex";
  };

  window.tdbCloseModal = function () {
    const modal = document.getElementById("tdbModal");
    if (modal) modal.style.display = "none";
  };

  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape") window.tdbCloseModal();
  });

  const modal = document.getElementById("tdbModal");
  if (modal) {
    modal.addEventListener("click", function (e) {
      if (e.target === this) window.tdbCloseModal();
    });
  }
})();
