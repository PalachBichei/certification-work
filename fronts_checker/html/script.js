let counter = 0

document.getElementById('uploadButton').addEventListener('click', function () {
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];
    const maxSize = 10 * 1024 * 1024;

    if (!file) {
        showMessage('Необходимо выбрать файл', true);
        return;
    }

    if (file.size > maxSize) {
        showMessage('Максимальный размер файла не должен превышать 10МБ', true);
        return;
    }

    const formData = new FormData();
    formData.append('file', file);

    document.getElementById('loader').classList.remove('hidden');

    fetch('http://localhost:8000/upload', {
        method: 'POST',
        body: formData,
    })
        .then(response => {
            if (response) {
                return response.json()
            }
        })
        .then(data => {
            const isViolation = data.class_name;
            if(isViolation == "Two_People_error\n")
                showModal("Выявлено нарушение пдд")
            else
                showModal("Не выявлено нарушение пдд")
        })

        .catch(error => {
            showMessage('Не удалось загрузить файл: ' + error.message, true);
        })
        .finally(() => {
            document.getElementById('loader').classList.add('hidden');
        });
});

function showMessage(message, isError = false) {
    if (isError) {
        const errorToast = document.getElementById('errorToast');
        const errorMessage = document.getElementById('errorMessage');

        errorMessage.textContent = message;
        errorToast.style.display = 'block';
        errorToast.classList.add('show');

        setTimeout(() => {
            errorToast.classList.remove('show');
            setTimeout(() => {
                errorToast.style.display = 'none';
            }, 300);
        }, 2000);
    } else {
        const messageElement = document.getElementById('message');
        messageElement.textContent = message;
        messageElement.classList.remove('error');
    }
}

function showModal(message) {
    const modal = document.getElementById('modal');
    const modalMessage = document.getElementById('modalMessage');
    const closeButton = document.querySelector('.close');

    if (modal && modalMessage && closeButton) {
        modalMessage.textContent = message;
        modal.classList.remove('hidden');

        modal.addEventListener('click', function (event) {
            if (event.target === modal) {
                modal.classList.add('hidden');
            }
        });

        closeButton.addEventListener('click', function () {
            modal.classList.add('hidden');
        });
    } else {
        console.error('Элементы модального окна не найдены');
    }
}

// document.getElementById('closeModal').addEventListener('click', function () {
//     const modal = document.getElementById('modal');
//     modal.classList.add('hidden');
// });
