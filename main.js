document.addEventListener('DOMContentLoaded', () => {
    fetchTasks();

    document.getElementById('taskForm').addEventListener('submit', async (e) => {
        e.preventDefault();

        const name = document.getElementById('taskName').value;
        const deadline = document.getElementById('taskDeadline').value;
        const urgency_score = parseInt(document.getElementById('taskUrgency').value);
        const dependencies = document.getElementById('taskDependencies').value.split(',').map(Number).filter(n => !isNaN(n));

        // Data validation
        if (!name.trim()) {
            alert('Task name is required');
            return;
        }
        if (!deadline) {
            alert('Task deadline is required');
            return;
        }
        if (isNaN(urgency_score) || urgency_score < 1 || urgency_score > 10) {
            alert('Urgency score must be a number between 1 and 10');
            return;
        }

        const task = {
            name,
            deadline,
            urgency_score,
            normalized_urgency: urgency_score / 10,
            dependencies
        };

        try {
            const response = await fetch('/tasks', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(task)
            });

            if (!response.ok) {
                throw new Error(`Failed to add task: ${response.status}`);
            }

            fetchTasks();
            e.target.reset();
            alert('Task added successfully!'); // User feedback
        } catch (error) {
            console.error(error);
            alert('Failed to add task. Please try again.'); // User feedback
        }
    });

    document.getElementById('prioritizeBtn').addEventListener('click', async () => {
        try {
            const response = await fetch('/tasks');
            if (!response.ok) {
                throw new Error(`Failed to fetch tasks: ${response.status}`);
            }
            const tasks = await response.json();
            const completed_ids = tasks.filter(t => t.status === 'Completed').map(t => t.id);

            const prioResponse = await fetch('/tasks/prioritize', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ completed_ids })
            });

            if (!prioResponse.ok) {
                throw new Error(`Failed to prioritize tasks: ${prioResponse.status}`);
            }

            const prioritizedTasks = await prioResponse.json();
            renderChart(prioritizedTasks);
            alert('Tasks prioritized successfully!');
        } catch (error) {
            console.error(error);
            alert('Failed to prioritize tasks. Please try again.');
        }
    });
});

async function fetchTasks() {
    try {
        const response = await fetch('/tasks');
        if (!response.ok) {
            throw new Error(`Failed to fetch tasks: ${response.status}`);
        }
        const tasks = await response.json();
        const list = document.getElementById('taskList');
        list.innerHTML = '';

        tasks.forEach(task => {
            const li = document.createElement('li');
            li.textContent = `${task.name} - Deadline: ${task.deadline} - Status: ${task.status}`;
            list.appendChild(li);
        });
    } catch (error) {
        console.error(error);
        alert('Failed to fetch tasks. Please check your network connection.');
    }
}

function renderChart(tasks) {
    const ctx = document.getElementById('taskChart').getContext('2d');
    if (window.taskChart) {
        window.taskChart.destroy();
    }

    window.taskChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: tasks.map(t => t.name),
            datasets: [{
                label: 'Priority Score',
                data: tasks.map(t => t.ml_priority_score), // Use ml_priority_score
                backgroundColor: 'rgba(75, 192, 192, 0.7)',
                borderColor: 'rgba(75, 192, 192, 1)',
                borderWidth: 1
            }]
        },
        options: {  // Add options for better chart display
            responsive: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Priority Score'
                    }
                },
                x: {
                    title: {
                        display: true,
                        text: 'Task Name'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top' // Customize legend position
                }
            }
        }
    });
}

