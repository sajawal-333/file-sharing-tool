const form = document.getElementById("upload-form");
const progressContainer = document.getElementById("progress-container");
const progressBar = document.getElementById("progress-bar");
const progressText = document.getElementById("progress-text");

if (form) {
    form.addEventListener("submit", (event) => {
        event.preventDefault();

        const fileInput = document.getElementById("file");
        if (!fileInput.files.length) {
            alert("Please choose a file.");
            return;
        }

        const file = fileInput.files[0];
        const maxBytes = 1024 * 1024 * 1024;
        if (file.size > maxBytes) {
            alert("File is larger than 1 GB limit.");
            return;
        }

        const formData = new FormData(form);
        const xhr = new XMLHttpRequest();

        xhr.open("POST", form.action, true);

        if (progressContainer && progressBar && progressText) {
            xhr.upload.addEventListener("loadstart", () => {
                progressContainer.classList.remove("hidden");
                progressText.classList.remove("hidden");
                progressBar.style.width = "0%";
                progressText.textContent = "0%";
            });

            xhr.upload.addEventListener("progress", (e) => {
                if (e.lengthComputable) {
                    const percent = Math.round((e.loaded / e.total) * 100);
                    progressBar.style.width = percent + "%";
                    progressText.textContent = percent + "%";
                }
            });
        }

        xhr.onreadystatechange = () => {
            if (xhr.readyState === XMLHttpRequest.DONE) {
                if (xhr.status >= 200 && xhr.status < 300) {
                    // Replace the page with the server's response (success page with link)
                    document.open();
                    document.write(xhr.responseText);
                    document.close();
                } else if (xhr.status === 413) {
                    alert("File is too large. Maximum allowed size is 1 GB.");
                } else {
                    alert("Upload failed. Please try again.");
                }
            }
        };

        xhr.send(formData);
    });
}

