// Global variable to track pending requests to prevent double-clicking
let pendingRequests = new Set();

function handleTodoToggle(itemId, checkbox, willBeCompleted) {
    console.log('handleTodoToggle:', itemId, 'willBeCompleted:', willBeCompleted);
    
    // Prevent multiple requests for the same item
    if (pendingRequests.has(itemId)) {
        console.log('Request already pending for item:', itemId);
        checkbox.checked = !checkbox.checked; // Revert the checkbox
        return;
    }
    
    toggleTodoCompletion(itemId, willBeCompleted, checkbox);
}

function handleAssignmentToggle(itemId, checkbox) {
    console.log('handleAssignmentToggle:', itemId, 'checked:', checkbox.checked);

    // Prevent multiple requests for the same item
    if (pendingRequests.has(itemId)) {
        console.log('Request already pending for item:', itemId);
        checkbox.checked = !checkbox.checked; // Revert the checkbox
        return;
    }

    const csrfTokenElement = document.querySelector('meta[name="csrf-token"]');
    const toggleUrlElement = document.querySelector('meta[name="toggle-assignment-url"]');

    if (!csrfTokenElement) {
        console.error('CSRF token not found');
        alert('Security token not found. Please refresh the page.');
        checkbox.checked = !checkbox.checked;
        return;
    }

    if (!toggleUrlElement) {
        console.error('Toggle assignment URL not found');
        alert('Configuration error. Please refresh the page.');
        checkbox.checked = !checkbox.checked;
        return;
    }

    const csrfToken = csrfTokenElement.getAttribute('content');
    const baseUrl = toggleUrlElement.getAttribute('content');

    // Add to pending requests
    pendingRequests.add(itemId);

    // Use FormData to send CSRF token as form data
    const formData = new FormData();
    formData.append('csrf_token', csrfToken);

    fetch(baseUrl.replace('0', itemId), {
        method: 'POST',
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.text().then(text => {
            try {
                return JSON.parse(text);
            } catch (e) {
                console.error('Server returned non-JSON response:', text.substring(0, 200));
                throw new Error('Server error: Expected JSON response but got HTML. Check server logs.');
            }
        });
    })
    .then(data => {
        if (data.success) {
            // Explicitly set the checkbox state to match the server response
            checkbox.checked = data.completed;
            console.log('Assignment toggle successful, completed:', data.completed);
        } else {
            console.error('Assignment toggle failed:', data.error);
            alert('Failed to toggle assignment completion: ' + (data.error || 'Unknown error'));
            // Revert checkbox state on failure
            checkbox.checked = !checkbox.checked;
        }
    })
    .catch(error => {
        console.error('Error toggling assignment:', error);
        alert('Error toggling assignment: ' + error.message);
        // Revert checkbox state on error
        checkbox.checked = !checkbox.checked;
    })
    .finally(() => {
        // Remove from pending requests
        pendingRequests.delete(itemId);
    });
}

function toggleTodoCompletion(itemId, completed, checkbox) {
    const csrfTokenElement = document.querySelector('meta[name="csrf-token"]');
    const toggleUrlElement = document.querySelector('meta[name="toggle-todo-url"]');

    if (!csrfTokenElement) {
        console.error('CSRF token not found');
        alert('Security token not found. Please refresh the page.');
        checkbox.checked = !checkbox.checked;
        return;
    }

    if (!toggleUrlElement) {
        console.error('Toggle todo URL not found');
        alert('Configuration error. Please refresh the page.');
        checkbox.checked = !checkbox.checked;
        return;
    }

    const csrfToken = csrfTokenElement.getAttribute('content');
    const baseUrl = toggleUrlElement.getAttribute('content');
    console.log('Toggling todo completion:', itemId, 'to completed:', completed);

    // Add to pending requests
    pendingRequests.add(itemId);

    // Use FormData to send CSRF token as form data
    const formData = new FormData();
    formData.append('csrf_token', csrfToken);

    fetch(baseUrl.replace('0', itemId), {
        method: 'POST',
        body: formData
    })
    .then(response => {
        console.log('Response status:', response.status);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return response.text().then(text => {
            try {
                return JSON.parse(text);
            } catch (e) {
                console.error('Server returned non-JSON response:', text.substring(0, 200));
                throw new Error('Server error: Expected JSON response but got HTML. Check server logs.');
            }
        });
    })
    .then(data => {
        console.log('Toggle response:', data);
        if (data.success) {
            // Set the checkbox state based on server response
            checkbox.checked = data.is_completed;
            console.log('Todo toggle successful, is_completed:', data.is_completed);
            
            // If the todo is completed, handle the UI update
            if (data.is_completed) {
                const row = checkbox.closest('tr');
                if (row) {
                    // Add visual feedback for completion
                    row.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
                    row.style.opacity = '0.7';
                    row.style.textDecoration = 'line-through';
                    
                    // Optionally remove the row after a delay
                    setTimeout(() => {
                        row.style.opacity = '0';
                        row.style.transform = 'translateX(-20px)';
                        setTimeout(() => {
                            row.remove();
                        }, 500);
                    }, 1000); // Wait 1 second before starting fade out
                }
            }
        } else {
            console.error('Server returned failure:', data);
            alert('Failed to toggle todo: ' + (data.error || 'Unknown error'));
            // Revert checkbox state on failure
            checkbox.checked = !checkbox.checked;
        }
    })
    .catch(error => {
        console.error('Error toggling todo:', error);
        alert('Error toggling todo item: ' + error.message);
        // Revert checkbox state on error
        checkbox.checked = !checkbox.checked;
    })
    .finally(() => {
        // Remove from pending requests
        pendingRequests.delete(itemId);
    });
}

// Edit todo function
function editTodo(todoId, description, dueDate, courseId) {
    const modal = document.getElementById('edit-todo-modal');
    const form = document.getElementById('edit-todo-form');

    // Set the form action
    form.action = `/update_todo_item/${todoId}`;

    // Populate the form fields
    document.getElementById('edit-todo-id').value = todoId;
    document.getElementById('edit-description').value = description;
    document.getElementById('edit-due-date').value = dueDate;
    document.getElementById('edit-course').value = courseId || '';

    // Show the modal
    modal.classList.remove('hidden');
}

// Open import modal function
function openImportModal() {
    const modal = document.getElementById('import-modal');
    modal.classList.remove('hidden');
}

document.addEventListener('DOMContentLoaded', function () {
    // Add event listeners to all todo checkboxes
    const checkboxes = document.querySelectorAll('.todo-checkbox');
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function(event) {
            const itemId = this.dataset.itemId;
            const itemType = this.dataset.itemType;
            console.log('Checkbox changed:', itemId, itemType, 'checked:', this.checked);
            
            if (itemType === 'todo') {
                handleTodoToggle(itemId, this, this.checked);
            } else if (itemType === 'assignment') {
                handleAssignmentToggle(itemId, this);
            }
        });
    });
    // Submit assignment score
    const assignmentModalForm = document.getElementById('assignment-modal-form');
    if (assignmentModalForm) {
        assignmentModalForm.addEventListener('submit', function (event) {
            event.preventDefault();
            const formData = new FormData(this);
            // Ensure CSRF token is included
            const csrfToken = document.querySelector('meta[name="csrf-token"]').getAttribute('content');
            formData.append('csrf_token', csrfToken);
            fetch('/submit_assignment_score', {
                method: 'POST',
                body: formData,
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Remove the assignment row from the table
                    const assignmentId = formData.get('assignment_id');
                    const row = document.querySelector(`input[onclick*="'${assignmentId}'"]`).closest('tr');
                    row.remove();

                    // Close the modal
                    document.getElementById('assignment-modal').classList.add('hidden');
                } else {
                    alert('Failed to save assignment score.');
                }
            })
            .catch(error => console.error('Error:', error));
        });
    }

    // Close assignment modal
    const closeModalBtn = document.getElementById('close-modal');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', function () {
            document.getElementById('assignment-modal').classList.add('hidden');
        });
    }

    // Close edit todo modal
    const closeEditModalBtn = document.getElementById('close-edit-modal');
    if (closeEditModalBtn) {
        closeEditModalBtn.addEventListener('click', function () {
            document.getElementById('edit-todo-modal').classList.add('hidden');
        });
    }

    // Submit edit todo form
    const editTodoForm = document.getElementById('edit-todo-form');
    if (editTodoForm) {
        editTodoForm.addEventListener('submit', function (event) {
            // Let the form submit normally - it will redirect back to the todo page
        });
    }

    // Actions dropdown functionality
    const actionsDropdownBtn = document.getElementById('actions-dropdown-btn');
    const actionsDropdown = document.getElementById('actions-dropdown');

    if (actionsDropdownBtn && actionsDropdown) {
        // Toggle dropdown on button click
        actionsDropdownBtn.addEventListener('click', function (event) {
            event.stopPropagation();
            actionsDropdown.classList.toggle('hidden');
        });

        // Close dropdown when clicking outside
        document.addEventListener('click', function (event) {
            if (!actionsDropdownBtn.contains(event.target) && !actionsDropdown.contains(event.target)) {
                actionsDropdown.classList.add('hidden');
            }
        });
    }

    // Close import modal
    const closeImportModalBtn = document.getElementById('close-import-modal');
    if (closeImportModalBtn) {
        closeImportModalBtn.addEventListener('click', function () {
            document.getElementById('import-modal').classList.add('hidden');
        });
    }
});