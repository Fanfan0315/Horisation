// Static/js/horcsv.js
(() => {
  const $ = (id) => document.getElementById(id);

  // DOM 元素
  const fileInput = $('fileInput');
  const btnChoose = $('btnChoose');
  const btnPreview = $('btnPreview');
  const btnSummary = $('btnSummary');
  const btnClean = $('btnClean');
  const btnFormat = $('btnFormat');
  const dropzone = $('dropzone');
  const rowsN = $('rowsN');
  const encodingSelect = $('encodingSelect');
  const separatorInput = $('separatorInput');
  const caseSelect = $('caseSelect');
  const formatMappingInput = $('formatMappingInput');
  const diffFile1Input = $('diffFile1Input');
  const diffFile2Input = $('diffFile2Input');
  const diffFile1Name = $('diffFile1Name');
  const diffFile2Name = $('diffFile2Name');
  const diffEncoding1 = $('diffEncoding1');
  const diffEncoding2 = $('diffEncoding2');
  const diffSeparator1 = $('diffSeparator1');
  const diffSeparator2 = $('diffSeparator2');
  const diffMappingInput = $('diffMappingInput');
  const btnDiffHighlight = $('btnDiffHighlight');
  const btnDiffReport = $('btnDiffReport');
  const columnsArea = $('columnsArea');
  const previewTable = $('previewTable');
  const statusEl = $('statusMessage');  // 修正：从 'status' 改为 'statusMessage'
  const fileNameEl = $('fileName');
  const resultSection = $('resultSection');
  const summaryCards = $('summaryCards');
  const summaryDetails = $('summaryDetails');
  const diffStatusEl = $('diffStatus');
  const diffCreatedFiles = $('diffCreatedFiles');

  let currentFile = null;

  // 工具函数
  function setStatus(msg, type = 'info') {
    if (!statusEl) return;
    statusEl.innerHTML = '';
    if (!msg) return;

    const badge = document.createElement('div');
    badge.className = `status-badge status-${type}`;
    badge.textContent = msg;
    statusEl.appendChild(badge);
  }

function setDiffStatus(msg, type = 'info') {
    if (!diffStatusEl) return;
    diffStatusEl.innerHTML = '';
    if (!msg) return;

    const badge = document.createElement('div');
    badge.className = `status-badge status-${type}`;
    badge.textContent = msg;
    diffStatusEl.appendChild(badge);
  }

  function renderCreatedFiles(files) {
    if (!diffCreatedFiles) return;
    diffCreatedFiles.innerHTML = '';
    (files || []).forEach(file => {
      const li = document.createElement('li');
      li.textContent = `📁 ${file}`;
      diffCreatedFiles.appendChild(li);
    });
  }

  function updateFileBadge(badgeEl, file) {
    if (!badgeEl) return;
    const span = badgeEl.querySelector('span');
    if (file) {
      if (span) span.textContent = file.name;
      badgeEl.style.display = 'inline-flex';
    } else {
      if (span) span.textContent = '';
      badgeEl.style.display = 'none';
    }
  }

  function appendIfValue(fd, key, value) {
    if (value) {
      fd.append(key, value);
    }
  }

  function stripBom(text) {
    return text.replace(/^\ufeff/, '');
  }

  function normalizeSmartPunctuation(text) {
    return text
      .replace(/[\u201C\u201D]/g, '"')
      .replace(/[\u2018\u2019]/g, "'")
      .replace(/[\uFF0C\u3001]/g, ',')
      .replace(/[\uFF1A]/g, ':');
  }

  function clampJsonEnvelope(text) {
    const startIdx = text.search(/[\[{]/);
    if (startIdx > 0) {
      text = text.slice(startIdx);
    }

    const lastArray = text.lastIndexOf(']');
    const lastObject = text.lastIndexOf('}');
    const endIdx = Math.max(lastArray, lastObject);
    if (endIdx >= 0 && endIdx < text.length - 1) {
      text = text.slice(0, endIdx + 1);
    }

    return text;
  }

  function buildMappingCandidates(text) {
    const candidates = [];
    const trimmed = clampJsonEnvelope(normalizeSmartPunctuation(stripBom(text.trim())));

    if (text) {
      candidates.push(text);
    }

    if (trimmed) {
      candidates.push(trimmed);

      const loweredBool = trimmed
        .replace(/\bTrue\b/g, 'true')
        .replace(/\bFalse\b/g, 'false')
        .replace(/\bNone\b/g, 'null');
      if (loweredBool !== trimmed) {
        candidates.push(loweredBool);
      }

      if (!trimmed.includes('"') && trimmed.includes("'")) {
        candidates.push(trimmed.replace(/'/g, '"'));
      }
    }

    return [...new Set(candidates.filter(Boolean))];
  }

  function getMappingPayload(inputEl, { required = false } = {}) {
    if (!inputEl) {
      if (required) {
        throw new Error('缺少映射输入区域');
      }
      return '';
    }

    const text = inputEl.value || '';
    if (!text) {
      if (required) {
        throw new Error('请提供映射配置（JSON 数组）');
      }
      return '';
    }

    let lastError = null;
    const candidates = buildMappingCandidates(text);

    for (const candidate of candidates) {
      try {
        const parsed = JSON.parse(candidate);
        if (!Array.isArray(parsed)) {
          throw new Error('映射配置必须是数组');
        }
        return JSON.stringify(parsed);
      } catch (err) {
        lastError = err;
      }
    }

    const message = lastError?.message || '未知错误';
    throw new Error(`映射配置 JSON 无效：${message}`);
  }


  function clearTable() {
    if (previewTable) previewTable.innerHTML = '';
  }

  function clearColumns() {
    if (columnsArea) columnsArea.innerHTML = '';
  }

  function showResultSection() {
    if (resultSection) {
      resultSection.style.display = 'block';
    }
  }

    async function parseJsonResponse(resp) {
    const contentType = resp.headers?.get?.('content-type') || '';

    if (contentType.includes('application/json')) {
      return resp.json();
    }

    const text = await resp.text();

    try {
      return JSON.parse(text);
    } catch (err) {
      const message = text?.trim();
      return {
        ok: false,
        error: message || `HTTP ${resp.status}`
      };
    }
  }

  // 渲染列标签（带类型颜色）
  function renderColumns(cols, dtypes = {}) {
    clearColumns();
    (cols || []).forEach(c => {
      const span = document.createElement('span');
      span.className = 'chip';

      // 根据数据类型添加样式
      const dtype = dtypes[c] || 'text';
      if (dtype === 'numeric') {
        span.classList.add('numeric');
      } else if (dtype === 'date') {
        span.classList.add('date');
      }

      span.textContent = c;
      columnsArea.appendChild(span);
    });
  }

  // 渲染表格
  function renderTable(cols, rows) {
    clearTable();
    if (!cols?.length) return;

    const thead = document.createElement('thead');
    const trh = document.createElement('tr');
    cols.forEach(c => {
      const th = document.createElement('th');
      th.textContent = c;
      trh.appendChild(th);
    });
    thead.appendChild(trh);

    const tbody = document.createElement('tbody');
    (rows || []).forEach(r => {
      const tr = document.createElement('tr');
      cols.forEach(c => {
        const td = document.createElement('td');
        let v = r[c];
        if (v === null || v === undefined) v = '';
        td.textContent = String(v);
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });

    previewTable.appendChild(thead);
    previewTable.appendChild(tbody);
  }

  // 渲染概要卡片
  function renderSummaryCards(summary) {
    if (!summaryCards) return;
    summaryCards.innerHTML = '';

    const cards = [
      { label: '总行数', value: summary.rows || 0 },
      { label: '总列数', value: summary.cols || 0 },
      { label: '缺失值', value: Object.values(summary.na_count || {}).reduce((a, b) => a + b, 0) }
    ];

    cards.forEach(card => {
      const div = document.createElement('div');
      div.className = 'summary-card';
      div.innerHTML = `
        <div class="summary-value">${card.value}</div>
        <div class="summary-label">${card.label}</div>
      `;
      summaryCards.appendChild(div);
    });
  }

  // 渲染概要详情
  function renderSummaryDetails(summary) {
    if (!summaryDetails) return;

    const lines = [];

    // 列名
    if (summary.columns) {
      lines.push(`<strong>列名：</strong>${summary.columns.join(', ')}`);
    }

    // 数据类型
    if (summary.dtypes) {
      const dtypesStr = Object.entries(summary.dtypes)
        .map(([col, type]) => `${col}: ${type}`)
        .join(', ');
      lines.push(`<strong>数据类型：</strong>${dtypesStr}`);
    }

    // 缺失值统计
    if (summary.na_count) {
      const naStr = Object.entries(summary.na_count)
        .filter(([_, count]) => count > 0)
        .map(([col, count]) => `${col}: ${count}`)
        .join(', ');
      if (naStr) {
        lines.push(`<strong>缺失值统计：</strong>${naStr}`);
      }
    }

    summaryDetails.innerHTML = lines.join('<br>');
  }

  // 选择文件按钮
  btnChoose?.addEventListener('click', () => fileInput?.click());

  // 文件选择事件
  fileInput?.addEventListener('change', () => {
    currentFile = fileInput.files?.[0] || null;
    if (currentFile) {
      fileNameEl.textContent = `📄 ${currentFile.name}`;
      fileNameEl.style.display = 'inline-flex';
    } else {
      fileNameEl.textContent = '';
      fileNameEl.style.display = 'none';
    }
    setStatus('');
    clearTable();
    clearColumns();
  });

  // 全局阻止拖拽默认行为
  ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(evt => {
    window.addEventListener(evt, (e) => {
      e.preventDefault();
      e.stopPropagation();
    });
  });

  // 拖拽上传
  if (dropzone) {
    let dragCounter = 0;

    dropzone.addEventListener('dragenter', () => {
      dragCounter++;
      dropzone.classList.add('dragover');
    });

    dropzone.addEventListener('dragover', (e) => {
      e.dataTransfer.dropEffect = 'copy';
    });

    dropzone.addEventListener('dragleave', () => {
      dragCounter = Math.max(0, dragCounter - 1);
      if (dragCounter === 0) {
        dropzone.classList.remove('dragover');
      }
    });

    dropzone.addEventListener('drop', (e) => {
      dragCounter = 0;
      dropzone.classList.remove('dragover');

      const files = e.dataTransfer?.files;
      if (!files || !files.length) return;

      const file = files[0];
      currentFile = file;

      try {
        // 同步到 file input
        const dt = new DataTransfer();
        dt.items.add(file);
        fileInput.files = dt.files;
      } catch (err) {
        console.warn('无法同步到 file input:', err);
      }

      fileNameEl.textContent = `📄 ${file.name}`;
      fileNameEl.style.display = 'inline-flex';
      setStatus('');
      clearTable();
      clearColumns();
    });
  }

    // diff 文件选择
  if (diffFile1Input) {
    diffFile1Input.addEventListener('change', () => {
      const file = diffFile1Input.files?.[0];
      updateFileBadge(diffFile1Name, file);
    });
  }

  if (diffFile2Input) {
    diffFile2Input.addEventListener('change', () => {
      const file = diffFile2Input.files?.[0];
      updateFileBadge(diffFile2Name, file);
    });
  }


  // 构建查询参数
  function buildQueryParams() {
    const params = new URLSearchParams();

    // 预览行数
    const n = Math.max(1, Math.min(2000, parseInt(rowsN?.value || '10', 10)));
    params.append('n', n);

    // 编码
    const encoding = encodingSelect?.value;
    if (encoding) {
      params.append('encoding', encoding);
    }

    // 分隔符
    const separator = separatorInput?.value?.trim();
    if (separator && separator !== ',') {
      params.append('sep', separator);
    }

    return params.toString();
  }

  // 预览按钮
  btnPreview?.addEventListener('click', async () => {
    try {
      if (!currentFile) {
        setStatus('请先选择文件', 'error');
        return;
      }

      const queryParams = buildQueryParams();
      const fd = new FormData();
      fd.append('file', currentFile, currentFile.name);

      setStatus('上传并解析中...', 'info');
      btnPreview.disabled = true;

      const resp = await fetch(`/api/csv/preview?${queryParams}`, {
        method: 'POST',
        body: fd
      });

      const data = await resp.json();

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
      }

      // 渲染结果
      renderColumns(data.columns || []);
      renderTable(data.columns || [], data.rows || []);
      showResultSection();

      setStatus(`预览完成：${(data.columns || []).length} 列，${(data.rows || []).length} 行`, 'success');
    } catch (e) {
      console.error(e);
      setStatus(`解析失败：${e.message}`, 'error');
    } finally {
      btnPreview.disabled = false;
    }
  });

  // 概要按钮
  btnSummary?.addEventListener('click', async () => {
    try {
      if (!currentFile) {
        setStatus('请先选择文件', 'error');
        return;
      }

      const queryParams = buildQueryParams();
      const fd = new FormData();
      fd.append('file', currentFile, currentFile.name);

      setStatus('计算概要统计中...', 'info');
      btnSummary.disabled = true;

      const resp = await fetch(`/api/csv/summary?${queryParams}`, {
        method: 'POST',
        body: fd
      });

      const data = await resp.json();

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
      }

      const summary = data.summary || {};

      // 渲染概要信息
      renderSummaryCards(summary);
      renderSummaryDetails(summary);
      renderColumns(summary.columns || [], summary.dtypes || {});
      showResultSection();

      // 切换到概要Tab
      document.querySelector('.tab[data-tab="summary"]')?.click();

      setStatus(`概要已生成`, 'success');
    } catch (e) {
      console.error(e);
      setStatus(`概要失败：${e.message}`, 'error');
    } finally {
      btnSummary.disabled = false;
    }
  });

  // 清洗按钮
  btnClean?.addEventListener('click', async () => {
    try {
      if (!currentFile) {
        setStatus('请先选择文件', 'error');
        return;
      }

      const fd = new FormData();
      fd.append('file', currentFile, currentFile.name);

      // 构建清洗参数
      const params = new URLSearchParams();
      const caseValue = caseSelect?.value || 'upper';
      params.append('case', caseValue);
      params.append('strip_special', 'true');
      params.append('remove_duplicates', 'true');

      setStatus('清洗数据中...', 'info');
      btnClean.disabled = true;

      const resp = await fetch(`/api/csv/clean?${params.toString()}`, {
        method: 'POST',
        body: fd
      });

      const data = await resp.json();

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
      }

      // 显示清洗结果
      const msg = `清洗完成：${data.cleaned_rows} 行，移除重复 ${data.removed_duplicates} 行`;
      setStatus(msg, 'success');

      // 显示清洗后的列名
      if (data.columns) {
        renderColumns(data.columns);
        showResultSection();
      }
    } catch (e) {
      console.error(e);
      setStatus(`清洗失败：${e.message}`, 'error');
    } finally {
      btnClean.disabled = false;
    }
  });

  // 格式化按钮
  btnFormat?.addEventListener('click', async () => {
    try {
      if (!currentFile) {
        setStatus('请先选择文件后再格式化', 'error');
        return;
      }

      let mappingPayload = '';
      try {
        mappingPayload = getMappingPayload(formatMappingInput, { required: false });
      } catch (err) {
        setStatus(err.message, 'error');
        return;
      }

      const fd = new FormData();
      fd.append('file', currentFile, currentFile.name);
      if (mappingPayload) {
        fd.append('mapping', mappingPayload);
      }

      appendIfValue(fd, 'encoding', encodingSelect?.value || '');
      const sep = separatorInput?.value?.trim();
      if (sep) {
        fd.append('sep', sep);
      }

      setStatus('格式化处理中...', 'info');
      btnFormat.disabled = true;

      const resp = await fetch('/api/csv/format', {
        method: 'POST',
        body: fd
      });

      const data = await resp.json();

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
      }

      renderColumns(data.columns || []);
      renderTable(data.columns || [], data.rows || []);
      showResultSection();

      const columnCount = (data.columns || []).length;
      const rowCount = (data.rows || []).length;
      setStatus(`格式化完成：${columnCount} 列，预览 ${rowCount} 行`, 'success');
    } catch (e) {
      console.error(e);
      setStatus(`格式化失败：${e.message}`, 'error');
    } finally {
      if (btnFormat) btnFormat.disabled = false;
    }
  });

  async function handleDiffRequest(endpoint) {
    try {
      setDiffStatus('', 'info');
      renderCreatedFiles([]);

      const file1 = diffFile1Input?.files?.[0];
      const file2 = diffFile2Input?.files?.[0];

      if (!file1 || !file2) {
        setDiffStatus('请同时选择 File 1 与 File 2', 'error');
        return;
      }

      let mappingPayload = '';
      try {
        mappingPayload = getMappingPayload(diffMappingInput, { required: true });
      } catch (err) {
        setDiffStatus(err.message, 'error');
        return;
      }

      const fd = new FormData();
      fd.append('file1', file1, file1.name);
      fd.append('file2', file2, file2.name);
      fd.append('mapping', mappingPayload);

      appendIfValue(fd, 'encoding1', diffEncoding1?.value || '');
      appendIfValue(fd, 'encoding2', diffEncoding2?.value || '');

      const sep1 = diffSeparator1?.value?.trim();
      if (sep1) {
        fd.append('sep1', sep1);
      }

      const sep2 = diffSeparator2?.value?.trim();
      if (sep2) {
        fd.append('sep2', sep2);
      }

      setDiffStatus('生成差异中，请稍候...', 'info');
      if (btnDiffHighlight) btnDiffHighlight.disabled = true;
      if (btnDiffReport) btnDiffReport.disabled = true;

      const resp = await fetch(endpoint, {
        method: 'POST',
        body: fd
      });

      const data = await resp.json();

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
      }

      const files = data.created_files || [];
      setDiffStatus(`生成成功：${files.length} 个输出文件`, 'success');
      renderCreatedFiles(files);
    } catch (e) {
      console.error(e);
      setDiffStatus(`生成失败：${e.message}`, 'error');
    } finally {
      if (btnDiffHighlight) btnDiffHighlight.disabled = false;
      if (btnDiffReport) btnDiffReport.disabled = false;
    }
  }

  btnDiffHighlight?.addEventListener('click', () => handleDiffRequest('/api/csv/diff-highlight'));
  btnDiffReport?.addEventListener('click', () => handleDiffRequest('/api/csv/diff-report'));


  console.log('✅ CSV 工作区已初始化');
})();
