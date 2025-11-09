// Static/js/horcsv.js
(() => {
  const $ = (id) => document.getElementById(id);

  // DOM 元素
  const fileInput = $('fileInput');
  const btnChoose = $('btnChoose');
  const btnClean = $('btnClean');
  const uploadDropzone = $('uploadDropzone');
  const encodingSelect = $('encodingSelect');
  const separatorInput = $('separatorInput');
  const caseSelect = $('caseSelect');
  const cleanColumnsCheckbox = $('cleanColumnsCheckbox');
  const stripSpecialCheckbox = $('stripSpecialCheckbox');
  const cleanCellsCheckbox = $('cleanCellsCheckbox');
  const removeDuplicatesCheckbox = $('removeDuplicatesCheckbox');
  const normalizeStringsCheckbox = $('normalizeStringsCheckbox');
  const roundDecimalsCheckbox = $('roundDecimalsCheckbox');
  const scaleNumericCheckbox = $('scaleNumericCheckbox');
  const formatPercentCheckbox = $('formatPercentCheckbox');
  const formatDatesCheckbox = $('formatDatesCheckbox');
  const fillMissingCheckbox = $('fillMissingCheckbox');
  const handleOutliersCheckbox = $('handleOutliersCheckbox');
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
  const statusEl = $('statusMessage');
  const fileNameEl = $('fileName');
  const fileNameText = fileNameEl?.querySelector('span');
  const diffStatusEl = $('diffStatus');
  const diffCreatedFiles = $('diffCreatedFiles');
  const cleanDownloadWrap = $('cleanDownload');
  const cleanDownloadLink = $('cleanDownloadLink');

  let currentFile = null;

  function setCurrentFile(file) {
    currentFile = file || null;

    if (fileInput) {
      if (currentFile) {
        try {
          const dataTransfer = new DataTransfer();
          dataTransfer.items.add(currentFile);
          fileInput.files = dataTransfer.files;
        } catch (err) {
          // Older browsers may not support programmatic assignment; ignore.
        }
      } else {
        fileInput.value = '';
      }
    }

    if (currentFile) {
      if (fileNameText) {
        fileNameText.textContent = currentFile.name;
      }
      if (fileNameEl) {
        fileNameEl.style.display = 'inline-flex';
      }
    } else {
      if (fileNameText) {
        fileNameText.textContent = '';
      }
      if (fileNameEl) {
        fileNameEl.style.display = 'none';
      }
    }
  }

  function syncColumnControls() {
    const enabled = !!cleanColumnsCheckbox?.checked;
    if (caseSelect) {
      caseSelect.disabled = !enabled;
    }
    if (stripSpecialCheckbox) {
      stripSpecialCheckbox.disabled = !enabled;
    }
  }

  if (cleanColumnsCheckbox) {
    cleanColumnsCheckbox.addEventListener('change', syncColumnControls);
    syncColumnControls();
  }
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


  function resetCleanDownload() {
    if (cleanDownloadWrap) {
      cleanDownloadWrap.style.display = 'none';
    }
    if (cleanDownloadLink) {
      cleanDownloadLink.removeAttribute('href');
      cleanDownloadLink.removeAttribute('download');
      cleanDownloadLink.textContent = '下载清洗后的文件';
    }
  }

  function showCleanDownload(url, filename) {
    if (!cleanDownloadWrap || !cleanDownloadLink || !url) return;
    cleanDownloadLink.href = url;
    const displayName = filename || 'cleaned.csv';
    cleanDownloadLink.textContent = `下载清洗后的文件 (${displayName})`;
    cleanDownloadLink.setAttribute('download', displayName);
    cleanDownloadWrap.style.display = 'inline-flex';
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

  async function parseJsonResponse(resp) {
    const contentType = resp.headers?.get?.('content-type') || '';

    if (contentType.includes('application/json')) {
      return resp.json();
    }

    const text = await resp.text();
    const trimmed = (text || '').trim();
    const looksHtml = /^<!doctype html/i.test(trimmed) || /^<html/i.test(trimmed);

    if (looksHtml) {
      const hint = resp.status === 404
        ? '请确认接口地址是否正确'
        : '请确认已登录并检查服务器日志';
      return {
        ok: false,
        error: `服务器返回 HTML 响应 (HTTP ${resp.status})：${hint}`
      };
    }

    if (!trimmed) {
      return {
        ok: resp.ok,
        error: `HTTP ${resp.status}`
      };
    }

    try {
      return JSON.parse(trimmed);
    } catch (err) {
      return {
        ok: false,
        error: trimmed || `HTTP ${resp.status}`
      };
    }
  }

  // 选择文件按钮
  btnChoose?.addEventListener('click', () => fileInput?.click());

  uploadDropzone?.addEventListener('click', () => fileInput?.click());

  if (uploadDropzone) {
    const activateDropzone = (event) => {
      event.preventDefault();
      event.stopPropagation();
      uploadDropzone.classList.add('active');
    };

    const deactivateDropzone = (event) => {
      event.preventDefault();
      event.stopPropagation();
      uploadDropzone.classList.remove('active');
    };

      ['dragenter', 'dragover'].forEach((evtName) => {
      uploadDropzone.addEventListener(evtName, activateDropzone);
    });

    ['dragleave', 'dragend'].forEach((evtName) => {
      uploadDropzone.addEventListener(evtName, deactivateDropzone);
    });

    uploadDropzone.addEventListener('drop', (event) => {
      event.preventDefault();
      event.stopPropagation();
      uploadDropzone.classList.remove('active');

      const file = event.dataTransfer?.files?.[0];
      if (file) {
        setCurrentFile(file);
        setStatus('');
        resetCleanDownload();
      }
    });
  }

  // 文件选择事件
  fileInput?.addEventListener('change', () => {
    setCurrentFile(fileInput.files?.[0] || null);
    setStatus('');
    resetCleanDownload();
  });

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
      const cleanColumns = cleanColumnsCheckbox?.checked ?? true;
      const stripSpecial = cleanColumns && (stripSpecialCheckbox?.checked ?? true);
      const cleanCells = cleanCellsCheckbox?.checked ?? true;
      const removeDuplicates = removeDuplicatesCheckbox?.checked ?? true;
      const normalizeStrings = normalizeStringsCheckbox?.checked ?? true;
      const roundDecimals = roundDecimalsCheckbox?.checked ?? true;
      const scaleNumeric = scaleNumericCheckbox?.checked ?? false;
      const formatPercentages = formatPercentCheckbox?.checked ?? false;
      const formatDates = formatDatesCheckbox?.checked ?? true;
      const fillMissing = fillMissingCheckbox?.checked ?? true;
      const handleOutliers = handleOutliersCheckbox?.checked ?? false;

      params.append('case', caseValue);
      params.append('clean_columns', cleanColumns ? 'true' : 'false');
      params.append('strip_special', stripSpecial ? 'true' : 'false');
      params.append('clean_cells', cleanCells ? 'true' : 'false');
      params.append('normalize_strings', normalizeStrings ? 'true' : 'false');
      params.append('round_decimals', roundDecimals ? 'true' : 'false');
      params.append('scale_numeric', scaleNumeric ? 'true' : 'false');
      params.append('format_percentages', formatPercentages ? 'true' : 'false');
      params.append('format_dates', formatDates ? 'true' : 'false');
      params.append('fill_missing', fillMissing ? 'true' : 'false');
      params.append('handle_outliers', handleOutliers ? 'true' : 'false');
      params.append('remove_duplicates', removeDuplicates ? 'true' : 'false');

      const encoding = encodingSelect?.value;
      if (encoding) {
        params.append('encoding', encoding);
      }

      const separator = separatorInput?.value?.trim();
      if (separator) {
        params.append('sep', separator);
      }

      setStatus('清洗数据中...', 'info');
      resetCleanDownload();
      btnClean.disabled = true;

      const resp = await fetch(`/api/csv/clean?${params.toString()}`, {
        method: 'POST',
        body: fd
      });

      const data = await resp.json();

      if (!resp.ok || !data.ok) {
        throw new Error(data.error || `HTTP ${resp.status}`);
      }

      const cleanedRows = data.cleaned_rows ?? 0;
      const removedDuplicates = data.removed_duplicates ?? 0;
      const steps = Array.isArray(data.applied_steps) ? data.applied_steps : [];

      if (steps.length) {
        const parts = [`清洗完成：${cleanedRows} 行`];
        if (steps.includes('重复行去重')) {
          parts.push(`移除重复 ${removedDuplicates} 行`);
        }
        parts.push(`执行步骤：${steps.join('、')}`);
        setStatus(parts.join('，'), 'success');
      } else {
        setStatus(`未执行任何清洗步骤，${cleanedRows} 行数据保持不变`, 'info');
      }

      if (data.download_url) {
        showCleanDownload(data.download_url, data.output_filename);
      }
    } catch (e) {
      console.error(e);
      setStatus(`清洗失败：${e.message}`, 'error');
      resetCleanDownload();
    } finally {
      if (btnClean) {
        btnClean.disabled = false;
      }
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

      const payloadEntries = Array.from(fd.entries());
      const sendRequest = async (url) => {
        const body = new FormData();
        payloadEntries.forEach(([key, value]) => body.append(key, value));
        const resp = await fetch(url, {
          method: 'POST',
          body
        });
        const data = await parseJsonResponse(resp);
        return { resp, data };
      };

      setDiffStatus('生成差异中，请稍候...', 'info');
      if (btnDiffHighlight) btnDiffHighlight.disabled = true;
      if (btnDiffReport) btnDiffReport.disabled = true;

      let { resp, data } = await sendRequest(endpoint);

      const fallbackEndpoint = endpoint.includes('-')
        ? endpoint.replace(/-/g, '_')
        : endpoint;

      const needsFallback =
        resp.status === 404 &&
        fallbackEndpoint !== endpoint &&
        (!data?.ok) &&
        (!data?.error || /not\s+found/i.test(data.error));

      if (needsFallback) {
        console.warn(`API route ${endpoint} missing, retrying as ${fallbackEndpoint}`);
        ({ resp, data } = await sendRequest(fallbackEndpoint));
      }

      if (!resp.ok || !data?.ok) {
        const message = data?.error || `HTTP ${resp.status}`;
        throw new Error(message);
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
