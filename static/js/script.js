// static/js/script.js

document.addEventListener('DOMContentLoaded', function () {
    console.log('script.js loaded successfully!');

    // Example: Show a message when a form is submitted
    const form = document.querySelector('form');
    if (form) {
        form.addEventListener('submit', function () {
            alert('Form submitted!');
        });
    }

    // Example: Toggle visibility of an element with ID 'extraInfo'
    const toggleButton = document.getElementById('toggleButton');
    const extraInfo = document.getElementById('extraInfo');
    if (toggleButton && extraInfo) {
        toggleButton.addEventListener('click', function () {
            extraInfo.style.display = (extraInfo.style.display === 'none') ? 'block' : 'none';
        });
    }
});
