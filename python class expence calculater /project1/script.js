/* script.js */
document.addEventListener("DOMContentLoaded", function() {
    // Set the date input to today's date automatically
    const dateInput = document.querySelector('input[type="date"]');
    if(dateInput) {
        dateInput.valueAsDate = new Date();
    }
});