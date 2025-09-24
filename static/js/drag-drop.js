/**
 * MITS Cloud Drag and Drop Functionality
 * Provides comprehensive drag and drop support for file uploads and folder organization
 */

class DragDropManager {
    constructor() {
        this.dropZones = new Set();
        this.draggedElement = null;
        this.dragOverlay = null;
        this.uploadProgress = new Map();
        this.init();
    }

    init() {
        this.createDragOverlay();
        this.setupGlobalEventListeners();
        this.setupFileUploadDropZones();
    }

    createDragOverlay() {
        this.dragOverlay = document.createElement('div');
        this.dragOverlay.className = 'fixed inset-0 bg-blue-500 bg-opacity-20 border-4 border-dashed border-blue-500 z-50 pointer-events-none hidden';
        this.dragOverlay.innerHTML = `
            <div class="flex items-center justify-center h-full">
                <div class="bg-white rounded-lg p-8 shadow-xl text-center">
                    <div class="text-6xl mb-4">📁</div>
                    <div class="text-xl font-semibold text-blue-600">Drop files here to upload</div>
                    <div class="text-sm text-gray-500 mt-2">Release to upload files to MITS Cloud</div>
                </div>
            </div>
        `;
        document.body.appendChild(this.dragOverlay);
    }

    setupGlobalEventListeners() {
        // Prevent default drag behaviors on the entire document
        ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
            document.addEventListener(eventName, (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        // Show overlay when dragging files over the page
        document.addEventListener('dragenter', (e) => {
            if (this.isFileDrag(e)) {
                this.showDragOverlay();
            }
        });

        document.addEventListener('dragleave', (e) => {
            if (e.target === document.body || e.target === document.documentElement) {
                this.hideDragOverlay();
            }
        });

        document.addEventListener('drop', (e) => {
            this.hideDragOverlay();
            if (this.isFileDrag(e)) {
                this.handleGlobalFileDrop(e);
            }
        });
    }

    handleGlobalFileDrop(e) {
        e.preventDefault();
        e.stopPropagation();
        
        const files = Array.from(e.dataTransfer.files);
        if (files.length === 0) return;
        
        // Check if we're in a folder context
        const currentFolderId = window.driveCurrentFolderId || null;
        const session = document.getElementById('session')?.value;
        const department = document.getElementById('department')?.value;
        
        console.log('Global file drop - Current folder context:', {
            currentFolderId: currentFolderId,
            session: session,
            department: department,
            fileCount: files.length
        });
        
        if (!session || !department) {
            this.showToast('Please select session and department first', 'error');
            return;
        }
        
        // Use the existing upload functionality
        this.uploadFilesToDrive(files, null);
    }

    setupFileUploadDropZones() {
        // Find all file input elements and make their containers drop zones
        const fileInputs = document.querySelectorAll('input[type="file"]');
        fileInputs.forEach(input => {
            const container = input.closest('.bg-white, .bg-slate-50, .upload-zone');
            if (container) {
                this.addDropZone(container, input);
            }
        });

        // Add drop zones for specific upload areas
        const uploadAreas = document.querySelectorAll('.upload-area, .drive-grid, .faculty-files');
        uploadAreas.forEach(area => {
            this.addDropZone(area, null, 'upload');
        });

        // Setup enhanced grid drag and drop
        this.setupGridDragDrop();

        // Setup folder organization drag and drop
        this.setupFolderOrganization();
        
        // Setup multi-select functionality
        this.setupMultiSelect();
        
        // Setup global menu auto-close
        this.setupGlobalMenuClose();
    }

    setupGridDragDrop() {
        // Enhanced grid-specific drag and drop functionality
        const driveGrid = document.getElementById('drive-grid');
        if (driveGrid) {
            this.setupGridSorting(driveGrid);
            this.setupGridDropZones(driveGrid);
        }
    }

    setupGridSorting(grid) {
        // Enable sorting within the grid
        grid.addEventListener('dragover', (e) => {
            e.preventDefault();
            const afterElement = this.getDragAfterElement(grid, e.clientY);
            const dragging = document.querySelector('.dragging');
            
            if (afterElement == null) {
                grid.appendChild(dragging);
            } else {
                grid.insertBefore(dragging, afterElement);
            }
        });
    }

    setupGridDropZones(grid) {
        // Add visual drop zones between grid items
        grid.addEventListener('dragenter', (e) => {
            if (e.target === grid) {
                grid.classList.add('drag-over');
                this.showEmptyDropZone(grid);
            }
        });

        grid.addEventListener('dragleave', (e) => {
            if (!grid.contains(e.relatedTarget)) {
                grid.classList.remove('drag-over');
                this.hideEmptyDropZone(grid);
            }
        });
    }

    getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.folder-item:not(.dragging), .file-item:not(.dragging)')];
        
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }

    setupFolderOrganization() {
        // Make folder items draggable
        this.makeFoldersDraggable();
        
        // Setup drop targets for folders
        this.setupFolderDropTargets();
        
        // Setup file drag and drop to folders
        this.setupFileToFolderDragDrop();
    }

    makeFoldersDraggable() {
        // This will be called when folders are rendered
        const folderItems = document.querySelectorAll('.folder-item, [data-folder-id]');
        folderItems.forEach(item => {
            this.makeDraggable(item);
        });
    }

    makeDraggable(element) {
        element.draggable = true;
        element.classList.add('folder-item', 'grid-item-sortable');
        
        element.addEventListener('dragstart', (e) => {
            this.draggedElement = element;
            element.classList.add('dragging');
            
            const folderId = element.getAttribute('data-folder-id') || 
                           element.getAttribute('data-id') ||
                           element.id.replace('folder-', '');
            
            const folderName = element.querySelector('.font-medium')?.textContent || 'Unknown';
            
            console.log('Drag start - folder ID:', folderId, 'name:', folderName);
            
            const dragData = {
                type: 'folder',
                id: folderId,
                name: folderName
            };
            
            console.log('Setting drag data:', dragData);
            
            e.dataTransfer.setData('text/plain', JSON.stringify(dragData));
            e.dataTransfer.effectAllowed = 'move';
            
            // Add visual feedback
            this.showDragPreview(element);
        });
        
        element.addEventListener('dragend', (e) => {
            element.classList.remove('dragging');
            this.draggedElement = null;
            this.hideDragPreview();
        });
    }

    setupFolderDropTargets() {
        // Make folders drop targets for other folders
        const folderItems = document.querySelectorAll('.folder-item, [data-folder-id]');
        folderItems.forEach(item => {
            this.makeDropTarget(item);
        });
    }

    makeDropTarget(element) {
        element.addEventListener('dragover', (e) => {
            e.preventDefault();
            e.dataTransfer.dropEffect = 'move';
            this.highlightDropZone(element, true);
        });
        
        element.addEventListener('dragleave', (e) => {
            if (!element.contains(e.relatedTarget)) {
                this.highlightDropZone(element, false);
            }
        });
        
        element.addEventListener('drop', (e) => {
            e.preventDefault();
            this.highlightDropZone(element, false);
            
            try {
                // Check if files are being dropped from file system
                const files = e.dataTransfer.files;
                if (files && files.length > 0) {
                    console.log('Files dropped from file system:', files.length);
                    this.handleFileUploadToFolder(files, element);
                    return;
                }
                
                // Check if existing items are being moved within the system
                const rawData = e.dataTransfer.getData('text/plain');
                console.log('Raw drag data:', rawData);
                
                if (rawData) {
                    const data = JSON.parse(rawData);
                    console.log('Parsed drag data:', data);
                    
                    if (data.type === 'folder') {
                        console.log('Handling folder drop');
                        this.handleFolderMove(data, element);
                    } else if (data.type === 'file') {
                        console.log('Handling file drop');
                        this.handleFileMove(data, element);
                    } else {
                        console.warn('Unknown drag data type:', data.type);
                    }
                } else {
                    console.warn('No drag data found');
                }
            } catch (error) {
                console.error('Error handling drop:', error);
                this.showToast('Error processing drop operation', 'error');
            }
        });
    }

    setupFileToFolderDragDrop() {
        // Make files draggable to folders
        const fileItems = document.querySelectorAll('[data-file-id], .file-item');
        fileItems.forEach(item => {
            this.makeFileDraggable(item);
        });
    }

    makeFileDraggable(element) {
        element.draggable = true;
        element.classList.add('file-item', 'grid-item-sortable');
        
        element.addEventListener('dragstart', (e) => {
            this.draggedElement = element;
            element.classList.add('dragging');
            
            const fileId = element.getAttribute('data-file-id') || 
                          element.getAttribute('data-id') ||
                          element.id.replace('file-', '');
            
            // Check if this is part of a multi-select operation
            const selectedFiles = this.getSelectedFiles();
            const isMultiSelect = selectedFiles.length > 1;
            
            const dragData = {
                type: 'file',
                id: fileId,
                name: element.querySelector('.font-medium')?.textContent || 'Unknown',
                isRecursive: isMultiSelect,
                files: isMultiSelect ? selectedFiles : [{
                    id: fileId,
                    name: element.querySelector('.font-medium')?.textContent || 'Unknown',
                    element: element
                }]
            };
            
            e.dataTransfer.setData('text/plain', JSON.stringify(dragData));
            e.dataTransfer.effectAllowed = 'move';
            
            // Add visual feedback
            this.showDragPreview(element);
            
            // Multi-select drag detected
        });
        
        element.addEventListener('dragend', (e) => {
            element.classList.remove('dragging');
            this.draggedElement = null;
            this.hideDragPreview();
        });
    }

    async handleFolderMove(data, targetElement) {
        console.log('handleFolderMove called with:', { data, targetElement });
        
        const targetFolderId = targetElement.getAttribute('data-folder-id') || 
                              targetElement.getAttribute('data-id') ||
                              targetElement.id.replace('folder-', '');
        
        console.log('Target folder ID:', targetFolderId);
        
        if (data.id === targetFolderId) {
            this.showToast('Cannot move folder to itself', 'error');
            return;
        }
        
        // Validate required data
        if (!data.id) {
            this.showToast('Invalid folder data: missing folder ID', 'error');
            console.error('Missing folder ID in drag data:', data);
            return;
        }
        
        if (!targetFolderId) {
            this.showToast('Invalid target: could not determine target folder', 'error');
            console.error('Could not determine target folder ID from element:', targetElement);
            return;
        }
        
        // Validate the move operation
        const validation = this.validateFolderMove(data.id, targetFolderId);
        if (!validation.valid) {
            this.showToast(validation.reason, 'error');
            console.error('Move validation failed:', validation);
            return;
        }
        
        try {
            const formData = new FormData();
            formData.append('parent', targetFolderId);
            
            console.log('Sending PATCH request to:', `/api/folders/${data.id}/`);
            console.log('FormData contents:', Object.fromEntries(formData.entries()));
            
            // Check if CSRF token is available
            const csrfToken = this.getCsrfToken();
            if (!csrfToken) {
                throw new Error('CSRF token not found. Please refresh the page and try again.');
            }
            
            const response = await fetch(`/api/folders/${data.id}/`, {
                method: 'PATCH',
                body: formData,
                headers: { 
                    'X-CSRFToken': csrfToken,
                    'X-Requested-With': 'XMLHttpRequest'
                }
            });
            
            console.log('Response status:', response.status);
            console.log('Response headers:', Object.fromEntries(response.headers.entries()));
            
            if (response.ok) {
                const result = await response.json().catch(() => ({}));
                console.log('Move successful:', result);
                this.showToast(`Folder "${data.name}" moved successfully`, 'success');
                
                // Refresh the display
                if (typeof refreshDrive === 'function') refreshDrive();
                if (typeof loadFolderTree === 'function') loadFolderTree();
            } else {
                const errorText = await response.text();
                console.error('Move failed with status:', response.status);
                console.error('Error response:', errorText);
                
                let errorMessage = 'Move failed';
                try {
                    const errorJson = JSON.parse(errorText);
                    errorMessage = errorJson.detail || errorJson.message || errorMessage;
                } catch (e) {
                    errorMessage = errorText || errorMessage;
                }
                
                throw new Error(errorMessage);
            }
        } catch (error) {
            console.error('Exception in handleFolderMove:', error);
            
            // Handle specific error types
            if (error.name === 'TypeError' && error.message.includes('fetch')) {
                console.log('Fetch failed, trying XMLHttpRequest fallback...');
                try {
                    const result = await this.moveFolderWithXHR(data.id, targetFolderId);
                    if (result.success) {
                        this.showToast(`Folder "${data.name}" moved successfully`, 'success');
                        
                        // Refresh the display
                        if (typeof refreshDrive === 'function') refreshDrive();
                        if (typeof loadFolderTree === 'function') loadFolderTree();
                        return;
                    }
                } catch (xhrError) {
                    console.error('XMLHttpRequest also failed:', xhrError);
                    this.showToast('Network error: Unable to connect to server. Please check your connection and try again.', 'error');
                }
            } else if (error.message.includes('CSRF')) {
                this.showToast('Security error: Please refresh the page and try again.', 'error');
            } else {
                this.showToast(`Failed to move folder: ${error.message}`, 'error');
            }
        }
    }

    addDropZone(element, fileInput = null, type = 'file') {
        if (!element) return;

        element.classList.add('drag-drop-zone');
        element.setAttribute('data-drop-type', type);
        
        if (fileInput) {
            element.setAttribute('data-file-input', fileInput.id || fileInput.name);
        }

        // Add visual feedback classes
        element.classList.add('transition-all', 'duration-200');

        // Event listeners for drag and drop
        element.addEventListener('dragenter', (e) => this.handleDragEnter(e, element));
        element.addEventListener('dragover', (e) => this.handleDragOver(e, element));
        element.addEventListener('dragleave', (e) => this.handleDragLeave(e, element));
        element.addEventListener('drop', (e) => this.handleDrop(e, element));

        this.dropZones.add(element);
    }

    handleDragEnter(e, element) {
        e.preventDefault();
        e.stopPropagation();
        
        if (this.isFileDrag(e)) {
            element.classList.add('drag-over', 'bg-blue-50', 'border-blue-300', 'border-2', 'border-dashed');
            this.hideDragOverlay(); // Hide global overlay when over specific drop zone
        }
    }

    handleDragOver(e, element) {
        e.preventDefault();
        e.stopPropagation();
        
        if (this.isFileDrag(e)) {
            element.classList.add('drag-over');
        }
    }

    handleDragLeave(e, element) {
        e.preventDefault();
        e.stopPropagation();
        
        // Only remove drag-over class if we're actually leaving the element
        if (!element.contains(e.relatedTarget)) {
            element.classList.remove('drag-over', 'bg-blue-50', 'border-blue-300', 'border-2', 'border-dashed');
        }
    }

    handleDrop(e, element) {
        e.preventDefault();
        e.stopPropagation();
        
        element.classList.remove('drag-over', 'bg-blue-50', 'border-blue-300', 'border-2', 'border-dashed');
        
        if (this.isFileDrag(e)) {
            const files = Array.from(e.dataTransfer.files);
            const dropType = element.getAttribute('data-drop-type');
            
            if (dropType === 'upload') {
                this.handleFileUpload(files, element);
            } else {
                this.handleFileInput(files, element);
            }
        }
    }

    handleFileInput(files, element) {
        const fileInputId = element.getAttribute('data-file-input');
        const fileInput = document.getElementById(fileInputId) || element.querySelector('input[type="file"]');
        
        if (fileInput) {
            // Create a new FileList-like object
            const dt = new DataTransfer();
            files.forEach(file => dt.items.add(file));
            fileInput.files = dt.files;
            
            // Trigger change event
            fileInput.dispatchEvent(new Event('change', { bubbles: true }));
        }
    }

    handleFileUpload(files, element) {
        if (files.length === 0) return;

        // Determine upload context based on element
        const isFaculty = element.closest('#faculty-upload-form') !== null;
        const isDashboard = element.closest('#upload-form') !== null;
        const isDrive = element.classList.contains('drive-grid');

        if (isFaculty) {
            this.uploadFilesToFaculty(files, element);
        } else if (isDashboard) {
            this.uploadFilesToDashboard(files, element);
        } else if (isDrive) {
            this.uploadFilesToDrive(files, element);
        } else {
            // Default upload behavior
            this.uploadFiles(files, element);
        }
    }

    async uploadFilesToFaculty(files, element) {
        const form = document.getElementById('faculty-upload-form');
        if (!form) return;

        const session = document.getElementById('faculty-session')?.value;
        const department = document.getElementById('faculty-department')?.value;
        const parent = document.getElementById('faculty-parent')?.value;
        const isPublic = document.getElementById('faculty-public')?.checked || false;

        if (!session || !department) {
            this.showToast('Please select session and department first', 'error');
            return;
        }

        // Show upload progress
        this.showUploadProgress(files.length);

        try {
            // Handle folder uploads (multiple files with webkitRelativePath)
            const folderFiles = files.filter(f => f.webkitRelativePath);
            const singleFiles = files.filter(f => !f.webkitRelativePath);

            if (folderFiles.length > 0) {
                await this.uploadFolderStructure(folderFiles, { session, department, parent, isPublic });
            }

            if (singleFiles.length > 0) {
                await this.uploadSingleFiles(singleFiles, { session, department, parent, isPublic });
            }

            this.showToast('Files uploaded successfully!', 'success');
            
            // Refresh the faculty files display
            if (typeof loadFacultyFiles === 'function') {
                loadFacultyFiles();
            }
            if (typeof loadFacultyFolders === 'function') {
                loadFacultyFolders();
            }

        } catch (error) {
            this.showToast('Upload failed: ' + error.message, 'error');
        } finally {
            this.hideUploadProgress();
        }
    }

    async uploadFilesToDashboard(files, element) {
        const form = document.getElementById('upload-form');
        if (!form) return;

        const session = document.getElementById('session')?.value;
        const department = document.getElementById('department')?.value;
        const parent = document.getElementById('parent')?.value;
        const isPublic = document.getElementById('visibility-public')?.checked || false;

        if (!session || !department) {
            this.showToast('Please select session and department first', 'error');
            return;
        }

        this.showUploadProgress(files.length);

        try {
            const folderFiles = files.filter(f => f.webkitRelativePath);
            const singleFiles = files.filter(f => !f.webkitRelativePath);

            if (folderFiles.length > 0) {
                await this.uploadFolderStructure(folderFiles, { session, department, parent, isPublic });
            }

            if (singleFiles.length > 0) {
                await this.uploadSingleFiles(singleFiles, { session, department, parent, isPublic });
            }

            this.showToast('Files uploaded successfully!', 'success');
            
            // Refresh displays
            if (typeof loadMine === 'function') loadMine();
            if (typeof loadFolderTree === 'function') loadFolderTree();
            if (typeof refreshDrive === 'function') refreshDrive();

        } catch (error) {
            this.showToast('Upload failed: ' + error.message, 'error');
        } finally {
            this.hideUploadProgress();
        }
    }

    async uploadFilesToDrive(files, element) {
        // Get current folder context
        const currentFolderId = window.driveCurrentFolderId || null;
        
        // Get session and department from form or user profile
        const session = document.getElementById('session')?.value;
        const department = document.getElementById('department')?.value;
        
        if (!session || !department) {
            this.showToast('Please select session and department first', 'error');
            return;
        }
        
        // Check if any files have webkitRelativePath (indicating folder structure)
        const hasFolderStructure = Array.from(files).some(file => file.webkitRelativePath);
        
        console.log('Uploading files to drive:', {
            fileCount: files.length,
            hasFolderStructure: hasFolderStructure,
            currentFolderId: currentFolderId,
            session: session,
            department: department,
            samplePaths: Array.from(files).slice(0, 3).map(f => ({
                name: f.name,
                webkitRelativePath: f.webkitRelativePath
            }))
        });
        
        if (hasFolderStructure) {
            // Use recursive folder upload for folder structures
            const context = {
                session: session,
                department: department,
                parent: currentFolderId,
                isPublic: document.getElementById('visibility-public')?.checked || false
            };
            
            this.showUploadProgress(files.length);
            
            try {
                await this.uploadFolderStructure(files, context);
                this.showToast('Folder structure uploaded successfully!', 'success');
                
                if (typeof refreshDrive === 'function') {
                    refreshDrive();
                }
                if (typeof loadFolderTree === 'function') {
                    loadFolderTree();
                }
            } catch (error) {
                this.showToast('Folder upload failed: ' + error.message, 'error');
            } finally {
                this.hideUploadProgress();
            }
        } else {
            // Handle individual files
            this.showUploadProgress(files.length);

            try {
                for (const file of files) {
                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('session', session);
                    formData.append('department', department);
                    if (currentFolderId) {
                        formData.append('folder', currentFolderId);
                    }
                    formData.append('is_public', document.getElementById('visibility-public')?.checked || false);
                    
                    console.log('Individual file form data:', {
                        session: session,
                        department: department,
                        folder: currentFolderId,
                        is_public: document.getElementById('visibility-public')?.checked || false,
                        fileName: file.name
                    });

                    const response = await fetch('/api/files/', {
                        method: 'POST',
                        body: formData,
                        headers: { 
                            'X-CSRFToken': this.getCsrfToken(),
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });

                    if (!response.ok) {
                        const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
                        console.error('Individual file upload failed:', {
                            fileName: file.name,
                            status: response.status,
                            statusText: response.statusText,
                            error: error,
                            formData: Object.fromEntries(formData.entries())
                        });
                        throw new Error(error.detail || 'Upload failed');
                    }
                }

                this.showToast('Files uploaded successfully!', 'success');
                
                if (typeof refreshDrive === 'function') {
                    refreshDrive();
                }

            } catch (error) {
                this.showToast('Upload failed: ' + error.message, 'error');
            } finally {
                this.hideUploadProgress();
            }
        }
    }

    async uploadFolderStructure(files, context) {
        const { session, department, parent, isPublic } = context;
        const folderIdByPath = new Map();
        const rootParentId = parent || null;
        folderIdByPath.set('', rootParentId);

        // Create folder structure
        const folderPaths = new Set();
        for (const file of files) {
            const relPath = file.webkitRelativePath || file.name;
            
            const parts = relPath.split('/');
            parts.pop(); // remove file name
            let pathAcc = '';
            for (const part of parts) {
                pathAcc = pathAcc ? `${pathAcc}/${part}` : part;
                folderPaths.add(pathAcc);
            }
            
            // If file is in root of folder (no subfolder), add empty string to ensure root folder is created
            if (parts.length === 0) {
                folderPaths.add('');
            }
        }

        const sortedPaths = Array.from(folderPaths).sort((a, b) => a.split('/').length - b.split('/').length);
        
        console.log('Creating folder structure:', {
            totalFiles: files.length,
            folderPaths: Array.from(folderPaths),
            sortedPaths: sortedPaths,
            rootParentId: rootParentId
        });

        for (const path of sortedPaths) {
            if (folderIdByPath.has(path)) continue;
            
            const segments = path.split('/');
            const name = segments[segments.length - 1];
            const parentPath = segments.slice(0, -1).join('/');
            const parentId = folderIdByPath.get(parentPath) || rootParentId;

            console.log('Creating folder:', {
                path: path,
                name: name,
                parentPath: parentPath,
                parentId: parentId
            });

            const formData = new FormData();
            formData.append('session', session);
            formData.append('department', department);
            formData.append('name', name);
            if (parentId) formData.append('parent', parentId);
            formData.append('is_public', isPublic);

            const response = await fetch('/api/folders/', {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': this.getCsrfToken() }
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'Folder creation failed' }));
                throw new Error(`Failed to create folder "${path}": ${error.detail}`);
            }

            const result = await response.json();
            folderIdByPath.set(path, result.id);
            
            console.log('Folder created successfully:', {
                path: path,
                folderId: result.id
            });
        }

        // Upload files to their respective folders
        console.log('Uploading files to folders:', {
            folderIdByPath: Object.fromEntries(folderIdByPath),
            rootParentId: rootParentId
        });
        
        for (const file of files) {
            const relPath = file.webkitRelativePath || file.name;
            const folderPath = relPath.split('/').slice(0, -1).join('/');
            const targetFolderId = folderIdByPath.get(folderPath) || rootParentId;

            console.log('Uploading file:', {
                fileName: file.name,
                relPath: relPath,
                folderPath: folderPath,
                targetFolderId: targetFolderId
            });

            const formData = new FormData();
            formData.append('session', session);
            formData.append('department', department);
            if (targetFolderId) formData.append('folder', targetFolderId);
            formData.append('file', file);
            formData.append('is_public', isPublic);
            
            console.log('Form data being sent:', {
                session: session,
                department: department,
                folder: targetFolderId,
                is_public: isPublic,
                fileName: file.name
            });

            const response = await fetch('/api/files/', {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': this.getCsrfToken() }
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'File upload failed' }));
                console.error('File upload failed:', {
                    fileName: file.name,
                    relPath: relPath,
                    status: response.status,
                    statusText: response.statusText,
                    error: error
                });
                throw new Error(`Failed to upload "${relPath}": ${error.detail}`);
            }
            
            console.log('File uploaded successfully:', file.name);
        }
    }

    async uploadSingleFiles(files, context) {
        const { session, department, parent, isPublic } = context;

        for (const file of files) {
            const formData = new FormData();
            formData.append('session', session);
            formData.append('department', department);
            if (parent) formData.append('folder', parent);
            formData.append('file', file);
            formData.append('is_public', isPublic);

            const response = await fetch('/api/files/', {
                method: 'POST',
                body: formData,
                headers: { 'X-CSRFToken': this.getCsrfToken() }
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({ detail: 'File upload failed' }));
                throw new Error(`Failed to upload "${file.name}": ${error.detail}`);
            }
        }
    }

    showUploadProgress(totalFiles) {
        // Create or update progress indicator
        let progressEl = document.getElementById('upload-progress');
        if (!progressEl) {
            progressEl = document.createElement('div');
            progressEl.id = 'upload-progress';
            progressEl.className = 'fixed top-4 right-4 bg-white rounded-lg shadow-lg p-4 z-50 min-w-64';
            document.body.appendChild(progressEl);
        }

        progressEl.innerHTML = `
            <div class="flex items-center gap-3">
                <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                <div>
                    <div class="font-medium text-gray-900">Uploading files...</div>
                    <div class="text-sm text-gray-500">Processing ${totalFiles} file(s)</div>
                </div>
            </div>
        `;
    }

    hideUploadProgress() {
        const progressEl = document.getElementById('upload-progress');
        if (progressEl) {
            progressEl.remove();
        }
    }

    showDragOverlay() {
        if (this.dragOverlay) {
            this.dragOverlay.classList.remove('hidden');
        }
    }

    hideDragOverlay() {
        if (this.dragOverlay) {
            this.dragOverlay.classList.add('hidden');
        }
    }

    isFileDrag(e) {
        return e.dataTransfer && e.dataTransfer.types && e.dataTransfer.types.includes('Files');
    }

    getCsrfToken() {
        // Try multiple methods to get CSRF token
        let token = '';
        
        // Method 1: From cookie
        const cookieMatch = document.cookie.match(/csrftoken=([^;]+)/);
        if (cookieMatch) {
            token = cookieMatch[1];
        }
        
        // Method 2: From meta tag
        if (!token) {
            const metaTag = document.querySelector('meta[name="csrf-token"]');
            if (metaTag) {
                token = metaTag.getAttribute('content');
            }
        }
        
        // Method 3: From form input
        if (!token) {
            const csrfInput = document.querySelector('input[name="csrfmiddlewaretoken"]');
            if (csrfInput) {
                token = csrfInput.value;
            }
        }
        
        console.log('CSRF Token:', token ? 'Found' : 'Not found');
        return token;
    }

    showToast(message, type = 'info') {
        // Use existing toast function if available, otherwise create our own
        if (typeof showToast === 'function') {
            showToast(message, { success: type === 'success' });
        } else {
            // Fallback toast implementation
            const toast = document.createElement('div');
            toast.className = `fixed bottom-4 right-4 px-4 py-2 rounded shadow-lg z-50 ${
                type === 'success' ? 'bg-green-600 text-white' : 
                type === 'error' ? 'bg-red-600 text-white' : 
                'bg-blue-600 text-white'
            }`;
            toast.textContent = message;
            document.body.appendChild(toast);
            
            setTimeout(() => {
                toast.remove();
            }, 3000);
        }
    }

    // Method to add new drop zones dynamically
    addDropZoneToElement(element, options = {}) {
        this.addDropZone(element, options.fileInput, options.type);
    }

    // Method to remove drop zones
    removeDropZone(element) {
        if (this.dropZones.has(element)) {
            element.classList.remove('drag-drop-zone', 'drag-over', 'bg-blue-50', 'border-blue-300', 'border-2', 'border-dashed');
            this.dropZones.delete(element);
        }
    }

    // Method to refresh drag and drop functionality after content updates
    refreshDragDrop() {
        // Re-setup folder organization
        this.setupFolderOrganization();
        
        // Re-setup file upload drop zones
        this.setupFileUploadDropZones();
    }

    // Debug method to test folder move functionality
    testFolderMove(sourceFolderId, targetFolderId) {
        console.log('Testing folder move:', { sourceFolderId, targetFolderId });
        
        const formData = new FormData();
        formData.append('parent', targetFolderId);
        
        return fetch(`/api/folders/${sourceFolderId}/`, {
            method: 'PATCH',
            body: formData,
            headers: { 
                'X-CSRFToken': this.getCsrfToken(),
                'X-Requested-With': 'XMLHttpRequest'
            }
        }).then(response => {
            console.log('Test response status:', response.status);
            return response.text().then(text => {
                console.log('Test response text:', text);
                return { status: response.status, text: text };
            });
        }).catch(error => {
            console.error('Test error:', error);
            return { error: error.message };
        });
    }

    // Alternative folder move method using XMLHttpRequest as fallback
    async moveFolderWithXHR(sourceFolderId, targetFolderId) {
        return new Promise((resolve, reject) => {
            const xhr = new XMLHttpRequest();
            const formData = new FormData();
            formData.append('parent', targetFolderId);
            
            xhr.open('PATCH', `/api/folders/${sourceFolderId}/`, true);
            xhr.setRequestHeader('X-CSRFToken', this.getCsrfToken());
            xhr.setRequestHeader('X-Requested-With', 'XMLHttpRequest');
            
            xhr.onload = function() {
                if (xhr.status >= 200 && xhr.status < 300) {
                    try {
                        const response = JSON.parse(xhr.responseText);
                        resolve({ success: true, data: response });
                    } catch (e) {
                        resolve({ success: true, data: xhr.responseText });
                    }
                } else {
                    reject(new Error(`HTTP ${xhr.status}: ${xhr.statusText}`));
                }
            };
            
            xhr.onerror = function() {
                reject(new Error('Network error occurred'));
            };
            
            xhr.ontimeout = function() {
                reject(new Error('Request timeout'));
            };
            
            xhr.timeout = 10000; // 10 second timeout
            xhr.send(formData);
        });
    }

    // Check if API endpoint is accessible
    async checkAPIHealth() {
        try {
            const response = await fetch('/api/folders/', {
                method: 'GET',
                headers: { 'X-CSRFToken': this.getCsrfToken() }
            });
            return {
                accessible: response.ok,
                status: response.status,
                statusText: response.statusText
            };
        } catch (error) {
            return {
                accessible: false,
                error: error.message
            };
        }
    }

    // Comprehensive diagnostic function
    async runDiagnostics() {
        console.log('=== Drag and Drop Diagnostics ===');
        
        // Check CSRF token
        const csrfToken = this.getCsrfToken();
        console.log('CSRF Token:', csrfToken ? 'Found' : 'Missing');
        
        // Check API health
        const apiHealth = await this.checkAPIHealth();
        console.log('API Health:', apiHealth);
        
        // Check folder elements
        const folders = document.querySelectorAll('.folder-item');
        console.log('Folder elements found:', folders.length);
        folders.forEach((folder, index) => {
            const id = folder.getAttribute('data-folder-id');
            const name = folder.querySelector('.font-medium')?.textContent;
            console.log(`Folder ${index + 1}:`, { id, name, element: folder });
        });
        
        // Check drop targets
        const dropTargets = document.querySelectorAll('.folder-item');
        console.log('Drop targets found:', dropTargets.length);
        
        // Test network connectivity
        try {
            const testResponse = await fetch(window.location.origin + '/api/folders/', {
                method: 'GET',
                headers: { 'X-CSRFToken': csrfToken }
            });
            console.log('Network test:', {
                status: testResponse.status,
                ok: testResponse.ok,
                url: testResponse.url
            });
        } catch (error) {
            console.error('Network test failed:', error);
        }
        
        console.log('=== End Diagnostics ===');
        
        return {
            csrfToken: !!csrfToken,
            apiHealth,
            folderCount: folders.length,
            dropTargetCount: dropTargets.length
        };
    }

    // Method to make new elements draggable (called after dynamic content is added)
    makeNewElementsDraggable() {
        // Find new folder items that aren't already draggable
        const newFolderItems = document.querySelectorAll('.folder-item:not([draggable]), [data-folder-id]:not([draggable])');
        newFolderItems.forEach(item => {
            this.makeDraggable(item);
            this.makeDropTarget(item);
        });
        
        // Find new file items that aren't already draggable
        const newFileItems = document.querySelectorAll('[data-file-id]:not([draggable]), .file-item:not([draggable])');
        newFileItems.forEach(item => {
            this.makeFileDraggable(item);
        });
    }

    // Method to show empty drop zone when appropriate
    showEmptyDropZone(container) {
        const emptyZone = container.querySelector('.empty-drop-zone, #empty-drop-zone, #faculty-empty-drop-zone');
        if (emptyZone) {
            emptyZone.classList.remove('hidden');
            emptyZone.classList.add('show');
        }
    }

    // Method to hide empty drop zone
    hideEmptyDropZone(container) {
        const emptyZone = container.querySelector('.empty-drop-zone, #empty-drop-zone, #faculty-empty-drop-zone');
        if (emptyZone) {
            emptyZone.classList.add('hidden');
            emptyZone.classList.remove('show');
        }
    }

    // Enhanced drag preview functionality
    showDragPreview(element) {
        // Create a floating preview element
        const preview = document.createElement('div');
        preview.className = 'drag-preview';
        preview.style.cssText = `
            position: fixed;
            top: -1000px;
            left: -1000px;
            width: ${element.offsetWidth}px;
            height: ${element.offsetHeight}px;
            background: white;
            border: 2px dashed #3b82f6;
            border-radius: 0.5rem;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.15);
            opacity: 0.8;
            z-index: 10000;
            pointer-events: none;
            transform: rotate(5deg);
        `;
        
        // Clone the element content
        const clone = element.cloneNode(true);
        clone.style.cssText = 'width: 100%; height: 100%;';
        preview.appendChild(clone);
        
        document.body.appendChild(preview);
        element._dragPreview = preview;
    }

    hideDragPreview() {
        if (this.draggedElement && this.draggedElement._dragPreview) {
            this.draggedElement._dragPreview.remove();
            delete this.draggedElement._dragPreview;
        }
    }

    // Enhanced drop zone highlighting
    highlightDropZone(element, isActive = true) {
        if (isActive) {
            element.classList.add('drop-target', 'drag-over');
            this.showDropIndicator(element);
        } else {
            element.classList.remove('drop-target', 'drag-over');
            this.hideDropIndicator(element);
        }
    }

    showDropIndicator(element) {
        let indicator = element.querySelector('.drop-zone-indicator');
        if (!indicator) {
            indicator = document.createElement('div');
            indicator.className = 'drop-zone-indicator';
            element.appendChild(indicator);
        }
        indicator.classList.add('active');
    }

    hideDropIndicator(element) {
        const indicator = element.querySelector('.drop-zone-indicator');
        if (indicator) {
            indicator.classList.remove('active');
        }
    }

    // Validate folder move operation
    validateFolderMove(sourceId, targetId) {
        if (!sourceId || !targetId) {
            return { valid: false, reason: 'Missing source or target folder ID' };
        }
        
        if (sourceId === targetId) {
            return { valid: false, reason: 'Cannot move folder to itself' };
        }
        
        // Check if target is a descendant of source (would create circular reference)
        // This is a basic check - in a real implementation, you'd need to check the folder hierarchy
        return { valid: true };
    }

    // Enhanced file movement with visual feedback
    async handleFileUploadToFolder(files, targetElement) {
        const targetFolderId = targetElement.getAttribute('data-folder-id') || 
                              targetElement.getAttribute('data-id') ||
                              targetElement.id.replace('folder-', '');
        
        console.log('handleFileUploadToFolder called with:', { 
            fileCount: files.length, 
            targetElement, 
            targetFolderId 
        });
        
        // Get session and department from form or user profile
        const session = document.getElementById('session')?.value;
        const department = document.getElementById('department')?.value;
        
        if (!session || !department) {
            this.showToast('Please select session and department first', 'error');
            return;
        }
        
        // Check if any files have webkitRelativePath (indicating folder structure)
        const hasFolderStructure = Array.from(files).some(file => file.webkitRelativePath);
        
        console.log('Uploading files to folder:', {
            fileCount: files.length,
            hasFolderStructure: hasFolderStructure,
            targetFolderId: targetFolderId,
            samplePaths: Array.from(files).slice(0, 3).map(f => ({
                name: f.name,
                webkitRelativePath: f.webkitRelativePath
            }))
        });
        
        if (hasFolderStructure) {
            // Use recursive folder upload for folder structures
            const context = {
                session: session,
                department: department,
                parent: targetFolderId,
                isPublic: document.getElementById('visibility-public')?.checked || false
            };
            
            this.showUploadProgress(files.length);
            
            try {
                await this.uploadFolderStructure(files, context);
                this.showToast('Folder structure uploaded successfully!', 'success');
                
                if (typeof refreshDrive === 'function') {
                    refreshDrive();
                }
                if (typeof loadFolderTree === 'function') {
                    loadFolderTree();
                }
            } catch (error) {
                this.showToast('Folder upload failed: ' + error.message, 'error');
            } finally {
                this.hideUploadProgress();
            }
        } else {
            // Handle individual files
            this.showUploadProgress(files.length);

            try {
                for (const file of files) {
                    const formData = new FormData();
                    formData.append('file', file);
                    formData.append('session', session);
                    formData.append('department', department);
                    formData.append('folder', targetFolderId);
                    formData.append('is_public', document.getElementById('visibility-public')?.checked || false);
                    
                    console.log('Uploading file to folder:', {
                        fileName: file.name,
                        targetFolderId: targetFolderId,
                        session: session,
                        department: department
                    });

                    const response = await fetch('/api/files/', {
                        method: 'POST',
                        body: formData,
                        headers: { 
                            'X-CSRFToken': this.getCsrfToken(),
                            'X-Requested-With': 'XMLHttpRequest'
                        }
                    });

                    if (!response.ok) {
                        const error = await response.json().catch(() => ({ detail: 'Upload failed' }));
                        console.error('File upload to folder failed:', {
                            fileName: file.name,
                            targetFolderId: targetFolderId,
                            status: response.status,
                            statusText: response.statusText,
                            error: error
                        });
                        throw new Error(error.detail || 'Upload failed');
                    }
                }

                this.showToast('Files uploaded successfully!', 'success');
                
                if (typeof refreshDrive === 'function') {
                    refreshDrive();
                }
                if (typeof loadFolderTree === 'function') {
                    loadFolderTree();
                }

            } catch (error) {
                this.showToast('Upload failed: ' + error.message, 'error');
            } finally {
                this.hideUploadProgress();
            }
        }
    }

    async handleFileMove(data, targetElement) {
        const targetFolderId = targetElement.getAttribute('data-folder-id') || 
                              targetElement.getAttribute('data-id') ||
                              targetElement.id.replace('folder-', '');
        
        console.log('handleFileMove called with:', { data, targetElement, targetFolderId });
        
        if (data.id === targetFolderId) {
            this.showToast('Cannot move file to the same location', 'error');
            return;
        }
        
        // Check if this is a recursive operation (multiple files)
        if (data.isRecursive && data.files && data.files.length > 1) {
            console.log('Handling recursive file move for', data.files.length, 'files');
            await this.handleRecursiveFileMove(data.files, targetFolderId);
            return;
        }
        
        try {
            const formData = new FormData();
            formData.append('folder', targetFolderId);
            
            console.log('Moving file', data.id, 'to folder', targetFolderId);
            
            const response = await fetch(`/api/files/${data.id}/`, {
                method: 'PATCH',
                body: formData,
                headers: { 'X-CSRFToken': this.getCsrfToken() }
            });
            
            console.log('File move response:', response.status);
            
            if (response.ok) {
                this.showToast(`File "${data.name}" moved successfully`, 'success');
                
                // Refresh the display
                if (typeof refreshDrive === 'function') refreshDrive();
                if (typeof loadFolderTree === 'function') loadFolderTree();
            } else {
                const error = await response.json().catch(() => ({ detail: 'Move failed' }));
                throw new Error(error.detail);
            }
        } catch (error) {
            console.error('Error moving file:', error);
            this.showToast(`Failed to move file: ${error.message}`, 'error');
        }
    }

    async handleRecursiveFileMove(files, targetFolderId) {
        console.log('handleRecursiveFileMove called with', files.length, 'files to folder', targetFolderId);
        
        let successCount = 0;
        let errorCount = 0;
        const errors = [];
        
        for (const file of files) {
            try {
                const formData = new FormData();
                formData.append('folder', targetFolderId);
                
                console.log('Moving file', file.id, 'to folder', targetFolderId);
                
                const response = await fetch(`/api/files/${file.id}/`, {
                    method: 'PATCH',
                    body: formData,
                    headers: { 'X-CSRFToken': this.getCsrfToken() }
                });
                
                if (response.ok) {
                    successCount++;
                    console.log('File', file.name, 'moved successfully');
                } else {
                    const error = await response.json().catch(() => ({ detail: 'Move failed' }));
                    errorCount++;
                    errors.push(`${file.name}: ${error.detail}`);
                    console.error('Failed to move file', file.name, ':', error);
                }
            } catch (error) {
                errorCount++;
                errors.push(`${file.name}: ${error.message}`);
                console.error('Error moving file', file.name, ':', error);
            }
        }
        
        // Show summary
        if (successCount > 0) {
            this.showToast(`${successCount} file(s) moved successfully`, 'success');
        }
        
        if (errorCount > 0) {
            this.showToast(`${errorCount} file(s) failed to move: ${errors.join(', ')}`, 'error');
        }
        
        // Refresh the display
        if (typeof refreshDrive === 'function') refreshDrive();
        if (typeof loadFolderTree === 'function') loadFolderTree();
    }

    getSelectedFiles() {
        // Get all selected files from the current view
        const selectedFiles = [];
        const fileItems = document.querySelectorAll('.file-item.selected, .file-item[data-selected="true"]');
        
        fileItems.forEach(item => {
            const fileId = item.getAttribute('data-file-id') || 
                          item.getAttribute('data-id') ||
                          item.id.replace('file-', '');
            const fileName = item.querySelector('.font-medium')?.textContent || 'Unknown';
            
            selectedFiles.push({
                id: fileId,
                name: fileName,
                element: item
            });
        });
        
        return selectedFiles;
    }

    setupMultiSelect() {
        // Add click handlers for multi-select
        document.addEventListener('click', (e) => {
            const fileItem = e.target.closest('.file-item');
            if (!fileItem) return;
            
            // Handle Ctrl/Cmd + click for multi-select
            if (e.ctrlKey || e.metaKey) {
                e.preventDefault();
                this.toggleFileSelection(fileItem);
            } else {
                // Single select - clear others and select this one
                this.clearFileSelections();
                this.selectFile(fileItem);
            }
        });
        
        // Handle keyboard shortcuts
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.clearFileSelections();
            } else if (e.key === 'a' && (e.ctrlKey || e.metaKey)) {
                e.preventDefault();
                this.selectAllFiles();
            }
        });
    }

    setupGlobalMenuClose() {
        // Global click listener to auto-close menus when clicking outside
        document.addEventListener('click', (e) => {
            // Check if the clicked element is a menu button or inside a menu
            const isMenuButton = e.target.closest('[onclick*="toggleFileMenu"], [onclick*="toggleFolderMenu"]');
            const isInsideMenu = e.target.closest('[id^="file-menu-"], [id^="folder-menu-"]');
            
            // If clicking on a menu button, don't close menus (let the toggle function handle it)
            if (isMenuButton) {
                return;
            }
            
            // If clicking inside a menu, don't close it
            if (isInsideMenu) {
                return;
            }
            
            // Otherwise, close all menus
            this.hideAllMenus();
        });

        // Global keyboard listener to close menus on Escape
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                this.hideAllMenus();
            }
        });
    }

    hideAllMenus() {
        document.querySelectorAll('[id^="file-menu-"]').forEach(el => el.classList.add('hidden'));
        document.querySelectorAll('[id^="folder-menu-"]').forEach(el => el.classList.add('hidden'));
    }

    toggleFileSelection(fileItem) {
        if (fileItem.classList.contains('selected')) {
            fileItem.classList.remove('selected');
            fileItem.removeAttribute('data-selected');
        } else {
            fileItem.classList.add('selected');
            fileItem.setAttribute('data-selected', 'true');
        }
    }

    selectFile(fileItem) {
        fileItem.classList.add('selected');
        fileItem.setAttribute('data-selected', 'true');
    }

    clearFileSelections() {
        const selectedFiles = document.querySelectorAll('.file-item.selected, .file-item[data-selected="true"]');
        selectedFiles.forEach(item => {
            item.classList.remove('selected');
            item.removeAttribute('data-selected');
        });
    }

    selectAllFiles() {
        const fileItems = document.querySelectorAll('.file-item');
        fileItems.forEach(item => {
            item.classList.add('selected');
            item.setAttribute('data-selected', 'true');
        });
    }
}

// Initialize drag and drop when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.dragDropManager = new DragDropManager();
});

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = DragDropManager;
}
