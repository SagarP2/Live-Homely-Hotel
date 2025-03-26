// Confirmation for deleting a room
function confirmDelete(roomId) {
    const confirmation = confirm(`Are you sure you want to delete room ID: ${roomId}?`);
    if (confirmation) {
        window.location.href = `/delete_room/${roomId}`;
    }
}

// Toggle visibility of the add/edit form
function toggleForm(formId) {
    const form = document.getElementById(formId);
    if (form.style.display === 'none' || form.style.display === '') {
        form.style.display = 'block';
    } else {
        form.style.display = 'none';
    }
}

// Real-time form validation
document.addEventListener('DOMContentLoaded', () => {

    const form = document.getElementById('room-form');

    if (form) {
        form.addEventListener('submit', (event) => {
            const price = document.getElementById('price').value;
            const image = document.getElementById('image').files[0];
            
            if (isNaN(price) || parseFloat(price) <= 0) {
                alert('Please enter a valid price.');
                event.preventDefault();
                return;
            }

            if (image) {
                const validExtensions = ['image/jpeg', 'image/png', 'image/jpg'];
                if (!validExtensions.includes(image.type)) {
                    alert('Please upload a valid image file (JPEG, JPG, PNG).');
                    event.preventDefault();
                }
            }
        });
    }
});

// Filter rooms by availability
function filterRooms() {
    const filter = document.getElementById('availability-filter').value.toLowerCase();
    const rows = document.querySelectorAll('tbody tr');

    rows.forEach(row => {
        const availability = row.children[3].textContent.toLowerCase();
        row.style.display = (availability.includes(filter) || filter === 'all') ? '' : 'none';
    });
}

// Display room image preview before uploading
function previewImage() {
    const input = document.getElementById('image');
    const preview = document.getElementById('image-preview');

    const file = input.files[0];
    if (file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            preview.src = e.target.result;
            preview.style.display = 'block';
        };
        reader.readAsDataURL(file);
    } else {
        preview.style.display = 'none';
    }
}
