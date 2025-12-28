/**
 * Enhanced Canvas Sync Interface
 * ==============================
 * 
 * Provides a modern, user-friendly interface for Canvas sync with:
 * - Real-time progress updates via Server-Sent Events
 * - Alert-based notifications instead of progress bars
 * - Error recovery and retry mechanisms
 * - Better user feedback and status communication
 * 
 * Author: Canvas Integration Team
 * Date: 2024-12-20
 */

class EnhancedCanvasSync {
    constructor() {
        this.eventSource = null;
        this.currentSync = null;
        this.retryCount = 0;
        this.maxRetries = 3;
        
        // Bind methods
        this.startSync = this.startSync.bind(this);
        this.cancelSync = this.cancelSync.bind(this);
        this.retrySync = this.retrySync.bind(this);
        
        // Initialize UI
        this.initializeUI();
        this.checkSyncStatus();
    }
    
    initializeUI() {
        // Create enhanced sync interface
        const syncContainer = document.getElementById('canvas-sync-container');
        if (!syncContainer) return;
        
        syncContainer.innerHTML = `
            <div class="enhanced-sync-interface">
                <!-- Sync Status Card -->
                <div class="sync-status-card" id="sync-status-card">
                    <div class="status-header">
                        <h3>Canvas Sync Status</h3>
                        <span class="status-badge" id="status-badge">Ready</span>
                    </div>
                    <div class="status-content" id="status-content">
                        <p id="status-message">Ready to sync with Canvas</p>
                        <div class="sync-details" id="sync-details" style="display: none;">
                            <div class="detail-item">
                                <span class="label">Progress:</span>
                                <span class="value" id="progress-text">0%</span>
                            </div>
                            <div class="detail-item">
                                <span class="label">Current Task:</span>
                                <span class="value" id="current-task">-</span>
                            </div>
                            <div class="detail-item">
                                <span class="label">Elapsed Time:</span>
                                <span class="value" id="elapsed-time">0s</span>
                            </div>
                            <div class="detail-item">
                                <span class="label">Estimated Remaining:</span>
                                <span class="value" id="remaining-time">-</span>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Sync Controls -->
                <div class="sync-controls">
                    <div class="sync-options" id="sync-options">
                        <div class="option-group">
                            <label>Sync Type:</label>
                            <select id="sync-type" class="form-select">
                                <option value="all">All Courses</option>
                                <option value="term">Specific Term</option>
                                <option value="course">Single Course</option>
                            </select>
                        </div>
                        
                        <div class="option-group" id="target-selection" style="display: none;">
                            <label>Select Target:</label>
                            <select id="target-id" class="form-select">
                                <option value="">Choose...</option>
                            </select>
                        </div>
                        
                        <div class="option-group">
                            <label class="checkbox-label">
                                <input type="checkbox" id="use-incremental" checked>
                                Use incremental sync (faster for updates)
                            </label>
                        </div>
                        
                        <div class="option-group advanced-options" style="display: none;">
                            <label>Courses per chunk:</label>
                            <input type="number" id="chunk-size" value="10" min="5" max="50" class="form-input">
                            <small>Smaller chunks = more stable, larger chunks = faster</small>
                        </div>
                    </div>
                    
                    <div class="action-buttons">
                        <button id="preview-btn" class="btn btn-secondary">
                            <i class="fas fa-eye"></i> Preview Sync
                        </button>
                        <button id="start-sync-btn" class="btn btn-primary">
                            <i class="fas fa-sync"></i> Start Sync
                        </button>
                        <button id="cancel-sync-btn" class="btn btn-danger" style="display: none;">
                            <i class="fas fa-times"></i> Cancel Sync
                        </button>
                        <button id="retry-sync-btn" class="btn btn-warning" style="display: none;">
                            <i class="fas fa-redo"></i> Retry from Checkpoint
                        </button>
                    </div>
                </div>
                
                <!-- Notifications Area -->
                <div class="sync-notifications" id="sync-notifications">
                    <!-- Dynamic notifications will appear here -->
                </div>
                
                <!-- Sync History -->
                <div class="sync-history" id="sync-history" style="display: none;">
                    <h4>Recent Syncs</h4>
                    <div class="history-list" id="history-list">
                        <!-- History items will be populated here -->
                    </div>
                </div>
                
                <!-- Advanced Options Toggle -->
                <div class="advanced-toggle">
                    <button id="toggle-advanced" class="btn btn-link">
                        <i class="fas fa-cog"></i> Advanced Options
                    </button>
                </div>
            </div>
        `;
        
        // Add event listeners
        this.attachEventListeners();
        
        // Add CSS styles
        this.addStyles();
    }
    
    attachEventListeners() {
        // Main action buttons
        document.getElementById('start-sync-btn').addEventListener('click', this.startSync);
        document.getElementById('cancel-sync-btn').addEventListener('click', this.cancelSync);
        document.getElementById('retry-sync-btn').addEventListener('click', this.retrySync);
        document.getElementById('preview-btn').addEventListener('click', this.previewSync.bind(this));
        
        // Sync type change
        document.getElementById('sync-type').addEventListener('change', this.handleSyncTypeChange.bind(this));
        
        // Advanced options toggle
        document.getElementById('toggle-advanced').addEventListener('click', this.toggleAdvancedOptions.bind(this));
        
        // Test connection button (if exists)
        const testBtn = document.getElementById('test-canvas-connection');
        if (testBtn) {
            testBtn.addEventListener('click', this.testConnection.bind(this));
        }
    }
    
    async startSync() {
        try {
            // Disable sync button and show loading state
            this.setUIState('starting');
            
            // Get sync parameters
            const syncData = {
                sync_type: document.getElementById('sync-type').value,
                target_id: document.getElementById('target-id').value || null,
                use_incremental: document.getElementById('use-incremental').checked,
                chunk_size: parseInt(document.getElementById('chunk-size').value) || 10
            };
            
            // Validate parameters
            if (syncData.sync_type !== 'all' && !syncData.target_id) {
                this.showNotification('Please select a target for the sync type chosen.', 'warning');
                this.setUIState('ready');
                return;
            }
            
            // Show starting notification
            this.showNotification('Starting Canvas sync...', 'info', false);
            
            // Start sync via API
            const response = await fetch('/sync/canvas/start_enhanced', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(syncData)
            });
            
            const result = await this.parseJSONResponse(response);
            
            if (result.success) {
                this.currentSync = result;
                this.setUIState('syncing');
                this.showNotification(result.message, 'success');
                
                // Start real-time progress monitoring
                this.startProgressMonitoring();
                
                // Show sync details
                this.showSyncDetails(true);
                
            } else {
                this.setUIState('error');
                this.showNotification(result.message, 'error');
                
                // Handle specific error types
                if (result.error_type === 'credentials_missing') {
                    this.showCredentialsPrompt();
                } else if (result.error_type === 'sync_in_progress') {
                    this.handleExistingSync(result.current_progress);
                }
            }
            
        } catch (error) {
            console.error('Failed to start sync:', error);
            this.setUIState('error');
            this.showNotification('Failed to start sync. Please try again.', 'error');
        }
    }
    
    async cancelSync() {
        try {
            this.setUIState('cancelling');
            this.showNotification('Cancelling sync...', 'info', false);
            
            const response = await fetch('/sync/canvas/cancel', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const result = await this.parseJSONResponse(response);
            
            if (result.success) {
                this.stopProgressMonitoring();
                this.setUIState('cancelled');
                this.showNotification('Canvas sync cancelled successfully.', 'info');
                this.showSyncDetails(false);
            } else {
                this.showNotification('Failed to cancel sync: ' + result.message, 'error');
                this.setUIState('syncing'); // Revert to syncing state
            }
            
        } catch (error) {
            console.error('Failed to cancel sync:', error);
            this.showNotification('Failed to cancel sync.', 'error');
        }
    }
    
    async retrySync() {
        try {
            this.retryCount++;
            this.setUIState('retrying');
            this.showNotification(`Retrying sync (attempt ${this.retryCount})...`, 'info', false);
            
            const syncData = {
                sync_type: document.getElementById('sync-type').value,
                target_id: document.getElementById('target-id').value || null,
                chunk_size: parseInt(document.getElementById('chunk-size').value) || 10
            };
            
            const response = await fetch('/sync/canvas/retry', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(syncData)
            });
            
            const result = await this.parseJSONResponse(response);
            
            if (result.success) {
                this.currentSync = result;
                this.setUIState('syncing');
                this.showNotification(result.message, 'success');
                this.startProgressMonitoring();
            } else {
                this.setUIState('error');
                this.showNotification('Retry failed: ' + result.message, 'error');
                
                if (this.retryCount < this.maxRetries) {
                    setTimeout(() => {
                        document.getElementById('retry-sync-btn').style.display = 'inline-block';
                    }, 5000); // Show retry button after 5 seconds
                }
            }
            
        } catch (error) {
            console.error('Failed to retry sync:', error);
            this.setUIState('error');
            this.showNotification('Failed to retry sync.', 'error');
        }
    }
    
    async previewSync() {
        try {
            const previewData = {
                use_incremental: document.getElementById('use-incremental').checked
            };
            
            this.showNotification('Loading preview...', 'info', false);
            
            const response = await fetch('/sync/canvas/preview', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                },
                body: JSON.stringify(previewData)
            });
            
            const result = await this.parseJSONResponse(response);
            
            if (result.success) {
                this.showPreviewModal(result);
            } else {
                this.showNotification('Preview failed: ' + result.message, 'error');
            }
            
        } catch (error) {
            console.error('Failed to get preview:', error);
            this.showNotification('Failed to load preview.', 'error');
        }
    }
    
    startProgressMonitoring() {
        if (this.eventSource) {
            try { this.eventSource.close(); } catch (e) {}
            this.eventSource = null;
        }

        const userId = this.getCurrentUserId();
        const sseUrl = `/sync/canvas/progress_stream?user_id=${encodeURIComponent(userId)}`;

        try {
            this.eventSource = new EventSource(sseUrl);

            // Ensure cookies/credentials will be sent when supported
            try {
                if ('withCredentials' in this.eventSource) {
                    this.eventSource.withCredentials = true;
                }
            } catch (e) {
                // Ignore if not supported
            }

            // If connection doesn't open within timeout, fallback to polling
            let openTimeout = setTimeout(() => {
                console.warn('SSE connection did not open in time, falling back to polling');
                try { this.eventSource.close(); } catch (e) {}
                this.eventSource = null;
                this.startProgressPolling();
            }, 15000); // Increased from 5s to 15s

            this.eventSource.onopen = () => {
                clearTimeout(openTimeout);
                console.log('Real-time progress monitoring started');
            };

            this.eventSource.onmessage = (event) => {
                try {
                    const progressData = JSON.parse(event.data);
                    
                    // Ignore heartbeat messages (just for keepalive)
                    if (progressData.status === 'heartbeat') {
                        console.debug('SSE heartbeat received');
                        return;
                    }
                    
                    this.updateProgress(progressData);
                } catch (error) {
                    console.error('Failed to parse progress data:', error);
                }
            };

            this.eventSource.onerror = (error) => {
                console.warn('SSE connection failed, falling back to polling', error);
                try { this.eventSource.close(); } catch (e) {}
                this.eventSource = null;
                this.startProgressPolling();
            };

        } catch (error) {
            console.warn('Failed to initialize EventSource, falling back to polling', error);
            this.startProgressPolling();
        }
    }
    
    startProgressPolling() {
        // Fallback polling mechanism
        this.progressPollingInterval = setInterval(async () => {
            try {
                const response = await fetch('/sync/canvas/progress_enhanced');
                const result = await this.parseJSONResponse(response);
                
                if (result.success && result.progress) {
                    this.updateProgress(result.progress);
                }
            } catch (error) {
                console.error('Progress polling error:', error);
            }
        }, 2000); // Poll every 2 seconds
    }
    
    stopProgressMonitoring() {
        if (this.eventSource) {
            this.eventSource.close();
            this.eventSource = null;
        }
        
        if (this.progressPollingInterval) {
            clearInterval(this.progressPollingInterval);
            this.progressPollingInterval = null;
        }
    }
    
    updateProgress(progressData) {
        if (!progressData) return;
        
        // Update progress display
        const progressText = document.getElementById('progress-text');
        const currentTask = document.getElementById('current-task');
        const elapsedTime = document.getElementById('elapsed-time');
        const remainingTime = document.getElementById('remaining-time');
        
        if (progressText) {
            progressText.textContent = `${progressData.progress_percent}%`;
        }
        
        if (currentTask) {
            currentTask.textContent = progressData.current_operation || 'Processing...';
        }
        
        if (elapsedTime) {
            elapsedTime.textContent = this.formatTime(progressData.elapsed_time || 0);
        }
        
        if (remainingTime && progressData.estimated_remaining) {
            remainingTime.textContent = this.formatTime(progressData.estimated_remaining);
        } else if (remainingTime) {
            remainingTime.textContent = '-';
        }
        
        // Update status message with current operation
        const statusMessage = document.getElementById('status-message');
        if (statusMessage) {
            statusMessage.textContent = progressData.current_operation || 'Syncing in progress...';
        }
        
        // Handle completion or errors
        if (progressData.is_complete) {
            this.stopProgressMonitoring();
            
            if (progressData.errors && progressData.errors.length > 0) {
                this.setUIState('error');
                this.showNotification('Sync completed with errors. Check the details below.', 'warning');
                this.showErrors(progressData.errors);
            } else {
                this.setUIState('completed');
                this.showNotification('Canvas sync completed successfully! 🎉', 'success');
                
                // Show success summary
                if (progressData.result_summary) {
                    this.showSuccessSummary(progressData.result_summary);
                }
            }
            
            this.showSyncDetails(false);
            this.refreshSyncHistory();
        }
        
        // Show milestone notifications
        this.showMilestoneNotifications(progressData);
    }
    
    showMilestoneNotifications(progressData) {
        const progress = progressData.progress_percent;
        
        // Show notifications at key milestones
        if (progress === 25 && !this.milestones?.quarter) {
            this.showNotification('✨ 25% complete - Making great progress!', 'info', true, 3000);
            this.milestones = { ...(this.milestones || {}), quarter: true };
        } else if (progress === 50 && !this.milestones?.half) {
            this.showNotification('🚀 Halfway there! 50% complete', 'info', true, 3000);
            this.milestones = { ...(this.milestones || {}), half: true };
        } else if (progress === 75 && !this.milestones?.threeQuarter) {
            this.showNotification('🏁 75% complete - Almost finished!', 'info', true, 3000);
            this.milestones = { ...(this.milestones || {}), threeQuarter: true };
        }
    }
    
    setUIState(state) {
        const statusBadge = document.getElementById('status-badge');
        const startBtn = document.getElementById('start-sync-btn');
        const cancelBtn = document.getElementById('cancel-sync-btn');
        const retryBtn = document.getElementById('retry-sync-btn');
        const syncOptions = document.getElementById('sync-options');
        
        // Reset milestone tracking
        if (state === 'syncing') {
            this.milestones = {};
        }
        
        switch (state) {
            case 'ready':
                statusBadge.className = 'status-badge ready';
                statusBadge.textContent = 'Ready';
                startBtn.style.display = 'inline-block';
                cancelBtn.style.display = 'none';
                retryBtn.style.display = 'none';
                syncOptions.style.display = 'block';
                startBtn.disabled = false;
                break;
                
            case 'starting':
                statusBadge.className = 'status-badge starting';
                statusBadge.textContent = 'Starting...';
                startBtn.disabled = true;
                break;
                
            case 'syncing':
                statusBadge.className = 'status-badge syncing';
                statusBadge.textContent = 'Syncing';
                startBtn.style.display = 'none';
                cancelBtn.style.display = 'inline-block';
                retryBtn.style.display = 'none';
                syncOptions.style.display = 'none';
                break;
                
            case 'cancelling':
                statusBadge.className = 'status-badge cancelling';
                statusBadge.textContent = 'Cancelling...';
                cancelBtn.disabled = true;
                break;
                
            case 'cancelled':
                statusBadge.className = 'status-badge cancelled';
                statusBadge.textContent = 'Cancelled';
                this.setUIState('ready');
                break;
                
            case 'completed':
                statusBadge.className = 'status-badge completed';
                statusBadge.textContent = 'Completed';
                setTimeout(() => this.setUIState('ready'), 5000);
                break;
                
            case 'error':
                statusBadge.className = 'status-badge error';
                statusBadge.textContent = 'Error';
                startBtn.style.display = 'inline-block';
                cancelBtn.style.display = 'none';
                retryBtn.style.display = 'inline-block';
                syncOptions.style.display = 'block';
                startBtn.disabled = false;
                cancelBtn.disabled = false;
                break;
                
            case 'retrying':
                statusBadge.className = 'status-badge retrying';
                statusBadge.textContent = 'Retrying...';
                retryBtn.disabled = true;
                break;
        }
    }
    
    showNotification(message, type = 'info', dismissible = true, duration = 5000) {
        const notificationsContainer = document.getElementById('sync-notifications');
        
        const notification = document.createElement('div');
        notification.className = `sync-notification ${type} ${dismissible ? 'dismissible' : ''}`;
        
        notification.innerHTML = `
            <div class="notification-content">
                <span class="notification-icon">${this.getNotificationIcon(type)}</span>
                <span class="notification-message">${message}</span>
                ${dismissible ? '<button class="notification-close" onclick="this.parentElement.parentElement.remove()">&times;</button>' : ''}
            </div>
        `;
        
        notificationsContainer.appendChild(notification);
        
        // Auto-dismiss after duration
        if (dismissible && duration > 0) {
            setTimeout(() => {
                if (notification.parentElement) {
                    notification.remove();
                }
            }, duration);
        }
        
        // Limit number of notifications
        const notifications = notificationsContainer.querySelectorAll('.sync-notification');
        if (notifications.length > 5) {
            notifications[0].remove();
        }
    }
    
    getNotificationIcon(type) {
        const icons = {
            'info': '<i class="fas fa-info-circle"></i>',
            'success': '<i class="fas fa-check-circle"></i>',
            'warning': '<i class="fas fa-exclamation-triangle"></i>',
            'error': '<i class="fas fa-times-circle"></i>'
        };
        return icons[type] || icons['info'];
    }
    
    showSyncDetails(show) {
        const syncDetails = document.getElementById('sync-details');
        if (syncDetails) {
            syncDetails.style.display = show ? 'block' : 'none';
        }
    }
    
    formatTime(seconds) {
        if (!seconds || seconds < 0) return '0s';
        
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        const secs = Math.floor(seconds % 60);
        
        if (hours > 0) {
            return `${hours}h ${minutes}m ${secs}s`;
        } else if (minutes > 0) {
            return `${minutes}m ${secs}s`;
        } else {
            return `${secs}s`;
        }
    }
    
    getCSRFToken() {
        return document.querySelector('meta[name=csrf-token]')?.getAttribute('content') || '';
    }
    
    getCurrentUserId() {
        // Extract user ID from page context or meta tag
        return document.querySelector('meta[name=current-user-id]')?.getAttribute('content') || '1';
    }
    
    addStyles() {
        const style = document.createElement('style');
        style.textContent = `
            .enhanced-sync-interface {
                max-width: 800px;
                margin: 20px auto;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
            
            .sync-status-card {
                background: #fff;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                padding: 24px;
                margin-bottom: 24px;
                border: 1px solid #e1e5e9;
            }
            
            .status-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 16px;
            }
            
            .status-header h3 {
                margin: 0;
                color: #1a202c;
                font-size: 1.25rem;
            }
            
            .status-badge {
                padding: 6px 12px;
                border-radius: 20px;
                font-size: 0.875rem;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            .status-badge.ready { background: #e6fffa; color: #065f46; }
            .status-badge.starting { background: #fef3c7; color: #92400e; }
            .status-badge.syncing { background: #dbeafe; color: #1e40af; }
            .status-badge.cancelling { background: #fed7d7; color: #c53030; }
            .status-badge.completed { background: #d1fae5; color: #065f46; }
            .status-badge.error { background: #fed7d7; color: #c53030; }
            .status-badge.retrying { background: #fef3c7; color: #92400e; }
            
            .sync-details {
                background: #f8fafc;
                border-radius: 8px;
                padding: 16px;
                margin-top: 16px;
            }
            
            .detail-item {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 8px 0;
                border-bottom: 1px solid #e2e8f0;
            }
            
            .detail-item:last-child {
                border-bottom: none;
            }
            
            .detail-item .label {
                font-weight: 600;
                color: #4a5568;
            }
            
            .detail-item .value {
                font-family: 'SF Mono', Monaco, monospace;
                background: #e2e8f0;
                padding: 4px 8px;
                border-radius: 4px;
                font-size: 0.875rem;
            }
            
            .sync-controls {
                background: #fff;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                padding: 24px;
                margin-bottom: 24px;
                border: 1px solid #e1e5e9;
            }
            
            .sync-options {
                margin-bottom: 24px;
            }
            
            .option-group {
                margin-bottom: 16px;
            }
            
            .option-group label {
                display: block;
                font-weight: 600;
                color: #374151;
                margin-bottom: 8px;
            }
            
            .form-select, .form-input {
                width: 100%;
                padding: 12px;
                border: 2px solid #e5e7eb;
                border-radius: 8px;
                font-size: 1rem;
                transition: border-color 0.2s;
            }
            
            .form-select:focus, .form-input:focus {
                outline: none;
                border-color: #3b82f6;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
            }
            
            .checkbox-label {
                display: flex;
                align-items: center;
                cursor: pointer;
            }
            
            .checkbox-label input {
                margin-right: 8px;
            }
            
            .action-buttons {
                display: flex;
                gap: 12px;
                flex-wrap: wrap;
            }
            
            .btn {
                padding: 12px 24px;
                border-radius: 8px;
                font-weight: 600;
                cursor: pointer;
                border: none;
                transition: all 0.2s;
                display: inline-flex;
                align-items: center;
                gap: 8px;
                text-decoration: none;
            }
            
            .btn:disabled {
                opacity: 0.6;
                cursor: not-allowed;
            }
            
            .btn-primary {
                background: #3b82f6;
                color: white;
            }
            
            .btn-primary:hover:not(:disabled) {
                background: #2563eb;
                transform: translateY(-1px);
            }
            
            .btn-secondary {
                background: #6b7280;
                color: white;
            }
            
            .btn-secondary:hover:not(:disabled) {
                background: #4b5563;
            }
            
            .btn-danger {
                background: #dc2626;
                color: white;
            }
            
            .btn-danger:hover:not(:disabled) {
                background: #b91c1c;
            }
            
            .btn-warning {
                background: #f59e0b;
                color: white;
            }
            
            .btn-warning:hover:not(:disabled) {
                background: #d97706;
            }
            
            .btn-link {
                background: none;
                color: #3b82f6;
                text-decoration: none;
            }
            
            .btn-link:hover {
                color: #2563eb;
                text-decoration: underline;
            }
            
            .sync-notifications {
                margin-bottom: 24px;
            }
            
            .sync-notification {
                background: #fff;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                margin-bottom: 12px;
                border-left: 4px solid #3b82f6;
                overflow: hidden;
                animation: slideIn 0.3s ease-out;
            }
            
            .sync-notification.info { border-left-color: #3b82f6; }
            .sync-notification.success { border-left-color: #059669; }
            .sync-notification.warning { border-left-color: #d97706; }
            .sync-notification.error { border-left-color: #dc2626; }
            
            .notification-content {
                padding: 16px;
                display: flex;
                align-items: center;
                gap: 12px;
            }
            
            .notification-icon {
                flex-shrink: 0;
                font-size: 1.125rem;
            }
            
            .notification-message {
                flex: 1;
                font-weight: 500;
            }
            
            .notification-close {
                background: none;
                border: none;
                font-size: 1.5rem;
                cursor: pointer;
                color: #6b7280;
                padding: 0;
                width: 24px;
                height: 24px;
                display: flex;
                align-items: center;
                justify-content: center;
            }
            
            .notification-close:hover {
                color: #374151;
            }
            
            @keyframes slideIn {
                from {
                    transform: translateX(100%);
                    opacity: 0;
                }
                to {
                    transform: translateX(0);
                    opacity: 1;
                }
            }
            
            .advanced-toggle {
                text-align: center;
                margin-top: 16px;
            }
            
            .sync-history {
                background: #fff;
                border-radius: 12px;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                padding: 24px;
                border: 1px solid #e1e5e9;
            }
            
            .sync-history h4 {
                margin: 0 0 16px 0;
                color: #1a202c;
            }
            
            @media (max-width: 768px) {
                .enhanced-sync-interface {
                    margin: 16px;
                }
                
                .action-buttons {
                    flex-direction: column;
                }
                
                .btn {
                    width: 100%;
                    justify-content: center;
                }
            }
        `;
        document.head.appendChild(style);
    }
    
    // Additional methods for complete functionality
    async checkSyncStatus() {
        try {
            const response = await fetch('/sync/canvas/status');
            const result = await this.parseJSONResponse(response);
            
            if (result.success) {
                if (result.current_sync && !result.current_sync.is_complete) {
                    // Resume monitoring active sync
                    this.currentSync = result.current_sync;
                    this.setUIState('syncing');
                    this.startProgressMonitoring();
                    this.showSyncDetails(true);
                }
                
                // Show sync history
                if (result.recent_syncs && result.recent_syncs.length > 0) {
                    this.displaySyncHistory(result.recent_syncs);
                }
            }
        } catch (error) {
            console.error('Failed to check sync status:', error);
        }
    }
    
    handleSyncTypeChange() {
        const syncType = document.getElementById('sync-type').value;
        const targetSelection = document.getElementById('target-selection');
        
        if (syncType === 'all') {
            targetSelection.style.display = 'none';
        } else {
            targetSelection.style.display = 'block';
            // Would populate with terms or courses based on selection
        }
    }
    
    toggleAdvancedOptions() {
        const advancedOptions = document.querySelector('.advanced-options');
        const toggleBtn = document.getElementById('toggle-advanced');
        
        if (advancedOptions.style.display === 'none' || !advancedOptions.style.display) {
            advancedOptions.style.display = 'block';
            toggleBtn.innerHTML = '<i class="fas fa-cog"></i> Hide Advanced Options';
        } else {
            advancedOptions.style.display = 'none';
            toggleBtn.innerHTML = '<i class="fas fa-cog"></i> Advanced Options';
        }
    }
    
    async testConnection() {
        try {
            this.showNotification('Testing Canvas connection...', 'info', false);
            
            const response = await fetch('/sync/canvas/test_connection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.getCSRFToken()
                }
            });
            
            const result = await this.parseJSONResponse(response);
            
            if (result.success) {
                this.showNotification('✅ Canvas connection successful!', 'success');
            } else {
                this.showNotification('❌ Canvas connection failed: ' + result.message, 'error');
            }
        } catch (error) {
            this.showNotification('❌ Connection test failed', 'error');
        }
    }
    
    // Placeholder methods for additional functionality
    showPreviewModal(previewData) {
        // Implementation for preview modal
        console.log('Preview data:', previewData);
    }
    
    showCredentialsPrompt() {
        this.showNotification('Please configure your Canvas credentials in Settings.', 'warning');
    }
    
    handleExistingSync(progressData) {
        this.updateProgress(progressData);
        this.setUIState('syncing');
        this.startProgressMonitoring();
    }
    
    showErrors(errors) {
        errors.forEach(error => {
            this.showNotification(error, 'error', true, 10000);
        });
    }
    
    showSuccessSummary(summary) {
        const summaryText = `Successfully synced: ${summary.courses} courses, ${summary.assignments} assignments, ${summary.categories} categories`;
        this.showNotification(summaryText, 'success', true, 8000);
    }
    
    refreshSyncHistory() {
        // Refresh the sync history display
        this.checkSyncStatus();
    }
    
    displaySyncHistory(syncs) {
        const historyContainer = document.getElementById('sync-history');
        const historyList = document.getElementById('history-list');
        
        if (syncs.length > 0) {
            historyContainer.style.display = 'block';
            historyList.innerHTML = syncs.map(sync => `
                <div class="history-item">
                    <span class="sync-type">${sync.sync_type}</span>
                    <span class="sync-date">${new Date(sync.created_at).toLocaleString()}</span>
                    <span class="sync-status ${sync.is_complete ? 'completed' : 'incomplete'}">
                        ${sync.is_complete ? '✓' : '⏳'}
                    </span>
                </div>
            `).join('');
        }
    }
    
    // Helper method for safe JSON parsing
    async parseJSONResponse(response) {
        try {
            // Check if response is successful
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            // Check if response is JSON
            const contentType = response.headers.get('content-type');
            if (!contentType || !contentType.includes('application/json')) {
                const text = await response.text();
                if (text.includes('<!DOCTYPE') || text.includes('<html')) {
                    throw new Error('Server returned HTML page instead of JSON (likely authentication required)');
                }
                throw new Error('Server did not return JSON response');
            }
            
            return await response.json();
        } catch (error) {
            console.error('Failed to parse JSON response:', error);
            throw error;
        }
    }
}

// Initialize the enhanced Canvas sync interface when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('canvas-sync-container')) {
        window.enhancedCanvasSync = new EnhancedCanvasSync();
    }
});