document.addEventListener('DOMContentLoaded', () => {
    // -----------------------------------------
    // Theme Toggling
    // -----------------------------------------
    const themeBtn = document.getElementById('theme-toggle');
    const root = document.documentElement;

    if (themeBtn) {
        const isDark = localStorage.getItem('theme') === 'dark';
        if (isDark) {
            root.setAttribute('data-theme', 'dark');
            themeBtn.innerHTML = '<i class="fas fa-sun"></i>';
        }

        themeBtn.addEventListener('click', () => {
            if (root.getAttribute('data-theme') === 'dark') {
                root.removeAttribute('data-theme');
                localStorage.setItem('theme', 'light');
                themeBtn.innerHTML = '<i class="fas fa-moon"></i>';
            } else {
                root.setAttribute('data-theme', 'dark');
                localStorage.setItem('theme', 'dark');
                themeBtn.innerHTML = '<i class="fas fa-sun"></i>';
            }
        });
    }

    // -----------------------------------------
    // Sidebar Mobile Toggle
    // -----------------------------------------
    const menuToggle = document.getElementById('menu-toggle');
    const sidebar = document.querySelector('.sidebar');
    if (menuToggle && sidebar) {
        menuToggle.addEventListener('click', () => {
            sidebar.classList.toggle('open');
        });
    }

    // -----------------------------------------
    // Guard: Only run homepage-specific logic
    // if the dashboard elements actually exist
    // -----------------------------------------
    const dashboard = document.getElementById('module-dashboard');
    const workspace = document.getElementById('processing-workspace');

    if (!dashboard || !workspace) {
        // Not on the homepage — stop here to avoid
        // null reference errors and unwanted scrollTo calls
        return;
    }

    // -----------------------------------------
    // Sidebar Navigation Click (homepage only)
    // -----------------------------------------
    document.querySelectorAll('.nav-item').forEach(item => {
        item.addEventListener('click', (e) => {
            e.preventDefault();
            document.querySelectorAll('.nav-item').forEach(nav => nav.classList.remove('active'));
            item.classList.add('active');
            
            const target = item.dataset.target;
            const pageTitle = document.getElementById('page-title');

            if (target === 'dashboard') {
                workspace.style.display = 'none';
                dashboard.style.display = 'block';
                if (pageTitle) pageTitle.textContent = "Dashboard";
                window.scrollTo({top: 0, behavior: 'smooth'});
            } else {
                workspace.style.display = 'none';
                dashboard.style.display = 'block';
                if (pageTitle) pageTitle.textContent = "Dashboard";
                const catHeader = document.getElementById('cat-' + target);
                if (catHeader) {
                    const y = catHeader.getBoundingClientRect().top + window.scrollY - 80;
                    window.scrollTo({top: y, behavior: 'smooth'});
                }
            }
            if (sidebar && window.innerWidth <= 900) {
                sidebar.classList.remove('open');
            }
        });
    });

    // -----------------------------------------
    // SPA / Workspace Navigation Logic
    // -----------------------------------------
    let currentModule = '';
    let currentAction = '';

    // Clicking a Tool Card
    document.querySelectorAll('.tool-card').forEach(card => {
        card.addEventListener('click', (e) => {
            // Don't interfere with links inside tool cards
            if (e.target.closest('a')) return;
            // Don't interfere with favorite buttons
            if (e.target.closest('.fav-btn')) return;

            currentModule = card.dataset.module;
            currentAction = card.dataset.action;
            const titleEl = card.querySelector('h4');
            if (titleEl) {
                openWorkspace(titleEl.textContent, currentAction);
            }
        });
    });

    // Back button
    const backBtn = document.getElementById('back-to-dash');
    if (backBtn) {
        backBtn.addEventListener('click', (e) => {
            e.preventDefault();
            workspace.style.display = 'none';
            dashboard.style.display = 'block';
            const pageTitle = document.getElementById('page-title');
            if (pageTitle) pageTitle.textContent = "Dashboard";
        });
    }

    // -----------------------------------------
    // File Upload & Progress Logic
    // -----------------------------------------
    const uploadZone = document.getElementById('upload-zone');
    const fileInput = document.getElementById('file-input');
    const progressArea = document.getElementById('progress-area');
    const resultArea = document.getElementById('result-area');
    const toolParams = document.getElementById('tool-parameters');

    if (!uploadZone || !fileInput) return;
    
    // Set Workspace Title & Prepare Params
    function openWorkspace(toolName, action) {
        dashboard.style.display = 'none';
        workspace.style.display = 'block';
        window.scrollTo({top: 0, behavior: 'smooth'});
        
        document.getElementById('workspace-title').textContent = toolName;
        currentAction = action;
        
        // Reset areas
        uploadZone.style.display = 'block';
        if (progressArea) progressArea.style.display = 'none';
        if (resultArea) resultArea.style.display = 'none';
        const textBox = document.getElementById('text-result-box');
        if (textBox) textBox.style.display = 'none';
        
        // Build Params based on specific actions
        if (toolParams) {
            toolParams.style.display = 'none';
            toolParams.innerHTML = '';
        
            if (action === 'protect' || action === 'unlock') {
                toolParams.style.display = 'block';
                toolParams.innerHTML = `<label>Password</label><br><input type="password" id="param-password" class="param-input" placeholder="Enter password..." style="width:100%; padding:10px; margin-top:5px; border-radius:5px; border:1px solid #ccc;">`;
            } else if (action === 'split' || action === 'remove-pages' || action === 'extract-pages') {
                toolParams.style.display = 'block';
                toolParams.innerHTML = `<label>Pages (e.g. 1, 3, 5)</label><br><input type="text" id="param-pages" class="param-input" placeholder="1, 3, 5" style="width:100%; padding:10px; margin-top:5px; border-radius:5px; border:1px solid #ccc;">`;
            } else if (action === 'organize') {
                toolParams.style.display = 'block';
                toolParams.innerHTML = `<label>Page Order (e.g. 2, 1, 3)</label><br><input type="text" id="param-pages" class="param-input" style="width:100%; padding:10px; margin-top:5px; border-radius:5px; border:1px solid #ccc;">`;
            } else if (action === 'rotate') {
                toolParams.style.display = 'block';
                toolParams.innerHTML = `<label>Angle (e.g. 90, 180, 270)</label><br><input type="number" id="param-angle" class="param-input" value="90" style="width:100%; padding:10px; margin-top:5px; border-radius:5px; border:1px solid #ccc;">`;
            } else if (action === 'add-watermark' || action === 'redact' || action === 'edit-pdf') {
                toolParams.style.display = 'block';
                toolParams.innerHTML = `<label>Text Content</label><br><input type="text" id="param-text" class="param-input" style="width:100%; padding:10px; margin-top:5px; border-radius:5px; border:1px solid #ccc;">`;
            } else if (action === 'translate') {
                toolParams.style.display = 'block';
                toolParams.innerHTML = `<label>Target Language</label><br><input type="text" id="param-language" class="param-input" value="Spanish" style="width:100%; padding:10px; margin-top:5px; border-radius:5px; border:1px solid #ccc;">`;
            } else if (action === 'chat') {
                toolParams.style.display = 'block';
                toolParams.innerHTML = `<label>Question</label><br><input type="text" id="param-question" class="param-input" placeholder="What is this document about?" style="width:100%; padding:10px; margin-top:5px; border-radius:5px; border:1px solid #ccc;">`;
            } else if (action === 'sign') {
                toolParams.style.display = 'block';
                toolParams.innerHTML = `<label>Password for PFX</label><br><input type="password" id="param-password" class="param-input" style="width:100%; padding:10px; margin-top:5px; border-radius:5px; border:1px solid #ccc;">`;
            }
        }
    }

    // Drag & Drop Listeners
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('drag-over');
    });

    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('drag-over');
    });

    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('drag-over');
        handleFiles(e.dataTransfer.files);
    });

    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    function showError(msg) {
        alert(msg);
    }

    function handleFiles(files) {
        if (!files || files.length === 0) return;
        
        let formData = new FormData();

        // Bind Dynamic Parameters
        const paramPwd = document.getElementById('param-password');
        const paramPgs = document.getElementById('param-pages');
        const paramTxt = document.getElementById('param-text');
        const paramAng = document.getElementById('param-angle');
        const paramLan = document.getElementById('param-language');
        const paramQry = document.getElementById('param-question');

        if (paramPwd) formData.append('password', paramPwd.value);
        if (paramPgs) formData.append('pages', paramPgs.value);
        if (paramTxt) formData.append('text', paramTxt.value);
        if (paramAng) formData.append('angle', paramAng.value);
        if (paramLan) formData.append('language', paramLan.value);
        if (paramQry) formData.append('question', paramQry.value);

        // Size Limit 50MB
        for (let i = 0; i < files.length; i++) {
            if (files[i].size > 50 * 1024 * 1024) {
                showError('File exceeds 50MB limit.');
                return;
            }
            formData.append('files[]', files[i]);
        }

        // Custom File Preview rendering
        const fileNamesHTML = Array.from(files).map(f => {
            if (f.type.startsWith('image/')) {
                return `<p><i class="fas fa-image text-primary"></i> ${f.name} <span class="text-muted">(${(f.size/1024/1024).toFixed(2)} MB)</span></p>`;
            } else if (f.type === 'application/pdf') {
                return `<p><i class="fas fa-file-pdf text-danger"></i> ${f.name} <span class="text-muted">(${(f.size/1024/1024).toFixed(2)} MB)</span></p>`;
            } else {
                return `<p><i class="fas fa-file text-secondary"></i> ${f.name} <span class="text-muted">(${(f.size/1024/1024).toFixed(2)} MB)</span></p>`;
            }
        }).join('');

        let progressMessage = document.getElementById('progress-message');
        if (!progressMessage && progressArea) {
            const h4 = progressArea.querySelector('h4');
            if (h4) {
                const previewDiv = document.createElement('div');
                previewDiv.id = "progress-message";
                previewDiv.style.margin = "1rem 0";
                previewDiv.style.textAlign = "left";
                previewDiv.style.background = "var(--bg-color)";
                previewDiv.style.padding = "1rem";
                previewDiv.style.borderRadius = "8px";
                h4.insertAdjacentElement('afterend', previewDiv);
                progressMessage = previewDiv;
            }
        }
        if (progressMessage) progressMessage.innerHTML = fileNamesHTML;

        uploadAndProcess(formData, currentAction);
    }

    function uploadAndProcess(formData, action) {
        uploadZone.style.display = 'none';
        if (toolParams && toolParams.innerHTML) toolParams.style.display = 'none';
        if (progressArea) progressArea.style.display = 'block';

        const dynamicEndpoint = '/api/' + action;

        const csrfMeta = document.querySelector('meta[name="csrf-token"]');
        const csrfToken = csrfMeta ? csrfMeta.getAttribute('content') : '';

        fetch(dynamicEndpoint, {
            method: 'POST',
            headers: {
                'X-CSRFToken': csrfToken
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (progressArea) progressArea.style.display = 'none';
            if (data.error) {
                showError(data.error);
                uploadZone.style.display = 'block';
                if (toolParams && toolParams.innerHTML) toolParams.style.display = 'block';
            } else if (data.success) {
                if (resultArea) resultArea.style.display = 'block';
                
                // Show text box if AI / OCR result
                if (data.text_result) {
                    const txtBox = document.getElementById('text-result-box');
                    if (txtBox) {
                        txtBox.style.display = 'block';
                        txtBox.innerHTML = '<pre style="white-space: pre-wrap; word-wrap: break-word;">' + data.text_result + '</pre>';
                    }
                }
                
                // Show Download if available
                const dbtn = document.getElementById('download-btn');
                if (dbtn) {
                    if (data.download_url) {
                        dbtn.style.display = 'inline-block';
                        dbtn.href = data.download_url;
                    } else {
                        dbtn.style.display = 'none';
                    }
                }
            }
        })
        .catch(err => {
            if (progressArea) progressArea.style.display = 'none';
            showError('An error occurred during communication with the server.');
            console.error(err);
            uploadZone.style.display = 'block';
            if (toolParams && toolParams.innerHTML) toolParams.style.display = 'block';
        });
    }

});
