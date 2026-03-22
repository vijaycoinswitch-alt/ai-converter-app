document.addEventListener('DOMContentLoaded', () => {
    // Theme toggling
    const themeToggle = document.getElementById('theme-toggle');
    const body = document.body;
    
    // Check saved theme
    if (localStorage.getItem('theme') === 'dark') {
        body.setAttribute('data-theme', 'dark');
        themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
    }
    
    themeToggle.addEventListener('click', () => {
        if (body.getAttribute('data-theme') === 'dark') {
            body.removeAttribute('data-theme');
            localStorage.setItem('theme', 'light');
            themeToggle.innerHTML = '<i class="fas fa-moon"></i>';
        } else {
            body.setAttribute('data-theme', 'dark');
            localStorage.setItem('theme', 'dark');
            themeToggle.innerHTML = '<i class="fas fa-sun"></i>';
        }
    });

    // Tool Selection & Workspace
    const toolsGrid = document.getElementById('tools-grid');
    const workspace = document.getElementById('workspace');
    const closeWorkspaceBtn = document.getElementById('close-workspace');
    const workspaceTitle = document.getElementById('workspace-title');
    const fileInput = document.getElementById('file-input');
    const uploadZone = document.getElementById('upload-zone');
    const progressArea = document.getElementById('progress-area');
    const resultArea = document.getElementById('result-area');
    const downloadBtn = document.getElementById('download-btn');
    const errorMsg = document.getElementById('error-msg');
    const progressText = document.getElementById('progress-text');
    
    let currentConversionType = '';

    if (toolsGrid) {
        document.querySelectorAll('.tool-card').forEach(card => {
            card.addEventListener('click', () => {
                currentConversionType = card.dataset.type;
                workspaceTitle.textContent = card.querySelector('h3').textContent;
                
                if (currentConversionType === 'merge-pdf') {
                    fileInput.multiple = true;
                    uploadZone.querySelector('p').textContent = 'Drag and drop multiple PDF files here';
                } else {
                    fileInput.multiple = false;
                    uploadZone.querySelector('p').textContent = 'Drag and drop your file here';
                }

                toolsGrid.style.display = 'none';
                workspace.style.display = 'block';
                resetWorkspace();
            });
        });
    }

    if (closeWorkspaceBtn) {
        closeWorkspaceBtn.addEventListener('click', () => {
            workspace.style.display = 'none';
            toolsGrid.style.display = 'grid';
            resetWorkspace();
        });
    }

    // Drag and Drop
    if (uploadZone) {
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, preventDefaults, false);
        });

        function preventDefaults(e) {
            e.preventDefault();
            e.stopPropagation();
        }

        ['dragenter', 'dragover'].forEach(eventName => {
            uploadZone.addEventListener(eventName, () => {
                uploadZone.classList.add('dragover');
            }, false);
        });

        ['dragleave', 'drop'].forEach(eventName => {
            uploadZone.addEventListener(eventName, () => {
                uploadZone.classList.remove('dragover');
            }, false);
        });

        uploadZone.addEventListener('drop', (e) => {
            let dt = e.dataTransfer;
            let files = dt.files;
            handleFiles(files);
        });

        uploadZone.addEventListener('click', () => {
            fileInput.click();
        });

        fileInput.addEventListener('change', function() {
            handleFiles(this.files);
        });
    }

    function handleFiles(files) {
        if (!files || files.length === 0) return;
        
        let formData = new FormData();
        formData.append('type', currentConversionType);

        if (currentConversionType === 'merge-pdf') {
            if (files.length < 2) {
                showError('Please select at least 2 files for merging.');
                return;
            }
            for (let i = 0; i < files.length; i++) {
                formData.append('files[]', files[i]);
            }
        } else {
            // Validation for size
            if (files[0].size > 50 * 1024 * 1024) {
                showError('File exceeds 50MB limit.');
                return;
            }
            formData.append('file', files[0]);
        }

        uploadAndConvert(formData);
    }

    function uploadAndConvert(formData) {
        uploadZone.style.display = 'none';
        progressArea.style.display = 'block';
        resultArea.style.display = 'none';
        errorMsg.style.display = 'none';
        errorMsg.textContent = '';
        progressText.textContent = 'Uploading and Converting... This may take a while.';

        fetch('/api/convert', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            progressArea.style.display = 'none';
            if (data.error) {
                showError(data.error);
                uploadZone.style.display = 'block';
            } else if (data.success) {
                resultArea.style.display = 'block';
                downloadBtn.href = data.download_url;
            }
        })
        .catch(error => {
            progressArea.style.display = 'none';
            uploadZone.style.display = 'block';
            showError('An error occurred during conversion.');
            console.error(error);
        });
    }

    function showError(message) {
        errorMsg.textContent = message;
        errorMsg.style.display = 'block';
        errorMsg.style.color = 'var(--danger)';
        errorMsg.style.marginTop = '1rem';
    }

    function resetWorkspace() {
        uploadZone.style.display = 'block';
        progressArea.style.display = 'none';
        resultArea.style.display = 'none';
        errorMsg.style.display = 'none';
        fileInput.value = '';
    }
});
