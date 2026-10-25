document.addEventListener("DOMContentLoaded", function() {
    
    // Check if Python data exists
    if (typeof budgetData === 'undefined') {
        alert("Please run main.py first to generate data!");
        return;
    }

    // 1. Update HTML Text
    document.getElementById("userName").innerText = budgetData.name;
    document.getElementById("incomeDisplay").innerText = "$" + budgetData.income.toLocaleString();
    document.getElementById("expenseDisplay").innerText = "-$" + budgetData.expense.toLocaleString();
    document.getElementById("savingsDisplay").innerText = "$" + budgetData.savings.toLocaleString();
    document.getElementById("statusBadge").innerText = budgetData.status;

    // 2. Render Chart
    const ctx = document.getElementById('budgetChart').getContext('2d');
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: budgetData.labels,
            datasets: [{
                data: budgetData.data,
                backgroundColor: budgetData.colors,
                borderColor: 'rgba(255, 255, 255, 0.2)',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: 'white' }
                }
            }
        }
    });
});