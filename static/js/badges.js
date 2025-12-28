document.addEventListener('DOMContentLoaded', function () {
    fetch('/get_todo_counts')
        .then(response => response.json())
        .then(data => {
            const overdueBadge = document.getElementById('todo-badge-overdue');
            const weekBadge = document.getElementById('todo-badge-week');

            if (data.overdue > 0) {
                overdueBadge.textContent = data.overdue;
                overdueBadge.classList.remove('hidden');
            } else {
                overdueBadge.classList.add('hidden');
            }

            if (data.week > 0) {
                weekBadge.textContent = data.week;
                weekBadge.classList.remove('hidden');
            } else {
                weekBadge.classList.add('hidden');
            }
        })
        .catch(error => console.error('Error fetching ToDo counts:', error));
});